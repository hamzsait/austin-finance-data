"""Load AIPAC catchup findings from agents."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new_records = [
    # === NORA LIEBERMAN — TIER 1 AIPAC ===
    ('Lieberman, Nora', 'AIPAC (Austin)', 'Local AIPAC Leadership Chair', 'aipac_direct',
     'https://shalomaustin.org/standwithisrael/',
     'TIER 1 finding. Identified publicly as Austins Local AIPAC Leadership Chair. Credited with "growing Austins pro-Israel political group." Spoke at Shalom Austin Stand With Israel community events.'),
    ('Lieberman, Nora', 'AIPAC', '"My AIPAC Story" featured speaker (national video series)', 'aipac_direct',
     'https://ar-ar.facebook.com/AIPAC/videos/nora-lieberman-myaipacstory/2543648125964476/',
     'Featured in AIPACs official "My AIPAC Story" video testimonial series'),

    # === DANIEL LUBETZKY — ADL NATIONAL BOARD ===
    ('Lubetzky, Daniel', 'Anti-Defamation League (ADL)', 'NATIONAL Board of Directors',
     'jewish_civic', 'https://www.adl.org/who-we-are/our-organization/our-board-of-directors/daniel-lubetzky',
     'NATIONAL board (not just Austin chapter). Lubetzky Family Foundation Frontline Impact Project mobilized aid to Israel after Oct 7 2023.'),
    ('Lubetzky, Daniel', 'AIPAC', 'Former AIPAC activist (Stanford Law early 1990s, historical)',
     'aipac_direct', 'https://stanforddaily.com/2023/12/06/kind-ceo-and-human-rights-activist-daniel-lubetzky-works-for-a-two-state-solution/',
     'Self-disclosed former AIPAC activist during Stanford Law years. Has since shifted to two-state solution advocacy. Historical AIPAC tie only — not current supporter.'),
]

added = 0
for row in new_records:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} new affiliations from AIPAC catchup')

# Now show all AIPAC-direct findings for Qadri donors
print()
print('=== Qadri donors with AIPAC-direct ties ===')
cur.execute('''
    SELECT DISTINCT ca.canonical_name, ca.role, ca.organization,
           SUM(CAST(cf.contribution_amount AS REAL)) as qadri_total
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name = ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE cf.recipient = 'Qadri, Zohaib' AND cf.correction != 'X'
      AND ca.category IN ('aipac_direct', 'pro_israel')
    GROUP BY ca.canonical_name, ca.organization
    ORDER BY qadri_total DESC
''')
for r in cur.fetchall():
    print(f'  {r[0]:<22} ${r[3]:>5,.0f} | {r[2][:40]} — {r[1][:50]}')

cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print()
print(f'Total civic affiliations: {cur.fetchone()[0]}')
c.close()
