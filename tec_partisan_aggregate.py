"""
Aggregate Texas Ethics Commission (TEC) contributions per Austin donor into
partisan dem/rep/other totals, stored as new columns on donor_identities.

Classification of the 10 tracked TEC committees:
  Rep:   Texans for Lawsuit Reform, Associated Republicans of Texas,
         Defend Texas Liberty, Empower Texans
  Dem:   Texas Trial Lawyers Association PAC
  Other: TXOGA Good Government Committee, Texas REALTORS PAC (TREPAC),
         Texas Apartment Association PAC, GHBA HOME-PAC,
         Austin Board of Realtors PAC
"""
import sqlite3

DB = "austin_finance.db"

TEC_COMMITTEE_LEAN = {
    "00028135": "Rep",    # Texans for Lawsuit Reform PAC
    "00015555": "Rep",    # Associated Republicans of Texas Campaign Fund
    "00089881": "Rep",    # Defend Texas Liberty
    "00061927": "Rep",    # Empower Texans PAC (terminated)
    "00015666": "Dem",    # Texas Trial Lawyers Association PAC
    "00070864": "Other",  # Texas Oil and Gas Association GGC (industry)
    "00015487": "Other",  # Texas REALTORS PAC (bipartisan)
    "00017303": "Other",  # Texas Apartment Association PAC
    "00015700": "Other",  # GHBA HOME-PAC
    "00035370": "Other",  # Austin Board of Realtors PAC
}

c = sqlite3.connect(DB, timeout=60)
c.execute("PRAGMA journal_mode=WAL")
cur = c.cursor()

# Add TEC aggregate columns if they don't exist
cur.execute("PRAGMA table_info(donor_identities)")
existing_cols = {row[1] for row in cur.fetchall()}
for col, col_sql in [
    ("tec_total_dem", "REAL DEFAULT 0"),
    ("tec_total_rep", "REAL DEFAULT 0"),
    ("tec_total_other", "REAL DEFAULT 0"),
    ("tec_total_donations", "INTEGER DEFAULT 0"),
    ("tec_matched", "INTEGER DEFAULT 0"),
]:
    if col not in existing_cols:
        cur.execute(f"ALTER TABLE donor_identities ADD COLUMN {col} {col_sql}")
        print(f"Added column: {col}")

# Reset
cur.execute("""
    UPDATE donor_identities
    SET tec_total_dem=0, tec_total_rep=0, tec_total_other=0,
        tec_total_donations=0, tec_matched=0
""")
c.commit()

# For each donor with TEC matches, aggregate by committee lean
cur.execute("""
    SELECT austin_donor_id, filer_ident, SUM(CAST(contribution_amount AS REAL)) AS total,
           COUNT(*) AS n
    FROM texas_contributions_raw
    WHERE austin_donor_id IS NOT NULL AND austin_donor_id != ''
    GROUP BY austin_donor_id, filer_ident
""")
rows = cur.fetchall()
print(f"TEC match rows to aggregate: {len(rows):,}")

per_donor = {}
unclassified = set()
for donor_id, filer_ident, total, n in rows:
    lean = TEC_COMMITTEE_LEAN.get(filer_ident)
    if not lean:
        unclassified.add(filer_ident)
        continue
    d = per_donor.setdefault(donor_id, {"dem": 0.0, "rep": 0.0, "other": 0.0, "n": 0})
    if lean == "Dem":
        d["dem"] += total or 0
    elif lean == "Rep":
        d["rep"] += total or 0
    else:
        d["other"] += total or 0
    d["n"] += n or 0

if unclassified:
    print(f"WARNING: unclassified committees: {unclassified}")

for donor_id, t in per_donor.items():
    cur.execute("""
        UPDATE donor_identities
        SET tec_total_dem=?, tec_total_rep=?, tec_total_other=?,
            tec_total_donations=?, tec_matched=1
        WHERE donor_id=?
    """, (round(t["dem"], 2), round(t["rep"], 2), round(t["other"], 2), t["n"], donor_id))
c.commit()

print(f"Donors with TEC aggregates written: {len(per_donor):,}")
cur.execute("SELECT COUNT(*) FROM donor_identities WHERE tec_matched=1")
print(f"Total donor_identities with tec_matched=1: {cur.fetchone()[0]:,}")
cur.execute("""
    SELECT SUM(tec_total_dem), SUM(tec_total_rep), SUM(tec_total_other)
    FROM donor_identities WHERE tec_matched=1
""")
dem, rep, other = cur.fetchone()
print(f"Aggregates: D=${dem:,.0f}  R=${rep:,.0f}  Other=${other:,.0f}")
c.close()
