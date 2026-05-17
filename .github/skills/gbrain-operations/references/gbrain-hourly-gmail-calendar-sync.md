# Archived source: `gbrain-hourly-gmail-calendar-sync`

Hourly Gmail/Calendar sync is a scheduled gbrain import workflow.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-hourly-gmail-calendar-sync`

---

# When to use
Use this skill for inspecting, debugging, or manually running the current production Gmail + Calendar sync design in `/home/tonyxu/brain`.

This skill used to document a monolithic hourly job. That design is obsolete.

Current production design is split into two responsibilities:
1. daytime incremental Gmail + Calendar digest sync
2. separate daily heavyweight calendar history export + daily calendar rebuild/import

## Live cron shape to preserve
- Current owner is consolidated `email-butler-ops`, running `15 8-21 * * *` PT.
- `email-butler-ops.py` runs Gmail collector, Calendar collector, Gmail staging, and gbrain Gmail/Calendar digest imports (`--no-embed`) as part of the broader Email Butler ops loop.
- Do not recreate a separate `daytime-gmail-calendar-digest-sync` cron unless Tony explicitly asks to split gbrain sync back out of Email Butler.
- A separate daily heavyweight calendar history rebuild may exist independently if needed.

This replaced the older standalone daytime sync cron shape.

# Daytime incremental sync workflow
1. Run collectors from `/home/tonyxu/brain/scripts/collectors`:
   - `python3 collect_gmail.py`
   - `python3 collect_calendar.py`
2. Stage only the Gmail digest days from the latest collector run:
   - `python3 stage_gmail_digest_import.py`
   - this reads `/home/tonyxu/brain/state/gmail_state.json`, copies only those `days` digest markdown files into `/home/tonyxu/brain/state/gmail_digest_import_staging/`, and prints JSON summary
3. Import digest trees into gbrain (use `--no-embed` to avoid OpenAI embedding 429 quota errors):
   - `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain import /home/tonyxu/brain/state/gmail_digest_import_staging --no-embed --json'`
   - `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain import /home/tonyxu/brain/sources/calendar/digests --no-embed --json'`

## Live path correction
Some older prompts still reference stale paths such as:
- `/home/tonyxu/brain/collectors/gmail/collect_gmail.py`
- `/home/tonyxu/brain/collectors/calendar/collect_calendar.py`
- `build_digest_staging.py`

Those are obsolete for the current repo layout.

Use the live commands from `/home/tonyxu/brain/scripts/collectors` instead:
- `python3 /home/tonyxu/brain/scripts/collectors/collect_gmail.py`
- `python3 /home/tonyxu/brain/scripts/collectors/collect_calendar.py`
- `python3 /home/tonyxu/brain/scripts/collectors/stage_gmail_digest_import.py`

# Cron job conventions
- This is still a sync job — keep the workflow focused on collectors, staging, and imports.
- Do NOT attach extra presentation-only skills to this job.
- Current daytime sync cron is alert-only: if every collector/staging/import step exits 0 and import JSON reports `status: success` with `errors: 0`, final response must be exactly `[SILENT]`.
- Do not send success summaries, routine status updates, or unchanged-state updates for healthy scheduled runs.
- Notify only for actionable problems: collector failure, staging/import failure, delivery failure, partial failure, warning worth action, or blocking issue.
- If notifying, keep it Telegram-short Chinese: lead line such as `**Daytime Sync Alert**`, failing step, root cause, impact, and one next action if useful.
- No raw JSON, no command echo, no stack traces, no tables, no long explanations.
- When embedding quota is available again, remove `--no-embed` to restore embedding enrichment.

# Calendar scope limitation
- `collect_calendar.py` only sees calendars accessible from the authenticated Google account (`yihan.xu@gmail.com`).
- LinkedIn work calendar (`@linkedin.com`) is a separate Google Workspace account and is NOT included.
- To add LinkedIn calendar, a separate CalDAV/iCal source or second Google account integration would be needed.
4. Verify:
   - collector output reports message/event counts and digest counts
   - staging helper reports the exact Gmail `days` imported
   - `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain stats'`
   - one targeted search for recent imported content if needed

# Cron output requirement
The production daytime sync cron is alert-only. For a fully healthy run, final response must be exactly `[SILENT]`; do not send success summaries, routine status updates, or unchanged-state updates.

Only when there is an actionable problem should the final response notify Tony. If reporting a partial success/failure, do not report only dates or file names; include:
- the failing or partial step
- the Gmail digest day(s) affected, if relevant
- the Calendar digest day(s) affected, if relevant
- impact in one short line
- one next-action line only if useful

Judgment:
- `synced 2026-04-14` is not a useful user-facing update by itself
- healthy syncs should be silent; problem reports should be short and actionable

# Separate daily heavyweight workflow
Use `/home/tonyxu/brain/scripts/collectors/collect_calendar_historical.py` for the heavyweight path.

That job is responsible for:
- refreshing calendar list metadata
- exporting full calendar history
- rebuilding `/home/tonyxu/brain/daily/calendar/{YYYY}/{YYYY-MM-DD}.md`
- rebuilding `/home/tonyxu/brain/daily/calendar/INDEX.md`
- importing rebuilt daily calendar into gbrain without embeddings

