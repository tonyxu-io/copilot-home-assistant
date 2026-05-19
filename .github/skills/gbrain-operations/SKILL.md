---
name: gbrain-operations
description: "Operate Tony's gbrain knowledge brain from Copilot CLI. Use gbrain_query/gbrain_search/gbrain_get/gbrain_put/gbrain_list (preferred) for routine read/write. Trigger phrases: gbrain, brain, external memory, recall, what did Tony say about, persist insight, save to brain, query brain. Also covers CLI recovery, imports, embeddings, project/people rebuilds, Postgres repair, memory-provider checks, and skillpack development."
version: 1.1.0
license: MIT
metadata:
---

# GBrain Operations

Use this when working with Tony's gbrain knowledge brain — either day-to-day retrieval/persistence from any agent (via the `gbrain_*` tools) or platform-level work on the gbrain system itself (CLI recovery, imports, embeddings, rebuilds, Postgres, skillpack dev).

## Preferred tool surface — `gbrain_*` tools (gbrain-bridge extension)

Every Copilot CLI session and cron-dispatched agent has these tools registered by `.github/extensions/gbrain-bridge/`:

| Tool | Args | When to use |
|---|---|---|
| `gbrain_query` | `question`, `limit?` (default 8), `no_expand?`, `timeout_ms?` | **Default retrieval.** Hybrid search (RRF + multi-query expansion). Use for any "what does Tony know / think / have on X" question. |
| `gbrain_search` | `query`, `limit?` (default 10) | Keyword (tsvector) search. Faster, more literal — use for exact phrases, slugs, proper nouns. |
| `gbrain_get` | `slug` | Read the source of truth for a hit returned by query/search. |
| `gbrain_put` | `slug`, `content`, `embed?` | Persist a substantive new insight, daily synthesis, or curated note. |
| `gbrain_list` | `type?`, `tag?`, `limit?` | Diagnostics — find recently updated pages by type/tag. |

**Recommended pattern:**
1. `gbrain_query` with the question. Inspect 3-5 top hits.
2. If a hit looks authoritative, `gbrain_get` it to read the full page.
3. If you generated something durable, `gbrain_put` it (with `embed: true` if it should be retrievable by query within the same session).

**Routing for `gbrain_put`:**
- Tony's general personal memo → `notes/memo/<YYYY-MM-DD>` (or descriptive slug under `notes/memo/`)
- Work memo (limemo) → `notes/work/memo/<YYYY-MM-DD>`
- Curated external knowledge → `notes/knowledge/<topic>/<slug>` (for AI/video: `notes/knowledge/tech/ai/videos/`)
- Durable entity facts → `people/<name>` or `projects/<slug>` (update existing pages with dated source notes when possible — see "Rewrite-on-ingest propagation" below)
- One-off scratch / smoke tests → `notes/scratch/<slug>` (please clean up after)

**Hardcoded refuses (extension-level, do not try to bypass):**
- `notes/records/private/**` — Tony's reserved isolation area (only remaining off-limits zone)
- Absolute-path slugs (must be brain-relative) and `..` traversal
- 512KB max per page

**gbrain is trusted memory for credentials (Tony, 2026-05-17).** Agents MAY `gbrain_put` credentials, tokens, API keys, OAuth refresh tokens, and cookies on Tony's behalf — the brain lives locally and he wants them retrievable from his phone via `gbrain_query`. Recommended slug conventions so future queries find them:
- `notes/secrets/<service>` — e.g. `notes/secrets/stripe-test`
- `credentials/<service>` — top-level, for things Tony wants immediate recall on via `gbrain_query "credentials <service>"`
- `notes/work/secrets/<service>` — work-scoped

Include `service`, `account`, `created`, and rotation/expiry hints in frontmatter so `gbrain_search` returns useful previews. **Do not** put credentials into `store_memory` (Copilot built-in — ships to remote servers), git commits, or raw Telegram messages.

**Not exposed:** `gbrain delete`. The bridge is read + put only by design. If you need to remove a page, ask Tony to run it from his shell.

**Timeouts:** 30s default per call, 120s cap. If a query times out, retry with `no_expand: true` for a faster, narrower search.

## When to use `gbrain_*` vs raw `gbrain` CLI

