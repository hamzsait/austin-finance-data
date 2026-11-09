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

Give every donor identity that step 3 left at `fec_matched = 0` a federal giving history: `fec_enrich.py` queries the FEC `schedule_a` endpoint by name (+ state TX, + zip when the result set is large), keeps the rows whose name/zip composite scores ≥ 75, classifies each receiving committee Dem/Rep/Other (`fec_committee_cache`), and writes `fec_partisan_lean` (= Dem $ / (Dem $ + Rep $)), `fec_total_dem/rep/other/donations`, `fec_matched = 1`, `fec_matched_at` to `donor_identities`, plus the confirmed receipts to `fec_contributions_raw`. It ends with `resolve_from_fec_employers()`, which fills `resolved_industry` from the FEC employer string for donors still unresolved (`resolved_confidence = 'fec-employer'`). Then `fec_dedup_pass.py` repairs receipts the fuzzy match attributed to more than one identity. Nothing on the site reads `fec_matched`; the profile partisan panel reads `fec_partisan_lean` / `fec_total_*` (and the TEC columns), so this step is what makes the new donors' lean dots appear.

### 5a. Sizing and the `--limit` rule

```sql
SELECT COUNT(*) FROM donor_identities WHERE fec_matched = 0 OR fec_matched IS NULL;   -- step 3 printed this as "donors awaiting FEC"
```

The script selects `fec_matched = 0 OR NULL` ordered by `total_donated DESC` and stops at `--limit` (default 2000). The old backlog (identities never enriched, 3,142 before this run) competes with the newly minted ones for those slots, and big new donors sort ahead of small old ones, so a `--limit` below the count above leaves an unpredictable mix behind. **Always set `--limit` ≥ the count** (5000 for the November run). There is no `--since`/targeted mode; the only selector is the flag. `--reset` zeroes every flag and re-processes all 46k identities — never use it in a refresh.

### 5b. Rate limit, wall-clock, and what `--dry-run` really does

- Keys: `.env` holds `FEC_API_KEY_1..3` (check with `grep -cE '^FEC_API_KEY_[1-9]=.+' .env`). The in-process limiter allows `800 × keys` calls per 10 min (2,400 with three keys); on a 429 the key goes into cooldown for `Retry-After + 5` s and the next key is used. 500/503 back off and retry; **504 and connection errors are not retried past the request layer**: the donor is logged `[ERROR] <name>: 504 Server Error …`, counted in `errors=`, and **left at `fec_matched = 0`**, so a second identical run picks exactly those up. Run a second pass; names that 504 again are the persistent residue described below, not a retry target.
- Calls per donor: 1 schedule_a page, +1 if the name has > 300 TX hits (zip narrowing), +1 per additional 100-row page, +1 per committee not yet in `fec_committee_cache` (7,899 cached before this run, so almost none). Heavy donors at the top of the ordering cost 5–10 s each; the long tail of one-hit/no-hit donors costs ~1 s. Budget by the observed figures in the worked example, not by the limiter.
- `--dry-run` skips the `donor_identities` / `fec_contributions_raw` writes but **makes every API call** (and still inserts into `fec_committee_cache`). A full dry run therefore costs the same hours as the real run. Use it time-boxed (`timeout 300 …`) to confirm the `Processing N donors` line and that results come back, then run for real.
- Output is block-buffered: only the `[i/N] Processing: …` line every 50 donors, `[rate limit]`/`[429 …]` and `[ERROR]` lines flush immediately. A log that has not grown for 30 min while the process is alive means a stuck HTTP call (60 s timeout × 8 retries worst case per call); report rather than restart blindly.
- **The `[ERROR]` lines print the full request URL including `api_key=`.** Keep the logs in `_scratch/` (gitignored) and redact before pasting anywhere: `sed -i -E 's/api_key=[A-Za-z0-9]+/api_key=REDACTED/g' _scratch/fec_*.log`.

```bash
PY="/c/Users/Hamza Sait/AppData/Local/Microsoft/WindowsApps/python3.13.exe"
timeout 300 "$PY" fec_enrich.py --dry-run --limit 5000 > _scratch/fec_$(date +%F)_dryrun.log 2>&1   # time-boxed sanity check
"$PY" fec_enrich.py --limit 5000 > _scratch/fec_$(date +%F).log 2>&1; echo "EXIT=$?" >> _scratch/fec_$(date +%F).log   # background it; hours
"$PY" fec_enrich.py --limit 500  > _scratch/fec_$(date +%F)_pass2.log 2>&1   # pass 2: only the errors= leftovers remain fec_matched=0; expect the same 504s to repeat
```

Nothing else may hold the DB for writing while it runs (it commits after every donor). Read-only inspection is fine (WAL).

**Run the real pass as a detached Windows process (recommended on this machine).** A background shell started from a Claude Code session is a child of the session: the harness kills background shells when the machine runs low on memory ("stopped because the system is running low on memory" — it happened at 237/4,674 on 2026-11-09, 13 minutes in, with nothing wrong in the script), and the Bash tool's foreground timeout caps at 10 minutes. `Start-Process` from PowerShell puts the interpreter outside the session's process tree, so neither applies. Redirect both streams and set the working directory explicitly, because the script opens `austin_finance.db` relative to CWD and loads `.env` relative to its own path:

```powershell
# PowerShell 5.1, from anywhere
$repo = "C:\Users\Hamza Sait\Electoral\decode-politics\austin-finance-data"
$py   = "C:\Users\Hamza Sait\AppData\Local\Microsoft\WindowsApps\python3.13.exe"
$d    = Get-Date -Format yyyy-MM-dd
Start-Process -FilePath $py -ArgumentList "fec_enrich.py --limit 5000" -WorkingDirectory $repo `
  -RedirectStandardOutput "$repo\_scratch\fec_${d}_resume.log" -RedirectStandardError "$repo\_scratch\fec_${d}_resume.err" `
  -WindowStyle Hidden -PassThru | Select-Object Id, StartTime
# progress: the log grows one "[i/N] Processing: …" line per 50 donors
Get-Content "$repo\_scratch\fec_${d}_resume.log" -Tail 3
# finished when the process is gone and the log ends with "DB summary:" … "Rep-leaning (<=0.4): N"
Get-Process python3.13 -ErrorAction SilentlyContinue
```

Resuming after any interruption (harness reap, reboot, Ctrl-C) is the same command: every donor is committed individually and only `fec_matched = 0` rows are selected, so it continues where it stopped and also retries the `[ERROR]` donors. Redact the key from the logs when the run is done (`.err` is normally empty; `requests` warnings would land there).

