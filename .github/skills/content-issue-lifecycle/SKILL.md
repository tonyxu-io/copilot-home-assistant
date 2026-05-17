---
name: content-issue-lifecycle
description: >
  Standardized procedure for managing GitHub Issues in your content pipeline repository as content
  moves through the pipeline, AND the reconciliation workflow that syncs Issues to actual Late/Zernio
  post status. Use when agent says "update issue", "close issue", "schedule post", "publish content",
  "reschedule post", "content published", "issue lifecycle", "content pipeline sync", "reconcile
  issues", "sync posts to issues", "issue reconciliation", "match posts to issues",
  "pipeline sync", "update issue status from posts", or any content state transition that should be
  reflected in GitHub Issues.
---

# Content Issue Lifecycle Skill

> Standardized procedure for managing GitHub Issues in the configured content pipeline repository as content moves through the pipeline. Used by any agent that creates, schedules, publishes, or reschedules content.

## When to Use

- After scheduling a post (any platform)
- After publishing/going live
- After rescheduling or cancelling a post
- After completing all platforms for an issue
- When creating a new content item not sourced from an existing issue

## Repository

All issues live in: `{{CONTENT_PIPELINE_REPO}}`

## Status Labels

The single source of truth for content state. Only ONE status label at a time:

| Label | Meaning |
|-------|---------|
| `status:idea` | Raw idea, not yet developed |
| `status:draft` | Being written/created |
| `status:ready` | Approved, waiting to be scheduled |
| `status:scheduled` | At least one platform is scheduled |
| `status:published` | All platforms published / post is live |
| `status:cancelled` | Dropped from pipeline |

### Transition Rules

- Only move forward (idea → draft → ready → scheduled → published)
- Exception: `status:cancelled` can be applied from any state
- When the FIRST platform is scheduled: move to `status:scheduled`
- When ALL platforms are confirmed published: move to `status:published`

## Procedure: Post Scheduled

Run this after successfully scheduling a post on any platform.

### Step 1: Add Structured Comment

```bash
gh issue comment {issue_number} --repo {{CONTENT_PIPELINE_REPO}} --body "## 🎨 [{Platform}] Post — Scheduled ✅

**Agent:** {your_agent_name}
**Date:** {today YYYY-MM-DD}
**Platform:** {platform_name} ({account_name})
**Post ID:** \`{late_post_id}\`
**Scheduled for:** {datetime with timezone}

### Post Preview
> {first 3-5 lines of the post content}

### Details
- **Pillar:** {content_pillar}
- **Image:** {brief image description}
- **Hashtags:** {hashtag list}

### Remaining Platforms
- [ ] YouTube
- [ ] YouTube Shorts
- [ ] TikTok
- [ ] LinkedIn
- [ ] X / Twitter

(Check off platforms that have been scheduled)

---
*Automated by {your_agent_name}*"
```

### Step 2: Update Status Label

Swap the current status label to `status:scheduled` (if not already):

```bash
gh issue edit {issue_number} --repo {{CONTENT_PIPELINE_REPO}} \
  --remove-label "status:draft" --add-label "status:scheduled"
```

Remove whichever prior label exists (`status:idea`, `status:draft`, `status:ready`).

### Step 3: Verify

Confirm comment was posted and label changed before proceeding to any notification step.

## Procedure: All Platforms Complete

When every platform checkbox is checked:

```bash
gh issue edit {issue_number} --repo {{CONTENT_PIPELINE_REPO}} \
  --remove-label "status:scheduled" --add-label "status:published"
```

Add a final comment:
```bash
gh issue comment {issue_number} --repo {{CONTENT_PIPELINE_REPO}} \
  --body "## ✅ All Platforms Published

All scheduled platforms are now live. Closing issue.

---
*Automated by {your_agent_name}*"
```

Then close: `gh issue close {issue_number} --repo {{CONTENT_PIPELINE_REPO}}`

## Procedure: Post Rescheduled

Add a comment documenting the change:

```bash
gh issue comment {issue_number} --repo {{CONTENT_PIPELINE_REPO}} --body "## 🔄 Rescheduled

**Platform:** {platform}
**Old date:** {original_datetime}
**New date:** {new_datetime}
**Reason:** {reason}

---
*Automated by {your_agent_name}*"
```

## Procedure: Content Created Without an Issue

If content was created from a trending topic, voice command, or other trigger without a pre-existing issue:

1. Create a new issue documenting the post
2. Apply `status:scheduled` label immediately
3. Add the standard structured comment (Step 1 above)

## Why This Matters

The content-management repo is the **single source of truth** for what's been created vs. what's still in the pipeline. Skipping issue updates causes pipeline tracking failures and content duplication.

## Consuming Agents

- `content-creative` — Phase 5 (mandatory post-scheduling)
- `content-editor` — After publishing video-derived content
- `content-scheduler` — After rescheduling or queue reordering
- `content-manager` — Pipeline health monitoring (reads, doesn't write)

---

## Reconciliation (Sync Posts → Issues)

*Merged from the former `content-reconciliation` skill on 2026-05-17. Use this section when you need to retroactively sync GitHub Issues to actual Late/Zernio post status (Mon + Thu morning reconciliation cron, or manual trigger).*

Keeps GitHub Issues in `{{CONTENT_REPO}}` in sync with actual Zernio/Late post status. Runs as a scheduled cron job (Mon + Thu mornings) and can be triggered manually.

## Reconciliation Workflow

1. **Pull posts** — Paginate through `late_list_posts` for both `scheduled` and `published` statuses (at least 300-500 of each for good coverage).
2. **Pull open issues** — List all open issues from `{{CONTENT_REPO}}`.
3. **Match posts to issues** — Use fuzzy matching on:
   - Issue title vs post content/title (multi-word phrase overlap)
   - Topic-specific keyword matching (e.g., "mythos", "openshell", "copilot cli")
   - Issue number tags in posts (e.g., `issue-197`)
   - A match score threshold of **≥5** to avoid false positives.
4. **Update matched issues:**
   - **Comment** — Leave a structured comment with post IDs, platforms, dates, and status table.
   - **Label** — Set the correct status label:
     - `status:published` if any posts are published
     - `status:scheduled` if posts exist but none published yet
   - Remove stale status labels (`status:draft`, `status:ready`, `status:recorded`) when upgrading.
   - **Close** — Close the issue if it has 3+ published posts and zero remaining scheduled posts (fully rolled out).
5. **Report** — Send a summary notification to the operator with match stats, label changes, and closed issues.
6. **Track orphans** — Note issues with no matching posts (still need recording) and unmatched posts (generic/lifestyle content).

## Skip Logic

- Don't re-comment on issues that already have a recent reconciliation comment (within 3 days).
- Don't downgrade labels (e.g., don't change `status:published` back to `status:scheduled`).
- Issues with `status:article-published` are blog-only — skip video reconciliation for these.

## Comment Template

```markdown
## 🤖 Automated Pipeline Reconciliation

**Total posts found:** X (Y published, Z scheduled)

**Published on:** platform1, platform2
**Scheduled on:** platform3

### Post Details
| Platform | Status | Date | Post ID |
|----------|--------|------|---------|
| youtube | published | 2026-04-14 | `abc123...` |

**Status updated to:** `status:published`
```

## Integration Notes

- Uses the `content-pillar-schema` skill for label definitions and lifecycle transitions.
- Uses the `late-publishing` skill for platform account IDs when querying posts.
- Notify the operator using your preferred messaging channel. Never hardcode chat IDs in this skill.
