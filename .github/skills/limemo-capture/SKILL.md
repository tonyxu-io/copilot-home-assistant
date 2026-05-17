---
name: limemo-capture
description: Quick memo capture for Tony. `memo` is personal memo and should be routed into structured brain notes; `limemo` is work memo and is stored under `notes/work/memo`, with gbrain write/embedding and one-line confirmation.
version: 1.1.0
license: MIT
metadata:
---

# Memo / Limemo Capture

Use this whenever Tony's message **starts with `memo` or `limemo`** (case-insensitive, with or without a trailing colon).

## Semantics

- `memo` = **personal memo**. Store the raw fragment, then route/curate into structured brain notes when the destination is obvious.
- `limemo` = **work memo**. Store under work memo files; do not mix it into personal memo.
- `linote` is legacy. Prefer `limemo`.

## Trigger

Message text matches, after trim:

- `memo <content>`
- `memo: <content>`
- `limemo <content>`
- `limemo: <content>`

If the first whitespace-delimited token equals `memo` or `limemo` after removing an optional trailing colon, this skill applies.

## Target paths

### Personal memo (`memo`)

Raw capture:

```text
/home/tonyxu/brain/notes/memo/YYYY-MM-DD.md
gbrain slug: notes/memo/YYYY-MM-DD
```

`memo` is a general personal memo system, not a content inbox for X/LinkedIn. It may contain ideas, links, prompts, decisions, reminders, family/home notes, learning notes, taste notes, or anything Tony wants in the brain repo. Content drafting is only one optional downstream use.

Structured curation target when obvious:

- `notes/family/...` — family, home, health, travel, parenting.
- `notes/knowledge/...` — AI, tech, reading, philosophy, music, photography.
- `notes/writing/...` — writing direction, style, drafts, and publishable ideas.
- `notes/records/...` — non-private admin/reference records only.
- `people/` or `projects/` — durable person/project facts.
- Never write secrets or credentials; never touch `notes/records/secrets/`.

### Work memo (`limemo`)

Raw capture:

```text
/home/tonyxu/brain/notes/work/memo/YYYY-MM-DD.md
gbrain slug: notes/work/memo/YYYY-MM-DD
```

If a work memo clearly updates durable work context, optionally curate into existing structured work notes under:

- `notes/work/projects/`
- `notes/work/growth/`
- `notes/work/operations/`
- `notes/work/people/`
- `notes/work/domain/`
- `notes/work/reference/`

Keep company-sensitive details scoped. Company Slack/internal comms are off-limits unless Tony explicitly provides safe text.

## Behavior

1. **Extract content**: strip the prefix (`memo` or `limemo`, optional `:`), trim whitespace.
   - If empty personal memo, reply exactly: `⚠️ memo: 空内容，没存。`
   - If empty work memo, reply exactly: `⚠️ limemo: 空内容，没存。`
2. **Compute date/time** in `America/Los_Angeles`.
3. **Append raw entry** to the right dated file under `## Raw fragments`:
   ```md
   - HH:MM PT — <verbatim note body>
   ```
   Preserve Tony's wording exactly. Do not summarize, translate, or improve the raw entry.
   If the note includes a URL and Tony gave a reason/context, keep the reason next to the URL.
4. **Structured promotion when obvious:** preserve raw first, then update the best durable note.
   - For `memo`, create/update structured notes under `notes/`, `people/`, or `projects/` only when the target is clear; otherwise raw-only is correct.
   - For `limemo`, do promote when the memo is clearly reusable work knowledge or future review material. Common cases:
   - Do **not** promote every bare URL or vague fragment. Raw-only is acceptable when the destination is unclear.
   - Keep raw wording as provenance; structured notes may generalize IDs/placeholders and remove one-off noise.
5. **Write to gbrain**:
   ```bash
   gbrain put <slug> < <file>
   gbrain embed <slug>
   ```
   Also `gbrain put` and `gbrain embed <structured-slug>` any structured note you create/update.
6. **Verify** by reading back the file and/or `gbrain get <slug>`. For batch reconciliation or if `gbrain stats` shows `Embedded < Chunks`, run `gbrain embed --stale`.
7. **Reply one short line**:
   - Personal raw-only: `✓ memo 入库 · notes/memo/YYYY-MM-DD (今日第 N 条)`
   - Personal with structured note: `✓ memo 入库 · notes/memo/YYYY-MM-DD → <structured-path>`
   - Work raw-only: `✓ limemo 入库 · notes/work/memo/YYYY-MM-DD (今日第 N 条)`
   - Work with structured note: `✓ limemo 入库 · notes/work/memo/YYYY-MM-DD (今日第 N 条) → <structured-path>`

## File templates

### Personal memo file

```md
---
title: Memo — YYYY-MM-DD
tags:
  - memo
  - personal
captured: YYYY-MM-DD
---

# Memo — YYYY-MM-DD

## Raw fragments

## Structured routing
```

### Work memo file

```md
---
title: Work Memo — YYYY-MM-DD
tags:
  - limemo
  - work
captured: YYYY-MM-DD
---

# Work Memo — YYYY-MM-DD

## Raw fragments

## Structured routing
```

## Implementation notes

- Use `execute_code` or direct file tools for atomic read-modify-write.
- Count N as the number of bullet entries under `## Raw fragments`.
- If embedding fails but `gbrain put` succeeds, still confirm saved. Only report failure if file write or `gbrain put` fails.
- When structured promotion touches multiple pages, sync and verify every touched slug, not just the raw memo slug.
- Promotion targets should use stable human-readable paths and generalized reusable content; for command snippets, replace one-off IDs with placeholders in the reference note while keeping the exact raw command in the dated memo.
- Do not echo the full note body back.
- Never ask clarifying questions for capture; if structure is unclear, save raw only.

## When not to use

- Message does not start with `memo` or `limemo`.
- Tony asks to read/search/edit/delete memos — handle with normal file/gbrain workflows, not this capture-only flow.
