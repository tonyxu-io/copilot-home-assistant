# GBrain Apple Notes reorganization notes

Session context: Tony asked to reorganize `/home/tonyxu/brain/sources/AppleNotes` into an optimized folder structure after Apple Notes had been imported into gbrain.

## Key lesson

Do **not** start with an aggressive content classifier for Apple Notes. The first dry-run used keyword rules and misfiled many LinkedIn/interview/work notes into family/admin buckets because terms like `LinkedIn`, `receipt`, `identity`, `meeting`, and `family` are overloaded. A safer approach is **folder-level normalization**:

- Collapse noisy top-level PARA/export folders into a small stable taxonomy.
- Preserve meaningful existing subfolders below the new bucket.
- Leave `Imported Notes/Root Notes` in an inbox for human review instead of guessing.

## Recommended structure

Under `/home/tonyxu/brain/sources/AppleNotes`:

- `00 Inbox/` — imported/root notes needing review
- `10 Family & Home/` — family, Han/Aaron, home, health, travel
- `20 Work & LinkedIn/` — LinkedIn work, career, interviews, oncall, work projects/resources/archive
- `30 Projects/` — personal projects not purely family/work library
- `40 Knowledge Library/` — tech, AI, reading, philosophy, writing, music, habits
- `50 Admin & Records/` — accounts, recovery, immigration, certificates, inventory, receipts, tickets, letters
- `60 Archive/` — past travel/archive material
- `_attachments/` — unchanged
- `_reports/` — reports/manifests only

## Safe workflow

1. Inspect current tree and counts:
   ```bash
   python3 - <<'PY'
   from pathlib import Path
   from collections import Counter
   root = Path('/home/tonyxu/brain/sources/AppleNotes')
   files = [p for p in root.rglob('*.md') if '_reports' not in p.parts]
   print(len(files))
   for k, v in Counter(p.relative_to(root).parts[0] for p in files).most_common():
       print(v, k)
   PY
   ```
2. Generate a **dry-run manifest** first. Check conflicts and sample moves before touching files.
3. Back up Markdown files outside the brain tree, e.g. `/home/tonyxu/.hermes/backups/apple-notes-backup-before-reorg-YYYY-MM-DD`. Do not place a full backup under `sources/AppleNotes/_reports`, or `gbrain import` will import duplicate backup pages.
4. Apply moves from the manifest. Preserve `_attachments/` unchanged.
5. Remove empty directories bottom-up.
6. Run normalizer:
   ```bash
   cd /home/tonyxu/brain
   python3 scripts/normalize_apple_notes_import.py
   ```
7. Reimport just Apple Notes:
   ```bash
   gbrain import /home/tonyxu/brain/sources/AppleNotes --no-embed --fresh
   gbrain embed --stale
   ```
8. Verify:
   ```bash
   gbrain stats
   gbrain get '00-inbox/root-notes/my-second-brain-in-apple-notes-para-method-part-4'
   gbrain get '20-work-linkedin/resources/curli-commands/adexperiments-qei'
   ```

## Pitfalls observed

- `gbrain import` imports every Markdown file under the target directory. If you store full backups in `_reports`, they become duplicate gbrain pages. Keep backups outside the brain source tree.
- `gbrain search` is keyword/FTS-ish and can miss obvious path-ish queries after reorg; verify exact moved pages with `gbrain get <slug>` when possible.
- `gbrain import --fresh` refreshed new moved paths but did not automatically delete old path-derived slugs created by previous imports. Filesystem may be clean while DB has stale old slugs. Flag this to Tony if search duplicates matter; do a focused stale-slug cleanup rather than broad destructive delete.
- `gbrain sync --help` unexpectedly executed sync work in this environment and timed out. Do not treat every `--help` as harmless for gbrain; prefer known docs/source inspection when unsure.
- `gbrain embed --stale` can be long-running and silent for stretches. Run in background, poll, and verify final `Embedded == Chunks` via `gbrain stats`.

## Result from the observed session

- Moved 532 Apple Notes Markdown notes with 0 conflicts.
- Final top-level counts excluding README/reports:
  - `20 Work & LinkedIn`: 333
  - `40 Knowledge Library`: 70
  - `00 Inbox`: 49
  - `10 Family & Home`: 46
  - `50 Admin & Records`: 30
  - `60 Archive`: 2
  - `30 Projects`: 2
- `gbrain import /home/tonyxu/brain/sources/AppleNotes --no-embed --fresh` imported 536 pages, 0 skipped, 0 errors, 656 chunks.
- `gbrain embed --stale` completed with all chunks embedded.
