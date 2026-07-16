"""Apply user decisions from travis_identity_review.csv.

For rows marked decision=MERGE: repoint the county donor's campaign_finance
rows from their tcv- identity to the existing identity, delete the tcv-
identity, recompute the surviving identity's aggregates, and mark the
review_queue row resolved. Everything else -> resolved as SEPARATE.

Usage: python travis_apply_review.py travis_identity_review.csv [--dry-run]
"""
import csv, sqlite3, sys

DB = "austin_finance.db"
path = sys.argv[1] if len(sys.argv) > 1 else "travis_identity_review.csv"
DRY = "--dry-run" in sys.argv

conn = sqlite3.connect(DB, timeout=120)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

merged = separated = skipped = 0
for row in csv.DictReader(open(path, encoding="utf-8-sig")):
    decision = (row["decision"] or "").strip().upper()
    if decision not in ("MERGE", "SEPARATE", ""):
        print(f"  ?? unknown decision '{row['decision']}' for {row['county_donor']} — skipped")
        skipped += 1
        continue
    if decision != "MERGE":
        cur.execute("UPDATE review_queue SET resolved='travis-separate' WHERE rowid=?", (row["qid"],))
        separated += 1
        continue

    # find the county donor's tcv- identity via their campaign_finance rows
    tcv = cur.execute("""
        SELECT DISTINCT donor_id FROM campaign_finance
        WHERE transaction_id LIKE 'TRAVIS-%' AND donor = ? AND donor_id LIKE 'tcv-%'
    """, (row["county_donor"],)).fetchall()
    target = cur.execute("SELECT donor_id FROM donor_identities WHERE canonical_name = ? ORDER BY total_donated DESC LIMIT 1",
                         (row["existing_identity"],)).fetchone()
    if not tcv or not target:
        print(f"  !! cannot merge {row['county_donor']} -> {row['existing_identity']}: "
              f"{'no tcv identity' if not tcv else 'target identity not found'}")
        skipped += 1
        continue
    tgt = target["donor_id"]
    for t in tcv:
        cur.execute("UPDATE campaign_finance SET donor_id=?, match_confidence='travis-user-merge' WHERE donor_id=?", (tgt, t["donor_id"]))
        cur.execute("UPDATE campaign_finance SET donor_id_2=? WHERE donor_id_2=?", (tgt, t["donor_id"]))
        cur.execute("DELETE FROM donor_identities WHERE donor_id=?", (t["donor_id"],))
    # recompute target aggregates
    agg = cur.execute("""SELECT SUM(CAST(contribution_amount AS REAL)), COUNT(*),
                         MIN(contribution_date), MAX(contribution_date)
                         FROM campaign_finance WHERE donor_id=? OR donor_id_2=?""", (tgt, tgt)).fetchone()
    camps = sorted({r[0] for r in cur.execute(
        "SELECT DISTINCT recipient FROM campaign_finance WHERE donor_id=? OR donor_id_2=?", (tgt, tgt))})
    cur.execute("""UPDATE donor_identities SET total_donated=?, record_count=?, campaign_count=?,
                   campaigns=?, first_seen=?, last_seen=? WHERE donor_id=?""",
                (agg[0] or 0, agg[1], len(camps), "|".join(camps), agg[2], agg[3], tgt))
    cur.execute("UPDATE review_queue SET resolved='travis-merged' WHERE rowid=?", (row["qid"],))
    merged += 1
    print(f"  merged {row['county_donor']} -> {row['existing_identity']}")

print(f"\nmerged={merged} separate={separated} skipped={skipped}")
if DRY:
    conn.rollback(); print("DRY RUN — rolled back")
else:
    conn.commit()
