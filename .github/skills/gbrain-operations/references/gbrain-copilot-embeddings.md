# Archived source: `gbrain-copilot-embeddings`

Copilot embedding repair is an embeddings/provider subsection of gbrain operations.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-copilot-embeddings`

---

# gbrain Copilot Embeddings

Use when Tony asks to make gbrain use GitHub Copilot embedding models, avoid OpenAI quota, repair embedding failures, or re-embed gbrain with Copilot.

## Context

Tony's active `gbrain` command may come from Bun global install, not necessarily `/home/tonyxu/gbrain` checkout.
Known-good CLI path in this environment was:

- `~/.bun/bin/gbrain`
- real source: `~/.bun/install/global/node_modules/gbrain/src/cli.ts`
- version seen: `gbrain 0.9.2`

Do not print GitHub/Copilot/OpenAI tokens, DB URLs, cookies, or auth headers. Redact as `[REDACTED]`.

## Workflow

1. Locate the active CLI first.
   - `which gbrain`
   - `gbrain --version`
   - `readlink -f $(which gbrain)`
   - If global package is active, inspect `~/.bun/install/global/node_modules/gbrain`.
   - Also check `/home/tonyxu/gbrain` git status if upstreamable changes matter.

2. Inspect embedding-related source.
   - `src/core/embedding.ts`
   - `src/core/config.ts`
   - `src/core/import-file.ts`
   - `src/commands/embed.ts`
   - `src/core/search/hybrid.ts`
   - `src/cli.ts`
   - pgvector schema/migration files if dimensions must change.

3. Confirm Copilot endpoint and auth without leaking credentials.
   - Local Copilot CLI config may exist at `~/.copilot/config.json`.
   - Parse it only in scripts that redact output.
   - Do not print tokens.
   - The endpoint discovered working for embeddings was `https://api.github.com/embeddings` with header `X-GitHub-Api-Version: 2025-05-01`.
   - Model: `metis-1024-I16-Binary`.
   - Dimensions: `1024`.

4. Use TDD.
   - Add focused tests for provider selection/request formatting before implementation.
   - For Copilot, mock `fetch` and expect:
     - POST `https://api.github.com/embeddings`
     - body `{ inputs: [...], model: "metis-1024-I16-Binary" }`
     - `X-GitHub-Api-Version: 2025-05-01`
     - result vectors length `1024`
   - For generic OpenAI-compatible providers, mock env and `fetch` and expect:
     - POST `<GBRAIN_EMBEDDING_BASE_URL without trailing slash>/embeddings`
     - `Authorization: Bearer <api key>` without logging the real key
     - body `{ input: [...], model: <configured model>, dimensions: <configured dimensions> }`
     - OpenAI-style response parsing from `data[].embedding`, preserving response `index` ordering.
   - Watch at least one test fail before production code when feasible.

5. Implement provider wiring generically, not as a one-off Copilot branch.
   - Prefer a provider config layer/registry with at least:
     - `openai`
     - `openai-compatible`
     - `copilot`
   - Generic OpenAI-compatible envs should include:
     - `GBRAIN_EMBEDDING_PROVIDER=openai-compatible`
     - `GBRAIN_EMBEDDING_BASE_URL=https://provider.example/v1`
     - `GBRAIN_EMBEDDING_API_KEY=...`
     - `GBRAIN_EMBEDDING_MODEL=<model>`
     - `GBRAIN_EMBEDDING_DIMENSIONS=<dims>`
     - optional `GBRAIN_EMBEDDING_BATCH_SIZE=<n>`
   - Keep backward-compatible aliases where useful, e.g. `GBRAIN_OPENAI_COMPATIBLE_BASE_URL`, `GBRAIN_OPENAI_COMPATIBLE_API_KEY`, `GBRAIN_OPENAI_EMBEDDING_MODEL`, `GBRAIN_OPENAI_EMBEDDING_DIMENSIONS`, and `GBRAIN_COPILOT_EMBEDDING_MODEL`.
   - Support provider envs such as `GBRAIN_EMBEDDING_PROVIDER=copilot` / `EMBEDDING_PROVIDER=copilot`.
   - Copilot token order can be:
     1. `GBRAIN_COPILOT_TOKEN`
     2. `COPILOT_GITHUB_TOKEN`
     3. `GH_TOKEN`
     4. `GITHUB_TOKEN`
     5. parsed `~/.copilot/config.json`
   - Keep OpenAI as fallback/default where already expected.
   - For OpenAI-compatible providers, call `${baseUrl.replace(/\/$/, '')}/embeddings` using OpenAI-style body `{ input, model, dimensions }` and parse OpenAI-style `data[].embedding` responses sorted by `index`.
   - For Copilot, call GitHub’s `/embeddings` endpoint with `{ inputs, model }`, batch conservatively, normalize vectors if needed, and handle retry-after on errors.

