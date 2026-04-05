import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()
cur.execute("""SELECT COUNT(*) FROM donor_identities unres WHERE unres.resolved_industry IS NULL AND EXISTS (SELECT 1 FROM donor_identities res WHERE res.canonical_name = unres.canonical_name AND res.resolved_industry IS NOT NULL AND res.resolved_industry NOT IN ('Not Employed','Self-Employed','Student'))""")
print('Cross-identity eligible:', cur.fetchone()[0])
cur.execute("""SELECT unres.canonical_name, unres.canonical_zip, res.resolved_industry, res.resolved_employer_display, res.canonical_zip FROM donor_identities unres JOIN donor_identities res ON res.canonical_name = unres.canonical_name WHERE unres.resolved_industry IS NULL AND res.resolved_industry IS NOT NULL AND res.resolved_industry NOT IN ('Not Employed','Self-Employed','Student') GROUP BY unres.donor_id LIMIT 20""")
for r in cur.fetchall():
    print(f"  [{r[0]}] unres_zip={r[1]} <- {r[2]} ({r[3]}) from zip={r[4]}")
conn.close()
