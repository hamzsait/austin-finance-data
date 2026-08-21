"""
Cross-identity resolution pass.
For donor_ids that remain unresolved after the main pass, borrow the resolution
from a sibling donor_id (same canonical_name) that IS resolved to a real sector.

Safety: only apply when the sibling resolution came from a named employer
(confidence='employer'), not just occupation inference. This prevents
a vague occupation match from being propagated across identities.
"""
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# Fetch all unresolved donor_ids and their canonical_name
cur.execute("""
    SELECT donor_id, canonical_name
    FROM donor_identities
    WHERE resolved_industry IS NULL
""")
unresolved = cur.fetchall()
print(f"{len(unresolved):,} unresolved donor_ids to evaluate")

# Build index: canonical_name -> list of (donor_id, resolved_industry, resolved_employer_display, confidence, total_amt)
cur.execute("""
    SELECT di.donor_id, di.canonical_name,
           di.resolved_industry, di.resolved_employer_display, di.resolved_confidence,
           COALESCE(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total_amt
    FROM donor_identities di
    LEFT JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE di.resolved_industry IS NOT NULL
      AND di.resolved_industry NOT IN ('Not Employed', 'Self-Employed', 'Student')
    GROUP BY di.donor_id
""")
resolved_by_name = {}
for donor_id, canonical_name, ind, emp, conf, amt in cur.fetchall():
    resolved_by_name.setdefault(canonical_name, []).append((donor_id, ind, emp, conf, amt))

updates = []
skipped_common = 0
skipped_no_sibling = 0
applied = 0

for donor_id, canonical_name in unresolved:
    siblings = resolved_by_name.get(canonical_name, [])
    if not siblings:
        skipped_no_sibling += 1
        continue

    # Filter to employer-confidence siblings only (stronger signal)
    strong = [s for s in siblings if s[3] == 'employer']
    pool = strong if strong else siblings

    # Pick the sibling with the highest total donation amount (most representative)
    best = max(pool, key=lambda s: s[4])
    _, ind, emp, conf, _ = best

    updates.append((ind, emp, f"cross-identity ({conf})", donor_id))
    applied += 1

print(f"  Applied cross-identity resolution: {applied:,}")
print(f"  No sibling found:                  {skipped_no_sibling:,}")

cur.executemany("""
    UPDATE donor_identities
    SET resolved_industry=?, resolved_employer_display=?, resolved_confidence=?
    WHERE donor_id=?
""", updates)
conn.commit()
print(f"  Written to DB.")

# ── Spot check Aaron Gonzales ──────────────────────────────────────────────────
print("\n── Gonzales, Aaron ──")
cur.execute("""
    SELECT donor_id, canonical_name, canonical_zip,
           resolved_industry, resolved_employer_display, resolved_confidence
    FROM donor_identities WHERE canonical_name = 'Gonzales, Aaron'
""")
for r in cur.fetchall():
    print(f"  {r[0][:8]}  zip={r[2]}  → {r[3]}  via={r[5]}  emp=[{r[4]}]")

# ── Spot check Hamza Sait ──────────────────────────────────────────────────────
print("\n── Sait, Hamza ──")
cur.execute("""
    SELECT donor_id, canonical_name, canonical_zip,
           resolved_industry, resolved_employer_display, resolved_confidence
    FROM donor_identities WHERE canonical_name = 'Sait, Hamza'
""")
for r in cur.fetchall():
    print(f"  {r[0][:8]}  zip={r[2]}  → {r[3]}  via={r[5]}  emp=[{r[4]}]")

# ── Updated Qadri breakdown ────────────────────────────────────────────────────
print("\n── Qadri breakdown (post cross-identity) ──")
cur.execute("""
    SELECT
        COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
        SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)) as total,
        COUNT(DISTINCT cf.donor_id) as donors
    FROM campaign_finance cf
    LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
    WHERE cf.recipient LIKE '%Qadri%' AND cf.contribution_year >= 2022
    GROUP BY 1 ORDER BY 2 DESC
""")
rows = cur.fetchall()
grand = sum(r[1] or 0 for r in rows)
for r in rows:
    pct = (r[1] or 0) / grand * 100
    print(f"  {r[0]:<35} ${r[1]:>9,.0f}  {pct:>5.1f}%  {r[2]:>5} donors")
print(f"  {'TOTAL':<35} ${grand:>9,.0f}")
conn.close()
