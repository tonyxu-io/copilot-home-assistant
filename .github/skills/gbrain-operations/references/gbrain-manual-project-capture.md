# Archived source: `gbrain-manual-project-capture`

Manual project capture is a fallback write path under gbrain operations.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-manual-project-capture`

---

# GBrain manual project capture

Use this when Tony says some result, status, or admin milestone should be "recorded to gbrain" and the information is already in chat.

## Core judgment

Do not block on the `gbrain` CLI. In this environment it may be missing even when the canonical knowledge base exists on disk under `/home/tonyxu/brain`.

If the user wants the fact recorded now, write the project note directly in the local markdown store and update the projects index.

## Capturing generated exports into gbrain

Use this variant when Tony asks to add an exported dataset to gbrain, especially YouTube/X/social exports.

1. Prefer creating a concise gbrain page with counts, export timestamp, sample rows, and local artifact paths, instead of pasting thousands of rows into a page.
2. **Canonical artifact storage:** copy every exported source file into `/home/tonyxu/brain/sources/<export-family>/<YYYYMMDD>/` before or immediately after importing the gbrain page. Do not leave the page pointing only at `/home/tonyxu/exports/...` or `/tmp/...`.
   - Examples:
     - `/home/tonyxu/brain/sources/xhs-likes-favorites/20260426/`
     - `/home/tonyxu/brain/sources/youtube-likes/20260425/`
   - Include JSONL/CSV/raw JSON/summary Markdown/screenshots when present.
   - Normalize awkward temporary names if useful (for example remove doubled dots from filenames), but preserve timestamps.
3. Use `gbrain put <slug> < summary.md` when the CLI is healthy.
4. Add useful tags with `gbrain tag <slug> <tag>`.
5. `gbrain put` writes to the gbrain database and may not create a markdown file under `/home/tonyxu/brain`; verify with `gbrain list` / `gbrain get`, not only filesystem search. If Tony expects files, put raw artifacts under `brain/sources` and update the page body to point there.
6. `gbrain files upload-raw` may report success but `gbrain files list` can still show no files when storage is git/local-path based. Treat this as non-authoritative; include absolute `/home/tonyxu/brain/sources/...` artifact paths in the page body and verify with filesystem search.
7. Embedding can fail with OpenAI quota `429` while the page write still succeeds. Report the caveat: page and keyword search are available, vector search may not be refreshed.
8. Verify with:
   - `gbrain get <slug>`
   - `gbrain search "distinctive sample title"`
   - `find /home/tonyxu/brain/sources/<export-family>/<YYYYMMDD> -maxdepth 1 -type f` or `search_files` for artifact paths

## Procedure

1. Load context and inspect the local brain tree.
   - Check whether `/home/tonyxu/brain` exists.
   - Check whether `gbrain` CLI exists with `which gbrain` / `gbrain --version`.
   - If CLI is missing or irrelevant, proceed with direct file edits.

2. Decide whether this belongs in a project page.
   - Good fits: taxes, home/admin milestones, school admissions, travel/visa workflows, major purchases, durable personal operations.
   - Prefer a year-prefixed slug, e.g. `2025-income-tax-filing`.

3. Create or update `/home/tonyxu/brain/projects/<slug>.md` using the standard structure:
   - `# Title`
   - `## Summary`
   - `## State`
   - `## Open Threads`
   - `## Timeline`

4. Record only durable facts from chat.
   - Dates explicitly given
   - Amounts, statuses, balances due
   - What still needs verification
   - Source should clearly say it came from chat / status page / user-provided snapshot

5. Update `/home/tonyxu/brain/projects/README.md`.
   - Add the new wiki link in the active projects list.
   - Keep the existing list format intact.

6. Verify both files by reading them back.

## Bulk work-project inventory capture

Use this variant when Tony provides a canonical list of work projects and wants them recorded in `brain/projects` immediately.

1. Treat the user-provided list as canonical.
   - Create one page per listed project.
   - Preserve the project title exactly as given.
   - If the title is truncated with `…`, keep it truncated instead of guessing the full name.

2. Use a year-prefixed slug, but keep the on-page title equal to the user-provided title.
   - For fiscal labels like `FY24H2`, derive the calendar year prefix from the fiscal year number for the filename only.
   - Example: `FY24H2 - Response-based FCAP` → `2024-linkedin-fy24h2-response-based-fcap.md`

3. Distinguish inventory capture from source-backed reconstruction.
   - If you have only the user's list, create an inventory page with conservative wording like `Inventory captured / details pending`.
   - If local source notes exist, enrich the page with dated timeline bullets and a references section.
   - Do not pretend unmatched projects are source-backed.

4. When matching local work sources, add a `## References` section before `## Open Threads`.
   - Include:
     - source note paths
     - GitHub links found in those notes
     - Google Docs/Sheets links found in those notes
     - important internal links if useful for future recovery
   - This is especially useful for LinkedIn Apple Notes project archives where one note often acts as a hub to PRs, docs, Jira, dashboards, and internal tools.

5. Be conservative about attribution.
   - Shared roadmap or review notes may contain links for adjacent projects.
   - It is acceptable to attach those links as references, but label the page as source-backed inventory unless the evidence is clearly project-specific.

## Naming rules

- Use year-prefixed slugs.
- Use a human title that matches the durable topic, e.g. `2025 Income Tax Filing`.
- Prefer one durable parent project over fragment pages.

## LinkedIn/FY project inventory capture

When the user provides a canonical work-project list (for example LinkedIn FY/Half project names) and wants them reflected in brain now:

1. Create one project page per listed item instead of collapsing them into broad umbrella pages.
2. Preserve the user-provided canonical title exactly as given.
   - If the title is truncated with `…`, keep it truncated rather than guessing.
   - If the fiscal label looks odd (for example `FH25H2` vs `FY25H2`), preserve the user text unless they correct it.
3. Use a year-prefixed slug derived from the fiscal year in the title when possible.
4. If local source notes exist, add a `## References` section before `## Open Threads` with:
   - source note paths under `brain/sources/AppleNotes/In LinkedIn/`
   - matched GitHub links
   - matched Google Docs/Sheets links
   - important internal LinkedIn links when useful
5. If no local source match exists, still create the page as inventory capture only.
   - Make the status explicit, such as `Inventory captured / details pending`.
   - Add an open thread telling future-you to attach the strongest source before claiming milestones.
6. Be conservative about attribution.
   - Shared roadmap notes may contain links for adjacent projects; include them only when the page is clearly serving as a source for the named project.
   - Prefer explicit source-note paths over overconfident timeline claims.
7. If earlier broad/umbrella pages exist, keep them on disk unless asked to delete them, but update the index so the canonical project list is what shows up in `projects/README.md`.

## Pitfalls

- Do not assume the `gbrain` CLI is installed just because the repo exists.
- Do not wait for a rebuild pipeline when the user asked for a direct capture.
- Do not invent payment confirmations, settlement dates, or other missing facts.
- Record pending verification as an open thread instead of pretending the workflow is complete.
- Do not “fix” truncated project names by guessing the missing words.
- Do not present shared roadmap links as project-specific proof unless the surrounding source text actually ties them to that project.

## Verification

Done means:
- the project markdown file exists with the captured facts
- `projects/README.md` links to it
- read-back confirms the content on disk