6. Propagate model metadata.
   - Import/write paths should store model metadata including dimensions, e.g. `metis-1024-I16-Binary:1024`.
   - Existing OpenAI metadata may be `text-embedding-3-large:1536`.
   - `embed` command should update model metadata when it refreshes embeddings.

7. Handle pgvector dimensions deliberately.
   - OpenAI existing column is likely `vector(1536)`.
   - Copilot Blackbird is `vector(1024)`.
   - Add a command or migration path that:
     - smoke-tests Copilot embedding first;
     - drops/recreates vector index;
     - clears old embeddings;
     - alters `content_chunks.embedding` to `vector(1024)`;
     - stores config keys such as `embedding_provider`, `embedding_model`, `embedding_dimensions`.
   - For upstreamable PR fixes, a robust pattern is:
     - export a `parseEmbeddingDimensions(value, fallback)` helper from `src/core/embedding.ts` instead of duplicating env parsing;
     - add an `embedding-schema` helper that resolves current env/model config and emits session-local settings, e.g. `SET gbrain.embedding_dimensions = '1024'; SET gbrain.embedding_model = 'metis-1024-I16-Binary';`;
     - call the schema-settings helper before executing embedded schema SQL in both `PostgresEngine.initSchema()` and `PGLiteEngine.initSchema()`, so new DBs run migrations with the intended dimension even though `schema-embedded.ts` / `pglite-schema.ts` still contain static `vector(1536)`;
     - add a migration that reads `current_setting('gbrain.embedding_dimensions', true)`, drops `idx_chunks_embedding`, clears old embeddings (`embedding = NULL`, `embedded_at = NULL`), alters `content_chunks.embedding TYPE vector(<configured_dimensions>)`, recreates the HNSW index, and writes `embedding_model` / `embedding_dimensions` config keys;
     - add an `upsertChunks` guard in both Postgres and PGLite engines that rejects vectors whose `Float32Array.length` differs from the configured dimension before hitting DB errors.
   - Warn Tony that page data is preserved but old embeddings are cleared and must be regenerated.