Do not run this heavyweight rebuild inside the daytime incremental sync unless you are explicitly debugging end-to-end rebuild behavior.

# Script mapping
- `/home/tonyxu/brain/scripts/collectors/collect_calendar.py` = lightweight rolling collector
- `/home/tonyxu/brain/scripts/collectors/collect_calendar_historical.py` = heavyweight history export + daily calendar rebuild workflow

# Pitfalls
- Tony explicitly does not want syncs running during nighttime PT. Keep recurring sync/import jobs in daytime PT windows only.
- Keep triage/alert jobs separate from state-sync/import jobs even if they all touch Gmail.
- If you manually run a cron job for testing, inspect `next_run` afterward. Manual runs can skew it off the intended cadence. If that happens, reapply/update the schedule so the next execution lands back on the expected boundary.
- `collect_gmail.py` and `collect_calendar.py` use UTC date boundaries in their current implementation. Watch for evening PT off-by-one-day behavior in user-facing daily outputs.
- When a run asks you to verify that "today's" digest files exist, treat PT (`America/Los_Angeles`) as the operational day for reporting success. It is normal to also see a Gmail digest for UTC-today while the calendar digest for UTC-today does not exist yet. Report that explicitly instead of calling the run broken.
- There is path drift risk between `/home/tonyxu/brain/sources/calendar/google-history/` and `/home/tonyxu/brain/sources/calendar/raw/`, plus slug inconsistency such as `tonys-icloud-calendar` vs `tony-s-icloud-calendar`. Avoid creating more duplicate canonical paths.
- Large `gbrain import` runs may hit a foreground timeout even while work is progressing. If so, rerun the exact same command once and let it resume from checkpoint.
- In Hermes, foreground `terminal` calls cap at 600s. If the required single retry needs a longer effective timeout, run the exact same import command as a background process, monitor it with `process`, and terminate it if it is still crawling with repeated quota errors and no meaningful progress.
- Gmail digest imports that embed during `gbrain import ... --json` can still time out after resume if the embedding provider is quota-limited. A real observed error was `429 You exceeded your current quota, please check your plan and billing details.` Report that exact error instead of pretending the import succeeded. **Fix:** use `--no-embed` flag to skip embedding and import content only. This was confirmed working on 2026-04-19: 575 imported, 220 skipped, 0 errors, 168s.
- Important nuance: Gmail import can also finish with JSON `status: success`, `imported > 0`, and `errors: 0` while still printing per-file `embedding failed ... 429 You exceeded your current quota...` lines. In that case, report it as: content import succeeded, but embedding enrichment is partial/incomplete due to quota pressure.
- Calendar digest imports can fail the same way: after the required single retry, `gbrain import /home/tonyxu/brain/sources/calendar/digests --json` may keep running for a long time with repeated `429 You exceeded your current quota...` embedding failures and very low CPU progress. **Fix:** use `--no-embed` flag. Confirmed working: same command completes in ~168s with 0 errors. For this cheap daytime job, do not babysit it forever. If the retry is still crawling after an extended wait and shows no meaningful progress, terminate it and report that the calendar import remains incomplete due to embedding quota pressure.
- `gbrain import /home/tonyxu/brain/sources/calendar/digests --json` scans the whole calendar digest tree, not just the newly collected days. In practice it may spend its limited successful imports or quota-failure time on older historical digest files (for example 2020 dates) before it ever reaches the current run's dates. For daytime reporting, treat collector output plus on-disk verification of the newly collected digest files as the source of truth for what changed; do not imply the calendar import fully covered the fresh days just because the collector succeeded.
- When you rerun the calendar import in Hermes as a background process, `process log` / `process poll` may show little or no stdout even while the import is alive. In that case, inspect the PID with `ps -p <pid> -o pid=,etime=,%cpu=,%mem=,stat=,cmd=` to judge whether it is genuinely progressing or just idling under quota pressure before deciding to kill it.
- If daytime import fails with `ON CONFLICT` / missing unique constraint after a gbrain upgrade, check the Postgres `pages` table for `pages_source_slug_key: UNIQUE (source_id, slug)`. First verify there are no duplicate `(source_id, slug)` rows, then add the constraint idempotently. A real repair was:
  ```sql
  SELECT slug, source_id, count(*)::int n
  FROM pages
  GROUP BY slug, source_id
  HAVING count(*) > 1;

  ALTER TABLE pages ADD CONSTRAINT pages_source_slug_key UNIQUE (source_id, slug);
  ```
  After repair, rerun the same `--no-embed` Gmail staging and calendar digest imports and expect `errors: 0`.
- If a manual `gbrain embed --stale` verification times out but `gbrain health` already shows `Missing embeddings: 0` and `Stale pages: 0`, inspect and kill the leftover `gbrain embed --stale` process; do not let it run forever beside cron.
- Do not run people/project rebuilds in this job.

# Success checks
- Daytime sync job contains only incremental collectors plus digest imports.
- Heavy calendar-history export and daily calendar rebuild live in the separate daily job.
- Daytime sync schedule excludes overnight PT hours.
- Triage jobs remain separate and staggered.
- `next_run` values still align with intended cron boundaries after any manual testing.
