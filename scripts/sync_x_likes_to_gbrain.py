#!/usr/bin/env python3
"""Incrementally sync Tony's X/Twitter social activity into gbrain.

Uses Agent Reach/twitter-cli cookie-auth GraphQL, not the official X API.
Writes canonical source files under:
- /home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD
- /home/tonyxu/brain/sources/x-posts/agent-reach-YYYYMMDD
and refreshes gbrain pages plus latest JSONL/CSV aliases.

Cron behavior: quiet on success by default; print a short summary only with --verbose.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

LIKES_BASE_DIR = Path("/home/tonyxu/brain/sources/x-likes")
POSTS_BASE_DIR = Path("/home/tonyxu/brain/sources/x-posts")
USER_ID = "11706742"
SCREEN_NAME = "t0nyxu"
TWITTER_PYTHON = Path("/home/tonyxu/.local/share/uv/tools/twitter-cli/bin/python")
MAX_PAGES = 20
PAGE_COUNT = 40
SLEEP_BASE_SECONDS = 2.5


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def ensure_twitter_cli_import_path() -> None:
    # Run from /tmp (or any non-repo dir) to avoid local module shadowing.
    os.chdir("/tmp")


def graphql_imports():
    tool_root = TWITTER_PYTHON.parent.parent
    candidates = sorted((tool_root / "lib").glob("python*/site-packages"), reverse=True)
    for site_packages in candidates:
        if (site_packages / "twitter_cli").exists():
            sys.path.insert(0, str(site_packages))
            break
    else:
        raise RuntimeError(f"twitter_cli package not found under {tool_root / 'lib'}")

    from twitter_cli.auth import get_cookies
    from twitter_cli.client import TwitterClient
    from twitter_cli.config import load_config
    from twitter_cli.graphql import FEATURES
    from twitter_cli.parser import _deep_get, parse_timeline_response
    from twitter_cli.serialization import tweets_to_data

    return get_cookies, TwitterClient, load_config, FEATURES, _deep_get, parse_timeline_response, tweets_to_data


def get_user_timeline_instructions(data: dict[str, Any], deep_get) -> Any:
    return (
        deep_get(data, "data", "user", "result", "timeline", "timeline", "instructions")
        or deep_get(data, "data", "user", "result", "timeline_v2", "timeline", "instructions")
    )


def get_likes_instructions(data: dict[str, Any], deep_get) -> Any:
    return get_user_timeline_instructions(data, deep_get)


def extract_reply_contexts(raw: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Extract reply/conversation metadata from raw GraphQL tweet payloads.

    twitter-cli's Tweet model currently serializes posts/reposts/quotes but drops
    the legacy `in_reply_to_*` fields. UserTweets does expose them in raw GraphQL;
    preserve those fields so Tony-authored replies can be classified separately
    from ordinary posts in source exports and daily activity ledgers.
    """
    contexts: dict[str, dict[str, str]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            legacy = node.get("legacy") if isinstance(node.get("legacy"), dict) else None
            if legacy:
                tweet_id = str(node.get("rest_id") or legacy.get("id_str") or "")
                ctx: dict[str, str] = {}
                mapping = {
                    "conversation_id_str": "conversationId",
                    "in_reply_to_status_id_str": "inReplyToStatusId",
                    "in_reply_to_user_id_str": "inReplyToUserId",
                    "in_reply_to_screen_name": "inReplyToScreenName",
                }
                for raw_key, out_key in mapping.items():
                    value = legacy.get(raw_key)
                    if value:
                        ctx[out_key] = str(value)
                if tweet_id and any(k.startswith("inReplyTo") for k in ctx):
                    contexts[tweet_id] = ctx
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(raw)
    return contexts


def load_existing_ids(base_dir: Path, pattern: str) -> set[str]:
    ids: set[str] = set()
    for jsonl in base_dir.glob(pattern):
        with jsonl.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = rec.get("id")
                if tid:
                    ids.add(str(tid))
    return ids


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def parse_dt(rec: dict[str, Any]) -> datetime:
    iso = rec.get("createdAtISO") or rec.get("created_at")
    if iso:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    created = rec.get("createdAt")
    if created:
        return datetime.strptime(str(created), "%a %b %d %H:%M:%S %z %Y")
    return datetime.fromtimestamp(0, tz=timezone.utc)


def normalize_record(rec: dict[str, Any], activity_type: str) -> dict[str, Any]:
    rec = dict(rec)
    rec["text"] = normalize_text(rec.get("text") or "")
    rec["activityType"] = activity_type
    if activity_type == "timeline":
        is_reply = bool(rec.get("inReplyToStatusId") or rec.get("inReplyToUserId") or rec.get("inReplyToScreenName"))
        rec["kind"] = "repost" if rec.get("isRetweet") else ("reply" if is_reply else "post")
    elif activity_type == "like":
        rec["kind"] = "like"
    return rec


def author_screen(rec: dict[str, Any]) -> str:
    author = rec.get("author") or {}
    return author.get("screenName") or author.get("username") or "unknown"


def is_tony_timeline_record(rec: dict[str, Any]) -> bool:
    """Keep Tony-authored posts/replies plus explicit reposts by Tony.

    UserTweetsAndReplies raw GraphQL includes surrounding conversation tweets.
    Those tweets are useful context but are not Tony's own timeline activity;
    exporting them as `X posts` made reply targets look like Tony's posts.
    """
    kind = rec.get("kind") or "post"
    return author_screen(rec) == SCREEN_NAME or (kind == "repost" and rec.get("retweetedBy") == SCREEN_NAME)


def build_client(max_pages: int):
    get_cookies, TwitterClient, load_config, FEATURES, deep_get, parse_timeline_response, tweets_to_data = graphql_imports()
    cookies = get_cookies()
    rl = dict((load_config() or {}).get("rateLimit") or {})
    rl["maxCount"] = max(5000, max_pages * PAGE_COUNT)
    client = TwitterClient(cookies["auth_token"], cookies["ct0"], rl, cookie_string=cookies.get("cookie_string"))
    return client, FEATURES, deep_get, parse_timeline_response, tweets_to_data


def fetch_incremental(
    *,
    client,
    features: dict[str, Any],
    deep_get,
    parse_timeline_response,
    tweets_to_data,
    out_dir: Path,
    known_ids: set[str],
    max_pages: int,
    full: bool,
    operation_name: str,
    instruction_getter: Callable[[dict[str, Any], Any], Any],
    base_variables: dict[str, Any],
    raw_prefix: str,
    activity_type: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    cursor = None
    fetched_ids: set[str] = set()
    new_records: list[dict[str, Any]] = []
    page_meta: list[dict[str, Any]] = []
    stop_reason = "max_pages"

    for page in range(1, max_pages + 1):
        variables = dict(base_variables)
        variables["count"] = PAGE_COUNT
        if cursor:
            variables["cursor"] = cursor

        raw = client._graphql_get(operation_name, variables, features)
        raw_file = out_dir / f"{raw_prefix}_graphql_page_{page:03d}.json"
        raw_file.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

        tweets, next_cursor = parse_timeline_response(raw, lambda data: instruction_getter(data, deep_get))
        data = tweets_to_data(tweets)
        reply_contexts = extract_reply_contexts(raw) if activity_type == "timeline" else {}
        page_new = 0
        page_duplicates = 0
        hit_known = False

        for rec in data:
            tid = str(rec.get("id") or "")
            if not tid or tid in fetched_ids:
                page_duplicates += 1
                continue
            fetched_ids.add(tid)
            if tid in known_ids:
                page_duplicates += 1
                hit_known = True
                continue
            if tid in reply_contexts:
                rec = dict(rec)
                rec.update(reply_contexts[tid])
            new_records.append(normalize_record(rec, activity_type))
            page_new += 1

        page_meta.append(
            {
                "page": page,
                "tweet_count": len(data),
                "new_count": page_new,
                "duplicate_or_known_count": page_duplicates,
                "hit_known": hit_known,
                "raw_file": str(raw_file),
                "next_cursor": bool(next_cursor),
            }
        )

        if hit_known and not full:
            stop_reason = "caught_up_to_existing_export"
            break
        if not next_cursor or next_cursor == cursor:
            stop_reason = "no_next_cursor"
            break
        cursor = next_cursor
        time.sleep(SLEEP_BASE_SECONDS * random.uniform(0.7, 1.4))

    return new_records, page_meta, stop_reason


def load_all_records(base_dir: Path, pattern: str, new_records: list[dict[str, Any]], activity_type: str) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for jsonl in sorted(base_dir.glob(pattern)):
        with jsonl.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = str(rec.get("id") or "")
                if tid:
                    norm = normalize_record(rec, activity_type)
                    if activity_type == "timeline" and not is_tony_timeline_record(norm):
                        continue
                    by_id.setdefault(tid, norm)
    for rec in new_records:
        tid = str(rec.get("id") or "")
        if tid:
            norm = normalize_record(rec, activity_type)
            if activity_type == "timeline" and not is_tony_timeline_record(norm):
                continue
            by_id[tid] = norm
    records = list(by_id.values())
    records.sort(key=parse_dt, reverse=True)
    return records


def enrich_timeline_records_from_raw(records: list[dict[str, Any]], raw_files: list[Path]) -> list[dict[str, Any]]:
    reply_contexts: dict[str, dict[str, str]] = {}
    for raw_file in raw_files:
        try:
            raw = json.loads(raw_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        reply_contexts.update(extract_reply_contexts(raw))

    enriched: list[dict[str, Any]] = []
    for rec in records:
        tid = str(rec.get("id") or "")
        rec = dict(rec)
        if tid in reply_contexts:
            rec.update(reply_contexts[tid])
        enriched.append(normalize_record(rec, "timeline"))
    enriched.sort(key=parse_dt, reverse=True)
    return enriched


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=True, separators=(",", ":")) + "\n")
    # Validate JSONL line integrity.
    with path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            json.loads(line)


def tweet_url(rec: dict[str, Any]) -> str:
    screen = author_screen(rec)
    tid = rec.get("id")
    return f"https://x.com/{screen}/status/{tid}" if screen != "unknown" else f"https://x.com/i/status/{tid}"


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = ["id", "createdAtISO", "activityType", "kind", "author_screen_name", "author_name", "text", "url", "lang", "conversationId", "inReplyToStatusId", "inReplyToScreenName"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for rec in records:
            author = rec.get("author") or {}
            writer.writerow(
                {
                    "id": rec.get("id"),
                    "createdAtISO": parse_dt(rec).isoformat(),
                    "activityType": rec.get("activityType") or "",
                    "kind": rec.get("kind") or "",
                    "author_screen_name": author_screen(rec),
                    "author_name": author.get("name") or "",
                    "text": rec.get("text") or "",
                    "url": tweet_url(rec),
                    "lang": rec.get("lang") or "",
                    "conversationId": rec.get("conversationId") or "",
                    "inReplyToStatusId": rec.get("inReplyToStatusId") or "",
                    "inReplyToScreenName": rec.get("inReplyToScreenName") or "",
                }
            )


def render_year_pages(md_dir: Path, records: list[dict[str, Any]], raw_path: Path, *, activity_label: str, page_prefix: str) -> list[Path]:
    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        year = str(parse_dt(rec).year)
        by_year[year].append(rec)

    written: list[Path] = []
    for year in sorted(by_year.keys(), reverse=True):
        rows = by_year[year]
        path = md_dir / f"{page_prefix}-{year}.md"
        lines = [
            f"# {activity_label} — {year}",
            "",
            f"_{len(rows)} records from Agent Reach Twitter cookie export._",
            "",
            f"Source: `{raw_path}`",
            "",
        ]
        for rec in rows:
            dt = parse_dt(rec)
            screen = author_screen(rec)
            text = normalize_text(rec.get("text") or "")
            kind = rec.get("kind") or "tweet"
            lines.append(f"- **{dt.date().isoformat()}** · `{kind}` · [@{screen}]({tweet_url(rec)}) — {text}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)
    return written


def write_index(
    path: Path,
    records: list[dict[str, Any]],
    daily_new: int,
    page_meta: list[dict[str, Any]],
    stop_reason: str,
    raw_path: Path,
    jsonl_path: Path,
    csv_path: Path,
    md_dir: Path,
    *,
    title: str,
    source_method: str,
    page_prefix: str,
) -> None:
    by_year = Counter(str(parse_dt(r).year) for r in records)
    by_kind = Counter((r.get("kind") or "unknown") for r in records)
    langs = Counter((r.get("lang") or "unknown") for r in records)
    authors = Counter(author_screen(r) for r in records)
    if records:
        oldest = parse_dt(records[-1]).isoformat()
        newest = parse_dt(records[0]).isoformat()
    else:
        oldest = newest = "n/a"

    today_title = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# {title} — Agent Reach Export {today_title}",
        "",
        f"- Method: {source_method}",
        f"- Account: `@{SCREEN_NAME}`",
        f"- Unique records in cumulative export: {len(records)}",
        f"- Newly captured in this run: {daily_new}",
        f"- Time range covered: {oldest} → {newest}",
        f"- Raw paginated GraphQL pages this run: {len(page_meta)}",
        f"- Stop reason: `{stop_reason}`",
        f"- Canonical raw export: `{raw_path}`",
        f"- JSONL: `{jsonl_path}`",
        f"- CSV: `{csv_path}`",
        f"- Markdown pages: `{md_dir}/{page_prefix}-*.md`",
        "",
        "## By kind",
        "",
    ]
    for kind, count in sorted(by_kind.items()):
        lines.append(f"- {kind}: {count}")
    lines += ["", "## By year", ""]
    for year, count in sorted(by_year.items(), reverse=True):
        lines.append(f"- {year}: {count}")
    lines += ["", "## Top languages", ""]
    for lang, count in langs.most_common(10):
        lines.append(f"- {lang}: {count}")
    lines += ["", "## Top authors", ""]
    for author, count in authors.most_common(12):
        lines.append(f"- @{author}: {count}")
    lines += ["", "## Caveat", ""]
    lines.append(
        "This export depends on what X web GraphQL exposes from the current cookie session. "
        "Deleted/private/unavailable tweets can disappear from the visible timelines."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_gbrain_put(slug: str, file_path: Path) -> subprocess.CompletedProcess[str]:
    cmd = f"set -euo pipefail; gbrain put {sh_quote(slug)} < {sh_quote(str(file_path))}"
    return subprocess.run(["bash", "-lc", cmd], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)


def sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def import_to_gbrain(index_path: Path, year_paths: list[Path], date_tag: str, *, slug_prefix: str) -> tuple[list[str], list[str]]:
    if os.getenv("SKIP_GBRAIN_IMPORT") == "1":
        return [], []
    ok: list[str] = []
    errors: list[str] = []
    targets = [(f"{slug_prefix}-agent-reach-export-{date_tag}", index_path)]
    targets += [(p.stem, p) for p in year_paths]
    for slug, path in targets:
        proc = run_gbrain_put(slug, path)
        if proc.returncode == 0:
            ok.append(slug)
        else:
            errors.append(f"{slug}: exit {proc.returncode}: {(proc.stderr or proc.stdout)[-1000:]}")
    return ok, errors


def copy_latest(jsonl_path: Path, csv_path: Path, latest_dir: Path, jsonl_name: str, csv_name: str) -> None:
    latest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(jsonl_path, latest_dir / jsonl_name)
    shutil.copy2(csv_path, latest_dir / csv_name)


def sync_likes(client, features, deep_get, parse_timeline_response, tweets_to_data, today: str, args) -> tuple[int, int, int, str, int]:
    out_dir = LIKES_BASE_DIR / f"agent-reach-{today}"
    md_dir = out_dir / "md"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    known_ids = load_existing_ids(LIKES_BASE_DIR, "agent-reach-*/twitter_likes_agent_reach_*.jsonl")
    new_records, page_meta, stop_reason = fetch_incremental(
        client=client,
        features=features,
        deep_get=deep_get,
        parse_timeline_response=parse_timeline_response,
        tweets_to_data=tweets_to_data,
        out_dir=out_dir,
        known_ids=known_ids,
        max_pages=args.max_pages,
        full=args.full,
        operation_name="Likes",
        instruction_getter=get_likes_instructions,
        base_variables={
            "userId": USER_ID,
            "includePromotedContent": False,
            "withClientEventToken": False,
            "withBirdwatchNotes": False,
            "withVoice": True,
        },
        raw_prefix="likes",
        activity_type="like",
    )
    all_records = load_all_records(LIKES_BASE_DIR, "agent-reach-*/twitter_likes_agent_reach_*.jsonl", new_records, "like")

    raw_path = out_dir / f"twitter_likes_agent_reach_paginated_{today}.raw.json"
    jsonl_path = out_dir / f"twitter_likes_agent_reach_{today}.jsonl"
    csv_path = out_dir / f"twitter_likes_agent_reach_{today}.csv"
    index_path = out_dir / "index.md"

    raw_payload = {
        "ok": True,
        "source": "agent-reach twitter-cli GraphQL Likes incremental sync",
        "account": {"id": USER_ID, "screenName": SCREEN_NAME},
        "run_date": today,
        "new_count": len(new_records),
        "cumulative_count": len(all_records),
        "stop_reason": stop_reason,
        "pages": page_meta,
        "data": all_records,
    }
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(jsonl_path, all_records)
    write_csv(csv_path, all_records)
    copy_latest(jsonl_path, csv_path, LIKES_BASE_DIR / "latest", "twitter_likes_agent_reach_latest.jsonl", "twitter_likes_agent_reach_latest.csv")
    year_paths = render_year_pages(md_dir, all_records, raw_path, activity_label="X/Twitter Likes", page_prefix="x-likes")
    write_index(
        index_path,
        all_records,
        len(new_records),
        page_meta,
        stop_reason,
        raw_path,
        jsonl_path,
        csv_path,
        md_dir,
        title="X/Twitter Likes",
        source_method="Agent Reach `twitter` CLI / cookie-auth GraphQL Likes pagination",
        page_prefix="x-likes",
    )

    imported, errors = import_to_gbrain(index_path, year_paths, today, slug_prefix="x-likes")
    if errors:
        raise RuntimeError("gbrain import failed for X likes: " + "; ".join(errors))
    return len(new_records), len(all_records), len(page_meta), stop_reason, len(imported)


def sync_posts(client, features, deep_get, parse_timeline_response, tweets_to_data, today: str, args) -> tuple[int, int, int, str, int]:
    out_dir = POSTS_BASE_DIR / f"agent-reach-{today}"
    md_dir = out_dir / "md"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    known_ids = load_existing_ids(POSTS_BASE_DIR, "agent-reach-*/twitter_posts_agent_reach_*.jsonl")
    timeline_variables = {
        "userId": USER_ID,
        "includePromotedContent": False,
        "latestControlAvailable": True,
        "requestContext": "launch",
        "withQuickPromoteEligibilityTweetFields": True,
        "withVoice": True,
        "withV2Timeline": True,
    }

    # UserTweets exposes posts + reposts but usually omits authored replies.
    # UserTweetsAndReplies exposes authored replies but can omit reposts. Fetch
    # both and merge by tweet ID so historical replies and reposts are retained.
    new_posts, post_page_meta, post_stop = fetch_incremental(
        client=client,
        features=features,
        deep_get=deep_get,
        parse_timeline_response=parse_timeline_response,
        tweets_to_data=tweets_to_data,
        out_dir=out_dir,
        known_ids=known_ids,
        max_pages=args.max_pages,
        full=args.full,
        operation_name="UserTweets",
        instruction_getter=get_user_timeline_instructions,
        base_variables=timeline_variables,
        raw_prefix="posts",
        activity_type="timeline",
    )
    known_plus_posts = set(known_ids)
    known_plus_posts.update(str(r.get("id")) for r in new_posts if r.get("id"))
    new_replies, reply_page_meta, reply_stop = fetch_incremental(
        client=client,
        features=features,
        deep_get=deep_get,
        parse_timeline_response=parse_timeline_response,
        tweets_to_data=tweets_to_data,
        out_dir=out_dir,
        known_ids=known_plus_posts,
        max_pages=args.max_pages,
        full=args.full,
        operation_name="UserTweetsAndReplies",
        instruction_getter=get_user_timeline_instructions,
        base_variables=timeline_variables,
        raw_prefix="replies",
        activity_type="timeline",
    )
    new_records = new_posts + new_replies
    page_meta = post_page_meta + reply_page_meta
    stop_reason = f"UserTweets={post_stop}; UserTweetsAndReplies={reply_stop}"
    all_records = load_all_records(POSTS_BASE_DIR, "agent-reach-*/twitter_posts_agent_reach_*.jsonl", new_records, "timeline")
    raw_files = sorted(POSTS_BASE_DIR.glob("agent-reach-*/posts_graphql_page_*.json")) + sorted(POSTS_BASE_DIR.glob("agent-reach-*/replies_graphql_page_*.json"))
    all_records = enrich_timeline_records_from_raw(all_records, raw_files)

    raw_path = out_dir / f"twitter_posts_agent_reach_paginated_{today}.raw.json"
    jsonl_path = out_dir / f"twitter_posts_agent_reach_{today}.jsonl"
    csv_path = out_dir / f"twitter_posts_agent_reach_{today}.csv"
    index_path = out_dir / "index.md"

    raw_payload = {
        "ok": True,
        "source": "agent-reach twitter-cli GraphQL UserTweets incremental sync",
        "account": {"id": USER_ID, "screenName": SCREEN_NAME},
        "run_date": today,
        "new_count": len(new_records),
        "cumulative_count": len(all_records),
        "stop_reason": stop_reason,
        "pages": page_meta,
        "data": all_records,
    }
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(jsonl_path, all_records)
    write_csv(csv_path, all_records)
    copy_latest(jsonl_path, csv_path, POSTS_BASE_DIR / "latest", "twitter_posts_agent_reach_latest.jsonl", "twitter_posts_agent_reach_latest.csv")
    year_paths = render_year_pages(md_dir, all_records, raw_path, activity_label="X/Twitter Posts, Replies, and Reposts", page_prefix="x-posts")
    write_index(
        index_path,
        all_records,
        len(new_records),
        page_meta,
        stop_reason,
        raw_path,
        jsonl_path,
        csv_path,
        md_dir,
        title="X/Twitter Posts, Replies, and Reposts",
        source_method="Agent Reach `twitter` CLI / cookie-auth GraphQL UserTweets pagination",
        page_prefix="x-posts",
    )

    imported, errors = import_to_gbrain(index_path, year_paths, today, slug_prefix="x-posts")
    if errors:
        raise RuntimeError("gbrain import failed for X posts: " + "; ".join(errors))
    return len(new_records), len(all_records), len(page_meta), stop_reason, len(imported)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES)
    parser.add_argument("--full", action="store_true", help="Do not stop when reaching already-known tweets")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--likes-only", action="store_true", help="Sync only X likes")
    parser.add_argument("--posts-only", action="store_true", help="Sync only X posts/replies/reposts")
    args = parser.parse_args()
    if args.likes_only and args.posts_only:
        eprint("ERROR: --likes-only and --posts-only are mutually exclusive")
        return 2

    ensure_twitter_cli_import_path()
    today = datetime.now().strftime("%Y%m%d")
    client, features, deep_get, parse_timeline_response, tweets_to_data = build_client(args.max_pages)

    summaries: list[str] = []
    try:
        if not args.posts_only:
            new_count, total_count, pages, stop, imported = sync_likes(client, features, deep_get, parse_timeline_response, tweets_to_data, today, args)
            summaries.append(f"likes new={new_count} cumulative={total_count} pages={pages} stop={stop} imported={imported}")
        if not args.likes_only:
            new_count, total_count, pages, stop, imported = sync_posts(client, features, deep_get, parse_timeline_response, tweets_to_data, today, args)
            summaries.append(f"posts/replies/reposts new={new_count} cumulative={total_count} pages={pages} stop={stop} imported={imported}")
    except Exception as exc:
        eprint(f"ERROR: {type(exc).__name__}: {exc}")
        return 2

    if args.verbose:
        print("Synced X activity: " + "; ".join(summaries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
