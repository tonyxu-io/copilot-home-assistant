# Archived source: `gbrain-skillpack-development`

GBrain skillpack changes are a development subsection of gbrain operations.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-skillpack-development`

---

# GBrain Skillpack Development

Use when adding or modifying a bundled gbrain skill under `~/gbrain/skills`, especially when the user asks for a new “plugin” or memory/agent workflow skill.

## Key judgment

In gbrain, many user-facing “plugins” are markdown skills shipped through the skillpack, not TypeScript runtime plugins. Before writing code, inspect whether the requested behavior belongs in:

- `skills/<name>/SKILL.md` + manifests/resolver — for agent workflow/routing knowledge.
- `src/core/minions/plugin-loader.ts` / `GBRAIN_PLUGIN_PATH` — for external subagent definition loading.
- `src/commands/integrations.ts` / recipes — for data-source integrations.
- TypeScript operations/commands — only when behavior requires a new runtime capability.

For memory-routing style tasks, prefer a bundled skill only when the requested behavior is agent guidance/routing knowledge.

**Exception — actual Hermes memory backend:** If Tony asks for a “Hermes memory provider/plugin”, links to `hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin`, or expects GBrain to be selected via `hermes memory setup/status`, do **not** implement only a gbrain skillpack skill. Build a real Hermes `MemoryProvider` plugin under the Hermes Agent repo:

- `~/.hermes/hermes-agent/plugins/memory/<name>/__init__.py` implementing `agent.memory_provider.MemoryProvider`.
- `plugin.yaml` with `name`, `description`, optional `pip_dependencies`/`hooks`.
- `README.md` with setup/config/tools.
- `register(ctx)` calling `ctx.register_memory_provider(<Provider>())`.
- Core methods: `name`, `is_available()` (no network calls), `initialize(session_id, **kwargs)` using `hermes_home`, `get_config_schema()`, `save_config()`, `get_tool_schemas()`, `handle_tool_call()`.
- Optional hooks as needed: `prefetch`, `queue_prefetch`, `sync_turn` (non-blocking), `on_memory_write`, `on_pre_compress`, `shutdown`.
- Verify with `hermes memory status`; activate with `hermes config set memory.provider <name>` only if the user wants it active.

For a GBrain-backed Hermes provider specifically, expose tools such as `gbrain_search`, `gbrain_query`, `gbrain_get`, `gbrain_remember`, and be careful: current `gbrain search/query --json` may not emit JSON unless the CLI has explicit global `--json` support. Verify the real CLI output before assuming JSON.

If Tony says a gbrain skill should “work with Hermes agent”, do not stop at adding it to gbrain’s bundle. Make the skill host-agent agnostic and install/verify it in Hermes too:

- Phrase behavior for Hermes explicitly (`memory`, `skill_manage`, `session_search`) while keeping it usable by other agents.
- Avoid OpenClaw-specific filing or prose unless the feature is genuinely OpenClaw-only.
- Prefer host-agnostic brain directories like `agents/` over `openclaw/` for agent-runtime notes.
- Install into Hermes with `gbrain skillpack install <name> --skills-dir /home/tonyxu/.hermes/skills/<category> --workspace /home/tonyxu/.hermes --json` when the user expects immediate Hermes availability.
- Verify with `hermes skills list` and read back `/home/tonyxu/.hermes/skills/<category>/<name>/SKILL.md`.

## Workflow

1. **Inspect first**
   - `git status --short`
   - Read relevant docs/code:
     - `docs/guides/plugin-authors.md`
     - `docs/guides/brain-vs-memory.md`
     - `skills/RESOLVER.md`
     - `skills/manifest.json`
     - `openclaw.plugin.json`
     - relevant existing `skills/*/SKILL.md`

2. **Write failing tests first**
   - Add a focused test under `test/`, e.g. `test/<feature>-plugin.test.ts`.
   - Test at minimum:
     - `skills/<name>/SKILL.md` exists.
     - Required frontmatter and sections exist: `name`, `description`, `## Contract`, `## Anti-Patterns`, `## Output Format`.
     - The skill is listed in `skills/manifest.json`.
     - The skill is shipped in `openclaw.plugin.json#skills` when it should be bundled.
     - `skills/RESOLVER.md` has triggers pointing to it.
     - Relevant docs mention it when appropriate.
   - Run the specific test and verify RED before implementing.

3. **Implement the skill**
   - Create `skills/<name>/SKILL.md` with YAML frontmatter.
   - Include:
     - crisp Contract
     - phases / decision tree
     - Output Format
     - Anti-Patterns
     - examples
   - Keep `writes_to:` entries limited to directories present in `skills/_brain-filing-rules.json`, otherwise `check-resolvable` will warn.

4. **Register it**
   - Add to `skills/manifest.json`.
   - Add to `openclaw.plugin.json#skills` if it should ship in the bundle.
   - Add resolver triggers in `skills/RESOLVER.md`.
   - Update `docs/GBRAIN_SKILLPACK.md` or related docs if it is part of the public/reference architecture.

5. **Verify**
   - Run targeted tests:
     ```bash
     cd ~/gbrain
     bun test test/<feature>-plugin.test.ts test/skills-conformance.test.ts test/skillpack-sync-guard.test.ts test/check-resolvable.test.ts
     ```
   - Run typecheck:
     ```bash
     bun run typecheck
     ```
   - Run resolver smoke check:
     ```bash
     gbrain check-resolvable --skills-dir ./skills --json
     ```
   - For tests whose auto-detection is affected by Tony’s real `~/.openclaw/workspace`, isolate env:
     ```bash
     HOME=/tmp/definitely-no-openclaw-home OPENCLAW_WORKSPACE= bun test test/check-resolvable-cli.test.ts
     ```

## Pitfalls

- `search_files` may omit untracked files from `git diff --stat`; use `git status --short` and `wc -l` for new files.
- Existing local `~/.openclaw/workspace` can change `check-resolvable-cli` source detection from `repo_root` to `openclaw_workspace_home_root`. This is an environment issue, not necessarily a feature regression; isolate `HOME` and `OPENCLAW_WORKSPACE` for that test.
- `writes_to:` must match `_brain-filing-rules.json`; directories like `originals/` or `wiki/agents/` may be conceptually valid in prose but still fail/warn in resolver checks unless the filing rules know them.
- Do not add TypeScript plugin machinery for behavior that is just agent routing knowledge.
- For GBrain-backed Hermes `MemoryProvider` work, prefer global JSON mode before the operation command: `gbrain --json search ...` / `gbrain --json query ...`. Preserve command-local `--json` for CLI-only commands like `gbrain check-resolvable ... --json`; do not blindly strip every `--json` as global, and do not propagate `json` through `childGlobalFlags()` into child maintenance commands.
- To verify a Hermes GBrain `MemoryProvider` end-to-end, use the real Hermes venv (`~/.hermes/hermes-agent/venv/bin/python3`), not `.venv` and not system Python. Good checks:
  1. `hermes memory status` should show `gbrain (local) ← active` and config should have `memory.provider: gbrain`.
  2. Run provider tests from a seeded temp venv if needed: `/tmp/hermes-test-venv/bin/python -m pytest tests/plugins/test_gbrain_memory_plugin.py -q -o 'addopts='`.
  3. Direct provider smoke: import `GBrainMemoryProvider`, initialize it, and call `gbrain_search`, `gbrain_query`, `gbrain_get`; ensure no JSON `error` field.
  4. Manager smoke: import `MemoryManager`, add `load_memory_provider('gbrain')`, confirm `gbrain_search/query/get/remember` in `get_all_tool_names()`, `handle_tool_call('gbrain_search', ...)` works, and `queue_prefetch_all()` + `shutdown_all()` produces context that `build_memory_context_block()` wraps in `<memory-context>`.
  5. Runtime smoke: instantiate `AIAgent(model='dummy', quiet_mode=True, enabled_toolsets=[])` and confirm provider `gbrain` is registered, `gbrain_query` is in `valid_tool_names`, and the corresponding tool schema exists.
- Hermes gateway can run for days and may not hot-load new provider code. If `hermes memory status` and direct/runtime smoke pass but Telegram behavior still seems stale, restart the gateway (`/restart` or `hermes gateway restart`).
- For GBrain-backed Hermes profile separation, `plugins.gbrain.brain_slug_prefix` is only a write namespace by default. It keeps remembered pages under different slug prefixes such as `agents/hermes-family/memory`, but `gbrain_search` / `gbrain_query` can still read the global GBrain corpus unless the provider adds explicit scoped-read behavior. Treat this as write separation, not security/privacy isolation. For real profile isolation, add provider config such as `query_scope_prefix` / `allow_global_read`, enforce prefix checks in `gbrain_get`, filter `gbrain_search` results by slug/path prefix, and filter or scope `gbrain_query` sources where the CLI supports it.
- When configuring a secondary Hermes profile to use the GBrain MemoryProvider with a separate namespace, edit that profile's `config.yaml` rather than the default config. Minimal family-style config:
  ```yaml
  memory:
    provider: gbrain
  plugins:
    gbrain:
      brain_slug_prefix: agents/hermes-family/memory
      auto_sync_turns: "false"
      max_results: "5"
  ```
  Verify with `hermes --profile <name> memory status`, then smoke-test via the real Hermes venv with `HERMES_HOME=/home/tonyxu/.hermes/profiles/<name>` and `GBrainMemoryProvider().handle_tool_call('gbrain_remember', ...)` using a slug under the expected prefix. Restart that profile's gateway if it was already running (`hermes --profile <name> gateway restart`) and re-check `gateway status`.
- To list Hermes GBrain memory pages, `gbrain` currently lacks native `list --prefix`; use JSON output plus `jq`, e.g. `gbrain --json list --limit 1000 | jq -r '.[] | select(.slug | startswith("agents/hermes/memory/")) | "\(.updated_at)\t\(.slug)\t\(.title)"'`. Use `agents/hermes-family/memory/` for family or an OR expression for both. Read with `gbrain get <slug>` and delete smoke pages with `gbrain delete <slug>`, then verify `gbrain get <slug>` fails.

## Completion criteria

Done only when:

- The new/changed skill exists and is resolver-reachable.
- Both manifests include it if bundled.
- Targeted tests pass.
- `bun run typecheck` passes.
- `gbrain check-resolvable --skills-dir ./skills --json` returns `ok: true` with zero warnings/errors.
