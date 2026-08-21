"""Industry backfill for Katie Kam's and Dave Thadani's donors ahead of the D9
race page (D9_EXPANSION_PLAN.md — both filed first in 2026, after the global
enrichment passes; 11 + 7 donors unresolved).

Same shape as the D3/D5 backfills: donor-level manual classifications from
unambiguous employer strings, scoped to the two candidates' donors, `manual`
confidence. Left unresolved (generic/unidentifiable): Werner ('Zanzibar
Enterprises' / 'Alchemist'), Rindfuss (Consultant), Vishwanathan
(Recruitment), Levesque (Program coordinator), Mohon ('ann martin').

Idempotent; re-run against the canonical DB after the branch merges.

Usage: python d9_research/_backfill_kam_thadani_employers.py [--dry-run]
"""
import argparse, sqlite3, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# (canonical_name, industry, display) — employer strings verified 2026-07-19:
#   Battlespace Simulations = military simulation software; MealSuite =
#   food-service software; Babson Diagnostics = blood-testing startup;
#   Tenderheart Health Outcomes = home-health supplies; Marsh = insurance
#   brokerage; Pedernales Cellars = Hill Country winery; Convoy = freight;
#   Lee Engineering = traffic engineering firm
CALLS = {
    # Kam donors
    "Kam, Clinton":       ("Technology",           "Battlespace Simulations"),
    "Montoya, Claudio":   ("Self-Employed",        "Self-Employed"),
    "Kuhlken, David":     ("Hospitality / Events", "Pedernales Cellars"),
    "Childers, Laura":    ("Finance",              "Marsh (insurance)"),
    "Lach, Jon":          ("Technology",           "MealSuite"),
    "Lehr, Robert":       ("Engineering",          "Lee Engineering"),
    "Vandersand, David":  ("Healthcare",           "Babson Diagnostics"),
    # Thadani donors
    "Hernandez, Joel":    ("Retail",               "Sam's Club"),
    "Stewart , Jacob":    ("Transportation",       "Convoy"),
    "Adapalli, Arjun":    ("Healthcare",           "Tenderheart Health Outcomes"),
    "Munguia, Eamon":     ("Retail",               "Yard Sign Plus"),
    "Wimble, Peyton":     ("Hospitality / Events", "Olive Garden"),
    "Ahsan , Syed":       ("Government",           "Fort Bend County HHS"),
}

pool_ids = {r[0] for r in cur.execute("""
    SELECT DISTINCT di.donor_id
    FROM campaign_finance cf JOIN donor_identities di ON di.donor_id = cf.donor_id
    WHERE cf.recipient IN ('Kam, Katherine', 'Thadani, Dave')
      AND di.resolved_industry IS NULL""")}
print(f"Kam/Thadani donors unresolved: {len(pool_ids)}")

updates = []
for name, (industry, display) in CALLS.items():
    row = cur.execute(
        "SELECT donor_id FROM donor_identities WHERE canonical_name=? AND resolved_industry IS NULL",
        (name,)).fetchone()
    if row and row[0] in pool_ids:
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

for rec in ("Kam, Katherine", "Thadani, Dave"):
    n, tot = cur.execute("""
        SELECT COUNT(DISTINCT CASE WHEN di.resolved_industry IS NOT NULL THEN di.donor_id END),
               COUNT(DISTINCT di.donor_id)
        FROM campaign_finance cf JOIN donor_identities di ON di.donor_id = cf.donor_id
        WHERE cf.recipient=?""", (rec,)).fetchone()
    print(f"{rec}: {n}/{tot} resolved")
conn.close()
