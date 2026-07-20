"""Industry backfill for Selena Xie's donors ahead of the D8 race page
(D8_EXPANSION_PLAN.md — her filings begin June 2025 and 168 of 660 donors are
industry-unresolved, the weakest coverage of any 2026 candidate so far).

Unlike the Shah/Weinberg backfills (hand-researched employer lists), Xie's
unresolved donors overwhelmingly put a JOB TITLE in the employer field
("Paramedic", "RN", "Professor", "Retired"...), so this is a rules pass in the
style of fix_unclassified_employers.py's occupation inference, scoped to her
donors. Plain "Retired" with no other signal -> Not Employed (site convention,
see fix_retired_industry.py). Generic titles (sales, manager, scientist,
designer...) are left unresolved rather than guessed.

Idempotent; re-run against the canonical DB after the branch merges.

Usage: python d8_research/_backfill_xie_employers.py [--dry-run]
"""
import argparse, re, sqlite3, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

conn = sqlite3.connect("austin_finance.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# First match wins; matched against BOTH the employer string and the
# occupation string (title-in-employer-field is the dominant pattern here).
RULES = [
    (r'\b(paramedic|emt|medic|ems)\b',                        "Healthcare"),
    (r'\b(rn|nurse|np|crna|nursing)\b',                       "Healthcare"),
    (r'\b(physician|doctor|md|dds|dmd|pa-c|therapist|counselor|pharmacist)\b', "Healthcare"),
    (r'\butsw\b|\but southwestern\b|\bmedical (center|school)\b', "Healthcare"),
    (r'\b(professor|teacher|educator|lecturer|faculty|instructor)\b', "Education"),
    (r'\b(lawyer|attorney|paralegal|legal)\b',                "Legal"),
    (r'\b(firefighter|fire dept|police|city of austin|atcems|county|federal|govt|government)\b', "Government"),
    (r'\bwhataburger\b|\bmml hospitality\b|\b(restaurant|bartender|chef|barista|winemaker|brewer)\b', "Hospitality / Events"),
    (r'\b(vintage clothing|retail|shop owner|boutique)\b',    "Retail"),
    (r'\b(software|engineer at|tech|developer|programmer)\b', "Technology"),
    (r'\bstudent\b',                                          "Student"),
]
COMPILED = [(re.compile(p, re.I), ind) for p, ind in RULES]

SELF = re.compile(r'^\s*(self[- ]?employed|self|owner|business owner|sole proprietor)\s*$', re.I)
RETIRED = re.compile(r'^\s*retired\s*$', re.I)

rows = cur.execute("""
    SELECT di.donor_id, di.canonical_name,
           GROUP_CONCAT(DISTINCT cf.donor_reported_employer) emp,
           GROUP_CONCAT(DISTINCT cf.donor_reported_occupation) occ
    FROM campaign_finance cf JOIN donor_identities di ON di.donor_id = cf.donor_id
    WHERE cf.recipient = 'Xie, Selena' AND di.resolved_industry IS NULL
      AND CAST(REPLACE(REPLACE(cf.contribution_amount,'$',''),',','') AS REAL) > 0
    GROUP BY di.donor_id""").fetchall()
print(f"Xie donors unresolved: {len(rows)}")

updates, skipped = [], 0
for r in rows:
    emp, occ = (r["emp"] or "").strip(), (r["occ"] or "").strip()
    text = f"{emp} {occ}"
    industry = display = None
    for pat, ind in COMPILED:
        if pat.search(text):
            industry, display = ind, (emp if emp.lower() not in ("", "na", "n/a") else occ)
            break
    if industry is None and (SELF.match(emp) or SELF.match(occ)):
        industry, display = "Self-Employed", "Self-Employed"
    if industry is None and RETIRED.match(emp) and (not occ or RETIRED.match(occ) or occ.lower() in ("na", "n/a")):
        industry, display = "Not Employed", "Retired"
    if industry:
        updates.append((industry, display[:80], "manual", r["donor_id"]))
    else:
        skipped += 1

from collections import Counter
print(Counter(u[0] for u in updates))
print(f"classify {len(updates)}, leave unresolved {skipped}")

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
    WHERE cf.recipient='Xie, Selena'""").fetchone()
print(f"Xie donors resolved after run: {n}/{tot}")
conn.close()
