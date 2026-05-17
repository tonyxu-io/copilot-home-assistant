# GBrain careful local upgrade — 2026-05-06

Use this as a session-specific reference for upgrading Tony's local `/home/tonyxu/gbrain` checkout without losing local work or breaking the live Postgres brain.

## Context

- Pre-upgrade active CLI: `/home/tonyxu/.bun/bin/gbrain`, version `0.22.6.1`.
- Local checkout: `/home/tonyxu/gbrain` with Tony-local commits and Copilot embedding customization.
- Upstream after fetch: `origin/master` package version `0.27.0`; release branch `origin/garrytan/v0.28-release` package version `0.28.0`; npm package named `gbrain@1.3.1` appeared unrelated.
- Real DB used Postgres and existing pgvector column was `vector(1024)` from Copilot/Metis embeddings.
- Secrets/DB URLs must be aggressively redacted in all diagnostics.

## Safe upgrade pattern

1. Inspect before modifying:
   - `which gbrain && readlink -f "$(which gbrain)" && gbrain --version`
   - `git status --short --branch`, `git log --oneline origin/master..HEAD`, `git fetch --all --tags --prune`
   - Redacted `~/.gbrain/config.json`, redacted embedding env, and schema version.
2. Create rollback refs from current HEAD:
   - `git branch backup/pre-upgrade-<timestamp>`
   - `git tag -a pre-upgrade-<timestamp> -m 'pre gbrain upgrade <timestamp>'`
3. Prefer a new install branch from upstream master when the local checkout is stale but has preserved backup refs:
   - `git checkout -B latest-install-copilot origin/master`
   - Re-apply only known-needed Tony-local changes, not a blind merge of all old local commits.
4. Run `bun install`, ensure `src/cli.ts` is executable, `bun link`, then verify the active CLI still resolves through `/home/tonyxu/.bun/bin/gbrain` to the checkout.
5. Run migrations separately from smoke tests. If normal CLI fails because schema is stale, do not keep retrying commands that auto-initialize the schema; inspect the exact missing columns first.

## v0.27 schema jump pitfall

Jumping from an older local DB around schema version 29 to v0.27 schema version 36 can fail before formal migrations run because embedded schema SQL forward-references columns introduced by later migrations. Symptom examples:

- `gbrain stats`/search/doctor fails after upgrade even though DB connectivity is fine.
- `gbrain init --migrate-only --json` initially exits non-zero.
- Missing columns around v30–v36 include `sources.archived`, `sources.archived_at`, `sources.archive_expires_at`, `pages.deleted_at`, `mcp_request_log.agent_name`, `mcp_request_log.params`, `mcp_request_log.error_message`, `oauth_clients.token_ttl`, `oauth_clients.deleted_at`, `subagent_messages.schema_version`, `subagent_messages.provider_id`, `subagent_tool_executions.schema_version`, `subagent_tool_executions.provider_id`.

Repair approach:

- Verify locks/blockers first; do not kill unrelated sessions unless necessary.
- Apply only idempotent additive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` / `CREATE INDEX IF NOT EXISTS ...` repairs for the forward-referenced columns.
- Then rerun:
  ```bash
  env -u GBRAIN_EMBEDDING_PROVIDER \
    GBRAIN_EMBEDDING_MODEL=<provider-prefixed-model> \
    GBRAIN_EMBEDDING_DIMENSIONS=<existing-vector-dims> \
    GBRAIN_POOL_SIZE=1 \
    GBRAIN_STATEMENT_TIMEOUT=10min \
    gbrain init --migrate-only --json
  ```
- Success result in this session: schema `29 → 36`, then `gbrain apply-migrations --list` said all migrations up to date.

## v0.27 embedding env migration

v0.27 uses provider-prefixed model IDs (`provider:model`). The old env pattern breaks embedding:

```bash
GBRAIN_EMBEDDING_PROVIDER=copilot
GBRAIN_EMBEDDING_MODEL=metis-1024-I16-Binary
GBRAIN_EMBEDDING_DIMENSIONS=1024
```

Failure symptom:

- `Model id "metis-1024-I16-Binary" is missing a provider prefix.`

Fix pattern:

- Remove/ignore `GBRAIN_EMBEDDING_PROVIDER`; provider is encoded in the model string.
- Preserve existing pgvector dimensions. For Tony's current 1024-dim Metis brain, use:
  ```bash
  export GBRAIN_EMBEDDING_MODEL=litellm:metis-1024-I16-Binary
  export GBRAIN_EMBEDDING_DIMENSIONS=1024
  ```
- Keep this above any `.bashrc` non-interactive guard so Hermes/cron login shells inherit it.
- Do **not** switch to `openai:text-embedding-3-large` with 1536 dims unless intentionally migrating/re-embedding the whole vector schema.

Caveat: `litellm:metis-1024-I16-Binary` requires a reachable LiteLLM/OpenAI-compatible endpoint. If the endpoint is down, `gbrain embed --stale` may log connection failures but other read/search/stats operations can still be healthy.

## Verification checklist

Minimum post-upgrade checks:

- `git status --short --branch` clean or intentionally ahead.
- Backup branch/tag visible.
- `which gbrain`, `readlink -f "$(which gbrain)"`, `gbrain --version`.
- DB schema: `select value from config where key='version'` equals latest expected (v0.27 => `36`).
- `bash -lic 'gbrain --version && gbrain stats'` to test Tony's normal shell env.
- `GBRAIN_STATEMENT_TIMEOUT=10min gbrain search "ADU project" --limit 2` or another known durable page.
- `gbrain doctor` and classify warnings vs blockers. Existing data hygiene warnings (resolver routing misses, graph/frontmatter coverage, a few missing embeddings when provider endpoint is down) are not upgrade blockers.
- `bun run typecheck`.
- A small targeted test suite, e.g. schema-bootstrap, allow-list, and soft-delete tests.

Observed healthy final state in this session:

- `gbrain 0.27.0`
- Branch `latest-install-copilot...origin/master [ahead 1]`
- Backup refs `backup/pre-upgrade-20260506-111252` and `pre-upgrade-20260506-111252`
- Schema `36`
- `gbrain stats`: 34,061 pages; 45,069 chunks; 45,065 embedded
- `gbrain doctor`: Health score 80/100, all checks OK with warnings
- `bun run typecheck`: pass
- Selected tests: 28 pass / 0 fail

## Rollback

If the upgraded CLI is broken beyond repair:

```bash
cd /home/tonyxu/gbrain
git checkout latest-install-copilot
git reset --hard backup/pre-upgrade-<timestamp>
bun install
chmod +x src/cli.ts
bun link
gbrain --version
```

Schema rollback is separate and should not be attempted casually after successful migrations; restore from DB backup if a destructive schema migration caused data loss.