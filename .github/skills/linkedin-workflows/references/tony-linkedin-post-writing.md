# Archived source: `tony-linkedin-post-writing`

Tony-style post drafting is a LinkedIn writing subsection.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/tony-linkedin-post-writing`

---

# Tony LinkedIn Post Writing

Use this when Tony asks to draft, shorten, revise, or make a LinkedIn post sound like him.

## Core contract

- Default to Tony's actual writing voice from his blog, not generic LinkedIn thought-leader style.
- Keep it reflective, concrete, and understated.
- For Tony's English LinkedIn posts, prefer simple, natural ESL phrasing over polished ghostwriter English.
- Avoid hype, grand predictions, excessive polish, and engagement-bait questions.
- If the topic is work-adjacent, keep company-sensitive details abstract and public-safe.

## Primary source

Local blog repo:

```text
/home/tonyxu/tonyxu-blog/src/content/blog
```

Useful posts for AI/productivity voice:

```text
/home/tonyxu/tonyxu-blog/src/content/blog/2026-ai-toolchain.md
/home/tonyxu/tonyxu-blog/src/content/blog/how-i-use-hermes-agent.md
/home/tonyxu/tonyxu-blog/src/content/blog/2024-productivity-tools.md
/home/tonyxu/tonyxu-blog/src/content/blog/2019-productivity-tools.md
/home/tonyxu/tonyxu-blog/src/content/blog/2023-year-in-review.md
/home/tonyxu/tonyxu-blog/src/content/blog/guide-to-cope-with-newborn-night-feeds.md
```

If the repo is unavailable, use the live site as fallback with bb-browser:

```bash
npx -y bb-browser --port 9222 --json open https://tonyxu.io/ --tab
npx -y bb-browser --port 9222 --json eval "({url:location.href,title:document.title,text:document.body.innerText.slice(0,5000)})" --tab <tab>
```

## Style fingerprint

Tony's blog voice is:

- first-person and experiential: “我现在…”, “对我来说…”, “我发现…”
- practical rather than performative
- specific tools first, then the workflow insight
- short paragraphs, often one idea each
- direct judgment: “这点很关键”, “真正有用的是…”, “不是…而是…”
- small time-capsule framing is acceptable for life/work transitions
- comfortable mixing work tools with family/life context when relevant

Avoid:

- generic LinkedIn openers like “Excited to share”
- inflated claims like “AI will redefine everything”
- too many emojis or hashtags
- overexplaining the obvious
- making the post sound like a corporate announcement
- turning reflective posts into advice/process checklists unless Tony asks for takeaways
- reflexively hedging strong subjective feelings; if Tony says something felt almost perfect or magical, preserve that feeling instead of softening it with caveats
- making Tony sound AI-skeptical or anti-autonomy when discussing agents; he is an AI believer, so frame boundaries as what daily-use AI agents unlock, not as “be careful with AI” caution-posting

## AI-believer / second-brain framing

When building on Hermes Agent, gbrain, or “second brain” themes, prefer a pro-AI, next-generation framing:

- Strong thesis: “The next generation of second brain is not for storing knowledge. It is for turning remembered context into action.”
- Contrast: old second brain = capture / organize / retrieve; next-gen second brain = remember / reason / act / verify / escalate.
- Grounding stack: Hermes Agent = execution layer; gbrain = knowledge base; memory = durable preferences; skills = reusable workflows; Telegram = mobile interface.
- Engagement framing should be optimistic and practical: daily boring work is what proves AI agents are real, not flashy demos.
- Avoid leading with “I don’t want fully autonomous AI agents”; it reads like Tony is skeptical. If discussing autonomy, phrase it as correctly delegated action or remembered context moving work forward.

Good hooks:

```text
The next generation of second brain is not for storing knowledge.
It is for turning remembered context into action.
```

```text
I am more bullish on AI agents after using them for boring work.
```

## Workflow

1. Read 2–5 relevant blog posts from the local repo before drafting, especially recent AI/productivity posts.
2. If Tony points to a specific artifact (for example Claude Code insights/export), read and extract the lived-use patterns before revising. Use the artifact for concrete feeling and workflow detail, not as a list of recommendations.
3. Extract the user’s requested facts and constraints.
4. Draft in English if the post is for LinkedIn unless Tony asks for Chinese.
5. Use a concise reflective shape:

```text
[life/work moment]

[what changed]

[concrete tool progression]

[the real underlying shift]

[what still matters / judgment]

[open curiosity or understated ending]
```

5. If Tony asks for shorter, cut examples first, not the core insight.
6. If Tony says “in my tone,” remove LinkedIn polish and move closer to blog-note style.

## Example pattern: AI coding workflow + paternity leave

Good direction:

```text
I’m going on paternity leave in 3 weeks, so this feels like a good time to leave a small note.

Over the past 6 months, my AI coding workflow changed pretty fast.

Copilot felt like a better autocomplete.
Windsurf felt like the editor finally understood more of the repo.
Claude Code felt like giving work to someone who could actually go do it.

Almost perfectly.
Almost magically.

That is the weird part.

I know where the rough edges are.
I know it still needs context, review, and judgment.

But the first time an agent reads the code, makes the change, runs the test, sees the failure, fixes it, and comes back with a working diff — it does feel like magic.

I don’t just ask AI to write code anymore.

I ask it to make progress:

read the code,
understand the context,
make a change,
run the test,
debug the failure,
review the diff,
try again.

That changes the texture of software engineering.

Some mechanical parts feel lighter.
Waiting on myself feels less like the bottleneck.

It feels faster, but not simply easier.

The cost of a bad assumption is higher now.

I write less code by hand,
but spend more time deciding what should exist.

I’ll be away from day-to-day coding for a few months. Given how much this workflow has changed recently, I’m genuinely curious what it will feel like when I come back.

Same job. Probably not quite the same workflow.
```

Revision lessons from Tony:

- If a paragraph starts sounding like advice — e.g. “best AI workflow is less about clever prompts, more about process” followed by checklist items — cut it unless the goal is explicitly instructional.
- For this topic, center the feeling: faster, magical, exposed, changed texture of work.
- Keep the tool progression concrete but subjective: “felt like…” works better than categorical claims.
- Prefer concise judgment lines over long explanation:
  - “It feels faster, but not simply easier.”
  - “I write less code by hand, but spend more time deciding what should exist.”

## Verification

Before finalizing:

- Does it sound like a real note Tony would post, not a LinkedIn ghostwriter?
- Is the central point concrete and grounded in tools/workflow?
- Are company details public-safe?
- Is it short enough to read on mobile?
- If asked to shorten, can the reader still remember one sentence after reading it?
