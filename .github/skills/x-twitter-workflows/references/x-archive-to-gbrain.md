# Archived source: `x-archive-to-gbrain`

Archive export belongs under the broader X/Twitter data workflows class.

Original skill path: `/home/tonyxu/.hermes/skills/social-media/x-archive-to-gbrain`

---

# When to use

User wants their X/Twitter likes or bookmarks imported into gbrain as durable notes.

# Hard constraints (learned, don't retry)

1. **Official Likes endpoint (`GET /2/users/:id/liked_tweets`) only returns the most recent ~800 tweets** before hitting `CreditsDepleted` on Free/Basic tiers. Do not treat this as full history.

2. **Agent Reach / `twitter-cli` cookie-auth GraphQL can fetch much more of the user's own visible likes** without official API credits. Prefer it when Twitter cookies are configured. It is still not guaranteed to equal profile `likes` count because deleted/private/unavailable tweets can disappear from the web GraphQL timeline.

3. **Bookmarks endpoint requires OAuth2 user context.** OAuth1 (the default for most xurl setups) gets `403 Unsupported Authentication`. Setting up OAuth2 requires a browser callback flow — not feasible over Telegram. Tell the user to run `xurl auth` locally before attempting bookmarks.

4. **No Pro-tier budget assumed.** Don't suggest the paid X API plan unless the user brings it up.

# Workflow (likes via Agent Reach cookie auth — preferred when configured)

Use this before falling back to official `xurl` API. It avoids X API credit limits and can fetch far more of the user's visible likes through the browser-session GraphQL endpoint.

1. Confirm Agent Reach Twitter auth:

```bash
twitter status --json
```

Expected: `ok: true`, authenticated user `@t0nyxu`, and profile `likes` count.

2. Try the stock CLI first, but know its practical cap:

```bash
mkdir -p /home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD
twitter likes t0nyxu -n 5000 --json -o /home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD/twitter_likes_agent_reach_YYYYMMDD.raw.json
```

Current `twitter-cli` has an internal hard cap around 500 and often returns only ~200 for `twitter likes`, even with a larger `-n`. If the count is far below profile likes, use the custom pagination below.

3. Custom pagination via `twitter_cli.client.TwitterClient._graphql_get("Likes", ...)` can walk the web GraphQL cursor. Run it with the twitter-cli tool Python from `/tmp` to avoid import shadowing:

```bash
cd /tmp && ~/.local/share/uv/tools/twitter-cli/bin/python /tmp/fetch_twitter_likes_agent_reach.py
```

Core script pattern:

```python
from twitter_cli.auth import get_cookies
from twitter_cli.client import TwitterClient
from twitter_cli.config import load_config
from twitter_cli.graphql import FEATURES
from twitter_cli.parser import parse_timeline_response, _deep_get
from twitter_cli.serialization import tweets_to_data

cookies = get_cookies()
rl = dict((load_config() or {}).get("rateLimit") or {})
rl["maxCount"] = 5000  # override package hard cap for this direct client use
client = TwitterClient(cookies["auth_token"], cookies["ct0"], rl, cookie_string=cookies.get("cookie_string"))

def get_likes_instructions(data):
    return (_deep_get(data, "data", "user", "result", "timeline", "timeline", "instructions")
            or _deep_get(data, "data", "user", "result", "timeline_v2", "timeline", "instructions"))

cursor = None
seen = set()
all_tweets = []
for page in range(1, 160):
    variables = {
        "count": 40,
        "userId": "11706742",
        "includePromotedContent": False,
        "withClientEventToken": False,
        "withBirdwatchNotes": False,
        "withVoice": True,
    }
    if cursor:
        variables["cursor"] = cursor
    raw = client._graphql_get("Likes", variables, FEATURES)
    Path(out_dir, f"likes_graphql_page_{page:03d}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2))
    tweets, next_cursor = parse_timeline_response(raw, get_likes_instructions)
    for tw in tweets:
        if tw.id and tw.id not in seen:
            seen.add(tw.id)
            all_tweets.append(tw)
    if not next_cursor or next_cursor == cursor:
        break
    cursor = next_cursor
    time.sleep(2.5 * random.uniform(0.7, 1.4))

export = {"ok": True, "source": "agent-reach twitter-cli GraphQL Likes", "data": tweets_to_data(all_tweets)}
Path(out_dir, "twitter_likes_agent_reach_paginated_YYYYMMDD.raw.json").write_text(json.dumps(export, ensure_ascii=False, indent=2))
```

4. Normalize into canonical source files under `/home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD/`:

