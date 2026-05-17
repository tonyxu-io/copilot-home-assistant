# Archived source: `daily-x-likes-sync`

Daily likes sync is a scheduled X/Twitter-to-gbrain workflow.

Original skill path: `/home/tonyxu/.hermes/skills/daily-x-likes-sync`

---

# Daily X/Twitter Likes Sync to GBrain

Automatically sync Tony's X/Twitter likes into gbrain using Agent Reach cookie-auth GraphQL on a daily basis. Handles incremental sync, import path challenges, and integrates with Hermes cron system.

## When to Use

- When you need daily incremental sync of X likes to gbrain
- When working with Agent Reach cookie auth (not official X API)
- When dealing with Python module import path issues in scripts
- When setting up automated social media data pipelines

## Hard Constraints (Learned from Practice)

1. **Agent Reach cookie auth required**: The script depends on Twitter CLI being authenticated via `twitter status --json` - official X API OAuth is not used
2. **PYTHONPATH must be set**: twitter_cli modules live in `/home/tonyxu/.local/share/uv/tools/twitter-cli/lib/python3.12/site-packages` and must be prepended to sys.path
3. **Cookies not accessible from script context**: The script runs in a different context than the CLI, so cookie extraction may fail even when CLI shows auth
4. **Incremental sync**: Script stops when it catches up to existing likes to avoid duplicate processing
5. **No official API rate limits**: Uses GraphQL via Agent Reach, not X's rate-limited official API

## Architecture

### Script Location
- `/home/tonyxu/.hermes/scripts/sync_x_likes_to_gbrain.py` - Main sync script
- Runs from `/tmp` to avoid module shadowing issues
- Uses `twitter_cli` Python modules from Twitter CLI installation

### Output Structure
```
/home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD/
├── index.md                          # Daily export summary
├── twitter_likes_agent_reach_YYYYMMDD.jsonl  # Line-delimited JSON
├── twitter_likes_agent_reach_YYYYMMDD.csv     # CSV format
├── twitter_likes_agent_reach_paginated_YYYYMMDD.raw.json  # Full payload
├── md/x-likes-2015.md               # Yearly markdown pages
├── md/x-likes-2016.md
└── md/x-likes-2026.md               # (and so on)
```

### GBrain Pages
- `x-likes-agent-reach-export-YYYYMMDD` - Daily export index
- `x-likes-YYYY` - Yearly aggregated pages

## Setup

### 1. Verify Twitter CLI Auth
```bash
twitter status --json
# Should show authenticated user info and likes count
```

### 2. Test Twitter CLI Imports
```bash
cd /tmp
export PYTHONPATH=/home/tonyxu/.local/share/uv/tools/twitter-cli/lib/python3.12/site-packages
python3 -c "
from twitter_cli.auth import get_cookies
from twitter_cli.client import TwitterClient
from twitter_cli.config import load_config
from twitter_cli.graphql import FEATURES
from twitter_cli.parser import _deep_get, parse_timeline_response
from twitter_cli.serialization import tweets_to_data
print('SUCCESS: All imports OK')
"
```

### 3. Manual Sync Test
```bash
python3 /home/tonyxu/.hermes/scripts/sync_x_likes_to_gbrain.py --verbose
```

### 4. Add Cron Job (Manual)
Edit `/home/tonyxu/.hermes/cron/jobs.json` and add:

```json
{
  "id": "sync-x-likes-to-gbrain-YYYYMMDD",
  "name": "sync-x-likes-to-gbrain",
  "prompt": "Incrementally sync Tony's X/Twitter likes into gbrain using Agent Reach/twitter-cli cookie-auth GraphQL. Run daily.\n\nSteps:\n1. Check Twitter CLI status and verify Agent Reach auth with `twitter status --json`\n2. Run the sync script: `python3 /home/tonyxu/.hermes/scripts/sync_x_likes_to_gbrain.py`\n3. If successful, verify output files are created in /home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD/\n4. Test a few gbrain pages exist (x-likes-YYYY, x-likes-agent-reach-export-YYYYMMDD)\n5. Report success status and file count, or error if any failures occur\n\nThe script should handle incremental sync - only fetch new likes not already in the export directory. It uses cookie-auth GraphQL via Agent Reach, not the official X API which is rate-limited.\n\nOn failure, include error details from the script output.",
  "skills": ["terminal"],
  "skill": "terminal",
  "model": null,
  "provider": null,
  "base_url": null,
  "script": null,
  "schedule": {
    "kind": "cron",
    "expr": "0 8 * * *",
    "display": "0 8 * * *"
  },
  "schedule_display": "0 8 * * *",
  "repeat": {
    "times": null,
    "completed": 0
  },
  "enabled": true,
  "state": "scheduled",
  "paused_at": null,
  "paused_reason": null,
  "created_at": "2026-04-29T02:15:00-07:00",
  "deliver": "origin",
  "enabled_toolsets": ["terminal"]
}
```

## Script Features

### Incremental Sync Logic
- Loads existing tweet IDs from all previous exports
- Stops when reaching already-known tweets (unless `--full` flag)
- Uses GraphQL pagination with random delays to avoid detection

### Data Processing
- Normalizes text (removes extra whitespace, newlines)
- Handles missing/duplicate records gracefully
- Preserves original tweet metadata (author, metrics, dates)
- Generates year-grouped markdown pages for readability

### Error Handling
- Validates JSONL integrity after writing
- Reports detailed error messages for gbrain import failures
- Continues partial sync on embedding quota errors (gbrain still saves)

### Performance
- Limits to 20 pages by default (configurable)
- Random 2.5s ±0.4s delays between requests
- Processes 40 tweets per GraphQL page

## Troubleshooting

### "No Twitter cookies found"
- Run `twitter status --json` to verify auth
- The script and CLI may have different cookie contexts
- Try using the Twitter CLI directly first

### "ModuleNotFoundError: twitter_cli"
- Ensure PYTHONPATH is set correctly
- Use `/home/tonyxu/.local/share/uv/tools/twitter-cli/bin/python` for script execution
- Run from `/tmp` to avoid module shadowing

### "429 quota" errors
- These are unlikely with GraphQL Agent Reach approach
- If they occur, it's probably from gbrain embedding, not X API
- The script will save the data even if embedding fails

### Cron job not running
- Check `/home/tonyxu/.hermes/cron/jobs.json` for syntax errors
- Verify job is enabled and not paused
- Check Hermes cron service logs

## Verification

After successful sync:
```bash
# Count files in export directory
find /home/tonyxu/brain/sources/x-likes/agent-reach-$(date +%Y%m%d) -type f | wc -l

# Test gbrain pages
gbrain get x-likes-2026
gbrain get x-likes-agent-reach-export-$(date +%Y%m%d)

# Search for recent likes
gbrain search "from:last week"
```

## Daily Schedule

- **Time:** 8:00 AM PT daily
- **Cron:** `0 8 * * *`
- **Next run:** 2026-04-29 08:00:00 PT
- **Delivery:** Telegram only on failure, blocker, warning, or substantive new issue; routine successful syncs should stay silent.

## Adaptability

This pattern can be adapted for:
- Other social media daily syncs
- Incremental data exports from APIs with rate limits
- Automated document generation and gbrain ingestion
- Cookie-based authentication workflows

## Notes from Implementation

- Learned that Twitter CLI and Python modules need explicit PYTHONPATH setup
- Cookie auth works differently from CLI to Python context
- GraphQL Agent Reach approach bypasses official X API rate limits (~800 tweet cap)
- Incremental sync prevents duplicate processing and saves time
- GBrain embedding can fail independently of data storage
