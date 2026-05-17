# Archived source: `gbrain-memory-provider-debugging`

Hermes memory-provider debugging is a gbrain integration subsection.

Original skill path: `/home/tonyxu/.hermes/skills/devops/gbrain-memory-provider-debugging`

---

# GBrain Memory Provider Debugging

Use when Tony asks whether Hermes is using gbrain as the custom memory provider, why no memories appear in gbrain, or how to list/show Hermes memories stored by the gbrain memory plugin.

## Core model

Hermes built-in memory (`MEMORY.md` / `USER.md`) is always active. `memory.provider: gbrain` adds an external provider; it does not replace the built-in store.

The gbrain provider can write in these paths:

1. Explicit `memory` tool add/replace → mirrored via `on_memory_write()` to gbrain.
2. Explicit `gbrain_remember` tool call → writes directly with `gbrain put`.
3. Conversation turn auto-sync → only if `plugins.gbrain.auto_sync_turns` or `GBRAIN_MEMORY_AUTO_SYNC` is truthy; default is false to avoid noise.
4. Pre-compression capture → only when context compression triggers.

Therefore, ordinary chat turns do **not** necessarily create gbrain memory pages.

## Quick verification commands

```bash
hermes memory status
python3 - <<'PY'
import yaml, pathlib, json
p = pathlib.Path.home() / '.hermes/config.yaml'
data = yaml.safe_load(p.read_text()) or {}
print(json.dumps(data.get('memory', {}), indent=2, ensure_ascii=False))
print(json.dumps(data.get('plugins', {}).get('gbrain', {}), indent=2, ensure_ascii=False))
PY
command -v gbrain && gbrain --version
gbrain config show
```

Expected healthy status:

- `Provider: gbrain`
- `Plugin: installed ✓`
- `Status: available ✓`
- config has `memory.provider: gbrain`
- `gbrain` CLI is on PATH

## Where Hermes gbrain memory pages go

Provider source: `~/.hermes/hermes-agent/plugins/memory/gbrain/__init__.py`.

Default slug prefix is:

```text
agents/hermes/memory
```

Unless overridden by:

```yaml
plugins:
  gbrain:
    brain_slug_prefix: agents/hermes-family/memory
```

`gbrain put` writes to the active gbrain backend, usually Postgres on Tony's host. Do not expect markdown files to appear under `/home/tonyxu/brain/agents/...`; verify with gbrain CLI, not only filesystem search.

Useful checks:

```bash
gbrain list | grep -E '^agents/hermes|^agents/hermes-family' || true
gbrain search "hermes-memory-tool"
gbrain search "gbrain_remember"
```

If no results appear, then no mirrored memory write has landed yet.

## Multi-profile install and namespaces

Hermes profiles are isolated `$HERMES_HOME`s. A memory provider can be installed in multiple profiles at once; each profile reads its own `$HERMES_HOME/plugins/<name>/` and `$HERMES_HOME/config.yaml`. Use distinct `plugins.gbrain.brain_slug_prefix` values to keep namespaces separate.

Example on Tony's host:

```yaml
# default: ~/.hermes/config.yaml
memory:
  provider: gbrain
plugins:
  gbrain:
    brain_slug_prefix: agents/hermes/memory
    auto_sync_turns: "true"
    max_results: "5"
    capture_on_pre_compress: "false"
```

```yaml
# family: ~/.hermes/profiles/family/config.yaml
memory:
  provider: gbrain
plugins:
  gbrain:
    brain_slug_prefix: agents/hermes-family/memory
    auto_sync_turns: "true"
    max_results: "5"
    capture_on_pre_compress: "false"
```

If the plugin repo is already installed in one profile, a symlink can make it available in another profile, e.g. `~/.hermes/plugins/gbrain -> ~/.hermes/profiles/family/plugins/gbrain`. Verify with both `hermes memory status` and `hermes --profile family memory status`.

After changing plugin install/config for a running gateway, restart that profile's gateway; a long-running gateway may keep old provider state.

## Source-level checks

Read these files when diagnosing behavior:

- `agent/memory_provider.py` — provider contract; `on_memory_write` mirrors built-in memory writes.
- `agent/memory_manager.py` — external provider orchestration.
- `run_agent.py` — memory provider init and the bridge after `memory` tool calls.
- `plugins/memory/gbrain/__init__.py` — gbrain provider implementation.

Key implementation facts:

- `GBrainMemoryProvider._DEFAULT_SLUG_PREFIX = "agents/hermes/memory"`.
- `sync_turn()` returns immediately unless `auto_sync_turns` / `GBRAIN_MEMORY_AUTO_SYNC` is true.
- `on_memory_write()` mirrors `add` and `replace` to gbrain with source `hermes-memory-tool`.
- `gbrain_remember` writes direct markdown pages with `gbrain put <slug>`.
- Failed capture is logged only at debug level as `GBrain capture failed`, so absence of obvious warnings does not prove writes happened.

## Log checks

```bash
grep -iE "Memory provider 'gbrain' activated|Memory provider 'gbrain' registered|GBrain capture failed|gbrain command failed|hermes-memory-tool|gbrain" ~/.hermes/logs/*.log | tail -120
```

Interpretation:

- Registration/activation proves the provider loaded.
- No `agents/hermes/...` pages plus no `hermes-memory-tool` search results means nothing has been mirrored, not necessarily that provider setup is broken.

