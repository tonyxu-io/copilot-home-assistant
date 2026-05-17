# Archived source: `gbrain-daytime-sync-no-embed`

No-embedding daytime sync is a scoped gbrain import/sync fallback.

Original skill path: `/home/tonyxu/.hermes/skills/productivity/gbrain-daytime-sync-no-embed`

---

# gbrain daytime sync without embeddings

Use this when Gmail/Calendar digest imports fail with OpenAI embedding quota errors such as:
- `429 You exceeded your current quota`
- embedding failures during `gbrain import`

## Goal
Keep Gmail/Calendar sync flowing by rerunning imports with embeddings disabled.

## Steps

1. **Confirm the failure is embedding-related**
   - Look for 429/quota errors in import output.
   - If the failure is unrelated, do not use this workflow.

2. **Run import with embeddings disabled**
   - Add `--no-embed` to the relevant `gbrain import` command.
   - Example:
     ```bash
     gbrain import /home/tonyxu/brain/sources/calendar/digests --json --no-embed
     ```
   - Use the same flag for Gmail imports if they are part of the same daytime sync path.

3. **Verify the rerun**
   - Expect `0 errors`.
   - Accept some `Skipped` items if they were already processed or intentionally skipped.

4. **Restore embeddings later**
   - Remove `--no-embed` only after quota/billing is healthy again.

## Notes
- This is a temporary mitigation, not a fix for the quota issue.
- Do not assume all sync paths need the flag; only apply it to the jobs actually hitting 429s.
