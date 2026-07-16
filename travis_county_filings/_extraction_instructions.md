# Vision extraction instructions — TEC Form C/OH pages

You are extracting campaign-contribution data from rendered page images of Texas
Ethics Commission Form C/OH campaign finance reports (Travis County filings).
You will be given a list of PNG page images (one per PDF page) and an output
JSON path. Read EVERY page image with the Read tool, classify it, extract data
from the relevant page types, and Write the output JSON. Pages may be typed
(electronic filings) or handwritten (older paper filings) — extract both.

## Page types

Classify every page as exactly one of:

- `COVER1` — "CANDIDATE / OFFICEHOLDER CAMPAIGN FINANCE REPORT, COVER SHEET PG 1".
  Has filer name, report type checkboxes (January 15 / July 15 / 30th day before
  election / 8th day before election / Runoff / Exceeded modified reporting limit
  / Final Report / 15th day after treasurer appointment), and PERIOD COVERED.
- `COVER2` — "SUPPORT & TOTALS, COVER SHEET PG 2". Has boxes 1–6:
  total unitemized political contributions, TOTAL POLITICAL CONTRIBUTIONS,
  total unitemized expenditures, total expenditures, contribution balance,
  outstanding loans. (Older form revisions may number these slightly
  differently — capture by label, not box number.)
- `COVER3` — any additional C/OH cover/subtotals page ("C/OH COVER SHEET PG 3",
  purpose-of-expenditure subtotals, etc.). No extraction needed.
- `A1` — "MONETARY POLITICAL CONTRIBUTIONS, SCHEDULE A1". Up to 5 contribution
  entries per page. Older paper revisions title it "POLITICAL CONTRIBUTIONS
  OTHER THAN PLEDGES OR LOANS, SCHEDULE A" — treat those as A1 too.
- `A2` — "NON-MONETARY (IN-KIND) POLITICAL CONTRIBUTIONS, SCHEDULE A2".
- `OTHER` — every other schedule or page (pledges B, loans E, expenditures F/F1,
  unpaid incurred obligations, credit-card expenditures, payments from political
  contributions to a business of the candidate, T, instructions, affidavit-only
  pages, correction affidavit CORR, treasurer appointment CTA/ACTA, blank pages).
- `UNREADABLE` — you truly cannot make out the page. Use sparingly.

## What to extract

### COVER1
```json
{"page": 1, "type": "COVER1", "filer_name": "Brown, Andy",
 "report_type": "January 15", "period_from": "07/01/2021",
 "period_through": "12/31/2021", "office_held": "Travis County Judge",
 "correction": false}
```
`report_type`: the checked box, verbatim label. `correction`: true if a
"Correction Affidavit" indication / CCOH marking is present.

### COVER2
```json
{"page": 2, "type": "COVER2", "total_unitemized_contributions": 0.00,
 "total_contributions": 316123.76, "total_unitemized_expenditures": 0.00,
 "total_expenditures": 114371.07, "contribution_balance": 571690.77,
 "outstanding_loans": 0.00}
```
Blank/empty boxes → null. Read amounts digit by digit; commas and cents matter.

### A1 (each entry on the page)
```json
{"page": 5, "type": "A1", "sch_pos": "2/126",
 "entries": [
   {"date": "12/31/2021", "name": "Alter, Alison",
    "city_state_zip": "Austin, TX 78756", "amount": 25.00,
    "occupation": "City Council Member", "employer": "City of Austin",
    "oos_pac": false}
 ]}
```
- `sch_pos`: the "Total pages Schedule A1: Sch: X/Y" header value as "X/Y" if
  present, else null (older handwritten forms say "1 of 1" — record as "1/1").
- `name` exactly as written, including "Last, First" order — do NOT reorder.
- Street addresses are usually redacted (black boxes); record only the visible
  "City, ST Zip" line in `city_state_zip`. If fully redacted → null.
- `oos_pac`: true only if the out-of-state PAC checkbox is checked.
- Empty entry slots on a partially-filled page are simply omitted.
- Handwritten "None" across the entry area → `entries: []`.

### A2 — same as A1 plus `"in_kind_description"` and use the amount box value.

### OTHER / COVER3
```json
{"page": 9, "type": "OTHER", "label": "SCHEDULE F1"}
```
`label`: the schedule letter/title you saw (short).

### UNREADABLE
```json
{"page": 9, "type": "UNREADABLE", "note": "what you can tell"}
```

## Accuracy rules (critical)

1. Transcribe EXACTLY — no normalization of names, no guessing missing digits.
   If a character is genuinely ambiguous, pick the best reading and add
   `"uncertain": true` to that entry with a short `"note"`.
2. Amounts: if an amount is unreadable, set it null and `"uncertain": true` —
   never invent a number. Watch for handwritten amounts without cents.
3. Do not skip pages. Output must contain one object per input page, in order.
4. Do not double-read: each entry appears on exactly one page.
5. Dates as MM/DD/YYYY strings exactly as written (2-digit years: keep as
   written, e.g. "12/31/16").

## Output

Write ONE JSON file at the output path you were given:
```json
{"chunk": "<given chunk id>", "pages": [ ...one object per page, in order... ]}
```
Then reply with only: chunk id, page-type counts, total A1/A2 entries, sum of
A1 amounts on your pages, and any pages marked uncertain/unreadable. Keep the
reply under 10 lines; the JSON file is the deliverable.
