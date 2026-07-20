"""
identity_assign_incremental.py  (2026-07-17)

INCREMENTAL, NON-DESTRUCTIVE donor_id assignment for the new 2026 rows.

Scope — intentionally minimal (the fragmentation fix is a SEPARATE later
deliverable, see IDENTITY_MIGRATION_DESIGN.md):
  * Processes ONLY rows where donor_id IS NULL and the donor is an
    individual-with-comma (same population build_identities keys). Never reads
    or rewrites any already-assigned row, and never drops/rebuilds a table.
  * Attaches a new row to an EXISTING identity when its normalized
    (last, first, zip5) key already exists in donor_identities (the biggest
    fragment for that key is chosen). Otherwise mints a fresh uuid4 — matching
    the current table's id convention — shared across new rows with the same key.
  * Recomputes base aggregates ONLY for the identities that actually changed
    (existing ones that gained rows) and INSERTs base rows for brand-new
    identities. Enrichment columns (fec_*, ip_*, ff_*, gun_*, tec_*, resolved_*)
    are never touched.

Safety: single transaction, hard verification gates before COMMIT, ROLLBACK on
any gate failure. Back up the DB BEFORE running this (the driver does that).

Usage:
    python identity_assign_incremental.py            # execute
    python identity_assign_incremental.py --dry-run  # report only, no writes
"""

import argparse
import sqlite3
import uuid
from collections import defaultdict, Counter

import build_identities as bi   # reuse normalize_name / normalize_zip / normalize_employer

DB = r"C:\Users\Hamza Sait\Electoral\austin-finance-data\austin_finance.db"

INDIV = ('INDIVIDUAL', 'Individual')

# Cast expression reused VERBATIM for the SUM invariant (amounts are clean
# numeric TEXT — no $ or commas — verified 2026-07-17, but strip defensively).
AMT_CAST = "CAST(REPLACE(REPLACE(contribution_amount,'$',''),',','') AS REAL)"


def norm_key(donor, city_state_zip):
    """(last, first, zip5) using the same normalizers that built existing ids."""
    last, first = bi.normalize_name(donor)
    zip5 = bi.normalize_zip(city_state_zip)
    if not last or not first:
        return None
    return (last, first, zip5)


