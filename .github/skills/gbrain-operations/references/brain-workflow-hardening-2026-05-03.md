# Brain workflow hardening — 2026-05-03

## Context

Tony asked to continue reviewing and improving `/home/tonyxu/brain` workflow after the social activity collector had been repaired. The useful learning was not a new narrow workflow, but a broader hardening pattern for brain/GBrain maintenance: local Markdown can be healthy while GBrain is missing exact pages, and git can quietly track transient collector artifacts unless explicitly cleaned.

## What changed

- Added a repair/backfill tool in the repo: `scripts/sync_daily_activity_to_gbrain.py`.
- The tool supports targeted exact-page repair (`--slug YYYY-MM-DD`), recent-window repair (`--since YYYY-MM-DD --missing-only`), and resumable sync state via `state/activity_collector_gbrain_sync_state.json`.
- Repaired missing recent daily activity pages such as `daily/activity/2026/2026-05-02` and `daily/activity/2026/2026-05-03`.
- Updated `social-activity-collector` cron prompt to include:
  1. X auth check,
  2. X likes sync,
  3. `collect_activity.py --quiet-success`,
  4. recent missing-page repair with `sync_daily_activity_to_gbrain.py --all --missing-only --since 2026-04-25`,
  5. coverage verification,
  6. `gbrain embed --stale` + stats parity,
  7. readback of representative daily/X pages.
- Updated top-level brain workflow docs (`README.md`, `Home.md`, `Import Dashboard.md`) and synced them to GBrain with stable slugs.
- Tightened `.gitignore` for transient state, generated latest aliases, failed raw exports, and Python cache files.
- Removed already-tracked transient material from git index with `git rm --cached`, without deleting local files:
  - `scripts/__pycache__`, `scripts/collectors/__pycache__`
  - `state/rebuild_backups`
  - `state/gmail_digest_import_staging`

## Verification pattern

Use exact readback, not search alone:

```bash
cd /home/tonyxu/brain
python3 -m py_compile scripts/sync_daily_activity_to_gbrain.py scripts/collect_activity.py scripts/backfill_daily_activity_from_sources.py scripts/verify_daily_activity_coverage.py
python3 scripts/collect_activity.py --quiet-success
python3 scripts/verify_daily_activity_coverage.py --json
python3 scripts/sync_daily_activity_to_gbrain.py --slug 2026-05-02 --missing-only
python3 scripts/sync_daily_activity_to_gbrain.py --slug 2026-05-03 --missing-only
gbrain get daily/activity/2026/2026-05-02
gbrain get daily/activity/2026/2026-05-03
gbrain get x-likes-agent-reach-export-20260502
gbrain embed --stale
gbrain stats
```

Healthy observed state:

- Activity coverage: `7711 / 7711`, `1259` days.
- GBrain embedding parity: `Chunks == Embedded`.
- Sync state hash count matched daily activity file count (`1259`).
- `notes/records/private/`, `sources/x-likes/latest/`, pycache, rebuild backups, and Gmail import staging should not be tracked.

## Pitfalls

- A bulk `--all --missing-only` repair over every historical daily page can be slow because it probes each slug with `gbrain get`; prefer targeted `--slug` or bounded recent windows unless doing a deliberate backfill.
- `changed_files=0` from the collector does not prove GBrain contains all local daily pages. Exact `gbrain get daily/activity/...` is the source-of-truth check.
- Do not kill or rewrite long-running syncs blindly; inspect process/logs first. If a repair script is silent while probing thousands of pages, add progress output and narrower date filters.
- Do not commit generated collector churn casually; distinguish human-authored workflow/doc/script changes from Gmail/Calendar/source state churn.
- `git rm --cached` is appropriate for removing tracked generated/transient files while preserving local copies; do not use destructive deletion unless Tony approves.