- `twitter_likes_agent_reach_paginated_YYYYMMDD.raw.json`
- `likes_graphql_page_NNN.json` raw pages
- `twitter_likes_agent_reach_YYYYMMDD.jsonl`
- `twitter_likes_agent_reach_YYYYMMDD.csv`
- `index.md`
- `md/x-likes-YYYY.md`

Important: when writing JSONL, use `json.dumps(..., ensure_ascii=True, separators=(",", ":"))` or otherwise ensure U+2028/U+2029 and embedded newlines cannot corrupt line-delimited JSON. Validate by reading every JSONL line back with `json.loads`.

5. Import/refresh gbrain:

```bash
gbrain put x-likes-agent-reach-export-YYYYMMDD < index.md
for f in md/x-likes-*.md; do slug=$(basename "$f" .md); gbrain put "$slug" < "$f"; done
```

Add tags: `x twitter likes export social agent-reach`.

6. Verify:

```bash
find /home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD -type f | wc -l
gbrain get x-likes-agent-reach-export-YYYYMMDD
gbrain get x-likes-2026
gbrain search "distinctive tweet keyword"
```

Expected from Tony's 2026-04-25 run: 4,009 unique liked tweets, 102 raw GraphQL pages, 9 year pages, covering 2015-10-22 → 2026-04-25. Profile showed ~4,261 likes, so remaining delta likely came from deleted/private/unavailable tweets.

# Workflow (likes via official API, partial coverage)

1. Confirm auth: `xurl whoami` should return the user profile.

2. Get user ID from whoami output.

3. **Dedup before fetching.** Load all existing tweet IDs from `~/.hermes/data/x-archive/raw/likes_page_*.json` into a set. This is the "known IDs" set.

4. Paginate with `xurl "/2/users/<ID>/liked_tweets?max_results=100&tweet.fields=created_at,author_id&expansions=author_id&user.fields=username,name&pagination_token=..."`. Save each page as raw JSON to `~/.hermes/data/x-archive/raw/likes_page_NNN.json` (continue numbering from last existing page). Stop when:
   - `meta.next_token` is missing, OR
   - response body is the `CreditsDepleted` error (parse will fail with `Extra data` JSONDecodeError because xurl appends a red "Error: request failed" line after the JSON body — that's the signal), OR
   - **Any tweet in the current page is already in the known IDs set** — this means we've caught up to previously exported data. Save this final page (it may contain some new tweets at the top) and stop. Since the API returns likes in reverse chronological order, all subsequent pages are guaranteed to be duplicates.

4. Parse all valid pages, dedupe by tweet id, join author_id → username via `includes.users`.

5. Group by year from `created_at[:4]`. Sort within each year descending by date.

6. Render each year as one markdown file with lines like:
   `- **YYYY-MM-DD** · [@username](https://x.com/username/status/ID) — text`

7. Import to gbrain with slug pattern `x-likes-YYYY`:
   ```bash
   gbrain put x-likes-2026 < x-likes-2026.md
   ```

8. If `gbrain put` emits an embedding error (`429 quota`) the page still saved — just no semantic search for that one. Keyword search still works.

# Workflow (full history via archive — preferred for completeness)

1. User requests archive at x.com/settings → "Download an archive of your data". Delivery takes ~24h.

2. User unzips and provides the path. Look for `data/like.js` and `data/account-*.js` (for the handle).

3. `like.js` is JS-wrapped JSON: `window.YTD.like.part0 = [...]`. Strip the prefix, `JSON.parse` the array. Each entry has `like.tweetId` and `like.fullText`.

4. Hydrate with author info if needed — archive doesn't include author username per tweet, only the ID. For historical archive, it's acceptable to write `unknown` and link via tweet ID: `https://x.com/i/status/TWEET_ID` resolves correctly.

5. Same year-grouping + gbrain import as above.

# Pitfalls

- **xurl output is not pure JSON on errors.** It appends ANSI-colored `Error: request failed` after the JSON body. `json.load` fails with `Extra data`. Detect CreditsDepleted by catching `JSONDecodeError` or by checking for `"title": "CreditsDepleted"` before parsing.
- **Tweet text contains raw newlines.** Normalize with `.replace("\n", " ").strip()` before writing markdown bullets.
- **~800 is a hard API ceiling, not a rate limit.** Waiting won't help. Only archive gives full history.
- **Bookmarks total count is not reported by whoami.** User's `public_metrics.like_count` covers likes only.
- **Project taxonomy**: user explicitly preferred dedicated `x-likes` / `x-bookmarks` pages outside the main project list (prior convention: fold life/work into parent projects, but X archive is reference material, not a project).
