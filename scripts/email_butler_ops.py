#!/usr/bin/env python3
"""Consolidated email-butler ops wrapper.

Owns:
- Gmail label maintenance
- Action Queue scan
- Low-risk archive during 19:00 hour
- Gmail + Calendar collectors
- Gmail digest staging
- gbrain import of Gmail/Calendar digests without embeddings

Outputs JSON with safe summaries only. No message IDs, tokens, OAuth secrets, DB URLs, or full sensitive bodies.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

HOME = Path.home()
SCRIPTS_DIR = Path(__file__).resolve().parent
STATE_DIR = HOME / ".local" / "state" / "copilot-home-assistant"
OPS_LATEST_PATH = STATE_DIR / "email_butler_ops_latest.json"
OPS_HISTORY_PATH = STATE_DIR / "email_butler_ops_history.json"
BRAIN = Path("/home/tonyxu/brain")
COLLECTORS = BRAIN / "scripts" / "collectors"
REDACT_RE = re.compile(
    r"(postgresql://[^\s]+|postgres://[^\s]+|ya29\.[A-Za-z0-9._-]+|Bearer\s+[^\s]+|gh[pousr]_[A-Za-z0-9_]+|[A-Za-z0-9_=-]{120,})"
)

LABEL_SCRIPT = SCRIPTS_DIR / "email_butler_label_maintenance.py"
ACTION_SCRIPT = SCRIPTS_DIR / "email_butler_action_queue.py"
ARCHIVE_SCRIPT = SCRIPTS_DIR / "email_butler_low_risk_archive.py"

# Wall-clock budget for the whole wrapper. The email-butler agent hard-kills
# this process at ~480s, so we leave a margin to flush partial JSON + state.
# Each sub-step gets min(step_cap, remaining_budget - RESERVE_S). When the
# budget is exhausted, remaining steps are short-circuited as "skipped_deadline"
# instead of being SIGKILLed mid-run by the parent agent.
SOFT_DEADLINE_S = 420
RESERVE_S = 20  # headroom kept aside for serialization + state write

# Per-step timeout caps (seconds). Tight, based on observed runtimes
# (gmail collect ~106s, calendar collect ~4s, calendar import ~29s, all
# others <5s on Tony's live inbox 2026-05-17), plus generous headroom.
STEP_TIMEOUT = {
    "labels": 120,
    "action_queue": 510,  # action_queue.py has its own 480s SOFT_DEADLINE_S
    "archive": 180,
    "collect_gmail": 240,
    "collect_calendar": 90,
    "stage_gmail": 60,
    "import_gmail": 120,
    "import_calendar": 120,
}

_START_TIME = time.time()


def _elapsed() -> float:
    return time.time() - _START_TIME


def log(msg: str) -> None:
    """Timestamped progress to stderr — survives partial runs for forensics."""
    print(f"[ebops +{_elapsed():6.1f}s] {msg}", file=sys.stderr, flush=True)


def remaining_budget() -> float:
    return SOFT_DEADLINE_S - _elapsed()


def budget_for(step: str) -> int:
    """Return the timeout to pass to subprocess for this step.

    Caps at STEP_TIMEOUT[step] and at remaining_budget - RESERVE_S so a hung
    child can never silently exceed the wrapper's soft deadline.
    """
    cap = STEP_TIMEOUT.get(step, 120)
    return max(1, min(cap, int(remaining_budget() - RESERVE_S)))


def deadline_hit() -> bool:
    return remaining_budget() <= RESERVE_S


def redact(text: str) -> str:
    return REDACT_RE.sub("[REDACTED]", text)


def parse_jsonish(text: str) -> Any:
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "[{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[idx:])
            return payload
        except json.JSONDecodeError:
            continue
    return None


def run_cmd(cmd: str, *, cwd: Path | None = None, timeout: int = 600) -> dict[str, Any]:
    env = os.environ.copy()
    env["PATH"] = "/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:/home/tonyxu/.bun/bin:" + env.get("PATH", "")
    started = time.time()
    try:
        proc = subprocess.run(["bash", "-lic", cmd], cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        partial = redact(((exc.stdout or "") + ("\nSTDERR:\n" + (exc.stderr or "") if exc.stderr else ""))) if (exc.stdout or exc.stderr) else ""
        return {
            "status": "error",
            "exit_code": 124,
            "json": None,
            "tail": (partial[-2000:] if partial else f"TimeoutExpired after {timeout}s"),
            "duration_s": round(time.time() - started, 1),
            "timed_out": True,
        }
    out = redact((proc.stdout or "") + ("\nSTDERR:\n" + proc.stderr if proc.stderr else ""))
    payload = parse_jsonish(out)
    return {
        "status": "success" if proc.returncode == 0 else "error",
        "exit_code": proc.returncode,
        "json": payload,
        "tail": out[-2000:],
        "duration_s": round(time.time() - started, 1),
        "timed_out": False,
    }


def run_python(script_name: str, *, cwd: Path = COLLECTORS, timeout: int = 600) -> dict[str, Any]:
    return run_cmd(f"python3 {script_name}", cwd=cwd, timeout=timeout)


def deadline_step(name: str) -> dict[str, Any]:
    """Synthetic step result for steps skipped because the soft deadline hit."""
    return {
        "status": "skipped_deadline",
        "exit_code": None,
        "json": {"status": "skipped_deadline", "reason": f"wrapper soft deadline {SOFT_DEADLINE_S}s reached before step {name}"},
        "tail": "",
        "duration_s": 0.0,
        "timed_out": False,
    }


def summarize_import(step: dict[str, Any]) -> dict[str, Any]:
    data = step.get("json")
    if isinstance(data, dict):
        return {
            "status": data.get("status", step.get("status")),
            "imported": data.get("imported"),
            "skipped": data.get("skipped"),
            "errors": data.get("errors"),
            "chunks": data.get("chunks"),
            "total_files": data.get("total_files"),
            "exit_code": step.get("exit_code"),
        }
    return {"status": step.get("status"), "exit_code": step.get("exit_code"), "tail": step.get("tail", "")[-500:]}


def summarize_generic_step(step: dict[str, Any]) -> dict[str, Any]:
    """Keep only safe, compact status/count fields from collector outputs."""
    allowed_keys = {
        "status", "exit_code", "count", "total", "processed", "written", "created",
        "updated", "skipped", "errors", "messages", "events", "digests", "files",
        "new", "changed", "duration_s",
    }
    out: dict[str, Any] = {}
    for key, value in step.items():
        if key not in allowed_keys:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, list):
            out[key] = len(value)
        elif isinstance(value, dict):
            out[key] = {k: v for k, v in value.items() if k in allowed_keys and isinstance(v, (str, int, float, bool))}
    if "status" not in out:
        out["status"] = step.get("status", "unknown")
    return out


def public_maintenance_summary(result: dict[str, Any], now: datetime) -> dict[str, Any]:
    labels = result.get("labels") if isinstance(result.get("labels"), dict) else {}
    label_rules = labels.get("rules", []) if isinstance(labels, dict) else []
    safe_label_rules = []
    total_new_labeled = 0
    for rule in label_rules:
        if not isinstance(rule, dict):
            continue
        new_labeled = int(rule.get("new_labeled") or 0)
        total_new_labeled += new_labeled
        safe_label_rules.append({
            "label": rule.get("label"),
            "matched": rule.get("matched"),
            "new_labeled": new_labeled,
        })

    action_queue = result.get("action_queue") if isinstance(result.get("action_queue"), dict) else {}
    archive = result.get("archive") if isinstance(result.get("archive"), dict) else {}
    sync = result.get("sync") if isinstance(result.get("sync"), dict) else {}

    safe_sync = {}
    for name, step in sync.items():
        if isinstance(step, dict):
            safe_sync[name] = summarize_generic_step(step)
        else:
            safe_sync[name] = {"status": str(step)}

    return {
        "last_run_iso": now.isoformat(),
        "status": result.get("status"),
        "ran_sync": result.get("ran_sync"),
        "sync_hours": result.get("sync_hours"),
        "ran_archive": result.get("ran_archive"),
        "soft_deadline_s": result.get("soft_deadline_s"),
        "deadline_hit": result.get("deadline_hit", False),
        "timed_out_steps": result.get("timed_out_steps", []),
        "step_durations_s": result.get("step_durations_s", {}),
        "step_timeouts_s": result.get("step_timeouts_s", {}),
        "labels": {
            "status": labels.get("status") if isinstance(labels, dict) else None,
            "created_labels": labels.get("created_labels", []) if isinstance(labels, dict) else [],
            "total_new_labeled": total_new_labeled,
            "rules": safe_label_rules,
        },
        "action_queue": {
            "status": action_queue.get("status"),
            "new_count": result.get("new_action_count", 0),
            "candidate_count": action_queue.get("candidate_count"),
            "filtered_count": action_queue.get("filtered_count"),
        },
        "archive": {
            "status": archive.get("status"),
            "total_archived": archive.get("total_archived", 0),
            "rules": [
                {"rule": r.get("rule"), "matched": r.get("matched"), "archived": r.get("archived")}
                for r in archive.get("rules", [])
                if isinstance(r, dict)
            ],
        },
        "sync": safe_sync,
        "safety": "label-only except low-risk archive removes INBOX only; no delete/mark-read/send/reply/forward/calendar writes",
    }


def write_ops_state(result: dict[str, Any], now: datetime) -> None:
    summary = public_maintenance_summary(result, now)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OPS_LATEST_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    history: list[Any] = []
    if OPS_HISTORY_PATH.exists():
        try:
            history = json.loads(OPS_HISTORY_PATH.read_text())
        except Exception:
            history = []
    if not isinstance(history, list):
        history = []
    history.append(summary)
    OPS_HISTORY_PATH.write_text(json.dumps(history[-100:], ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-sync", action="store_true", help="skip Gmail/Calendar collectors + gbrain imports")
    parser.add_argument("--sync-hours", default="8,12,16,20", help="comma-separated local hours when sync should run; empty means every run")
    parser.add_argument("--skip-action", action="store_true", help="skip action queue scan")
    parser.add_argument("--force-archive", action="store_true", help="run low-risk archive regardless of hour")
    args = parser.parse_args()

    now = datetime.now().astimezone()
    sync_hours = {
        int(part.strip())
        for part in str(args.sync_hours or "").split(",")
        if part.strip().isdigit()
    }
    should_sync = (not args.skip_sync) and (not sync_hours or now.hour in sync_hours)
    result: dict[str, Any] = {
        "status": "success",
        "mode": "email-butler-ops-consolidated",
        "ran_archive": False,
        "ran_sync": should_sync,
        "sync_hours": sorted(sync_hours),
        "soft_deadline_s": SOFT_DEADLINE_S,
        "step_durations_s": {},
        "step_timeouts_s": {},
        "deadline_hit": False,
    }
    log(f"start hour={now.hour} should_sync={should_sync} budget={SOFT_DEADLINE_S}s")

    def record_step(name: str, step: dict[str, Any]) -> None:
        result["step_durations_s"][name] = step.get("duration_s")
        if step.get("timed_out"):
            result["status"] = "error"
            result.setdefault("timed_out_steps", []).append(name)

    # Email-butler maintenance layer ---------------------------------------
    if deadline_hit():
        labels = deadline_step("labels")
        result["deadline_hit"] = True
        log("SKIP labels — deadline already hit")
    else:
        t = budget_for("labels")
        result["step_timeouts_s"]["labels"] = t
        log(f"-> labels (timeout={t}s)")
        labels = run_cmd(str(LABEL_SCRIPT), timeout=t)
        log(f"<- labels status={labels['status']} dur={labels.get('duration_s')}s")
    result["labels"] = labels.get("json") if isinstance(labels.get("json"), dict) else labels
    record_step("labels", labels)
    if labels["status"] != "success" or (isinstance(labels.get("json"), dict) and labels["json"].get("status") != "success"):
        result["status"] = "error"

    if args.skip_action:
        result["action_queue"] = {"status": "skipped"}
    elif deadline_hit():
        action = deadline_step("action_queue")
        result["action_queue"] = action["json"]
        record_step("action_queue", action)
        result["deadline_hit"] = True
        result["status"] = "error"
        log("SKIP action_queue — deadline hit")
    else:
        t = budget_for("action_queue")
        result["step_timeouts_s"]["action_queue"] = t
        log(f"-> action_queue (timeout={t}s)")
        action = run_cmd(str(ACTION_SCRIPT), timeout=t)
        log(f"<- action_queue status={action['status']} dur={action.get('duration_s')}s")
        result["action_queue"] = action.get("json") if isinstance(action.get("json"), dict) else action
        record_step("action_queue", action)
        if action["status"] != "success" or (isinstance(action.get("json"), dict) and action["json"].get("status") != "success"):
            result["status"] = "error"

    if args.force_archive or now.hour == 19:
        if deadline_hit():
            archive = deadline_step("archive")
            result["deadline_hit"] = True
            log("SKIP archive — deadline hit")
        else:
            t = budget_for("archive")
            result["step_timeouts_s"]["archive"] = t
            log(f"-> archive (timeout={t}s)")
            archive = run_cmd(str(ARCHIVE_SCRIPT), timeout=t)
            log(f"<- archive status={archive['status']} dur={archive.get('duration_s')}s")
        result["archive"] = archive.get("json") if isinstance(archive.get("json"), dict) else archive
        result["ran_archive"] = True
        record_step("archive", archive)
        if archive["status"] != "success" or (isinstance(archive.get("json"), dict) and archive["json"].get("status") != "success"):
            result["status"] = "error"
    else:
        result["archive"] = {"status": "skipped"}

    # Gmail + Calendar knowledge sync layer --------------------------------
    if should_sync:
        sync: dict[str, Any] = {}
        steps: list[tuple[str, Any]] = [
            ("collect_gmail", lambda t: run_python("collect_gmail.py", timeout=t)),
            ("collect_calendar", lambda t: run_python("collect_calendar.py", timeout=t)),
            ("stage_gmail", lambda t: run_python("stage_gmail_digest_import.py", timeout=t)),
            ("import_gmail", lambda t: run_cmd("source ~/.bashrc >/dev/null 2>&1; gbrain import /home/tonyxu/brain/state/gmail_digest_import_staging --no-embed --json", timeout=t)),
            ("import_calendar", lambda t: run_cmd("source ~/.bashrc >/dev/null 2>&1; gbrain import /home/tonyxu/brain/sources/calendar/digests --no-embed --json", timeout=t)),
        ]
        for name, fn in steps:
            if deadline_hit():
                step = deadline_step(name)
                result["deadline_hit"] = True
                result["status"] = "error"
                log(f"SKIP {name} — deadline hit")
            else:
                t = budget_for(name)
                result["step_timeouts_s"][name] = t
                log(f"-> {name} (timeout={t}s, remaining={remaining_budget():.0f}s)")
                try:
                    step = fn(t)
                except subprocess.TimeoutExpired as exc:
                    step = {"status": "error", "exit_code": 124, "tail": redact(str(exc))[-1000:], "json": None, "duration_s": float(t), "timed_out": True}
                except Exception as exc:
                    step = {"status": "error", "exit_code": 1, "tail": redact(str(exc))[-1000:], "json": None, "duration_s": round(_elapsed(), 1), "timed_out": False}
                log(f"<- {name} status={step.get('status')} dur={step.get('duration_s')}s")
            if name.startswith("import_"):
                sync[name] = summarize_import(step)
            else:
                payload = step.get("json")
                sync[name] = payload if isinstance(payload, dict) else {"status": step.get("status"), "exit_code": step.get("exit_code"), "tail": step.get("tail", "")[-500:]}
            # Preserve duration in per-step output so future hangs are diagnosable.
            if isinstance(sync[name], dict) and step.get("duration_s") is not None:
                sync[name].setdefault("duration_s", step["duration_s"])
            record_step(name, step)
            # strict success criteria
            current = sync[name]
            failed = step.get("status") not in ("success",) and step.get("status") != "skipped_deadline"
            if step.get("status") == "skipped_deadline":
                failed = True
            if isinstance(current, dict):
                if current.get("status") in ("error", "failed", "skipped_deadline"):
                    failed = True
                if current.get("errors") not in (None, 0):
                    failed = True
            if failed:
                result["status"] = "error"
                break
        result["sync"] = sync
    else:
        result["sync"] = {"status": "skipped"}

    aq = result.get("action_queue", {})
    result["new_action_count"] = aq.get("new_count", 0) if isinstance(aq, dict) else 0
    result["new_action_items"] = aq.get("items", []) if isinstance(aq, dict) else []

    write_ops_state(result, now)
    log(f"done status={result['status']} total_elapsed={_elapsed():.1f}s deadline_hit={result.get('deadline_hit')}")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