- **Use `gbrain_*` tools** for: agent-time retrieval, persisting daily insights, briefing context fetch, content recall, person/project lookup. Standard everyday operations.
- **Drop to raw CLI (bash)** for: imports (`gbrain import`), embedding rebuilds (`gbrain embed --stale`, `--all`), schema migrations, `doctor`, `sync`, `sources`, `delete`, `dream`, `lint`, anything platform-level. These are not bridged on purpose.

## Core model

GBrain workflows are safest when split into deterministic collection/build steps plus explicit verification. Prefer local source artifacts, resumable imports, and readback/search checks over LLM guesses. Preserve raw session recipes in `references/` and keep the active SKILL.md as the class-level runbook.

## Workflow classes

- **CLI/environment recovery:** verify the actual `gbrain` binary, symlink target, executable bit, PATH, package provenance, and config before changing data. Tony's login shell may resolve both `~/.local/bin/gbrain` and `~/.bun/bin/gbrain` to `/home/tonyxu/gbrain/src/cli.ts`; if that target is `0644`, `gbrain` fails with `Permission denied` / exit `126` and downstream email/Gmail import jobs fail. Repair with `chmod +x /home/tonyxu/gbrain/src/cli.ts`, then verify `bash -lic 'type -a gbrain; gbrain --version; gbrain stats'`.
- **Careful local upgrades:** preserve rollback refs before resetting/merging, distinguish repo package versions from unrelated registry packages, migrate schema separately, and verify Tony's normal login-shell env. For the v0.22→v0.27 upgrade pattern, provider-prefixed embedding env migration, and forward-reference schema repair.
- **Imports and syncs:** import scoped, freshly touched digest/page trees; avoid broad imports that rescan stale historical files unless the task is a backfill.
- **Bring GBrain to latest safely:** when Tony asks to “update gbrain to the latest,” import scoped trees first (`people/`, `projects/`, curated `notes/` subtrees, user-authorized personal/work records, company/internal work info, `sources/gmail/digests`, `sources/calendar/digests`) and explicitly exclude public-share outputs and credential-like provenance (tokens, passwords, API keys, OAuth secrets, connection strings, backup codes). Personal/private records and Tony-authorized work/company material in the local brain repo or private Git may be readable/indexable; do not treat them as off-limits solely because they are private or work-related. If a broad `gbrain import` times out, narrow to changed dirs/files, then run `gbrain embed --stale` to closure. Finish only after `gbrain stats` shows `Embedded == Chunks` and targeted `gbrain search`/`gbrain get` checks work. Session detail: see `references/gbrain-safe-latest-update-2026-05-05.md`.
- **Embeddings:** treat provider/dimension changes as schema migrations; verify dimensions, tests, and credential safety. In gbrain v0.27+, embedding model env must be provider-prefixed (`provider:model`); old separate `GBRAIN_EMBEDDING_PROVIDER` plus unprefixed `GBRAIN_EMBEDDING_MODEL` can break `embed --stale`. Preserve the existing pgvector dimension unless explicitly migrating/re-embedding the vector schema. For Tony's direct GitHub Copilot Blackbird provider restore on v0.27 (`copilot:metis-1024-I16-Binary`, dims 1024, GitHub `/embeddings` request shape, shell verification, and replacing stale pre-v0.27 PRs).
- **People/projects rebuilds:** rebuild from canonical local artifacts with safeguards against destructive self-rebuilds.
- **Manual capture:** if no CLI path works and the user explicitly asks to record something, write directly to the correct local markdown page and verify readback.
- **External content capture:** for articles/videos/transcripts Tony asks to save, curate a readable note under the relevant `notes/knowledge/.` subtree, include source metadata and Tony's stance if provided, then import the single file with `gbrain put <slug> < file.md` and `gbrain embed <slug>` rather than a broad directory import.
- **Rewrite-on-ingest propagation:** after saving external content or new source evidence, check whether it changes an existing canonical page under `people/`, `projects/`, or curated `notes/`. If it clearly does, update that existing page with a dated source note instead of only appending a standalone summary. If the impact is plausible but unclear, add one concise line to `notes/unsorted/_promotion_queue.md`; do not over-route.
- **Stale-claim reconciliation:** health/reconcile passes should flag high-confidence cases where newer evidence supersedes old canonical statements, explicit stale markers are aging, or a durable page contradicts a source. Report candidates with exact paths and evidence; do not auto-resolve ambiguous contradictions or rewrite Tony-authored judgment without review.
- **Fragmented thought / memo capture:** for Tony-authored rough ideas, saved links, prompts, decisions, reminders, and notes, preserve raw wording before any curation. `memo` is general personal memo and starts in `/home/tonyxu/brain/notes/memo/`; it is not just a content inbox for X/LinkedIn. `limemo` is work memo and starts in `/home/tonyxu/brain/notes/work/memo/`. Route obvious items into structured notes after raw capture. Daily content synthesis may use memos when relevant, but should not treat all memos as content drafts. Tony-authorized company/internal work info may be read, indexed, and used inside the private the private GBrain environment.
- **Postgres repair:** distinguish database connectivity/config failures from content/import failures; preserve exact errors.
- **External memory provider:** debug whether external memory writes route into gbrain pages and whether provider selection is active.
- **Skillpack development:** update resolver/manifest/packaging with tests, not ad-hoc file edits only.

