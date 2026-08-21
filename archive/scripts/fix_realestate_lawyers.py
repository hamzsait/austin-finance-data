"""
Reclassify real-estate-development law firms from Legal -> Real Estate.
Firms: Armbrust & Brown, Jackson Walker, Winstead, Holland & Knight, METCALFE WOLFF STUART
"""
import sqlite3, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("austin_finance.db", timeout=120)
conn.execute("PRAGMA journal_mode=WAL")
cur = conn.cursor()

RE_FIRMS = [
    'Armbrust  & Brown',
    'Jackson Walker',
    'Winstead',
    'Holland & Knight',
    'METCALFE WOLFF STUART & Williams, LLP',
]

# 1. Update employer_identities
cur.execute(f"""
    UPDATE employer_identities
    SET industry = 'Real Estate'
    WHERE canonical_name IN ({','.join('?'*len(RE_FIRMS))})
      AND industry = 'Legal'
""", RE_FIRMS)
print(f"employer_identities updated: {cur.rowcount} rows")

# 2. Update donor_identities where resolved_employer_display matches
cur.execute(f"""
    UPDATE donor_identities
    SET resolved_industry = 'Real Estate'
    WHERE resolved_employer_display IN ({','.join('?'*len(RE_FIRMS))})
      AND resolved_industry = 'Legal'
""", RE_FIRMS)
print(f"donor_identities updated: {cur.rowcount} rows")

conn.commit()

# 3. Rebuild qadri_all_donations.json
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
print(f"  Written {len(rows):,} records")

# 4. Print new INTEREST_GROUPS breakdown
print("\nNew Qadri breakdown:")
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