8. Watch for Bun/runtime and test module-cache pitfalls.
   - Tests that import `src/core/embedding.ts` after changing env may see stale exported constants.
   - Use query-suffixed dynamic imports in tests, e.g. `../src/core/embedding.ts?copilot-test-1`.
   - Existing tests that mock `../src/core/embedding.ts` must export any newly required named exports such as `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, and `getEmbeddingProvider`.
   - Add `mock.restore()` carefully; mocks can leak across files.
   - In live CLI code, avoid relying on module-scope `EMBEDDING_MODEL` / `EMBEDDING_DIMENSIONS` after setting `process.env.GBRAIN_EMBEDDING_PROVIDER` inside the same process. Dynamic import may still see constants initialized before the env flip. For commands like `use-copilot-embeddings`, call functions such as `getEmbeddingModel()` and `getEmbeddingDimensions()` after setting env, and compare smoke-test vector length against those function results.
   - `bun --check file1 file2` may be parsed oddly in this global package context; if it routes to `gbrain` or prints `Unknown command`, use targeted `bun test` and CLI smoke tests as the source of truth.

9. Install a PR branch and verify/re-embed.
   - If asked to install the PR branch globally, first verify it is based on latest upstream (`git fetch origin --prune`, compare `origin/master..HEAD`, run targeted tests). In this environment the branch `feat/copilot-embeddings` installed as `gbrain 0.21.0` from `github:tonyxu-io/gbrain#feat/copilot-embeddings`.
   - `bun add -g github:tonyxu-io/gbrain#feat/copilot-embeddings` may fail with a Bun dependency-loop if the existing global `~/.bun/install/global/package.json` has `gbrain: github:garrytan/gbrain`. Fix by removing first, then adding: `bun remove -g gbrain && bun add -g github:tonyxu-io/gbrain#feat/copilot-embeddings`.
   - After install, confirm the active binary and provider support: `which gbrain`, `gbrain --version`, `readlink -f $(which gbrain)`, and grep the installed `src/core/embedding.ts` for `GBRAIN_EMBEDDING_PROVIDER` / `copilot`.
   - Persist Tony's Copilot embedding env in `~/.bashrc` when this is meant to be the default runtime: `GBRAIN_EMBEDDING_PROVIDER=copilot`, `GBRAIN_EMBEDDING_MODEL=metis-1024-I16-Binary`, `GBRAIN_EMBEDDING_DIMENSIONS=1024`, and use conservative `GBRAIN_EMBED_CONCURRENCY=1` for Copilot rate limits.
   - Put those env exports **before** `.bashrc`'s non-interactive-shell guard/`return`; otherwise Hermes/cron/non-interactive `bash -lc` sessions will not inherit them even though an interactive shell does. Verify with `bash -lc '. ~/.bashrc; printf "%s\n" "$GBRAIN_EMBEDDING_PROVIDER"'`.
   - Run targeted tests first, e.g. Copilot embedding test, embed tests, config tests, import-file tests, CLI tests, pglite engine tests.
   - Full `bun test` may include unrelated network/update timeout noise; distinguish new regressions from pre-existing flakes.
   - Run `bun install` in `/home/tonyxu/gbrain` before targeted tests if dependencies like `marked` are missing. Its postinstall may print a non-blocking `gbrain apply-migrations` failure if the active global `gbrain` is older.
   - Run `bun run typecheck` after adding query-suffixed dynamic imports in tests. TypeScript cannot resolve literal imports such as `../src/core/embedding.ts?copilot-test-1`; use a helper that returns `import(
     `../src/core/embedding.ts?${suffix}`
   ) as Promise<typeof import('../src/core/embedding.ts')>` instead. Also cast mocked `fetch` as `unknown as typeof fetch` because Bun's fetch type has extra static members.
   - When a test file mocks `../src/core/embedding.ts`, any new named export used indirectly by new helper modules must be included in the mock. Example: after adding `parseEmbeddingDimensions`, `test/embed.test.ts` needed its embedding mock to export it or unrelated multi-file test runs failed with `Export named 'parseEmbeddingDimensions' not found` even though the focused test passed.
   - Run live smoke tests without printing secrets:
     - `gbrain use-copilot-embeddings` — expect `Copilot embeddings enabled: metis-1024-I16-Binary (1024 dimensions)`.
     - `gbrain health` — confirms coverage/missing counts without exposing credentials.
   - Then re-embed in the background, conservatively:
     - `GBRAIN_EMBED_CONCURRENCY=4 gbrain embed --all`
     - Use Hermes `terminal(background=true, notify_on_complete=true, watch_patterns=["Error embedding", "embedding failed", "Copilot embeddings request failed", "quota", "rate"])`.
     - If `Error embedding ... 429 Too Many Requests` appears but the process eventually exits 0, run `GBRAIN_EMBED_CONCURRENCY=1 gbrain embed --stale` to finish only the missing chunks. This is slow because it scans all pages, but it successfully converges after rate-limit misses.
     - Poll `gbrain health` for progress; large brains may run for many minutes. No CLI output is normal because `embed --all` updates with carriage returns and background buffering may hide progress.
   - Verify stored embedding length/model metadata through safe DB queries with credentials redacted if needed.
   - If `gbrain embed <slug>` says chunks are already embedded, it will not refresh metadata. For a live Copilot smoke, clear one known page's chunk embeddings safely (`UPDATE content_chunks SET embedding = NULL, embedded_at = NULL WHERE page_id = (SELECT id FROM pages WHERE slug='<safe-slug>' LIMIT 1)`), then run `gbrain embed --slugs <safe-slug>` and verify the row model is `metis-1024-I16-Binary:1024` and column type is `vector(1024)`.

10. Repair stale DB schema after jumping from old global gbrain to a newer PR branch.
   - Symptom: after installing the PR branch, `gbrain query` or `gbrain apply-migrations --yes` fails with missing columns such as `pages.source_id`, `links.link_source`, `ingest_log.source_id`, or `minion_jobs.quiet_hours`, while `gbrain health` may still partly work.
   - First probe schema safely using the DB URL from `~/.gbrain/config.json` inside a script that redacts output. Check at least: `config.version`, `sources` table, `pages.source_id`, `pages.page_kind`, `content_chunks` embedding type, code edge tables, links provenance columns, ingest_log source_id, and minion job parity columns.
   - `psql` may not be installed; use a Bun script from the `/home/tonyxu/gbrain` repo so `postgres` resolves from local deps. Never print the DB URL.
   - If the schema is stale but the tables already contain data, use **idempotent additive repairs only**: create `sources` + default source; add `pages.source_id` / `page_kind`; add code chunk metadata/search columns and code edge tables; add links provenance columns; add `ingest_log.source_id`; add minion job parity columns including `quiet_hours` / `stagger_key`; set config keys `embedding_provider`, `embedding_model`, `embedding_dimensions`, and `version`.
   - Avoid long full-table backfills in foreground. A search_vector backfill over all chunks timed out at 600s; adding the column/trigger/index without immediate backfill was enough for operational recovery.
   - After verifying current CLI operations, repair `~/.gbrain/migrations/completed.jsonl` by appending `status:"complete"` entries for migrations that are truly satisfied. This clears stale `partial` migration warnings; do not do it before schema checks pass.
   - `gbrain apply-migrations --list`, `gbrain doctor --fast`, `gbrain health`, and a real `gbrain query` are the minimum verification. `doctor --fast` may still warn about resolver skills and skipped DB checks; that is not a Copilot embedding failure.

