# Austin campaign-finance refresh runbook

How to bring decodepolitics.org's Austin data forward after the City Clerk posts a new round of campaign-finance reports (semiannual Jan 15 / Jul 15, 30-day and 8-day pre-election, runoff). The pipeline is additive: new rows are pulled from the city's Socrata feed into `austin_finance.db`, attached to existing donor/employer identities, enriched, and then every published page is regenerated from the DB. Each numbered step is idempotent on its own; run them in order and do not skip the verification queries, because later steps silently trust earlier ones.

## Prerequisites

- Run every command from the repo root of the **main checkout** (`austin-finance-data`), not a worktree. Scripts open `austin_finance.db` by relative path, and the DB is gitignored so it exists only in the main checkout.
- Interpreter: `"/c/Users/Hamza Sait/AppData/Local/Microsoft/WindowsApps/python3.13.exe"` (Git Bash path; `python3.13.exe` in PowerShell). It has `requests`, `rapidfuzz`, `jellyfish`, `python-dotenv`. WSL `python3` lacks `rapidfuzz`; do not use it for the resolvers.
- Back up before touching the DB. Naming convention: `austin_finance.backup-YYYY-MM-DD-<reason>.db` in the repo root (gitignored by `*.db`). Example: `austin_finance.backup-2026-11-08-pre-nov-refresh.db`.
- Scratch output goes in `_scratch/` (gitignored, `.gitignore:57`). Confirm with `git check-ignore -v _scratch/<file>`.
- Read-only DB inspection: `python3.13.exe -c` with `sqlite3.connect("file:austin_finance.db?mode=ro", uri=True)`. There is no `sqlite3` CLI on the Windows PATH.

## Step 0 — Sync code

```bash
git fetch origin
git log master..origin/master --stat      # look for *.py and austin_races.json changes
git pull --ff-only
git log --oneline -1                       # record the SHA
```

If the pull is not a fast-forward, stop and resolve on a branch. Never refresh data on a checkout that is behind origin; the rebuild scripts in steps 7–10 may have changed.

## Step 1 — Backup

```bash
cp austin_finance.db austin_finance.backup-$(date +%F)-<reason>.db
ls -la austin_finance*.db
```

The DB is ~2.4 GB; the copy takes under a minute. Keep the backup until the refreshed site is live and spot-checked, then delete stale backups (untracked).

## Step 2 — Fetch new rows from the city feed

### 2a. Confirm online that there is something to fetch

Clerk side (what *should* exist):

- Report schedule and every posted report, by filer: <https://www.austintexas.gov/clerk/elections/2026_campaign_finance_reporting> (adjust the year). Each filed report is linked; check that the candidates you care about appear under the report you expect.
- Statutory deadlines: <https://www.austintexas.gov/content/election-calendar>. For a Tuesday Nov 3 election: 30th-day report Mon Oct 5 (the 30th day is a Sunday and rolls forward), 8th-day report Mon Oct 26.

Feed side (what the API holds; Socrata dataset `3kfv-biw6`). API field names equal the DB's 17 feed columns (`API_COLUMNS` in `fetch_data_incremental.py`); the API additionally has `donor_address`, which the DB does not store. Use `curl -G --data-urlencode`; fetch tools that re-encode the URL mangle `%` and `like` clauses and return HTTP 400.

```bash
# high-water marks and row count
curl -s "https://data.austintexas.gov/resource/3kfv-biw6.json?\$select=max(date_reported),max(contribution_date),count(*)"

# filings since the DB high-water mark (substitute your own max date_reported)
curl -s -G https://data.austintexas.gov/resource/3kfv-biw6.json \
  --data-urlencode "\$where=date_reported>'2026-07-16'" \
  --data-urlencode "\$select=date_reported,count(*)" \
  --data-urlencode "\$group=date_reported" --data-urlencode "\$order=date_reported"

# per recipient, same window
curl -s -G https://data.austintexas.gov/resource/3kfv-biw6.json \
  --data-urlencode "\$where=date_reported>'2026-07-16'" \
  --data-urlencode "\$select=recipient,count(*),sum(contribution_amount),min(contribution_date),max(contribution_date)" \
  --data-urlencode "\$group=recipient" --data-urlencode "\$order=count desc" --data-urlencode "\$limit=100"

# re-keying pre-check: feed rows at or before the DB high-water mark, by year.
# Must equal the DB query below for every year the feed fully serves (2023+).
curl -s -G https://data.austintexas.gov/resource/3kfv-biw6.json \
  --data-urlencode "\$where=date_reported<='2026-07-16T23:59:59'" \
  --data-urlencode "\$select=contribution_year,count(*)" \
  --data-urlencode "\$group=contribution_year" --data-urlencode "\$order=contribution_year"
```

DB side, read-only, before fetching:

```sql
SELECT COUNT(*) FROM campaign_finance;
-- city high-water marks (exclude Travis PDF rows and joint shadows)
SELECT MAX(date_reported), MAX(contribution_date) FROM campaign_finance
 WHERE transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1;
-- compare with the API pre-check
SELECT contribution_year, COUNT(*) FROM campaign_finance
 WHERE transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1
   AND contribution_year >= '2022' AND date_reported <= '2026-07-16T23:59:59'
 GROUP BY 1 ORDER BY 1;
```

Travis County rows (`TRAVIS%` ids, `date_reported` without the `T00:00:00.000` suffix) are not in the feed; exclude them when reading city high-water marks. 2022 will not match the API because the publisher re-scoped the feed and now serves only part of 2022; 2023 onward must match exactly. Check the arithmetic: `(feed count) - (feed rows <= high-water mark)` must equal the sum of the grouped post-high-water counts. If it does not, the feed has changed rows you already hold: stop and investigate before fetching.

### 2b. Archive the previous run's id list

`fetch_incremental_new_txns.txt` in the repo root is overwritten by every run. If one is present from the previous refresh, move it to `archive/logs/fetch_incremental_new_txns_<YYYY-MM>.txt` (check `archive/logs/` first; never overwrite). The Aug 2026 list is `archive/logs/fetch_incremental_new_txns.txt` (unsuffixed, left as found). On 2026-11-08 the root file was already absent, so nothing was moved.

### 2c. Run the fetcher

```bash
"/c/Users/Hamza Sait/AppData/Local/Microsoft/WindowsApps/python3.13.exe" -u fetch_data_incremental.py \
  > _scratch/fetch_$(date +%F).log 2>&1; echo "EXIT=$?" >> _scratch/fetch_$(date +%F).log
```

