# Brain source snapshot and embedding closure — 2026-05-04

## Session lesson

During GBrain taxonomy / X activity repair, unrelated generated Gmail and Calendar source snapshots were also dirty. The right handling was to inspect them, verify they were generated source snapshots rather than secrets or accidental scratch files, normalize trivial formatting issues, and commit them separately from the attribution fix.

## Pattern

1. Inspect status by category:

```bash
git status --porcelain
```

Group by top-level path (`daily/`, `scripts/`, `sources/gmail/`, `sources/calendar/`, `state/`).

2. Split commits by concern:

- X attribution and daily ledgers in one commit.
- Gmail/Calendar generated snapshots and their state files in a separate `chore` commit.

3. Before staging generated source snapshots, run a lightweight secret scan over changed/untracked source and state files. Report only paths/line numbers, never secret-like content.

4. Normalize generated Markdown trailing blank EOF lines if `git diff --check` complains:

```python
from pathlib import Path
for rel in paths:
    p = Path(rel)
    lines = p.read_text(encoding='utf-8').splitlines()
    while lines and lines[-1].strip() == '':
        lines.pop()
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
```

5. Commit only after `git diff --check` passes.

## Embedding closure

After imports/backfills, run:

```bash
gbrain embed --stale
gbrain stats
```

Do not close taxonomy/coverage work until `Embedded == Chunks`. If the embed command is slow, run it as a background process and poll `gbrain stats`; progress can continue even if the process output looks stale.

## Readback verification

Use exact readbacks for representative slugs:

```bash
gbrain get daily/activity/YYYY/YYYY-MM-DD
gbrain get brain-readme
gbrain get notes/knowledge/tech/ai/second-brain-operating-system
```

Exact search may miss; `gbrain get` is the stronger source-of-truth check for known slugs.
