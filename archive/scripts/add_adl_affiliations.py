"""Add ADL Austin board members to civic_affiliations and cross-reference with donor data."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

# All ADL Austin board members and key roles from the research
adl_records = [
    # Board Chairs (in order)
    ('Salmanson, Mark', 'Austin Anti-Defamation League (ADL)', 'Past Board Chair (post-Adler era, c. 2012)', 'jewish_civic',
     'https://communitymatters.biz/2010/01/30/adl-tol-some-pics/',
     'Listed as past ADL Austin chair in Community Matters Jan 2010'),
    ('Sperling, Robyn', 'Austin Anti-Defamation League (ADL)', 'Past Board Chair; National Commissioner', 'jewish_civic',
     'https://www.facebook.com/ADLAustin/videos/2349643755355226/',
     '2019 Golden Door Gala Maislin honoree; past board chair'),
    ('Newberg, Jeff', 'Austin Anti-Defamation League (ADL)', 'Past Board Chair (4th); National Commissioner', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl/',
     'Per Shalom Austin 2023; also Endeavor Real Estate co-founder'),
    ('Stein, Lynne', 'Austin Anti-Defamation League (ADL)', 'Board Chair (2020-2021)', 'jewish_civic',
     'https://shalomaustin.org/2020/11/23/anti-defamation-league-work-reflects-2020-challenges/',
     'Verified via Shalom Austin Nov 2020'),
    # Executive Board members
    ('Gottesman, Morris', 'Austin Anti-Defamation League (ADL)', 'Executive Board Member', 'jewish_civic',
     'https://shalomaustin.org/2021/08/24/adl-austin-honors-laura-and-morris-gottesman/',
     '2021 Torch of Liberty honoree (with wife Laura); US Capital Advisors'),
    ('Newberg, Val', 'Austin Anti-Defamation League (ADL)', 'Longtime Board Member', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl/',
     'Wife of Jeff Newberg; longtime ADL board member and dedicated volunteer'),
    ('Berkowitz, Jason', 'Austin Anti-Defamation League (ADL)', 'Board Member (since Jan 2012)', 'jewish_civic',
     'https://www.linkedin.com/in/jason-berkowitz-b0917310/',
     'Co-chair, 2011 Glass Leadership Institute class'),
    ('Soifer, Jan', 'Austin Anti-Defamation League (ADL)', 'Local & Regional Executive Committee; Co-Chair Civil Rights Cmte; Associate National Commissioner', 'jewish_civic',
     'https://jansoifer.com/about/',
     'Judge, 345th District Court Travis County'),
    ('Land, Diane', 'Austin Anti-Defamation League (ADL)', 'Board involvement (Adler-era); 2017 Maislin Humanitarian Award co-honoree', 'jewish_civic',
     'https://www.facebook.com/ADLAustin/videos/1686295158100429/',
     'Spouse of former Mayor Steve Adler; DT Land Group commercial real estate'),
    ('Winkelman, Marc', 'Austin Anti-Defamation League (ADL)', 'Board Member; National Jewish Democratic Council secretary', 'jewish_civic',
     'https://austin.adl.org/news/meet-the-winkelmans-again',
     'CEO Go! Retail/Calendar Club; documented ADL Austin involvement; also formerly secretary Elie Wiesel Foundation for Humanity'),
    ('Winkelman, Suzanne', 'Austin Anti-Defamation League (ADL)', 'Planning Committee', 'jewish_civic',
     'https://communitymatters.biz/2009/04/14/adl-torch-of-liberty-award/',
     'Spouse of Marc Winkelman; 2009 Torch of Liberty planning committee'),
    ('Shaw, Dave', 'Austin Anti-Defamation League (ADL)', 'Board Member (referenced)', 'jewish_civic',
     'https://communitymatters.biz/2010/01/30/adl-tol-some-pics/',
     'Arrow; testimonials director / 2010 fundraising committee'),
    ('Waxman, Judy', 'Austin Anti-Defamation League (ADL)', 'Leadership Roles (2009 messaging/PR committee)', 'jewish_civic',
     'https://communitymatters.biz/2009/11/07/',
     'Verified via Community Matters'),
    # Honorees
    ('Gottesman, Laura', 'Austin Anti-Defamation League (ADL)', '2021 Torch of Liberty Award honoree', 'jewish_civic',
     'https://shalomaustin.org/2021/08/24/adl-austin-honors-laura-and-morris-gottesman/',
     'With husband Morris (Executive Board)'),
    ('Rogat, Edie', 'Austin Anti-Defamation League (ADL)', '2019 Torch of Liberty Award honoree', 'jewish_civic',
     'https://www.facebook.com/ADLAustin/videos/479507596147223/',
     'Honored with Cotter Cunningham at 2019 Golden Door Gala'),
    ('Cunningham, Cotter', 'Austin Anti-Defamation League (ADL)', '2019 Torch of Liberty Award honoree', 'jewish_civic',
     'https://www.facebook.com/ADLAustin/videos/479507596147223/',
     'Co-honoree with Edie Rogat'),
    ('Sepulveda, Eugene', 'Austin Anti-Defamation League (ADL)', '2010 Torch of Liberty Co-Chair; 2022 Maislin Humanitarian Award honoree', 'jewish_civic',
     'https://communitymatters.biz/2010/01/30/adl-tol-some-pics/',
     'With husband Steven Tomlinson'),
    ('Tomlinson, Steven', 'Austin Anti-Defamation League (ADL)', '2022 Maislin Humanitarian Award honoree', 'jewish_civic',
     'https://communitymatters.biz/2010/01/30/adl-tol-some-pics/',
     'With husband Eugene Sepulveda'),
    ('Maislin, Audrey', 'Austin Anti-Defamation League (ADL)', '2012 Lifetime Achievement Award; namesake of Maislin Humanitarian Award', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl/',
     'Longtime major ADL donor (Austin/Houston)'),
    ('Maislin, Raymond', 'Austin Anti-Defamation League (ADL)', '2012 Lifetime Achievement Award; namesake of Maislin Humanitarian Award', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl/',
     'Longtime major ADL donor (Austin/Houston)'),
    ('Rudy, Amy', 'Austin Anti-Defamation League (ADL)', '2010 Torch of Liberty Award honoree', 'jewish_civic',
     'https://communitymatters.biz/2010/01/30/adl-tol-some-pics/',
     'With husband Kirk Rudy (Endeavor co-founder, ADL board)'),
]

added = 0
for row in adl_records:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount:
        added += 1

c.commit()
print(f'Added {added} new ADL Austin affiliations')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations now: {cur.fetchone()[0]}')

# Cross-reference with donor data
print()
print('=== ADL Austin board members cross-referenced with Austin donor data ===')
adl_names = [r[0] for r in adl_records]
for name in adl_names:
    cur.execute('''
        SELECT di.canonical_name, di.canonical_zip, di.fec_partisan_lean, di.ip_spectrum,
               SUM(CAST(cf.contribution_amount AS REAL)) as local_total,
               COUNT(DISTINCT cf.recipient) as campaigns
        FROM donor_identities di
        JOIN campaign_finance cf ON cf.donor_id = di.donor_id
        WHERE cf.correction != 'X' AND di.canonical_name = ?
        GROUP BY di.donor_id
        HAVING local_total > 0
        ORDER BY local_total DESC
        LIMIT 3
    ''', (name,))
    rows = cur.fetchall()
    if rows:
        for r in rows:
            ip = f' IP={r[3]}' if r[3] else ''
            lean = f' lean={r[2]:.2f}' if r[2] is not None else ''
            print(f'  {r[0]:<25} zip={(r[1] or "?"):<8} ${r[4] or 0:>7,.0f} ({r[5]} camps){lean}{ip}')

c.close()