11. Upstreaming to a PR/fork.
   - The active global package under `~/.bun/install/global/node_modules/gbrain` may already contain the hotfix, but it is not a git repo. Port changes carefully into `/home/tonyxu/gbrain` instead of copying wholesale, because upstream `origin/master` can be far ahead and has evolved APIs.
   - Start from upstream: `git fetch origin --prune && git checkout -B feat/copilot-embeddings origin/master`.
   - Preserve newer upstream behavior while porting. In the v0.22-era repo, keep `EmbedBatchOptions.onBatchComplete`, progress reporters, dry-run result accounting, and cost preview exports.
   - If the first implementation is Copilot-specific and Tony asks to make it generic, keep the existing PR/branch open and amend/force-push instead of opening a second PR. Rename PR title/commit/body to generic wording such as `feat: add configurable embedding providers`.
   - Do not rely on module-scope constants when command code may set env before calling embedding helpers. For new embedding writes, prefer `getEmbeddingModel()` / `getEmbeddingDimensions()` at call time, and store `${getEmbeddingModel()}:${getEmbeddingDimensions()}` in chunk metadata.
   - Also update `src/core/import-file.ts`; imports that embed immediately should write model metadata, not just `gbrain embed` refreshes.
   - Existing tests that mock `../src/core/embedding.ts` may need all exported names used by code under test, including `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `EMBEDDING_COST_PER_1K_TOKENS`, `getEmbeddingProvider`, `getEmbeddingModel`, `getEmbeddingDimensions`, and `estimateEmbeddingCostUsd`.
   - Verify before pushing with `bun run typecheck`, targeted embedding/embed/import tests, and `git diff --check`. Sanitize any terminal output that might include DB URLs, bearer tokens, GitHub tokens, or long secret-like strings.
   - After pushing, do not stop at "comment addressed" if the PR is still `CONFLICTING`. Check `gh pr view <PR> --json mergeable,headRefOid` and, if needed, merge/rebase current `origin/master` into the PR worktree, resolve conflicts, run verification again, push, and comment with the updated mergeable status.
   - When resolving conflicts between embedding-dimension work and newer upstream schema-bootstrap changes, keep both sides: call `prepareEmbeddingSchemaSettings(this)` before embedded schema replay, then keep upstream `applyForwardReferenceBootstrap()` and Postgres `verifySchema(this)` paths. The embedding settings must be established before `SCHEMA_SQL` / `PGLITE_SCHEMA_SQL`; the bootstrap still protects older brains from forward-referenced columns.
   - Full `bun test` in large gbrain worktrees can crash Bun 1.3.9 with native segfault/illegal-instruction after many PGLite-heavy tests. Treat that as a Bun/runtime signal only after verifying the crash-adjacent files standalone. Record both: e.g. `bun test --max-concurrency=1` crashed, but `bun test test/graph-query.test.ts test/minions-shell.test.ts` and the targeted PR suite passed.
   - If Tony's fork does not exist, create it with `gh repo fork garrytan/gbrain --clone=false`, add a remote such as `tony`, push the branch there, and open the PR with `--repo garrytan/gbrain --head tonyxu-io:<branch> --base master`.
   - Avoid inline multiline PR bodies with backticks in shell commands; command substitution will corrupt the PR body or run accidental commands. Write the body to a temp file and use `gh pr create --body-file /tmp/body.md`, or patch the PR body via `gh api repos/OWNER/REPO/pulls/PR -X PATCH -f body="$(cat /tmp/body.md)"` from a safe script.
   - If `gh pr edit` fails with GitHub Projects classic GraphQL warnings, use REST instead: `gh api repos/OWNER/REPO/pulls/PR -X PATCH -f title='...'` and similarly for `body`.

## Pitfalls

- Do not call `gbrain upgrade` casually; it may overwrite global-package edits.
- Do not assume `/home/tonyxu/gbrain` is the active CLI. Confirm with `readlink -f`.
- Direct calls to older-looking endpoints such as `https://api.github.com/copilot_internal/v2/token` may return 404; prefer inspecting local Copilot package/code and using the existing Copilot token/config carefully.
- Changing pgvector dimensions is schema-affecting and clears embeddings; verify scope before running on Tony's real DB.
- Avoid logging response/request headers when Authorization may be present.
