# Travis County Commissioners — 2026 donations refresh

Exploration notes for branch `travis-2026-donations`. Written 2026-08-07 against
the state of the EasyVote portal that day.

## What's already in the repo (the July 2026 process, reusable)

The original ingest is fully documented and scripted; nothing needs to be
reinvented except the download step.

| Stage | Asset | State |
|---|---|---|
| 1. Find + download PDFs | *(was ad-hoc)* → now `travis_county_filings/_fetch_filings.py` | **written this branch** |
| 2. Render pages to PNG | `travis_county_filings/_render_pages.py` | reusable as-is |
| 3. Chunk into jobs | `travis_county_filings/_make_chunks.py` | reusable as-is |
| 4. Vision extraction | `_run_extraction.js` + `_extraction_instructions.md` | reusable; see caveats |
| 5. Reconcile / QA | `travis_county_filings/_validate.py` | reusable as-is |
| 6. Assemble CSV | `travis_county_filings/_assemble_csv.py` | reusable as-is |
| 7. Load into SQLite | `travis_ingest.py` (has `--append-only <slug>`) | reusable as-is |
| 8. Identity resolution | folded into `travis_ingest.py` (incremental) | reusable as-is |
| 9. Build profile JSON + HTML | `build_candidate.py` → `generate_profile_data.py` | needs new roster entries |
| 10. Landing cards | `update_landing_cycles.py`, `austin_landing.json` | needs new cards |
| 11. Race pages | `build_race.py`, `austin_races.json`, `race_template.html` | **no county races exist yet** |

`travis_county_filings/extracted/EXTRACTION_REPORT.md` documents the July run
(5,894 rows, $3.4M, 63/68 reports reconciling to the penny) and lists the five
known filer-side discrepancies — read it before re-reconciling.

### The one gap: there was no downloader

The README documented the EasyVote API flow but no script implemented it. I
wrote `_fetch_filings.py` on this branch and verified all three API steps still
work anonymously. It merges into `manifest.json` and skips anything already
downloaded, so it doubles as the "any new filings?" check:

```
python travis_county_filings/_fetch_filings.py --list
```

## Current data state vs. the portal

The DB stops mid-2026-cycle for everyone:

| Official | Rows in DB | Latest contribution | Latest filing pulled |
|---|---:|---|---|
| Brown, Andy (Judge) | 2,750 | 2025-12-31 | 2026-01-15 |
| Travillion (Pct 1) | 957 | 2025-11-24 | 2026-01-25 |
| Shea (Pct 2) | 1,313 | 2026-02-23 | 2026-02-26 |
| Howard (Pct 3) | 692 | 2025-12-31 | 2026-01-15 |
| Gómez (Pct 4) | 181 | 2025-09-02 | 2026-01-13 |
| Morales (Pct 4) | 1,146 | 2026-05-15 | 2026-05-18 |

**Three new incumbent filings have posted since the July 15 pull** — the July
2026 semiannuals covering Jan 1 – Jun 30, 2026:

- Brown, Andy — 2026-07-14 COH (112 pages)
- Howard, Ann — 2026-07-17 COH (46 pages)
- Travillion, Jeff — 2026-07-22 COH (92 pages)

Shea, Gómez and Morales have filed nothing new since the last pull.

## Scope question: "remaining commissioners"

Two readings, both real work. They can be done independently.

**(A) The three new incumbent July 2026 reports** — 250 pages. Closes the
2026-cycle gap for people already on the site.

**(B) The challengers we have never covered.** The portal has six active
non-incumbent commissioner candidates with 2025–26 filings and zero presence in
our DB. Pct 2 and Pct 4 are contested races where we currently show only one
side:

| Filer | Race | Docs | Latest |
|---|---|---:|---|
| Armstrong, Reese | Pct 2 | 7 | 2026-02-23 |
| Marzullo, Amanda | Pct 2 | 6 | 2026-02-24 |
| Astray-Caneda, Evelio | Pct 2 | 3 | 2026-03-21 |
| Woody, Susanna | Pct 4 | 17 | 2026-02-24 |
| Fernandez, Gavino | Pct 4 | 3 | 2026-02-23 |
| Zapata, Ofelia | Pct 4 | 3 | 2026-04-27 |

All 42 documents for A + B are already downloaded to this worktree (~150 MB,
gitignored).

## The extraction picture has changed — most of this is now free

The July run treated every page as an image because the older scanned filings
required it. That is no longer true across the board. Of the 42 downloaded PDFs:

- **13 files / 290 pages have a real text layer** (electronic TEC filings,
  ~2,300 chars/page) — parseable deterministically, no model calls.
- **29 files / 651 pages are pure scans** (0 chars/page) — still need vision.

Notably **Brown's 112-page July 2026 report is text-layer**, while Howard's and
Travillion's are scans.

A prototype text parser (`proto_parse.py`, scratchpad) already pulls
date / name / amount / city-state-zip / occupation / employer straight out of
the text layer. On Brown's July 2026 report it extracted **79 entries totalling
$12,413.00, exactly matching the cover sheet's sworn total** on the first run.

The prototype is not finished — the occupation/employer field split is wrong on
some entries, and multi-schedule reports (Marzullo's 51 A1 pages) need the real
reconciliation logic from `_validate.py` rather than the naive cover-total regex
it uses now. But the approach is proven and worth finishing: it is exact,
instant, and free where it applies.

Recommended split:
- text-layer PDFs → finish the deterministic parser, emit the same per-page JSON
  shape `_assemble_csv.py` already consumes
- scanned PDFs → existing vision pipeline unchanged (651 pages ≈ 33 chunks)
- both → same `_validate.py` reconciliation gate, so quality bar is unchanged

## Getting it onto the website

Steps 1–8 land rows in `austin_finance.db`. From there:

1. `travis_ingest.py --append-only <slug>` — re-ingests just that official.
   **Important:** a bare re-run deletes and re-mints all `tcv-` identities and
   would destroy FEC enrichment. Always use `--append-only`.
2. Add each new person to `CANDIDATE_CYCLES` in `generate_profile_data.py`
   (Travis rule: March primary is the real race, 4-year terms) and to `ROSTER`
   in `build_candidate.py`.
3. `python build_candidate.py --slug <slug>` — writes `<slug>_data.json`,
   `<slug>_all_donations.json`, and `profile_<slug>.html`.
4. `python update_landing_cycles.py` — stamps on-ballot status and cycle totals
   onto `austin_landing.json` cards. New challengers need a card added with
   `"section": "county"`.
5. `python rebuild_all_ooa.py`, then `generate_sitemap.py`.

**Open design decision:** `austin_races.json` currently contains only the five
City Council districts. Pct 2 and Pct 4 are genuinely contested and would be
natural race pages (`/austin/pct2/`, `/austin/pct4/`), but that means extending
race metadata to county races — `race_template.html` and `build_race.py` assume
council seats. Alternative is to ship the challengers as standalone profiles
plus landing cards and defer race pages.

## Environment note

PyMuPDF was missing from `python3.13.exe` and had to be reinstalled
(`pip install PyMuPDF`) — `_render_pages.py` imports it as `fitz`, which now
emits a deprecation warning but still works. `_run_extraction.js` also has a
hardcoded `PAGES_ROOT` pointing at a stale July scratchpad path; update it
before the next vision run.
