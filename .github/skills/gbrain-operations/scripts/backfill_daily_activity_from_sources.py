#!/usr/bin/env python3
"""Backfill brain daily activity notes from source likes/favorites/saves.

Policy:
- Date-shard by content generation date when available, not export date.
- Keep source-specific exports under sources/... as provenance.
- Write deterministic Markdown under daily/activity/YYYY/YYYY-MM-DD.md.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path('/home/tonyxu/brain')
OUT_ROOT = ROOT / 'daily' / 'activity'


def parse_date(value: Any) -> str | None:
    if value in (None, '', 'None'):
        return None
    if isinstance(value, (int, float)):
        # Heuristic: unix seconds or ms.
        ts = float(value)
        if ts > 10_000_000_000:
            ts /= 1000
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        except Exception:
            return None
    s = str(value).strip()
    if not s or s == 'None':
        return None
    # YYYYMMDD
    if re.fullmatch(r'\d{8}', s):
        return f'{s[:4]}-{s[4:6]}-{s[6:8]}'
    # ISO-ish or YYYY-MM-DD HH:MM
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return None


def collection_date_from_path(path: Path) -> str | None:
    text = str(path)
    m = re.search(r'(20\d{2})(\d{2})(\d{2})', text)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m = re.search(r'(20\d{2})-(\d{2})-(\d{2})', text)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return None


def clean(s: Any, limit: int = 260) -> str:
    s = '' if s is None else str(s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.replace('|', '\\|')
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + '…'
    return s


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def add_item(days: dict[str, list[dict[str, Any]]], *, date: str | None, source: str, title: str, url: str = '', author: str = '', text: str = '', date_basis: str, source_file: Path, kind: str = 'like') -> None:
    if not date:
        date = collection_date_from_path(source_file) or 'unknown-date'
        date_basis = 'collection_date_fallback'
    days[date].append({
        'source': source,
        'kind': kind,
        'title': clean(title, 180),
        'author': clean(author, 80),
        'url': clean(url, 220),
        'text': clean(text, 300),
        'date_basis': date_basis,
        'source_file': rel(source_file),
    })


def load_jsonl(path: Path):
    with path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def collect_x(days: dict[str, list[dict[str, Any]]]) -> None:
    path = ROOT / 'sources/x-likes/agent-reach-20260425/twitter_likes_agent_reach_20260425.jsonl'
    if not path.exists():
        return
    seen = set()
    for obj in load_jsonl(path):
        tweet_id = obj.get('id')
        if tweet_id in seen:
            continue
        seen.add(tweet_id)
        author_obj = obj.get('author') if isinstance(obj.get('author'), dict) else {}
        author = author_obj.get('screenName') or author_obj.get('name') or ''
        url = f'https://x.com/{author}/status/{tweet_id}' if author and tweet_id else ''
        date = parse_date(obj.get('createdAtISO') or obj.get('createdAtLocal'))
        add_item(days, date=date, source='X likes', title=obj.get('text') or f'Tweet {tweet_id}', url=url, author=author, text=obj.get('text') or '', date_basis='content_created_at', source_file=path, kind='like')


def collect_youtube(days: dict[str, list[dict[str, Any]]]) -> None:
    path = ROOT / 'sources/youtube-likes/20260425/youtube_liked_all_20260425_170014.jsonl'
    if not path.exists():
        return
    seen = set()
    for obj in load_jsonl(path):
        vid = obj.get('id') or obj.get('url')
        kind = obj.get('kind') or ''
        # Same video can appear once as normal YouTube and once as YouTube Music; keep both signals.
        key = (kind, vid)
        if key in seen:
            continue
        seen.add(key)
        date = parse_date(obj.get('release_timestamp') or obj.get('timestamp') or obj.get('upload_date') or obj.get('published') or obj.get('published_at'))
        basis = 'content_created_at' if date else 'collection_date'
        source = 'YouTube Music likes' if kind == 'music' else 'YouTube likes'
        add_item(days, date=date or collection_date_from_path(path), source=source, title=obj.get('title') or vid or 'YouTube item', url=obj.get('url') or '', author=obj.get('channel') or obj.get('uploader') or '', text=f"kind={kind}", date_basis=basis, source_file=path, kind='like')


def collect_xhs(days: dict[str, list[dict[str, Any]]]) -> None:
    path = ROOT / 'sources/xhs-likes-favorites/20260426/xhs_ui_likes_favorites_20260426015848.jsonl'
    if not path.exists():
        return
    seen = set()
    for obj in load_jsonl(path):
        key = obj.get('url') or obj.get('title') or obj.get('index')
        signal_source = obj.get('source') or ''
        # Same note can be both liked and favorited; keep both activity signals.
        dedupe_key = (signal_source, key)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        date = parse_date(obj.get('created_at') or obj.get('createdAt') or obj.get('published_at') or obj.get('publish_time'))
        basis = 'content_created_at' if date else 'collection_date'
        source = 'Xiaohongshu favorites' if signal_source == 'favorite' else 'Xiaohongshu likes'
        add_item(days, date=date or collection_date_from_path(path), source=source, title=obj.get('title') or 'XHS item', url=obj.get('url') or '', text=obj.get('text') or '', date_basis=basis, source_file=path, kind=signal_source or 'like/favorite')


def collect_maps(days: dict[str, list[dict[str, Any]]]) -> None:
    path = ROOT / 'sources/google-maps-favorite-food/20260426/google_maps_favorite_food_20260426.jsonl'
    if not path.exists():
        return
    seen = set()
    for obj in load_jsonl(path):
        key = obj.get('google_cid') or obj.get('google_place_url') or obj.get('name')
        if key in seen:
            continue
        seen.add(key)
        date = parse_date(obj.get('list_added_at_utc') or obj.get('list_updated_at_utc'))
        add_item(days, date=date, source='Google Maps favorite food', title=obj.get('name') or obj.get('google_place_name') or 'Place', url=obj.get('google_maps_url') or obj.get('google_place_url') or '', text=obj.get('address') or obj.get('display_name_address') or '', date_basis='activity_saved_at', source_file=path, kind='favorite')


def collect_douban(days: dict[str, list[dict[str, Any]]]) -> None:
    path = ROOT / 'sources/douban/20260417/douban_120942873_export.json'
    if not path.exists():
        return
    data = json.load(path.open('r', encoding='utf-8', errors='ignore'))
    seen = set()
    for obj in data if isinstance(data, list) else []:
        key = obj.get('url') or obj.get('title') or obj.get('no')
        if key in seen:
            continue
        seen.add(key)
        date = parse_date(obj.get('added_at'))
        add_item(days, date=date, source='Douban', title=obj.get('title') or 'Douban item', url=obj.get('url') or '', text=f"rating={obj.get('rating') or ''}; year={obj.get('year') or ''}; genres={obj.get('genres') or ''}", date_basis='activity_added_at', source_file=path, kind='saved/rated')


def render_day(date: str, items: list[dict[str, Any]]) -> str:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in sorted(items, key=lambda x: (x['source'], x['title'], x['url'])):
        by_source[item['source']].append(item)
    lines: list[str] = []
    lines.extend([
        '---', 'type: source', f'title: Daily Activity — {date}', f'date: {date}', 'tags:', '  - daily', '  - activity', '  - likes', '---', '', f'# Daily Activity — {date}', '',
        '> Cross-source activity ledger generated from `sources/...`. Date sharding follows content generation date when available, not export date. Items with missing content timestamps are explicitly marked `date_basis: collection_date`.', '', '## Summary',
    ])
    for source, vals in sorted(by_source.items()):
        basis_counts = defaultdict(int)
        for v in vals:
            basis_counts[v['date_basis']] += 1
        basis = ', '.join(f'{k}={v}' for k, v in sorted(basis_counts.items()))
        lines.append(f'- {source}: {len(vals)} ({basis})')
    for source, vals in sorted(by_source.items()):
        lines.extend(['', f'## {source}', ''])
        srcs = sorted(set(v['source_file'] for v in vals))
        lines.append('Source files: ' + ', '.join(f'`{s}`' for s in srcs))
        lines.append('')
        for v in vals:
            label = f"[{v['title']}]({v['url']})" if v['url'] else v['title']
            suffix = []
            if v['author']:
                suffix.append(f"by {v['author']}")
            suffix.append(f"date_basis: `{v['date_basis']}`")
            line = f"- {label} — " + '; '.join(suffix)
            if v['text'] and v['text'] != v['title']:
                line += f" — {v['text']}"
            lines.append(line)
    lines.append('')
    return '\n'.join(lines)


def main() -> None:
    days: dict[str, list[dict[str, Any]]] = defaultdict(list)
    collect_x(days); collect_youtube(days); collect_xhs(days); collect_maps(days); collect_douban(days)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    written = []
    total_items = 0
    for date, items in sorted(days.items()):
        out = OUT_ROOT / 'unknown-date.md' if date == 'unknown-date' else OUT_ROOT / date[:4] / f'{date}.md'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_day(date, items), encoding='utf-8')
        written.append(out); total_items += len(items)
    print(f'written_files={len(written)}')
    print(f'total_items={total_items}')
    for p in written[:20]: print(p.relative_to(ROOT))
    for p in written[-20:]: print(p.relative_to(ROOT))

if __name__ == '__main__':
    main()
