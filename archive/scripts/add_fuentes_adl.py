"""Load ADL findings for Fuentes donors."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # (canonical_name, organization, role, category, source_url, notes)

    # Stephen Adler - ADL Austin Region past Board Chair 2009-2012; helped create
    # Austin Hate Crimes Task Force and expanded No Place for Hate program.
    # Matches Fuentes batch_1 "Adler, Stephen" (mayor, Austin 78701).
    ('Adler, Stephen', 'Anti-Defamation League (ADL) Austin',
     'Past Board Chair (2009-2012); helped create Austin Hate Crimes Task Force; expanded No Place for Hate program',
     'jewish_civic',
     'https://en.wikipedia.org/wiki/Steve_Adler_(politician)',
     'Wikipedia biography of Steve Adler (58th Austin mayor 2015-2023) explicitly documents he "served as the board chair of the Anti-Defamation League Austin Region" from 2009 to 2012 and notes ADL board-chair work alongside Texas Tribune/Ballet Austin civic roles. Disambiguation: Fuentes donor listed as "mayor" at Austin 78701 matches Steve Adler, former Austin mayor.'),

    # Jeff Newberg - ADL Austin 4th Board Chair, National Commissioner, Past Board Member,
    # Austin Advisory Board member. 2023 Golden Door Awards honoree.
    # Matches Fuentes batch_2 "Newberg, Jeffrey" (Endeavor Real Estate Group, Austin 78746).
    ('Newberg, Jeffrey', 'Anti-Defamation League (ADL) Austin',
     'Past Board Chair (4th Chair); National Commissioner; Austin Advisory Board; 2023 Golden Door Awards honoree',
     'jewish_civic',
     'https://platform.reverecre.com/user/jeff.newberg',
     'Revere CRE profile lists Jeff Newberg as ADL Austin Past Board Member, Past Chair, National Commissioner, Austin Advisory Board. Confirmed by Shalom Austin Sep 2023 "Choosing Hope in a World of Hate" piece noting Jeff served as ADL Austin\'s 4th board chair, and 2023 ADL Austin Golden Door Awards Dinner honoree (Oct 30, 2023) with wife Val. Disambiguation: Fuentes donor employer "endeavor estate group real" (Endeavor Real Estate Group) and Austin 78746 location match Newberg\'s role as co-founder/Managing Principal of Endeavor.'),

    # Val Newberg - longtime ADL Austin board member, 2023 Golden Door Awards honoree.
    # Matches Fuentes batch_2 "Newberg, Valerie" (homemaker, Austin 78746 - same household as Jeff).
    ('Newberg, Valerie', 'Anti-Defamation League (ADL) Austin',
     'Longtime Board Member; 2023 Golden Door Awards honoree',
     'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl/',
     'Shalom Austin Sep 2023 piece ("Choosing Hope in a World of Hate") describes Val Newberg as "a longtime ADL board member and dedicated volunteer." Honored with husband Jeff Newberg at 2023 ADL Austin Golden Door Awards Dinner (Oct 30, 2023). Disambiguation: same 78746 Austin ZIP as Jeff Newberg (Endeavor); listed as "homemaker" in Fuentes filing, matching Velasquez filing pattern.'),

    # Dan Graham - ADL Austin 2016 True Colors honoree (Vision in Action Award).
    # Matches Fuentes batch_2 "Graham, Dan" (BuildASign CEO, Austin 78730).
    ('Graham, Dan', 'Anti-Defamation League (ADL) Austin',
     '2016 True Colors honoree (Vision in Action Award)',
     'jewish_civic',
     'https://austin.culturemap.com/news/society/09-09-16-anti-defamation-league-true-colors-2016/',
     'CultureMap Austin coverage of ADL Austin 5th annual True Colors event (Sep 2016) identifies Dan Graham as honoree in the "young Austin leaders show their true colors" story. Disambiguation: Fuentes donor employer "a build ceo sign" (BuildASign CEO) and Austin 78730 location match Dan Graham co-founder/CEO of BuildASign, consistent with Velasquez research that paired him with Notley co-founder Lisa Graham.'),
]

added = 0
for row in new:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} ADL-tied Fuentes donors')
c.close()
