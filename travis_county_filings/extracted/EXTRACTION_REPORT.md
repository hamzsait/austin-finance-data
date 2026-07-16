# Step 1 — PDF → CSV extraction: final report

Extracted 2026-07-15 from the 68 Form C/OH campaign finance reports (3,694
pages) in `travis_county_filings/`, using page-by-page vision extraction with
per-report reconciliation against each report's notarized cover-sheet totals.

## Results

| Official | Itemized contributions | Total | Reports |
|---|---:|---:|---:|
| Andy Brown (County Judge) | 2,750 | $1,429,392.32 | 11 |
| Jeff Travillion (Pct 1) | 957 | $619,514.00 | 13 |
| Brigid Shea (Pct 2) | 1,314 | $789,214.00 | 19 (1 superseded) |
| Ann Howard (Pct 3) | 692 | $399,089.15 | 9 |
| Margaret Gómez (Pct 4) | 181 | $160,264.12 | 17 |
| **Total** | **5,894** | **$3,397,473.59** | 67 included |

Coverage: Jan 2017 – Feb 2026 (whatever each official filed with the county).
Includes monetary (Schedule A1) and in-kind (A2) contributions with donor name,
date, amount, city/state/zip, occupation, employer, and source report + page.

## Validation

Every report was checked three ways:
1. **Page completeness** — every PDF page classified; Schedule A1 page counts
   verified against the form's own "Sch: X/Y" numbering.
2. **Money reconciliation** — itemized (A1+A2) + unitemized must equal the
   sworn cover-sheet total (±$1).
3. **Entry sanity** — non-null amounts, parseable dates, non-empty names;
   ambiguous readings flagged `uncertain` (48 rows, 0.8%).

**63 of 68 reports reconcile exactly (to the penny).** The remaining 5 carry
*documented filer-side errors* — the sworn filings are internally inconsistent
and our extraction was verified against the page images (evidence in
`reconcile/*.json`):

| Report | Delta | Cause (verified on page images) |
|---|---:|---|
| Brown Jan 2026 | +$5,000 | Husch Blackwell $5,000 listed twice in schedules; cover total is $5,000 lower |
| Gómez Jul 2017 | +$13,850.06 | Prior-period balance written into the unitemized box; real contributions $1,500 |
| Gómez 8-day 2022 | +$59.40 | Filer's own two cover pages disagree with each other |
| Gómez runoff 2022 | −$2,750 | One A1 page missing from the county's scanned record itself (form says 4 pages, PDF has 3) |
| Gómez Jul 2022 | +$300 | Filer's stated total is $300 below the sum of her own itemized entries |

Three extraction errors were found and fixed during reconciliation (two
handwritten-digit misreads, one cover-total misread) — all corroborated by the
reports' own subtotal pages before editing.

## Corrections / dedupe

- `pct2_brigid-shea__2022-01-31_COH` superseded by the identical-period
  2022-02-01 refiling (excluded from CSVs).
- Shea's portal-labeled "CCOH" (2026-02-26) is actually a **Daily Pre-Election
  Report** (one $2,500 contribution); kept, exempt from cover-total checks.
- Note for future refreshes: daily pre-election contributions may reappear in
  the following semiannual report (Jul 2026, not yet filed) — dedupe by
  donor+date+amount when ingesting that report.

## Files

- `travis_contributions.csv` — all 5,894 rows, schema aligned to `campaign_finance`
- `<official>.csv` — per-official slices
- `validation.json` / `review_queue.json` — machine-readable QA results;
  the queue holds the 48 uncertain entries + filer-discrepancy notes
- `reconcile/*.json` — page-level evidence for every adjudicated mismatch
- `assembly_summary.json` — totals, superseded reports, dedupe notes
- `raw/` — per-chunk page-level extraction (source of truth for re-assembly)

## Pipeline (for re-runs when new reports drop)

1. `_render_pages.py <pages_dir>` — render PDFs to 200-DPI PNGs
2. `_make_chunks.py <pages_dir>` — build ~20-page extraction jobs
3. `_run_extraction.js` — headless Claude vision jobs (pool of 4,
   usage-limit-aware) following `_extraction_instructions.md`
4. `_validate.py` — reconcile every report; failures → reconciliation agents
5. `_assemble_csv.py` — dedupe + emit CSVs
