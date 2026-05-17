# Archived source: `gbrain-postgres-reinit-and-import`

Postgres reinitialization and reimport are gbrain infrastructure operations.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-postgres-reinit-and-import`

---

Use when gbrain drifted to PGlite, the user wants self-hosted Postgres restored, or imports behave strangely under Hermes terminal execution.

## Principles
- Trust the live config file over memory or chat history.
- Do not assume `gbrain` is unavailable until you reload an interactive bash shell.
- Import a specific readable content directory, not a broad home directory.
- Treat `tcsetattr`, `ioctl`, and timeout noise during `gbrain import` as possible TTY/progress-rendering issues; verify actual DB progress before declaring failure.

## Steps
1. Verify current config.
   - `read_file ~/.gbrain/config.json`
   - Check whether `engine` is `pglite` or `postgres`.

2. Reload bash interactively and verify CLI path.
   - Use `bash -lic 'type -a gbrain; which gbrain; gbrain --help | head -n 60'`
   - Reason: `source ~/.bashrc` in a non-interactive shell may miss PATH changes; in this case gbrain lived at `/home/tonyxu/.bun/bin/gbrain` and only showed up reliably with `bash -lic`.

3. Re-init against Postgres.
   - Ensure `GBRAIN_DATABASE_URL` is present from `~/.bashrc`.
   - Run: `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain init --url "$GBRAIN_DATABASE_URL"'`
   - Expect many harmless `already exists, skipping` notices if the schema already exists.

4. Verify live state after init.
   - `read_file ~/.gbrain/config.json`
   - `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain doctor --json'`
   - `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain stats'`
   - Confirm config shows `engine: postgres` and the expected database URL.

5. Reimport carefully.
   - First discover a specific markdown directory with file tools.
   - Do NOT run `gbrain import . --fresh` from `/home/...` unless you want permission errors and junk.
   - Prefer a narrow target such as `/home/tonyxu/tony-assistant-backup/openclaw/notes`.
   - Command: `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain import /path/to/notes --fresh --json'`

6. If import hangs or times out with TTY noise, verify progress before retrying.
   - Symptoms seen: `tcsetattr: Inappropriate ioctl for device`, timeout after showing `Found N markdown files`.
   - Immediately run `gbrain stats` to see whether pages/chunks increased.
   - If counts increased, the importer was making progress despite ugly shell behavior.
   - Best next move is background/PTY execution for the import if a clean finish is needed.

7. Prefer PTY background execution for flaky imports.
   - Use terminal background mode with `pty=true`, for example:
     `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain import /path/to/notes --fresh --json'`
   - Then poll or wait on the process instead of assuming the foreground timeout means failure.
   - This is the least stupid way to handle CLIs that render progress or touch terminal state.

8. For long-running imports, automatically schedule progress updates.
   - Create a cron job that runs every 5 minutes and reports back to the origin Telegram chat.
   - Each cron run should:
     1) poll the import process session id,
     2) run `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain stats'` in the repo/workdir,
     3) send a short plain-text update with running/finished status, uptime if available, and current Pages/Chunks.
   - Do NOT rely on the cron-run agent to successfully delete itself every time. Cron sessions are isolated, and self-removal via prompt is fragile.
   - Safer pattern: create the cron with a finite repeat count, let it send progress, and when the finished notification lands in the main chat, explicitly remove the cron job from the main session.
   - Default to doing this every time for Tony on long gbrain imports so he does not have to babysit the process.

