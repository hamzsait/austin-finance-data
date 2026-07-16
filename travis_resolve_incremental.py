"""Incremental industry resolution for donors still unresolved — same logic as
resolve_donor_identities.py (employer-dominant first, then OCC_RULES on
occupation) but scoped to donors with resolved_industry IS NULL, so it never
resets existing resolutions (the stock script does a full reset).

Extracts OCC_RULES/infer_from_occupation from resolve_donor_identities.py by
source parsing (importing it would execute its full-reset top-level code).
"""
import re, sqlite3
from collections import defaultdict

# ── lift OCC_RULES + helper from the canonical script without executing it ──
src = open("resolve_donor_identities.py", encoding="utf-8").read()
block = re.search(r"OCC_RULES = \[.*?\n\]", src, re.S).group(0)
ns = {"re": re}
exec(block, ns)
OCC_RULES = [(re.compile(p, re.I), ind) for p, ind in ns["OCC_RULES"]]

NOT_EMPLOYED = re.compile(r"^\s*(not\s*employed|retired|retd|homemaker|housewife|unemployed|none)\s*\.?\s*$", re.I)
SELF_EMPLOYED = re.compile(r"^\s*(self[\s-]*employed|self)\s*\.?\s*$", re.I)

def infer_from_occupation(occ):
    if not occ:
        return None
    if NOT_EMPLOYED.match(occ):
        return "Not Employed"
    for rx, ind in OCC_RULES:
        if rx.search(occ):
            return ind
    if SELF_EMPLOYED.match(occ):
        return "Self-Employed"
    return None

conn = sqlite3.connect("austin_finance.db", timeout=120)
cur = conn.cursor()

# unresolved donors + their transactions (employer industry via employer_id)
cur.execute("""
    SELECT di.donor_id, cf.donor_reported_employer, ei.industry, ei.canonical_name,
           cf.donor_reported_occupation, CAST(cf.contribution_amount AS REAL)
    FROM campaign_finance cf
    JOIN donor_identities di ON di.donor_id = cf.donor_id
    LEFT JOIN employer_identities ei ON ei.employer_id = cf.employer_id
    WHERE di.resolved_industry IS NULL
""")
by_donor = defaultdict(list)
for row in cur.fetchall():
    by_donor[row[0]].append(row[1:])

updates = []
emp_hits = occ_hits = 0
for donor_id, txns in by_donor.items():
    # Step 1: dominant classified employer by dollars
    emp_tot = defaultdict(float)
    emp_name = {}
    for raw_emp, industry, emp_can, occ, amt in txns:
        if industry and industry not in ("Not Employed",):
            emp_tot[industry] += amt or 0
            emp_name.setdefault(industry, emp_can)
    if emp_tot:
        ind = max(emp_tot, key=emp_tot.get)
        updates.append((ind, emp_name[ind], "employer-incr", donor_id))
        emp_hits += 1
        continue
    # Step 2: occupation rules (majority of dollars)
    occ_tot = defaultdict(float)
    for raw_emp, industry, emp_can, occ, amt in txns:
        ind = infer_from_occupation(occ or "")
        if ind:
            occ_tot[ind] += amt or 0
    if occ_tot:
        ind = max(occ_tot, key=occ_tot.get)
        updates.append((ind, None, "occupation-incr", donor_id))
        occ_hits += 1

cur.executemany("""UPDATE donor_identities SET resolved_industry=?,
    resolved_employer_display=COALESCE(resolved_employer_display, ?),
    resolved_confidence=? WHERE donor_id=? AND resolved_industry IS NULL""", updates)
conn.commit()

n = cur.execute("""SELECT COUNT(DISTINCT di.donor_id) FROM campaign_finance cf
    JOIN donor_identities di ON di.donor_id=cf.donor_id
    WHERE cf.transaction_id LIKE 'TRAVIS-%' AND di.resolved_industry IS NULL""").fetchone()[0]
print(f"resolved: {emp_hits} via employer, {occ_hits} via occupation ({len(updates)} total)")
print(f"county donors still unknown: {n}")
