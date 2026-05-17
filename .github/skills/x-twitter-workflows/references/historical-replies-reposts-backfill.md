# Historical X replies/reposts backfill

Use when Tony asks to fill historical X replies/reposts into brain/GBrain activity ledgers.

## Key learning

`UserTweets` alone is insufficient: it exposes posts + reposts and may include only a small number of replies. To capture authored replies, fetch `UserTweetsAndReplies` too, then merge both timelines by tweet ID.

## Workflow

1. Run the live helper, not a stale skill copy:

```bash
cd /home/tonyxu/brain
/home/tonyxu/.hermes/scripts/sync_x_likes_to_gbrain.py --posts-only --full --max-pages 200 --verbose
```

Expected success summary from the 2026-05-03 backfill class:

```text
Synced X activity: posts/replies/reposts new=2603 cumulative=2787 pages=83 stop=UserTweets=no_next_cursor; UserTweetsAndReplies=no_next_cursor imported=10
```

2. Verify latest cumulative export:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/home/tonyxu/brain/sources/x-posts/latest/twitter_posts_agent_reach_latest.jsonl')
counts={}; ids=set(); dup=0; oldest=newest=None
for line in p.open():
    rec=json.loads(line); tid=str(rec.get('id') or '')
    dup += tid in ids; ids.add(tid)
    counts[rec.get('kind','?')]=counts.get(rec.get('kind','?'),0)+1
    dt=rec.get('createdAtISO') or rec.get('createdAt')
    if dt:
        oldest=dt if oldest is None or dt<oldest else oldest
        newest=dt if newest is None or dt>newest else newest
print({'total':len(ids),'duplicates':dup,'counts':counts,'oldest':oldest,'newest':newest})
PY
```

3. Rebuild daily ledgers and GBrain:

```bash
python3 scripts/collect_activity.py --quiet-success
gbrain embed --stale
gbrain stats
```

If a long full sync times out mid-GBrain sync, rerun `collect_activity.py`; it uses `state/activity_collector_gbrain_sync_state.json`. The collector should skip already-synced file hashes before continuing.

4. Verify coverage:

```bash
python3 scripts/verify_daily_activity_coverage.py --json
```

Known-good after backfill:

- X posts/replies/reposts total: `2787`
- Posts: `1151`
- Replies: `1573`
- Reposts: `63`
- Coverage: `10501 / 10501`, warnings `[]`
- GBrain parity: `Chunks == Embedded`

## Pitfalls

- Do not infer historical reply completeness from `UserTweets`; use `UserTweetsAndReplies`.
- Do not collapse `in_reply_to_*` records into generic posts.
- Search can time out for broad `gbrain search "notes/"`; use `gbrain list --type ...`, filesystem counts, and exact `gbrain get` readbacks.
- Before committing raw GraphQL pages, run a staged secret/token scan and avoid printing token-like values.
