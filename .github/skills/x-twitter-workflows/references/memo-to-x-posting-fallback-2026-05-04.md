# Memo-to-X posting fallback notes (2026-05-04)

Context: Tony asked to post a just-captured personal memo to X: `庆祝吴宜泽获得斯诺克世锦赛冠军！`.

## What worked

- First saved the `memo:` content through `limemo-capture` before attempting the public side effect.
- Verified the post text length cheaply before posting: 16 chars.

## What failed

- Local/Mac Chrome CDP was unavailable:
  - `curl http://127.0.0.1:9222/json/version` failed to connect.
  - `npx -y bb-browser --port 9222 --json status` returned `{"running":false}`.
  - Recreating the documented Debian → Mac Chrome tunnel failed with `Permission denied (publickey,password,keyboard-interactive)`.
- Browserbase/non-local X session opened the login flow, so it was not usable for Tony's logged-in X posting.
- `xurl whoami` succeeded, but `xurl post` failed with `CreditsDepleted`; read auth does not imply write credits.

## Future workflow

1. If the source is `memo:`, save the memo first and verify gbrain before posting.
2. For Tony X posting, prefer logged-in Chrome CDP:
   - `curl -sS http://127.0.0.1:9222/json/version`
   - `npx -y bb-browser --port 9222 --json status`
3. If CDP is down, try the documented SSH tunnel only if non-interactive auth works. If it returns permission denied, do not keep poking; report that the browser path is blocked.
4. Only try `xurl post` when Tony explicitly asked to publish and browser posting is blocked; expect `CreditsDepleted` even when `whoami` works.
5. If both paths fail, give Tony the exact pasteable post text and a one-line reason. Do not over-explain.