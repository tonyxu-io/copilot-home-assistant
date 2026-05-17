#!/usr/bin/env python3
"""Action queue detector for Tony's email-butler.

Read-only. Finds recent actionable emails and emits only new high-signal items since last run.
For reply-worthy items, includes a concise suggested draft reply. It never sends, replies,
marks read, archives, or deletes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

GWS = "/home/linuxbrew/.linuxbrew/bin/gws"
LLM_CLI = os.environ.get("LLM_CLI_PATH", "/home/tonyxu/.npm-global/bin/copilot")
STATE_PATH = Path.home() / ".local" / "state" / "copilot-home-assistant" / "email_butler_action_queue.json"
REDACT_RE = re.compile(r"(ya29\.[A-Za-z0-9._-]+|Bearer\s+[^\s]+|gh[pousr]_[A-Za-z0-9_]+|[A-Za-z0-9_=-]{120,})")

QUERY = 'newer_than:14d (label:"Action Needed" OR label:Recruiting OR "open to a quick call" OR "quick call" OR "would love to tell you more" OR "please sign" OR "action required" OR "requires your attention" OR "final notice" OR "verify your" OR "document to sign" OR "complete your" OR "payment failed" OR "failed payment" OR "tax deadline" OR "security alert" OR "new login" OR "new sign-in" OR "account locked" OR "container stopped unexpectedly" OR "backup failed" OR "certificate expiring") -category:promotions -category:social -category:forums'
MAX_RESULTS = 15
MAX_DRAFTS = 3

# Wall-clock budget. The wrapper (email_butler_ops.py) hard-kills this
# subprocess at 600s, so we leave ourselves a comfortable margin to emit a
# well-formed partial-result JSON instead of being SIGKILLed mid-output.
SOFT_DEADLINE_S = 480
GWS_TIMEOUT_S = 45  # Gmail API HTTP calls; anything past this is a hang.
LLM_TIMEOUT_S = 45  # Copilot CLI for short structured replies.

_START_TIME = time.time()


def _elapsed() -> float:
    return time.time() - _START_TIME


def log(msg: str) -> None:
    """Emit a timestamped progress line to stderr for forensic timeout debugging."""
    print(f"[aq +{_elapsed():6.1f}s] {msg}", file=sys.stderr, flush=True)


def soft_deadline_hit() -> bool:
    return _elapsed() >= SOFT_DEADLINE_S

IGNORE_FROM = re.compile(r"(noreply@medium|newsletter|substack|linkedin job|indeed|ziprecruiter)", re.I)
LOW_SIGNAL_SUBJECT = re.compile(r"(sale|discount|webinar|digest|newsletter|recommended|promotion|completed a scheduled task|success|succeeded|has recovered|resolved)", re.I)
NO_REPLY_FROM = re.compile(r"(no-?reply|do-?not-?reply|notification|alerts?|ealerts|donotreply)", re.I)
SELF_EMAILS = {"yihan.xu@gmail.com"}
ACK_ONLY_RE = re.compile(r"^(thanks|thank you|thx|got it|sounds good|ok|okay|appreciate it|no worries)\b", re.I)
ACTION_ASK_RE = re.compile(r"(\?|please|can you|could you|would you|let me know|schedule|available|quick call|call this week|next step|follow up)", re.I)


def redact(text: str) -> str:
    return REDACT_RE.sub("[REDACTED]", text)


def decode_jsonish(output: str) -> Any:
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(output):
        if ch not in "[{":
            continue
        try:
            payload, _end = decoder.raw_decode(output[idx:].strip())
            return payload
        except json.JSONDecodeError:
            continue
    return None


def retry_call(fn: Callable[[], Any], attempts: int = 3, base_delay: float = 1.5) -> Any:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt == attempts - 1:
                break
            time.sleep(base_delay * (2 ** attempt))
    assert last_exc is not None
    raise last_exc


def _cmd_label(cmd: list[str]) -> str:
    """Short forensic label for a subprocess call.

    Captures the binary basename plus the first few args so a hang can be
    pinpointed to a specific gws/copilot invocation in stderr — without
    leaking message IDs, query strings, or token-bearing flags.
    """
    if not cmd:
        return "?"
    base = os.path.basename(cmd[0]) or cmd[0]
    safe_args: list[str] = []
    for a in cmd[1:6]:
        if not isinstance(a, str):
            continue
        if a.startswith("--params") or len(a) > 40 or "{" in a or "=" in a and len(a) > 30:
            safe_args.append("<arg>")
        else:
            safe_args.append(a)
    return f"{base} {' '.join(safe_args)}".strip()


def run_cmd(cmd: list[str], timeout: int = GWS_TIMEOUT_S) -> str:
    env = os.environ.copy()
    env["PATH"] = "/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:" + env.get("PATH", "")
    label = _cmd_label(cmd)
    started = time.time()
    log(f"exec> {label} (timeout={timeout}s)")
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        # Forensic breadcrumb: the offending subprocess hit its hard timeout.
        # The wrapper still gets to see WHICH call hung, which is exactly the
        # information PR #7 was missing when only loop-boundary logs existed.
        log(f"exec! {label} TIMEOUT after {time.time()-started:.1f}s")
        raise
    dur = time.time() - started
    out = proc.stdout or ""
    err = proc.stderr or ""
    log(f"exec< {label} rc={proc.returncode} dur={dur:.1f}s bytes_out={len(out)}")
    if proc.returncode != 0:
        raise RuntimeError(redact(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{out}\n{err}")[:2000])
    return out


def run_gws(args: list[str]) -> Any:
    return decode_jsonish(run_cmd([GWS, *args], timeout=GWS_TIMEOUT_S))


def email_from_header(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("email") or "").lower()
    text = str(value or "")
    m = re.search(r"<([^>]+)>", text)
    return (m.group(1) if m else text).strip().lower()


def header_value(message: dict[str, Any], name: str) -> str:
    headers = ((message.get("payload") or {}).get("headers") or [])
    for header in headers:
        if str(header.get("name", "")).lower() == name.lower():
            return str(header.get("value") or "")
    return ""


def newest_thread_message(mid: str, raw: dict[str, Any] | None = None) -> dict[str, Any] | None:
    thread_id = None
    if isinstance(raw, dict):
        thread_id = raw.get("thread_id") or raw.get("threadId")
    if not thread_id:
        try:
            fetched = read_message(mid)
            thread_id = fetched.get("thread_id") or fetched.get("threadId")
        except Exception:
            thread_id = None
    if not thread_id:
        thread_id = mid
    data = run_gws([
        "gmail", "users", "threads", "get",
        "--params", json.dumps({
            "userId": "me",
            "id": thread_id,
            "format": "metadata",
            "metadataHeaders": ["From", "To", "Subject", "Date"],
        }),
        "--format", "json",
    ])
    messages = data.get("messages", []) if isinstance(data, dict) else []
    if not messages:
        return None
    return max(messages, key=lambda x: int(x.get("internalDate") or 0))


def already_handled_or_ack(mid: str, body: str = "", raw: dict[str, Any] | None = None) -> bool:
    try:
        newest = newest_thread_message(mid, raw=raw)
    except Exception:
        return False
    if not newest:
        return False
    newest_id = newest.get("id")
    from_email = email_from_header(header_value(newest, "From"))
    snippet = str(newest.get("snippet") or "")
    text = re.sub(r"\s+", " ", snippet or body).strip()
    if from_email in SELF_EMAILS:
        return True
    if is_ack_only_response(text):
        return True
    if newest_id != mid and is_ack_only_response(body):
        return True
    return False


def leading_unquoted_text(text: str) -> str:
    lines = []
    for line in str(text or "").replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if re.match(r"^On .+ wrote:$", stripped, re.I) or stripped.startswith(">") or stripped.startswith("-----Original Message-----"):
            break
        lines.append(stripped)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def is_ack_only_response(text: str) -> bool:
    leading = leading_unquoted_text(text)
    if not leading:
        return False
    return bool(ACK_ONLY_RE.search(leading) and not ACTION_ASK_RE.search(leading))


def triage() -> list[dict[str, Any]]:
    data = run_gws(["gmail", "+triage", "--max", str(MAX_RESULTS), "--query", QUERY, "--format", "json"])
    msgs = data.get("messages", []) if isinstance(data, dict) else data or []
    out = []
    for m in msgs:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        frm = m.get("from", "")
        subj = m.get("subject", "")
        if not mid or IGNORE_FROM.search(frm) or LOW_SIGNAL_SUBJECT.search(subj):
            continue
        if re.search(r"authentication code|verification code|one-time code", subj, re.I) and not re.search(r"security alert|new login|new sign-in|password", subj, re.I):
            continue
        out.append({
            "id": mid,
            "from": frm,
            "subject": subj,
            "date": m.get("date", ""),
        })
    return out


def read_message(mid: str) -> dict[str, Any]:
    data = run_gws(["gmail", "+read", "--id", mid, "--format", "json"])
    return data if isinstance(data, dict) else {}


def first_name(sender: str) -> str:
    m = re.match(r'"?([^"<@]+)', sender.strip())
    raw = (m.group(1) if m else "").strip()
    raw = raw.split()[0] if raw else ""
    return raw or "there"


def classify(subject: str, frm: str, body: str = "") -> str:
    text = f"{subject} {frm} {body[:2000]}".lower()
    if any(k in text for k in ["hiring", "recruiter", "career opportunity", "job opportunity", "senior product engineer", "engineering role", "open to a quick call", "quick call this week"]):
        return "招聘"
    if any(k in text for k in ["sign", "document", "docusign", "verified.eu"]):
        return "签署/文件"
    if any(k in text for k in ["security", "login", "password", "verify", "2fa", "verification", "account locked"]):
        return "安全"
    if any(k in text for k in ["container stopped", "backup failed", "certificate expiring", "down", "outage", "failed"]):
        return "基础设施"
    if any(k in text for k in ["payment", "invoice", "transfer", "statement", "tax", "bill"]):
        return "财务"
    if any(k in text for k in ["final notice", "inactive", "deleted", "required", "requires", "please respond", "please reply"]):
        return "需处理"
    return "需判断"


def is_reply_worthy(kind: str, frm: str, subject: str, body: str) -> bool:
    text = f"{subject} {body[:2000]}".lower()
    if NO_REPLY_FROM.search(frm):
        return False
    if kind == "招聘":
        return True
    if kind in {"安全", "基础设施", "财务", "签署/文件"}:
        return False
    return bool(re.search(r"(please reply|please respond|let me know|open to|quick call|schedule|available|can you|could you)", text, re.I))


def deterministic_recruiting_decline(sender: str) -> str:
    name = first_name(sender)
    return f"Hi {name},\n\nThanks for reaching out. I'm not looking for new opportunities right now, but appreciate you thinking of me.\n\nTony"


def llm_json(prompt: str) -> Any:
    out = run_cmd([
        LLM_CLI, "-p", prompt, "--no-color", "--no-custom-instructions",
        "--deny-tool=shell", "--deny-tool=write", "--deny-tool=read",
        "--deny-tool=edit", "--deny-tool=create", "--deny-tool=bash",
        "--deny-tool=write_bash", "--deny-tool=read_bash",
        "--disable-builtin-mcps",
    ], timeout=LLM_TIMEOUT_S)
    return decode_jsonish(out)


def model_draft_reply(message: dict[str, Any], kind: str) -> str | None:
    if kind == "招聘":
        return deterministic_recruiting_decline(message.get("from", ""))
    body = (message.get("body_text") or "")[:3000]
    prompt = f"""
