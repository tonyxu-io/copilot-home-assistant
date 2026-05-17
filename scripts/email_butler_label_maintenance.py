#!/usr/bin/env python3
"""Model-based Gmail label maintenance for Tony's email-butler cron.

Architecture: scan recent mail, classify each message against all production labels,
then apply labels. Label-only: does not archive, delete, mark read, send, reply, or forward.
Uses gws CLI for Gmail and an external LLM CLI for model classification.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

GWS = "/home/linuxbrew/.linuxbrew/bin/gws"
LLM_CLI = os.environ.get("LLM_CLI_PATH", "/home/tonyxu/.npm-global/bin/copilot")
STATE_PATH = Path.home() / ".local" / "state" / "copilot-home-assistant" / "email_butler_label_maintenance.json"

SCAN_QUERY = "newer_than:7d -in:spam -in:trash"
SCAN_MAX = 500
MAX_REVIEW_PER_RUN = 40
BATCH_SIZE = 20
CLASSIFIER_VERSION = 3
CLASSIFIED_CACHE_SECONDS = 8 * 24 * 60 * 60

REDACT_RE = re.compile(
    r"(ya29\.[A-Za-z0-9._-]+|Bearer\s+[^\s]+|gh[pousr]_[A-Za-z0-9_]+|[A-Za-z0-9_=-]{120,})"
)

LABEL_DEFINITIONS: dict[str, str] = {
    "Family": "family, kids, spouse, school/preschool, childcare, children's activities/classes, family logistics, and parental/family leave logistics. Keep MCC/Bloomz/SVIS/Menlo Swim/Soccer Shots if about Tony's family/kids. Keep parental leave approval/leave-letter messages. Reject generic city/library/retail newsletters.",
    "Receipts": "purchase/payment/order/shipment/delivery/invoice/receipt/statement confirmations or transactional proof. Reject marketing that merely advertises products, sales, or says payment in non-transactional content.",
    "Travel": "flights, hotels, Airbnb, trip bookings, itineraries, ride share, travel changes/cancellations. Reject travel ads/newsletters without an actual booking/trip for Tony.",
    "Security": "security alerts, login/sign-in alerts, password/2FA/verification/account-lock notifications. Reject promotional/privacy newsletters and routine product updates.",
    "Finance": "banking, credit cards, investment accounts, tax, insurance, financial statements, transfers, bills/payments. Reject retail promos and unrelated newsletters.",
    "Recruiting": "true recruiting/job/career-opportunity outreach to Tony: recruiter/hiring-manager messages, interview/follow-up, specific roles, compensation/role pitches, referrals. Reject marketing/promotions/newsletters/events/open houses/restaurants/USPS digests/school-family updates/generic articles even if they say join us, hiring, opportunity, or role in another context.",
    "Ops/Infrastructure": "infrastructure/system/service alerts for Tony's self-hosted systems/accounts and developer automation: Synology, Cloudflare, n8n, Bitwarden, uptime, cron/container/task scheduler, domains/certificates, GitHub Actions workflow failures/cancellations, service failures/recoveries. Reject product newsletters/webinars and normal GitHub comment notifications that are not failures.",
    "ADU": "122 Walnut ADU project: Menlo Park permit, BLD2025-01110, J&P Design, geotech, plan review, ADU contractor/design/resubmittal. Reject general real-estate listings, home purchase ads, USPS digests, unrelated home/property emails.",
    "Home": "non-ADU home/property operations: utilities, PG&E, Recology, property tax, home insurance, mortgage, repairs/maintenance for main home. Reject ADU permit/design threads and real-estate marketing/listings.",
    "Read Later": "newsletters, digests, media, long-form articles, events/webinars/livestreams, non-urgent product/model/API announcements, and other non-urgent content worth reading later. Reject transactional receipts, security alerts, family/school action items, ADU/Home operational mail, and urgent/action-required mail.",
    "Action Needed": "messages that require Tony to do something soon: sign, submit, pay, verify, schedule, approve, respond, review an attached/updated document, move/act on a vehicle/charging spot, deadline/final notice, failed payment, account locked/security action. Reject pure notifications, FYI, marketing, completed/success notices, and generic events/newsletters.",
}

PRODUCTION_LABELS = list(LABEL_DEFINITIONS.keys())


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


def run_cmd(cmd: list[str], timeout: int = 180) -> str:
    env = os.environ.copy()
    env["PATH"] = "/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:" + env.get("PATH", "")
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
    out = proc.stdout or ""
    err = proc.stderr or ""
    if proc.returncode != 0:
        raise RuntimeError(redact(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{out}\n{err}")[:2000])
    return out


def run_gws(args: list[str], timeout: int = 180) -> Any:
    return decode_jsonish(run_cmd([GWS, *args], timeout=timeout))


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"labeled": {}}
    try:
        data = json.loads(STATE_PATH.read_text())
        return data if isinstance(data, dict) else {"labeled": {}}
    except Exception:
        return {"labeled": {}}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))


def get_labels() -> dict[str, str]:
    data = run_gws(["gmail", "users", "labels", "list", "--params", '{"userId":"me"}', "--format", "json"])
    labels = data.get("labels", []) if isinstance(data, dict) else data or []
    return {label["name"]: label["id"] for label in labels if "name" in label and "id" in label}


def ensure_label(name: str, labels: dict[str, str]) -> tuple[str, bool]:
    if name in labels:
        return labels[name], False
    data = run_gws([
        "gmail", "users", "labels", "create",
        "--params", '{"userId":"me"}',
        "--json", json.dumps({"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}),
        "--format", "json",
    ])
    label_id = data.get("id") if isinstance(data, dict) else None
    if not label_id:
        labels = get_labels()
        label_id = labels.get(name)
    if not label_id:
        raise RuntimeError(f"created label {name!r} but could not resolve id")
    labels[name] = label_id
    return label_id, True


def list_message_ids(query: str, max_results: int) -> list[str]:
    data = run_gws([
        "gmail", "users", "messages", "list",
        "--params", json.dumps({"userId": "me", "q": query, "maxResults": max_results}),
        "--format", "json",
    ])
    msgs = data.get("messages", []) if isinstance(data, dict) else []
    # Gmail returns newest first. Keep that order while deduping.
    seen: set[str] = set()
    ids: list[str] = []
    for msg in msgs:
        mid = msg.get("id") if isinstance(msg, dict) else None
        if mid and mid not in seen:
            ids.append(mid)
            seen.add(mid)
    return ids


def batch_add_label(ids: list[str], label_id: str) -> int:
    applied = 0
    for idx in range(0, len(ids), 100):
        chunk = ids[idx:idx + 100]
        if not chunk:
            continue
        run_gws([
            "gmail", "users", "messages", "batchModify",
            "--params", '{"userId":"me"}',
            "--json", json.dumps({"ids": chunk, "addLabelIds": [label_id]}),
            "--format", "json",
        ])
        applied += len(chunk)
        time.sleep(0.2)
    return applied


def read_message_brief(mid: str) -> dict[str, Any]:
    data = run_gws([
        "gmail", "users", "messages", "get",
        "--params", json.dumps({
            "userId": "me",
            "id": mid,
            "format": "metadata",
            "metadataHeaders": ["From", "Subject", "Date", "To", "Cc"],
        }),
        "--format", "json",
    ])
    headers = {h.get("name", "").lower(): h.get("value", "") for h in data.get("payload", {}).get("headers", [])}
    return {
        "id": mid,
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": data.get("snippet", ""),
        "gmail_label_ids": data.get("labelIds", []),
    }


def llm_json(prompt: str) -> Any:
    out = run_cmd([
        LLM_CLI, "-p", prompt, "--no-color", "--no-custom-instructions",
        "--deny-tool=shell", "--deny-tool=write", "--deny-tool=read",
        "--deny-tool=edit", "--deny-tool=create", "--deny-tool=bash",
        "--deny-tool=write_bash", "--deny-tool=read_bash",
        "--disable-builtin-mcps",
    ], timeout=90)
    return decode_jsonish(out)


def prune_classified_cache(state: dict[str, Any]) -> dict[str, Any]:
    cache = state.setdefault("classified_recent", {})
    if not isinstance(cache, dict):
        cache = {}
        state["classified_recent"] = cache
    cutoff = int(time.time()) - CLASSIFIED_CACHE_SECONDS
    for mid, item in list(cache.items()):
        if not isinstance(item, dict) or item.get("version") != CLASSIFIER_VERSION or int(item.get("ts", 0) or 0) < cutoff:
            cache.pop(mid, None)
    if len(cache) > 5000:
        newest = sorted(cache.items(), key=lambda kv: int(kv[1].get("ts", 0)) if isinstance(kv[1], dict) else 0)[-5000:]
        cache.clear()
        cache.update(dict(newest))
    return cache


def select_ids_to_review(candidate_ids: list[str], classified_cache: dict[str, Any], max_review: int) -> list[str]:
    """Newest-first uncached candidate IDs, bounded per run for predictable latency."""
    if max_review <= 0:
        return []
    return [mid for mid in candidate_ids if mid not in classified_cache][:max_review]


def classify_messages(messages: list[dict[str, Any]], batch_size: int) -> tuple[dict[str, list[str]], dict[str, int]]:
    labels_by_id: dict[str, list[str]] = {}
    stats = {"model_batches": 0, "model_errors": 0, "model_reviewed": 0}
    allowed = set(PRODUCTION_LABELS)
    label_doc = "\n".join(f"- {label}: {definition}" for label, definition in LABEL_DEFINITIONS.items())

    for idx in range(0, len(messages), batch_size):
        chunk = messages[idx:idx + batch_size]
        payload = [
            {k: m[k] for k in ["id", "from", "to", "cc", "subject", "date", "snippet"]}
            for m in chunk
        ]
        prompt = f"""