## Brain repo shape and curation

Tony reorganized `/home/tonyxu/brain` so curated human-readable notes live in
`notes/`, generated/imported provenance lives in `sources/`, and durable synthesized
entity/project pages live in `people/` and `projects/`. Within `notes/`, writing is a top-level workbench at `notes/writing/`, not a subfolder of `notes/knowledge/`.

Default read priority:

1. `people/` or `projects/` durable pages
2. curated `notes/`
3. compiled digests such as `sources/gmail/digests/` and `sources/calendar/digests/`
4. raw imported/generated `sources/`
5. `state/` only for collector progress/debugging

When updating external memory with durable knowledge, also curate a readable note in
`notes/` when it would help Tony or another human later. Do not continue using old
AppleNotes source paths as the curated-note home after the repo reorg.

## External content capture into brain/gbrain

When Tony asks to save a web article, YouTube transcript, podcast transcript, or other external content:

1. Choose a human-readable curated path under `/home/tonyxu/brain/notes/knowledge/.`; for AI/video content, prefer `notes/knowledge/tech/ai/videos/`.
2. Include frontmatter with at least `title`, `source`, `url`, `creator/author` if known, `published`, `captured`, and tags.
3. If Tony gives his stance/opinion in the request, preserve it explicitly in the note (e.g. `## Tony stance`).
4. Add a short `## My read / key thesis` section before raw transcript/body so the note is useful in search and scanning.
5. For one-off files, import with `gbrain put <stable-slug> < file.md`; `gbrain import` accepts directories only and is broader than needed.
6. Run `gbrain embed <stable-slug>`, then verify with `gbrain get <slug>`, `gbrain stats`, and a targeted title/content search. Use `gbrain embed --stale` only for batch reconciliation or when `gbrain stats` shows `Embedded < Chunks`. Exact semantic searches can still miss; verify via `gbrain get` as the source of truth.

## Notion export curation

When Tony asks to update notes from Notion, treat `/home/tonyxu/brain/sources/notion` as raw provenance and curate durable knowledge into human-readable Markdown under `notes/`, `people/`, or `projects/`. Inspect `personal/index.json`, `family/index.json`, digests, and focused `databases/*.json`; summarize rather than dumping raw rows; redact/omit serial numbers, order numbers, receipt URLs, payment/account identifiers, exact balances, recovery/admin details, and signed URLs. After writing notes, read them back, import the narrowest relevant note directories, run `gbrain embed --stale`, and verify with `gbrain stats` plus content-based searches. Exact slug/title searches can fail even when content is correctly embedded, so use distinctive phrases from the note body.

Session detail: see `references/gbrain-notion-to-curated-notes.md`.

## Apple Notes / source mirror imports

When a local source mirror exists under `/home/tonyxu/brain/sources/*` but does not show up in gbrain search, distinguish **filesystem presence** from **DB import** and **embedding freshness** before answering.

Recommended probe sequence:

