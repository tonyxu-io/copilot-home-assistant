# X reply attribution filtering — 2026-05-04

## Problem

Tony flagged `daily/activity` rows under `X replies` that were not his own replies. They were the posts he replied to, pulled in as context from X web GraphQL `UserTweetsAndReplies`.

Bad symptom: reply target tweets appeared as if they were Tony-authored posts/replies.

## Root cause

`UserTweetsAndReplies` can include surrounding conversation/context tweets, not just the account owner's authored replies. If the pipeline treats every tweet returned by that endpoint as timeline activity, reply targets leak into:

- `sources/x-posts/latest/twitter_posts_agent_reach_latest.jsonl`
- `daily/activity/YYYY/YYYY-MM-DD.md`
- downstream writing/activity synthesis

## Correct rule

For Tony's timeline exports and daily ledgers, keep only:

1. Tony-authored rows: `author.screenName == t0nyxu` or `author.username == t0nyxu`
2. Explicit Tony reposts: `kind == repost` and `retweetedBy == t0nyxu`

Everything else from `UserTweetsAndReplies` is reply/conversation context. It may be useful as metadata, but must not be emitted as Tony's own `X posts` or `X replies` item.

## Implementation pattern

Collector-side filter in `~/.hermes/scripts/sync_x_likes_to_gbrain.py`:

```python
def is_tony_timeline_record(rec):
    kind = rec.get('kind') or 'post'
    return author_screen(rec) == SCREEN_NAME or (kind == 'repost' and rec.get('retweetedBy') == SCREEN_NAME)
```

Apply it after normalizing/enriching timeline records and before writing cumulative exports.

Daily ledger filter in `/home/tonyxu/brain/scripts/backfill_daily_activity_from_sources.py`:

```python
def is_tony_x_activity(obj, *, author, kind):
    return author == 't0nyxu' or (kind == 'repost' and obj.get('retweetedBy') == 't0nyxu')
```

Apply it before `add_item(...)` for X posts/replies/reposts.

Coverage verifier in `/home/tonyxu/brain/scripts/verify_daily_activity_coverage.py` must count only the same Tony-authored/reposted rows from `x-posts-jsonl`; otherwise it will treat filtered context tweets as missing coverage.

## Verification checklist

- `python3 -m py_compile ~/.hermes/scripts/sync_x_likes_to_gbrain.py scripts/backfill_daily_activity_from_sources.py scripts/verify_daily_activity_coverage.py`
- Rebuild affected daily ledgers.
- `python3 scripts/verify_daily_activity_coverage.py --json` returns `ok: true` with no warnings/failures.
- Targeted search for flagged reply-target tweet IDs/titles returns no `daily/activity` matches.
- Programmatic scan of `sources/x-posts/latest/twitter_posts_agent_reach_latest.jsonl` reports `bad_non_tony == 0`.
- If GBrain pages were stale, sync affected daily pages and run `gbrain embed --stale`; final `gbrain stats` should show `Embedded == Chunks`.

## Pitfalls

- `sources/x-posts/latest/` is ignored by git in this repo, so collector-output fixes may not show as tracked file changes. Commit the repo-local scripts/daily ledgers; remember that the live helper script under `~/.hermes/scripts/` is outside the brain repo.
- `git diff --check` can fail on unrelated generated Gmail/Calendar digest blank EOF lines. Normalize trailing blank lines before committing source snapshots.
- Split commits by concern: one commit for X attribution/ledger repair, another for unrelated refreshed Gmail/Calendar snapshots.