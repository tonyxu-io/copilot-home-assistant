# GBrain Apple Notes import and embedding notes

Context from a session where Tony asked why Apple Notes content was not visible in gbrain.

## Observed state

- Local mirror existed: `/home/tonyxu/brain/sources/AppleNotes`.
- Local mirror had 534 Markdown files and about 1.08 MB of Markdown content.
- `gbrain sources list` only showed the default federated source at `/home/tonyxu/brain`.
- Initial `gbrain search "sources/AppleNotes" --limit 10` returned `No results`.
- Initial `gbrain search "Apple Notes" --limit 10` mostly returned unrelated Gmail digests.
- `/home/tonyxu/brain/Import Dashboard.md` linked Apple Notes as source mirror and documented cleanup commands.
- `/home/tonyxu/brain/sources/AppleNotes/README.md` explicitly says it is a source mirror, not the durable knowledge layer.

## Useful commands

```bash
python3 - <<'PY'
from pathlib import Path
root = Path('/home/tonyxu/brain/sources/AppleNotes')
files = list(root.rglob('*.md'))
print('exists', root.exists(), 'is_dir', root.is_dir())
print('md_count', len(files))
print('total_bytes', sum(p.stat().st_size for p in files))
for p in files[:20]:
    print(p.relative_to('/home/tonyxu/brain'))
PY

gbrain search "sources/AppleNotes" --limit 10
gbrain search "Apple Notes Mirror" --limit 10

gbrain import /home/tonyxu/brain/sources/AppleNotes --no-embed
gbrain embed --stale

gbrain stats
gbrain search "Apple Notes Mirror" --limit 5
gbrain query "Apple Notes second brain PARA" --no-expand
```

## Result from import

`gbrain import /home/tonyxu/brain/sources/AppleNotes --no-embed` imported:

- 534 pages
- 647 chunks
- 0 skipped
- 0 errors

Post-import stats in that session:

- Pages rose to 24659
- Chunks rose to 34400
- Embedded initially remained behind, then rose as `gbrain embed --stale` ran

## Important pitfall

Do not rely only on full path search. Subdirectory imports may normalize slugs differently:

- `sources/AppleNotes/README.md` appeared as slug `readme`
- `Imported Notes/Root Notes/My Second Brain in Apple Notes (PARA Method)  Part 4.md` appeared as `imported-notes/root-notes/my-second-brain-in-apple-notes-para-method-part-4`
- Some notes did appear with `sources/applenotes/...` or `applenotes/...` prefixes in hybrid query results

So verify with known title/content searches, not only `gbrain get sources/AppleNotes/...`.

## User-facing diagnosis template

If local files exist but gbrain cannot search them:

> Apple Notes was present in the local brain source mirror, but not imported/embedded into the gbrain DB. I imported the mirror and started stale embedding refresh. Search should now work by note title/content; semantic query improves as embeddings finish.
