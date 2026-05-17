# Tony Gmail noisy source notes

Session-derived heuristics for inbox cleanup and noise audits. Keep counts as evidence, not as permanent truth; rerun live queries before action.

## Safe-ish archive candidates after explicit Tony authorization

Archive means remove `INBOX` only. Do not delete, mark read, or remove other labels.

- Synology / DigitalOne machine notifications
  - Query shape: `in:inbox (synology OR digitalone OR from:digital1.dev)`
  - Evidence: historical export showed DigitalOne/Synology as one of the largest noise sources; Tony authorized archiving Synology.
- Redfin real-estate listing/home-report updates
  - Query shape: `in:inbox redfin` or `in:inbox from:redfin.com`
  - Evidence: Tony authorized archiving Redfin; historical export showed many Redfin home-report/listing updates.
- USPS Informed Delivery daily digest
  - Query shape: `in:inbox (from:email.informeddelivery.usps.com OR from:informeddelivery.usps.com OR "Informed Delivery Daily Digest" OR "Your Daily Digest")`
  - Low-risk if phrased as daily digest; avoid USPS change-of-address or package exception notices unless user asks.
- Amazon / shopping logistics
  - Query shape: `in:inbox (from:amazon.com OR subject:(shipped OR delivered OR receipt OR order))`
  - Safer to narrow to receipts/shipping/delivered; do not archive disputes, returns requiring action, or account/security alerts blindly.
- Apple receipts
  - Query shape: `in:inbox from:email.apple.com subject:(receipt OR invoice)`
- GitHub bot notifications
  - Query shape: `in:inbox from:github.com (Copilot OR "workflow" OR "run failed" OR "PR #")`
  - Caution: failed workflows / mentions may be actionable; consider keeping failures in `Ops/Infrastructure` or `Action Needed`.

## High-noise but conservative categories

Do not mass-archive without narrower rules or explicit confirmation:

- Finance/security: Fidelity, BoA, Chase, PayPal, Venmo, Mint, TurboTax, PenFed, Google security alerts.
- Family/school: Bloomz, school, kids, Han/family threads.
- Travel confirmations: airlines, hotels, Airbnb, Amex travel.

## Implementation reminders

- `resultSizeEstimate` can be misleading for complex Gmail queries. For action, paginate actual `messages` IDs until `nextPageToken` is empty.
- Verify after archive with both the combined query and each separate term.
- Report only counts and action boundary: “removed INBOX only; no delete; no mark-read.”
