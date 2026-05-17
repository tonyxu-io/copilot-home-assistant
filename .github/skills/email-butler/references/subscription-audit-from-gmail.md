# Subscription / recurring charge audit from Gmail

Use this when Tony asks what monthly subscriptions, recurring bills, memberships, or paid plans he has.

## Default approach

1. Prefer the local Gmail export first; it is faster and avoids noisy live full-mail scans:
   - `/home/tonyxu/brain/sources/gmail/messages/*.json`
2. Search recent windows, usually last 6–12 months, for semantic subscription signals:
   - `subscription`, `monthly`, `membership`, `recurring`, `renewal`, `invoice`, `receipt`, `autopay`, `plan`, `billing`, `charged`.
3. Group by merchant/service, not by raw subject. Separate:
   - active/likely active monthly subscriptions
   - recurring household bills / services
   - usage-based cloud/API invoices
   - annual memberships/domain renewals
   - canceled/on-hold/uncertain items
4. For high-signal items, read full Gmail messages with `gws gmail +read --id ... --format json` to extract price and renewal date. Do not pipe directly into a truncating consumer; `gws` can panic on broken pipe. Write to `/tmp/gmail_<id>.json` first if needed.
5. Report concise caveats: Gmail evidence is not a complete card-statement audit; Apple subscriptions and bank/card statements are needed for a fully authoritative list.

## Useful extraction patterns

Python over local daily exports:

```python
from pathlib import Path
import json, re, html
from email.utils import parsedate_to_datetime

base = Path('/home/tonyxu/brain/sources/gmail/messages')
terms = re.compile(r'\b(subscription|monthly|membership|recurring|renewal|invoice|receipt|autopay|plan|billing|charged)\b', re.I)

for p in base.glob('*.json'):
    data = json.loads(p.read_text(errors='ignore'))
    for m in data.get('messages', []):
        text = html.unescape(' '.join(str(m.get(k, '')) for k in ['from', 'subject', 'snippet']))
        if terms.search(text):
            print(m.get('date'), m.get('from'), m.get('subject'), m.get('snippet'))
```

Full-message detail pattern:

```bash
id=GMAIL_MESSAGE_ID
bash -lic "/home/linuxbrew/.linuxbrew/bin/gws gmail +read --id $id --format json > /tmp/gmail_$id.json"
python3 - <<'PY'
import json, re
s = open('/tmp/gmail_GMAIL_MESSAGE_ID.json', errors='ignore').read()
print(re.findall(r'\$\s?\d[\d,]*(?:\.\d{2})?', s)[:20])
print(re.findall(r'renews?.{0,100}|renewal.{0,100}|monthly.{0,100}|membership.{0,140}', s, re.I)[:20])
PY
```

## Interpretation rules

- `Apple <no_reply@email.apple.com>` receipts often bundle multiple subscriptions; extract the individual product lines (`iCloud+`, `Google Photos`, app subscriptions) rather than calling the whole thing “Apple”.
- `ChatGPT - Your plan will not renew` means not active after the stated billing-period end, even if there are marketing emails for Pro.
- `Blue Bottle Your Subscription's on Hold`, Descript refund/cancel threads, and similar emails belong in “on hold / canceled / uncertain”, not active.
- Cloud/API bills (`AWS`, `Cloudflare`, `OpenRouter`, `X Developer Platform`, `Z.ai`) may be monthly/usage-based rather than fixed subscriptions; label them as such unless the email states a fixed cadence and price.
- Domain renewals and Costco-style memberships are recurring but usually annual; do not mix them into monthly totals.
- Autopay utilities/landscaping are recurring bills, not optional software subscriptions; keep them in a separate bucket.

## Output style for Tony

Keep it short and mobile-first:

- `确定在续的` — name, price/cadence, last evidence date.
- `看起来是 recurring / paid plan` — name, evidence, uncertainty.
- `不是 active monthly / 已停或不确定` — name and why.
- End with one caveat if needed: “这不是完整信用卡账单审计，只是 Gmail receipts/subscription emails.”