## Explaining to Tony

Keep the answer short:

```text
Yes — gbrain is configured as the custom memory provider.
But it is additive, not a replacement for Hermes built-in memory.
Normal chat turns do not auto-write to gbrain unless auto_sync_turns is enabled.
Expected Hermes-gbrain pages live under agents/hermes/memory by default and may be in Postgres, not files.
Right now no mirrored memory pages show up, so either no memory tool write happened since activation or the prefix/config needs adjustment.
```

## Pitfalls

- Do not assume `/home/tonyxu/brain/agents/hermes-family/memory` should exist. The default prefix is `agents/hermes/memory`, and gbrain may store pages only in Postgres.
- `hermes memory status` run from an interactive shell can say gbrain is available while the Telegram gateway cannot load it: gateway PATH may omit `~/.bun/bin`. Check `/proc/<gateway-pid>/environ`; on Tony's host the stable fix is symlinks `/home/tonyxu/.local/bin/gbrain -> /home/tonyxu/.bun/bin/gbrain` and `/home/tonyxu/.local/bin/bun -> /home/tonyxu/.bun/bin/bun`, because gateway PATH includes `~/.local/bin`.
- Do not tell Tony “everything is normal” if `memory.provider: gbrain` is set but no mirrored pages exist; say the provider is configured, but no writes have landed.
- Do not enable conversation auto-sync without confirming. It can flood gbrain with low-value chat turns.
- Do not print database URLs or tokens from `gbrain config show`; rely on redacted CLI output.

## If Tony wants it fixed

Likely options:

1. Set `plugins.gbrain.brain_slug_prefix` to the expected family/profile path.
2. Leave `auto_sync_turns` off and use explicit `memory` / `gbrain_remember` writes for durable facts.
3. If he truly wants every turn captured, enable `auto_sync_turns`, but warn about noise first.
4. Run a controlled smoke test by adding a harmless memory via the `memory` tool, then verify with `gbrain search "hermes-memory-tool"` and remove the smoke page if requested.

## When creating or updating the Hermes gbrain provider PR

Use a clean worktree if the main checkout has unrelated dirty files:

```bash
git worktree add -B feat/gbrain-memory-provider .worktrees/gbrain-memory-provider origin/main
# copy only plugins/memory/gbrain/ and tests/plugins/test_gbrain_memory_plugin.py if needed
```

Security hardening checklist before opening the PR:

- Call `gbrain` via `subprocess.run([...], shell=False)` only; never shell-interpolate queries/slugs/content.
- Validate user/model-provided slugs: reject leading `-`, `..`, and anything outside lowercase letters, digits, `/`, `_`, `-`.
- Build markdown frontmatter with `yaml.safe_dump`; do not f-string raw content/category/source/user IDs into YAML.
- Keep `auto_sync_turns` and pre-compression capture default-off. Pre-compress capture should return a success message only if the write actually succeeded.
- Redact or genericize CLI errors independent of Hermes' optional global `security.redact_secrets`; `agent.redact.redact_sensitive_text()` is disabled by default unless configured.
- Guard background prefetch with a generation/session token. Clear stale cached prefetch on every `on_session_switch`, including `reset=False` resume/branch/compression transitions.
- Skip capture for secret-like content (`API_KEY=`, `Authorization Bearer`, PEM private keys, etc.).

Verification commands:

```bash
# If uv created .venv without pip, scripts/run_tests.sh may fail installing pytest-split.
.venv/bin/python -m ensurepip --upgrade || true
./scripts/run_tests.sh tests/plugins/test_gbrain_memory_plugin.py -q
git diff --cached --check
.venv/bin/python -m compileall -q plugins/memory/gbrain tests/plugins/test_gbrain_memory_plugin.py
```

Before commit/PR, run an independent reviewer over `git diff --cached`. Treat reviewer failures as blockers; patch and rerun tests/review rather than pushing a known-risk PR.

## If upstream PR should become an independent repo

If Tony says to close the Hermes upstream PR because the gbrain memory provider may need an independent repo, treat that as a course correction, not only a PR-close request.

Do this sequence unless he explicitly says "only close the PR":

1. Close/comment on the upstream PR.
2. Preserve the existing worktree/commit SHA and branch before cleanup.
3. Create a standalone repo such as `hermes-gbrain-memory-provider` or ask only if repo name/visibility materially matters.
4. Export only the plugin implementation, tests, README, and minimal packaging/CI files needed for a separate distributable plugin; do not copy unrelated Hermes checkout files or private config.
5. Add a compatibility note explaining which Hermes Agent version/API the plugin targets.
6. Run a secret scan and lightweight tests before the first push.
7. Push the repo and report the repo URL plus the closed PR URL.

Useful starting point from an existing PR branch:

```bash
SRC=/home/tonyxu/.hermes/hermes-agent/.worktrees/gbrain-memory-provider
DST=/tmp/hermes-gbrain-memory-provider
mkdir -p "$DST"
rsync -a \
  "$SRC/plugins/memory/gbrain/" "$DST/hermes_gbrain_memory/"
rsync -a \
  "$SRC/tests/plugins/test_gbrain_memory_plugin.py" "$DST/tests/test_gbrain_memory_plugin.py"
```

Then create minimal repo metadata (`README.md`, `pyproject.toml`, `LICENSE`, `.github/workflows/test.yml`) and push with `gh repo create ... --source "$DST" --push`.
