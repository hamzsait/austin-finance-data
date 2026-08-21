"""Industry backfill for David Weinberg's donors ahead of the D5 race page
(D5_EXPANSION_PLAN.md SSC/SSE.4 — 13 of 116 donors industry-unresolved; his
filings begin Oct 2025, after the global enrichment passes).

Same shape as d3_research/_backfill_shah_employers.py: donor-level manual
classifications from unambiguous employer/occupation strings, scoped to
Weinberg's donors, `manual` confidence. Employers here are one-donor strings
(mostly out-of-state), so no global employer_identities classification pass
is warranted — donor-level only.

Left unresolved on purpose (nothing usable): Ashley (no emp/occ), Waitzman
(N/A), Distenfeld (occ 'Dog trainer', no employer), Blinn ('Minuteman
Weather' — sector ambiguous).

Idempotent; must be re-run against the canonical DB after the branch merges.

Usage: python d5_research/_backfill_weinberg_employers.py [--dry-run]
"""
import argparse, sqlite3, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# (canonical_name, industry, display) — employer/occupation strings verified
# unambiguous 2026-07-19:
#   Rosenthal = NY State Assemblymember (employer 'NY State', occ Assemblymember)
#   NeighborWorks America / Prevent Cancer Foundation / Griffiss Institute =
#     nonprofits; CARE + 'Senior Policy Advocate' = advocacy
#   Thermo Fisher Scientific = life sciences; Function Health = health testing
#   STChealth = immunization-records software
CALLS = {
    "Rosenthal, Linda":  ("Government",           "NY State Assembly"),
    "Meegan, Erin":      ("Nonprofit / Advocacy", "CARE (policy advocacy)"),
    "Watts, Kathryn":    ("Nonprofit / Advocacy", "NeighborWorks America"),
    "Niland, Thomas":    ("Government",           "City and County of Denver"),
    "Mulligan, Seth":    ("Nonprofit / Advocacy", "Griffiss Institute"),
    "Cileli, Alen":      ("Healthcare",           "Thermo Fisher Scientific"),
    "Cuvar, Kelly":      ("Nonprofit / Advocacy", "Prevent Cancer Foundation"),
    "Unangst, Spencer":  ("Technology",           "STChealth"),
    "Riotto, Andrew":    ("Healthcare",           "Function Health"),
}

weinberg_ids = {r[0] for r in cur.execute("""
    SELECT DISTINCT di.donor_id
    FROM campaign_finance cf JOIN donor_identities di ON di.donor_id = cf.donor_id
    WHERE cf.recipient = 'Weinberg, David M.' AND di.resolved_industry IS NULL""")}
print(f"Weinberg donors still unresolved: {len(weinberg_ids)}")

updates = []
for name, (industry, display) in CALLS.items():
    row = cur.execute(
        "SELECT donor_id FROM donor_identities WHERE canonical_name=? AND resolved_industry IS NULL",
        (name,)).fetchone()
    if row and row[0] in weinberg_ids:
        updates.append((industry, display, "manual", row[0]))
        print(f"  {name:22} -> {industry:22} [{display}]")

if not args.dry_run:
    cur.executemany("""
        UPDATE donor_identities
        SET resolved_industry=?, resolved_employer_display=?, resolved_confidence=?
        WHERE donor_id=? AND resolved_industry IS NULL""", updates)
    conn.commit()
else:
    print("DRY RUN — no writes")

n, tot = cur.execute("""
    SELECT COUNT(DISTINCT CASE WHEN di.resolved_industry IS NOT NULL THEN di.donor_id END),
           COUNT(DISTINCT di.donor_id)
    FROM campaign_finance cf JOIN donor_identities di ON di.donor_id = cf.donor_id
    WHERE cf.recipient='Weinberg, David M.'""").fetchone()
print(f"Weinberg donors resolved after run: {n}/{tot}")
conn.close()
