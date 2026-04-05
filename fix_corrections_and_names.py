"""
Two critical fixes:
1. correction='X' rows are superseded by amendments — zero them out so they
   don't inflate totals or appear in donor drawers.
2. Reversed canonical names (Firstname, Lastname instead of Lastname, Firstname)
   — detect via bidirectional pairs and common first-name heuristics, fix,
   then re-run cross-identity resolution for affected donor_ids.
"""
import sqlite3, sys, io, json, re
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("austin_finance.db", timeout=120)
conn.execute("PRAGMA journal_mode=WAL")
cur = conn.cursor()

# ── 1. Zero out correction=X balanced_amount ──────────────────────────────────
cur.execute("""
    UPDATE campaign_finance
    SET balanced_amount = 0.0
    WHERE (correction = 'X' OR correction = 'x')
      AND (balanced_amount IS NULL OR balanced_amount != 0)
""")
zeroed = cur.rowcount
print(f"Zeroed correction=X rows: {zeroed:,}")
conn.commit()

# ── 2. Find ALL reversed name pairs ──────────────────────────────────────────
# A name is "reversed" if (A, B) exists AND (B, A) also exists in donor_identities
print("\nFinding reversed name pairs...")
cur.execute("SELECT DISTINCT canonical_name FROM donor_identities WHERE canonical_name LIKE '%, %'")
all_names = {r[0] for r in cur.fetchall() if r[0]}
print(f"  {len(all_names):,} distinct names with comma")

# Find bidirectional pairs
pairs = []   # (wrong_version, correct_version)
seen = set()
for name in all_names:
    if name in seen:
        continue
    parts = name.split(', ', 1)
    if len(parts) != 2:
        continue
    a, b = parts[0].strip(), parts[1].strip()
    flipped = f"{b}, {a}"
    if flipped in all_names and flipped not in seen:
        # Decide which is correct: Last, First format
        # Heuristic: whichever has more total donation records is likely the canonical form
        cur.execute("""
            SELECT COUNT(*) FROM campaign_finance cf
            JOIN donor_identities di ON cf.donor_id = di.donor_id
            WHERE di.canonical_name = ?
        """, (name,))
        n1 = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM campaign_finance cf
            JOIN donor_identities di ON cf.donor_id = di.donor_id
            WHERE di.canonical_name = ?
        """, (flipped,))
        n2 = cur.fetchone()[0]
        # The smaller one is likely the reversed/noise version
        if n1 <= n2:
            pairs.append((name, flipped))    # name is wrong, flipped is correct
        else:
            pairs.append((flipped, name))    # flipped is wrong, name is correct
        seen.add(name)
        seen.add(flipped)

print(f"  Found {len(pairs)} reversal pairs")
for wrong, correct in sorted(pairs, key=lambda x: x[1])[:50]:
    print(f"    [{wrong}] -> [{correct}]")

# ── 3. Rename reversed entries ────────────────────────────────────────────────
print("\nFixing reversed names...")
fixed = 0
for wrong, correct in pairs:
    cur.execute(
        "UPDATE donor_identities SET canonical_name=? WHERE canonical_name=?",
        (correct, wrong)
    )
    fixed += cur.rowcount
conn.commit()
print(f"  Renamed {fixed:,} donor_id entries")

# ── 4. Re-run cross-identity for newly renamed identities ─────────────────────
print("\nRe-running cross-identity resolution for affected names...")
affected_names = {correct for _, correct in pairs}

newly_resolved = 0
for name in affected_names:
    # Find unresolved donor_ids with this name
    cur.execute("""
        SELECT donor_id FROM donor_identities
        WHERE canonical_name=? AND resolved_industry IS NULL
    """, (name,))
    unresolved = [r[0] for r in cur.fetchall()]
    if not unresolved:
        continue

    # Best resolved sibling (non-noise, employer confidence preferred)
    cur.execute("""
        SELECT resolved_industry, resolved_employer_display, resolved_confidence,
               SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)) as tot
        FROM donor_identities di
        LEFT JOIN campaign_finance cf ON cf.donor_id = di.donor_id
        WHERE di.canonical_name=?
          AND di.resolved_industry IS NOT NULL
          AND di.resolved_industry NOT IN ('Not Employed','Self-Employed','Student')
        GROUP BY di.donor_id
        ORDER BY (di.resolved_confidence = 'employer') DESC, tot DESC
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
        newly_resolved += 1

conn.commit()
print(f"  Cross-resolved {newly_resolved} identities")

# ── 5. Rebuild qadri_all_donations.json ──────────────────────────────────────
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
donations_json = json.dumps(rows, separators=(',', ':'), ensure_ascii=False)
with open("qadri_all_donations.json", "w", encoding="utf-8") as f:
    f.write(donations_json)
print(f"  Written {len(rows):,} records, {len(donations_json.encode())//1024} KB")

# ── 6. New INTEREST_GROUPS totals ─────────────────────────────────────────────
print("\nNew Qadri breakdown (correction=X excluded):")
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
OTHER = {"Media","Retail","Architecture","Entertainment","Transportation","Labor","Venture Capital","Retail / Media / Other"}
NOISE = {"Not Employed","Self-Employed","Student","Unknown","Unknown / Unclassified"}
employer_total = sum(r[1] for r in breakdown if r[0] not in NOISE)
other_total = sum(r[1] for r in breakdown if r[0] in OTHER)
other_donors = sum(r[2] for r in breakdown if r[0] in OTHER)

print(f"  Grand total: ${grand:,.0f}")
print(f"  Employer-affiliated: ${employer_total:,.0f} = {employer_total/grand*100:.1f}%")
print()
for r in breakdown:
    pct = r[1]/grand*100
    print(f"  (\"{r[0]}\", {int(r[1])}, {r[2]}),  # {pct:.1f}%")

print(f"\n  Retail/Media/Other combined: ${other_total:,.0f}, {other_donors} donors")
conn.close()
