"""
Priority FEC enrichment for specific employer groups (Endeavor, Armbrust & Brown).
Runs alongside the main fec_enrich.py (WAL mode handles concurrency).
"""
import sqlite3, sys, os

DB = "austin_finance.db"

# Get the donor IDs we want to prioritize BEFORE importing fec_enrich
conn = sqlite3.connect(DB, timeout=120)
conn.execute("PRAGMA journal_mode=WAL")
cur = conn.cursor()
cur.execute("""
    SELECT DISTINCT di.donor_id, di.canonical_name, di.canonical_zip
    FROM donor_identities di
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    LEFT JOIN employer_identities ei ON ei.employer_id = cf.employer_id
    WHERE cf.correction != 'X'
      AND (ei.canonical_name LIKE '%Endeavor%' OR cf.donor_reported_employer LIKE '%Endeavor%'
           OR ei.canonical_name LIKE '%Armbrust%' OR cf.donor_reported_employer LIKE '%Armbrust%')
      AND (di.fec_matched = 0 OR di.fec_matched IS NULL)
""")
priority_donors = [{"donor_id": r[0], "canonical_name": r[1], "canonical_zip": r[2]} for r in cur.fetchall()]
conn.close()

print(f"Priority batch: {len(priority_donors)} Endeavor/Armbrust donors to process", flush=True)

# Now patch sys.argv and run fec_enrich's main with a custom donor list
# Instead of importing, we'll just inline the key logic
import io, time, requests
from datetime import datetime, timezone

# Import fec_enrich carefully
import fec_enrich as fe

conn = sqlite3.connect(DB, timeout=120)
conn.execute("PRAGMA journal_mode=WAL")
conn.row_factory = sqlite3.Row
fe.setup_db(conn)

session = requests.Session()
session.headers.update({"User-Agent": "Austin Finance Research / priority-batch"})
rate_limiter = fe.RateLimiter(max_calls=1600, window_seconds=600)
committee_cache = fe.CommitteeCache(conn, session, rate_limiter)

stats = {"matched": 0, "no_history": 0, "errors": 0}

for i, donor in enumerate(priority_donors, 1):
    donor_id = donor["donor_id"]
    cname = donor["canonical_name"]
    local_zip = (donor["canonical_zip"] or "")[:5]

    fec_query, local_last, local_first = fe.normalize_name_for_fec(cname)
    if not local_last:
        conn.execute("UPDATE donor_identities SET fec_matched=1, fec_matched_at=? WHERE donor_id=?",
                     (datetime.now(timezone.utc).isoformat(), donor_id))
        conn.commit()
        continue

    if i % 10 == 0 or i <= 5:
        print(f"  [{i}/{len(priority_donors)}] {cname}", flush=True)

    try:
        raw_rows = fe.query_fec_schedule_a(session, fec_query, local_zip, rate_limiter)
    except Exception as e:
        print(f"  [ERROR] {cname}: {e}", flush=True)
        stats["errors"] += 1
        continue

    if not raw_rows:
        stats["no_history"] += 1
        conn.execute("UPDATE donor_identities SET fec_matched=1, fec_total_donations=0, fec_matched_at=? WHERE donor_id=?",
                     (datetime.now(timezone.utc).isoformat(), donor_id))
        conn.commit()
        continue

    confirmed = [(row, score) for row in raw_rows for ok, score in [fe.confirm_match(local_last, local_first, local_zip, row)] if ok]

    if not confirmed:
        stats["no_history"] += 1
        conn.execute("UPDATE donor_identities SET fec_matched=1, fec_total_donations=0, fec_matched_at=? WHERE donor_id=?",
                     (datetime.now(timezone.utc).isoformat(), donor_id))
        conn.commit()
        continue

    dem_total = rep_total = other_total = 0.0
    raw_inserts = []
    for row, score in confirmed:
        committee_id = row.get("committee_id", "")
        amount = row.get("contribution_receipt_amount") or 0.0
        if amount <= 0:
            continue
        classification = committee_cache.get(committee_id) if committee_id else "Other"
        if classification == "Dem":
            dem_total += amount
        elif classification == "Rep":
            rep_total += amount
        else:
            other_total += amount
        raw_inserts.append((
            donor_id, committee_id, amount,
            row.get("contribution_receipt_date"),
            row.get("contributor_name"),
            row.get("contributor_city"),
            row.get("contributor_zip"),
            (row.get("contributor_employer") or "").strip() or None,
            (row.get("contributor_occupation") or "").strip() or None,
            row.get("sub_id"), score
        ))

    lean = dem_total / (dem_total + rep_total) if (dem_total + rep_total) > 0 else None

    conn.executemany("""
        INSERT OR REPLACE INTO fec_contributions_raw
        (donor_id, committee_id, contribution_amount, contribution_date,
         fec_contributor_name, fec_contributor_city, fec_contributor_zip,
         fec_employer, fec_occupation, fec_sub_id, confirm_score)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, raw_inserts)
    conn.execute("""
        UPDATE donor_identities
        SET fec_partisan_lean=?, fec_total_dem=?, fec_total_rep=?,
            fec_total_other=?, fec_total_donations=?,
            fec_matched=1, fec_matched_at=?
        WHERE donor_id=?
    """, (lean, dem_total, rep_total, other_total, len(raw_inserts),
          datetime.now(timezone.utc).isoformat(), donor_id))
    conn.commit()

    lean_str = f"{lean:.2f}" if lean is not None else "n/a"
    print(f"    {cname}: D=${dem_total:,.0f} R=${rep_total:,.0f} lean={lean_str}", flush=True)
    stats["matched"] += 1

print(f"\nDone. matched={stats['matched']}  no_history={stats['no_history']}  errors={stats['errors']}", flush=True)
conn.close()
