# X Composer Automation Pitfalls — 2026-05-01

Session learning from trying to post a short Chinese X post through Tony's logged-in browser.

## What failed

- `bb-browser fill <textbox-ref> <text>` reported success, but the Draft.js editor remained empty and `tweetButtonInline` stayed disabled.
- `bb-browser type` and very slow per-character typing made text visible in `data-testid="tweetTextarea_0"`, but the Post button still had `disabled` and `aria-disabled="true"`.
- CDP synthetic insertion paths (`Input.insertText`, custom paste/input events, `document.execCommand('insertText')`) also failed to make X's React/Draft.js state accept the draft.
- Forcing the DOM button enabled and clicking did not post.
- Direct web GraphQL mutation returned:

```json
{
  "code": 226,
  "message": "Authorization: This request looks like it might be automated. To protect our users from spam and other malicious activity, we can't complete this action right now. Please try again later. (226)"
}
```

## Correction from Tony

Tony correctly pointed out that the disabled X Post button was because the composer had not recognized input content. Do not jump straight to "X risk control" when the button is disabled. First prove the editor state is accepted by Draft.js:

- editor contains the exact intended text
- `tweetButtonInline.disabled === false`
- `aria-disabled !== "true"`

The working direction is to make input human-equivalent enough for Draft.js/React state, not to mutate DOM or force-enable the button.

## Useful diagnostics

Check editor and button state:

```js
(() => {
  const ed = document.querySelector('[data-testid="tweetTextarea_0"]');
  const btn = document.querySelector('[data-testid="tweetButtonInline"]');
  return {
    editor: ed?.innerText,
    length: ed?.innerText?.length,
    disabled: btn?.disabled,
    ariaDisabled: btn?.getAttribute('aria-disabled')
  };
})()
```

If text is visible but `disabled: true`, treat it as not postable by automation.

## Recommended fallback

Leave the text in the composer if possible and ask Tony to manually click Post. Do not keep retrying GraphQL or random DOM clicks; X spam defenses are sensitive.
