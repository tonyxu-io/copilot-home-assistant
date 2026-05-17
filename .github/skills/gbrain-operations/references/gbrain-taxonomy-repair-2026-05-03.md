# GBrain taxonomy repair — 2026-05-03

## Problem

Tony asked why GBrain showed only ~77 `type=note` pages while `/home/tonyxu/brain/notes/**/*.md` had hundreds of Markdown files. Root cause was a mix of:

- `type` is a DB taxonomy field, not a filesystem count.
- Many brain repo Markdown files were never imported after repo reorganization/backfills.
- Imported provenance under `sources/gmail` and `sources/calendar` was over-bucketed as generic `source` instead of `email` / `calendar-event`.

## Safe repair approach

Prefer a deterministic repo-local script over broad `gbrain sync` or wide search queries:

1. Inventory DB by `slug` prefix and `type` using Postgres direct queries.
2. Compare path-derived slugs from safe Markdown files to existing `pages.slug`.
3. Normalize existing rows by ordered path-prefix rules:
   - `people/` → `person`
   - `projects/` → `project`
   - `sources/gmail/` → `email`
   - `sources/calendar/` → `calendar-event`
   - `daily/activity/` and `daily/calendar/` → `source`
   - `notes/writing/` → `writing`
   - `notes/work/people/` → `person`
   - `notes/work/projects/` → `project`
   - broad `notes/` → `note`
4. Import missing safe Markdown with GBrain's own `importFile(engine, fullPath, relPath, { noEmbed: true })` rather than reimplementing parsing/chunking.
5. After import, update the imported page type if the parser inferred a broader/wrong type.
6. Add an explicit `--purge-excluded` mode for already-indexed excluded prefixes. It should delete DB pages whose slugs begin with `notes/records/secrets/`, `state/`, `sources/x-likes/`, `sources/x-posts/`, YouTube raw mirror prefixes, or XHS raw mirror prefixes. Verify with a dry-run count before applying.
7. Defer embeddings: run `gbrain embed --stale` after the batch if needed.

## Safety exclusions

Never import or normalize these during taxonomy repair:

- `notes/records/secrets/**`
- `state/**`
- symlinks
- hidden paths
- `.raw/` sidecars
- oversized files above GBrain's import guard
- raw social/source mirrors that may contain token-like URL query strings, especially `sources/x-likes/**`, `sources/x-posts/**`, YouTube raw mirrors, XHS raw mirrors

Daily/activity pages are the safe rollup for social activity; raw mirrors are provenance and need separate approval before indexing.

## Pitfalls found

- `gbrain sync --help` unexpectedly executed sync work in this environment. Do not assume per-command help is harmless; inspect source or use very narrow commands.
- `bun --check` / `bun --syntax-only` may run a shebang script enough to trigger its argument parser, causing a usage exit instead of a pure TypeScript validation. For one-off TS scripts, validate by running a dry-run mode with safe flags instead.
- `gbrain embed --stale` can take a long time and its process output may appear stale between bursts. Track it with a background process plus periodic `gbrain stats`; if you must stop and restart after DB cleanup, expect the stale page count to shrink and the new run to resume from the remaining chunks.
- Broad `gbrain search "notes/"` can hit Postgres statement timeouts. Use exact `gbrain get`, DB prefix counts, or `gbrain list --type` instead.
- `gbrain sync` uses git diff anchors and can attempt huge delete/rename/import sets after repo reorg. Avoid it for taxonomy-only repair unless intentionally reconciling the whole repo.
- `gbrain import` / sync collection does not automatically honor repo `.gitignore` for secrets; guard exclusions explicitly in repair scripts.
- Long imports with no progress output are hard to supervise. Future repair scripts should emit periodic progress to stderr and support resume/batch limits.

## Verification checklist

- `gbrain stats` shows expected type buckets; `note` should track imported `notes/**` pages, not raw filesystem total unless all notes were safely imported.
- Targeted DB prefix counts match filesystem counts for safe prefixes within expected exclusions.
- Excluded-prefix DB counts are zero after purge: `notes/records/secrets/%`, `state/%`, `sources/x-likes/%`, `sources/x-posts/%`, YouTube raw mirror prefixes, and XHS raw mirror prefixes. In the 2026-05-03 run, 40 stale `state/rebuild_backups/...` pages were found and purged.
- `gbrain get <sample-slug>` works for examples from `notes/`, `notes/writing/`, `daily/activity/`, `sources/gmail/`, and `sources/calendar/`.
- `notes/records/secrets/%` count is zero or unchanged and never newly imported.
- `Embedded == Chunks` after `gbrain embed --stale`, if embeddings were deferred.
- Commit the repair script and any intentional Markdown changes separately if possible.
