#!/usr/bin/env python3
"""Low-risk Gmail auto-archive for Tony's email-butler.

Archives only very conservative categories:
- Gmail category promotions/social/forums older than 7 days
- label:Recruiting older than 7 days

Never deletes, marks read, sends, replies, or forwards.
Outputs JSON summary with counts only, no message IDs.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

GWS = "/home/linuxbrew/.linuxbrew/bin/gws"
STATE_PATH = Path.home() / ".local" / "state" / "copilot-home-assistant" / "email_butler_low_risk_archive.json"
REDACT_RE = re.compile(r"(ya29\.[A-Za-z0-9._-]+|Bearer\s+[^\s]+|gh[pousr]_[A-Za-z0-9_]+|[A-Za-z0-9_=-]{120,})")

PROTECT = '-label:"Action Needed" -label:Family -label:Security -label:ADU -label:Home -label:"Home/ADU"'

RULES = [
    {"name": "promotions_older_7d", "query": f"in:inbox category:promotions older_than:7d {PROTECT}", "max": 100},
    {"name": "social_older_7d", "query": f"in:inbox category:social older_than:7d {PROTECT}", "max": 100},
    {"name": "forums_older_7d", "query": f"in:inbox category:forums older_than:7d {PROTECT}", "max": 100},
    {"name": "recruiting_older_7d", "query": f"in:inbox label:Recruiting older_than:7d {PROTECT}", "max": 100},
    {"name": "read_later_older_14d", "query": f"in:inbox label:\"Read Later\" older_than:14d {PROTECT}", "max": 100},
    {"name": "ops_success_noise_older_3d", "query": 'in:inbox label:"Ops/Infrastructure" older_than:3d ("completed a scheduled task" OR "success" OR "succeeded" OR "has recovered" OR "resolved") -label:"Action Needed" -label:Security', "max": 100},
    {"name": "shopping_logistics_older_14d", "query": f"in:inbox older_than:14d (from:auto-confirm@amazon.com OR from:shipment-tracking@amazon.com OR from:order-update@amazon.com OR from:uspsinformeddelivery@email.informeddelivery.usps.com OR from:mcinfo@ups.com) {PROTECT}", "max": 100},
]


def redact(text: str) -> str:
    return REDACT_RE.sub("[REDACTED]", text)


def decode_jsonish(output: str) -> Any:
    starts = [i for i in (output.find("{"), output.find("[")) if i >= 0]
    if not starts:
        return None
    text = output[min(starts):].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        marker = text.find("\nSTDERR:")
        if marker >= 0:
            return json.loads(text[:marker].strip())
        raise


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


def run_gws(args: list[str]) -> Any:
    env = os.environ.copy()
    env["PATH"] = "/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:" + env.get("PATH", "")
    proc = subprocess.run([GWS, *args], text=True, capture_output=True, timeout=120, env=env)
    out = proc.stdout or ""
    err = proc.stderr or ""
    if proc.returncode != 0:
        raise RuntimeError(redact(f"gws failed ({proc.returncode}): {' '.join([GWS, *args])}\n{out}\n{err}")[:2000])
    return decode_jsonish(out)


def list_ids(query: str, max_results: int) -> list[str]:
    data = run_gws([
        "gmail", "users", "messages", "list",
        "--params", json.dumps({"userId": "me", "q": query, "maxResults": max_results}),
        "--format", "json",
    ])
    msgs = data.get("messages", []) if isinstance(data, dict) else []
    return sorted({m["id"] for m in msgs if isinstance(m, dict) and m.get("id")})


def batch_archive(ids: list[str]) -> int:
    total = 0
    for idx in range(0, len(ids), 100):
        chunk = ids[idx:idx + 100]
        if not chunk:
            continue
        run_gws([
            "gmail", "users", "messages", "batchModify",
            "--params", '{"userId":"me"}',
            "--json", json.dumps({"ids": chunk, "removeLabelIds": ["INBOX"]}),
            "--format", "json",
        ])
        total += len(chunk)
        time.sleep(0.2)
    return total


def main() -> int:
    if not Path(GWS).exists():
        print(json.dumps({"status": "error", "error": f"gws not found at {GWS}"}))
        return 1
    summary = []
    total = 0
    for rule in RULES:
        ids = retry_call(lambda r=rule: list_ids(r["query"], int(r["max"])))
        archived = batch_archive(ids) if ids else 0
        total += archived
        summary.append({"rule": rule["name"], "matched": len(ids), "archived": archived})
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"last_run_epoch": int(time.time()), "rules": summary}, indent=2, sort_keys=True))
    print(json.dumps({"status": "success", "mode": "archive-only-low-risk", "total_archived": total, "rules": summary, "safety": "no delete/mark-read/send/reply/forward"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "error": redact(str(exc))}, ensure_ascii=False))
        raise
