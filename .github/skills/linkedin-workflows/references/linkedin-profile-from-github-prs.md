# Archived source: `linkedin-profile-from-github-prs`

Profile drafting from PR evidence is a LinkedIn content workflow.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/linkedin-profile-from-github-prs`

---

# LinkedIn Profile From GitHub PRs

Use when Tony asks to improve, rewrite, or review his LinkedIn profile / headline / About / Experience using GitHub PR evidence.

## Contract

- Use Tony's **LinkedIn work-scope PR export** as the primary evidence source.
- Do **not** use public/personal GitHub PRs such as gbrain, Hermes, personal blog, or other outside-work OSS projects for LinkedIn profile copy unless Tony explicitly asks for a personal-site/GitHub-profile version.
- Keep company-sensitive details at profile-safe abstraction level. Do not expose private repo URLs in final public-facing copy unless Tony explicitly wants internal references preserved.
- Separate three artifacts when useful:
  1. public LinkedIn-ready copy,
  2. evidence notes with internal PR references,
  3. excluded outside-work/personal material.

## Canonical Source

Primary export:

```text
/home/tonyxu/brain/sources/LinkedIn/GitHub/pull_requests.md
```

Known shape:

- Markdown file grouped by repo.
- Header includes total/status counts.
- Rows look like:

```markdown
| [#1028](https://github.com/linkedin-multiproduct/ads-privacy-offline/pull/1028) | Add member coverage check to mask token profile data quality assertions | Merged | 2026-04-08 | 2026-04-09 |
```

As of Apr 2026, the export contained roughly:

- 1171 total PRs
- 1035 merged PRs
- Main clusters: `tscp-experiment-offline`, `tscp-experiment`, `metric-defs`, `campaign-manager-api`, `ads-privacy-offline`, `conversion-tracking-processor-beam`, `avro-schemas`, `li-productivity-agents`, `marketing-science-context`.

## Workflow

0. **Read the current live LinkedIn profile when possible.**

Use Tony's logged-in Chrome via bb-browser/CDP to capture current headline, About, and Experience before drafting. The current profile slug verified in Apr 2026 is:

```bash
npx -y bb-browser --port 9222 --json open https://www.linkedin.com/in/tonyxu93/ --tab
npx -y bb-browser --port 9222 --json eval "({url: location.href, title: document.title, text: document.body.innerText.slice(0,8000)})" --tab <tab>
```

Known caveat: `https://www.linkedin.com/in/tonyxu-io/` returns LinkedIn 404; use `tonyxu93` unless Tony says it changed.

1. **Parse the export, don't guess from memory.**

```python
from pathlib import Path
import re, collections
p = Path('/home/tonyxu/brain/sources/LinkedIn/GitHub/pull_requests.md')
text = p.read_text(errors='ignore')
repo = None
prs = []
for line in text.splitlines():
    m = re.match(r'##\s+(.+?) \((\d+) PRs\)', line)
    if m:
        repo = m.group(1)
        continue
    m = re.match(r'\| \[#(\d+)\]\(([^)]+)\) \| (.*?) \| (\w+) \| ([0-9-]+) \|\s*([0-9-]*)\s*\|', line)
    if m and repo:
        num, url, title, state, created, merged = m.groups()
        prs.append({
            'repo': repo,
            'num': int(num),
            'url': url,
            'title': title,
            'state': state,
            'created': created,
            'merged': merged,
        })
print(len(prs), collections.Counter(p['state'] for p in prs))
print(collections.Counter(p['repo'] for p in prs).most_common(20))
```

2. **Extract themes by work scope.** Useful buckets:

- Marketing Science experimentation systems: A/B testing, experiment, lift test, Brand Lift, incremental lift, randomization units, experiment hub.
- CTV / Brand Lift / survey measurement: CTV, survey, questionnaire, screener, BLT, lift testing survey.
- Privacy-safe offline pipelines: CLOAK, privacy-offline, mask token, data quality, coverage, consent, ACL.
- Data pipelines / reliability: Beam, Airflow, DAG, pipeline, processor, sensor, schedule, partition, coalesce, timeout, monitoring.
- APIs / schemas / product surfaces: campaign-manager-api, schema, resource, UI state, endpoint, client, dimension, metric.
- Developer productivity / AI-assisted work tooling: context repo, runbooks, workspace knowledge, Claude Code dotfiles, Ads Experiment Copilot.

3. **Draft public-facing LinkedIn copy.**

Recommended headline style:

```text
Staff Software Engineer @ LinkedIn | Ads Experimentation, Lift Measurement & Privacy-Safe Data Systems
```

Shorter conservative alternative:

```text
Staff Software Engineer @ LinkedIn | Ads Experimentation & Measurement Infrastructure
```

Recommended About structure:

- First sentence: role + domain.
- Second paragraph: concrete system scope grounded in PR themes.
- Third paragraph: recent focus areas.
- Final sentence: operating philosophy / value.

Example:

```text
I’m a Staff Software Engineer at LinkedIn building experimentation and measurement systems for LinkedIn Ads.

My current work is in Marketing Science, where I build infrastructure that helps advertisers measure the real impact of their campaigns: A/B testing systems, Brand Lift and CTV measurement, survey workflows, privacy-safe offline processing, metrics, APIs, schemas, and reliability tooling.

Before Marketing Science, I worked on LinkedIn’s Developer/API Platform and Sales Navigator application platform, building partner-facing APIs, internal developer tools, and integration surfaces used by internal teams, partners, and third-party applications. Earlier at Moxtra, I worked across software engineering, solutions engineering, and product execution, which shaped how I approach engineering: technical depth, product judgment, and clear cross-functional communication.

I’m strongest in backend/platform engineering, experimentation infrastructure, ads measurement, API design, and data pipelines. I like turning ambiguous measurement problems into durable systems: clean APIs, observable pipelines, safer data handling, and tools that help teams move faster without adding operational risk.
```

4. **Draft Experience bullets.** Keep them impact-oriented but evidence-grounded. For Tony's current Staff role, prefer:

```text
Designing and building Marketing Science infrastructure for LinkedIn Ads experimentation and lift measurement.

- Built and evolved experimentation systems across A/B testing, Brand Lift, CTV measurement, and account-level lift workflows.
- Developed privacy-safe offline data pipelines for lift-testing signals including survey actions, impressions, click events, profile attributes, and related measurement datasets.
- Improved measurement reliability through data quality checks, coverage validation, DAG scheduling changes, partition/sensor fixes, timeout tuning, monitoring, and alerting.
- Expanded API, schema, metric, and product surfaces for experimentation workflows, including randomization-unit metadata, timestamps, campaign scheduling behavior, UI states, dimensions, and health metrics.
- Improved team productivity with workspace knowledge, runbooks, context repositories, and AI-assisted developer tooling for Marketing Science workflows.
```

Reusable bullet themes for other LinkedIn roles:

- Built and evolved Marketing Science experimentation systems across A/B testing, Brand Lift, CTV measurement, and incremental-lift workflows.
- Developed privacy-safe offline processing and CLOAK-based lift-testing pipelines for survey actions, impressions, click events, profile attributes, and related datasets.
- Improved data quality and reliability with coverage checks, sensor/partition fixes, scheduling changes, timeout tuning, small-file reduction, and monitoring/alerting updates across Beam/Airflow/DAG workflows.
- Expanded API/schema and metric surfaces for experimentation, including randomization unit metadata, created/end timestamps, campaign scheduling behavior, UI states, dimension definitions, and health/usage metrics.
- Maintained broad cross-repo changes across Marketing Science infrastructure, including experimentation services, metric definitions, campaign-manager APIs, offline pipelines, conversion-tracking processors, schemas, and related services.
- Improved team productivity with workspace knowledge bases, runbooks, context-repo integration, Claude Code dotfiles/install scripts, and Ads Experiment Copilot examples/fixes.

5. **Keep evidence separate from public copy.**

Selected evidence examples from the export may include:

- `linkedin-context/marketing-science-context#19` — company-level lift testing spec.
- `linkedin-context/marketing-science-context#18` — CTV Screener Creative Experiment retroactive spec and plan.
- `linkedin-multiproduct/ads-privacy-offline#1028` — member coverage check for mask token profile data quality assertions.
- `linkedin-multiproduct/ads-privacy-offline#1017` — data quality task for mask token profile DAG coverage.
- `linkedin-multiproduct/ads-privacy-offline#854` — RTB BLP click event CLOAK pipeline.
- `linkedin-multiproduct/ads-privacy-offline#616` — CLOAK pipeline for survey impressions.
- `linkedin-multiproduct/ads-privacy-offline#578` — CLOAK pipeline for processed survey actions v3.
- `linkedin-multiproduct/ads-privacy-offline#569` — CLOAK implementation for six AVO lift-testing datasets.
- `linkedin-multiproduct/avro-schemas#9449` — randomizationUnitType field in lift test cache update schemas.
- `linkedin-multiproduct/campaign-manager-api#10994` — createdAt for A/B test and Brand Lift test.
- `linkedin-multiproduct/campaign-manager-api#10123` — randomizationUnitType in A/B test API schema.
- `linkedin-multiproduct/li-productivity-agents#9175` — Ads Experiment Copilot agent for Marketing Science team.

## Verification

Before finalizing:

1. Confirm source path exists and parse count is nonzero.
2. Check the draft for outside-work terms in public-facing copy. It is okay for internal notes to say "outside-work/personal automation" generically, but public copy should not mention personal projects unless requested:

```bash
for term in gbrain Hermes tonyxu-blog garrytan NousResearch; do
  grep -i "$term" /tmp/linkedin_profile_work_scope_from_linkedin_github_prs.md && echo "forbidden:$term"
done
```

3. Avoid private/internal links in public-facing copy. Keep PR links only in the evidence appendix unless Tony asks to include them.
4. If writing a file, use a clear path such as:

```text
/tmp/linkedin_profile_work_scope_from_linkedin_github_prs.md
```

## Anti-Patterns

- Do not mention gbrain, Hermes Agent, Tony's personal blog, public OSS PRs, or personal automation work in a LinkedIn work profile unless explicitly requested.
- Do not infer impact metrics not present in the export.
- Do not turn PR titles into an acronym soup. Translate into recruiter-readable domains: experimentation, measurement, privacy-safe data systems, reliable pipelines, API/schema evolution.
- Do not expose internal repo URLs in a public copy block by default.
- Do not claim ownership of team/company outcomes beyond what the PR evidence supports.
