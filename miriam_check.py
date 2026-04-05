import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()
cur.execute("SELECT di.donor_id, di.canonical_name, di.canonical_zip, di.canonical_employer, di.resolved_industry FROM donor_identities di WHERE di.canonical_name = 'Miriam, Schulman'")
for r in cur.fetchall():
    print(f"id={r[0][:8]}  name=[{r[1]}]  zip={r[2]}  emp=[{r[3]}]  resolved={r[4]}")
cur.execute("SELECT cf.recipient, cf.contribution_date, ROUND(COALESCE(cf.balanced_amount,cf.contribution_amount),2), cf.donor_reported_employer, cf.donor_reported_occupation, cf.city_state_zip FROM campaign_finance cf LEFT JOIN donor_identities di ON cf.donor_id=di.donor_id WHERE di.canonical_name='Miriam, Schulman' ORDER BY cf.contribution_date")
for r in cur.fetchall():
    print(f"  {r[1][:10]}  {r[0][:35]:<35}  ${r[2]:>7}  emp=[{r[3]}]  occ=[{r[4]}]  loc={r[5]}")
conn.close()
