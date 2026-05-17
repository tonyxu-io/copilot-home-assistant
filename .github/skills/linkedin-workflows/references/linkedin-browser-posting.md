# Archived source: `linkedin-browser-posting`

Browser posting is one LinkedIn execution path.

Original skill path: `/home/tonyxu/.hermes/skills/social-media/linkedin-browser-posting`

---

# LinkedIn Browser Posting

Use when Tony explicitly asks to post a drafted update to LinkedIn.

## Safety contract

- Posting is an external public side effect. Only post after Tony explicitly asks to post the final text.
- Do not silently revise the text during posting. Save the exact post text to a temp file and use that file.
- After posting, verify LinkedIn reports success and the new post text appears in the feed.
- If the composer is open but the Post button is disabled, stop and report; do not keep random-clicking.

## Environment

Tony's LinkedIn login is available through local Chrome DevTools Protocol:

```bash
npx -y bb-browser --port 9222 --json open https://www.linkedin.com/feed/ --tab
```

Known caveat: `bb-browser` can snapshot LinkedIn's SDUI/interop composer and show refs like `textbox "Text editor for creating content"`, but `bb-browser fill/type/click` may fail with errors like:

```text
Unknown ref xpath: div[1]/div/div/div/div[2]/div/div[2]/div[1]/div/div/div/div/div/div/div[1]
```

When that happens, use Chrome DevTools Protocol accessibility nodes as the fallback.

## Workflow

1. Save the exact post text:

```bash
cat > /tmp/linkedin_post.txt <<'EOF'
...exact post text...
EOF
```

2. Open LinkedIn feed with the normal post composer pre-activated, then snapshot:

```bash
npx -y bb-browser --port 9222 --json open 'https://www.linkedin.com/feed/?shareActive=true' --tab
sleep 3
npx -y bb-browser --port 9222 --json snapshot -i -c -d 8 --tab <tab>
```

Prefer `feed/?shareActive=true` over `/post/new/`: LinkedIn currently redirects `/post/new/` to the article editor (`/article/new/`), not the normal feed post composer.

3. If the composer is not already open, click `Start a post` from the latest snapshot. If ref clicks fail, locate the visible button by JS and click it:

```bash
npx -y bb-browser --port 9222 --json eval '(() => {
  const btn=[...document.querySelectorAll("button,[role=button],div")]
    .find(e => (e.innerText||"").trim()==="Start a post");
  if (!btn) return {ok:false, reason:"no Start a post"};
  btn.scrollIntoView({block:"center"});
  btn.click();
  return {ok:true};
})()' --tab <tab>
```

4. Verify the composer exists. The snapshot should include:

```text
button "Dismiss"
button "Tony Xu Post to Anyone"
textbox "Text editor for creating content"
button "Schedule post"
button "Post"   # may be disabled before text is inserted
```

5. If `bb-browser type/fill` fails on the textbox ref, use a CDP + Accessibility fallback. This resolves the LinkedIn composer textbox by AX name, types the exact file content, verifies the Post button is enabled, clicks it, then verifies success:

