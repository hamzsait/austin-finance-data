# Archive

Frozen one-off scripts and research artifacts kept for the audit trail. Nothing
here is imported by the live pipeline (verified at reorg time, 2026-08-20) and
nothing here is fetched by the site.

- `scripts/` — completed one-off migrations, backfills, and lookups
  (`_tmp_*`, `add_*`, `fix_*`, `classify_*`, per-candidate FEC batches, legacy
  page generators, etc.). Most compute paths from their own file location
  (`ROOT = dirname(__file__)`), and a few import root modules
  (e.g. `fec_enrich`), so **re-running one requires copying it back to the repo
  root first**. They are archived precisely because they should not be re-run.
- `research/` — LLM/manual research batch inputs and results
  (adl/qadri/siegel/fuentes/harpermadison/velasquez batches, firm totals,
  siegel findings).
- `d1_research/ … d9_research/, travis_research/` — per-district research
  batch corpora from the 2026 race-page expansions.
- `d1_delta_research/`, `d3_delta_research/` — November 2026 delta scrubs over
  the donors the October filings added (runbook step 11): D1 12 batches /
  230 donors / $46.49, D3 5 batches / 85 donors / $13.24, both on
  `claude-opus-5-5`. Scripts resolve the repo root from here or from a
  working copy at the repo root, so copy either dir as the next delta's template.
- `reviews/` — completed manual review CSVs (Travis identity review v1/v2).
  The FEC dedup review CSVs remain at the repo root while that review is open.
- `logs/` — committed run logs.
- `deprecated/` — superseded code (formerly `_deprecated/`).
