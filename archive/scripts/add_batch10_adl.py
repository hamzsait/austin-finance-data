"""Load batch 10 ADL findings."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # Lisa Kaufman — Past ADL Board Chair + Lion of Judah
    ('Kaufman, Lisa', 'Anti-Defamation League (ADL) Central Texas Region', 'Past Board Chair, Board of Directors',
     'jewish_civic', 'https://daviskaufman.com/about-us/lisa-kaufman/',
     'Davis Kaufman PLLC partner (Austin lobbying/public policy law firm). Firm bio explicitly states past-board chair role.'),
    ('Kaufman, Lisa', 'Shalom Austin Womens Philanthropy Lion of Judah', 'Member',
     'jewish_civic', 'https://shalomaustin.org/wplions/',
     'Lion of Judah is Shalom Austin / Jewish Federation top womens giving society'),

    # Sandy Dochen — MAJOR finding (past Shalom Austin president + current ADL board + 2024 DC advocacy trip)
    ('Dochen, Sandy', 'Anti-Defamation League (ADL)', 'Current Board Member',
     'jewish_civic', 'https://www.linkedin.com/in/sandydochen',
     'Multiple independent sources confirm ADL board role. Also on Science Mill board, NWACA, etc.'),
    ('Dochen, Sandy', 'Shalom Austin (Jewish Federation of Greater Austin)', 'Past President / Past Presidents Council; Former Vice Chair',
     'jewish_civic', 'https://shalomaustin.org/2024/03/01/ignite-2024/',
     'Joseph Krassner Campaign Leadership Award recipient (March 2024 IGNITE! event). Part of Austin Jewish community delegation to DC in March 2024 to advocate for Israel and against antisemitism.'),
    ('Dochen, Sandy', 'Shalom Austin', 'King David Society donor ($25K-$36K) 2022-23 Honor Roll + Legacy Society member',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Carol and Sandy Dochen. King David Society = top donor tier.'),

    # Emma Reed — ADL staff employee
    ('Reed, Emma', 'Anti-Defamation League (ADL) National', 'Executive Legal Assistant (staff)',
     'jewish_civic', 'https://www.linkedin.com/in/emmarreed/',
     'Paid staff employee at ADL. NYC metro based. Donor address Scarsdale NY consistent.'),
]

added = 0
for row in new:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} from batch 10 ADL')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations: {cur.fetchone()[0]}')

# Show complete picture of ADL-tied people
print()
print('=== ALL Qadri donors with verified ADL Austin board/leadership ties ===')
cur.execute('''
    SELECT ca.canonical_name, ca.role,
           SUM(CAST(cf.contribution_amount AS REAL)) as qadri_total
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name = ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE cf.recipient = 'Qadri, Zohaib' AND cf.correction != 'X'
      AND ca.organization LIKE '%Anti-Defamation%'
    GROUP BY ca.canonical_name, ca.role
    ORDER BY qadri_total DESC
''')
for r in cur.fetchall():
    print(f'  {r[0]:<20} ${r[2]:>5,.0f} | {r[1][:70]}')
c.close()
