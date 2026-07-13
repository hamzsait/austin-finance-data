"""Load batch 3 (donors 201-300) ADL/Oil findings."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new_records = [
    # === Andrew/Andy Pastor (Endeavor co-founder) — NEW Jewish civic findings ===
    ('Pastor, Andrew', 'Dell Jewish Community Center / Shalom Austin', 'Past Trustee; Past Member of Development Board',
     'jewish_civic', 'https://www.endeavor-re.com/about/team/andy-pastor/',
     'Endeavor Real Estate co-founder. Verified via Endeavor team bio and Shalom Austin'),
    ('Pastor, Andrew', 'Shalom Austin', 'King David Society donor ($25K-$36K) 2022-23; "Laura and Andy Pastor Lobby" namesake',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Top-tier multi-year donor with wife Laura. Lobby in Shalom Austin Early Childhood Program named after them'),
    ('Pastor, Andrew', 'Endeavor Real Estate Group', 'Co-Founder & Managing Principal', 'business',
     'https://www.endeavor-re.com/about/team/andy-pastor/', 'One of 5 founding principals'),

    # === Jeffrey Newberg — additional Shalom Austin / Hillel detail (some already in DB) ===
    ('Newberg, Jeff', 'Shalom Austin', 'King David Society donor ($50K-$99K) 2022-23 with Val',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Very high tier donor; among the largest Shalom Austin gifts'),
    ('Newberg, Jeff', 'Texas Hillel', 'Donor', 'jewish_civic',
     'https://texashillel.org/donors/', 'Listed donors page'),
    ('Newberg, Val', 'Jewish Community Association of Austin (JCAA)', 'Director', 'jewish_civic',
     'https://theorg.com/org/shalom-austin/org-chart/jeff-newberg',
     'Listed in Shalom Austin org chart'),

    # === Sly Majid — NEW finding ===
    ('Majid, Sly', 'Shalom Austin', 'Donor 2022-23 Honor Roll ($5K-$10K, listed as Rachel Loebl and Sly Majid)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Former Chief Service Officer for Austin Mayors Office (Adler era); now Volkswagen Government Relations. Joint donation with Rachel Loebl.'),

    # === Ashley Phillips — NEW Oil & Gas finding ===
    ('Phillips, Ashley', 'Austin Women in Oil and Gas', 'Administrative Chair and Board of Directors (2019-present)',
     'oil_gas_industry_association', 'https://www.prnewswire.com/news-releases/tk-partner-appointed-to-austin-women-in-oil-and-gas-board-of-directors-300812769.html',
     'Partner at Holland & Knight (formerly Thompson & Knight); practice covers oil & gas regulatory and transactional matters in Eagle Ford, Bakken, Permian Basin'),
    ('Phillips, Ashley', 'Kay Bailey Hutchison Center for Energy, Law & Business (UT Austin)', 'Advisory Council member (2015-present)',
     'oil_gas_academic', 'https://www.hklaw.com/en/professionals/p/phillips-ashley-t-k',
     'Energy law and business advisory council at UT Austin'),
    ('Phillips, Ashley', 'Holland & Knight (formerly Thompson & Knight)', 'Partner — Energy Practice', 'business',
     'https://www.hklaw.com/en/professionals/p/phillips-ashley-t-k', 'Oil & gas regulatory, transactional, environmental'),
]

added = 0
for row in new_records:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} new affiliations')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations: {cur.fetchone()[0]}')
c.close()
