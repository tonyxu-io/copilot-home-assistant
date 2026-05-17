---
name: linkedin-workflows
description: Handle LinkedIn posting, profile drafting, work-note capture, and Tony-style LinkedIn writing from local evidence.
version: 1.0.0
license: MIT
metadata:
---

# LinkedIn Workflows

Use this for LinkedIn-specific work: posting through the browser, drafting profile updates from evidence, and writing Tony-style LinkedIn posts. Legacy `linote` capture has been replaced by `limemo` in the `limemo-capture` skill.

## Workflow classes

- **Browser posting:** use logged-in Chrome/CDP where available; verify the composer and final post state. See `references/linkedin-browser-posting.md` for the exact AX/CDP fallback that works when LinkedIn's SDUI composer ignores normal `bb-browser` clicks/fills.
- **Profile drafting:** ground on LinkedIn/work evidence and GitHub PR exports; avoid public/OSS projects unless requested.
- **Quick memo capture:** use `limemo-capture` for Tony's quick notes. `memo` is general personal memo and starts at `/home/tonyxu/brain/notes/memo/YYYY-MM-DD.md`; `limemo` is work memo and starts at `/home/tonyxu/brain/notes/work/memo/YYYY-MM-DD.md`. Route obvious items into structured notes after preserving raw text; never reduce `memo` to X/LinkedIn content capture, and never use old `linkedin-notes-YYYY-MM` pages.
- **Post writing:** learn style from Tony's local posts/blog and keep the voice reflective, concrete, and not corporate. For AI-agent/second-brain posts, use the AI-believer framing in `references/tony-linkedin-post-writing.md` — next-gen second brain = remembered context turned into action, not cautious anti-autonomy framing. Before polishing, run an **interestingness gate**: score the draft on fresh observation, tension, specificity, sharpness, and shareability. If it is below 6/10, do not merely humanize it; change the angle. Tony explicitly dislikes drafts that are correct but bloodless.
- **Growth/cadence planning:** when Tony asks about becoming more visible on LinkedIn, use `references/linkedin-growth-playbook-2026-05-01.md` as a scaffold for pillars, cadence, content mix, commenting, and profile CTA. Treat it as distribution strategy only; do not let it override Tony's non-generic voice.
- **Content backlog:** when Tony asks for a LinkedIn backlog, maintain `/home/tonyxu/brain/sources/LinkedIn/post-backlog.md`; see `references/linkedin-content-backlog-insights.md` for the gbrain import/verification workflow and the deeper agent theses.
- **Daily content editor / fragmented thoughts:** Tony's fragmented thoughts and saved links should live in the brain repo before they become posts. Use `/home/tonyxu/brain/notes/memo/` for general personal memo and `/home/tonyxu/brain/notes/work/memo/` for work memo; route obvious items into structured notes. Treat X/LinkedIn drafting as one optional downstream use, not the purpose of every memo. The daily editor should run a triage/curation pass before the editorial pass. All collected activity likes/favorites/saves should be represented in `/home/tonyxu/brain/daily/activity/YYYY/YYYY-MM-DD.md` first, date-sharded by content generation date when available; use export/collection date only as a labeled fallback. Source exports stay under `sources/...` as provenance. Use Tony's activity streams (X likes/bookmarks, YouTube likes, YouTube Music likes, Xiaohongshu likes/favorites, Douban, Google Maps saves, and `sources/preference-profile/`) as inspiration/ranking evidence rather than Tony-authored claims, and write public-safe drafts to `notes/writing/content-drafts/YYYY-MM-DD.md` when useful. Activity syntheses can live under `notes/writing/activity-inspiration/YYYY-MM-DD.md`. See `references/content-editor-brain-repo-workflow.md`.

Keep narrow source recipes and examples in `references/`.