Classify each Gmail message for Tony into zero or more production labels.

Allowed labels and definitions:
{label_doc}

Return ONLY valid JSON in this shape:
{{"decisions":[{{"id":"...","labels":["Label A"],"reason":"short"}}]}}

Rules:
- Consider EVERY allowed label for EVERY message.
- Use zero labels when no definition clearly fits.
- Multi-label is allowed when clearly warranted, e.g. Family + Action Needed.
- Be conservative. If uncertain, leave that label out.
- Use only metadata/snippet; do not assume hidden content.
- Label-only maintenance: do not suggest archive/delete/read/reply/send actions.

Messages:
{json.dumps(payload, ensure_ascii=False)}
""".strip()
        try:
            data = retry_call(lambda: llm_json(prompt), attempts=2, base_delay=2)
            decisions = data.get("decisions", []) if isinstance(data, dict) else []
            for decision in decisions:
                if not isinstance(decision, dict):
                    continue
                mid = decision.get("id")
                raw_labels = decision.get("labels", [])
                if not isinstance(mid, str) or not isinstance(raw_labels, list):
                    continue
                labels = sorted({label for label in raw_labels if isinstance(label, str) and label in allowed})
                labels_by_id[mid] = labels
            stats["model_batches"] += 1
            stats["model_reviewed"] += len(chunk)
        except Exception:
            # Fail closed for this batch. Nothing gets labeled or cached for these messages.
            stats["model_errors"] += 1
    return labels_by_id, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Label recent Gmail using model-based multi-label classification.")
    parser.add_argument("--dry-run", action="store_true", help="classify but do not apply labels or update cache")
    parser.add_argument("--max-review", type=int, default=MAX_REVIEW_PER_RUN, help="maximum uncached recent messages to model-classify this run")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="messages per model classification batch")
    args = parser.parse_args()

    if not Path(GWS).exists():
        print(json.dumps({"status": "error", "error": f"gws not found at {GWS}"}))
        return 1
    if not Path(LLM_CLI).exists():
        print(json.dumps({"status": "error", "error": f"LLM CLI not found at {LLM_CLI}"}))
        return 1

    state = load_state()
    labeled_state = state.setdefault("labeled", {})
    classified_cache = prune_classified_cache(state)

    labels = get_labels()
    created: list[str] = []
    label_ids: dict[str, str] = {}
    for label in PRODUCTION_LABELS:
        label_id, was_created = ensure_label(label, labels)
        label_ids[label] = label_id
        if was_created:
            created.append(label)

    candidate_ids = retry_call(lambda: list_message_ids(SCAN_QUERY, SCAN_MAX))
    ids_to_review = select_ids_to_review(candidate_ids, classified_cache, max(0, args.max_review))
    briefs = [retry_call(lambda mid=mid: read_message_brief(mid), attempts=2, base_delay=1) for mid in ids_to_review]

    labels_by_id, model_stats = classify_messages(briefs, max(1, args.batch_size)) if briefs else ({}, {"model_batches": 0, "model_errors": 0, "model_reviewed": 0})

    apply_by_label: dict[str, list[str]] = {label: [] for label in PRODUCTION_LABELS}
    for mid, msg_labels in labels_by_id.items():
        for label in msg_labels:
            apply_by_label[label].append(mid)

    summary: list[dict[str, Any]] = []
    now = int(time.time())
    for label in PRODUCTION_LABELS:
        seen_for_label = set(labeled_state.setdefault(label, []))
        ids = sorted(set(apply_by_label.get(label, [])))
        new_ids = [mid for mid in ids if mid not in seen_for_label]
        applied = 0 if args.dry_run else (batch_add_label(new_ids, label_ids[label]) if new_ids else 0)
        if not args.dry_run:
            seen_for_label.update(new_ids)
            labeled_state[label] = sorted(seen_for_label)[-2000:]
        summary.append({"label": label, "model_selected": len(ids), "new_labeled": applied})

    if not args.dry_run:
        for mid in labels_by_id:
            classified_cache[mid] = {"ts": now, "version": CLASSIFIER_VERSION, "labels": labels_by_id.get(mid, [])}
        state["last_run_epoch"] = now
        state["last_mode"] = "recent-all-mail-multilabel-model"
        save_state(state)

    # Detect catastrophic LLM failure: review was attempted but every batch errored
    model_total_batches = model_stats.get("model_batches", 0)
    model_errors = model_stats.get("model_errors", 0)
    review_attempted = len(ids_to_review) > 0
    all_batches_failed = review_attempted and model_total_batches == 0 and model_errors > 0
    status = "error" if all_batches_failed else "success"
    result = {
        "status": status,
        "mode": "recent-all-mail-multilabel-model",
        "scan_query": SCAN_QUERY,
        "scan_max": SCAN_MAX,
        "max_review_per_run": max(0, args.max_review),
        "batch_size": max(1, args.batch_size),
        "candidate_count": len(candidate_ids),
        "skipped_cached": len(candidate_ids) - len(ids_to_review),
        "reviewed_count": len(ids_to_review),
        "created_labels": created,
        "model": model_stats,
        "rules": summary,
        "dry_run": args.dry_run,
        "safety": "no archive/delete/mark-read/send/reply/forward",
    }
    if all_batches_failed:
        result["error"] = "All LLM classification batches failed"
    print(json.dumps(result, ensure_ascii=False))
    return 1 if all_batches_failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "error": redact(str(exc))}, ensure_ascii=False))
        raise
