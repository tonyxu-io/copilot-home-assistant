# Spec: LLM CLI Replacement v1

**Owner:** platform-manager
**Status:** Approved by Tony 2026-05-16 22:31 PT — "启动b, 使用copilot cli"
**Tier:** 3 (architecture change, multi-file, external dep swap)

## Problem

Two scripts shell out to a legacy external LLM CLI (`/home/tonyxu/.local/bin/hermes`) for JSON classification:

| Script | Use |
|--------|-----|
| `scripts/email_butler_action_queue.py` | Detect actionable emails + draft replies |
| `scripts/email_butler_label_maintenance.py` | Classify Gmail messages → labels |

Tony's directive (2026-05-16): copilot-home-assistant must not depend on the legacy CLI. Phase A stripped all docs/data/branding. Phase B (this spec) replaces the runtime binary call with **GitHub Copilot CLI**.

Until this lands, `email-butler-ops` cron is paused (line 59 of cron.json).

## Replacement target

GitHub Copilot CLI, already installed and authenticated on this host:

```
$ which copilot
/home/tonyxu/.npm-global/bin/copilot

$ copilot --version
GitHub Copilot CLI 1.0.49-1.
```

Non-interactive smoke test passed (2026-05-16 22:32 PT, returned valid JSON in ~6 s).

## Invocation change

**Before (legacy):**
```python
subprocess.run(
    [LLM_CLI, "chat", "-Q", "--source", "tool", "--max-turns", "1",
     "--ignore-rules", "-q", prompt],
    capture_output=True, text=True, timeout=240,
)
```

**After (copilot):**
```python
subprocess.run(
    [LLM_CLI, "-p", prompt, "--allow-all-tools", "--no-color"],
    capture_output=True, text=True, timeout=300,
)
```

| Flag | Why |
|------|-----|
| `-p <prompt>` | non-interactive mode |
| `--allow-all-tools` | required for non-interactive (no confirmation prompts) |
| `--no-color` | strip ANSI from captured output |
| `timeout=300` | copilot is slower than the legacy CLI (LLM RTT + agent init) |
| optional: `--effort low` | faster, lower cost for classification — try if quality holds |

## Output parsing

Copilot CLI prints the model response, then a metadata trailer:
```
{"test":"ok","n":42}

Changes   +0 -0
AI Units  38.5 (6s)
Tokens    ↑ 61.6k • ↓ 16 • 0 (cached)
```

Both target scripts already use `parse_jsonish()` which `raw_decode`s from the first `{` or `[`. The trailer is harmless. **No parser changes needed.**

## Affected files

| File | Change |
|------|--------|
| `scripts/email_butler_action_queue.py` | path constant (line 20), invocation args (228-229), error message branch |
| `scripts/email_butler_label_maintenance.py` | path constant (line 20), invocation args (193-195), error message branch |
| `cron.json` | re-enable `email-butler-ops`, drop `notes` field |

## Configuration

Make the binary discoverable via env var with sensible default:
```python
LLM_CLI = os.environ.get("LLM_CLI_PATH", "/home/tonyxu/.npm-global/bin/copilot")
```

Rationale: lets Tony override without code edits and makes the path discoverable.

## Cost note (not a blocker)

Smoke test: trivial prompt = 38.5 AI Units, ~6 s.
Label-maintenance can fire 30+ classifications per run; action-queue 5-25.
Worst case per hourly `email-butler-ops` cycle: ~50 calls × 14 hours = ~700 calls/day = ~28k AI Units/day from this cron alone.

**Mitigation deferred to v2:** batch multiple candidates into one prompt.

## Test plan

1. **Syntax:** `python3 -m py_compile scripts/email_butler_action_queue.py scripts/email_butler_label_maintenance.py`
2. **Single-call smoke (action queue):** invoke `llm_json` with a fixture prompt, assert JSON parses, latency < 60 s.
3. **End-to-end (action queue):** `python3 scripts/email_butler_action_queue.py --max-drafts 1` against live Gmail, assert exit 0 + valid JSON.
4. **End-to-end (label maintenance):** `python3 scripts/email_butler_label_maintenance.py`, assert exit 0 + valid JSON.
5. **Orchestrator:** `python3 scripts/email_butler_ops.py --skip-sync`, assert all sub-steps return success.
6. **Cron re-enable:** flip `enabled: true`, drop `notes`, verify `cron_next_run` picks it up.

## Rollout

1. Single commit with the code change.
2. Run tests 1–5 in order. Stop on first failure.
3. If all pass, re-enable cron (test 6).
4. Monitor first live cron run (08:15 next morning).
5. If first run fails, pause cron, investigate.

## Rollback

If Copilot CLI proves unreliable: pause cron, re-evaluate provider (OpenAI direct, Anthropic SDK), spec v2.

## Out of scope

- Batching multiple candidates per LLM call (cost optimization).
- Cleaning 30 reference-doc files under `.github/skills/*/references/` that still mention the legacy CLI.
- Other LLM call sites (none found in audit).
