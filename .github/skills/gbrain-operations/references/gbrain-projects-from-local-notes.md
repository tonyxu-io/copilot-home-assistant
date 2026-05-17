# Archived source: `gbrain-projects-from-local-notes`

Projects from local notes is a source-specific gbrain project rebuild path.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-projects-from-local-notes`

---

# GBrain projects from local notes

Use this when Tony wants project pages created in `brain/projects` from a local source tree like Apple Notes exports, especially when the existing Gmail/people rebuild pipeline does not cover that source family.

## Core judgment

Do not force everything through the Gmail-derived rebuild script.

When the source of truth is a local notes tree, build the project pages directly from those files and stay conservative:
- create pages only for durable project families with strong source evidence
- prefer dated roadmap / meeting / review notes over thin undated scratchpads
- do not invent canonical dates for weak notes just to make a page look complete

In practice, this means LinkedIn Apple Notes can justify a few durable project pages, while thin notes like one-line pointers or undated scratch files should remain unpromoted until more evidence exists.

## When to use

Trigger when:
- the user says to create projects from a local source folder rather than from Gmail
- `brain/projects` is missing project pages that clearly exist in Apple Notes / note exports
- there is no existing rebuild script for the source family
- the current local rebuild inventory does not include the requested source family

Do not use this when the user wants fresh fetch/backfill work. Use the upstream collector skill first.

## Procedure

1. Inspect current project state.
   - Check whether relevant project pages already exist under `brain/projects/`.
   - Read `brain/projects/README.md` so additions stay in the existing list style.
   - Search for existing related slugs before creating new ones.

2. Inspect the source tree broadly first.
   - Search the requested local source root for files and likely project clusters.
   - For Apple Notes / LinkedIn sources, inspect folders like:
     - `🚀 Projects`
     - dated meeting notes
     - review / growth / roadmap notes
   - Do not trust the first obvious file; many project folders contain only thin scratchpads.

3. Identify durable project candidates conservatively.
  - Good candidates usually have one or more of:
    - a project tracker entry
    - dated roadmap / review notes
    - meeting notes showing execution or follow-up
    - multiple files referring to the same project family
   - Bad candidates usually look like:
     - one-line metric pointers
     - API bookmark files
     - code snippets with no project context
     - undated scratchpads with no corroborating note

4. Determine the canonical year from the earliest reliable local evidence.
   - Prefer explicit dated files or dated references preserved in the source.
   - Examples that worked:
     - `2024-May Diff.md` justified 2024 project pages
     - `20240904 - Reducing BLT Bugs.md` provided a later operational milestone
     - a preserved Slack timestamp embedded in a note was usable after converting it to a date
   - Do not guess the year from current year or file mtime alone.

5. Merge thin project notes with stronger dated evidence.
   - Common pattern:
     - thin `🚀 Projects/...` notes provide project name, task list, or implementation details
     - dated growth / meeting notes provide the actual timeline anchors
   - Build the page from both.
   - Use the thin note for `What`, `Open Threads`, and technical scope.
   - Use the dated note for timeline milestones.

6. Write project pages manually.
   - Use standard structure:
     - `# Title`
     - `## Summary`
     - `## State`
     - `## Open Threads`
     - `## Timeline`
   - Include source-backed claims only.
   - If a person is known from the notes, list them. Otherwise keep it sparse.

7. Naming rules.
   - Use year-prefixed slugs.
   - Include source-domain qualifier when helpful, e.g. `2024-linkedin-...`.
   - Use the earliest reliable date, not the date the page was created.

8. Update `brain/projects/README.md`.
   - Add the new project links in the active-projects list.
   - Keep existing ordering/style stable unless there is a reason to rebuild the full index.

9. Verify by reading back the files.
   - Read each new project page.
   - Read `README.md` after the update.
   - If file tools return stale-cache text, verify with a direct file read path that bypasses the cached earlier result.

## Evidence heuristics that worked

For LinkedIn Apple Notes, these patterns were reliable:
- `🚀 Projects/My Projects.md` was useful as a project tracker, but not enough by itself for dates.
- dated notes like `2024-May Diff.md`, `20240904 - Reducing BLT Bugs.md`, and `20250121 - Product Jams.md` were strong anchors.
- thin project files like `Response-based FCAP.md` or `CAPI CRM.md` were only useful as supporting context, not as sole evidence.
- if a project family had only thin undated evidence (for example CAPI / Newton / Nielsen in this session), skip creating the page rather than faking confidence.

## Pitfalls

- Do not treat file modification time as project date.
- Do not promote every subfolder in a notes export into a durable project.
- Do not overfit to one scratch file with no dated corroboration.
- Do not overwrite `README.md` blindly without first preserving the existing index structure.
- Do not prune or delete note-sourced project pages just because they are absent from a Gmail/people-derived `project_candidate_inventory.json`. A local-notes source family can be legitimate while living outside that inventory.
- If you temporarily move note-sourced project pages during cleanup, restore them from backup immediately once you confirm they were built from local notes such as `sources/AppleNotes/In LinkedIn/`.
- Be aware that repeated `read_file` calls in the same conversation may return an unchanged-cache message; verify with an alternate read method if needed.

## Verification

Done means:
- new project files exist on disk
- each page has source-backed summary/state/open threads/timeline sections
- `brain/projects/README.md` links to the new pages
- weakly evidenced projects were intentionally skipped rather than hallucinated
