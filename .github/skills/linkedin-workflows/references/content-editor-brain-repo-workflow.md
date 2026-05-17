# Content editor brain-repo workflow

Session learning: Tony wants fragmented thoughts, rough notes, saved links, prompts, decisions, reminders, and other memos to live in the brain repo, not only in Telegram/session history or opaque GBrain pages. Some memos may become X/LinkedIn material, but **memo is not a content inbox**.

## Capture semantics

- `memo` = general personal memo. Preserve raw text, then organize into structured personal notes when the destination is obvious. Do not assume it is for X/LinkedIn.
- `limemo` = work memo. Preserve raw text under work memo files and route into structured work notes when obvious.
- `linote` is legacy. Use `limemo-capture` instead.

## Canonical capture locations

Personal raw memo:

```text
/home/tonyxu/brain/notes/memo/YYYY-MM-DD.md
gbrain slug: notes/memo/YYYY-MM-DD
```

Work raw memo:

```text
/home/tonyxu/brain/notes/work/memo/YYYY-MM-DD.md
gbrain slug: notes/work/memo/YYYY-MM-DD
```

Quick capture commands:

```text
memo <personal raw thought / note / link / prompt / reminder>
limemo <work raw thought / note / link / reminder>
```

## Dated note templates

Personal:

```md
---
title: Memo — YYYY-MM-DD
tags:
  - memo
  - personal
captured: YYYY-MM-DD
---

# Memo — YYYY-MM-DD

## Raw fragments

- HH:MM PT — <exact Tony text or saved link + reason>

## Structured routing

- <optional path updated>
```

Work:

```md
---
title: Work Memo — YYYY-MM-DD
tags:
  - limemo
  - work
captured: YYYY-MM-DD
---

# Work Memo — YYYY-MM-DD

## Raw fragments

- HH:MM PT — <exact Tony text or saved link + reason>

## Structured routing

- <optional path updated>
```

## Structured note routing

For `memo`, after raw capture, route obvious items into structured notes:

- `notes/family/...` — family, home, health, travel, parenting.
- `notes/knowledge/...` — AI, tech, reading, philosophy, music, photography, prompts.
- `notes/writing/...` — writing direction, style, drafts, and publishable ideas.
- `notes/records/...` — non-private admin/reference records only.
- `people/` or `projects/` — durable person/project facts.
- `notes/unsorted/_promotion_queue.md` — useful source-derived candidates that need later curation.

For `limemo`, route obvious work material into structured work notes:

- `notes/work/projects/`
- `notes/work/growth/`
- `notes/work/operations/`
- `notes/work/people/`
- `notes/work/domain/`
- `notes/work/reference/`

When not obvious, raw capture only. Do not hallucinate taxonomy.

## Daily editor workflow

Run two passes:

1. **Triage / curation pass** — preserve new raw fragments, route obvious durable items into structured notes, and update `people/` or `projects/` when appropriate.
2. **Editorial pass** — select only public-safe, content-worthy items for X/LinkedIn drafts.

Recommended draft output location:

```text
/home/tonyxu/brain/notes/writing/content-drafts/YYYY-MM-DD.md
```

Keep draft links back to source memos or structured notes so the public/private review path stays visible.

Daily activity ledger location:

```text
/home/tonyxu/brain/daily/activity/YYYY/YYYY-MM-DD.md
```

Every collected like/favorite/save should be represented in this daily file for the content generation date when available, not the export date. Keep source-specific exports under `sources/...` as provenance; the daily file is the cross-source day view. Use collection/export date only as a labeled fallback when the source lacks content/activity timestamps.

Optional activity-inspiration output:

```text
/home/tonyxu/brain/notes/writing/activity-inspiration/YYYY-MM-DD.md
```

Use this after the daily ledger exists when X likes/bookmarks, YouTube likes, YouTube Music likes, Xiaohongshu likes/favorites, Douban, Google Maps saves, or `sources/preference-profile/` produce recurring themes worth turning into writing angles. Activity signals are taste/ranking evidence, not Tony-authored claims or automatic endorsements.

## Daily editor source order

1. New Tony-authored chat/session fragments from the last ~24-36h.
2. Personal memo raw + structured notes:
   - `/home/tonyxu/brain/notes/memo/`
   - relevant structured subtrees under `/home/tonyxu/brain/notes/`
3. Work memo raw + structured work notes:
   - `/home/tonyxu/brain/notes/work/memo/`
   - relevant structured subtrees under `/home/tonyxu/brain/notes/work/`
4. Daily activity ledger:
   - `/home/tonyxu/brain/daily/activity/YYYY/YYYY-MM-DD.md`
   - include all collected likes/favorites/saves by content generation date when available; use collection/export date only as labeled fallback before synthesis.
5. Activity source exports for provenance/backfill and writing angles, not Tony-authored claims:
   - `/home/tonyxu/brain/sources/x-likes/`
   - `/home/tonyxu/brain/sources/youtube-likes/`
   - `/home/tonyxu/brain/sources/xhs-likes-favorites/`
   - `/home/tonyxu/brain/sources/douban/`
   - `/home/tonyxu/brain/sources/google-maps-favorite-food/`
   - `/home/tonyxu/brain/sources/preference-profile/`
6. Broader brain context:
   - `/home/tonyxu/brain/people/`
   - `/home/tonyxu/brain/projects/`
   - `/home/tonyxu/brain/notes/`
   - selected safe compiled digests/backlogs under `sources/` when clearly relevant.

## Content drafting rule

Only use a memo for X/LinkedIn drafting when it has clear public-content potential or Tony explicitly intended it as content. Many memos are just knowledge capture, decisions, reminders, prompts, or personal context.

Use likes/favorites/saves as **inspiration**, not direct endorsement. The editor should first ensure they are represented in `daily/activity/YYYY/YYYY-MM-DD.md`, then synthesize taste clusters and angles, then write in Tony's voice with public-safe framing and source backlinks.

## Safety boundaries

- Preserve Tony's exact phrasing for raw fragments.
- Keep URLs with Tony's stated reason/context.
- Do not treat assistant suggestions as Tony source material unless Tony explicitly accepted them.
- Do not scan or import `/home/tonyxu/brain/notes/records/private/`.
- Company Slack/internal comms stay off-limits.
- Never auto-publish to X or LinkedIn; produce drafts only until Tony explicitly confirms posting.

## GBrain verification pattern

For dated files:

```bash
gbrain put notes/memo/YYYY-MM-DD < /home/tonyxu/brain/notes/memo/YYYY-MM-DD.md
gbrain embed notes/memo/YYYY-MM-DD

gbrain put notes/work/memo/YYYY-MM-DD < /home/tonyxu/brain/notes/work/memo/YYYY-MM-DD.md
gbrain embed notes/work/memo/YYYY-MM-DD
```

For batches or after scheduled collectors, run:

```bash
gbrain embed --stale
gbrain stats
```

Verify with `gbrain get <slug>` or targeted search. Exact title search can miss; use distinctive body phrases. If `gbrain stats` shows `Embedded < Chunks`, run `gbrain embed --stale` before assuming search is current.
