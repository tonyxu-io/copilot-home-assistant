#!/usr/bin/env python3
"""Verify whether source likes/favorites/saves are represented in brain daily activity notes.

This is intentionally read-only. It prints counts and likely gaps without dumping item contents.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path('/home/tonyxu/brain')
DAILY = ROOT / 'daily' / 'activity'
SOURCE_ROOTS = [
    ROOT / 'sources' / 'x-likes',
    ROOT / 'sources' / 'youtube-likes',
    ROOT / 'sources' / 'xhs-likes-favorites',
    ROOT / 'sources' / 'douban',
    ROOT / 'sources' / 'google-maps-favorite-food',
    ROOT / 'sources' / 'preference-profile',
]


def line_count(path: Path) -> int:
    with path.open('r', encoding='utf-8', errors='ignore') as f:
        return sum(1 for _ in f)


def csv_count(path: Path) -> int:
    try:
        return max(0, line_count(path) - 1)
    except Exception:
        return 0


def json_count(path: Path) -> int | str:
    try:
        data = json.load(path.open('r', encoding='utf-8', errors='ignore'))
    except Exception as exc:
        return f'ERR:{exc}'
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict) and isinstance(data.get('entries'), list):
        return len(data['entries'])
    return 'json'


def source_summary() -> list[tuple[str, int, dict[str, int]]]:
    rows = []
    for root in SOURCE_ROOTS:
        counts: dict[str, int] = {}
        total = 0
        if root.exists():
            for path in root.rglob('*'):
                if path.is_file():
                    total += 1
                    counts[path.suffix.lower() or '<noext>'] = counts.get(path.suffix.lower() or '<noext>', 0) + 1
        rows.append((str(root.relative_to(ROOT)), total, counts))
    return rows


def likely_record_counts() -> list[tuple[str, str, int | str]]:
    candidates = [
        ('x-jsonl', ROOT / 'sources/x-likes/agent-reach-20260425/twitter_likes_agent_reach_20260425.jsonl', line_count),
        ('x-csv', ROOT / 'sources/x-likes/agent-reach-20260425/twitter_likes_agent_reach_20260425.csv', csv_count),
        ('youtube-all-jsonl', ROOT / 'sources/youtube-likes/20260425/youtube_liked_all_20260425_170014.jsonl', line_count),
        ('youtube-videos-jsonl', ROOT / 'sources/youtube-likes/20260425/youtube_liked_videos_20260425_170014.jsonl', line_count),
        ('youtube-music-jsonl', ROOT / 'sources/youtube-likes/20260425/youtube_liked_music_20260425_170014.jsonl', line_count),
        ('xhs-jsonl', ROOT / 'sources/xhs-likes-favorites/20260426/xhs_ui_likes_favorites_20260426015848.jsonl', line_count),
        ('maps-jsonl', ROOT / 'sources/google-maps-favorite-food/20260426/google_maps_favorite_food_20260426.jsonl', line_count),
        ('douban-json', ROOT / 'sources/douban/20260417/douban_120942873_export.json', json_count),
    ]
    out = []
    for label, path, counter in candidates:
        if path.exists():
            try:
                count = counter(path)
            except Exception as exc:  # pragma: no cover - diagnostic script
                count = f'ERR:{exc}'
            out.append((label, str(path.relative_to(ROOT)), count))
    return out


def daily_like_files() -> list[str]:
    if not (ROOT / 'daily').exists():
        return []
    needles = ('x-likes', 'youtube', 'xhs', 'xiaohongshu', '小红书', 'like', 'likes', 'favorite', 'favorites', 'bookmark')
    matches = []
    for path in (ROOT / 'daily').rglob('*.md'):
        if path.name == 'README.md':
            continue
        text = path.read_text(encoding='utf-8', errors='ignore').lower()
        if any(n in text for n in needles):
            matches.append(str(path.relative_to(ROOT)))
    return matches


def main() -> None:
    daily_files = sorted(DAILY.rglob('*.md')) if DAILY.exists() else []
    print(f'DAILY_ACTIVITY_EXISTS {DAILY.exists()}')
    print(f'DAILY_ACTIVITY_MD_COUNT {len(daily_files)}')
    for path in daily_files[:20]:
        print(f'DAILY_ACTIVITY_FILE {path.relative_to(ROOT)}')

    print('\nSOURCE_SUMMARY')
    for name, total, counts in source_summary():
        print(f'{name} files={total} ext={dict(sorted(counts.items()))}')

    print('\nLIKELY_RECORD_COUNTS')
    for label, path, count in likely_record_counts():
        print(f'{label} {path} {count}')

    print('\nDAILY_FILES_WITH_LIKE_TERMS')
    matches = daily_like_files()
    if matches:
        for path in matches[:50]:
            print(path)
    else:
        print('(none)')


if __name__ == '__main__':
    main()