```javascript
// /tmp/linkedin_post_ax.js
const fs = require('fs');
const post = fs.readFileSync('/tmp/linkedin_post.txt','utf8');
async function getWsUrl(){
  const tabs=await (await fetch('http://127.0.0.1:9222/json')).json();
  const tab=tabs.find(t=>(t.url||'').includes('linkedin.com/feed'));
  if(!tab) throw new Error('LinkedIn feed tab not found');
  return tab.webSocketDebuggerUrl;
}
class CDP{
  constructor(ws){
    this.ws=ws; this.id=1; this.p=new Map();
    ws.onmessage=e=>{const m=JSON.parse(e.data); if(m.id&&this.p.has(m.id)){const {res,rej}=this.p.get(m.id); this.p.delete(m.id); m.error?rej(new Error(JSON.stringify(m.error))):res(m.result)}};
  }
  send(method,params={}){const id=this.id++; this.ws.send(JSON.stringify({id,method,params})); return new Promise((res,rej)=>this.p.set(id,{res,rej}));}
}
function v(x){return x&&typeof x==='object'&&'value'in x?x.value:x}
(async()=>{
  const ws=new WebSocket(await getWsUrl());
  await new Promise((r,j)=>{ws.onopen=r; ws.onerror=j});
  const c=new CDP(ws);
  await c.send('Runtime.enable');
  await c.send('DOM.enable');
  await c.send('Accessibility.enable');

  let ax=await c.send('Accessibility.getFullAXTree',{});
  let editor=ax.nodes.find(n=>v(n.role)==='textbox' && v(n.name)==='Text editor for creating content');
  if(!editor) throw new Error('composer editor not found');

  let obj=await c.send('DOM.resolveNode',{backendNodeId:editor.backendDOMNodeId});
  await c.send('Runtime.callFunctionOn',{
    objectId:obj.object.objectId,
    functionDeclaration:`function(text){
      this.focus();
      const sel=window.getSelection();
      const range=document.createRange();
      range.selectNodeContents(this); sel.removeAllRanges(); sel.addRange(range);
      document.execCommand('delete', false, null);
      const dt = new DataTransfer(); dt.setData('text/plain', text);
      const ev = new ClipboardEvent('paste', {clipboardData: dt, bubbles:true, cancelable:true});
      this.dispatchEvent(ev);
      if(!(this.innerText||'').includes(text.slice(0,30))) document.execCommand('insertText', false, text);
      this.dispatchEvent(new InputEvent('input', {bubbles:true, inputType:'insertText', data:text}));
      return {innerText:this.innerText, active:document.activeElement===this};
    }`,
    arguments:[{value:post}], awaitPromise:true, returnByValue:true, userGesture:true
  });

  await new Promise(r=>setTimeout(r,1500));
  ax=await c.send('Accessibility.getFullAXTree',{});
  const ed2=ax.nodes.find(n=>v(n.role)==='textbox' && v(n.name)==='Text editor for creating content');
  const postBtn=ax.nodes.find(n=>v(n.role)==='button' && v(n.name)==='Post');
  if(!ed2 || !String(v(ed2.value)||'').includes(post.slice(0,30))) throw new Error('post text not inserted');
  if(!postBtn) throw new Error('Post button not found');
  if((postBtn.properties||[]).some(p=>p.name==='disabled' && v(p.value)===true)) throw new Error('Post button disabled');

  const btnObj=await c.send('DOM.resolveNode',{backendNodeId:postBtn.backendDOMNodeId});
  await c.send('Runtime.callFunctionOn',{objectId:btnObj.object.objectId,functionDeclaration:`function(){ this.click(); return this.innerText; }`,awaitPromise:true,returnByValue:true,userGesture:true});
  await new Promise(r=>setTimeout(r,4000));
  const final=await c.send('Runtime.evaluate',{expression:`(() => ({success:(document.body.innerText||'').includes('Post successful'), hasText:(document.body.innerText||'').includes(${JSON.stringify(post.slice(0,30))}), body:(document.body.innerText||'').slice(0,2000)}))()`,returnByValue:true});
  console.log(JSON.stringify(final.result.value,null,2));
  ws.close();
})().catch(e=>{console.error(e.stack||e); process.exit(1)});
```

Run:

```bash
node /tmp/linkedin_post_ax.js
```

6. Success criteria:

The output should include both:

```json
{
  "success": true,
  "hasText": true
}
```

Or the page body should contain:

```text
Post successful. View post
```

and the beginning of the posted text in the feed under `Tony Xu • You`.

## Pitfalls

- LinkedIn may render the composer through `#interop-outlet` / preload iframe. Coordinate clicks can focus the wrong invisible container; AX nodes are more reliable.
- `/post/new/` is not a reliable shortcut for feed posts; it can open `/article/new/` and show the article editor/onboarding modal. Use `https://www.linkedin.com/feed/?shareActive=true` for a standard post composer.
- If search/autocomplete focus is open after loading the feed, the post composer may still exist lower in the AX tree; use snapshot refs around `textbox "Text editor for creating content"` rather than assuming top-of-page focus means failure.
- `document.querySelector('[contenteditable=true]')` may return nothing even when the AX tree has a textbox. Use `Accessibility.getFullAXTree` and `DOM.resolveNode` by `backendDOMNodeId`.
- `Runtime.callFunctionOn` may return an unchanged `innerText` immediately, but the AX value can update after the paste/input event. Re-read AX after a short delay.
- The composer may insert extra blank lines internally; verify feed rendering, not only raw editor HTML.
