"""
Find and fix all reversed canonical names (Firstname, Lastname stored instead of Lastname, Firstname).
Uses in-memory approach — no per-pair DB queries.
"""
import sqlite3, sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("austin_finance.db", timeout=120)
conn.execute("PRAGMA journal_mode=WAL")
cur = conn.cursor()

# Load all names + their donor_id count into memory
print("Loading all canonical names...", flush=True)
cur.execute("""
    SELECT di.canonical_name, COUNT(DISTINCT di.donor_id) as id_count
    FROM donor_identities di
    WHERE di.canonical_name LIKE '%, %'
    GROUP BY di.canonical_name
""")
name_counts = {}  # name -> donor_id count
for row in cur.fetchall():
    if row[0]:
        name_counts[row[0]] = row[1]
print(f"  {len(name_counts):,} distinct names", flush=True)

# Find bidirectional pairs entirely in Python
name_set = set(name_counts.keys())
pairs = []   # (wrong, correct)
seen = set()
for name in name_set:
    if name in seen:
        continue
    parts = name.split(', ', 1)
    if len(parts) != 2:
        continue
    a, b = parts[0].strip(), parts[1].strip()
    if not a or not b:
        continue
    flipped = f"{b}, {a}"
    if flipped in name_set and flipped not in seen:
        # The one with MORE donor_ids is likely the canonical (correct) version
        n1 = name_counts[name]
        n2 = name_counts[flipped]
        if n1 <= n2:
            pairs.append((name, flipped))   # name is wrong
        else:
            pairs.append((flipped, name))   # flipped is wrong
        seen.add(name)
        seen.add(flipped)

print(f"  Found {len(pairs)} reversal pairs", flush=True)
for wrong, correct in sorted(pairs, key=lambda x: x[1])[:60]:
    print(f"    RENAME [{wrong}] -> [{correct}]")

# Apply renames
print(f"\nApplying renames...", flush=True)
fixed = 0
for wrong, correct in pairs:
    cur.execute(
        "UPDATE donor_identities SET canonical_name=? WHERE canonical_name=?",
        (correct, wrong)
    )
    fixed += cur.rowcount
conn.commit()
print(f"  Renamed {fixed} donor_id entries", flush=True)

# Cross-identity resolution for affected names
print("Re-running cross-identity for affected names...", flush=True)
affected = {correct for _, correct in pairs}
resolved = 0
for name in affected:
    cur.execute("""
        SELECT donor_id FROM donor_identities
        WHERE canonical_name=? AND resolved_industry IS NULL
    """, (name,))
    unresolved = [r[0] for r in cur.fetchall()]
    if not unresolved:
        continue
    cur.execute("""
        SELECT di.resolved_industry, di.resolved_employer_display, di.resolved_confidence
        FROM donor_identities di
        WHERE di.canonical_name=?
          AND di.resolved_industry IS NOT NULL
          AND di.resolved_industry NOT IN ('Not Employed','Self-Employed','Student')
        ORDER BY (di.resolved_confidence='employer') DESC
        LIMIT 1
    """, (name,))
    sibling = cur.fetchone()
    if not sibling:
        continue
    for did in unresolved:
        cur.execute("""
            UPDATE donor_identities
            SET resolved_industry=?, resolved_employer_display=?, resolved_confidence=?
            WHERE donor_id=?
        """, (sibling[0], sibling[1], f"cross-identity ({sibling[2]})", did))
        resolved += 1
conn.commit()
print(f"  Cross-resolved {resolved} identities", flush=True)

# Rebuild JSON (already filtered correction=X via balanced_amount=0)
print("Rebuilding qadri_all_donations.json...", flush=True)
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
donations_json = json.dumps(rows, separators=(',', ':'), ensure_ascii=False)
with open("qadri_all_donations.json", "w", encoding="utf-8") as f:
    f.write(donations_json)
print(f"  Written {len(rows):,} records, {len(donations_json.encode())//1024} KB", flush=True)

# Final breakdown
print("\nFinal Qadri breakdown:", flush=True)
cur.execute("""
    SELECT COALESCE(di.resolved_industry, ei.industry, "Unknown") as ind,
           ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)),0) as total,
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
OTHER = {"Media","Retail","Architecture","Entertainment","Transportation","Labor","Venture Capital","Retail / Media / Other"}
other_total = sum(r[1] for r in breakdown if r[0] in OTHER)
other_donors = sum(r[2] for r in breakdown if r[0] in OTHER)
print(f"  Total: ${grand:,.0f}  Employer-affiliated: {emp_total/grand*100:.1f}%")
for r in breakdown:
    print(f"  {r[0]:<35} ${r[1]:>8,.0f}  {r[1]/grand*100:>5.1f}%  {r[2]:>4} donors")
print(f"\n  Retail/Media/Other combined: ${other_total:,.0f}, {other_donors} donors")
conn.close()
print("\nDone.", flush=True)
