# Archived source: `gbrain-projects-rebuild-from-gmail-outputs`

Project rebuilds from Gmail outputs are gbrain rebuild workflows.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-projects-rebuild-from-gmail-outputs`

---

# GBrain projects rebuild from local source artifacts

Use this when the user wants to rebuild or expand `brain/projects` from already-exported local artifacts without rerunning Gmail backfills, calendar exports, or any other collectors.

## When to use

Trigger when:
- `brain/projects` only contains a few hardcoded pages and needs broader durable project coverage
- the user says they changed `brain/scripts` and wants Gmail/project rebuild rerun
- you need to infer missing project pages from existing `brain/people/*.md`
- the user explicitly does **not** want a fresh Gmail backfill or re-export

Do not use this if the user asks to fetch fresh Gmail data. Use existing export/backfill skills instead.

## Core judgment

Use one canonical rebuild script backed by a normalized event model. Do the school projects on that model first, then expand to the rest.

That means:
1. Keep all fetching/export work upstream in source-specific collectors
2. Define a normalized local event model first so calendar- and Gmail-derived timeline artifacts share one rendering shape
3. Read existing `brain/projects/*.md`, `brain/people/*.md`, and any seeded local timeline artifacts
4. Define explicit project seeds with slugs, titles, aliases, keywords, optional person-priority boosts, and explicit timeline events when the local evidence is already known
5. Score people pages against seeds and merge in normalized event evidence
6. Migrate school projects onto the normalized model before touching every other project family.
   - The current canonical script already does this for:
     - `2024-aaron-menlo-childrens-center-application`
     - `2024-aaron-menlo-childrens-center-school-ops`
     - `2025-aaron-silicon-valley-international-application`
   - Store `timeline_events` as normalized dicts with `date`, `label`, `summary`, `source_path`, and `source_family`.
   - Render markdown bullets from the normalized event list, not from hand-written final strings.
7. Only create project pages when evidence is strong enough, unless the seed is explicitly forced as durable
8. Rebuild `projects/README.md` from the discovered set
9. Emit a machine-readable inventory for review/debugging

This is the right tradeoff because it is maintainable, debuggable, deterministic, and avoids hallucinated projects.

## Files involved

Typical paths:
- `/home/tonyxu/brain/scripts/rebuild_projects.py`
- `/home/tonyxu/brain/projects/*.md`
- `/home/tonyxu/brain/people/*.md`
- `/home/tonyxu/brain/state/project_candidate_inventory.json`
- local timeline/source artifacts already on disk, such as `brain/daily/calendar/**/*.md` or Gmail digest/source markdown used to seed normalized project events

## Procedure

1. Inspect the current rebuild script.
   - Look for hardcoded project slugs or fixed index generation.
   - Confirm whether it only refreshes existing pages instead of discovering missing ones.

2. Inspect current local evidence.
   - Read `brain/people/*.md` and identify recurring multi-contact clusters.
   - Favor durable projects such as:
     - property / remodel / financing
     - wedding or event coordination
     - software/system projects
   - Ignore one-off transactions.

3. Define the normalized event model first.
   - Create one canonical event shape for project timelines, even if the first implementation is lightweight.
   - Minimum useful fields:
     - `date`
     - `label` or `kind`
     - `summary`
     - `source_path`
     - `source_family`
     - optional `project_slug`
     - optional `people_slugs`
   - The renderer should convert normalized events into the markdown bullet shape used in project `## Timeline` sections.
   - Avoid source-specific rendering branches spread all over the rebuild script.

4. Add seeded discovery.
   - Create a `PROJECT_SEEDS` structure with fields like:
     - `slug`
     - `title`
     - `kind`
     - `aliases`
     - `keywords`
     - `people_priority`
     - optional project metadata for generated page sections
     - optional explicit `timeline_events` already expressed in normalized/canonical form or rendered deterministically from it
   - Parse each people page into structured signals:
     - title
     - representative thread subjects
     - timeline subjects
     - timeline entries
     - lowercased full text

5. Score seed vs person.
   - Good default heuristic:
     - alias match in representative threads: +5
     - alias match in timeline subject: +4
     - keyword appears anywhere in full text: +2
     - person priority boost: configurable integer
   - Keep evidence only above a minimum threshold such as `>= 4`.

6. Activate candidates conservatively.
   - Keep a project if either:
     - its project page already exists, or
     - the seed is explicitly marked durable with `status: existing`, or
     - total score is high enough and evidence comes from at least 2 distinct people pages
   - A good default is:
     - `total_score >= 20`
     - `distinct_people >= 2`
   - Practical rule learned from use: `status: existing` should force inclusion for any durable seed category, not just software projects. Family/school projects may have sparse evidence in `people/*.md` but still need canonical project pages.

7. Generate or refresh project pages.
   - For each active candidate:
     - preserve existing file if present, but rewrite/refresh `## State`, `## Open Threads`, and `## Timeline`
     - create a new file if absent
   - Use a simple generated structure:
     - `# Title`
     - `## Summary`
     - `## State`
     - `## Open Threads`
     - `## Timeline`

8. Rebuild the index.
   - Rewrite `brain/projects/README.md` from the discovered candidate list.
   - Include rebuild timestamp, source inputs, and inventory path.

9. Write a debug inventory.
   - Save `brain/state/project_candidate_inventory.json`
   - Include:
     - generated timestamp
     - source inputs
     - candidates with score, status, evidence, and suggested people

10. Run and verify.
   - Execute the rebuild script.
   - Confirm the script exits cleanly.
   - Read back:
     - `projects/README.md`
     - new project pages
     - inventory JSON
   - Verify the expanded project set matches the intended durable clusters.

## Good initial seed examples

Useful first-pass durable seeds discovered from Gmail-derived people pages:
- `adu-122-walnut`
- `hermes-agent`
- `xu-chen-wedding`
- `2022-122-walnut-main-house-remodel`
- `2021-122-walnut-home-purchase-closing-insurance`
- `2019-centre-pointe-milpitas-home-purchase`
- `chase-home-refinance`
- `linkedin-career-moves`

Naming rule learned from use:
- all durable project slugs and titles should use a year prefix, not just home projects. Examples: `2026-hermes-agent`, `2020-chase-home-refinance`, `2018-linkedin-career-moves`.
- school/admissions projects should also use year-prefixed canonical names based on when the application process starts, not when later follow-up events happen. Example: `2024-aaron-menlo-childrens-center-application`, `2025-aaron-silicon-valley-international-application`.
- school application timelines should cover the full admissions chain when local evidence exists: apply/tour/playdate → interview → decision → enrollment agreement → orientation/welcome or other new-family onboarding. Do not stop at the last pre-admit milestone if later onboarding events are already present in calendar or Gmail digest sources.
- determine the year from the earliest reliable signal already present in local sources: calendar events, source markdown timestamps, or other durable dated artifacts. Do not guess from current year.
- when migrating old non-year-prefixed project files, treat the year-prefixed slug as canonical and move content into the new filename rather than creating a duplicate page.
- rebuild logic should check for legacy file paths: explicit `legacy_slugs` first, then an automatically derived unprefixed slug when the canonical slug starts with `YYYY-`.
- when a legacy path exists, read that file as the source page, write the rebuilt output to the canonical year-prefixed path, then delete the legacy file so the index and backlinks stop drifting.
- for purchase/closing/insurance projects, include the property address or a clearly distinguishing property identifier.
- do not split ADU subthreads like `Request for Geotechnical Report` or `122 Walnut St. ADU floor plan` into separate project pages; keep them under the main ADU project.
- do not split wedding room-block/timeline/vendor fragments into separate projects when they are clearly part of the main wedding project.

These worked because they had multiple related contacts and repeated project-shaped subjects over time.

Concrete evidence patterns that proved reusable:
- Builder/home-purchase projects often show up as repeated unit/community subjects like `Traditions Unit 2403`, `Centre Pointe`, `Offer Submitted`, `Home Orientation`, `Move In Survey`.
- Refinance projects show up through lender-operation subject clusters like `Loan refinance`, `Chase refinance`, `Items needed`, and `Documents needed and introduction` across multiple people pages.
- Career-history projects can be surfaced from onboarding + recruiter threads, but this is a risky broad bucket; use it as a temporary durable page only when multiple distinct people pages support it.

## Verification checklist

- Script runs without touching Gmail APIs or rerunning backfills
- `projects/README.md` lists all active discovered projects
- Newly created project pages are present on disk
- Existing project pages are preserved and refreshed
- Inventory JSON exists and contains evidence per candidate
- No junk one-off projects were created

## Pitfalls

- Do not switch straight to fuzzy unsupervised clustering. It becomes opaque fast.
- Do not infer projects from only one weak person page unless there is an existing project file.
- Do not rebuild Gmail exports if the user only asked to rerun project rebuilds from local outputs.
- Be careful with overmatching generic words like `invoice`, `project`, or `permit`; use aliases + priority boosts to anchor results.
- Verify generated timeline lines actually cite linked people pages and concrete evidence.
- Important cleanup nuance: a rebuild can refresh the active candidate set and rewrite `projects/README.md` without deleting stale old markdown pages already sitting in `projects/`. After tightening discovery logic or changing seeds, compare `projects/*.md` against `state/project_candidate_inventory.json`. Any project file whose slug is not in the active candidate list is an orphan, not a live project. Move those orphan files into a timestamped backup under `state/rebuild_backups/` and write a small manifest instead of hard-deleting them. This matters most for stale LinkedIn/work-project pages created by older broad capture workflows.

## Notes from experience

- The failure mode was a hardcoded rebuild that could only ever output ADU + Hermes + README.
- The fix was not “add more hardcoded projects.” The maintainable fix was adding seed-based candidate discovery first, then page generation.
- Writing a debug inventory file materially improves iteration speed because you can tune seeds/scoring without rereading every page manually.
