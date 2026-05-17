# Archived source: `like-based-preference-profile`

Preference profiles are derived from X/Twitter and other liked-content exports.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/like-based-preference-profile`

---

# Like-Based Preference Profile

Use when Tony asks to "learn my preferences", "learn from my likes", "从导出的 like 里学习我的喜好", or asks to personalize briefings/recommendations from exported liked/saved content.

## Inputs

Prefer canonical source artifacts under `/home/tonyxu/brain/sources/`:

- X/Twitter likes: `/home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD/twitter_likes_agent_reach_YYYYMMDD.jsonl`
- YouTube liked videos: `/home/tonyxu/brain/sources/youtube-likes/YYYYMMDD/youtube_liked_videos_*.jsonl`
- YouTube Music liked songs: `/home/tonyxu/brain/sources/youtube-likes/YYYYMMDD/youtube_liked_music_*.jsonl`
- XHS likes/favorites if relevant: `/home/tonyxu/brain/sources/xhs-likes-favorites/YYYYMMDD/*.jsonl`
- Douban movie/TV export if relevant: `/home/tonyxu/brain/sources/douban/YYYYMMDD/douban_*_export.json`

If multiple versions exist, use the latest canonical `brain/sources` export, not stale `/tmp` or `/home/tonyxu/exports` copies. Exception: if a prior export only exists in `/tmp`, first copy it into `/home/tonyxu/brain/sources/<family>/<YYYYMMDD>/`, then analyze the canonical copy.

## Workflow

1. Load the relevant export skills first if applicable:
   - `x-archive-to-gbrain` for X/Twitter likes.
   - `youtube-content` for YouTube / YouTube Music likes.
   - `gbrain-manual-project-capture` for gbrain/source artifact conventions.

2. Verify source files exist and counts are sane.

```python
from pathlib import Path
import json
p = Path('/home/tonyxu/brain/sources/x-likes/agent-reach-YYYYMMDD/twitter_likes_agent_reach_YYYYMMDD.jsonl')
count = sum(1 for _ in p.open())
```

3. Parse JSONL and compute statistics:
   - counts per source
   - language split
   - year/date ranges
   - top X authors and linked domains
   - top YouTube channels/artists
   - Douban genres, countries/regions, directors/actors, rating distribution, top-rated anchors
   - rough topic taxonomy by keyword/regex
   - distinctive examples per topic

Recommended taxonomy buckets:

- AI/LLM/Agents
- Developer Tools/Open Source
- Apple/Hardware/Consumer Tech
- Startups/Product/Business
- Design/UX/Creativity
- China/中文互联网
- Finance/Trading/Crypto
- Politics/Society
- Parenting/Kids/Education
- Music
- Comedy/Entertainment

4. Keep the analysis judgment-based, not just counts.
   - Likes are noisy; infer stable preferences only when multiple sources agree.
   - Separate content types: X tech discourse, YouTube videos, YouTube Music, XHS lifestyle/visuals, Douban movie/TV taste.
   - Douban ratings in Tony's export are public item ratings unless the export includes personal scores; use them as quality anchors, not proof of Tony's explicit rating.
   - Do not let music likes drown out tech/product preferences.
   - Treat kids/nursery content as possible family context unless it is a dominant cluster.

5. Write canonical artifacts under:

```text
/home/tonyxu/brain/sources/preference-profile/YYYYMMDD/
  like_preference_stats_YYYYMMDD.json
  tony_like_preference_profile_YYYYMMDD.md
```

6. Import the concise Markdown profile into gbrain:

```bash
gbrain put like-based-preference-profile-YYYYMMDD < /home/tonyxu/brain/sources/preference-profile/YYYYMMDD/tony_like_preference_profile_YYYYMMDD.md
for tag in preferences profile likes x youtube music personalization; do
  gbrain tag like-based-preference-profile-YYYYMMDD "$tag"
done
```

For domain-specific profiles, use explicit slugs and tags, e.g.:

```bash
gbrain put douban-viewing-preference-profile-YYYYMMDD < /home/tonyxu/brain/sources/douban/YYYYMMDD/douban_preference_profile_YYYYMMDD.md
for tag in douban movies tv preferences profile entertainment; do
  gbrain tag douban-viewing-preference-profile-YYYYMMDD "$tag"
done
```

If `gbrain put` emits OpenAI embedding quota `429`, the page write can still succeed. Verify with `gbrain get` and keyword search. If it fails with a transient Postgres `CONNECT_TIMEOUT`, retry once or twice; the later retry can succeed even when the first write failed after embedding.

7. Update long-term memory compactly only with durable, high-level preferences.
   - Good memory shape: `Like profile (Apr 2026, 7,020 likes): practical AI agents/LLM tooling, GitHub/open-source/dev tools, Apple/HW, product/startup mechanics, visual AI/design; 2:1 Chinese tech discourse. Music: Mandopop + classical/piano.`
   - Do not store raw counts, file paths, full top-author lists, or task progress in memory. Those belong in gbrain/source artifacts.

## Output format

Telegram final response should be short:

- State the main inferred preference in one sentence.
- List data sources/counts.
- List 5-7 high-signal preference clusters.
- Give gbrain slug and source path.
- Mention embedding 429 caveat only if it occurred.

## Known good result from 2026-04-25

Analyzed 7,020 liked items:

- X/Twitter likes: 4,009
- YouTube liked videos: 1,946
- YouTube Music liked songs: 1,065

Profile conclusion: Tony's strongest revealed preference is practical AI + systems + taste: AI agents, LLM tooling, GitHub/open-source/dev tools, Apple/hardware ecosystem shifts, startup/product mechanics, visual AI/design, and Chinese+English tech commentary. Music taste clusters around Mandopop/Taiwan-HK nostalgia plus classical/piano/orchestral.

Artifacts:

- gbrain page: `like-based-preference-profile-20260425`
- source markdown: `/home/tonyxu/brain/sources/preference-profile/20260425/tony_like_preference_profile_20260425.md`
- Douban movie/TV profile: `douban-viewing-preference-profile-20260417`
  - source dir: `/home/tonyxu/brain/sources/douban/20260417/`
  - source export: 249 rows from `/tmp/douban_120942873_export.json`, copied to sources
  - conclusion: Chinese-language drama/comedy/crime-suspense first; strong Mainland + HK/Taiwan cultural context; smart sitcoms and prestige international drama; examples include 红楼梦, 白色巨塔, 霸王别姬, The Office, Big Bang Theory, 漫长的季节, 狂飙, 黑暗荣耀.

## Pitfalls

- JSONL can be corrupted by embedded newlines or Unicode line separators. When creating JSONL, use `json.dumps(..., ensure_ascii=True, separators=(",", ":"))` and validate by reading every line with `json.loads`.
- X visible-like exports can miss deleted/private/unavailable tweets; do not claim perfect full history unless using official archive data.
- Keyword taxonomy is only a coarse lens. Use it to support judgment, not replace it.
- Memory is tight. Save one compact durable preference line, not a full report.
- Do not expose tokens/cookies or credential-derived raw data in summaries.
