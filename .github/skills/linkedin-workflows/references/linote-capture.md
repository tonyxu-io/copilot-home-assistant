# Archived source: `linote-capture`

Linote capture is a LinkedIn work-note subsection.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/linote-capture`

---

# Linote — Quick LinkedIn Notes Capture

Use this skill whenever Tony's message **starts with the word `linote`** (case-insensitive, with or without a trailing colon).

## Trigger

Message text matches (case-insensitive, trimmed):
- `linote <content>`
- `linote: <content>`
- `LINOTE <content>`
- etc.

If the first whitespace-delimited token equals `linote` (with optional trailing colon), this skill applies. Otherwise, ignore.

## Behavior

1. **Extract content**: strip the `linote` prefix (and optional `:`), trim whitespace. The remainder is the note body. If empty, reply: `⚠️ linote: 空内容，没存。` and stop.

2. **Compute target slug**: `linkedin-notes-YYYY-MM` using the current date in America/Los_Angeles.
   - Example: April 2026 → `linkedin-notes-2026-04`

3. **Fetch existing page content** (if any):
   ```bash
   gbrain get linkedin-notes-YYYY-MM 2>/dev/null
   ```
   If the page doesn't exist, start with a header:
   ```md
   # LinkedIn Notes — YYYY-MM
   ```

4. **Append the new entry** with a timestamp line:
   ```md
   ## YYYY-MM-DD HH:MM PT
   <note body>
   ```
   Timestamp uses America/Los_Angeles, 24h format. Separate entries by a blank line.

5. **Write back**:
   ```bash
   echo "<updated content>" | gbrain put linkedin-notes-YYYY-MM
   ```
   Use a heredoc or a temp file for multi-line content. Do NOT use `echo -e` — newlines will be mangled.

6. **Reply format** (single short Telegram line):
   ```
   ✓ linote 入库 · linkedin-notes-YYYY-MM (本月第 N 条)
   ```
   Compute N by counting `## ` headings in the updated page content.

## Implementation pattern

Use `execute_code` for atomic read-modify-write to avoid race conditions:

```python
from hermes_tools import terminal
from datetime import datetime
import zoneinfo

tz = zoneinfo.ZoneInfo("America/Los_Angeles")
now = datetime.now(tz)
slug = f"linkedin-notes-{now.strftime('%Y-%m')}"
timestamp = now.strftime("%Y-%m-%d %H:%M PT")

# Get existing content
r = terminal(f"gbrain get {slug} 2>/dev/null || true")
existing = r["output"].strip()
if not existing or "not found" in existing.lower():
    existing = f"# LinkedIn Notes — {now.strftime('%Y-%m')}\n"

# Append new entry
note_body = "<extracted content>"
new_entry = f"\n## {timestamp}\n{note_body}\n"
updated = existing.rstrip() + "\n" + new_entry

# Write atomically via temp file to preserve newlines
import tempfile
with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
    f.write(updated)
    tmp_path = f.name

terminal(f"gbrain put {slug} < {tmp_path}")

# Count entries
count = updated.count("\n## ")
print(f"✓ linote 入库 · {slug} (本月第 {count} 条)")
```

## Rules

- **No extra commentary.** The reply must be exactly the single-line confirmation. No preamble, no follow-up questions. Tony explicitly wants zero friction.
- **Never re-interpret the note.** Do not summarize, reformat, translate, or "improve" the note body. Store it verbatim.
- **Never ask clarifying questions** for a linote message. If ambiguous, just store it. Tony can re-send or edit later.
- **Don't echo the note back.** Tony already sent it.
- **Timezone is America/Los_Angeles.** Tony is in Menlo Park.
- If `gbrain put` fails, report the exact error in one line: `❌ linote 失败: <error>`.

## When NOT to use

- Message doesn't start with `linote` — fully ignore this skill.
- User asks to *read*, *search*, *edit*, or *delete* linotes — that's a different flow; handle with normal gbrain commands, not this skill.
- User says "stop linote" or "disable linote" — not a capture, treat as normal request.

## Pitfalls

- `gbrain put` reads stdin. Piping via `echo` mangles newlines. Always use a temp file or heredoc.
- `gbrain get` returns non-zero when page is missing; don't treat that as an error.
- Embedding regeneration may fail (OpenAI quota) — the page is still saved, so continue normally. Only escalate if `put` itself fails.
- Entry count: count `\n## ` (with newline prefix) to avoid counting the `# LinkedIn Notes` top-level header.
