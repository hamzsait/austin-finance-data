"""Load ADL findings from batches 7-8."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # Seth Halpern — CURRENT Shalom Austin Board Chair
    ('Halpern, Seth', 'Shalom Austin (Jewish Community Association of Austin)', 'Board Chair 2023-2024 (Chair Elect 2022-23)',
     'jewish_civic', 'https://shalomaustin.org/2024/03/01/jfna-shalom-austin/',
     'TOP governance role at Shalom Austin umbrella. Met with JFNA Chair Julie Platt Feb 2024 to discuss JFNA Israel work.'),
    ('Halpern, Seth', 'Shalom Austin', 'Joshua Society donor ($10K-$18K) with Lauren Halpern',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/', 'Top tier donor'),
    ('Halpern, Seth', 'Jewish Foundation of Austin', 'Lauren and Seth Halpern Fund namesake',
     'jewish_civic', 'https://shalomaustin.org/fundholders/', 'Named family fund'),

    # Stephen Mills — Ballet Austin, ADL Maislin honoree
    ('Mills, Stephen', 'Anti-Defamation League (ADL)', '2006 Maislin Humanitarian Award recipient',
     'jewish_civic', 'https://balletaustin.org/stephen-mills/light/',
     'Ballet Austin Artistic Director. Created Light / The Holocaust and Humanity Project. Spoke at US Holocaust Memorial Museum Voices on Anti-Semitism series (2013) and UN (2014).'),
    ('Mills, Stephen', 'Ballet Austin', 'Artistic Director', 'business',
     'https://balletaustin.org/stephen-mills/', ''),

    # Lily Smullen — CURRENT Vice Chair
    ('Smullen, Lily', 'Shalom Austin', 'Vice Chair Board of Directors (multi-year: 2018-19, 2022-23, 2023-24)',
     'jewish_civic', 'https://shalomaustin.org/2022/06/30/annual_meeting_recap_2022/',
     'Long-serving Vice Chair on Shalom Austin board (#2 position under Halpern)'),
    ('Smullen, Lily', 'Shalom Austin', 'Honor Roll donor ($5K-$10K) with AJ Smullen',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/', ''),

    # Jared Lindauer
    ('Lindauer, Jared', 'Shalom Austin', 'Outgoing Board Member (2022 Annual Meeting)',
     'jewish_civic', 'https://shalomaustin.org/2022/06/30/annual_meeting_recap_2022/',
     'Outgoing board member. Wife Kim Lindauer was welcomed as INCOMING Elected Director same meeting.'),
    ('Lindauer, Jared', 'Shalom Austin', 'Honor Roll donor ($1.8K-$5K) with Kim Lindauer',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/', ''),

    # Edward Safady — Prosperity Bank
    ('Safady, Edward', 'Shalom Austin', 'Honor Roll donor ($5K-$10K) Generations Campaign (as Eddie Safady)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Vice Chairman of Prosperity Bank. 42-year Austinite. Lebanese Christian heritage but direct Shalom Austin donor.'),
    ('Safady, Edward', 'Prosperity Bank', 'Vice Chairman', 'business',
     'Multiple sources', ''),
]

added = 0
for row in new:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} from ADL batch 7-8')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations: {cur.fetchone()[0]}')

print()
print('=== CURRENT Shalom Austin Leadership that gave to Qadri ===')
cur.execute('''
    SELECT ca.canonical_name, ca.role,
           SUM(CAST(cf.contribution_amount AS REAL)) as qadri_total
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name = ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE cf.recipient = 'Qadri, Zohaib' AND cf.correction != 'X'
      AND ca.organization LIKE '%Shalom Austin%'
      AND (ca.role LIKE '%Chair%' OR ca.role LIKE '%Director%' OR ca.role LIKE '%Board%')
    GROUP BY ca.canonical_name, ca.role
    ORDER BY qadri_total DESC
''')
for r in cur.fetchall():
    print(f'  {r[0]:<22} ${r[2]:>5,.0f} | {r[1][:70]}')
c.close()
