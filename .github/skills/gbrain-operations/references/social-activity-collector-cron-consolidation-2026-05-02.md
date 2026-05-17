# Social activity collector cron consolidation — 2026-05-02

## Context
Tony asked to reorganize collector cron jobs for `/home/tonyxu/brain` after a daily activity ledger collector had been added.

## Observed cron state
- `sync-x-likes-to-gbrain` was enabled but had `next_run_at: null` and had never run.
- `daily-activity-collector` ran downstream ledger build/coverage verification from existing source exports.
- These were not duplicates by function, but they formed a fragile upstream/downstream pair: source freshness depended on one job, coverage verification on another.

## Consolidation pattern
Create one class-level collector cron that owns the full passive social activity pipeline:

1. Workdir: `/home/tonyxu/brain`.
2. Verify X/Twitter auth: `twitter status --json`.
3. Run upstream X activity sync with no limiting flags: `python3 /home/tonyxu/.hermes/scripts/sync_x_likes_to_gbrain.py`. Despite the filename, this syncs both likes and UserTweets timeline activity (original posts, quote posts/replies when exposed, and reposts/retweets) unless `--likes-only` or `--posts-only` is passed.
4. Verify both latest aliases exist: `sources/x-likes/latest/twitter_likes_agent_reach_latest.jsonl` and `sources/x-posts/latest/twitter_posts_agent_reach_latest.jsonl`.
5. Build/verify daily ledgers: `python3 scripts/collect_activity.py --quiet-success`; coverage must include `X likes`, `X posts`, and `X reposts`.
5. Check `gbrain stats`; if `Embedded < Chunks`, run `gbrain embed --stale`, then re-check stats.
6. Success output should be exactly `[SILENT]`; failures should be concise Chinese alerts with failing layer, command, exit code, root cause/impact, and redacted secrets/raw IDs.
7. Do not allow the scheduled run to create/update/remove cron jobs.

## Concrete result from this session
- Created `social-activity-collector` at `40 8 * * *`, skills `x-twitter-workflows` + `gbrain-operations`, workdir `/home/tonyxu/brain`.
- Removed `sync-x-likes-to-gbrain` and `daily-activity-collector`.
- Kept `email-butler-ops` separate because Gmail/Calendar is a different failure domain.
- Kept `daily-content-editor` separate because it drafts writing and does not collect source activity.

## Verification
- Re-list cron jobs after consolidation.
- Check the replacement job has a sane `next_run_at`.
- Run lightweight verification without executing the full scheduled job if auth/network side effects are not needed: compile scripts and run `scripts/verify_daily_activity_coverage.py --json`.
- Inspect `state/activity_collector_state.json` for prior collector health.

## Pitfalls
- Do not merge user-facing briefings with collectors just because they both read Gmail/X/notes.
- Do not keep an enabled cron with `next_run_at: null` as a backup; it is scheduler debt.
- Do not alert on old known zero-byte YouTube raw artifacts unless they affect coverage or Tony approved cleanup.