No CLI arguments. It pages the whole feed (10k rows/page, ~14 pages), inserts only `transaction_id`s not already in the DB (17 feed columns; enrichment columns left NULL), then auto-runs `mark_restatements.mark()` and `build_joint_shadows.build()`. Observed runtime 2026-11-08: **31 seconds** end to end for a 132,660-row feed. Never run `fetch_data.py`; it drops the table.

What the output means:

- `=== BASELINE ===` / `=== DONE ===`: row counts before/after. The four guard rails (total delta, pre-2022 rows, Travis rows, distinct `donor_id`) must all read "unchanged" or the script rolls back and exits 1.
- `NEW ROWS BY YEAR`: keyed on `contribution_year`. For a routine refresh this is one line for the current year. **Re-keying signature:** several pre-current years listed here, and/or `NEW ROWS BY RECIPIENT` dominated by past-cycle recipients with contribution dates before the expected period. The city re-keyed every `transaction_id` once (Aug 2026), which makes the whole feed look new to a dedupe that keys only on `transaction_id`. If you see this, STOP: do not run steps 3+, restore the backup (`cp austin_finance.backup-... austin_finance.db`), and report. A few hundred current-year rows with contribution dates earlier than the new period is normal (late or first filings) and is not the signature.
- `NEW ROWS BY RECIPIENT (top 25)`: must equal the per-recipient API counts from 2a.
- `new contribution_date range` / `new date_reported range`: the latter's minimum should be the day after the old high-water mark.
- `[restate]` lines: `mark_restatements` zeroes `balanced_amount` on rows double-listed across reports (correction affidavits, overlapping reports). Expect a large "residual cross-report twins" count after pre-election reports, because the 8-day report re-lists part of the 30-day period.
- `[joint]` lines: shadow rows rebuilt; the count equals the prior run until step 3 splits new joint gifts.
- A `�` where the script prints an em dash is the Windows console code page, not a data problem.

`fetch_incremental_new_txns.txt` holds one new `transaction_id` per line. No downstream script reads it directly (`city_resolve_incremental.py` selects `donor_id IS NULL AND employer_id IS NULL AND date_reported > --since`), but it is the authoritative record of what this run inserted: use it for the verification join below and take `--since` for step 3 from its `date_reported` minimum. Leave it in the root until the next refresh archives it; it is untracked and must not be committed.

### 2d. Verify (read-only)

Load the id list into a temp table `newids(transaction_id)` and join:

```sql
-- every id landed
SELECT COUNT(*) FROM campaign_finance JOIN newids USING (transaction_id);
-- new high-water marks
SELECT MAX(date_reported), MAX(contribution_date) FROM campaign_finance
 WHERE transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1;
-- what came in
SELECT MIN(contribution_date), MAX(contribution_date), MIN(date_reported), MAX(date_reported)
  FROM campaign_finance JOIN newids USING (transaction_id);
SELECT contribution_year, COUNT(*) FROM campaign_finance JOIN newids USING (transaction_id) GROUP BY 1;
-- re-keying check: old-dated new rows on recipients with pre-current-year history
SELECT recipient, COUNT(*) FROM campaign_finance cf JOIN newids USING (transaction_id)
 WHERE cf.contribution_date < '<start of new period>'
   AND cf.recipient IN (SELECT recipient FROM campaign_finance
                         WHERE contribution_year < '<current year>' AND transaction_id NOT LIKE 'TRAVIS%')
 GROUP BY 1 ORDER BY 2 DESC;
-- per-candidate counts for the races being refreshed
SELECT recipient, COUNT(*), SUM(contribution_amount), MIN(contribution_date), MAX(contribution_date)
  FROM campaign_finance JOIN newids USING (transaction_id) WHERE recipient IN (...) GROUP BY 1;
-- all new rows still unresolved (should equal the id count until step 3)
SELECT COUNT(*) FROM campaign_finance JOIN newids USING (transaction_id) WHERE donor_id IS NULL;
```

### Worked example: November 2026 refresh (D1)

Run 2026-11-08 on master `4e6753d`; backup `austin_finance.backup-2026-11-08-pre-nov-refresh.db`.

