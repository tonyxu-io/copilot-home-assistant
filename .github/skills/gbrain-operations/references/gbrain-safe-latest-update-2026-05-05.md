# Safe “update GBrain to latest” runbook — 2026-05-05

## When this applies

Tony asks to update GBrain to the latest/current state, and the brain repo may include sensitive local records plus large historical source trees.

## Proven sequence

1. Work from `/home/tonyxu/brain`.
2. Verify CLI availability and baseline stats:
   ```bash
   which gbrain && gbrain stats
   ```
3. Protect sensitive/private material before imports:
   - Ensure `notes/records/secrets/` is ignored by git.
   - Do **not** import/embed secrets, raw credentials, raw social mirrors, `state/`, staging, or backup trees.
4. Prefer scoped imports over broad full-tree imports. Safe high-value targets include:
   ```bash
   gbrain import /home/tonyxu/brain/people --no-embed
   gbrain import /home/tonyxu/brain/projects --no-embed
   gbrain import /home/tonyxu/brain/sources/gmail/digests --no-embed
   gbrain import /home/tonyxu/brain/sources/calendar/digests --no-embed
   # curated notes: import narrow safe subfolders or individual files with gbrain put
   ```
5. If a broad import times out (observed: 600s timeout), treat that as a signal to narrow scope, not to repeat blindly.
6. Refresh embeddings to closure:
   ```bash
   gbrain embed --stale
   gbrain stats
   ```
7. Verify:
   - `Embedded == Chunks` in `gbrain stats`.
   - Targeted searches for recent known pages/phrases work.
   - Sensitive secrets do not show up in search.

## Session result example

Final successful closure:

```text
Embedded 3268 chunks across 2964 pages
[embed.pages] 2964/2964 (100%) done
Pages:     34032
Chunks:    45037
Embedded:  45037
Links:     330
Tags:      302
Timeline:  167
```

## Pitfalls

- `gbrain import` can be slow enough to hit a 600s timeout on broad safe-directory scans; narrowing to digest/source dirs plus stale embedding can still bring embeddings fully current.
- Do not expose or reprint sensitive insurance/member IDs when confirming completion.
- `notes/records/secrets/` may intentionally exist in the brain filesystem while being absent from GBrain index/search/embeddings. That is the desired privacy boundary.