Draft a concise email reply in Tony Xu's style.

Tony's style:
- concise, efficient, friendly
- default greeting: Hi [First Name],
- 1-3 sentences for most replies
- sign off with Tony
- no bullets, no emoji, no over-explaining

Safety:
- Return ONLY JSON: {{"draft_reply":"..."}}
- Do not send anything.
- If the message is not appropriate for a reply draft, return {{"draft_reply":null}}.

Message kind: {kind}
From: {message.get('from')}
Subject: {message.get('subject')}
Body excerpt:
{body}
""".strip()
    data = llm_json(prompt)
    draft = data.get("draft_reply") if isinstance(data, dict) else None
    return draft if isinstance(draft, str) and draft.strip() else None


def public_item(m: dict[str, Any], draft: str | None) -> dict[str, Any]:
    out = {"kind": m["kind"], "from": m["from"], "subject": m["subject"], "date": m["date"]}
    if draft:
        out["suggested_reply"] = draft
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-seen", action="store_true", help="include already-seen action candidates in output")
    parser.add_argument("--no-state-update", action="store_true", help="do not update seen state")
    parser.add_argument("--max-drafts", type=int, default=MAX_DRAFTS)
    args = parser.parse_args()

    if not Path(GWS).exists():
        print(json.dumps({"status": "error", "error": f"gws not found at {GWS}"}))
        return 1
    if not Path(LLM_CLI).exists():
        print(json.dumps({"status": "error", "error": f"LLM CLI not found at {LLM_CLI}"}))
        return 1

    state = {"seen": []}
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    seen = set(state.get("seen", []))
    log("triage:start")
    msgs = retry_call(triage)
    log(f"triage:done candidates={len(msgs)}")
    selected = msgs if args.include_seen else [m for m in msgs if m["id"] not in seen]
    log(f"selected={len(selected)} (after seen filter)")

    items: list[dict[str, Any]] = []
    draft_count = 0
    deadline_hit = False
    processed = 0
    for m in selected[:8]:
        if soft_deadline_hit():
            deadline_hit = True
            log(f"soft-deadline reached after {processed}/{len(selected[:8])} items; emitting partial result")
            break
        processed += 1
        mid = m["id"]
        log(f"item[{processed}] read id={mid}")
        try:
            raw = retry_call(lambda mid=mid: read_message(mid), attempts=2, base_delay=1)
        except Exception as exc:
            log(f"item[{processed}] read failed: {redact(str(exc))[:200]}")
            continue
        body = raw.get("body_text") or raw.get("snippet") or ""
        if email_from_header(raw.get("from")) in SELF_EMAILS or already_handled_or_ack(mid, body, raw=raw):
            log(f"item[{processed}] filtered (self/ack/handled)")
            continue
        m["kind"] = classify(m.get("subject", ""), m.get("from", ""), body)
        message_for_draft = {
            "from": m.get("from", ""),
            "subject": m.get("subject", ""),
            "body_text": body,
        }
        draft = None
        if (
            draft_count < max(0, args.max_drafts)
            and not soft_deadline_hit()
            and is_reply_worthy(m["kind"], m.get("from", ""), m.get("subject", ""), body)
        ):
            try:
                log(f"item[{processed}] llm draft kind={m['kind']}")
                draft = model_draft_reply(message_for_draft, m["kind"])
                if draft:
                    draft_count += 1
            except Exception as exc:
                log(f"item[{processed}] llm draft failed: {redact(str(exc))[:200]}")
                draft = None
        items.append(public_item(m, draft))

    if not args.no_state_update:
        seen.update(m["id"] for m in msgs)
        seen.update(item.get("id") for item in selected if item.get("id"))
        state = {"last_run_epoch": int(time.time()), "seen": sorted(seen)[-1000:]}
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))

    # `selected` is the raw set of newly-seen candidates from Gmail search.
    # Some candidates are intentionally filtered after reading full thread state
    # (for example, a recruiter thread whose newest message is Tony's sent reply).
    # User-facing notifications must count emitted actionable items, not raw
    # candidates, otherwise cron reports "1 new item" with no details.
    print(json.dumps({
        "status": "success",
        "new_count": len(items),
        "candidate_count": len(selected),
        "filtered_count": max(0, len(selected) - len(items)),
        "items": items,
        "draft_count": draft_count,
        "mode": "read-only-action-queue-with-draft-suggestions",
        "safety": "no send/reply/forward/archive/delete/mark-read",
        "partial": deadline_hit,
        "elapsed_s": round(_elapsed(), 1),
    }, ensure_ascii=False))
    log(f"done items={len(items)} drafts={draft_count} partial={deadline_hit} elapsed={_elapsed():.1f}s")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "error": redact(str(exc))}, ensure_ascii=False))
        raise
