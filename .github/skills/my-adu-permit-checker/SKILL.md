---
name: my-adu-permit-checker
description: "Checks the status of my ADU project for 122 Walnut St, Menlo Park, CA 94025. Provides updates on permit status, and detailed status for each phase of the project. Activates when user asks for 'my ADU permit status', 'check my ADU project', 'update on my ADU permit', or mentions wanting to know 'how's my ADU project going'."
---

# My ADU Permit Checker

Summarize latest updates on the ADU project for 122 Walnut St, Menlo Park, CA 94025, including permit status and processing status details.

## Workflow

1. Use "agent-browser" skill to open https://aca-prod.accela.com/MENLOPARK/Cap/CapHome.aspx?module=Building&TabName=Home (Must be exactly this URL, can't be changed)
2. Put "BLD2025-01110" in "Record Number" field and click search
   - If `browser_click` on the Search link appears to do nothing, first verify the record number is still in `ctl00_PlaceHolderMain_generalSearchForm_txtGSPermitNumber` via JS.
   - If still stuck on `CapHome.aspx`, clear the default Start/End Date fields if needed, then dispatch a DOM click on `#ctl00_PlaceHolderMain_btnNewSearch` or run its postback through page JS. After submission, inspect `location.href` and `document.body.innerText`; Accela may navigate only after the JS-dispatched click, not the accessibility click.
3. Check overall status of the permit application
4. Click "Record Info" dropdown button and click "Processing Status" to see detailed status for review stages.
5. On the Processing Status page, do not rely only on the visible summary rows. Expand each relevant review row and inspect the underlying entries/comments. In this Accela UI, the compact snapshot often truncates, merges labels, or even briefly reports an empty page, so use browser JS/DOM inspection aggressively to extract the real task history.
6. Reliable extraction pattern for this Accela page:
   - Use browser JS/DOM inspection aggressively; the accessibility snapshot may briefly show `Empty page` right after search even when the record detail page actually loaded.
   - If that happens, read `location.href`, `document.title`, and `document.body.innerText` with `browser_console` to confirm the record page and overall status before doing anything else.
   - The `Processing Status` tab content is often already present in the DOM under `#tab-processing_status`, `#ctl00_PlaceHolderMain_divWorkflow`, or `#ctl00_PlaceHolderMain_divProcessStatus` even if it is not exposed cleanly as clickable UI.
   - Prefer extracting from those containers' `innerText` first; this often yields the full task history without needing to expand individual rows.
   - Find stage text for labels like `Application Intake`, `Routing`, `PW Engineering Review`, `Flood Review`, `Building Review`, `Detailed Planning Review`, `High Level Planning Review`, `MP Municipal Water Review`, and `Review Decision`, then slice bounded text blocks around each label.
   - If needed, still extract each stage row's expand-link id from its HTML (`lnk_<guid>`) and click those links via JS, but treat that as fallback rather than the default path.
   - Expect some bleed/duplication between neighboring stages; trust explicit `Comment:` lines, the newest due/completed entries, and direct date checks more than raw row grouping.
   - For quick no-change verification, directly test for the known current markers in DOM text: overall status `Pending Resubmittal`, Review Decision completed `04/22/2026 by GDO, as Corrections`, PW Engineering / Flood both completed `04/22/2026 by EMH, as Corrections` with comment `See comments in consolidated review letter.`, Building Review completed `04/15/2026 by 3WC, as Corrections` with comment referencing `PC3-122 Walnut St Plans.pdf (DocID 14783242)`, Detailed Planning completed `04/22/2026 by crt, as Corrections` with comment `minor comments remain`.
   - This is the 3rd review cycle. All departments returned Corrections simultaneously. The next expected change is a new Resubmittal Received event in Routing after the applicant submits revised plans (4th resubmittal), which would flip overall status back to `In Review`.
   - Better extraction method than brute-force expanding every hidden row: locate each stage label cell with JS (for example, a `td.ACA_ALeft` whose trimmed text equals `PW Engineering Review`), then read the adjacent detail row's `innerText`/`textContent` even if `style="display:none"`. Hidden detail rows remain readable in the DOM and reliably return full stage history for Routing, Application Intake, Building Site Check, active reviews, and Review Decision, including dates/comments like `04/22/2026`, `04/01/2026 by MJS`, `See comments in combined response letter.`, and the long Review Decision comment blocks.
   - After clicking/searching into the record page, a JS-dispatched click on the `Processing Status` anchor may expose `#tab-processing_status`; if the tab text is still short, inspect `#divProcessingTable` directly rather than waiting for the accessibility snapshot.
   - Use manual expansion only as fallback or spot-checking. Blindly clicking many `lnk_<guid>` expanders is noisy and can return unlabeled fragments detached from their parent stage, especially in the Routing section.
   - A reliable JS extraction snippet is to iterate top-level `#divProcessingTable > table > tbody > tr`, identify stage label rows by `td.ACA_ALeft` text, then read the immediately following hidden detail row's `textContent`; capture the first cell icon title/alt (`complete`, `active`, `Previously Active`) as the stage state. This returned accurate details on 2026-04-28 without expanding rows.
   - When detecting new resubmittals, do not treat future due dates in Routing (for example `08/09/2026` or `10/19/2026`) as activity. Only `Completed on <date> ... as Resubmittal Received` after the last corrections decision is meaningful.
7. When the user wants raw current statuses instead of a change summary, return a flat list in this format:
   OVERALL: <overall permit status>
   - <stage name>: <current status summary>
   Include visible current stages such as Application Intake, Routing, PW Engineering Review, Flood Review, Building Review, Detailed Planning Review, High Level Planning Review, MP Municipal Water Review, and Review Decision when present.
8. Pay special attention to active/in-review stages (for this permit these have included PW Engineering Review, Flood Review, Building Review, and Detailed Planning Review). Capture both status history and any comment text, and compare the newest entry dates/comments against the last known state if available.
9. Treat these as meaningful updates: overall record status change, a newly active/completed review, a new reviewer comment, a new resubmittal event, or a changed condition/notice. If none of those changed, prefer silence when the calling context supports suppression.
10. Summarize only material changes in a concise manner for the user.
11. Default to Simplified Chinese for all user-facing summaries unless the surrounding caller explicitly asks for another language.
12. If the surrounding caller says to suppress empty updates, follow the caller's exact sentinel string. Do not mix old sentinel values with new wrapper instructions.
13. Do not send Telegram yourself when the surrounding system says final output is auto-delivered. The old workflow assumed explicit Telegram sending, but cron delivery may already handle that.