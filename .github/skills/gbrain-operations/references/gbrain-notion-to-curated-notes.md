# Notion Exports to Curated Brain Notes

Session-derived runbook for converting local Notion exports under `/home/tonyxu/brain/sources/notion` into Tony-readable notes and gbrain-searchable chunks.

## Source layout seen

- `/home/tonyxu/brain/sources/notion/personal/index.json`
- `/home/tonyxu/brain/sources/notion/personal/digest.md`
- `/home/tonyxu/brain/sources/notion/personal/databases/*.json`
- `/home/tonyxu/brain/sources/notion/family/index.json`
- `/home/tonyxu/brain/sources/notion/family/digest.md`
- `/home/tonyxu/brain/sources/notion/family/databases/*.json`

Useful database examples:

- Personal: `Life Timeline`, `Events`, `Inventory`, `Gift Ideas`, bookmarks/interview prep.
- Family: `Caring Schedule`, `Moments`, `Trips`, `Destinations`, `Itinerary`, `Schools Table`, inventory, finance/home ledgers.

## Curation pattern

1. Treat `/sources/notion` as raw provenance, not the reading layer.
2. Inspect `index.json` for database names/item counts, then open focused database JSON files for structured fields.
3. Promote durable, human-readable summaries into:
   - `notes/family/` for family, travel, child planning, profile/timeline.
   - `notes/records/` for inventory, finance, admin/home records.
   - `notes/knowledge/sources/` for source maps/navigation notes.
   - `people/` or `projects/` only when the source clearly updates a durable entity/project page.
4. Redact or omit secrets and sensitive identifiers. Do not copy raw serial numbers, order numbers, receipt URLs, payment/account identifiers, signed URLs, recovery/admin details, or exact balances unless explicitly needed.
5. Use concise frontmatter:
   ```md
   ---
   tags:
     - notion
     - <topic>
   updated: YYYY-MM-DD
   ---
   ```
6. Prefer summaries over raw dumps. For inventory and finance, summarize scope/categories and leave exact records in source exports.
7. Read back touched notes before importing.

## Import/embed verification

Use narrow imports where possible:

```bash
gbrain import /home/tonyxu/brain/notes/family --no-embed
gbrain import /home/tonyxu/brain/notes/records --no-embed
gbrain import /home/tonyxu/brain/notes/knowledge/sources --no-embed
gbrain embed --stale
gbrain stats
```

Verify with content queries, not only exact slugs/titles:

```bash
gbrain search "Family Baby and Leave Planning Han Parental Leave" --limit 5
gbrain search "Childcare and School Research Silicon Valley International School" --limit 5
gbrain search "Notion Source Map personal workspace family workspace" --limit 5
```

## Pitfalls observed

- `gbrain search` may fail for exact slug/title queries even when content is imported and embedded. Use distinctive content phrases for verification.
- `gbrain import` can exit `0` while reporting per-file errors. Read the import summary and warnings, not just the exit code.
- Broad imports may surface unrelated existing bad files, e.g. invalid slug warnings for non-ASCII/private notes. If the target notes were imported and embedded, report the warning separately instead of treating the whole import as failed.
- Tool output can be truncated; rerun focused parsing/reads when the exact database contents matter.

## Notes created in the reference session

- `notes/family/Tony Life Timeline.md`
- `notes/family/Family Baby and Leave Planning.md`
- `notes/family/Family Travel Index from Notion.md`
- `notes/family/Childcare and School Research.md`
- `notes/records/Personal and Family Inventory Overview.md`
- `notes/records/Family Home and Finance Records from Notion.md`
- `notes/knowledge/sources/Notion Source Map.md`
- Updated `notes/family/Tony Profile.md`
