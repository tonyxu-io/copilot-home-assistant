# Remote Chrome CDP SSH tunnel — Debian → MacBook Pro

Use this when browser automation on the Debian box cannot find or connect to local Chrome/CDP, but Tony's MacBook Pro has a logged-in Chrome session exposing CDP on `127.0.0.1:9222`.

## Mac launch command

Run on Tony's MacBook first, using a dedicated debug profile so CDP is exposed cleanly:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.hermes/chrome-debug" \
  --no-first-run \
  --no-default-browser-check &
```

## Tunnel command

Run from the Debian box:

```bash
ssh -fN \
  -M -S ~/.ssh/chrome-192.168.0.71-9222.sock \
  -L 127.0.0.1:9222:127.0.0.1:9222 \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  tonyxu@192.168.0.71
```

## Verify

```bash
curl -sS http://127.0.0.1:9222/json/version | jq .
npx -y bb-browser --port 9222 --json status
curl -sS http://127.0.0.1:9222/json/list | jq '.[].url'
```

A healthy tunnel should make Debian's `127.0.0.1:9222` behave like the Mac Chrome CDP endpoint. Note: `bb-browser --json status` can still report `{"running":false}` even when raw CDP is reachable; trust `curl /json/version` and operate with `chrome-remote-interface` if needed.

## Stop / inspect

Because the command uses SSH control master mode:

```bash
ssh -S ~/.ssh/chrome-192.168.0.71-9222.sock -O check tonyxu@192.168.0.71
ssh -S ~/.ssh/chrome-192.168.0.71-9222.sock -O exit tonyxu@192.168.0.71
```

If the control socket is stale, remove it and recreate the tunnel:

```bash
rm -f ~/.ssh/chrome-192.168.0.71-9222.sock
```

## Pitfalls

- The Mac must have Chrome running with remote debugging enabled on `127.0.0.1:9222`; use the dedicated `--user-data-dir="$HOME/.hermes/chrome-debug"` command above when starting from scratch.
- If Debian already has something bound to `127.0.0.1:9222`, the tunnel should fail fast because of `ExitOnForwardFailure=yes`.
- If SSH reports `Permission denied`, the fix is on the Mac/SSH side; do not keep retrying the tunnel. Ask Tony to start Chrome with the debug command or repair SSH auth.
- `bb-browser --port 9222 --json status` may say `running:false` even when `curl http://127.0.0.1:9222/json/version` shows a healthy Chrome. In that case, use raw CDP via `chrome-remote-interface` against a page target from `/json/list`.
- Do not switch to a fresh Browserbase/new Chrome session for Tony's X posting unless explicitly requested; it may not share Tony's logged-in X session.