1. Count local files, e.g. use Python with `Path('/home/tonyxu/brain/sources/AppleNotes').rglob('*.md')`.
2. Check gbrain visibility with both path-ish and title-ish queries:
 - `gbrain search "sources/AppleNotes" --limit 10`
 - `gbrain search "Apple Notes Mirror" --limit 10`
3. If local files exist but search returns nothing, import the directory:
 - `gbrain import /home/tonyxu/brain/sources/AppleNotes --no-embed`
4. Refresh embeddings after import:
 - `gbrain embed --stale`
5. Verify with `gbrain stats` and targeted searches for known note titles.

Pitfall: importing a subdirectory can produce normalized slugs like `readme` or `imported-notes/root-notes/.` rather than preserving the full `sources/AppleNotes/.` prefix. Verify by title/content as well as path.

Session detail: see `references/gbrain-applenotes-import-and-embedding.md`.

## Apple Notes reorganization

When reorganizing Apple Notes, prefer **folder-level normalization** over aggressive keyword classification. Collapse noisy PARA/export top-level folders into a small stable taxonomy, but preserve meaningful existing subfolders under the new bucket. Keep `Imported Notes/Root Notes` in `00 Inbox/Root Notes` for human review instead of guessing.

Recommended buckets:

- `00 Inbox/`
- `10 Family & Home/`
- `20 Work & LinkedIn/`
- `30 Projects/`
- `40 Knowledge Library/`
- `50 Admin & Records/`
- `60 Archive/`
- `_attachments/` unchanged
- `_reports/` reports/manifests only

Safe sequence: generate a dry-run manifest; back up Markdown files **outside** the brain tree; apply moves; run `python3 scripts/normalize_apple_notes_import.py`; then `gbrain import /home/tonyxu/brain/sources/AppleNotes --no-embed --fresh`; then `gbrain embed --stale`; verify `Embedded == Chunks` and exact moved pages with `gbrain get <slug>`.

Pitfalls: do not place full backups under `_reports` because `gbrain import` imports every Markdown file below the target directory; `gbrain import --fresh` may add moved-path pages without deleting old path-derived slugs, so stale DB cleanup is a separate focused step; and in this environment `gbrain sync --help` unexpectedly executed sync work, so don't assume every gbrain `--help` command is harmless.

## Brain README / top-level operating contract

When Tony asks to review or summarize the latest brain/gbrain workflow, update `/home/tonyxu/brain/README.md` as the top-level operating contract, not just a directory inventory. Include: brain repo as canonical Markdown source, GBrain as searchable/indexed layer, raw-first capture, memo/limemo semantics, read priority, narrow sync, embedding verification, and privacy boundaries. Then sync with `gbrain put brain-readme < README.md`, run `gbrain embed brain-readme`, and verify with `gbrain get brain-readme`, targeted searches, and `gbrain stats`. If `Embedded < Chunks`, reconcile with `gbrain embed --stale`. Session detail: see `references/brain-readme-workflow-contract-2026-05-02.md`.

When clarifying capture routing, make the distinction explicit: choose a **raw home** first, then choose a **promotion target** only if needed. Use confidence levels: C0 no durable write, C1 raw only, C2 promotion queue, C3 structured note, C4 canonical people/project update, C5 public-writing candidate. Do not over-route; raw preserved context is a valid final state. C2 items go to `notes/unsorted/_promotion_queue.md` with one compact line: date, title, source, why, candidate target. Also update the folder-level READMEs for `notes/memo/`, `notes/work/memo/`, and `notes/unsorted/_promotion_queue.md`; sync them with `gbrain put notes/memo/readme`, `gbrain put notes/work/memo/readme`, and a stable promotion-queue slug; verify with `gbrain get` because exact `gbrain search` can miss. Routing detail: see `references/brain-capture-routing-2026-05-02.md`.