**504 residue.** A subset of names 504s on every attempt: the API cannot serve the first page of `schedule_a` for them within its gateway timeout because the TX result set is enormous — very common surname + first name pairs (`Smith, Michael`, `Davis, Lisa`, `Moore, Joseph`, `Richardson, Michael`) and names with a stray leading initial glued to the surname (`S Llorens, John`, `G Baratz, Adam`, `D Martin, James`; the lone-letter token matches nearly everything in FEC's name search). The zip narrowing never engages because it needs that first page. Treat them as a persistent residue, not a retry target: after the second pass reports the same `errors=` count, stop. They stay `fec_matched = 0` (no lean, no receipts) and the site renders them as donors without federal history, which is the correct conservative outcome. A future fix is script-side (narrow by zip up front when the surname is in a common-name list, or strip glued initials in `_parse_name`), not more retries.

### 5c. What a miss looks like

Every processed donor ends with `fec_matched = 1` and a timestamp in `fec_matched_at`, including the misses: no FEC rows for the name, or rows that fail the ≥ 75 composite, give `fec_total_donations = 0`, `fec_partisan_lean NULL`, totals 0 and no `fec_contributions_raw` rows. Hits with only Other-classified committees get `fec_total_donations > 0` but `fec_partisan_lean NULL` (the profile panel shows them as federal donors without a lean). Names that do not parse to a surname are stamped matched without a query. So `fec_matched = 0` after the run means exactly "errored (504 residue) or never reached", nothing else.

```sql
SELECT fec_matched, fec_total_donations > 0 AS hit, fec_partisan_lean IS NOT NULL AS lean, COUNT(*)
  FROM donor_identities WHERE fec_matched_at >= '<run date>' GROUP BY 1,2,3;
SELECT COUNT(*) FROM donor_identities WHERE fec_matched = 0 OR fec_matched IS NULL;   -- = the 504 residue (139 in Nov 2026)
```

### 5d. Dedup pass

`fec_dedup_pass.py` (stdlib only; `--db`, `--dry-run`) finds `fec_sub_id`s held by two or more `donor_id`s in `fec_contributions_raw` — the same federal receipt counted once per local fragment, which inflates every FEC-derived number by the fragment count — and resolves each shared-receipt component three ways: **MERGE** fragments that are near-certainly one person (compatible names plus same zip5 / employer-token overlap / FEC address trail, or a distinctive spacing/compound/reversed-name pattern; remaps `campaign_finance.donor_id/_2`, `fec_contributions_raw`, `texas_contributions_raw.austin_donor_id`, `joint_donations`, folds the identity rows, records `identity_merges`, deletes the losers); **STRIP** receipts between fragments that stay separate people (owner by FEC-row zip, then employer token, then trail, then a confirm-score margin ≥ 10; the other copies are deleted); **REVIEW** the undecidable rest, left in place and written to `fec_dedup_review.csv` (tracked in git; one row per donor per sub_id, so the line count moves with the review remainder, not just this run's new donors). It then recomputes `fec_total_*` / `fec_partisan_lean` from the deduped raw table for every `fec_matched = 1` donor. Idempotent; the dry run rewrites the tracked review CSV too (so `git diff --stat fec_dedup_review.csv` after a dry run already shows the delta, and `git checkout fec_dedup_review.csv` restores it if you decide not to apply). The real run takes minutes (the merge remaps `campaign_finance` and the recompute scans the whole raw table); the dry run seconds.

```bash
"$PY" fec_dedup_pass.py --dry-run > _scratch/fec_dedup_$(date +%F)_dryrun.log 2>&1
"$PY" fec_dedup_pass.py           > _scratch/fec_dedup_$(date +%F).log 2>&1
git diff --stat fec_dedup_review.csv
```

Read the dry run's `MERGE:` lines before applying: every merge deletes a `donor_id`, which changes `COUNT(DISTINCT donor_id)` in the race stats and profiles (that is the point — fragments of one person were two "donors"). Merged ids that appear in `review_queue` or `identity_merges` stay recorded there.

Verification:

```sql
SELECT COUNT(*) FROM (SELECT fec_sub_id FROM fec_contributions_raw WHERE fec_sub_id IS NOT NULL AND fec_sub_id != ''
                       GROUP BY fec_sub_id HAVING COUNT(DISTINCT donor_id) > 1);        -- remaining = review remainder only
SELECT COUNT(*) FROM identity_merges WHERE person_key = 'fec-dedup-shared-subid' AND merged_at >= '<run date>';
SELECT COUNT(*) FROM donor_identities;                                                   -- down by the merge count
SELECT COUNT(*) FROM campaign_finance WHERE donor_id IN (SELECT merged_donor_id FROM identity_merges);  -- must be 0
```

### 5e. Spectrum flags

`fec_dedup_pass.py` ends with "re-run tec_partisan_aggregate.py, ip_spectrum_flag.py, fossil_fuel_flag.py, gun_lobby_flag.py". Since the Aug 2026 reorg all four live in `archive/scripts/`; they are run **from the repo root in place** (no copies) after every enrichment + dedup pass, because the flags are derived columns that are only as fresh as the last time the scripts ran:

| Script | Reads | Writes | Why it must re-run |
|---|---|---|---|
| `tec_partisan_aggregate.py` | `texas_contributions_raw` (10 tracked TEC committees) | `donor_identities.tec_total_dem/rep/other/donations`, `tec_matched` | only if the dedup pass **merged** identities that had TEC rows (the merge COALESCEs, never sums, the `tec_*` columns and remaps `austin_donor_id`); FEC enrichment does not touch TEC data. Read by the profile partisan panel. |
| `gun_lobby_flag.py` | `fec_contributions_raw` (10 committees) | `fec_committee_cache.gun_category`; `donor_identities.gun_spectrum/gun_tier/gun_total/gun_committees` | new FEC receipts; DB-only, not rendered by `generate_profile_data.py` (the profile's gun buckets are research `civic_affiliations`) |
| `ip_spectrum_flag.py` | `fec_contributions_raw` (**19** committees — 12 hawkish / 4 liberal Zionist / 3 pro-Palestine, the number the profile explainer quotes) | `fec_committee_cache.ip_category`; `donor_identities.ip_spectrum/ip_tier/ip_total/ip_committees` | new FEC receipts to AIPAC / J Street / etc.; merged fragments keep the winner's old totals until recomputed. **Read by `generate_profile_data.py`** (IP spectrum panel) |
| `fossil_fuel_flag.py` | `fec_contributions_raw` (53 committees) | `fec_committee_cache.fossil_category`; `donor_identities.ff_spectrum/ff_tier/ff_total/ff_committees` | new FEC receipts; DB-only, not rendered |

All four are full-reset-then-recompute, pure SQL over tables already in the DB (no network), idempotent, print reports to stdout only, and have no `--dry-run`. They are independent of one another (TEC reads only `texas_contributions_raw`; the three flag scripts read only `fec_contributions_raw`), so the order below is convention, not a dependency. The `ice_*` columns on `donor_identities` have no writer script in this repo yet (issue #37).

**DB path.** `gun_lobby_flag.py` and `tec_partisan_aggregate.py` open the CWD-relative `"austin_finance.db"`, so they must be launched from the repo root. `ip_spectrum_flag.py` and `fossil_fuel_flag.py` used to resolve `dirname(__file__)/austin_finance.db` (= `archive/scripts/austin_finance.db`, which does not exist — sqlite would create an empty file there); since 2026-11-09 both resolve `Path(__file__).resolve().parents[2] / "austin_finance.db"` (the repo root, two levels up from `archive/scripts/`), so they too run in place. Check afterwards that `git status` shows no stray `archive/scripts/austin_finance.db`. All four open the DB with `journal_mode=WAL`, which the DB already uses; other readers (a sibling worktree running `build_*`) are not blocked.

```bash
PY="/c/Users/Hamza Sait/AppData/Local/Microsoft/WindowsApps/python3.13.exe"
D=$(date +%F)
"$PY" -I _scratch/spectrum_counts.py austin_finance.db > _scratch/spectrum_${D}_before.txt   # read-only baseline (see below)
"$PY" -u archive/scripts/tec_partisan_aggregate.py > _scratch/spectrum_${D}_tec_agg.log  2>&1
"$PY" -u archive/scripts/gun_lobby_flag.py         > _scratch/spectrum_${D}_gun_flag.log 2>&1
"$PY" -u archive/scripts/ip_spectrum_flag.py       > _scratch/spectrum_${D}_ip_flag.log  2>&1
"$PY" -u archive/scripts/fossil_fuel_flag.py       > _scratch/spectrum_${D}_ff_flag.log  2>&1
"$PY" -I _scratch/spectrum_counts.py austin_finance.db > _scratch/spectrum_${D}_after.txt
diff _scratch/spectrum_${D}_before.txt _scratch/spectrum_${D}_after.txt
```

Runtime observed 2026-11-09 (46,264 identities, 8,027 cached committees): tec 0.9 s, gun 0.4 s, ip 0.8 s, ff 2.7 s — about 5 s for all four. Then steps 7–9 again (the flags only reach the site through the rebuilt `*_data.json`): `build_race.py --all` → `rebuild_all_ooa.py` (~3.5 min) → both landing scripts → the 17-page `--html-only` re-render loop.

Baseline / verification (read-only; `_scratch/spectrum_counts.py` is a session helper that prints the queries below for the whole table and for one district's donor pool — recreate it or run the SQL by hand):

```sql
SELECT COUNT(ip_spectrum), COUNT(ff_spectrum), COUNT(gun_spectrum),
       COUNT(*) FILTER (WHERE tec_matched = 1), ROUND(SUM(ip_total)), ROUND(SUM(ff_total)), ROUND(SUM(gun_total)),
       ROUND(SUM(tec_total_dem)), ROUND(SUM(tec_total_rep)), ROUND(SUM(tec_total_other))
  FROM donor_identities;
SELECT ip_spectrum, COUNT(*) FROM donor_identities WHERE ip_spectrum IS NOT NULL GROUP BY 1;   -- same for ff_, gun_
SELECT COUNT(ip_category), COUNT(fossil_category), COUNT(gun_category) FROM fec_committee_cache;  -- 14 / 49 / 10 on 2026-11-09
-- restricted to one district's donors (donor_id and donor_id_2 of the roster recipients)
SELECT COUNT(ip_spectrum), COUNT(ff_spectrum), COUNT(gun_spectrum), SUM(COALESCE(tec_matched, 0))
  FROM donor_identities WHERE donor_id IN (SELECT donor_id FROM campaign_finance WHERE recipient IN (<roster>) AND donor_id IS NOT NULL
                                    UNION SELECT donor_id_2 FROM campaign_finance WHERE recipient IN (<roster>) AND donor_id_2 IS NOT NULL);
```

Sanity rules: every flagged count must move **up or stay** (a drop means the reset ran and the recompute died — check the log for a traceback and re-run; the scripts are idempotent); no column may go all-NULL; the ip log must list 19 committees in STEP 2 (`Flagged` + `not in cache` lines — the pro-Palestine three and two hawkish PACs have no Austin donors and print `not in cache`, which is correct, not an error); `tec_matched` counts and the D/R/Other sums are unchanged unless the dedup merged TEC-matched identities; `austin_race_stats.json` and the race pages are byte-identical after `build_race.py --all` (flags do not touch money). Per-donor flag **moves** between identities are expected after a dedup: when a new `tcv-` identity fuzzy-matched the same FEC receipts as an existing donor, the dedup gave the shared `sub_id`s to one of them and the flag follows the receipts — log the pair for identity-frag-scan rather than "fixing" it here.

#### Worked example: November 2026 (run 2026-11-09, PR `spectrum-flags-nov-2026`)

Logs `_scratch/spectrum_2026-11-09_{tec_agg,gun_flag,ip_flag,ff_flag}.log`, counts `_scratch/spectrum_2026-11-09_{before,after}.txt`. All four exited 0, no tracebacks, no stray DB file. `donor_identities` flagged, whole table → D1 pool (1,855 donors of Goodwin / Ramos / Anderson / S. Brown / Riggins):

| Column | Before (all) | After (all) | Before (D1) | After (D1) |
|---|---|---|---|---|
| `ip_spectrum` | 162 (97 hawkish / 65 liberal Zionist) | **169** (103 / 66) | 7 | **8** |
| `ff_spectrum` | 542 (361 fossil / 181 climate) | **579** (392 / 187) | 18 | **22** |
| `gun_spectrum` | 238 (128 rights / 110 control) | **245** (134 / 111) | 7 | 7 |
| `tec_matched = 1` | 3,608 | 3,608 | 92 | 92 |
| sums `ip_total` / `ff_total` / `gun_total` | $3,114,160 / $1,959,263 / $240,512 | $3,197,385 / $2,032,473 / $244,275 | | |

TEC D/R/Other sums identical ($2,096,840 / $7,244,506 / $2,222,356): the dedup merged no TEC-matched identities. Committees flagged in `fec_committee_cache`: 14 IP (of 19), 49 fossil/climate (of 53), 10 gun (of 10), unchanged. Per D1 recipient: Goodwin ip 2 → **3** (Claire Selinger, `tcv-` Aug-25 $50 donor, AIPAC PAC $500 → tier 1 hawkish), Ramos ff 5 → **9**, S. Brown ff 3 → 4, Anderson ff 5 → 4. The new D1 flags are all `tcv-` identities created in step 3 (Ascot, Howard, Jones, McMichael, Meek, Selinger). The one drop — Perry Lorenz `68305c3f92668401` (Anderson donor, 40+ recipients since 2016) lost `climate_action` $5,050 — is a move, not a loss: the October `tcv-c5d82611…` "Lorenz, Perry" (Xie / Parks PAC donor, employer "estate real") took 256 of his FEC receipts including the NextGen Climate $5,050 in the dedup; the pair belongs in identity-frag-scan.

Rebuild: `build_race.py --all` 4 s (stats file and 5 race pages byte-identical), `rebuild_all_ooa.py` 211 s (34/34), landing scripts 2 s (`austin_landing.json` unchanged — flags are not on the cards), re-render 6 s. Only the 34 `*_data.json` changed (every one gets a new `meta.generated_at`; no `_all_donations.json` or `index.html` moved). IP panels that changed: **goodwin** 2 → 3 flagged (new "Pro-Israel (AIPAC-aligned)" entry: 1 donor, $500 federal / $50 local, beside the 2 liberal Zionist $26,390 / $600), **alter** 11 → 12 (hawkish 7 → 8, $1,085,952 → $1,087,952), **israel** 20 → 21 (liberal Zionist 14 → 15). Ramos unchanged (1 liberal Zionist: Cyral Miller, $149 / $10). Browser check (chrome-devtools, `http.server 8767`): `/austin/goodwin/` and `/austin/ramos/` load with zero console messages and render those panel counts.

### 5f. Verify (read-only)

```sql
-- coverage, whole table and restricted to donors on the new rows
SELECT COUNT(*) FILTER (WHERE fec_matched = 1) processed,
       COUNT(*) FILTER (WHERE fec_total_donations > 0) fec_hit,
       COUNT(*) FILTER (WHERE fec_partisan_lean IS NOT NULL) has_lean,
       COUNT(*) FILTER (WHERE fec_matched = 0 OR fec_matched IS NULL) pending
  FROM donor_identities;
SELECT COUNT(*) FILTER (WHERE di.fec_matched = 1), COUNT(*) FILTER (WHERE di.fec_total_donations > 0),
       COUNT(*) FILTER (WHERE di.fec_partisan_lean IS NOT NULL), COUNT(*)
  FROM (SELECT DISTINCT donor_id FROM campaign_finance WHERE date_reported > '<since>'
         AND transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1 AND donor_id IS NOT NULL) n
  JOIN donor_identities di USING (donor_id);
-- per candidate, cycle window = CANDIDATE_CYCLES start year (Ramos 2023, first-time filers all rows), incl. donor_id_2
SELECT COUNT(*) donors, COUNT(*) FILTER (WHERE fec_total_donations > 0) fec_hit,
       COUNT(*) FILTER (WHERE fec_partisan_lean IS NOT NULL) lean, COUNT(*) FILTER (WHERE fec_matched = 0) pending
  FROM (SELECT donor_id FROM campaign_finance WHERE recipient = '<recipient>' AND contribution_year >= '<start>'
         AND transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1 AND donor_id IS NOT NULL
        UNION SELECT donor_id_2 FROM campaign_finance WHERE recipient = '<recipient>' AND contribution_year >= '<start>'
         AND transaction_id NOT LIKE 'TRAVIS%' AND is_joint_shadow IS NOT 1 AND donor_id_2 IS NOT NULL) d
  JOIN donor_identities di USING (donor_id);
```

### Worked example: November 2026

Run 2026-11-09 (times CST = UTC−6; `fec_matched_at` stamps are UTC). Three keys in `.env`. Baseline (`_scratch/fec_2026-11-09_baseline.txt`): `fec_matched = 0` **4,674** = 3,142 old backlog + 1,532 minted in step 3.

Enrichment took three runs and **≈ 5.4 h of API time** in total:

1. `fec_enrich.py --limit 5000` from a Claude Code background shell, 00:53:37–01:06:27: 237 donors (≈ 3.2 s each at the heavy top of the ordering), 4 × 504, then **killed by the harness under system memory pressure** (`_scratch/fec_2026-11-09.log`). DB left consistent.
2. Same command relaunched detached via `Start-Process` (procedure in 5b) at ≈ 01:30, finished 05:44 (**≈ 4 h 14 min** for 4,437 donors, ≈ 3.4 s/donor average — the API was slow and 504-ing intermittently): `matched=2115 no_history=1773 errors=162`, 6 × 429 key rotations, no limiter sleeps; employer pass 4,891 candidates → **339 resolved**. `_scratch/fec_2026-11-09_resume.log` (`.err` empty).
3. Pass 2 (`--limit 500`), finished 06:42 after ≈ 58 min for 162 donors: `matched=8 no_history=15 errors=139`, employer pass +2. Nearly all of that hour was the 139 repeat-504s at ≈ 25 s each. `_scratch/fec_2026-11-09_pass2.log`.

Time-boxed dry run beforehand (`_scratch/fec_2026-11-09_dryrun.log`, 00:47:53–00:52:53): `Processing 4674 donors (dry_run=True)`, 34 donors with results, 8 × 504, stopped by `timeout 300` on purpose (exit 124 noted in the log).

**504 residue: 139 donors** (`_scratch/fec_2026-11-09_after_enrich.txt`), 58 of them `tcv-` ids minted this refresh, 33 with a glued leading initial. Examples: `s llorens, john` ($1,500), `Murphy` (surname only), `G Baratz, Adam`, `Oertli, T.`, `Richardson, Michael`, `Porter, Michael`, `D Martin, James`, `Davis, Lisa`, `Moore, Joseph`, `JOSEPH JR, JOE L`, `Smith, Jo Lynn`. Left at `fec_matched = 0`; not a retry target. On D1: Ramos 24 (`Smith, Michael`, `Smith, Justin`, `Scott, Karen`, `Roberts, Carl`, `Foley, Mike`, `J Davis, Tom`, `S Butler, Julia`, `S., Mary` …), Anderson 3 (`Brown, Emily`, `Crawford, Michael`, `Davis, Lisa`), Brown 1 (`Moore, Joseph`), Goodwin and Riggins 0.

Dedup: dry run 06:47:47–06:47:59 (12 s), real run 06:48:30–06:53:34 (5 min); logs `_scratch/fec_dedup_2026-11-09_dryrun.log`, `_scratch/fec_dedup_2026-11-09.log`. Enrichment had raised the shared-sub_id count from 28,966 to **53,610** (the new identities fuzzy-matched receipts already held by existing ones). Plan: 1,100 components / 2,315 ids; **merge 104 people from 212 ids** (links: exact 87, compound 7, fec-span-thin-emp 6, nickname 4, fec-span 3, reversed 3, fec-span-thin 1 — mostly a `tcv-` identity from step 3 whose name is byte-identical to an existing one, e.g. `Archuleta, Danielle | Archuleta, Danielle`, plus `Newman, Jake | Newman, Jacob`, `C Garcia, Julio | Garcia Jr, Julio`, `Bell-Sittler, Wolf | sittler, wolf`); strip 1,010 components. Applied: remapped 173 `campaign_finance.donor_id` + 2 `donor_id_2` rows, 6,461 `fec_contributions_raw` rows (5,820 duplicate receipts absorbed), **108 donor_ids merged into 104 people**, **9,590 duplicate receipt rows deleted** (dry run said 9,763; the merge absorbed the difference first), **39,081 sub_ids → review**, aggregates recomputed for 46,125 donors. Integrity: 0 `campaign_finance` rows point at a merged id, 0 merged ids remain in `donor_identities`. `fec_dedup_review.csv` 60,289 → **81,853 lines**; `git diff --stat` = 81,781 insertions / 60,217 deletions (the file is regenerated in component order, so the diff is a near-total rewrite even though the review set only grew by ≈ 10k sub_ids). Spectrum flags (5e) were run in a follow-up PR the same day (`spectrum-flags-nov-2026`); see the 5e worked example.

| | Before | After enrichment | After dedup |
|---|---|---|---|
| `donor_identities` | 46,372 | 46,372 | **46,264** (−108 merged) |
| `fec_matched = 0` | 4,674 | **139** | 139 |
| `fec_matched = 1` | 41,698 | 46,233 | 46,125 |
| with FEC receipts (`fec_total_donations > 0`) | 26,580 | 28,810 | **28,633** (+2,053) |
| with `fec_partisan_lean` | 26,069 | 28,253 | **28,081** (+2,012) |
| Dem ≥ 0.6 / Rep ≤ 0.4 | 17,120 / 8,032 | 18,573 / 8,676 | 18,456 / 8,630 |
| `resolved_confidence = 'fec-employer'` | 2,896 | 3,219 | 3,179 |
| `fec_contributions_raw` rows | 2,301,733 | 2,476,847 | 2,461,437 |
| `fec_committee_cache` | 7,899 | 8,027 | 8,027 |
| `identity_merges` | 2,550 | 2,550 | 2,658 |
| shared sub_ids (2+ donors) | 28,966 | 53,610 | 39,081 |
| donors on the new rows: total / `fec_matched=0` / receipts / lean | 4,865 / 2,371 / 1,654 / 1,626 | 4,865 / 66 / 2,893 / 2,831 | 4,842 / 66 / 2,831 / 2,771 |

D1 (profile cycle windows: Ramos `contribution_year >= 2023`, the other four all filings; distinct donors incl. `donor_id_2`, shadows excluded). Donor counts fall where the dedup merged a `tcv-` duplicate into an existing identity (Goodwin 1, Ramos 4); receipt counts fall slightly after dedup because stripped duplicates belonged to the other fragment:

| Candidate | Donors before → after | `fec_matched=0` before → after | FEC receipts before → after enrich → after dedup | Partisan lean before → after enrich → after dedup |
|---|---|---|---|---|
| Goodwin, Amber K. | 593 → 592 | 50 → 0 | 359 → 402 → **391** (66%) | 355 → 396 → **385** (65%) |
| Ramos, Misael D. | 809 → 805 | 494 → 24 | 216 → 507 → **497** (62%) | 214 → 501 → **491** (61%) |
| Anderson, Alexandria M. | 251 → 251 | 49 → 3 | 129 → 152 → **150** (60%) | 128 → 151 → **149** (59%) |
| Brown, Steven A. | 167 → 167 | 40 → 1 | 78 → 101 → **100** (60%) | 77 → 100 → **99** (59%) |
| Riggins, Portia T. | 7 → 7 | 4 → 0 | 2 → 3 → **3** | 2 → 3 → **3** |

Because the merges changed `COUNT(DISTINCT donor_id)` for Goodwin and Ramos, steps 7–8 must be re-run after this step (the 2026-11-09 00:35 race stats and D1 profiles predated it; the closing pass in steps 9–10 rebuilt everything from the final DB). Count files: `_scratch/fec_2026-11-09_baseline.txt`, `_scratch/fec_2026-11-09_after_enrich.txt`, `_scratch/fec_2026-11-09_after_dedup.txt`.

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

`build_candidate.py` runs `generate_profile_data.generate()` against the DB and writes three files per slug: `<slug>_data.json`, `<slug>_all_donations.json`, `austin/<slug>/index.html` (from `profile_template.html`, with the OG tags baked). Run it once per candidate whose rows changed — which, after a citywide fetch plus identity/FEC changes, is every profile: use `rebuild_all_ooa.py` (step 9) for the full set and the per-slug commands below only for a new candidate's first build or a targeted re-run.

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

`austin_landing.json` is the data behind the officeholder cards on the `/austin/` hub (`austin/index.html` renders it client-side) **and** the source of the OG description on every officeholder profile (`build_candidate.og_meta_for` reads the card's `raised` / `donors` / `topGroups` for the 17 roster slugs; 2026 challengers in `CANDIDATE_SLUGS` read `austin_race_stats.json` instead). Two scripts, neither takes flags; run them in this order.

- `refresh_landing_cards.py [slug ...]` (no args = every card). For each card whose `<slug>_data.json` exists and that is not marked `soon`, it copies `hero.total_raised` → `raised` (`$3.2M` / `$361K` style), `hero.unique_donors` → `donors`, `hero.employer_affiliated_pct` → `empPct`, and the top four `interest_groups` excluding `Unknown` → `topGroups` (label, formatted amount, bar width). Nothing else on the card is touched; `soon` cards are never flipped. It reads the **built JSON**, not the DB, so it can only be as fresh as step 7.
- `update_landing_cycles.py`. Stamps `on_ballot` on every card from `CANDIDATE_CYCLES` (`generate_profile_data.py`): true when the slug's last cycle has `election_year == datetime.now().year` and its label is not `Final Term`. For on-ballot cards it queries the DB (`SUM(COALESCE(balanced_amount, contribution_amount))`, `COUNT(DISTINCT donor_id)` over `contribution_year >= start_year`, positive rows only) and writes `raised_cycle` / `donors_cycle`, with `show_cycle = bool(raised)`; off-ballot cards lose those two keys and get `show_cycle: false`. The hub shows `show_cycle` cards as "raised this cycle" and the rest as "raised overall", the same split the profile pages use. Because it keys on the **current calendar year**, running it in January after an election flips every card back to "overall" — intended for a post-election refresh, but remember it if the December-runoff filings are ingested after New Year.

**Rebuild everything first.** A DB refresh is citywide: the new rows, the identity merges, the FEC employer fills and the research scrub move every profile's totals, donor counts, FEC-lean share, OOA card and industry mix, not just the refreshed district's. `refresh_landing_cards.py` reads every `<slug>_data.json`, so a partial step 7 leaves cards that disagree with their own profile pages (the drift that produced 14 stale cards by 2026-08-17). For a data refresh, step 7 is therefore `rebuild_all_ooa.py`, not a per-district list:

```bash
PY="/c/Users/Hamza Sait/AppData/Local/Microsoft/WindowsApps/python3.13.exe"
"$PY" -u build_race.py --all              > _scratch/build_race_$(date +%F).log  2>&1   # step 8 first: fresh stats for the challenger OG tags
"$PY" -u rebuild_all_ooa.py               > _scratch/rebuild_all_$(date +%F).log 2>&1   # every *_data.json in the root → JSON + HTML
"$PY" -u refresh_landing_cards.py         > _scratch/landing_$(date +%F).log     2>&1
"$PY" -u update_landing_cycles.py        >> _scratch/landing_$(date +%F).log     2>&1
# officeholder OG tags were baked from the OLD landing file above; re-render the 17 roster pages (HTML only, 5 s)
for slug in $("$PY" -c "import json;print(' '.join(c['slug'] for c in json.load(open('austin_landing.json',encoding='utf-8'))['candidates']))" | tr -d '\r'); do
  rec=$("$PY" -c "import json;print(json.load(open('${slug}_data.json',encoding='utf-8'))['meta']['candidate_name'])" | tr -d '\r')
  "$PY" -u build_candidate.py --html-only --recipient "$rec" --slug "$slug" >> _scratch/rerender_landing_$(date +%F).log 2>&1
done
```

`rebuild_all_ooa.py` has no flags: it globs `*_data.json` in the repo root (34 files on 2026-11-09: the 12 race candidates in `CANDIDATE_SLUGS`, the 6 Travis County officeholders, and 16 current or former council members and the mayor), takes each recipient string from its own `meta.candidate_name`, and runs `generate_profile_data.generate()` plus `build_candidate.make_profile_html()` per slug, collecting failures instead of stopping (`Done. N/34 rebuilt. FAILED: [...]` on the last line). A profile with no `_data.json` yet (a new candidate) is not in the glob and must be built once with `build_candidate.py --recipient … --slug …` first (step 7 rules). Nobody else may hold the DB open while it runs.

Why the re-render loop: the dependency is circular — the landing file is built from the profile JSON, and officeholder profile HTML bakes its OG text from the landing file. `rebuild_all_ooa.py` therefore renders the officeholder pages against the previous landing snapshot (Alter's page read "raised $343K from 850 donors" while the refreshed card said $361K / 894). `--html-only` re-renders from the template without re-exporting JSON; `--recipient` is required by the CLI but unused on the HTML-only path, so the slug's own `meta.candidate_name` is the safe value (`--slug` alone works for the 12 `ROSTER` slugs; `fuentes`, `harpermadison`, `siegel`, `velasquez`, `qadri` need `--recipient`). The `tr -d '\r'` matters: Python's `print` emits CRLF when piped in Git Bash, and a trailing `\r` in `$slug` breaks the path.

**Ellis caveat.** `CANDIDATE_CYCLES['ellis']` still ends in a 2026 cycle, so `update_landing_cycles.py` stamps her `on_ballot: true`, `show_cycle: true`, "$113K this cycle (424 donors)", although she missed the ballot (petition shortfall) and is not running. Left as is in the November 2026 refresh because her card copy, `austin_races.json` D8 entry and race-page bio are all part of the pending D8 editorial pass (step 6e); fix there, either by closing her 2026 cycle in `CANDIDATE_CYCLES` or by adding an explicit not-on-ballot override set to `update_landing_cycles.py`. `harpermadison` (`on_ballot: true`, `show_cycle: false`, $0 this cycle) is the designed zero-cycle fallback and needs nothing.

Verify: `git diff austin_landing.json` must touch only `raised` / `donors` / `empPct` / `topGroups` / `on_ballot` / `show_cycle` / `raised_cycle` / `donors_cycle` (equal insertions and deletions, no whole-file CRLF churn — `refresh_landing_cards.py` writes `\n`, `update_landing_cycles.py` writes the platform default, which has not caused churn on this machine). Every `raised` / `donors` on a card must equal the hero of its `<slug>_data.json`; every `raised_cycle` must equal the slug's row in `austin_race_stats.json` where one exists (same query, same window). Then check the hub in the browser (step 10).

### Worked example: November 2026

Run 2026-11-09 after `build_race.py --all` (4 s) and `rebuild_all_ooa.py` (**196 s**, 34/34 rebuilt, no failures; log `_scratch/rebuild_all_2026-11-09.log`). Both landing scripts together took 2 s (`_scratch/landing_2026-11-09.log`); the 17-page re-render 5 s (`_scratch/rerender_landing_slugs_2026-11-09.log`). `git diff --stat austin_landing.json`: 62 insertions / 62 deletions. `update_landing_cycles.py` reported `8/17 on this November's ballot` (harpermadison, velasquez, alter, ellis, qadri, brown, shea, morales), identical to the previous stamp — no `on_ballot` flips.

| Card | What moved |
|---|---|
| velasquez | $265K → **$291K**, 845 → 913 donors, empPct 87.8 → 85.5, cycle $97K/335 → **$123K/418**, topGroups 4th Legal → Education |
| alter | $343K → **$361K**, 850 → 894, empPct 88.1 → 86.6, cycle $184K/599 → **$203K/644** |
| qadri | $444K → **$463K**, 1,867 → 1,941, empPct 92.9 → 91.6, cycle $259K/1,054 → **$278K/1,139** |
| watson, fuentes, ellis, duchen, shea, morales | `topGroups` amounts ± $1K (industry re-resolution); duchen 4th Technology → Legal |
| laine, siegel, brown, duchen, shea, morales | `empPct` ± 0.1–0.7 |
| harpermadison, travillion, howard, gomez | unchanged |

The three big moves are the October filings for D3/D5/D9 incumbents, which no earlier step had rebuilt (the first D1 pass rebuilt only the five D1 profiles) — exactly the inconsistency the "rebuild everything" rule prevents. Ellis stayed `on_ballot: true` (see caveat).

## Step 10 — Sitemap + verify

### 10a. Sitemap

```bash
"$PY" generate_sitemap.py          # → sitemap.xml written: N URLs (M pages skipped)
git diff --stat sitemap.xml        # expect no change unless a page was added or removed
```

No flags. It walks every `index.html` under the repo root (skipping `.git`, `archive/`, `docs/`, `_scratch/`, `_deprecated/`, templates), keeps the pages whose `<link rel="canonical">` points at their own URL and that are not `http-equiv="refresh"` stubs, drops the `EXCLUDE` set (`/coming-soon/`), and rewrites `sitemap.xml`. Regenerated profile and race pages keep their canonical, so a refresh normally produces **no diff**; a new candidate directory under `austin/` appears automatically once its page is built. If the diff shows a page disappearing, its canonical was lost in a template change — fix the template, not the sitemap. November 2026: 57 URLs, 1 skipped (`/coming-soon/`), `sitemap.xml` identical to HEAD.

### 10b. Verification checklist

Run every item; the worked example records what each produced on 2026-11-09.

1. **Race stats vs the pre-rebuild snapshot.** Copy `austin_race_stats.json` to `_scratch/race_stats_before_final.json` before step 8 and diff per slug afterwards. After steps 2–4 the deltas must equal the new-row sums (step 8 checklist); after step 5 alone, `raised` must be unchanged and `donors` may fall only by that candidate's merge count; `topGroups` move freely (FEC-employer fills and the research scrub re-label donors). Any `raised` change at this point is a sign something wrote to `campaign_finance` after step 4.
2. **Profile JSON before/after** for the refreshed district (keep copies of the previous `<slug>_data.json` in `_scratch/`): `hero.{total_raised, unique_donors, employer_affiliated_pct}`; `partisan_lean.{matched_donors, total_donors, dem_donors, rep_donors, weighted_lean}` (the FEC pass must raise `matched_donors / total_donors`); `out_of_austin.cycles[].{ceiling, counted_total, pct_of_ceiling}` (unchanged by step 5 — the OOA count is zip-based; `ceiling` reflects `HAD_RUNOFF`); `civic_affiliations.total_donors_with_affiliations` and the `Unknown` entry in `interest_groups` (both move when step 11 was applied). Grep the JSON for two or three organisations the research pass added to confirm they rendered.
3. **OG tags.** `grep -o 'og:description" content="[^"]*' austin/<slug>/index.html` for one challenger (numbers must match `austin_race_stats.json`) and one officeholder whose landing card changed (numbers must match the refreshed `austin_landing.json`). A stale officeholder value means the step 9 re-render loop did not run.
4. **Headless render.** `"$PY" -m http.server 8766 --bind 127.0.0.1` from the repo root in a background shell; chrome-devtools `new_page` on `http://127.0.0.1:8766/austin/<race_id>/`, `/austin/<slug>/` for the two or three most-changed profiles, and `/austin/` (hub). **Reload each with `ignoreCache: true` before reading anything**: the browser serves last session's `austin_race_stats.json` / `<slug>_data.json` / `austin_landing.json` from cache and every number on the page will look stale when the files on disk are right. Then `list_console_messages` (expect none) and `evaluate_script` on `document.body.innerText` for the values. Race page: eyebrow/banner/heading per `phase`, money bars = `raised` per slug (the race page shows **no donor counts**), badges per `result`, placeholder note, footer "Data through". Profile: hero numbers — a repeat candidate's profile (Ramos) opens on the **This Cycle** view, so the hero shows the cycle figures that match the race stats, not the lifetime `hero.total_raised`; `.ooa-cycle` card text (ceiling, %, cap wording); the Federal Partisan Lean panel's Dem/Rep counts. Hub: the `N races · M candidates` line, the per-race tag (`RUNOFF DEC 12` …) and kind line (`Open seat · runoff · A vs. B`), card totals. Save full-page screenshots for the PR, close the pages, and stop the server (`Get-NetTCPConnection -LocalPort 8766 -State Listen | % { Stop-Process -Id $_.OwningProcess -Force }`; killing it makes the background task report "failed", which is expected).
5. **Sitemap** (10a).
6. **Commit hygiene.** `git status --short`, grouped:
   - *Tracked, commit:* `austin_race_stats.json`, `austin_races.json`, `austin_landing.json`, `austin/district*/index.html`, every `<slug>_data.json` / `<slug>_all_donations.json` / `austin/<slug>/index.html` the rebuild touched, `fec_dedup_review.csv` (step 5d), `docs/REFRESH_RUNBOOK.md`.
   - *Untracked, commit:* the research corpus directory for this refresh (`d1_delta_research/` in Nov 2026) **after** deleting its scratch files — chunked/merged intermediates (`_tmp_*`, `_part_*`, `_d05_part*`, `_d08_part*`, `_d1delta_11_part*`, `_merge_*.py`) are driver debris, not corpus; keep the batch inputs, `*_results.json`, the three scripts, `_research_instructions_v3.md`, `_scripts/`, the usage/apply/run logs and `_d1_delta_overridden_labels.csv` (`__pycache__/` is ignored). Step 11 §6 moves it under `archive/` later.
   - *Never commit:* `*.db` (ignored), `fetch_incremental_new_txns.txt` (untracked by design, archived in step 2b of the next refresh), `_scratch/` (ignored), FEC logs containing `api_key=`. Stray root files that predate the refresh (`watson-out-of-austin.html`, `watson_2022_out_of_austin.csv`, `travis_real_estate_totals.csv`, `assets/*-skyline.jpg`, `assets/texas.jpg`, `instagram_posts/TRAVIS_CAROUSEL_CORRECTIONS.md`) stay out unless the user says otherwise.

### Worked example: November 2026 (closing pass, 2026-11-09)

Runtimes: `build_race.py --all` 4 s · `rebuild_all_ooa.py` 196 s (34/34) · landing scripts 2 s · 17-page re-render 5 s · `generate_sitemap.py` < 1 s. Git: 104 tracked files modified (34 `_data.json`, 33 `_all_donations.json` — Gómez's was byte-identical —, 33 `austin/<slug>/index.html` — Riggins's OG text did not change —, the two JSON files, the landing file, the review CSV, this runbook); the five race pages came out identical to HEAD because no field total changed since the first pass.

Race stats vs `_scratch/race_stats_before_final.json`: `raised` unchanged on all 16; `donors` down only by the step-5 merges — goodwin 593 → 592, ramos 809 → 805, velasquez 421 → 418, weinberg 185 → 184, qadri 1,140 → 1,139, heyman 366 → 364; `topGroups` changed on 15 of 16 (Goodwin Real Estate $14,370 → $18,745, Ramos Technology $7,122 → $9,579).

Final D1 table (`austin_race_stats.json`):

| Slug | Raised | Donors | Contribs | last_gift |
|---|---|---|---|---|
| goodwin | $123,010 | 592 | 741 | 2026-10-21 |
| ramos | $64,992 | 805 | 1,103 | 2026-10-24 |
| anderson | $38,147 | 251 | 273 | 2026-10-21 |
| stevenbrown | $38,087 | 167 | 202 | 2026-10-20 |
| riggins | $1,317 | 7 | 8 | 2026-10-19 |

Profile JSON, first D1 pass (00:35) → final:

| | Goodwin | Ramos | Anderson |
|---|---|---|---|
| hero donors / empl.-affil. | 593 → 592 / 87.3 → **89.1%** | 875 → 870 / 60.1 → **67.1%** | 251 / 68.4 → **72.9%** |
| `partisan_lean` matched / total (share) | 357/593 (60.2%) → **387/592 (65.4%)** | 266/875 (30.4%) → **543/870 (62.4%)** | 128/251 (51.0%) → **149/251 (59.4%)** |
| Dem / Rep / mixed donors | 309/38/10 → 332/43/12 | 236/24/6 → 467/62/14 | 117/10/1 → 133/14/2 |
| `weighted_lean` | 0.846 → 0.835 | 0.861 → 0.868 | 0.931 → 0.896 |
| OOA 2026: ceiling / counted / % | $83,000 / $49,648 / 59.8% (unchanged) | $83,000 / $19,039 / 22.9% (unchanged; 2022 cycle $1,935 → $1,955, 9 → 7 unknown zips) | $50,000 / $9,965 / 19.9% (unchanged) |
| donors with affiliations | 225 → 240 | 49 → 67 | 34 → 39 |
| `Unknown` industry $ | 9,387 → 7,102 | 22,609 → 16,756 | 8,531 → 6,681 |

Step-11 entries now in the JSON: Goodwin — "Texas AFL-CIO" 7 → 10 mentions, Tara Pohlmeyer 0 → 8, Casey Haney 2 → 7; Ramos — "Commission Shift" 1 → 8, John Tarleton 0 → 5, Justin Clemmons 3 → 5; Anderson — Mosbacher (Annise Parker, `business`) 0 → 2.

Browser (cache bypassed, no console messages on any page): `/austin/district1/` eyebrow "OPEN SEAT · RUNOFF DECEMBER 12, 2026", heading "Who's in the Runoff", bars $123,010 / $64,992 / $38,147 / $38,087 / $1,317, 2 × ADVANCES TO RUNOFF + 4 × ELIMINATED, Nahas placeholder note, footer "Data through October 24, 2026". `/austin/goodwin/`: 592 unique donors; OOA "$49,648 counted of $83,000 allowed (60%) · Cap: $50,000 general + $33,000 runoff allowance (race advanced to a December runoff)"; Federal Partisan Lean 332 Dem-leaning (85.8%) / 43 Rep-leaning (11.1%). `/austin/ramos/` (opens on This Cycle): $65K / 805 unique donors / 1,103 contributions; OOA "$19,039 counted of $83,000 allowed (23%)" plus the 2022 card "$1,955 of $44,000 (4%)"; partisan panel 424 Dem (86.4%) / 56 Rep (11.4%) for the cycle's donors; Tarleton affiliation chip present. `/austin/`: "5 races · 19 candidates"; D1 tag RUNOFF DEC 12, "Open seat · runoff · Goodwin vs. Ramos · Natasha Harper-Madison not seeking re-election"; D3/D5/D8/D9 still FILING OPEN (pending step 6e). Screenshots (session temp): `C:\Users\HAMZAS~1\AppData\Local\Temp\claude\20bd6791b06d3fee\4644b339-8bd5-4849-807f-9efe1d98613d\scratchpad\final_d1.jpeg`, `final_goodwin.jpeg`, `final_hub.jpeg`.

## Step 11 — Delta affiliation scrub (LLM donor research on newly filed donors)

Re-run the Opus donor-research pass over the donors a new filing round added to a race pool that was already scrubbed once. Written for the District 1 delta (Nov 2026); the same shape works for any `dX`.

**Cost gate.** This step spends real money (≈ $4 per 20-donor batch on `claude-opus-5-5`, ≈ $8 on `opus-4-8`). Prep is free and read-only; nothing calls an LLM until `node _run_*.js`. Always stop after prep and show the user the batch count and estimate before running, and never restart automatically after an interruption — get a go.

**Order relative to step 5.** The apply originally wrote industry labels only `WHERE resolved_industry IS NULL`. In November 2026 the FEC-enrichment employer pass (step 5, `fec-employer`) ran concurrently and stamped heuristic labels on 18 of the delta donors first; of the 65 delta donors blocked by the gate, the heuristic label disagreed with the sourced LLM verdict on 26 (40 %), and every one checked was wrong (Casey Haney `Technology` → registered lobbyist, Consulting / PR; Tara Pohlmeyer `Nonprofit / Advocacy` → Texas AFL-CIO, Labor; John Tarleton `Engineering` → newspaper editor, Media; Donald Stuart `Real Estate` → law-firm partner, Legal; Doug Jaffe `Hospitality / Events` → developer, Real Estate). The gate in `_apply_d1_delta_results.py` is now `WHERE donor_id = ? AND (resolved_industry IS NULL OR resolved_confidence IS NULL OR resolved_confidence NOT LIKE 'llm-research-%')`: a sourced high/medium research verdict overrides keyword heuristics (`employer`, `fec-employer`, `occupation`, `*-incr`, `cross-identity`) but never an earlier `llm-research-*` verdict, so re-applying stays idempotent and two research corpora cannot fight. Keyword heuristics seed a classification; they should not pin it. With that gate the step can run before or after step 5; running it after is simpler because the FEC lean then rides along in the batch input.

### 11.0 What the scrub does

Each 20-donor batch goes to `claude -p` (headless Claude Code CLI, `--max-budget-usd 25` per job, 3–4 parallel workers) with `_research_instructions_v3.md`. The model researches each donor on the web and writes `<batch>_results.json`. The apply step writes `donor_identities.resolved_industry` / `resolved_employer_display` / `resolved_confidence = 'llm-research-<high|medium>'` under the gate above (low-confidence verdicts are kept in the corpus but never applied) and inserts `civic_affiliations` rows keyed on `canonical_name`, deduped on `(canonical_name, organization)`. After the profile rebuild (steps 7–9) the new donors show industry/employer tags and affiliation chips on the race and candidate pages.

Batch input row (one per donor; field names are fixed, the instructions key on `site_total`): `donor_id, name, zip, site_total, gave_to, occupations, employer_strings, locations, first_gift, last_gift, fec_partisan_lean, fec_donation_count`. Result row the apply expects: `donor_id, name, resolved_employer, industry, confidence (high|medium|low), evidence, source_url, searches_run{fec_pac, tx_lobbyist, bio_full_read}, affiliations[{org, role, category, source_url, snippet}]`.

### 11.1 Working dir (repo root, not inside `archive/`)

```bash
mkdir d1_delta_research
cp archive/travis_research/_research_instructions_v3.md d1_delta_research/
cp archive/d1_research/_prep_d1_batches.py   d1_delta_research/_prep_d1_delta_batches.py
cp archive/d1_research/_run_d1_research.js   d1_delta_research/_run_d1_delta_research.js
cp archive/d1_research/_apply_d1_results.py  d1_delta_research/_apply_d1_delta_results.py
```

Research dirs live at the repo root while active and are committed (inputs, results, usage log, scripts), then move under `archive/` when done. `_scratch/` is ignored; `d1_delta_research/` is not (`git check-ignore -v d1_delta_research/x.json` prints nothing). For the next district, copy from `archive/d1_delta_research/` or `archive/d3_delta_research/` instead: their scripts already carry every fix below and resolve the repo root from either location (`REPO = ROOT.parent.parent if ROOT.parent.name == "archive" else ROOT.parent`), so the copies run unchanged from the repo root.

### 11.2 Fixes the copied scripts need (the archived originals point at paths that no longer exist)

| Script | Archived | Delta |
|---|---|---|
| DB path (all three) | `ROOT/../austin_finance.db` → `archive/austin_finance.db` (missing) | `Path(__file__).resolve().parent.parent / 'austin_finance.db'` |
| Coverage globs (prep) | `../travis_research/donorbatch*.json`, `../travis_research/_pilot_covered_ids.json` | `../archive/travis_research/donorbatch*.json`, `../archive/travis_research/_pilot_covered_ids.json`, `../archive/d1_research/d1batch_*.json`, `../archive/d3_research/d3batch_*.json`, `../archive/d1_delta_research/d1delta_*.json`, `../archive/d3_delta_research/d3delta_*.json` — every finished `archive/d*_research/d*batch_*.json` and `archive/d*_delta_research/d*delta_*.json` |
| Batch prefix (prep + driver regex) | `d1batch_NN.json`, `/^d1batch_\d+\.json$/` | `d1delta_NN.json`, `/^d1delta_\d+\.json$/` — a different prefix so the driver can never pick up the finished archive set |
| Apply glob / gate | `d1batch_*_results.json`; `WHERE resolved_industry IS NULL` | `d1delta_*_results.json`; the widened gate quoted above |
| Instructions path (driver) | `../travis_research/_research_instructions_v3.md` | local copy in the working dir |
| Logs (driver) | `_d1_usage_log.jsonl`, `_d1_job_errors.log` | `_d1_delta_usage_log.jsonl`, `_d1_delta_job_errors.log` |
| Model / workers (driver) | `claude-opus-4-8`, `POOL = 4` | current Opus (`claude-opus-5-5` as of 2026-11; leave the old value in a comment), `POOL = 3` (see 11.4) |

Two coverage rules the original prep lacked — **both required, or already-scrubbed donors are re-billed**:

1. **`identity_merges` remap.** Every FEC dedup (step 5d; also 2026-08-19) merges donor ids (`merged_donor_id → into_donor_id`), and the archived batch files hold the old ids. Covered set = batch ids ∪ their merge targets, followed transitively (`while id in merge_map: id = merge_map[id]`). For D1, 21 of 606 archived ids were dead; all 21 remapped.
2. **`resolved_confidence LIKE 'llm-research-%'` skip.** Only an apply step writes that value, so it is a direct "already researched" flag that survives id churn.

Keep the pool rule unchanged: donors to the race's candidates (exact `recipient` strings) with `SUM(COALESCE(balanced_amount, contribution_amount)) >= 100`, positive rows only, lifetime (no cycle window), grouped by `donor_id`, no individual/entity filter, no joint special-casing, plus the lowercased `canonical_name` match against `civic_affiliations`. Open the DB read-only in the prep and in the apply's `--dry-run` (`sqlite3.connect('file:…?mode=ro', uri=True)`); other steps may be writing (WAL).

### 11.3 Prep → review → go/no-go

```bash
cd d1_delta_research && "$PY" _prep_d1_delta_batches.py
```

It prints pool / covered-by-source / uncovered / per-candidate split and writes `d1delta_NN.json`. Before spending, check: no delta `donor_id` appears in any archived batch after remap; the "already covered" breakdown is plausible (travis/pilot ids pre-date the July migration and are mostly dead, so their coverage shows up under the name match / `llm-research` rows, not under "travis"); uncovered donors whose first gift predates the last scrub are few (threshold crossers plus the handful the last run missed); ~5 random delta donors reconcile to their `campaign_finance` rows (zero-`balanced_amount` restatement rows excluded).

Cost estimate = batches × observed $/batch; wall clock ≈ ceil(batches / POOL) × minutes/batch. Present it and **stop for a go/no-go**.

| Run | Model | $/batch (20 donors) | min/batch |
|---|---|---|---|
| D1 Jul 2026 (606 donors) | opus-4-8 | $8.34 | 6–15 (median ~8) |
| D3 2026 | opus-4-8 | $4.43 | 5–8 |
| D1 delta Nov 2026 (230 donors) | opus-5-5 | **$3.87** ($1.27–7.27) | 2.5–8 (median 5.8) |

Cost scales with how many donors have a public footprint, not with donor count: the $500-tier batches averaged $4.51, the $100-tier batches $3.72. Use ≈ $4 and ≈ 6 min per batch for the next estimate on opus-5-5.

### 11.4 Run (costs money)

```bash
cd d1_delta_research && node _run_d1_delta_research.js > _d1_delta_run_log.txt 2>&1   # needs `claude` CLI on PATH; no npm SDK
```

Resumable: a re-run only picks up batches without a `_results` twin, and workers write the results file only at the end, so an interrupted run leaves no partial files. Watch `_d1_delta_job_errors.log`; a batch that fails 3× is reported FAILED at the end and re-runs by invoking the driver again. Check the first finished batch's `total_cost_usd` in `_d1_delta_usage_log.jsonl` against the estimate.

**Memory reap and relaunch.** Each `claude -p` worker is a full headless Claude Code process (~400 MB plus node children). On 2026-11-09, with `POOL = 4` plus a browser and Discord, the 16 GB laptop went critically low on memory one minute into wave 2 and Claude Code's background-shell reaper killed the driver (same mechanism as the step-5 FEC kill; `_d1_delta_job_errors.log` stayed empty — not a driver or CLI error). Fix that worked: relaunch the driver **detached from Claude Code** (PowerShell `Start-Process node -ArgumentList _run_d1_delta_research.js -WorkingDirectory <dir> -RedirectStandardOutput _d1_delta_run_log_wave2.txt -RedirectStandardError _d1_delta_run_err_wave2.txt -WindowStyle Hidden -PassThru`, as in step 5b) with `POOL = 3`, and wait on it from the session with a single background `until` loop that exits when all results files exist **or** the PID disappears. Alternative: start Claude Code with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1`. Never restart automatically after a reap.

### 11.5 Verify the corpus, then apply → rebuild

Mandatory before the apply (a small script next to the driver — `verify_d1_delta.py` was written ad hoc in Nov 2026; copy it into the research dir next time): every results file parses; row count = input count; **every result `donor_id` is in its input batch**; every `industry` is a taxonomy label; every affiliation has `org` + `source_url`. The driver's `goodOutput` only fails a batch when > 50 % of ids are missing, so a single mistyped id passes it silently and the apply's `WHERE donor_id = ?` matches nothing (Nov 2026: one UUID group mistyped in batch 01, fixed by string replacement in the results JSON). Spot-read 10–20 donors across candidates, including every `oil_gas` / `military_defense` / `gun_*` row, against the category definitions; **category corrections are made in the results JSON, not in the DB after the fact** — the JSON is the source of truth and the apply is idempotent.

```bash
"$PY" _apply_d1_delta_results.py --dry-run    # read-only; upper bound — it does not evaluate the gate
"$PY" _apply_d1_delta_results.py              # writes donor_identities + civic_affiliations; log the output
```

Before applying with the widened gate, dump the affected donors' previous `(donor_id, canonical_name, resolved_industry, resolved_employer_display, resolved_confidence)` plus the incoming label to a CSV in the research dir (`_d1_delta_overridden_labels.csv`, 65 rows in Nov 2026) so the override is reversible with one UPDATE per row. Then rebuild: steps 7–9 as above (`build_race.py --all`, `rebuild_all_ooa.py`, landing), and eyeball a few newly tagged donors and affiliation chips on the race page and profiles (step 10 records what rendered in Nov 2026). If the apply ran against a worktree copy of the DB, re-run it against the canonical DB after merge.

### 11.6 Archive

```bash
git mv d1_delta_research archive/d1_delta_research
```

First delete the driver debris (step 10b item 6), then commit inputs, results, usage log, apply/run logs, the overridden-labels CSV and the scripts together (how `archive/d1_research` etc. got there — one commit at reorg time). Add a line to `archive/README.md` under the per-district research corpora and a one-line entry (batches, $ total, model) to the refresh log for that month. The usage log stays with its corpus; do not merge it into `_d1_usage_log.jsonl`.

### Worked example — District 1 delta, November 2026

Prep 2026-11-09 (read-only). Pool rule: ≥ $100 to Goodwin / Ramos / Anderson / Brown / Riggins.

| | donors |
|---|---|
| ≥ $100 D1 donors after the October fetch | 890 |
| already covered | 657 — `archive/d1_research` live ids 585, `archive/d3_research` 32, via `identity_merges` remap 16, `civic_affiliations` name match only 24, travis/pilot 0 (ids pre-date the July migration) |
| uncovered but blank `canonical_name` (excluded) | 3 |
| **uncovered → delta pool** | **230** (130 are `tcv-` identities minted in step 3); Ramos 123, Goodwin 39, Brown 39, Anderson 33, Riggins 1 (a donor can count for several) |
| batches | **12** (11 × 20 + 1 × 10) |

Checks: 0 delta ids in any archived batch after remap; 0 with `llm-research-%`; min `site_total` $100; 5/5 spot-checks reconciled. Of the 232 October newcomers ≥ $100, 183 were in the delta; 32 were covered by the D3 scrub (Shah/Velásquez real-estate donors who also gave $500 to D1) and 17 were same-name matches to already-researched people. 50 delta donors had a first gift before July: 46 threshold crossers or July gifts first filed in October, ~4 genuine misses from the July run. Estimate presented: 12 × $8.34 = $100 (D1 rate) / 12 × $4.43 = $53 (D3 rate), 20–45 min.

Run 2026-11-09 06:57Z–07:24Z: **12/12 batches, 230/230 donors, $46.49 on `claude-opus-5-5`** ($3.87/batch mean, median 349 s/batch), 0 failed jobs, 0 retries. Wave 1 (batches 01–04, POOL 4) $18.03, finished 07:05Z; **07:06Z reaped** under memory pressure; waves 2–3 (05–12, POOL 3, detached, PID 7604) $28.46, finished 07:23Z. Per batch: 01 $4.17 · 02 $3.26 · 03 $6.38 · 04 $4.22 · 05 $2.32 · 06 $4.52 · 07 $3.02 · 08 $7.27 · 09 $2.55 · 10 $3.57 · 11 $3.94 · 12 (10 donors) $1.27.

Corpus: 230 rows; confidence high 56 / medium 57 / low 117 (51 % low vs July's 22 % — this delta is dominated by $100–$250 Ramos small donors with no public footprint, and opus-5-5 reports LinkedIn / TransparencyUSA 403s and FEC 429s candidly in `searches_run`, 115/230 with a `false`; the apply ignores that field); 223 with an industry; 45 donors / 94 affiliation rows (political 40, civic 38, business 12, military_defense 2, oil_gas 1, gun_control 1 after one edit). Defect fixed before apply: Glynn Jordan's `donor_id` mistyped in batch 01. Spot-reads (17 donors incl. every oil_gas / military_defense / gun row): every call backed by its source and consistent with the filed occupation/employer/zip; same-name people separated explicitly; out-of-state donors that look odd (an Illinois state representative, a Brooklyn editor, a Maryland biotech VP) are what the filings say. One judgment call: Annise Parker (Anderson, $100), `oil_gas` for "20 years in oil and gas, 18 at Mosbacher Energy" without an executive/board/owner role — changed to `business` in `d1delta_09_results.json` (coordinator decision); Francesca Cook's two `military_defense` rows kept (SVP + registered federal lobbyist meets the definition).

Apply (both runs in `_d1_delta_apply_log.txt`; dry run `_d1_delta_apply_dryrun.txt` said 113 donors / 94 rows):

| | first apply (original gate) | second apply (widened gate) | cumulative |
|---|---|---|---|
| donor rows updated | 48 (21 high, 27 medium); 65 blocked by existing heuristic labels (`employer` 34, `fec-employer` 18, `occupation` 6, `*-incr` 6, `cross-identity` 1) | **65** (all previously blocked; priors saved to `_d1_delta_overridden_labels.csv`) | **113** `llm-research-*`, 117 left at low confidence |
| `llm-research-%` rows DB-wide | 1,198 → 1,246 | → **1,311** | |
| `civic_affiliations` rows | 2,112 → **2,205** (+93; one within-run duplicate — Sylvia Camarillo's Travis County Democratic Party listed twice — collapsed by the dedup) | unchanged | 2,205 |
| `PRAGMA quick_check` | ok | ok | |

Rebuild and render: done in the closing pass (steps 7–10 above); the step-10 worked example lists the Texas AFL-CIO / Pohlmeyer / Haney (Goodwin), Commission Shift / Tarleton / Clemmons (Ramos) and Mosbacher (Anderson) entries now in the profile JSON and the fall in `Unknown` industry dollars. Archive move (11.6) done in PR #40 (2026-11-09): `archive/d1_delta_research/` (the 22 scratch intermediates were deleted before the PR #39 commit).

Follow-ups surfaced by the delta (not part of this step): 3 pool donors with empty `canonical_name` — joint-shadow half-rows (`68b3d570cdf64cad` Askew/Brown $450, `c98134210238c32d` Landry/Brown $431.85, `e13e67200499de64` Howsey/Anderson $250); 438 blank-name identities exist DB-wide; fix the identity and they fall into the next delta. 11 `tcv-` newcomers skipped on the name match are identity fragments of already-researched donors (Bledsoe, Phillips ×2, Wendler, Pastor, Gilliland, Cody, Frey, Flahive, Thumlert, Callahan): affiliations render (keyed on name) but they carry no industry tag until merged. Fragments seen inside the delta itself (harmless to apply, belong in identity-frag-scan): Rachel Kitto (04/05), Sara Gore / "Sara D Gore" (09), Lilly Ann / Lilly A Ortiz (06/11), Brandi Nelson (07/11 — different filed employers, may be two people), Shuronda Robinson / "Shuronda Parks" (06/07, both Adisa Communications).

### Worked example — District 3 delta, November 2026

Second run of this step, 2026-11-09, from `d3_delta_research/` (copied from `d1_delta_research/`, every 11.2 fix carried over; coverage globs also include `../archive/d1_delta_research/d1delta_*.json`). Pool rule unchanged from `archive/d3_research/_prep_d3_batches.py`: ≥ $100 lifetime to the D3 candidates the race page renders with finance data — Velasquez / Shah / Romero / Skinner. Gavino Fernandez (2022 rows only, `has_data: false` on the roster) was left out under that rule; he would add 16 donors.

| | donors |
|---|---|
| ≥ $100 D3 donors after the October fetch | 706 |
| already covered | 617 — `archive/d3_research` live ids 513, `civic_affiliations` name match only 42, `identity_merges` remap 32, `archive/d1_research` 22, `archive/d1_delta_research` 5, travis 2, `llm-research` only 1 |
| uncovered but blank `canonical_name` (excluded) | 4 (all Velasquez; `e8ed4f575433530a` $526.48, `f0d597e383234980` $342.41, `295f2732331c1f58` $263.31, `d645fe45b980812b` $263.31) |
| **uncovered → delta pool** | **85** (57 `tcv-` identities); Velasquez 45, Shah 32, Skinner 6, Romero 2 (Maribel Romero + the candidate's own self-contributions) |
| batches | **5** (4 × 20 + 1 × 5) |

Checks: 0 delta ids in any archived batch after remap; 0 with `llm-research-%`; min `site_total` $100; 5/5 spot-checks reconciled. 11 delta donors had a first gift before the 2026-07-20 D3 scrub: 3 are 2022 Velasquez donors who crossed $100 in 2026, the other 8 gave in June–July 2026 and were first filed after that run.

Run 2026-11-09 13:48Z–13:59Z, launched detached from PowerShell from the start (PID 11268, POOL 3): **5/5 batches, 85/85 donors, $13.24 on `claude-opus-5-5`** ($2.65/batch mean; 01 $2.75 · 02 $3.46 · 03 $3.12 · 04 $2.62 · 05 (5 donors) $1.28; 176–360 s/batch), 0 failed jobs, 0 retries, no reap. `verify_d3_delta.py` (now kept in the research dir) found no structural defects: 85 rows, all ids in their input batches, all industries in taxonomy, every affiliation with org + source_url.

Corpus: confidence high 10 / medium 25 / low 50 (59 % low — Shah's $100–$500 donors and Skinner's `NA`/`NA` donors have almost no public footprint); 72 with an industry; 12 donors / 24 affiliation rows (business 12, political 7, civic 5). Spot-reads (16 donors incl. the one spectrum row): sources consistent with filed occupation/employer/zip throughout; both candidates' self-contributions correctly identified and tagged `political`; the two City of Austin registered lobbyists (Michele Lynch, MWSW; Jeff Howard, McLean & Howard) sourced to the clerk's registry. One category correction in `d3delta_01_results.json`: Adam Ahmad's `oil_gas` row (President, "I am petroleum" → A. M. Petroleum, a fuel wholesaler / JD's Supermarkets operator; company match "most likely", role not independently confirmed) changed to `business` under the Parker precedent — downstream fuel retail with an unconfirmed executive role does not meet the exec/board/owner-of-oil-and-gas definition. Notable cluster: Ahmad, Zinovia Yakis and Vanessa Calixto (AM Petroleum / JD's Market, $500 each to Velásquez Aug–Oct 2026) plus Hassan Ladnany (JD's clerk, $250) gave while JD's Riverside store was in an eminent-domain dispute with Austin Transit Partnership that names Velásquez as a decision-maker.

Apply 2026-11-09 14:00Z (`_d3_delta_apply_log.txt`; dry run `_d3_delta_apply_dryrun.txt` said 35 donors / 24 rows):

| | expected | applied |
|---|---|---|
| donor rows updated | 35 (10 high, 25 medium) | **35**; 18 overrode heuristic labels (`employer` 10, `fec-employer` 4, `occupation` 2, `occupation-incr` 2; 8 of the 18 changed the industry, all 8 checked and the research label was right — e.g. Calixto `Legal`/`fec-employer` "Martinez Law Firm" → AM Petroleum risk manager, Puerta `Technology`/Dell → Texas Historical Commission), priors in `_d3_delta_overridden_labels.csv` |
| `llm-research-%` rows DB-wide | 1,304 → 1,339 | **1,339** (+35) |
| `civic_affiliations` rows | 2,205 → 2,229 | **2,229** (+24, 0 dups) |
| `PRAGMA quick_check` | ok | ok |

Research labels on ≥ $100 donors per candidate afterwards: Velasquez 58 of 619 (was 36), Shah 11 of 80 (was 2), Romero 2 of 2, Skinner 2 of 6. The low Velasquez share is not this delta's doing: the original D3 scrub (558 donors) was applied under the old `resolved_industry IS NULL` gate, so only 26 of its 540 live donors carry `llm-research-*` — re-applying `archive/d3_research` (and `archive/d1_research`) under the widened gate is a proposed follow-up, measured read-only on 2026-11-09 (D3: 410 donors would change, 153 with a different industry label; D1: 357 / 138; none give outside D1/D3). Rebuild (steps 7–8, D3 only — the other profiles already carried the step-5e flags from PR #41) and the 11.6 archive move were done in PR #40 (2026-11-09); the corpus is at `archive/d3_delta_research/`.

## Post-refresh follow-ups (open after the November 2026 refresh)

Data and identities:

- **139 FEC 504 residue** identities left at `fec_matched = 0` (step 5b); script-side fix (zip-first narrowing for common names, strip glued initials), not retries. 24 are Ramos donors.
- **1,761 `city26-pending` review-queue pairs** (step 3c; +836 this refresh) — potential duplicate donors until a merge pass reads the queue.
- **438 blank-`canonical_name` identities** DB-wide (joint-shadow halves; step 11 follow-ups), 3 of them in the D1 pool.
- **11 `tcv-` identity fragments** of already-researched D1 donors named in step 11 (Bledsoe, Phillips ×2, Wendler, Pastor, Gilliland, Cody, Frey, Flahive, Thumlert, Callahan) plus the five in-delta pairs, and Perry Lorenz `68305c3f92668401` / `tcv-c5d82611…` (the dedup moved his FEC receipts and `climate_action` flag to the October fragment; step 5e) → identity-frag-scan.
- "Trust, Ashley" (Goodwin) misclassified ENTITY by `ENTITY_KEYWORDS` (step 3d).

Editorial and site:

- **Ellis `on_ballot`** (step 9): stamped true / "this cycle" although she missed the ballot; fix in the D8 pass (close her 2026 cycle in `CANDIDATE_CYCLES` or add an override to `update_landing_cycles.py`).
- **D3 / D5 `HAD_RUNOFF` pairs withheld** (`velasquez`, `shah`, `alter`, `weinberg`; step 6c item 3) pending sign-off; until added, those four OOA cards read against $50k instead of $83k.
- **`runoff_early_voting` "2026-11-30 to 2026-12-08"** on D1 is Chronicle-sourced only; confirm against the Clerk / Travis County before Nov 30 or drop the field (step 6c).
- **Nahas placeholder** (`has_data: false`, no DB rows, eliminated Nov 3): keep as is for now; after the canvass decide whether a zero-money eliminated card stays on the D1 page or moves to `omitted`.
- **D3 / D5 / D8 / D9 editorial passes** pending: rosters, `phase`, `result`, `vote_pct`, intros per step 6e's per-district recipe; then `build_race.py --all`, the hub's "N races · M candidates" count (19 → 22 with corrected rosters) and the `index.html` hard-coded "45 candidates decoded" / og alt.
- Post-canvass and post-Dec 12 edits listed at the end of step 6e.
