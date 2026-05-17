# Brain writing taxonomy correction — 2026-05-02

Session lesson: Tony corrected that `writing` should not live under `notes/knowledge/`.

## Current rule

- `notes/knowledge/` is for learning/reference domains: AI, tech, reading, philosophy, music, photography, source maps.
- `notes/writing/` is a top-level workbench for writing direction, style references, drafts, publishable ideas, and personal writing.
- Daily X / LinkedIn drafts belong at:
  ```text
  /home/tonyxu/brain/notes/writing/content-drafts/YYYY-MM-DD.md
  ```
- `memo` may feed writing only after raw capture and public/private review.

## Migration applied

- Moved `notes/knowledge/writing/` → `notes/writing/`.
- Added `notes/writing/README.md` and `notes/writing/content-drafts/README.md`.
- Updated brain README, notes README, knowledge README, memo README, LinkedIn workflow docs, limemo capture docs, memory routing docs, daily content editor cron prompt, and `scripts/reorganize_apple_notes.py`.
- Synced key docs to GBrain with `gbrain put` + `gbrain embed <slug>`.

## Verification pattern

```bash
cd /home/tonyxu/brain
rg "notes/knowledge/writing|knowledge/writing|AI, tech, writing|Personal learning, technical thinking, writing" README.md notes .hermes/skills scripts || true
gbrain get writing-readme
gbrain stats
```

Expected: no live workflow references to `notes/knowledge/writing`; `Embedded == Chunks` after any stale reconciliation.
