---
name: agent-steering
description: >
  Background agent dispatch & steering protocol — when to launch new agents via the task tool
  vs steer existing idle/running agents via write_agent, run isolation guards, and the absolute
  cron exception. Use when user says "steer agent", "write_agent", "dispatch agent", "launch
  agent", "background agent", "idle agent", "running agent", "new vs existing", "agent decision",
  "run isolation", "inject context", "agent communication", or any multi-agent orchestration
  decision.
---

# Agent Steering & Dispatch Skill

The canonical decision framework AND protocol for choosing between launching a fresh agent
(`task` tool) vs steering an existing idle/running agent (`write_agent`). This applies to ALL
orchestration decisions, with one absolute exception for cron (see `cron-dispatch` skill).

> Merged from the former `agent-dispatch` skill on 2026-05-17. Both skills covered the same
> decision; this is the single canonical home.

## The Core Question

**Does this message CONTINUE an existing conversation, or START a new one?**

## Decision Flow

```
1. list_agents() → check for IDLE / running agents
2. Is there an agent in the SAME domain as this request?
   NO  → Launch new (task tool)
3. Is this a FOLLOW-UP to that agent's prior work?
   (correcting, clarifying, continuing a discussion)
   NO  → Launch new (task tool)
4. Does that agent have CONTEXT that would be lost by launching fresh?
   (names, decisions, partial work, conversation state)
   NO  → Launch new (task tool)
5. Is this a CRON dispatch?
   YES → Launch new ALWAYS (see cron-dispatch skill — ABSOLUTE rule)
6. Is this a NEW pipeline run / new asset / different run_id?
   YES → Launch new (see "Run Isolation Guard" below — ABSOLUTE rule)
7. All conditions met → STEER via write_agent
```

## Launch New Agent (`task` tool) — WHEN ANY is true

| Signal | Example |
|---|---|
| New topic unrelated to any running agent | "Plan meals for next week" when only a finance agent is idle |
| No idle agents exist | Nothing in `list_agents` with matching domain |
| No relevant context in existing agent | Agent was doing X, new request is about Y |
| High-quality results needed with clean slate | Complex analysis, report generation |
| Standalone request, no dependency on prior conversation | "Run my daily briefing" |
| Unsure whether to steer or launch | **Default to launch — clean context never hurts** |
| **ALL cron-dispatched jobs** | **Always fresh, zero exceptions** |
| **NEW pipeline run / new video / new client run_id** | **Always fresh — see Run Isolation Guard** |

## Steer Existing Agent (`write_agent`) — WHEN ALL are true

| Condition | Why |
|---|---|
| An idle/running agent exists in the same domain | Agent is available |
| Message is a follow-up | Correcting, clarifying, continuing prior work |
| Agent has context that would be lost | Names, decisions, partial calculations |
| Same `run_id` (for pipeline agents) | Cross-run contamination is forbidden |
| NOT a cron dispatch | Cron always gets fresh agents |

### Valid Steering Examples

```
# Follow-up within the same shopping conversation
write_agent(agent_id: "shopping-abc", message: "Also add eggs to the H-E-B cart")

# Correction to an ongoing finance discussion
write_agent(agent_id: "finance-xyz", message: "No, the Savor is the subscription card")

# Providing missing data the agent asked for
write_agent(agent_id: "meal-abc", message: "What about Thursday dinner?")

# Within-same-run follow-up to a video editor
write_agent(agent_id: "editor-abc", message: "YouTube URL is now available: https://...")
```

## Run Isolation Guard (Pipeline Agents — ABSOLUTE)

**⚠️ CRITICAL for multi-run agents** (content pipeline, video production, client projects):

Only steer within the SAME `run_id`. When a NEW production run, video upload, or
independent request arrives:

- **ALWAYS launch a fresh agent instance** via `task` tool
- **NEVER inject a new run's context/assets** into an agent processing a different run
- Cross-run contamination corrupts transcripts, research, deliverables, and publish targets

```
# ❌ WRONG — new video into existing session
write_agent(agent_id: "editor-abc", message: "New video uploaded: C:\\vidpipe\\new-video.mp4")
# ^ Contaminates the first run's context. Launch fresh instead.
```

## Cron Exception (ABSOLUTE)

**Cron dispatches MUST ALWAYS launch fresh agents via `task` tool.** Never use
`write_agent` for cron-dispatched instances. See `cron-dispatch` skill for the
full rationale.

## Anti-Patterns (NEVER do these)

- ❌ Funneling every task through `write_agent` just because an agent is idle
- ❌ Steering cron jobs into existing agents (ABSOLUTE prohibition)
- ❌ Injecting unrelated work into an agent that's idle but in a different domain
- ❌ Injecting a NEW pipeline run into a running pipeline agent (Run Isolation Guard)
- ❌ Assuming an agent's context is still relevant hours after its last turn
- ❌ Using `write_agent` for complex new requests that deserve clean context

## Priority Guideline

When in doubt: **launch new**. The cost of a fresh agent is ~30-60s startup. The cost of
polluted context is degraded output, confused behavior, and debugging nightmares.

## Relationship to Other Skills

- **`cron-dispatch`** — Contains the absolute cron rule. This skill covers the general case.
- **`quick-task-transition`** — For "done/next" transitions, handle inline (no agent at all).
  This skill is for when you DO need an agent.
