# Daily activity ledger backfill and verification

Session learning: after defining `daily/activity/YYYY/YYYY-MM-DD.md` as the cross-source daily ledger, historical likes/favorites/saves were **not** automatically present there. Do not assume the rule is implemented just because README/cron says so.

## Canonical rule

- Source-specific raw exports stay under `sources/...` as provenance.
- Every collected like/favorite/save should also be represented in:

```text
/home/tonyxu/brain/daily/activity/YYYY/YYYY-MM-DD.md
```

This is the day-level ledger used by writing workflows.

## Verification before answering

Run a deterministic coverage check:

```bash
cd /home/tonyxu/brain
python3 /home/tonyxu/.hermes/skills/productivity/gbrain-operations/scripts/verify_daily_activity_coverage.py
```

Minimum checks:

- Does `/home/tonyxu/brain/daily/activity/` exist?
- How many `daily/activity/**/*.md` files exist?
- How many records exist in source exports?
- Do daily files contain matching source references?

Observed source roots:

- `sources/x-likes/`
- `sources/youtube-likes/`
- `sources/xhs-likes-favorites/`
- `sources/douban/`
- `sources/google-maps-favorite-food/`
- `sources/preference-profile/`

## Backfill policy

If daily activity is missing:

1. Build deterministic Markdown day files from source exports. Prefer the reusable script when the current source shapes match:

```bash
cd /home/tonyxu/brain
python3 /home/tonyxu/.hermes/skills/productivity/gbrain-operations/scripts/backfill_daily_activity_from_sources.py
```

2. Use true content/activity date when present, not export date.
   - X likes usually have `createdAtISO` / `createdAtLocal` for the liked tweet’s creation time; use this as content generation date and label `date_basis: content_created_at`.
   - YouTube likes: use `release_timestamp`, `upload_date`, or published date when available; use collection/export date only if no content timestamp exists and label `date_basis: collection_date`.
   - Douban has `added_at`; use it when it represents Tony's saved/rated activity timestamp and label accordingly.
   - Google Maps has `list_added_at_utc` when available.
   - Xiaohongshu UI export: use item publish/create timestamp when present; otherwise collection date with `date_basis: collection_date`.
3. Include date basis in each section or item when it is not the content generation date.
4. Include source-file references for every section so the daily ledger is traceable.
5. Preserve distinct signals even when URLs overlap:
   - YouTube video and YouTube Music entries can share the same video id; keep both as separate sources (`YouTube likes`, `YouTube Music likes`).
   - Xiaohongshu `like` and `favorite` can share the same note URL; keep both if both were collected.
6. Keep daily ledgers raw-ish; writing syntheses still live in `notes/writing/activity-inspiration/YYYY-MM-DD.md`.
7. For GBrain, prefer canonical slugs with the full path:

```bash
gbrain put daily/activity/YYYY/YYYY-MM-DD < daily/activity/YYYY/YYYY-MM-DD.md
gbrain embed daily/activity/YYYY/YYYY-MM-DD
gbrain get daily/activity/YYYY/YYYY-MM-DD
```

Pitfall: `gbrain import /home/tonyxu/brain/daily` may create non-canonical slugs such as `2026-04-25` or `activity/2023/2023-05-09` instead of `daily/activity/YYYY/YYYY-MM-DD`. Verify with `gbrain get daily/activity/YYYY/YYYY-MM-DD`; do not assume broad import preserved the desired slug.

Use `gbrain embed --stale` only for reconciliation if `Embedded < Chunks`; poll until completion before claiming `Embedded == Chunks`.

## Final sync verification pattern

A completed broad import can still leave stale embeddings, and an interrupted/aborted progress line may be misleading. Finish with measured checks:

```bash
cd /home/tonyxu/brain
gbrain stats
# If Embedded < Chunks:
gbrain embed --stale
# Re-run until stats shows parity:
gbrain stats
```

Expected pass condition: `Embedded == Chunks`. In the 2026-05 daily activity backfill, the final verified state was `Chunks: 40186` and `Embedded: 40186` after an extra small `gbrain embed --stale` pass embedded the last 81 chunks.

Verify both retrieval and search:

```bash
gbrain get daily/activity/2026/2026-04-25
gbrain get daily/activity/2018/2018-03-03
gbrain search 'date_basis content_created_at' --limit 3
gbrain search 'YouTube Music likes collection_date' --limit 3
```

Slug pitfall from this run: `gbrain import /home/tonyxu/brain/daily --no-embed --fresh` imported pages and chunks successfully, but also produced non-canonical slugs like `activity/2026/2026-04-25` alongside canonical slugs. Treat canonical `daily/activity/YYYY/YYYY-MM-DD` as the supported address for future workflows; use non-canonical hits only as diagnostic evidence.

Coverage counts from the 2026-05 backfill, useful as a regression baseline:

- daily files: 1252
- total activity items: 7667
- X likes: 4009 (`content_created_at`)
- YouTube likes: 1946 (`collection_date` fallback; source lacked publish time)
- YouTube Music likes: 1065 (`collection_date` fallback; source lacked publish time)
- Xiaohongshu likes/favorites: 320 (`collection_date` fallback; source lacked create time)
- Douban: 249 (`activity_added_at`)
- Google Maps favorite food: 78 (`activity_saved_at`)

## Reporting

If the user asks whether likes are in daily notes, answer from measured filesystem/GBrain state, not intended workflow. Say the gap plainly and include counts.