# Second-brain health loop and raw export safety — 2026-05-03

Session learning from turning Tony's brain/GBrain setup into a more explicit second-brain operating system.

## Second-brain health pattern

When Tony asks for the agent to become a second brain, implement a **control loop**, not just more summaries:

1. Write or update a human-readable operating contract in the brain repo, e.g. `notes/knowledge/tech/ai/second-brain-operating-system.md`.
2. Link it from `/home/tonyxu/brain/README.md` so future agents discover it first.
3. Sync exact pages with `gbrain put <slug> < file.md` and `gbrain embed <slug>`.
4. Run `gbrain embed --stale` if stats show drift, then verify `Embedded == Chunks`.
5. Create a quiet cron health check only if it adds a new layer beyond existing workflow hygiene. For Tony, the useful scope was:
   - `gbrain stats` and embedding drift
   - `scripts/verify_daily_activity_coverage.py --json`
   - activity collector state freshness
   - Email Butler latest state
   - promotion queue size/age
   - git status for inexplicable/sensitive changes
6. Healthy result should be exactly `[SILENT]`; report only material failures or unsafe unexplained changes.

## Raw export / git safety pitfall

Agent Reach/X raw exports and normalized JSONL can contain URL query parameters from third-party links that look like credentials, e.g. `spstoken=...`. These are not necessarily account credentials, but they are still sensitive-looking bearer-ish URL tokens and should not be committed casually.

Before committing brain/source updates:

```bash
cd /home/tonyxu/brain
git add -A
python3 - <<'PY'
import pathlib, re, subprocess, json, sys
paths = subprocess.run(['git','diff','--cached','--name-only'], capture_output=True, text=True, check=True).stdout.splitlines()
patterns = [
    ('private_key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('aws_access_key', re.compile(r'AKIA[0-9A-Z]{16}')),
    ('gh_token', re.compile(r'gh[pousr]_[A-Za-z0-9_]{30,}')),
    ('openai_key', re.compile(r'sk-[A-Za-z0-9]{20,}')),
    ('generic_secret_assignment', re.compile(r'(?i)(api[_-]?key|secret|password|token|cookie)\s*[:=]\s*["\']?[^"\'\s]{20,}')),
]
findings=[]
for rel in paths:
    p=pathlib.Path(rel)
    if not p.exists() or p.is_dir() or p.stat().st_size > 8_000_000:
        continue
    text=p.read_text(errors='ignore')
    for name, pat in patterns:
        if pat.search(text):
            findings.append((rel, name)); break
print(json.dumps({'staged_paths':len(paths),'secret_findings':findings[:50],'finding_count':len(findings)}, indent=2))
if findings:
    sys.exit(2)
PY
```

If findings are in raw/source exports:

- Unstage the risky raw/jsonl files.
- Prefer committing curated markdown/year-grouped summaries and safe CSV/metadata when needed.
- Add generated latest aliases and high-risk raw/jsonl patterns to `.gitignore` when appropriate.
- Do not delete raw files unless Tony approved cleanup; local ignored provenance can remain on disk.

## Verification commands used

```bash
cd /home/tonyxu/brain
python3 -m py_compile scripts/backfill_daily_activity_from_sources.py scripts/verify_daily_activity_coverage.py scripts/collect_activity.py
python3 scripts/verify_daily_activity_coverage.py --json
gbrain stats
git diff --check
```

Avoid large compound verification commands after one gets marked `BLOCKED`; rerun smaller independent checks instead, not the exact blocked command.
