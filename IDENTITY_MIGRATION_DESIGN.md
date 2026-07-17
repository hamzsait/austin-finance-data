# identity_migration.py — Design Doc (2026-07-17)

Non-destructive, deterministic, idempotent re-clustering of donor identities across the
**whole** `austin_finance.db`. Replaces the fuzzy Union-Find in `build_identities.py` (which
silently drops blocks > 50 members — the fragmentation bug). Does **not** overwrite
`build_identities.py` and does **not** `DROP TABLE donor_identities` (that would nuke ~27
enrichment columns added by later scripts).

---

## 0. The bug being fixed (confirmed)

`build_identities.py:238-240` — `add_block(block_dict, max_block=50)` skips any
`(last_name, zip5)` block with `> 50` members. Skipped records are never compared, never
unioned, and each falls through to its own `uuid.uuid4()` at line 304.

Confirmed impact on current DB:
- **982** `(last, zip5)` blocks exceed 50 members, covering **122,048** rows.
- Blocks are dominated by ZIP **78721** (Austin Fire Fighters PAC payroll deductions):
  `johnson/78721` = 1,566 rows, `rodriguez/78721` = 1,009, etc.
- **Judah Rice**: 98 rows fragmented into **68** distinct `donor_id`s, $1,984.18 total.
  (Plan quoted $1,226 / 91 rows / 68 ids — the number grew because today's incremental
  2026 refresh added rows. Target: **1** unified id. Expected total ≈ **$1,984**, not $1,226.)

## 1. Schema facts that shape the design

`campaign_finance` (253,325 rows):
- amount col is `contribution_amount` **TEXT** (e.g. `"$1,984.18"`); date col is
  `contribution_date` TEXT. Plan's `amount`/`date` names don't exist — gates adapted.
- `donor_id` (primary donor), `donor_id_2` + `is_joint` (1,472 joint rows — the spouse is a
  genuinely separate identity; all 1,472 `donor_id_2` values exist in `donor_identities`).
- No street column — only `city_state_zip`. "street+zip" institutional detection is therefore
  approximated by zip5 outlier analysis.
- 16,455 rows have NULL donor_id: 12,639 are the new 2026 individuals (to be keyed here);
  the rest are non-individual / no-comma rows that never get an identity (stay NULL).

`donor_identities` (155,427 rows) — 37 cols. Base 10 + enrichment groups:
- FEC: `fec_partisan_lean, fec_total_dem/rep/other, fec_total_donations, fec_matched, fec_matched_at`
- Employer resolve: `resolved_industry, resolved_employer_display, resolved_confidence`
- Interest-group panels (same shape each): `ip_*`, `ff_*`, `gun_*` = `spectrum, tier, total, committees`
- TEC: `tec_total_dem/rep/other, tec_total_donations, tec_matched`

Enrichment tables keyed by donor_id (must be remapped when ids change):
- `fec_contributions_raw` — 4.0M rows, 44,387 donor_ids, `UNIQUE(donor_id, fec_sub_id)`.
- `texas_contributions_raw` — 1.8M rows, keyed via `austin_donor_id` (3,497 ids).
- `joint_donations` — `donor_id_1, donor_id_2, rowid_cf, parsed_name_2`.
- `civic_affiliations` — keyed by **`canonical_name`** (name-stable) → **no remap needed**.

## 2. Deterministic key (idempotent)

For each individual-with-comma row (same population `build_identities` processed —
`donor_type IN ('INDIVIDUAL','Individual') AND donor LIKE '%,%'`):

```
last, first = normalize_name(donor)          # reuse: ascii + nickname resolution + strip
zip5        = normalize_zip(city_state_zip)
if not last or not first: skip (donor_id stays NULL, as build_identities did)

base = f"{last}|{first}|{zip5}"
if zip5 in INSTITUTIONAL_ZIPS:               # employer/occupation tiebreak
    emp_occ = normalized(employer + occupation) tokens, sorted
    key = f"{base}|{emp_occ}"
else:
    key = base
donor_id = sha1(key.encode('utf-8')).hexdigest()[:16]
```

