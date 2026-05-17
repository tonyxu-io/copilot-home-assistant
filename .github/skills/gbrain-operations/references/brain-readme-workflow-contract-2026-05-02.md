# Brain README workflow contract — 2026-05-02

Session learning: Tony asked to re-review the latest brain/gbrain workflow and summarize it into `/home/tonyxu/brain/README.md`.

## Contract captured in README

- Brain repo is the canonical human-readable source.
- GBrain is the searchable/indexed memory layer.
- Raw capture comes first; curation and GBrain sync are downstream.
- Read priority: `people/` / `projects/` → `notes/` → compiled digests → raw `sources/` → `state/`.
- `memo` = general personal memo, not a content inbox for X/LinkedIn.
- `limemo` = work memo; `linote` is legacy.
- Content drafting is optional downstream use; never auto-publish.
- `notes/records/private/` must not be imported, embedded, indexed, or shared.
- Company Slack/internal comms are off-limits for personal automation.

## Update workflow

1. Load the governing skills first, especially `gbrain-operations`, `limemo-capture`, `memory`, and any content/social skill affected.
2. Inspect the current README and folder-specific READMEs before rewriting.
3. Rewrite `/home/tonyxu/brain/README.md` as the top-level operating contract, not just a directory listing.
4. Sync the README with:
   ```bash
   cd /home/tonyxu/brain
   gbrain put brain-readme < README.md
   gbrain embed brain-readme
   ```
   Use `gbrain embed --stale` only for batch reconciliation or when `gbrain stats` shows `Embedded < Chunks`.
5. Verify with:
   ```bash
   gbrain get brain-readme
   gbrain search "Brain repo is the canonical human-readable source" --limit 5
   gbrain stats
   ```
6. Healthy sync means `gbrain stats` works and `Embedded == Chunks` after embedding.

## DB outage retry pattern

If GBrain previously failed with `ECONNREFUSED`, retry in this order:

```bash
cd /home/tonyxu/brain
(timeout 3 bash -c '</dev/tcp/192.168.0.32/5433' && echo tcp_open) || echo tcp_closed_or_timeout
gbrain stats
```

Only run pending `gbrain put` / `embed` work after the TCP probe and `gbrain stats` succeed. If DB is still unavailable, keep the Markdown changes and report that only GBrain sync is blocked.
