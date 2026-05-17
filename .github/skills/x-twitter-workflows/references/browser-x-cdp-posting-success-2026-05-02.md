# Browser CDP X posting success pattern (2026-05-02)

Context: local Debian did not have a usable Chromium earlier, but `127.0.0.1:9222` later pointed at Tony's Mac Chrome via CDP tunnel. Posting succeeded using Chrome DevTools Protocol directly through `chrome-remote-interface`.

## Working sequence

1. Save final post text to a temp file and verify length first.
2. Check CDP availability:

```bash
curl -sS http://127.0.0.1:9222/json/version
```

3. Use `Target.createTarget({url:'https://x.com/compose/post'})` to open composer in the logged-in Chrome.
4. Wait for `[data-testid="tweetTextarea_0"]`.
5. Use real CDP mouse events to click the editor's bounding-box center.
6. Clear existing text with real key events (`Ctrl+A`, `Backspace`).
7. Use `Input.insertText({text})` only after the editor is focused.
8. Verify both Draft.js-visible editor text and button state:

```js
(() => {
  const ed = document.querySelector('[data-testid="tweetTextarea_0"]');
  const btn = document.querySelector('[data-testid="tweetButtonInline"], [data-testid="tweetButton"]');
  return {
    editor: ed?.innerText || '',
    disabled: !!btn?.disabled,
    aria: btn?.getAttribute('aria-disabled') || null,
    btnText: btn?.innerText || ''
  };
})()
```

9. Click the Post button with real CDP mouse events.
10. Verify the post appears in the home/profile feed, not just that the click happened. Successful signal observed: `Your post was sent.` plus the new post text under `Tony Xu @t0nyxu · 1s`.

## Pitfall avoided

Do not force-enable the Post button or call X GraphQL directly. If the button is disabled, Draft.js has not accepted the content; fix focus/input first.

## When `Input.insertText` leaves editor empty (observed 2026-05-15)

Even after clicking the textarea center and calling `Input.insertText`, Draft.js sometimes shows `editor.innerText === "\n"` and the Post button stays disabled. `document.activeElement` was a wrapper `<div role="group">`, not the contenteditable.

**Working fallback:** dispatch a synthetic `paste` ClipboardEvent with a DataTransfer payload directly on the textarea. Draft.js handles paste reliably even when insertText / per-character key events fail.

```js
const ed = document.querySelector('[data-testid="tweetTextarea_0"]');
ed.focus();
const dt = new DataTransfer();
dt.setData('text/plain', text);
ed.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
// verify ed.innerText === text and tweetButtonInline is enabled before clicking
```

After this, a normal `btn.click()` from page context posts successfully (toast `Your post was sent.` appears). CDP mouse-click on the button's bbox can fail silently if coordinates are off — `btn.click()` from page JS is more reliable once focus/state is correct.

## Minimal Node skeleton

```js
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const text = fs.readFileSync('/tmp/x_post.txt','utf8').trim();
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Browser target: 127.0.0.1:9222
// Use Target.createTarget -> Runtime/Page/DOM/Input.
// Click editor center with Input.dispatchMouseEvent.
// Clear with Input.dispatchKeyEvent Ctrl+A + Backspace.
// Insert with Input.insertText({text}).
// Verify editor text exactly equals `text` and button is enabled.
// Click button center and verify feed/toast text.
```
