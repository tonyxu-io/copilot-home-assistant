---
name: x-twitter-workflows
description: "Operate X/Twitter workflows: official API/x-cli usage, Agent Reach cookie auth, likes/bookmarks exports, gbrain archival, and preference-profile extraction."
version: 1.0.0
license: MIT
metadata:
---

# X/Twitter Workflows

Use this for X/Twitter actions and data extraction: posting/searching through official API tools, cookie-auth Agent Reach workflows, exporting likes/bookmarks to gbrain, daily likes sync, and deriving preference profiles from liked/saved content.

## Choose the path
## Choose the path

- **Tony posting / routine X actions:** use the logged-in browser session, not the X API. See `references/browser-x-posting.md` for Draft.js composer pitfalls and verification. If Debian has no local Chrome/CDP, use the Debian→Mac Chrome CDP tunnel in before falling back to a fresh browser session. For the direct CDP pattern that successfully posted via Tony's tunneled Mac Chrome, see `references/browser-x-cdp-posting-success-2026-05-02.md`. If posting comes from a just-captured `memo:`, save/verify the memo first, then attempt X; see `references/memo-to-x-posting-fallback-2026-05-04.md` for the CDP-down + xurl-CreditsDepleted fallback path.
- **Official API / x-cli:** good for posting, lookup, mentions, and small official-API tasks when explicitly requested; respect access/cost limits.
- **Agent Reach cookie auth:** preferred when official API limits make likes/bookmarks/history incomplete.
- **Archive export:** preferred for completeness when the user provides a full account archive.
- **GBrain sync:** write normalized, year-grouped or source-grouped pages and verify with readback/search.
- **Preference profile:** derive durable interests from likes/saved content, but keep raw exports as references/source artifacts.
- **Daily content editor / fragmented thoughts:** for X drafts based on Tony's rough ideas, preserve new fragments with the shared `memo` / `limemo` workflow first, then use broader brain context. All collected X likes/bookmarks/posts/replies/reposts should be represented in `/home/tonyxu/brain/daily/activity/YYYY/YYYY-MM-DD.md` by the activity/content generation date, not export date; source exports remain under `sources/x-likes/` and `sources/x-posts/` as provenance. The social activity collector must fetch both `UserTweets` (posts/reposts) and `UserTweetsAndReplies` (authored replies), merge by tweet ID, and classify raw GraphQL `in_reply_to_*` metadata as `kind=reply` / source `X replies`; do not collapse replies into generic posts. `UserTweetsAndReplies` also includes surrounding conversation/context tweets; filter timeline exports and daily ledgers to Tony-authored rows (`author.screenName == t0nyxu`) plus explicit reposts (`retweetedBy == t0nyxu`) so reply targets do not appear as Tony's own `X posts`. Before claiming coverage, run the gbrain-operations coverage verifier; README/cron rules do not prove historical backfill happened. Tony's X activity can inspire topics, social-native framing, authors, and arguments, but likes/reposts are taste/ranking signals rather than Tony-authored claims or automatic endorsements. Draft only; posting still requires explicit confirmation. See `linkedin-workflows` reference `content-editor-brain-repo-workflow.md` for the shared capture and activity-inspiration workflow.

## Draft quality gate

Before rewriting/polishing an X draft, especially AI/product/market commentary, check whether it is actually interesting. Score quickly on: fresh observation, tension, concrete detail, sharpness, and shareability. If it is below 6/10, change the angle instead of smoothing the prose. Tony dislikes correct-but-bloodless drafts; a memorable line like “漂亮陌生人”, “交付物才是证据”, or “接力赛” usually beats a clean thesis paragraph.

For AI infrastructure / stock-performance X posts, keep it as market observation, not investment advice. Use today's actual moves only after checking data. Good framing: “不是一个 ticker 的故事”, “市场在一层一层找瓶颈”, “接力赛”. Avoid tickers soup, buy/sell language, and long caveats.

## Posting workflow for Tony

Posting is a public side effect. Only publish after Tony explicitly asks to post/send the final text, and verify the result appears.

For Chinese X copy in Tony's voice, consult before drafting: conversational, short, lightly personal, and not LinkedIn-style. Avoid geopolitical framing unless explicitly requested, especially `中美` / `谁打败谁` language. When Tony provides his own rough line, improve from that line instead of expanding it into a product thesis.

For the logged-in local Chrome/CDP path:

1. Draft concise text first and verify it is within X's length limit.
2. Open `https://x.com/compose/post` in the existing local session:

 ```bash
 npx -y bb-browser --port 9222 --json open https://x.com/compose/post --tab
 ```

3. Prefer human-equivalent browser input: click the `Post text` textbox / `data-testid="tweetTextarea_0"`, then type via `bb-browser type <ref> "."` or paced key events.
4. Verify both the visible editor text and the enabled post button:

 ```js
 (() => {
 })()
 ```

5. If the Post button remains disabled even though visible editor text is present, stop and report. Do **not** force-remove `disabled` and click; Draft.js/React state has not accepted the text.
6. Verify success by checking the profile/feed for the new text or a success toast.

## Verification

Verify auth identity, sample counts, output files, and imported gbrain pages. Do not infer full-history completeness from a small API page.

## Agent Reach collector pitfalls

- When running the Python sync helper directly, use a neutral working directory such as `/tmp` before importing `twitter_cli`. Running from `/home/tonyxu/brain` or another repo can shadow installed packages and make `twitter status --json` succeed while the Python helper raises a misleading cookie/auth error.
- Keep source export freshness separate from GBrain database health. If the collector's source aliases and local daily ledgers are valid but Postgres/GBrain is unreachable, treat DB sync as a downstream health issue rather than failing the social source collector noisily.

## Pitfalls

- X's composer is Draft.js-backed: visible DOM text can exist while React state is empty, leaving `tweetButtonInline` disabled. This can happen after `bb-browser fill`, synthetic paste/input, CDP `Input.insertText`, or slow per-character typing if focus lands in the wrong layer. Treat a disabled Post button as authoritative; the root cause is usually that Draft.js did not accept the input, not necessarily platform risk control.
- When Tony points out the Post button is disabled because no content is recognized, fix the input method first: use real focus/click/selection/input events and verify editor text plus enabled button before blaming X automation defenses.
- Calling X's web GraphQL `CreateTweet` directly from a logged-in browser can return code **226**: `This request looks like it might be automated`. Do not retry aggressively; it can worsen trust signals. Fall back to manual posting or a real human browser gesture.
- Browserbase/new browser sessions may not share Tony's local X login; prefer the known local `bb-browser --port 9222` Chrome session for X actions.

See `references/x-composer-automation-pitfalls-2026-05-01.md` for the detailed failure transcript and diagnostics from the 2026-05-01 session.