Clerk: the 2026 reporting page lists 30th-day reports filed 9/30–10/7 (due Mon 2026-10-05) and 8th-day reports filed 10/26–11/2 (due Mon 2026-10-26), all linked. All six D1 candidates filed both: Goodwin, Ramos, Anderson, Brown, Riggins, Nahas (Nahas's July report was filed 7/14). Runoff is Sat 2026-12-12; no runoff finance deadlines posted yet.

API before fetch: 132,660 rows, `max(date_reported)` 2026-11-05, `max(contribution_date)` 2026-11-01, `rowsUpdatedAt` 2026-11-08 13:04 UTC. Feed rows with `date_reported` <= 2026-07-16 by year: 2022 2,504 / 2023 27,394 / 2024 46,417 / 2025 27,193 / 2026 15,444 (118,952). DB matched 2023–2026 exactly; 2022 was 53,580 in the DB (expected, feed re-scope). 132,660 − 118,952 = 13,708 = sum of the post-07-16 groups, so no re-keying.

| | Before | After |
|---|---|---|
| `campaign_finance` rows | 254,494 | 268,202 (+13,708) |
| city `max(date_reported)` | 2026-07-16 | 2026-11-05 |
| city `max(contribution_date)` | 2026-06-30 | 2026-11-01 |
| pre-2022 / Travis / shadow rows | 78,567 / 7,138 / 1,084 | unchanged |
| distinct `donor_id` | 44,809 | unchanged (new rows NULL) |

Fetcher summary: `NEW ROWS BY YEAR` = `2026 13,708` only. New `contribution_date` range 2026-01-03..2026-11-01; new `date_reported` range 2026-07-17..2026-11-05. 186 new rows carry pre-07-01 contribution dates: Bowen 89 (first filing 07-17 covering Apr–Jun), Shah 58, Austin Apartment Assoc. PAC 32, Austin United PAC 7, all `contribution_year` 2026, so not the re-keying signature. Restatements: 95 correction instances superseding 84 originals, 950 originals zeroed, 1,993 correction rows restored, 2,723 cross-report twins zeroed; 1,544 of the new rows ended with `balanced_amount = 0`. Shadows 1,084 → 1,084.

D1 new rows (contribution_date range; all latest `date_reported` 2026-10-26) and DB non-shadow row totals after:

| Candidate | New rows | New $ | Dates | Total rows |
|---|---|---|---|---|
| Goodwin, Amber K. | 158 | 31,664.00 | 07-01..10-21 | 741 |
| Ramos, Misael D. | 822 | 40,121.46 | 07-01..10-24 | 1,239 |
| Anderson, Alexandria M. | 72 | 9,780.00 | 07-01..10-21 | 270 |
| Brown, Steven A. | 88 | 15,724.00 | 07-02..10-20 | 200 |
| Riggins, Portia T. | 6 | 516.60 | 07-30..10-19 | 8 |
| Nahas, Michael D. | 0 | — | filed all reports; zero itemized rows in feed | 0 |

Other 2026 candidates with new rows: Heyman 261, Qadri 260, Xie 255, Bowen 240, Shah 180, Weinberg 137, Kam 127, Velasquez 100, Alter 68, Skinner 12, Brink 12, Romero 11, Thadani 3. PACs: Austin Fire Fighters PAC 7,431, Save Austin Now PAC 2,671 ($894,780), Austin Police Association PAC 498, Parks Pools Trails & Books PAC 119 ($122,052), Austin Apartment Assoc. PAC 74, Don't DOGE Our Austin 25 ($255,329), Austin United PAC 24, Restore Leadership ATX 10 ($104,700), Zo Must Go 10, RECA Advancing Democracy PAC 9 ($86,921), Better Austin PAC 7 ($140,600), Protect and Serve PAC 5 ($131,000), Austinites for Equity 4, HOME-PAC 2, Equity Action 1. Recipient names new to the DB: Austin Police Association PAC, Parks Pools Trails & Books PAC, Don't DOGE Our Austin, Restore Leadership ATX, Zo Must Go, Better Austin PAC, Protect and Serve PAC, Skinner, Brink.

Log: `_scratch/fetch_2026-11-08.log`. Id list: `fetch_incremental_new_txns.txt` (13,708 lines).

## Step 3 — Identity resolution

Attach every row step 2 inserted to a donor identity (`donor_id`) and an employer identity (`employer_id`), matching against the identities already in `donor_identities` / `employer_identities` and minting new ones only when nothing scores high enough. Same scoring and thresholds as `travis_ingest.py` (`build_identities.score_pair`, auto-accept ≥ 0.83, review 0.65–0.83; employers `build_employer_identities.score_employers`, auto ≥ 0.85). Existing identities are never dropped or re-minted. New ids carry the `tcv-` prefix and are inserted with `fec_matched = 0`, which is how step 5's targeted FEC run finds them.

### 3a. Scope and `--since`

```sql
-- what the script will touch (must equal the step-2 id count)
SELECT COUNT(*) FROM campaign_finance
 WHERE donor_id IS NULL AND employer_id IS NULL
   AND transaction_id NOT LIKE 'TRAVIS-%' AND date_reported > '<since>';
```

`--since` is the **previous** city high-water mark, i.e. the `max(date_reported)` step 2 recorded *before* fetching (2026-07-16 for the November run), not the new one. The comparison is a string `>` against `YYYY-MM-DDT00:00:00.000`, so it also admits rows filed on the since-date itself; those are already resolved from the previous refresh and the `employer_id IS NULL` clause drops them (the July rows filed 07-16 are 1,203 `migrated` individuals + 14 ENTITY rows with `employer_id` set, none in scope). The script default (`2026-03-09`) is stale; always pass `--since` explicitly. There is no row-list input: the script does not read `fetch_incremental_new_txns.txt`.

### 3b. Dry run, then real run

```bash
PY="/c/Users/Hamza Sait/AppData/Local/Microsoft/WindowsApps/python3.13.exe"
"$PY" -u city_resolve_incremental.py --dry-run --since <since> > _scratch/resolve_$(date +%F)_dryrun.log 2>&1
"$PY" -u city_resolve_incremental.py           --since <since> > _scratch/resolve_$(date +%F).log 2>&1
```

The dry run does all the work and rolls back at the end, so it costs the same as the real run (observed **924 s** for 13,708 rows; nearly all of it is `score_pair` against the ~45k existing identities). Do not start the real run until the dry run has exited; both open the DB for writing. Output is four lines:

- `rows to resolve: N` — must equal the step-2 id count. 0 means the wrong `--since` or the rows already have `employer_id`.
- `individuals: A matched, B new; joint: J; entities: E` — `A`/`B` count distinct *(last, first, zip5)* person groups, not rows: `A` groups scored ≥ 0.83 against an existing identity (stamped `match_confidence = city26-match-0.NN`), `B` groups got a fresh `tcv-` identity (`city26-new`). `B` should be a small fraction of `N`; a pre-election period is mostly repeat donors plus a handful of big PAC filings. `J` is joint-name rows ("Smith, John & Jane") split into `donor_id` / `donor_id_2`, `is_joint = 1`, `balanced_amount = half` (`city26-joint`). `E` is rows classified ENTITY (portal `donor_type` or `ENTITY_KEYWORDS` in the name); they get **no `donor_id`**, only an `employer_id`, and stay `donor_id IS NULL` by design.
- `employer stamps: X exact, Y fuzzy, Z new` — per row. Rows whose employer field is blank (and are not entities) get nothing and keep `employer_id IS NULL`.
- Real run only: `donors awaiting FEC (incl. backlog): N` — `donor_identities` with `fec_matched = 0 OR NULL`; this is step 5's input size.
- `DRY RUN � rolled back` — the `�` is the console code page, as in step 2.

Stop and report (do not run for real) if the dry run errors, reports 0 rows, or `B` is in the thousands for a routine window.

### 3c. Review-queue consequence

Every person group whose best candidate scored 0.65–0.83 is appended to `review_queue` with `resolved = 'city26-pending'` **and still gets a new identity**. The queue is a to-do list for a later manual/LLM merge pass; nothing downstream reads it, so the near-miss pairs are potential duplicate donors on the site until merged. Record the delta (`SELECT resolved, COUNT(*) FROM review_queue GROUP BY 1`) so the next scrub knows what this refresh added. Matched existing identities have `total_donated` / `record_count` / `campaigns` / `first_seen` / `last_seen` recomputed from their rows; new ones are seeded from the rows in scope.

### 3d. Verify (read-only)

```sql
-- remainder: should be exactly the ENTITY rows (+ any joint rows the name regex skipped)
SELECT donor_type, COUNT(*) FROM campaign_finance
 WHERE donor_id IS NULL AND date_reported > '<since>' AND transaction_id NOT LIKE 'TRAVIS%'
   AND is_joint_shadow IS NOT 1 GROUP BY 1;
-- confidence stamps on the new rows
SELECT match_confidence IS NULL, SUBSTR(match_confidence,1,12), COUNT(*) FROM campaign_finance
 WHERE date_reported > '<since>' AND transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1
 GROUP BY 1,2;
-- identities minted / employer coverage / review queue / FEC backlog
SELECT COUNT(*) FROM donor_identities;                                   -- delta = new identities
SELECT COUNT(*) FROM donor_identities WHERE donor_id LIKE 'tcv-%' AND fec_matched = 0;
SELECT COUNT(*) FROM campaign_finance WHERE employer_id IS NULL
   AND date_reported > '<since>' AND transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1;
SELECT resolved, COUNT(*) FROM review_queue GROUP BY 1;
SELECT COUNT(*) FROM donor_identities WHERE fec_matched = 0 OR fec_matched IS NULL;
-- per candidate: new rows resolved, distinct donors, and how many still need FEC
SELECT cf.recipient, COUNT(*) rows_with_id, COUNT(DISTINCT cf.donor_id) donors,
       COUNT(DISTINCT CASE WHEN di.fec_matched = 0 THEN cf.donor_id END) donors_no_fec
  FROM campaign_finance cf JOIN donor_identities di USING (donor_id)
 WHERE cf.date_reported > '<since>' AND cf.transaction_id NOT LIKE 'TRAVIS%'
   AND cf.is_joint_shadow IS NOT 1 AND cf.recipient IN (...) GROUP BY 1;
```

### Worked example: November 2026

Run 2026-11-08 (finished after midnight) with `--since 2026-07-16` (the pre-fetch high-water mark from step 2). Dry run 924 s, real run 912 s; identical summaries:

```
rows to resolve: 13708
individuals: 3046 matched, 1513 new; joint: 23; entities: 127
employer stamps: 9556 exact, 75 fuzzy, 618 new
donors awaiting FEC (incl. backlog): 4674
```

| | Before | After |
|---|---|---|
| new rows with `donor_id IS NULL` | 13,708 | 127 (126 ENTITY + 1, see below) |
| new rows by `match_confidence` | all NULL | 11,377 `city26-match-*` / 2,181 `city26-new` / 23 `city26-joint` / 127 NULL |
| `donor_identities` (of which `tcv-`) | 44,840 (13) | 46,372 (1,545) = +1,532 (1,513 individual + 19 minted while splitting joints) |
| distinct `donor_id` in `campaign_finance` | 44,809 | 46,341 (+1,532) |
| `employer_identities` (of which `tcv-`) | 16,292 (1,072) | 16,910 (1,690) = +618 |
| new rows with `employer_id IS NULL` | 13,708 | 3,459, all placeholder employers (`retired` 2,162, `Self*` 516, `Not Employed` 328, `NONE/None` 152, `N/A`/`NA` 48, blank 41, `homemaker` 19 …) that `normalize_employer()` empties — by design |
| `review_queue` `city26-pending` | 925 | 1,761 (+836; 1,744 score 0.65–0.75, 17 at 0.75–0.83) |
| `donor_identities.fec_matched = 0` | 3,142 | 4,674 (+1,532) |

Distinct donors on the 13,708 new rows: 4,569; of these 2,363 (2,379 counting `donor_id_2`) have `fec_matched = 0` — the 1,532 newly minted plus 831 pre-existing identities that were already in the backlog. Step 5's workload is therefore the full 4,674 `fec_matched = 0` set, or the 2,363 touched by this refresh if run targeted.

D1 (new rows = the step-2 counts; "new donors" = distinct `tcv-` ids minted this run):

| Candidate | New rows | With `donor_id` | Distinct donors | New donors | Donors `fec_matched=0` |
|---|---|---|---|---|---|
| Goodwin, Amber K. | 158 | 155 | 142 | 48 | 49 |
| Ramos, Misael D. | 822 | 821 | 636 | 493 | 494 |
| Anderson, Alexandria M. | 72 | 72 (1 joint) | 68 | 47 | 47 |
| Brown, Steven A. | 88 | 87 | 78 | 37 | 38 |
| Riggins, Portia T. | 6 | 6 | 5 | 4 | 4 |
| Nahas, Michael D. | 0 | — | — | — | — |

The 5 D1 rows without `donor_id` are AFSCME Vote PAC, Liberal Austin Democrats (Goodwin), ATU Cope (Brown), Signs4USA (Ramos) — entities, correct — and **"Trust, Ashley" (Goodwin)**, a person misclassified as ENTITY because `ENTITY_KEYWORDS` matches the surname "Trust"; she has an `employer_id` (a junk `tcv-` employer named after her) but no donor identity. Known limitation of the keyword classifier; fix by hand if she matters. Biggest sources of new identities elsewhere: Save Austin Now PAC 645 of 2,671 rows, Ramos 586 of 822, Austin Fire Fighters PAC 98 of 7,431 (the rest are repeat members).

Logs: `_scratch/resolve_2026-11-08_dryrun.log`, `_scratch/resolve_2026-11-08.log`.

## Step 4 — Joint shadows re-run

```bash
"$PY" -u build_joint_shadows.py > _scratch/shadows_$(date +%F).log 2>&1   # --dry-run to preview
```

Why again: the fetcher (step 2) already ran `build_joint_shadows.build()`, but at that point the new rows had no `donor_id_2` / `is_joint = 1`; those are set by step 3's joint split. Shadows (the spouse-#2 half of each joint gift, `is_joint_shadow = 1`, `transaction_id` suffixed `-J2`) are derived rows rebuilt from live joint parents, so this run is the one that credits spouse #2 for the newly fetched joint gifts. The pass is idempotent (DELETE all shadows, re-insert from parents) and takes seconds. Expected: `shadow rows: <before> existing -> <before + J> rebuilt`, where `J` is step 3's `joint:` count minus any parent with `balanced_amount = 0` (restated) or without a second id. `parents to re-split` should be 0 unless `mark_restatements` restored joint rows at full value.

```sql
SELECT COUNT(*) FROM campaign_finance WHERE is_joint_shadow = 1;
-- new joint parents vs their shadows
SELECT COUNT(*) FROM campaign_finance WHERE is_joint = 1 AND donor_id_2 IS NOT NULL
   AND is_joint_shadow IS NOT 1 AND date_reported > '<since>' AND transaction_id NOT LIKE 'TRAVIS%';
SELECT COUNT(*) FROM campaign_finance WHERE is_joint_shadow = 1 AND date_reported > '<since>';
```

### Worked example: November 2026

Run 2026-11-08 straight after step 3, 1 s:

```
[joint] parents to re-split to half value: 0 (-$0.00)
[joint] shadow rows: 1,084 existing -> 1,107 rebuilt (+$359,932.93 credited to spouse #2)
[joint] done
```

Shadows 1,084 → 1,107 (+23 = step 3's `joint: 23`; all 23 new parents have `donor_id_2` set and none is restated to 0). New shadows carry $17,385.13 to spouse #2; the $359,932.93 is the all-time total. `campaign_finance` 268,202 → 268,225. One of the 23 is on Anderson (D1). Log: `_scratch/shadows_2026-11-08.log`.

## Step 5 — FEC enrichment + dedup

<!-- TODO: filled by the agent that runs this step -->

## Step 6 — Edit `austin_races.json`

`austin_races.json` is the editorial layer for the five race pages. `race_template.html` and `austin/index.html` render **client-side at runtime** from `/austin_races.json` + `/austin_race_stats.json`; `build_race.py` only bakes `RACE_ID` and the OG/meta tags into `austin/<race_id>/index.html`. Consequences:

- A JSON-only change is live on the next deploy; no rebuild is needed for the page body.
- A `race_template.html` change needs `build_race.py --all --html-only` (no DB) to re-materialise every race page.
- The OG description is phase-aware and counts money, so after a data refresh run `build_race.py --all` (step 8), not `--html-only`.

The file is CRLF, `indent=1`, `ensure_ascii=False`, trailing newline. Edit by hand or round-trip through `json.load` → `json.dumps(d, indent=1, ensure_ascii=False).replace('\n', '\r\n') + '\r\n'`; either way `git diff austin_races.json` must show only the fields you meant to touch. The root `note` field documents the schema below.

### 6a. `data_through` — one value for all five races

`austin_race_stats.json` is a single shared file that `build_race.py` recomputes for **every** race on any run, so once the DB holds the new filings every race page shows the new money. `data_through` is purely editorial (`race_template.html` prints it in the facts strip, the methodology paragraph and the footer; nothing filters on it), so it must be set on **all five** district entries and the root `updated` bumped in the same pass; otherwise four pages show October money under "Data through June 30".

Pick the coverage end of the report round you just ingested, not the feed's `max(contribution_date)`:

```sql
-- council candidates (non-PAC): should all stop at the period end of the latest report
SELECT recipient, MAX(contribution_date), MAX(date_reported), COUNT(*) FROM campaign_finance
 WHERE transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1 AND date_reported > '<previous high-water>'
 GROUP BY 1 ORDER BY 2 DESC;
```

PACs file daily/special pre-election reports that run past the candidates' period end; ignore them for this field. Verify the period on one cover sheet (the `PERIOD COVERED … THROUGH` box on page 1 of the C/OH PDF). Semiannual rounds: Jan 15 covers through 12-31, Jul 15 through 06-30.

### 6b. Post-election fields (all additive; entries without them render as before)

Per race (`races[]`):

| field | values | notes |
|---|---|---|
| `phase` | `filing` \| `ballot_set` \| `runoff` \| `decided` | Absent → `ballot_set` if `ballot_final` is true, else `filing`. Set `ballot_final: true` alongside. |
| `result_note` | one sentence | Outcome banner, after a bold lead ("Headed to a runoff." / "Decided."). Say "unofficial until the canvass" until it is. |
| `result_source` | `{"outlet", "url", "date"}` | Banner links "Source: <outlet>". Omit `url` → no link. |
| `runoff_date` | ISO date | Already on every entry. "Runoff" fact + eyebrow in `runoff` phase; hidden in `decided`. |
| `runoff_early_voting` | `"YYYY-MM-DD to YYYY-MM-DD"` | Optional; "Early voting" fact in `runoff` phase only. |

Per candidate (`candidates[]`):

| field | values | notes |
|---|---|---|
| `result` | `won` \| `runoff` \| `eliminated` | Absent = still running (no badge). Set on **every** candidate once the race is `runoff`/`decided`. |
| `vote_pct` | number, e.g. `47.3` | Optional, appended to the badge. **Omit unless a reported figure is on hand.** |
| `has_data` / `placeholder_note` | bool / one sentence | `has_data: false` + `slug: null` + `recipient: null` = placeholder card: no money, the note replaces the stats. `build_race.py` skips it (no warning); `og_meta_for` still counts it in the "N-candidate field". |

What `phase` drives:

| | filing | ballot_set | runoff | decided |
|---|---|---|---|---|
| Banner | amber "field below is not final" + `context_note` | hidden | navy outcome banner: `result_note` + source | same, lead "Decided." |
| Eyebrow | `… · General <date>` | same | `… · Runoff <runoff_date>` | `… · Decided <election_date>` |
| Facts strip | filing opens/closes, general, runoff if needed, data through | same | general, runoff, early voting (if set), data through | general, data through |
| Candidates heading | Who's Running | Who's Running | Who's in the Runoff | Results |
| Cards | — | — | badge per `result`; advancing first, eliminated muted, money kept | badge; winner first |
| Default sort | A–Z | A–Z | Total raised (outcome is the primary key) | Total raised |
| Hub tag / kind line (`austin/index.html`) | FILING OPEN | BALLOT SET | RUNOFF DEC 12 · "Open seat · runoff · A vs. B" | DECIDED · "Open seat · decided · <winner> wins" |
| OG description (`build_race.py`) | "N candidates are running…" | same | "A and B head to a Dec 12 runoff for … $X raised across the N-candidate field…" | "<Winner> won … outright on Nov 3 … $X raised across…" |

`context_note` only displays in `filing` phase; rewrite it anyway so the JSON is not stale.

### 6c. Marking a race as a RUNOFF (D1 pattern)

1. District entry: `"ballot_final": true`, `"phase": "runoff"`, `result_note`, `result_source`, optionally `runoff_early_voting` (D1's dates came from the Chronicle only; confirm against the Clerk/Travis County before Nov 30 or drop the field). Append one outcome sentence to `intro`; rewrite `context_note`; clear moot `omitted` entries.
2. Every candidate: `"result": "runoff"` for the two advancing, `"eliminated"` for the rest. `vote_pct` only where reported.
3. `out_of_austin.py` `HAD_RUNOFF`: add `(slug, 2026)` for each advancing candidate **as a reviewed decision** — it raises that candidate's charter ceiling from $50k to $83k ($50k general + $33k runoff allowance) and changes their out-of-Austin reading. D1 (`goodwin`, `ramos`) are in; D3 (`velasquez`, `shah`) and D5 (`alter`, `weinberg`) are deliberately NOT added until the user signs off. Takes effect only when step 7 regenerates those profiles.
4. Steps 7–8 rebuild; then check `austin/<race_id>/index.html` meta description reads "… head to a Dec 12 runoff …" and the `/austin/` hub card shows RUNOFF DEC 12 + "A vs. B".

### 6d. Marking a race as DECIDED (D8 Xie, D9 Qadri)

Same, but `"phase": "decided"`, winner `"result": "won"`, everyone else `"eliminated"`, no `runoff_early_voting`, no `HAD_RUNOFF` change. Eyebrow becomes "Decided November 3, 2026"; the runoff fact disappears. If the incumbent won, the hub reads "Incumbent re-elected · <name> wins"; D8 must first have `kind` flipped to `open` (Ellis is not on the ballot) so it reads "Open seat · decided · Selena Xie wins".

### 6e. Per-district recipe still owed (from the 2026-11-08 audit; verify rosters against the Clerk's 8/17 ballot list)

- **D3** — add Fernandez (Gavino), Romero (Eduardo "Lalito"), Skinner (Brock); `phase: runoff`; Velásquez `runoff` 47.3, Shah `runoff` 24.7, Romero `eliminated` 12.1, Skinner `eliminated` 9.6, Fernandez `eliminated` 6.3 (KUT D3). Intro/bio "seeking a second term" → runoff framing. Hub 2 → 5.
- **D5** — add Brink (Elizabeth M. / Liz); keep Abraham placeholder (on ballot); `phase: runoff`; Alter `runoff` 47.77, Weinberg `runoff` 26.18, Brink `eliminated` 16, Abraham `eliminated` 10.05 (KUT D5). Re-verify the $275,000 Weinberg loan figure in `intro` (July number).
- **D8** — move Ellis to `outgoing` (petition shortfall, not on ballot; keep `/austin/ellis/` href); delete Hudsky; `kind: open`; rewrite `intro`; `phase: decided`; Xie `won` 64.38, Bowen `eliminated` 35.62 (Statesman / Austin Current). Drop `afp-d8-hudsky` from `PHOTOS` in `race_template.html` if the asset goes. Ellis's landing/cycle config needs an `update_landing_cycles.py` override (step 9).
- **D9** — add Huang (Kai Yu); Heyman ballot name "Rich"; clear the stale Ardalan `omitted` reason; `phase: decided`; Qadri `won` 51.38, Heyman `eliminated` 24.74, Kam `eliminated` 17.5, Huang `eliminated` 4.48, Thadani `eliminated` 1.9 (KUT D9). Intro + Qadri bio → won.

New candidates need slugs registered (step 7) and a profile build before their card shows money. After all five: bump root `updated`, run step 8, and fix the hard-coded "45 candidates decoded" / og alt on `index.html` (:250, :17) if the roster count moved (19 → 22 with corrected rosters).

Post-canvass: drop "unofficial until the canvass" from each `result_note`, add official `vote_pct`. After Dec 12: D1/D3/D5 → `phase: decided`, winner `won`, runner-up `eliminated`, `result_note` re-sourced; `HAD_RUNOFF` pairs stay (the allowance applies to the whole cycle). The profile OOA cap copy ("race advanced to a December runoff") is phase-neutral.

### Worked example: November 2026 (D1)

Edited 2026-11-09 in two passes. Editorial pass (template agent): D1 `ballot_final: true`, `phase: runoff`, `result_note` + KUT `result_source` (2026-11-03), `runoff_early_voting: "2026-11-30 to 2026-12-08"`, intro sentence appended, `context_note` rewritten, Kyra Rogers `omitted` entry removed, `result` set on all six candidates (Goodwin/Ramos `runoff`, four `eliminated`), `HAD_RUNOFF` += `("goodwin", 2026), ("ramos", 2026)`. Data pass (this step): root `updated` 2026-07-20 → 2026-11-09; `data_through` 2026-06-30 → **2026-10-24** on all five entries; Nahas `placeholder_note` → "Filed every required campaign finance report but has reported no itemized contributions." (he filed Jul 15, 30-day and 8-day reports; zero itemized rows in the feed, no `recipient` row in the DB). Nothing else on D3/D5/D8/D9 was touched (their copy is stale and gets its own pass).

Why 2026-10-24: the 8th-day-before-election report (filed 10-26) covers 09/25–10/24/2026 (Goodwin's and Ramos's cover sheets both say so), and every council candidate's `MAX(contribution_date)` in the new rows is ≤ 2026-10-24 (Xie, Weinberg, Velásquez, Shah, Ramos, Qadri, Heyman at 10-24; Goodwin 10-21; Brown 10-20; Riggins 10-19). The feed's `max(contribution_date)` of 2026-11-01 is PAC-only (Save Austin Now PAC daily reports to 11-01, Austin United PAC 10-31, Don't DOGE Our Austin 10-28, Restore Leadership ATX 10-27). `austin_race_stats.json` has no `last_gift` later than 10-24.

## Step 7 — Rebuild profiles

`build_candidate.py` runs `generate_profile_data.generate()` against the DB and writes three files per slug: `<slug>_data.json`, `<slug>_all_donations.json`, `austin/<slug>/index.html` (from `profile_template.html`, with the OG tags baked). Run it once per candidate whose rows changed.

**Order:** for 2026 race candidates (`CANDIDATE_SLUGS`), `build_candidate.og_meta_for` bakes the profile's OG description ("Raised $X from N donors this cycle…") from the shared `austin_race_stats.json`. Run step 8's `build_race.py --all` **before** this step so the stats file is fresh, or the profile OG tags carry the previous round's totals (fix after the fact with `build_candidate.py --html-only --slug <slug>`, which re-renders HTML without re-exporting JSON).

```bash
PY="/c/Users/Hamza Sait/AppData/Local/Microsoft/WindowsApps/python3.13.exe"
LOG=_scratch/build_$(date +%F).log
"$PY" -u build_race.py --all >> "$LOG" 2>&1          # step 8 first; see above
"$PY" -u build_candidate.py --recipient "Goodwin, Amber K."       --slug goodwin     >> "$LOG" 2>&1
"$PY" -u build_candidate.py --recipient "Ramos, Misael D."        --slug ramos       >> "$LOG" 2>&1
"$PY" -u build_candidate.py --recipient "Anderson, Alexandria M." --slug anderson    >> "$LOG" 2>&1
"$PY" -u build_candidate.py --recipient "Brown, Steven A."        --slug stevenbrown >> "$LOG" 2>&1
"$PY" -u build_candidate.py --recipient "Riggins, Portia T."      --slug riggins     >> "$LOG" 2>&1
```

Rules:

- `--recipient` is the **exact** `campaign_finance.recipient` string (copy it from `austin_races.json` → `candidates[].recipient`) and requires `--slug`. The lookup is a `LIKE` match, so a bare surname is dangerous: `Brown` also matches Travis County Judge Andy Brown (which is why Steven Brown's slug is `stevenbrown`). Incumbents/officeholders use `--slug <slug>` alone (from `ROSTER` in `build_candidate.py`) or `--all-remaining`.
- A new slug must be registered in four places before its first build, else the profile renders as an officeholder with the wrong window: `build_candidate.py` `CANDIDATE_SLUGS` (candidate framing instead of officeholder framing); `generate_profile_data.py` `CANDIDATE_CYCLES` (the cycle windows; first-time filers get `{'label': 'This Cycle', 'election_year': 2026, 'start_year': None, 'end_year': None}`; a prior run gets its own entry, e.g. Ramos `2022 Run` ending 2022 + `This Cycle` from 2023), `OFFICE_OVERRIDE` (`'Austin City Council · District N Candidate'` hero badge) and, if their filings start after 2018, `CANDIDATE_MIN_YEAR`. `build_race.py` imports `CANDIDATE_CYCLES` for the race-stat window too.
- `out_of_austin.py` `HAD_RUNOFF` is read by `generate_profile_data` via `out_of_austin.build_payload`; a pair added in step 6 only reaches the site when the profile is rebuilt here. Check `<slug>_data.json` → `out_of_austin.cycles[].{had_runoff, ceiling, pct_of_ceiling}`.
- If a loop feeds the recipient strings from a file, split on tabs only (`while IFS=$'\t' read -r rec slug`): the default `read` splits on the space inside "Goodwin, Amber K." and the build dies with `OSError … 'Amber K.\tgoodwin_data.json'` before writing anything.
- Each run prints an `index.html card` block with the hero numbers; it is informational (the landing page is rebuilt in step 9), but it is the quickest before/after check. Scan the log for `Traceback`.

Runtime observed 2026-11-09: 4 s per candidate (Ramos 7 s, 1,103 rows); the whole D1 set in 23 s. Nobody else may hold the DB open while this runs.

### Worked example: November 2026 (D1)

Run 2026-11-09 after step 8's `build_race.py --all`; log `_scratch/build_d1_2026-11-09.log`. All five exited 0, no warnings. Nahas has no DB rows and no slug, so nothing to build. Hero (all filings, not just this cycle — Ramos includes his 2022 run) and the 2026-cycle OOA block:

| Slug | Hero raised | Donors | Empl.-affil. | OOA ceiling | OOA counted | % of ceiling (Jul → Nov) |
|---|---|---|---|---|---|---|
| goodwin | $123,010 | 593 | 87.3% | $83,000 (`had_runoff`) | $49,648 | 97.7% → **59.8%** |
| ramos | $77,983 | 875 | 60.1% | $83,000 (`had_runoff`) | $19,039 | 18.4% → 22.9% |
| anderson | $38,147 | 251 | 68.4% | $50,000 | $9,965 | 9.9% → 19.9% |
| stevenbrown | $38,087 | 167 | 62.7% | $50,000 | $4,486 | 6.3% → 9.0% |
| riggins | $1,317 | 7 | 79.7% | $50,000 | $0 | 0.0% |

Goodwin's change is the contested number: the same $49,648 counted (up $800 from $48,848) now reads against the $83k runoff ceiling instead of $50k. The profile card renders "Cap: $50,000 general + $33,000 runoff allowance (race advanced to a December runoff)" with the $50k general tick on the meter. Known data wart: "Trust, Ashley" (Goodwin donor) is classified ENTITY by the keyword matcher (step 3) and has no donor identity.

## Step 8 — Rebuild race pages

```bash
"$PY" -u build_race.py --all               # recompute austin_race_stats.json from the DB, then render all five pages
"$PY" -u build_race.py --all --html-only   # template-only change: reuse the stats file, re-render pages
"$PY" -u build_race.py --race district1    # one page, but still recomputes the SHARED stats for every race
```

What it does: `build_stats()` runs one query per candidate with a slug + recipient (`SUM(COALESCE(balanced_amount, contribution_amount))`, `COUNT(DISTINCT donor_id)`, `COUNT(*)`, first/last gift, top-4 industries) over `contribution_year >= cycle_start` and `COALESCE(balanced_amount, contribution_amount) > 0`, for **every race in `austin_races.json`**, and overwrites `austin_race_stats.json` (one shared file; there is no per-race recompute). Restated twins (`balanced_amount = 0`) are excluded by the `> 0` filter; joint-gift shadow rows are included (the spouse-#2 half), which is why a candidate's `contributions` can be one more than their non-shadow row count. Then `make_race_html()` copies `race_template.html` to `austin/<race_id>/index.html`, substituting `RACE_ID` and the OG title/description/alt from `og_meta_for()`. Everything else on the page is fetched at runtime from the two JSON files.

`--all` vs `--html-only`: the OG description bakes the field total ("$265,553 raised across the six-candidate field") and the phase wording, so after a data refresh use `--all`; `--html-only` is for template edits when the stats file is already current. Runtime: 4 s either way.

Output lines: one `  <name>  $raised  donors  avg  first..last  (from <year|start>)` per candidate, then `wrote … austin_race_stats.json (N candidates)` and `Rendered: …` × 5. A `  ! <name>: no rows from <cycle> forward — card renders as pending` line means the recipient string has no qualifying rows: either the slug/recipient pair is wrong in `austin_races.json` or the candidate has not filed; the card falls back to the placeholder rendering. Placeholders (`slug: null`) are skipped silently.

Verification checklist (every item was run on 2026-11-09):

1. Stats vs previous: `git show HEAD:austin_race_stats.json` and diff `raised` / `donors` / `last_gift` per slug; every delta should equal the step-2 per-candidate new-row sums (minus restated/joint halves). No `last_gift` may exceed `data_through`.
2. Profiles: `<slug>_data.json` → `hero.total_raised` and `out_of_austin.cycles[]` (`limit`, `runoff_limit`, `ceiling`, `pct_of_ceiling`) for every rebuilt slug.
3. Cover-sheet cross-check for the top candidates: Clerk reporting page → candidate's latest C/OH PDF (`services.austintexas.gov/edims/document.cfm?id=…`), cover sheet page 2 line 2 "TOTAL POLITICAL CONTRIBUTIONS" and line 1 unitemized. Compare with `SUM(contribution_amount)` of the DB rows with that `date_reported`. The PDF text layer uses a shifted font encoding; a stdlib decoder (inflate streams, add 29 to each byte) is enough — no pypdf/poppler on this machine. A gap is expected only from unitemized gifts (line 1), in-kind rows, and restated twins; report it, do not "fix" it.
4. Headless render: `python3.13.exe -m http.server 8765 --bind 127.0.0.1` from the repo root, open `http://127.0.0.1:8765/austin/<race_id>/` in chrome-devtools, **reload with `ignoreCache`** (the browser happily serves last session's `austin_race_stats.json`), then check: no console messages; eyebrow/banner/facts strip match `phase` and `data_through`; money bars show the new totals; badges per `result`; placeholder note text; footer "Data through". Full-page screenshot for the PR. Also open one rebuilt profile and check the OOA card (`.ooa-cycle`). Stop the server (`Get-NetTCPConnection -LocalPort 8765` → `Stop-Process`).
5. `git status --short` / `git diff --stat`: expect `austin_race_stats.json`, `austin_races.json`, `austin/district{1,3,5,8,9}/index.html`, and per rebuilt slug `<slug>_data.json`, `<slug>_all_donations.json`, `austin/<slug>/index.html`. Untracked files that must **not** be committed: `fetch_incremental_new_txns.txt`, `*.db`, `_scratch/` (ignored). Stray untracked files in the root (`watson-out-of-austin.html`, `watson_2022_out_of_austin.csv`, `travis_real_estate_totals.csv`, `assets/*-skyline.jpg`, `assets/texas.jpg`, `instagram_posts/TRAVIS_CAROUSEL_CORRECTIONS.md`) predate the refresh; leave them out of the commit unless the user says otherwise.

### Worked example: November 2026 (D1)

`build_race.py --all` run 2026-11-09 00:35, 4 s, 16 candidates written, no `!` lines (Ellis still computes from his pre-ballot rows, last gift 06-30 — expected until the D8 pass moves him to `outgoing`). D1 OG description now: "Goodwin and Ramos head to a Dec 12 runoff for Austin City Council District 1, an open seat. $265,553 raised across the six-candidate field, decoded donor by donor."

| Slug | Raised Jul → Nov | Δ (= step-2 new $) | Donors | Contribs | last_gift |
|---|---|---|---|---|---|
| goodwin | $91,346 → $123,010 | +31,664 | 477 → 593 | 583 → 741 | 06-30 → 10-21 |
| ramos | $24,871 → $64,992 | +40,121 | 230 → 809 | 281 → 1,103 | 06-30 → 10-24 |
| anderson | $28,367 → $38,147 | +9,780 | 191 → 251 | 200 → 273 | 06-30 → 10-21 |
| stevenbrown | $22,363 → $38,087 | +15,724 | 98 → 167 | 114 → 202 | 06-30 → 10-20 |
| riggins | $800 → $1,317 | +517 | 2 → 7 | 2 → 8 | 03-02 → 10-19 |

Double-count check: none of the D1 new rows was zeroed by `mark_restatements` (the 1,544 zeroed rows are Save Austin Now PAC 1,288, Bowen 137, Qadri 105, Weinberg 44, Zo Must Go 5). Ramos's 30-day report covers 07-01..09-24 and the 8-day 09-25..10-24 with no (donor, date, amount) repeated across them; his 54 `balanced_amount = 0` rows are the 2022 correction affidavit, outside the cycle. Cover sheets (8th-day, period 09/25–10/24/2026): Goodwin line 2 $23,951.00 = DB rows reported 10-26 $23,951.00 (86 rows), exact. Ramos line 2 $20,496.79 = DB $20,226.79 (382 rows) + line 1 unitemized $270.00, exact; Ramos also reports $10,000 outstanding loans, which are not contributions and not in our totals. (Full-cycle totals do not reconcile to any single cover sheet: ours sum three reports and are net of joint-gift halving and in-kind rows.)

Browser check (chrome-devtools, cache bypassed): eyebrow "OPEN SEAT · RUNOFF DECEMBER 12, 2026"; banner "Headed to a runoff. … Source: KUT"; facts General Nov 3 / Runoff Dec 12 / Early voting Nov 30 – Dec 8 / Data through October 24, 2026; heading "Who's in the Runoff"; bars $123,010 / $64,992 / $38,147 / $38,087 / $1,317; Goodwin and Ramos ADVANCES TO RUNOFF, four ELIMINATED; Nahas card shows the new placeholder note; footer "Data through October 24, 2026."; no console messages. `/austin/goodwin/` OOA card: "$49,648 counted of $83,000 allowed (60%) · Cap: $50,000 general + $33,000 runoff allowance (race advanced to a December runoff)". Screenshot: `C:\Users\HAMZAS~1\AppData\Local\Temp\claude\20bd6791b06d3fee\4644b339-8bd5-4849-807f-9efe1d98613d\scratchpad\d1_after_rebuild.jpeg` (session temp; copy it into the PR if wanted).

## Step 9 — Landing refresh

<!-- TODO: filled by the agent that runs this step -->

## Step 10 — Sitemap + verify

<!-- TODO: filled by the agent that runs this step -->

## Step 11 — Delta affiliation scrub

<!-- TODO: filled by the agent that runs this step -->
