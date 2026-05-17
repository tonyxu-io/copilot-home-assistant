# GBrain v0.27 Copilot embedding provider restore — 2026-05-06

Use this as the concrete recipe when a local gbrain v0.27 upgrade accidentally routes Tony's embeddings through OpenAI/LiteLLM or loses direct GitHub Copilot embedding support.

## Working target

- Effective env:
  - `GBRAIN_EMBEDDING_MODEL=copilot:metis-1024-I16-Binary`
  - `GBRAIN_EMBEDDING_DIMENSIONS=1024`
  - `GBRAIN_EMBED_CONCURRENCY=1`
- Existing pgvector schema: `vector(1024)`; do not switch to `1536` unless intentionally migrating/re-embedding the schema.
- Direct Copilot endpoint: `https://api.github.com/embeddings`
- Required request shape:
  - POST
  - header `X-GitHub-Api-Version: 2025-05-01`
  - body `{ "inputs": ["..."], "model": "metis-1024-I16-Binary" }`
- Response shape: `{ "embeddings": [{ "embedding": [...] }] }`, vector length `1024`.

## Implementation pattern in v0.27 provider system

1. Add a recipe: `src/core/ai/recipes/copilot.ts`.
   - `id: 'copilot'`
   - `implementation: 'native-copilot'`
   - embedding model `metis-1024-I16-Binary`, default dims `1024`.
2. Register it in `src/core/ai/recipes/index.ts` and extend `Implementation` in `src/core/ai/types.ts`.
3. In `src/core/ai/gateway.ts`, handle `native-copilot` separately from `openai-compatible`.
   - Do **not** use OpenAI-compatible body shape for Copilot.
   - Token order: `GBRAIN_COPILOT_TOKEN`, `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`, then `~/.copilot/config.json`.
   - Never print tokens or the parsed config.
4. Add a focused Bun test that mocks `fetch` and asserts URL, headers, body shape, returned vector length, and `isAvailable('embedding')`.

## Shell/config pitfall

`gbrain config get embedding_model` can show the DB/config-plane value (e.g. `openai:text-embedding-3-large`) and still not represent the effective runtime env. For Tony's shell default, verify effective config with:

```bash
bash -lic 'printf "%s\n" "$GBRAIN_EMBEDDING_MODEL" "$GBRAIN_EMBEDDING_DIMENSIONS"'

bash -lic 'cd /home/tonyxu/gbrain && bun -e '\''
import { loadConfig } from "./src/core/config.ts";
const c = loadConfig();
console.log(JSON.stringify({ embedding_model: c?.embedding_model, embedding_dimensions: c?.embedding_dimensions }));
'\'''
```

Put exports before `.bashrc`'s non-interactive guard so Hermes/cron shells inherit them. Back up `.bashrc` before edits.

## PR replacement workflow for stale pre-v0.27 Copilot branches

When replacing an old Copilot embedding PR such as #450:

1. Inspect PR state first:
   - `gh pr view <N> --json state,headRefName,baseRefName,mergeStateStatus,updatedAt,url`
   - `gh pr diff <N> --name-only`
   - `git rev-list --left-right --count origin/master...origin/pr-<N>` after fetching `pull/<N>/head`.
2. If the PR is based on v0.22-era files (`src/core/embedding.ts`, `embedding-schema.ts`, etc.), close it and open a new v0.27 provider-system PR instead of force-updating the old branch.
3. Create the new branch from latest `origin/master`, not from Tony's stale fork `master`:
   - `git switch -c feat/copilot-provider-v027 origin/master`
4. Keep the new PR small: only gateway/recipe/type/test files. Do not carry old schema/provider abstraction files forward.
5. If pushing to Tony's fork fails with:
   - `refusing to allow a Personal Access Token to create or update workflow ... without workflow scope`
   the cause may be that Tony's fork `master` is old and upstream changed `.github/workflows/*`; GitHub treats the push as updating workflows even when the feature commit does not edit them.
   - Do **not** rebase onto stale fork `master`; the v0.27 provider files may not exist there.
   - Refresh `gh` auth with `workflow` scope interactively: `gh auth refresh --hostname github.com --scopes workflow`, then push.
   - Keep a fallback patch: `git format-patch -1 --stdout HEAD > /tmp/gbrain-copilot-provider-v027.patch`.
6. If linked `gbrain` says `Permission denied`, check `src/cli.ts` executable bit and restore locally with `chmod +x src/cli.ts`. With `core.filemode=false`, this should not enter the PR diff.

## Verification commands

```bash
cd /home/tonyxu/gbrain
bun test test/ai/copilot-provider.test.ts
bun run typecheck
bash -lic 'cd /home/tonyxu/gbrain && gbrain providers list'
bash -lic 'cd /home/tonyxu/gbrain && GBRAIN_STATEMENT_TIMEOUT=10min gbrain doctor'
```

A stronger live smoke test is importing `loadConfig()`, configuring the gateway, and calling `embedOne("gbrain copilot embedding smoke test")`; expected JSON should include model `copilot:metis-1024-I16-Binary`, dimensions `1024`, `available: true`, and `vector_length: 1024`.

## Session result

The restore passed:

- Copilot provider ready in `gbrain providers list`.
- Direct embedding smoke test returned vector length `1024`.
- `gbrain doctor` reported embeddings `100% coverage, 0 missing`.
- `bun run typecheck` passed.
- Targeted suite: `30 pass / 0 fail`.
