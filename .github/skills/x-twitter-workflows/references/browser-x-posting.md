# Browser-based X posting notes

Use this when posting to X through Tony's logged-in browser session instead of the X API.

## Draft.js composer behavior

X's composer is Draft.js-based. DOM text can appear in `[data-testid="tweetTextarea_0"]` while the internal Draft.js state is still empty. Symptom: the text is visible, but the `Post` button remains disabled (`data-testid="tweetButtonInline"`, `disabled=true`, `aria-disabled=true`).

Avoid relying on:
- `bb-browser fill` into the composer
- direct `innerText` / `innerHTML` mutation
- synthetic `input` / `paste` events only
- direct GraphQL `CreateTweet` calls (often returns 226 automated request)

Prefer real browser input:
1. Open `https://x.com/compose/post` in the logged-in browser session.
2. Click the editor `[data-testid="tweetTextarea_0"]` with real CDP mouse events or bb-browser `click`.
3. Select existing composer text with real key events (`Ctrl+A`/`Cmd+A`) and delete.
4. Insert text using CDP `Input.insertText` while the editor is actually focused, or use bb-browser `type` after a real click.
5. Verify both:
   - editor text equals desired text
   - `document.querySelector('[data-testid="tweetButtonInline"]').disabled === false`
6. Only then click `Post` and verify the new post appears in profile/feed.

If focus lands on an overlay/group instead of the editor, input may visually mutate the DOM but not Draft.js state. Re-click the editor coordinates and retry.

## Copy style for Tony

For Chinese X posts, keep it concise and declarative. Avoid low-signal self-referential starts like “我一直觉得”; lead with the claim.