def invariants(cur):
    return {
        "total": cur.execute("SELECT COUNT(*) FROM campaign_finance").fetchone()[0],
        "pre2022": cur.execute(
            "SELECT COUNT(*) FROM campaign_finance WHERE contribution_date < '2022-01-01'"
        ).fetchone()[0],
        "sum": cur.execute(f"SELECT ROUND(SUM({AMT_CAST}),2) FROM campaign_finance").fetchone()[0],
        "distinct_donor": cur.execute(
            "SELECT COUNT(DISTINCT donor_id) FROM campaign_finance WHERE donor_id IS NOT NULL"
        ).fetchone()[0],
        "keyable_null": cur.execute(
            "SELECT COUNT(*) FROM campaign_finance WHERE donor_id IS NULL "
            "AND donor_type IN ('INDIVIDUAL','Individual') AND donor LIKE '%,%'"
        ).fetchone()[0],
        "di_rows": cur.execute("SELECT COUNT(*) FROM donor_identities").fetchone()[0],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=180)
    conn.isolation_level = None   # autocommit; we manage BEGIN/COMMIT explicitly
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=180000")   # wait out the parallel writer
    cur = conn.cursor()

    # Non-destructive: speeds up the aggregation join below AND all future
    # profile generation (which joins cf.donor_id repeatedly).
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cf_donor_id ON campaign_finance(donor_id)")
    conn.commit()

    pre = invariants(cur)
    print("PRE-INVARIANTS:")
    for k, v in pre.items():
        print(f"  {k:16} {v:,}" if isinstance(v, int) else f"  {k:16} {v}")

    # ── 1. Existing key -> donor_id map (from donor_identities) ────────────────
    # For a fragmented key (many identities share it) pick the biggest fragment
    # by record_count, tie-broken by total_donated, then id (deterministic).
    print("\nBuilding existing (last,first,zip5) -> donor_id map from donor_identities ...")
    best_for_key = {}   # key -> (record_count, total_donated, donor_id)
    scanned = 0
    for did, cname, czip, rc, tot in cur.execute(
        "SELECT donor_id, canonical_name, canonical_zip, "
        "COALESCE(record_count,0), COALESCE(total_donated,0) FROM donor_identities"
    ):
        scanned += 1
        if not cname:
            continue
        # canonical_zip is already zip5; feed it through the same zip normalizer
        key = norm_key(cname, czip or "")
        if key is None:
            continue
        cand = (rc or 0, tot or 0.0, did or "")
        cur_best = best_for_key.get(key)
        if cur_best is None or cand > cur_best:
            best_for_key[key] = cand
    existing_map = {k: v[2] for k, v in best_for_key.items()}
    print(f"  scanned {scanned:,} identities -> {len(existing_map):,} distinct keys")

    # ── 2. Load keyable NULL rows ──────────────────────────────────────────────
    null_rows = cur.execute(
        "SELECT rowid, donor, city_state_zip, donor_reported_employer, "
        "donor_reported_occupation FROM campaign_finance "
        "WHERE donor_id IS NULL AND donor_type IN ('INDIVIDUAL','Individual') "
        "AND donor LIKE '%,%'"
    ).fetchall()
    print(f"\nKeyable NULL rows to assign: {len(null_rows):,}")

    # First pass: resolve keys, split new vs existing, count new-key multiplicity
    row_key = {}          # rowid -> key
    skipped = []          # rowids we can't parse
    new_key_counts = Counter()
    for rowid, donor, csz, emp, occ in null_rows:
        key = norm_key(donor, csz)
        if key is None:
            skipped.append(rowid)
            continue
        row_key[rowid] = key
        if key not in existing_map:
            new_key_counts[key] += 1

    # Mint a stable uuid4 per brand-new key (shared across that key's rows)
    new_key_id = {k: str(uuid.uuid4()) for k in new_key_counts}

    # Build the campaign_finance updates
    updates = []          # (donor_id, match_confidence, rowid)
    attached_existing = 0
    created_new_rows = 0
    affected_existing_ids = set()
    new_ids = set(new_key_id.values())
    for rowid, key in row_key.items():
        if key in existing_map:
            did = existing_map[key]
            conf = "high"
            attached_existing += 1
            affected_existing_ids.add(did)
        else:
            did = new_key_id[key]
            conf = "exact" if new_key_counts[key] == 1 else "high"
            created_new_rows += 1
        updates.append((did, conf, rowid))

    print(f"  attach to existing identity : {attached_existing:,} rows "
          f"-> {len(affected_existing_ids):,} existing identities gain rows")
    print(f"  brand-new identities        : {len(new_ids):,} "
          f"(covering {created_new_rows:,} rows)")
    print(f"  unparseable (left NULL)     : {len(skipped):,}")

    # Some existing identities we attach to have ZERO prior cf.donor_id presence
    # (e.g. joint second-donor identities live in donor_identities but appear in
    # campaign_finance only as donor_id_2). Attaching gives them their first
    # donor_id-column row, so they add to COUNT(DISTINCT donor_id). Count them
    # now (pre-write) so the distinct-donor gate expects the right delta.
    orphan_attach = 0
    if affected_existing_ids and not args.dry_run:
        cur.execute("CREATE TEMP TABLE _chk(donor_id TEXT PRIMARY KEY)")
        cur.executemany("INSERT OR IGNORE INTO _chk VALUES (?)",
                        [(d,) for d in affected_existing_ids])
        prior_present = cur.execute(
            "SELECT COUNT(*) FROM _chk c WHERE EXISTS("
            "SELECT 1 FROM campaign_finance cf WHERE cf.donor_id = c.donor_id)"
        ).fetchone()[0]
        orphan_attach = len(affected_existing_ids) - prior_present
        cur.execute("DROP TABLE _chk")
        print(f"  (existing ids w/ no prior cf presence: {orphan_attach})")

    if args.dry_run:
        print("\n[dry-run] no writes. Sample new identities:")
        for k, i in list(new_key_id.items())[:5]:
            print("   ", k, "->", i)
        conn.close()
        return

    # ── 3. Apply writes in a single transaction ────────────────────────────────
    # BEGIN IMMEDIATE grabs the write lock up-front (no read->write upgrade, which
    # SQLite refuses immediately as SQLITE_BUSY_SNAPSHOT when another writer —
    # here the parallel city_resolve_incremental job — is active). busy_timeout
    # makes us WAIT for that other writer instead of failing fast.
    try:
        cur.execute("BEGIN IMMEDIATE")

        # Re-read the baseline under our exclusive write lock so PRE and POST are
        # captured consistently (a concurrent writer can't move them mid-txn).
        pre = invariants(cur)

        cur.executemany(
            "UPDATE campaign_finance SET donor_id=?, match_confidence=? WHERE rowid=?",
            updates,
        )

        # Recompute base aggregates for affected + new ids in ONE pass.
        # Single indexed join over campaign_finance (idx_cf_donor_id), then
        # aggregate in Python (avoids GROUP_CONCAT separator limits + correlated
        # subqueries). Existing identities keep canonical_* + all enrichment;
        # only numeric aggregates are refreshed. New identities get modal
        # canonical_name/zip/employer.
        cur.execute("CREATE TEMP TABLE _affected(donor_id TEXT PRIMARY KEY)")
        cur.executemany("INSERT OR IGNORE INTO _affected VALUES (?)",
                        [(d,) for d in (affected_existing_ids | new_ids)])

        agg = defaultdict(lambda: {
            "sum": 0.0, "n": 0, "fs": "9999", "ls": "0000",
            "recips": set(), "names": [], "zips": [], "emps": [],
        })
        for did, donor, csz, emp, recip, date, amt in cur.execute(f"""
            SELECT cf.donor_id, cf.donor, cf.city_state_zip,
                   cf.donor_reported_employer, cf.recipient,
                   cf.contribution_date, {AMT_CAST}
            FROM campaign_finance cf
            JOIN _affected a ON a.donor_id = cf.donor_id
        """):
            m = agg[did]
            m["sum"] += (amt or 0.0)
            m["n"] += 1
            if date:
                if date < m["fs"]:
                    m["fs"] = date
                if date > m["ls"]:
                    m["ls"] = date
            if recip:
                m["recips"].add(recip)
            m["names"].append(donor or "")
            z = bi.normalize_zip(csz or "")
            if z:
                m["zips"].append(z)
            e = bi.normalize_employer(emp or "")
            if e:
                m["emps"].append(e)

        def most_common(lst):
            return Counter(lst).most_common(1)[0][0] if lst else ""

        def finalize(m):
            camps = "|".join(sorted(m["recips"]))
            fs = m["fs"] if m["fs"] != "9999" else ""
            ls = m["ls"] if m["ls"] != "0000" else ""
            return (round(m["sum"], 2), m["n"], fs, ls, camps, len(m["recips"]))

        # Existing identities: numeric aggregates only.
        upd_existing = []
        for did in affected_existing_ids:
            if did in agg:
                tot, rc, fs, ls, camps, ccount = finalize(agg[did])
                upd_existing.append((tot, rc, fs, ls, camps, ccount, did))
        cur.executemany("""
            UPDATE donor_identities
               SET total_donated=?, record_count=?, first_seen=?, last_seen=?,
                   campaigns=?, campaign_count=?
             WHERE donor_id=?
        """, upd_existing)

        # New identities: full base row (enrichment cols default to NULL/0).
        ins_new = []
        for did in new_ids:
            m = agg[did]
            tot, rc, fs, ls, camps, ccount = finalize(m)
            ins_new.append((
                did, most_common(m["names"]), most_common(m["zips"]),
                most_common(m["emps"]), tot, ccount, camps, rc, fs, ls,
            ))
        cur.executemany("""
            INSERT INTO donor_identities
              (donor_id, canonical_name, canonical_zip, canonical_employer,
               total_donated, campaign_count, campaigns, record_count,
               first_seen, last_seen)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, ins_new)

        # ── 4. Verification gates (pre-COMMIT) ─────────────────────────────────
        post = invariants(cur)
        gates = []
        gates.append(("total rows unchanged", post["total"] == pre["total"], f'{pre["total"]} -> {post["total"]}'))
        gates.append(("pre-2022 unchanged", post["pre2022"] == pre["pre2022"], f'{pre["pre2022"]} -> {post["pre2022"]}'))
        # SUM: allow <=1c float noise
        sum_ok = abs((post["sum"] or 0) - (pre["sum"] or 0)) < 0.01
        gates.append(("SUM(amount) unchanged", sum_ok, f'{pre["sum"]} -> {post["sum"]}'))
        gates.append(("keyable-null now == unparseable",
                      post["keyable_null"] == len(skipped),
                      f'{post["keyable_null"]} (expected {len(skipped)})'))
        expected_distinct = pre["distinct_donor"] + len(new_ids) + orphan_attach
        gates.append(("distinct donor_id += #new + orphan-attach",
                      post["distinct_donor"] == expected_distinct,
                      f'{pre["distinct_donor"]} -> {post["distinct_donor"]} '
                      f'(expected +{len(new_ids)}+{orphan_attach}={expected_distinct})'))
        orphans = cur.execute("""
            SELECT COUNT(*) FROM (
              SELECT DISTINCT cf.donor_id FROM campaign_finance cf
              LEFT JOIN donor_identities di ON di.donor_id = cf.donor_id
              WHERE cf.donor_id IS NOT NULL AND di.donor_id IS NULL)
        """).fetchone()[0]
        gates.append(("no orphan donor_ids", orphans == 0, f'orphans={orphans}'))
        gates.append(("di row count grew by #new",
                      post["di_rows"] == pre["di_rows"] + len(new_ids),
                      f'{pre["di_rows"]} -> {post["di_rows"]} (+{len(new_ids)})'))

        print("\nVERIFICATION GATES:")
        all_ok = True
        for name, ok, detail in gates:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
            all_ok = all_ok and ok

        if not all_ok:
            conn.rollback()
            print("\n*** A GATE FAILED — ROLLED BACK, no changes committed. ***")
            conn.close()
            raise SystemExit(1)

        conn.commit()
        print("\nCOMMITTED.")
    except Exception:
        conn.rollback()
        raise
    finally:
        # drop temp tables best-effort
        try:
            cur.execute("DROP TABLE IF EXISTS _affected")
            cur.execute("DROP TABLE IF EXISTS _newids")
        except Exception:
            pass

    # ── 5. Report ──────────────────────────────────────────────────────────────
    print("\n=== REPORT ===")
    print(f"  Rows attached to EXISTING identities : {attached_existing:,}")
    print(f"  Rows given a NEW identity            : {created_new_rows:,}")
    print(f"  New identities created               : {len(new_ids):,}")
    print(f"  Existing identities that gained rows : {len(affected_existing_ids):,}")
    print(f"    of which had no prior cf presence  : {orphan_attach:,}")
    print(f"  Rows left NULL (unparseable name)    : {len(skipped):,}")
    conn.close()


if __name__ == "__main__":
    main()
