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
    proc = subprocess.run(["bash", "-lic", cmd], cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, env=env)
    out = redact((proc.stdout or "") + ("\nSTDERR:\n" + proc.stderr if proc.stderr else ""))
    payload = parse_jsonish(out)
    return {
        "status": "success" if proc.returncode == 0 else "error",
        "exit_code": proc.returncode,
        "json": payload,
        "tail": out[-2000:],
    }


def run_python(script_name: str, *, cwd: Path = COLLECTORS, timeout: int = 600) -> dict[str, Any]:
    return run_cmd(f"python3 {script_name}", cwd=cwd, timeout=timeout)


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
    }

    # Email-butler maintenance layer.
    labels = run_cmd(str(LABEL_SCRIPT), timeout=600)
    result["labels"] = labels.get("json") if isinstance(labels.get("json"), dict) else labels
    if labels["status"] != "success" or (isinstance(labels.get("json"), dict) and labels["json"].get("status") != "success"):
        result["status"] = "error"

    if not args.skip_action:
        action = run_cmd(str(ACTION_SCRIPT), timeout=600)
        result["action_queue"] = action.get("json") if isinstance(action.get("json"), dict) else action
        if action["status"] != "success" or (isinstance(action.get("json"), dict) and action["json"].get("status") != "success"):
            result["status"] = "error"
    else:
        result["action_queue"] = {"status": "skipped"}

    if args.force_archive or now.hour == 19:
        archive = run_cmd(str(ARCHIVE_SCRIPT), timeout=600)
        result["archive"] = archive.get("json") if isinstance(archive.get("json"), dict) else archive
        result["ran_archive"] = True
        if archive["status"] != "success" or (isinstance(archive.get("json"), dict) and archive["json"].get("status") != "success"):
            result["status"] = "error"
    else:
        result["archive"] = {"status": "skipped"}

    # Gmail + Calendar knowledge sync layer.
    if should_sync:
        sync: dict[str, Any] = {}
        steps = [
            ("collect_gmail", lambda: run_python("collect_gmail.py", timeout=600)),
            ("collect_calendar", lambda: run_python("collect_calendar.py", timeout=600)),
            ("stage_gmail", lambda: run_python("stage_gmail_digest_import.py", timeout=300)),
            ("import_gmail", lambda: run_cmd("source ~/.bashrc >/dev/null 2>&1; gbrain import /home/tonyxu/brain/state/gmail_digest_import_staging --no-embed --json", timeout=600)),
            ("import_calendar", lambda: run_cmd("source ~/.bashrc >/dev/null 2>&1; gbrain import /home/tonyxu/brain/sources/calendar/digests --no-embed --json", timeout=600)),
        ]
        for name, fn in steps:
            started = time.time()
            try:
                step = fn()
            except subprocess.TimeoutExpired as exc:
                step = {"status": "error", "exit_code": 124, "tail": redact(str(exc))[-1000:], "json": None}
            except Exception as exc:
                step = {"status": "error", "exit_code": 1, "tail": redact(str(exc))[-1000:], "json": None}
            step["duration_s"] = round(time.time() - started, 1)
            if name.startswith("import_"):
                sync[name] = summarize_import(step)
            else:
                payload = step.get("json")
                sync[name] = payload if isinstance(payload, dict) else {"status": step.get("status"), "exit_code": step.get("exit_code"), "tail": step.get("tail", "")[-500:]}
            # strict success criteria
            current = sync[name]
            failed = step.get("status") != "success"
            if isinstance(current, dict):
                if current.get("status") in ("error", "failed"):
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
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
