# Archived source: `gbrain-people-rebuild-from-gmail-outputs`

People rebuilds from local Gmail/calendar outputs are gbrain rebuild workflows.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-people-rebuild-from-gmail-outputs`

---

# When to use

Use when Tony wants to rebuild `brain/people/` from existing local source artifacts without rerunning Gmail backfill/export or calendar collection. Trigger especially when the existing people corpus is polluted with newsletters, stores, travel vendors, service accounts, or one-way senders, or when seeded people pages should also be recoverable from calendar evidence.

# Core judgment

Do not rerun collectors by default. Reuse existing `people/` pages, `sources/gmail/messages/*.json`, and local calendar day files unless Tony explicitly asks for a new backfill/export.

Use one canonical rebuild script for people, backed by all local source artifacts. The rebuild must still be aggressive. Keep real contacts with meaningful interaction signal. Drop newsletters, stores, airlines, order confirmations, no-reply/service accounts, and low-signal one-way senders.

Calendar evidence is useful for seeded family contacts with sparse or no Gmail history, but it should not become a loophole that floods `people/` with every calendar noun on earth.

Known calendar filters from live rebuilds:
- Ignore recurring `Monthiversary` events for Aaron/family people pages.
- Ignore low-information `Pick up Aaron` / `Drop off Aaron` events.
- Expect future recurring-class filters (for example swim/soccer) if people timelines are still too noisy.

# Required safeguards

1. Inspect the current repo state first.
   - Check `people/`, `sources/gmail/messages/`, and any existing rebuild scripts.
   - Verify whether a stable backup/snapshot of pre-filter `people/` exists.

2. Never use the current output directory as the only durable input for a repeatable rebuild.
   - A script that reads `people/*.md` and then overwrites `people/*.md` is only safe for the first run.
   - On the second run, it will silently treat the already-filtered subset as the full universe and report fake totals.
   - Fix this by reading from a stable source snapshot such as `state/rebuild_backups/.../people/`, or by introducing a separate canonical source directory.

3. Do not touch `projects/`.
   - If a previous rebuild accidentally removed `projects/`, restore it immediately from backup before considering the task done.

4. Preserve known valid contacts when present.
   - Han Chen
   - Ram / Ram Nithyanandam
   - Lovely Time / `hello@whatalovelytime.com`
   - J&P Design

# Recommended workflow

1. Inspect source directories and existing outputs.
2. Search for backups under `state/rebuild_backups/` or equivalent.
3. Build or update a canonical script under `scripts/` that:
   - reads from the stable source snapshot, not the live output directory as its only durable input
   - parses Gmail day-sharded JSON from `sources/gmail/messages/*.json`
   - optionally parses local calendar day files from `daily/calendar/**/*.md`
   - computes per-sender stats such as incoming count, distinct threads, distinct subjects, greeting hits, quoted-user hits, and user-reference hits
   - supports explicit people seeds for durable family contacts that may be calendar-backed
   - collapses duplicate person pages by primary email
   - applies hard exclusions for transactional/system senders
   - applies whitelist overrides for known valid contacts
   - writes a machine-readable inventory such as `state/people_candidate_inventory.json`
   - emits a structured `Relationship to Tony` summary field for kept people pages using grounded overrides when known
   - includes `relationship_to_tony` in the inventory and README index
   - rebuilds `people/README.md`
4. Run the canonical script.
5. Verify that whitelist contacts are present in the rebuilt `people/` and README.
6. Verify any seeded calendar-backed people pages are intentional and not over-broad.
7. Verify the printed totals use the true source corpus size, not the post-filter output count.
8. Check `git status --short | cat` for collateral damage, especially accidental deletions under `projects/`.

# Heuristic guidance

Use a strict filter. Prefer false negatives over false positives.

Useful signals for keeping a contact:
- Human-looking title/name
- Human-looking sender display names in Gmail data
- Personal-looking local part in the email address
- Multiple incoming messages across multiple threads
- Reply subjects (`Re:`)
- Snippets that greet Tony/Han directly
- Snippets that quote Tony/Han (`wrote:`) or reference their names/emails

Useful signals for dropping a contact:
- `no-reply`, `donotreply`, `mailer-daemon`, `postmaster`
- generic mailbox locals like `support`, `info`, `billing`, `orders`, `notifications`, `team`
- titles/slugs containing stores, airlines, hotels, rewards, banks, customer service, marketplace, docusign, paypal, shipping keywords
- non-human titles with brand/company framing
- low interaction counts or obvious one-way/transactional traffic

# Pitfalls learned

- Codex CLI may fail in non-interactive shells if `AZURE_OPENAI_API_KEY` is unset even when `AZURE_OPENAI_RESPONSES_API_KEY` exists. If using Codex, export:
  `AZURE_OPENAI_API_KEY="$AZURE_OPENAI_RESPONSES_API_KEY"`
- Non-login tool shells may not inherit PATH from `.bashrc`; explicitly prepend needed binaries like Homebrew and npm-global paths.
- Running the rebuild script twice can mask the source count bug if the script reads from the already-pruned `people/` directory.
- `git status` is the fastest sanity check for accidental deletions outside `people/`.

# Verification checklist

- Script does not call `gws` or rerun Gmail backfill.
- Script comments explain heuristics.
- `people/README.md` exists and lists only high-confidence contacts.
- Whitelist contacts survive.
- The reported source-page count reflects the original source set.
- `projects/` remains intact.
- Sample kept/dropped slugs look sane.

# Handy commands

Check current damage:
```bash
git -C /home/tonyxu/brain status --short | cat
```

Run the rebuild:
```bash
python3 /home/tonyxu/brain/scripts/rebuild_people_from_gmail.py
```

Inspect backup candidates:
```bash
find /home/tonyxu/brain/state/rebuild_backups -maxdepth 3 -type f | head
```