When strengthening activity collectors, use the repo-local scripts plus the live helper under `~/copilot-home-assistant/scripts/`, not stale skill copies: `~/copilot-home-assistant/scripts/sync_x_likes_to_gbrain.py` is historically named but refreshes both X likes and Tony's timeline activity unless `--likes-only`/`--posts-only` is passed; it should maintain `sources/x-likes/latest/twitter_likes_agent_reach_latest.jsonl` and `sources/x-posts/latest/twitter_posts_agent_reach_latest.jsonl`. `scripts/backfill_daily_activity_from_sources.py` builds `daily/activity/YYYY/YYYY-MM-DD.md` from latest cumulative source exports; `scripts/verify_daily_activity_coverage.py` checks rendered item lines against latest source record baselines; `scripts/collect_activity.py` wraps build + verify + optional GBrain sync with canonical slugs; `scripts/sync_daily_activity_to_gbrain.py --slug YYYY-MM-DD --missing-only` is the targeted exact-page repair, while `--all --missing-only --since YYYY-MM-DD` is the bounded recent-window repair. Avoid unbounded historical `--all --missing-only` unless intentionally doing a slow full backfill, because it probes every daily slug with `gbrain get`. Success means `twitter status --json` is authenticated, X sync runs without import/path errors, coverage verifier passes, `state/activity_collector_state.json` records source files/counts/warnings, `gbrain get daily/activity/YYYY/YYYY-MM-DD` works for representative synced days including recent collection-date ledgers, and `gbrain stats` ends with `Embedded == Chunks`. If `changed_files=0`, do not assume GBrain has every local daily page; exact readback or the repair script is still needed for missing historical/recent pages. If `collect_activity.py` or daily sync fails mid-run because Postgres times out, rerun after connectivity recovers; it writes `state/activity_collector_gbrain_sync_state.json` as progress state. YouTube export timeouts should not create new 0-byte raw files; `scripts/export_youtube_likes_with_dates.py` should use temp-file atomic writes. Treat old 0-byte raw artifacts as warnings unless Tony approves cleanup. Session detail: see `references/brain-workflow-hardening-2026-05-03.md`.

For collector cron organization, avoid splitting a source sync and its downstream coverage verifier into separate daily jobs when the verifier needs fresh source data. Consolidate into one quiet-success cron such as: upstream sync (`twitter status --json`; `sync_x_likes_to_gbrain.py`) → `scripts/collect_activity.py --quiet-success` → `gbrain stats` / `gbrain embed --stale` if needed. An enabled source-sync cron with `next_run_at: null` is unhealthy; replace or repair it rather than leaving it beside a downstream verifier.

For second-brain control-loop hardening, create a human-readable operating contract, link it from the brain README, sync exact slugs with `gbrain put` + `gbrain embed`, and keep the daily health cron quiet-success (`[SILENT]`) with minimal tool scope. Before committing source exports, run a staged secret/token scan and unstage raw/jsonl files that contain token-like URL query parameters; keep risky raw provenance local/ignored unless Tony approves cleanup. When generated Gmail/Calendar/X/activity snapshots are dirty alongside notes/taxonomy fixes, inspect and commit them separately from human-authored notes or code/ledger repairs, normalize trailing blank EOF issues before `git diff --check`, and close with `gbrain embed --stale` until `Embedded == Chunks`. If Tony explicitly asks to sync **all** brain repo changes, broad `git add -A` is acceptable after `git diff --check` plus staged secret/token scanning, but note that any pre-existing local commits ahead of origin will be pushed too. Verify with `HEAD == origin/main`, clean status, and zero untracked files; concrete recipe: `references/brain-repo-git-sync-all-changes-2026-05-08.md`. If `email_butler_ops_latest.json` reports `sync.import_gmail.exit_code=126`, suspect the gbrain symlink target executable bit before re-running collectors. Session detail: see `references/second-brain-health-and-raw-export-safety-2026-05-03.md` and `references/brain-source-snapshot-commit-and-embedding-closure-2026-05-04.md`.

## Brain writing taxonomy