## Pitfalls
- Non-interactive `bash -lc` may still say `gbrain: command not found` even after PATH was updated; use `bash -lic`.
- Previous chat claims about gbrain state can be wrong. Check `~/.gbrain/config.json` first.
- Importing from the home directory can fail on unreadable folders like `docker/immich/postgres`.
- `doctor` may report embeddings as warn-only; that is not a Postgres or schema failure.
- `gbrain init` with no `--url` follows upstream's PGLite default and can silently rewrite `~/.gbrain/config.json` away from Tony's self-hosted Postgres. When updating via INSTALL_FOR_AGENTS.md, still run Tony's Postgres init afterward: `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain init --url "$GBRAIN_DATABASE_URL"'`, then verify `gbrain config show` says `engine: postgres`.
- After a newer install, `gbrain doctor --json` may fail only on RLS for new code-edge tables (`code_edges_chunk`, `code_edges_symbol`) even while `schema_version` is already latest. If `gbrain doctor --fix` does not repair it, use a local Bun script from `/home/tonyxu/gbrain` that loads config without printing the DB URL and runs:
  ```sql
  ALTER TABLE "public"."code_edges_chunk" ENABLE ROW LEVEL SECURITY;
  ALTER TABLE "public"."code_edges_symbol" ENABLE ROW LEVEL SECURITY;
  ```
  Verify `doctor` then says `RLS enabled on ... public tables`.
- For v0.12.2+ Postgres JSONB drift, run `gbrain repair-jsonb --dry-run --json` after upgrade. If it reports rows, run `gbrain repair-jsonb`, then repeat dry-run and expect `total_repaired: 0`.
- v0.22.4 frontmatter guard is audit-only. It can report thousands of `MISSING_OPEN` issues and queue `gbrain frontmatter validate /home/tonyxu/brain --fix`. Do **not** auto-run `--fix` without Tony's consent because it mutates many brain markdown files and creates `.bak` backups.
- `gbrain extract links --source db --dry-run --json` and `gbrain features --json --auto-fix` can run for minutes on Tony's 24k-page brain and may leave long-running processes after caller timeout. Check and kill stray `gbrain extract` / `gbrain features` processes before starting new verification.
- Direct DB checks can disagree with CLI embedding counts: in one upgrade, `gbrain doctor`/`health` reported 100% coverage while direct SQL still found old rows with `embedding IS NULL` and `embedded_at IS NOT NULL`. Do not leave it as “just a quirk” if Tony asks to fix warnings. Safe repair pattern:
  1. Count rows with a local Bun script from `/home/tonyxu/gbrain` using `loadConfig()` and never printing the DB URL:
     ```sql
     SELECT count(*)::int total,
            count(*) FILTER (WHERE embedding IS NULL)::int nulls,
            count(*) FILTER (WHERE embedding IS NULL AND embedded_at IS NOT NULL)::int contradictory
     FROM content_chunks;
     ```
  2. Clear only the false marker:
     ```sql
     UPDATE content_chunks
     SET embedded_at = NULL
     WHERE embedding IS NULL AND embedded_at IS NOT NULL;
     ```
  3. Run `bash -lc '. ~/.bashrc; GBRAIN_EMBED_CONCURRENCY=4 gbrain embed --stale'` as a tracked background process with `pty=true`, `notify_on_complete=true`, and watch patterns for real embedding/rate-limit errors. Do not use a broad `"429"` watch pattern because progress like `429/2833` is a false positive; use `"429 Too Many Requests"`.
  4. Let it finish; a 2.8k-page stale embed can take ~20 minutes. Final expected checks: `gbrain doctor` says embeddings `100% coverage, 0 missing`, `gbrain stats` has `Embedded == Chunks`, and direct SQL `embedding IS NULL` count is `0`.
- A hard failure like `Cannot connect to database: write CONNECT_TIMEOUT 192.168.0.32:5433. Fix: Check your connection URL in ~/.gbrain/config.json` means exactly what it says: treat it as live Postgres reachability or wrong-URL drift, not a markdown/import-data problem. Check `~/.gbrain/config.json`, compare it against the intended self-hosted Postgres URL, and verify the host/port is reachable before retrying imports.
- When upgrading gbrain across schema versions, import failures like `there is no unique or exclusion constraint matching the ON CONFLICT specification` can mean a migration ledger/schema drift issue, not bad markdown. For Postgres, inspect the unique constraints and indexes before rerunning imports.
- For newer gbrain source-aware imports, `pages` needs `UNIQUE (source_id, slug)` (`pages_source_slug_key`) in addition to the legacy `UNIQUE (slug)`. Safe repair pattern:
  1. Check duplicates:
     ```sql
     SELECT slug, source_id, count(*)::int n
     FROM pages
     GROUP BY slug, source_id
     HAVING count(*) > 1;
     ```
  2. If zero rows, add the constraint idempotently:
     ```sql
     DO $$ BEGIN
       IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='pages_source_slug_key') THEN
         ALTER TABLE pages ADD CONSTRAINT pages_source_slug_key UNIQUE (source_id, slug);
       END IF;
     END $$;
     ```
  3. Rerun the failed `gbrain import ... --no-embed --json` and verify `errors: 0`.
- A foreground timeout during `gbrain import` does not prove the import failed; check stats or run it under PTY/background mode.
- `gbrain import` may print only `Found N markdown files` for a long time with no per-file progress. Do not fake a remaining-count estimate unless the CLI actually exposes one.
- The honest progress signal is repeated `gbrain stats` snapshots (Pages/Chunks increasing), not the stuck-looking importer output.
- When importing a broad sources tree (for example `/home/tonyxu/brain/sources`), run any normalizer scripts first if they exist, but expect them to be no-ops on already-clean Apple Notes / Notion exports.
- Large imports can look frozen for a long time with output stuck at `Found N markdown files`; verify progress with repeated `gbrain stats` before killing the process.
- Gmail backfill collector output lives under `/home/tonyxu/brain/sources/gmail/digests`. If Tony asks to import the new Gmail pages, import that digest directory directly instead of the whole `sources/` tree.
- In one live run, `gbrain import /home/tonyxu/brain/sources/gmail/digests --json` reported only `Found 186 markdown files` for minutes, while `gbrain stats` still advanced from `Pages 17660 / Chunks 25150` to `Pages 17662 / Chunks 25154`. Treat that as real progress, not a hang.
- For source ingests under `/home/tonyxu/brain/sources`, run the normalizer scripts first: `python3 /home/tonyxu/brain/scripts/normalize_apple_notes_import.py` and `python3 /home/tonyxu/brain/scripts/normalize_notion_import.py`.
- When importing `/home/tonyxu/brain/sources` or collector digest directories, prefer `terminal(..., background=true, pty=true, notify_on_complete=true)` plus `process poll/wait`; this CLI is slow enough that pretending it's done would be bullshit.
- Deterministic collector output under `/home/tonyxu/brain/data/notion` is not a full Notion mirror for gbrain. Today it contains JSON plus only two markdown digests (`family/digest.md`, `personal/digest.md`), so `gbrain import /home/tonyxu/brain/data/notion --no-embed` imports only those digest markdown files unless a separate JSON-to-Markdown normalization step is added.
- Before importing Notion-related content, inspect the target path with file tools instead of assuming it is the old `sources/Notion` mirror. In this repo the legacy `sources/Notion` path was absent, while the active collector wrote to `data/notion/...` and `state/notion_state.json`.

## Verification checklist
- First clear stale long-running verification jobs from prior attempts: `ps -eo pid,etime,cmd | grep -E 'gbrain (embed|features|extract|import|sync|doctor|query)' | grep -v grep || true`; kill only confirmed stray gbrain processes.
- `~/.gbrain/config.json` contains `engine: postgres`.
- `database_url` points to the intended self-hosted Postgres host/port/db; redact it in all user-facing output.
- Active CLI is the linked checkout: `which gbrain`, `gbrain --version`, `readlink -f $(which gbrain)`; expected shape after latest install is `~/.bun/bin/gbrain -> /home/tonyxu/gbrain/src/cli.ts`.
- Copilot embedding env survives non-interactive shells: `GBRAIN_EMBEDDING_PROVIDER=copilot`, `GBRAIN_EMBEDDING_MODEL=metis-1024-I16-Binary`, `GBRAIN_EMBEDDING_DIMENSIONS=1024`, `GBRAIN_EMBED_CONCURRENCY=1`.
- `gbrain apply-migrations --list` and `gbrain apply-migrations --yes --non-interactive` show all migrations up to date.
- `gbrain doctor --json` exits 0 and shows connection/pgvector/RLS/schema_version/jsonb_integrity ok. Warnings for frontmatter/graph coverage are content hygiene, not setup failure.
- `gbrain repair-jsonb --dry-run --json` reports `total_repaired: 0` after any upgrade repair.
- `gbrain health`, `gbrain stats`, and a real `gbrain query "Tony LinkedIn ADU" --limit 3` work.
- For DB-level sanity without leaking credentials, run a Bun script from `/home/tonyxu/gbrain` that imports `loadConfig()` and queries: RLS status for `pages`, `content_chunks`, `code_edges_chunk`, `code_edges_symbol`; config rows for `version`, `embedding_provider`, `embedding_model`, `embedding_dimensions`; and aggregate `content_chunks` embedding counts.
- After import, page/chunk counts increase compared with pre-import stats.
