# LinkedIn content backlog + deeper Hermes Agent insight workflow

Use this when Tony asks to build, refine, or mine a backlog of LinkedIn topics from his Hermes/gbrain/AI workflow.

## Durable backlog location

Tony's LinkedIn backlog currently lives at:

```text
/home/tonyxu/brain/sources/LinkedIn/post-backlog.md
```

After editing it, import and verify with gbrain:

```bash
gbrain import /home/tonyxu/brain/sources/LinkedIn --no-embed
gbrain embed post-backlog
gbrain search "workflow architecture prompt engineering Hermes Agent" --limit 3
```

Note: `gbrain import` expects a directory, not a single markdown file. Importing `/home/tonyxu/brain/sources/LinkedIn/post-backlog.md` fails with `ENOTDIR`.

## Better-than-generic Hermes Agent angles

The strongest thesis from the 2026-04-30 backlog session:

> Prompt engineering is the wrong unit. Workflow architecture is the unit.

For Tony, Hermes Agent content is strongest when it goes past "second brain" and explains the operating system around the agent:

- context routing: session vs durable memory vs skills vs gbrain
- permission boundaries: read/draft/label/archive vs send/delete/deploy/spend
- escalation rules: error, blocker, decision, high-signal action item
- verification loops: tests, readback, browser state, gbrain search, final-state checks
- attention design: healthy means silent; the agent is an interrupt manager

High-signal post theses to keep reusing:

1. **Workflow architecture beats prompt engineering** — prompts matter, but the system is context, risk, verification, and escalation.
2. **Autonomy is not one slider** — useful agents need per-action permission levels.
3. **The agent is an interrupt manager** — the best assistant protects attention, not just completes tasks.
4. **Context needs a memory hierarchy** — working context, memory, skills, and knowledge base should not be mixed.
5. **The human shifts from operator to governor** — Tony sets goals/boundaries and reviews results; the agent handles safe execution.

## Tony-style handling

- Do not turn these into generic AI productivity advice.
- Keep first-person, concrete, and slightly understated.
- Prefer one strong insight per post, not a listicle.
- Good shape: lived workflow → surprising realization → concrete examples → boundary/judgment.
- Use phrases that sound like Tony: "The question is not can it do this. The question is should it do this without me." / "The impressive part is the model. The useful part is the receipt."