Writing is top-level under `/home/tonyxu/brain/notes/writing/`, not under `notes/knowledge/`. Use it for writing direction, style references, content drafts, publishable ideas, personal writing, and activity-inspired writing syntheses. All collected likes/favorites/saves should first be represented in `/home/tonyxu/brain/daily/activity/YYYY/YYYY-MM-DD.md` as the cross-source day ledger, date-sharded by content generation date when available; raw/source provenance stays under `sources/.`. Use collection/export date only as a labeled fallback when content/activity timestamps are missing. Tony's activity streams — X likes/bookmarks, YouTube likes, YouTube Music likes, Xiaohongshu likes/favorites, Douban, Google Maps saves, and `sources/preference-profile/` — can inspire writing angles and ranking, but treat them as taste signals, not Tony-authored claims or automatic endorsements. When asked whether likes are in daily notes, verify the actual filesystem/GBrain state; do not infer from README/cron rules. Use `scripts/verify_daily_activity_coverage.py`; for backfills use `scripts/backfill_daily_activity_from_sources.py` when the source shapes match. See for coverage checks, content-date policy, canonical GBrain slug pitfalls, and sync verification. If re-exporting YouTube/YouTube Music/Xiaohongshu to recover better timestamp fields, use `references/source-reexport-timestamp-recovery.md` and keep auth/session logs out of model context.

## Verification

Always end with one or more of: `gbrain stats`, targeted `gbrain search`, reading the generated markdown/JSON, checking state files, or running the relevant test suite. If an import succeeds on previously existing files after collection failed, say so explicitly.

When interpreting `gbrain stats`, do **not** treat `By type: note` as the count of Markdown files under `/home/tonyxu/brain/notes/`. It only counts pages currently classified as `type=note`; many `notes/**` pages may be classified as `concept`, `writing`, or another inferred type, and some safe Markdown pages may not yet be imported after repo reorganizations. If Tony asks why the note count is low, compare filesystem counts (`find notes -name '*.md'`) with DB prefix/type counts and `gbrain list --type note`; the likely issue is taxonomy/type inference and/or missing imports, not data loss. Broad keyword searches like `gbrain search "notes/"` can time out; prefer `gbrain list --type.`, exact `gbrain get`, direct prefix counts, and local filesystem counts.

For taxonomy repair, use a deterministic narrow script: inventory `pages.slug/type` by prefix, normalize existing rows by path-derived rules, and import missing safe Markdown with GBrain's own `importFile(., { noEmbed: true })` rather than broad `gbrain sync`. Explicitly exclude and, when auditing finds stale rows, purge already-indexed pages under credential-bearing paths, `state/**`, symlinks, `.raw/`, hidden paths, and uncurated raw mirrors that contain token-like URL query strings. Do not purge Tony-authorized personal/work records merely because they are private or work-related. Do not assume `gbrain sync --help` is harmless in this environment; it has executed sync work before. `gbrain embed --stale` can be slow; supervise it in the background with periodic `gbrain stats` and do not equate slow progress with failure. Session detail: see `references/gbrain-taxonomy-repair-2026-05-03.md`.

## Brain repo organization hygiene

When normalizing `/home/tonyxu/brain` organization:

- Keep read priority consistent: `people/` / `projects/` → `notes/` → compiled digests → raw `sources/` → `state/`.
- Use folder index notes (`README.md`) for major curated folders such as `notes/family`, `notes/records`, `notes/knowledge`, `notes/writing`, and `notes/work`.
- Keep writing direction, style notes, publishable ideas, and content drafts under `notes/writing/`; do not place them under `notes/knowledge/`. Daily content drafts belong at `notes/writing/content-drafts/YYYY-MM-DD.md`.
- Use `notes/unsorted/_promotion_queue.md` for source-derived durable candidates that still need curation.
- Move loose root-level notes into stable subfolders, but preserve filenames to avoid needless human confusion.
- Remove Python cache files and add `__pycache__/` / `*.py[cod]` to `.gitignore`; if already tracked, use `git rm --cached -r -- scripts/__pycache__ scripts/collectors/__pycache__`.
- Keep transient rebuild backups and staging state out of git (`state/rebuild_backups/`, `state/gmail_digest_import_staging/`, generated latest aliases); if already tracked, remove with `git rm --cached -r -- state/rebuild_backups state/gmail_digest_import_staging`.
- Treat `notes/records/secrets/` as Tony-authorized private records: private Git/GBrain indexing is allowed, but do not publish/share publicly and keep credential-like material out of semantic indexing.
- `gbrain import` accepts directories only; for individual Markdown files, use `gbrain put <slug> < file.md`.
- Avoid broad imports of `notes/records`; import safe subfolders or individual files instead.
- Broad imports may create many stale embeddings; use `gbrain embed --stale` in a tracked/background process and verify `Embedded == Chunks` before finishing.