- Idempotent: same input → same 16-hex id. Re-runs are no-ops.
- Drops fuzzy soundex spelling-variant merging (Smith/Smyth no longer auto-merge). Accepted:
  the plan explicitly prioritizes determinism/idempotency and matches the SA + HD-41 fix.
  Nickname merging is **kept** (via `normalize_name`'s NICKNAMES table), so Bill/William merge.

**INSTITUTIONAL_ZIPS** — computed, not hardcoded: zip5 where
`rows > 5000 AND rows/distinct_names > 20`. Only **78721** qualifies (77.6 rows/name vs
2.5–4.6 everywhere else). At 78721 `distinct_emp≈1` per firefighter, so appending emp_occ
does **not** re-fragment the very rows we're consolidating. Caveat logged: two different
same-named firefighters at 78721 both listing AFD/firefighter can't be separated (no signal)
— they'll merge. Safer than fragmentation; noted in report.

**Joint second donor (`donor_id_2`)**: for each `is_joint=1` row, re-key `parsed_name_2`
(from `joint_donations`, joined on `rowid_cf`) with the row's zip5 using the same function.
Update `campaign_finance.donor_id_2` and `joint_donations.donor_id_1/2`.

## 3. Migration algorithm

1. **Backup** `austin_finance.db` → `austin_finance.backup-2026-07-17-preidentitymigration.db`;
   verify `PRAGMA integrity_check=ok` and identical `COUNT(*)`.
2. Capture **pre-migration invariants**: total rows, pre-2022 rows, `SUM(cast amount)`,
   distinct donor_id count, Judah Rice state. (amount cast expr fixed & reused verbatim.)
3. **Compute new ids** in Python for every individual-with-comma row → build
   `old_id → new_id` and `rowid → new_id` maps. Detect INSTITUTIONAL_ZIPS first.
4. **Aggregate new `donor_identities`** (one row per new_id) into a staging dict:
   - Base: canonical_name = modal raw name; canonical_zip = modal zip5;
     canonical_employer = modal emp; total_donated = Σ amount; record_count; campaigns =
     ∪ recipients; campaign_count; first/last_seen.
   - **Union enrichment** across all old_ids collapsing into this new_id:
     - FEC: Σ dem/rep/other/donations; `fec_partisan_lean = D/(D+R)` (None if 0);
       `fec_matched = max`; `fec_matched_at = max`.
     - TEC: Σ dem/rep/other/donations; `tec_matched = max`.
     - ip/ff/gun (each): `total = Σ`; `tier = max`; `spectrum` from the old_id with the
       largest panel total; `committees` = ∪ pipe-split, deduped.
     - resolved_industry/employer/confidence: from the old_id (with non-null industry) of
       highest `total_donated`.
5. **Rewrite tables inside one transaction**:
   - `campaign_finance`: `UPDATE donor_id, donor_id_2, match_confidence` per rowid via a
     temp `rowid→new_id` table + set-based `UPDATE`. match_confidence = `exact` if the new
     cluster has 1 row else `high`.
   - `donor_identities`: `DELETE FROM` + bulk `INSERT` the staged rows (table **kept**, all
     37 columns preserved — not dropped).
   - `fec_contributions_raw`: rebuild via `INSERT OR IGNORE INTO new SELECT map(donor_id),…`
     (the OR IGNORE dedupes collided `(new_id, fec_sub_id)`), then swap. Report dropped dups.
   - `texas_contributions_raw`: `UPDATE austin_donor_id = map(austin_donor_id)` (set-based).
   - `joint_donations`: `UPDATE donor_id_1/2` via row-level remap.
   - `civic_affiliations`: untouched (name-keyed).
6. **Verification gates** (query post-migration, pre-COMMIT — HALT + rollback if any fails):
   - total `COUNT(*)` unchanged · pre-2022 `COUNT(*)` unchanged · `SUM(amount)` unchanged
     (bit-identical — we never touch amount/date/rowset).
   - `COUNT(DISTINCT donor_id)` **decreased** meaningfully.
   - Judah Rice → exactly **1** donor_id, total ≈ $1,984 (±cents).
   - No new_id collision anomalies; `donor_identities` row count == distinct new ids.
   - `fec_contributions_raw` post-count ≤ pre-count (dedupe only) and every remaining
     donor_id exists in donor_identities.
   - Only on all-pass → `COMMIT`. Else `ROLLBACK`, restore note, report.
7. **Report**: before/after identity-row + distinct-donor_id counts; top 20 previously-
   fragmented donors and their consolidated totals; fec dup rows dropped; institutional-zip
   caveat count.

## 4. Idempotency / safety notes
- Deterministic ids ⇒ re-running yields identical ids; step-4 aggregation over an
  already-migrated table re-derives the same values (one row per id already).
- No `contribution_amount` / `contribution_date` / row is ever mutated ⇒ dollar & count
  invariants are structurally guaranteed; gates are tripwires, not hopes.
- Backup + single-transaction + rollback-on-gate-fail ⇒ no partial-write risk.
- Does not touch `travis_research/`. Does not run `build_identities.py` or `fetch_data.py`.

## 5. Step 3 note (2026 rows)
The whole-DB pass in §3 processes population by `donor_type+comma`, independent of existing
donor_id, so the 12,639 new NULL rows are keyed in the same pass. Step 3 becomes a
report: for those rowids, how many new_ids already existed pre-migration (existing donor
giving again) vs. brand-new. No separate keying pass needed.
