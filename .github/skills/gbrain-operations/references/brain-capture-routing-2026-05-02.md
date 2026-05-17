# Brain capture routing clarification — 2026-05-02

Use this when reviewing or updating Tony's `/home/tonyxu/brain` capture workflow.

## Session learning

Tony asked to clarify how captured material should route after the brain workflow review. The durable contract was updated in:

- `/home/tonyxu/brain/README.md`
- `/home/tonyxu/brain/notes/memo/README.md`
- `/home/tonyxu/brain/notes/work/memo/README.md`

Then synced with:

```bash
gbrain put brain-readme < README.md
gbrain embed brain-readme
gbrain put notes/memo/readme < notes/memo/README.md
gbrain embed notes/memo/readme
gbrain put notes/work/memo/readme < notes/work/memo/README.md
gbrain embed notes/work/memo/readme
gbrain embed --stale
gbrain stats
```

Verification target: `Embedded == Chunks`; exact semantic search may miss, so prefer `gbrain get` plus grep for distinctive phrases.

## Capture model

Capture has two steps:

1. **Raw capture** — preserve original text/link/export first, with date and provenance.
2. **Routing / promotion** — only promote when the item is durable, searchable, actionable, or useful for writing later.

Do not over-route. If destination is unclear, keep raw capture only or add a one-line candidate to `notes/unsorted/_promotion_queue.md`.

## Routing table

Use the first matching destination:

- Tony's general thought/link/reminder/prompt/decision/taste/rough idea → raw `notes/memo/YYYY-MM-DD.md`; promote only if useful.
- Tony's work raw note → raw `notes/work/memo/YYYY-MM-DD.md`; trigger is `limemo`, legacy `linote` is retired; promote only if durable and safe.
- Person fact → `people/<person>.md` with dated source/timeline note; raw memo first if it arrived as a casual fragment.
- Project fact/status/decision/next step → `projects/<project>.md`; raw memo first if fragmentary. For family/home project working notes, `notes/family/home/...` may be the better human-readable home.
- Family/home/health/travel/parenting → `notes/family/...`.
- Admin/reference record → non-private `notes/records/...`; private/sensitive `notes/records/private/...` but never import/embed/share that subtree.
- External article/video/transcript/podcast/paper/web page Tony asks to save → curated note under `notes/knowledge/...` unless another bucket is clearly better; include source metadata, Tony stance, and `My read / key thesis`.
- Writing direction/voice/style/draft/publishable angle/content backlog → `notes/writing/...`; drafts go to `notes/writing/content-drafts/YYYY-MM-DD.md`; activity synthesis goes to `notes/writing/activity-inspiration/YYYY-MM-DD.md`.
- Passive likes/favorites/saves/listening/watch history → raw/source export in `sources/<platform>/...`; daily ledger in `daily/activity/YYYY/YYYY-MM-DD.md`, date-sharded by content generation date when possible; treat as taste/ranking evidence, not Tony-authored claims or endorsement.
- Useful but unclear source-derived item → `notes/unsorted/_promotion_queue.md` with source path/link and one-line reason.

## Pitfalls

- Do not treat `notes/memo/` as a content inbox. Writing is downstream only.
- Do not auto-promote every memo into a structured note; raw preserved context is a valid final state.
- Do not import/embed `notes/records/private/` or broad `notes/records/`.
- Do not rely only on `gbrain search`; exact title/phrase search can miss even when pages are correctly embedded.
