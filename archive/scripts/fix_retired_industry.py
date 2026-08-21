"""
Classify retired donors using occupation text signals.

Principle: even if a person lists "Retired" or "Not Employed" as employer,
their occupation strings often reveal the industry they came from — and their
financial interests remain tied to that background.

Approach:
  For each canonical_name, collect ALL occupation strings from ALL their
  donations. If any string signals a specific industry (via "Retired [X]"
  pattern), apply that industry to all unresolved donor_ids for that name.
"""
import sqlite3, sys, io, re
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("austin_finance.db", timeout=120)
conn.execute("PRAGMA journal_mode=WAL")
cur = conn.cursor()

# ── Industry keyword rules (order matters — first match wins) ─────────────────
RULES = [
    ('Technology',            ['computer','semiconductor','software','it exec','tech exec',
                                'hardware','digital','information technology','data science',
                                'it manager','it director']),
    ('Engineering',           ['engineer']),
    ('Healthcare',            ['medical','pharma','health','hospital','physician','doctor',
                                'nurse','biotech','clinical']),
    ('Finance',               ['financ','bank','invest','capital','insurance','portfolio',
                                'securities','brokerage']),
    ('Real Estate',           ['real estate','property','developer','construction','architect',
                                'land develop']),
    ('Legal',                 ['law firm','legal','attorney','paralegal','general counsel',
                                'legal counsel']),
    ('Energy / Environment',  ['oil','energy','gas','petroleum','utilities']),
    ('Education',             ['education','academic','university','school','professor',
                                'teacher','faculty']),
    ('Government',            ['government','civil serv','public serv','military','federal',
                                'state employ']),
    ('Consulting / PR',       ['consult','marketing','public relations']),
]

def classify_from_occupation(occ_text):
    """Return industry if occ_text has a retirement + industry signal."""
    t = occ_text.lower()
    # Must have a retirement marker
    if not any(marker in t for marker in ['retired','ret.','emeritus']):
        return None
    for industry, keywords in RULES:
        if any(kw in t for kw in keywords):
            return industry
    return None

# ── 1. Load all unresolved donor_ids with their canonical_name ────────────────
cur.execute("""
    SELECT donor_id, canonical_name
    FROM donor_identities
    WHERE resolved_industry IS NULL
""")
unresolved = {row[0]: row[1] for row in cur.fetchall()}
print(f"Unresolved donor_ids: {len(unresolved):,}")

# ── 2. Load all occupation strings per canonical_name (from all donations) ────
cur.execute("""
    SELECT di.canonical_name, cf.donor_reported_occupation
    FROM campaign_finance cf
    JOIN donor_identities di ON cf.donor_id = di.donor_id
    WHERE cf.donor_reported_occupation IS NOT NULL
      AND cf.donor_reported_occupation != ''
""")
name_occs = defaultdict(set)
for name, occ in cur.fetchall():
    name_occs[name].add(occ.strip())

# ── 3. Determine best industry per canonical_name ─────────────────────────────
name_to_industry = {}
name_to_best_occ = {}
for name, occs in name_occs.items():
    for occ in sorted(occs, key=len, reverse=True):  # longest/most-descriptive first
        ind = classify_from_occupation(occ)
        if ind:
            # Only assign if the name has unresolved donor_ids
            donor_ids_for_name = [did for did, n in unresolved.items() if n == name]
            if donor_ids_for_name:
                name_to_industry[name] = ind
                name_to_best_occ[name] = occ
                break

print(f"Names classifiable from retirement occupation: {len(name_to_industry)}")
print()

# ── 4. Show what we'll fix ─────────────────────────────────────────────────────
# Load totals per canonical_name for reporting
cur.execute("""
    SELECT di.canonical_name,
           SUM(CAST(COALESCE(cf.balanced_amount,cf.contribution_amount) AS REAL)) as total,
           COUNT(DISTINCT di.donor_id) as n_ids
    FROM donor_identities di
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE di.resolved_industry IS NULL
      AND COALESCE(cf.balanced_amount, cf.contribution_amount) > 0
    GROUP BY di.canonical_name
""")
name_stats = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

from collections import Counter
by_ind = defaultdict(list)
for name, ind in name_to_industry.items():
    total, n_ids = name_stats.get(name, (0, 0))
    by_ind[ind].append((name, ind, total, n_ids, name_to_best_occ[name]))

grand_total_reclassified = 0
for ind in sorted(by_ind):
    entries = sorted(by_ind[ind], key=lambda x: -x[2])
    subtotal = sum(e[2] for e in entries)
    grand_total_reclassified += subtotal
    print(f"{ind}: {len(entries)} donors, ${subtotal:,.0f}")
    for name, ind2, total, n_ids, occ in entries:
        print(f"    ${total:>7,.0f}  {n_ids:>2} ids  {name:<35}  \"{occ[:60]}\"")
    print()

print(f"Total amount reclassified: ${grand_total_reclassified:,.0f}\n")

# ── 5. Apply ──────────────────────────────────────────────────────────────────
fixed = 0
for name, industry in name_to_industry.items():
    donor_ids = [did for did, n in unresolved.items() if n == name]
    for did in donor_ids:
        cur.execute("""
            UPDATE donor_identities
            SET resolved_industry = ?, resolved_confidence = 'occupation-retired'
            WHERE donor_id = ?
        """, (industry, did))
        fixed += cur.rowcount

conn.commit()
print(f"Updated {fixed} donor_id rows")

# ── 6. Rebuild qadri_all_donations.json ───────────────────────────────────────
import json
print("\nRebuilding ALL_DONATIONS JSON...")
cur.execute("""
    SELECT
        di.canonical_name,
        cf.contribution_date,
        ROUND(COALESCE(cf.balanced_amount, cf.contribution_amount), 2),
        COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, ""),
        COALESCE(di.resolved_industry, ei.industry, "Unknown"),
        TRIM(COALESCE(cf.city_state_zip, ""))
    FROM campaign_finance cf
    LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
    WHERE cf.recipient LIKE "%Qadri%" AND cf.contribution_year >= 2022
      AND COALESCE(cf.balanced_amount, cf.contribution_amount) > 0
    ORDER BY cf.contribution_date DESC
""")
rows = cur.fetchall()
with open("qadri_all_donations.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(rows, separators=(',', ':'), ensure_ascii=False))
print(f"  Written {len(rows):,} records")

# ── 7. New breakdown ──────────────────────────────────────────────────────────
print("\nQadri breakdown after retirement fix:")
cur.execute("""
    SELECT
        COALESCE(di.resolved_industry, ei.industry, "Unknown") as industry,
        ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total,
        COUNT(DISTINCT cf.donor_id) as donors
    FROM campaign_finance cf
    LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
    WHERE cf.recipient LIKE "%Qadri%" AND cf.contribution_year >= 2022
      AND COALESCE(cf.balanced_amount, cf.contribution_amount) > 0
    GROUP BY 1 ORDER BY 2 DESC
""")
breakdown = cur.fetchall()
grand = sum(r[1] for r in breakdown)
NOISE = {"Not Employed","Self-Employed","Student","Unknown","Unknown / Unclassified"}
emp_total = sum(r[1] for r in breakdown if r[0] not in NOISE)
print(f"  Grand total: ${grand:,.0f}  Employer-affiliated: {emp_total/grand*100:.1f}%")
print()
for r in breakdown:
    print(f"  (\"{r[0]}\", {int(r[1])}, {r[2]}),  # {r[1]/grand*100:.1f}%")

conn.close()
print("\nDone.")
