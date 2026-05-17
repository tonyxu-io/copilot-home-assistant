# Archived source: `gbrain-cli-recovery`

CLI recovery is one operational subsection of the broader gbrain maintenance workflow.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-cli-recovery`

---

Use when `gbrain` is missing/broken after `gbrain upgrade` or a package-manager update, especially on Bun-based installs.

## Judgment

The `gbrain` CLI Tony uses comes from GitHub (`garrytan/gbrain`), not the npm registry package named `gbrain`. The npm package is a different ML library and can overwrite the CLI.

## Steps

1. Verify the breakage.
   - Run `which gbrain || true`
   - Run `gbrain --version || true`
   - If `gbrain upgrade` complains about missing `package.json`, treat it as an updater bug, not a local project issue.

2. Remove the wrong package if needed.
   - Bun global install case: `bun remove -g gbrain`
   - Confirm `which gbrain` no longer points to the broken binary.

3. Reinstall or update using the current upstream install path.
   - Fetch the latest agent instructions first:
     `python3 - <<'PY'\nimport urllib.request; print(urllib.request.urlopen('https://raw.githubusercontent.com/garrytan/gbrain/master/INSTALL_FOR_AGENTS.md', timeout=30).read().decode())\nPY`
   - Current upstream guidance says **do not** use Bun global GitHub install for normal installs; use clone + link so postinstall/migrations work:
     ```bash
     git clone https://github.com/garrytan/gbrain.git ~/gbrain  # if absent
     cd ~/gbrain
     git fetch origin --prune
     git checkout -B <working-branch> origin/master
     bun install
     bun link
     ```
   - If an old global package shadows the linked checkout, remove it first:
     `bun remove -g gbrain`, then rerun `cd ~/gbrain && bun link`.
   - If preserving Tony's local Copilot embedding PR before upstream merge, start from `origin/master` and cherry-pick/port the embedding-provider commit, then `bun install && bun link`.

4. Verify recovery.
   - `which gbrain`
   - `gbrain --version`
   - `readlink -f $(which gbrain)`
   - Current expected install shape is `~/.bun/bin/gbrain` symlinked to `/home/tonyxu/gbrain/src/cli.ts`, version matching `~/gbrain/package.json`.
   - If the CLI says `Permission denied`, make the source CLI executable: `chmod +x ~/gbrain/src/cli.ts`. To avoid dirty git status from executable-bit drift in this working checkout, `cd ~/gbrain && git config core.filemode false`.

## Pitfalls

- Do not trust npm version numbers for this CLI. Same package name, wrong project.
- `gbrain upgrade` may route to the wrong package source and self-corrupt the installation.
- Old advice to `bun add -g github:garrytan/gbrain` is now inferior for installs because Bun blocks top-level postinstall hooks on global installs; prefer clone + `bun link` per `INSTALL_FOR_AGENTS.md`.
- `gbrain init` with no URL can rewrite `~/.gbrain/config.json` to PGLite. For Tony's self-hosted Postgres, immediately re-run `bash -lic 'source ~/.bashrc >/dev/null 2>&1; gbrain init --url "$GBRAIN_DATABASE_URL"'` and verify config.
- If the user asks for a version that does not exist on npm, check whether they really mean a Git tag/commit.

## Verification

Recovery is complete only if:
- `which gbrain` resolves to the Bun shim path
- `readlink -f $(which gbrain)` resolves to the intended checkout or installed GitHub package
- `gbrain --version` returns the GitHub CLI version expected from that checkout
- Running `gbrain config show`, `gbrain doctor --json`, `gbrain stats`, and a real `gbrain query "..."` works without package-manager errors
