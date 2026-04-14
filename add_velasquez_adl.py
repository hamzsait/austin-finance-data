"""Load ADL findings for Velasquez donors."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # (canonical_name, organization, role, category, source_url, notes)

    # Jeff Newberg - ADL Austin 4th Board Chair, National Commissioner, Past Board Member,
    # Austin Advisory Board member. 2023 Golden Door Awards honoree.
    # Matches Velasquez batch_1 "Newberg, Jeff" (Endeavor Real Estate Group, Austin 78746).
    ('Newberg, Jeff', 'Anti-Defamation League (ADL) Austin',
     'Past Board Chair (4th Chair); National Commissioner; Austin Advisory Board; 2023 Golden Door Awards honoree',
     'jewish_civic',
     'https://platform.reverecre.com/user/jeff.newberg',
     'Profile on Revere CRE explicitly lists ADL Austin Past Board Member, Past Chair, National Commissioner, Austin Advisory Board. Confirmed by Shalom Austin Sep 2023 piece ("Choosing Hope in a World of Hate") noting Jeff served as ADL Austin\'s 4th board chair. Honored with Val Newberg at 2023 ADL Austin Golden Door Awards Dinner (Oct 30, 2023). Disambiguation: Velasquez donor employer "Endeavor Real Estate Group" matches Newberg\'s role as co-founder/Managing Principal of Endeavor.'),

    # Val Newberg - longtime ADL Austin board member, 2023 Golden Door Awards honoree.
    # Matches Velasquez batch_1 "Newberg, Valerie" (homemaker, Austin 78746 - same household as Jeff).
    ('Newberg, Valerie', 'Anti-Defamation League (ADL) Austin',
     'Longtime Board Member; 2023 Golden Door Awards honoree',
     'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl/',
     'Shalom Austin Sep 2023 piece describes Val Newberg as "a longtime ADL board member and dedicated volunteer." Honored with husband Jeff Newberg at 2023 ADL Austin Golden Door Awards Dinner. Disambiguation: same 78746 Austin address as Jeff Newberg (Endeavor); listed as "homemaker" in Velasquez filing.'),

    # Dan Graham - ADL Austin 2016 True Colors honoree (Vision in Action Award).
    # Matches Velasquez batches "Graham, Dan" (founder/partner at Notley, Austin).
    ('Graham, Dan', 'Anti-Defamation League (ADL) Austin',
     '2016 True Colors honoree (Vision in Action Award)',
     'jewish_civic',
     'https://austin.culturemap.com/news/society/09-09-16-anti-defamation-league-true-colors-2016/',
     'CultureMap Austin coverage of ADL Austin 5th annual True Colors event (Sep 2016) identifies Dan Graham as honoree. Disambiguation: Velasquez donor employer "Notley" (co-founder with wife Lisa) and Austin 78704/78721 location match Dan Graham co-founder of Notley impact investing firm.'),

    # Lisa Graham - ADL Austin 2016 True Colors honoree.
    # Matches Velasquez batches "Graham, Lisa" (founder Notley, Austin).
    ('Graham, Lisa', 'Anti-Defamation League (ADL) Austin',
     '2016 True Colors honoree',
     'jewish_civic',
     'https://austin.culturemap.com/news/society/09-09-16-anti-defamation-league-true-colors-2016/',
     'CultureMap Austin coverage of ADL Austin 5th annual True Colors event (Sep 2016) identifies Lisa Graham as one of the four young-leader honorees "celebrated for their work to advance social justice and civil rights." Disambiguation: Velasquez donor employer "Notley" (founder/CEO/Partner) and Austin 78744/78721 location match Lisa Graham co-founder/CEO of Notley.'),
]

added = 0
for row in new:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} ADL-tied Velasquez donors')
c.close()
