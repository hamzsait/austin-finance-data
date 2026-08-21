# decodepolitics.org — Austin campaign finance

GitHub Pages serves this repo's root at https://decodepolitics.org (branch
`master`, no build step, `CNAME` at root). **Everything tracked at root is
publicly reachable**, and the profile pages fetch their data JSONs by absolute
path from the site root — so the layout below is load-bearing.

## Layout

### Served by the site (do not move or rename)
- `index.html`, `404.html`, `robots.txt`, `sitemap.xml`, `CNAME`
- `<slug>_data.json` + `<slug>_all_donations.json` (34 pairs) — fetched by
  `austin/<slug>/` profile pages via `/${slug}_data.json`
- `austin_landing.json`, `austin_races.json`, `austin_race_stats.json` —
  fetched by landing and race pages
- `austin/` — generated profile + district race pages
- `sanantonio/` — **generated output synced from the sibling
  `san-antonio-finance-data` repo** (`publish_site.py` there). Never hand-edit.
- `assets/` — logos, fonts, OG images, candidate photos
- `landing/`, `coming-soon/` — standalone landing pages
- `profile_*.html`, `austin.html`, `landing.html`, `velasquez.html`,
  `proisrael.html` (+ `proisrael_council.json`) — legacy pages/redirect stubs
  kept alive for old inbound links
- `endeavor_armbrust_*.pdf` — direct-share PDF reports
- `instagram_posts/` — exported carousel PNGs

### Pipeline (root `.py`, flat imports — keep together at root)
- Ingest: `fetch_data_incremental.py`, `travis_ingest.py`,
  `texas_finance_scraper.py`, `tec_full_ingest.py`
- Identity/employer resolution: `build_identities.py`,
  `build_employer_identities.py`, `build_joint_donors.py`,
  `build_joint_shadows.py`, `identity_migration.py`,
  `city_resolve_incremental.py`
- Enrichment/correctness: `fec_enrich.py`, `fec_dedup_pass.py`,
  `mark_restatements.py`, `fix_corrections_and_names.py`
- Site generation: `generate_profile_data.py` + `out_of_austin.py` →
  `build_candidate.py` / `build_race.py` (render from `profile_template.html`
  / `race_template.html`), `rebuild_all_ooa.py`, `refresh_landing_cards.py`,
  `update_landing_cycles.py`, `generate_sitemap.py`
- Publishing extras: `generate_pdfs.py`, `generate_instagram_posts.py`

These scripts resolve paths relative to their own location, so moving one into
a subdirectory silently redirects its output — leave them at root.

### Everything else
- `docs/` — active specs; `docs/plans/` — historical plan/design docs
- `archive/` — frozen one-off scripts, research batches, review CSVs, logs
  (see `archive/README.md`)
- `travis_county_filings/` — Travis County ingest toolkit (own README)
- `_scratch/` (gitignored) — throwaway logs, screenshots, superseded dumps
- `austin_finance.db` (gitignored, ~2.4 GB) — the pipeline SQLite DB;
  `tec_data/` (gitignored) — raw TEC bulk CSVs

## Typical flows
- Refresh a profile: `python build_candidate.py --slug <slug>` then
  `python refresh_landing_cards.py`
- Race page: `python build_race.py --race district<N>`
- Rebuild everything: `python rebuild_all_ooa.py`
- Sitemap after adding pages: `python generate_sitemap.py`
