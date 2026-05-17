# Brain repo git sync-all workflow (2026-05-08)

Use this as a concrete recipe when Tony asks to "git同步所有改动" or otherwise wants `/home/tonyxu/brain` local changes committed and pushed to the private GitHub remote.

## Context

- Repo: `/home/tonyxu/brain`
- Remote: `https://github.com/tonyxu-io/tony-brain.git`
- Branch: `main`
- The repo often has a mix of human notes, generated Gmail/Calendar digests, state files, X likes/posts raw exports, and writing drafts.
- Tony explicitly asked for all changes to sync, so committing raw collector outputs was acceptable after safety checks.

## Safe sequence

```bash
cd /home/tonyxu/brain

git branch --show-current
git remote get-url origin
git fetch origin main --prune
git status --short --branch
git diff --stat
git ls-files --others --exclude-standard | wc -l

git add -A
git diff --cached --check
# If this reports whitespace/blank EOF issues, fix only formatting noise and re-stage.

# Run a staged secret scan before committing.
python3 - <<'PY'
import subprocess, re, sys, json
files = subprocess.check_output(['git','diff','--cached','--name-only'], text=True).splitlines()
high=[]; query=[]; path_sensitive=[]
assign_re = re.compile(r'''(?ix)\b(aws_access_key_id|aws_secret_access_key|api[_-]?key|client[_-]?secret|refresh[_-]?token|access[_-]?token|auth[_-]?token|id[_-]?token|session[_-]?token|password|passwd|private[_-]?key|bearer|cookie)\b\s*[:=]\s*['\"]?([A-Za-z0-9_./+=:@%\-]{16,})''')
query_re = re.compile(r'''(?ix)[?&](access_token|refresh_token|auth_token|id_token|api_key|apikey|client_secret|password|session|sid|cookie|ct0|twid|code)=([^\s&"'<>]{8,})''')
private_key_re = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')
for f in files:
    try:
        data = subprocess.check_output(['git','show',f':{f}'], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        continue
    if b'\0' in data[:4096]:
        continue
    text = data.decode('utf-8', errors='ignore')
    if 'notes/records/secrets/' in f or '/secrets/' in f:
        path_sensitive.append(f)
    if private_key_re.search(text):
        high.append((f,'private_key_block'))
    for m in assign_re.finditer(text):
        val=m.group(2)
        if any(x in val.lower() for x in ['redacted','example','placeholder','your_','the_','none','null','false','true']):
            continue
        high.append((f,m.group(1).lower()))
        break
    for m in query_re.finditer(text):
        query.append((f,m.group(1).lower()))
        break
print(json.dumps({
  'staged_files': len(files),
  'high_confidence_secret_hits': len(high),
  'token_query_param_hits': len(query),
  'sensitive_paths': len(path_sensitive),
  'high_files': sorted(set(x[0] for x in high))[:50],
  'query_files': sorted(set(x[0] for x in query))[:50],
  'sensitive_path_files': sorted(set(path_sensitive))[:50],
}, indent=2))
if high or query or path_sensitive:
    sys.exit(2)
PY

git commit -m "chore: sync brain updates"
git push origin main

git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git branch -r --contains HEAD
git diff --check
git ls-files --others --exclude-standard | wc -l
```

## Pitfalls

- `git diff --check` can fail on generated Markdown trailing whitespace or extra blank lines at EOF. Fix formatting deterministically, not content.
- A broad `git add -A` is acceptable only when Tony explicitly asks to sync all changes. For X/LinkedIn draft PRs, do **not** use broad staging; stage only the draft file.
- Do not print secret values. The scan should report counts and file paths only.
- If the repo is ahead of origin before the new commit, pushing will publish earlier local commits too. Say so if it matters; in this session main was already ahead before the sync commit.

## Verification result from session

- Staged files: 257
- Secret scan: 0 high-confidence hits, 0 token-query hits, 0 sensitive paths
- Commit: `90f40738 chore: sync brain updates`
- Push: `main -> origin/main`
- Final check: local `HEAD` equaled `origin/main`; worktree clean; untracked count 0.
