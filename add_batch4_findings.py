"""Load batch 4 (donors 301-400) ADL/Oil findings."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new_records = [
    # === Daniel Lubetzky (KIND Snacks founder) ===
    ('Lubetzky, Daniel', 'OneVoice Movement', 'Founder', 'liberal_zionist',
     'https://en.wikipedia.org/wiki/OneVoice_Movement',
     'Founded 2002 to promote Israeli-Palestinian two-state solution. Liberal Zionist peace org.'),
    ('Lubetzky, Daniel', 'PeaceWorks Foundation', 'Founder', 'liberal_zionist',
     'https://en.wikipedia.org/wiki/Daniel_Lubetzky',
     'Israeli-Palestinian peace org from which OneVoice emerged'),
    ('Lubetzky, Daniel', 'ADL Workplace Pledge to Fight Antisemitism', 'Lubetzky Family Foundation signatory', 'jewish_civic',
     'https://jewishinsider.com/2024/05/daniel-lubetzky-kind-snacks-milken-institute-global-conference-antisemitism/',
     'Family foundation signed pledge'),
    ('Lubetzky, Daniel', 'KIND Snacks', 'Founder', 'business',
     'https://en.wikipedia.org/wiki/Daniel_Lubetzky',
     'Major Austin-based food company; son of Holocaust survivor'),

    # === Nora Lieberman ===
    ('Lieberman, Nora', 'Shalom Austin', 'Elected Director, 2024-2025 Board of Directors',
     'jewish_civic', 'https://www.facebook.com/JewishAustin/videos/a-word-from-this-years-woman-of-valor-nora-lieberman/606425269824107/',
     'Currently on Shalom Austin board (current sitting member)'),
    ('Lieberman, Nora', 'Shalom Austin', '2019 Woman of Valor honoree',
     'jewish_civic', 'https://www.facebook.com/JewishAustin/videos/a-word-from-this-years-woman-of-valor-nora-lieberman/606425269824107/',
     'Annual highest honor from Shalom Austin Womens Philanthropy'),
    ('Lieberman, Nora', 'Shalom Austin', 'Forever Lion Legacy Society donor ($125K+ endowment); Honor Roll $10K-$18K tier',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Top legacy giving tier'),
    ('Lieberman, Nora', 'Texas Hillel', 'Donor (with husband Allen Lieberman)',
     'jewish_civic', 'https://texashillel.org/donors/', ''),

    # === Sandy Gottesman (DIFFERENT person from Morris Gottesman) ===
    ('Gottesman, Sandy', 'Shalom Austin', 'Major Donor ($36K-$50K) 2022-23',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Sandy Gottesman and Lisa Gottesman". Top tier donor.'),
    ('Gottesman, Sandy', 'Jewish Foundation of Austin', 'Sandy Gottesman Fund namesake', 'jewish_civic',
     'https://shalomaustin.org/fundholders/',
     'Endowed fund at Jewish Foundation through Shalom Austin'),

    # === Andrea Kahn (David Kahns wife) ===
    ('Kahn, Andrea', 'Shalom Austin', 'Donor ($10K-$18K) 2022-23 (with David Kahn)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Andrea Koplowitz Kahn and David Kahn". Multi-year donor.'),

    # === Dana Kunik (Daryl Kunik wife) ===
    ('Kunik, Dana', 'Shalom Austin', 'Donor ($5K-$10K) 2022-23 (with Daryl Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Wife of Daryl Kunik. Burt Kunik (Daryls father) was founder of JAMen at Shalom Austin.'),

    # === Robert Epstein — major finding ===
    ('Epstein, Robert', 'Shalom Austin JCC', 'Epstein Family Community Hall namesake',
     'jewish_civic', 'https://shalomaustin.org/venue/jcc-community-hall/',
     'Newly renovated 6,250 sqft ballroom-style event space named for the Epstein family. Robert Epstein 78746 Austin. Aubrey & Robert Epstein also Texas Hillel donors.'),
    ('Epstein, Robert', 'Texas Hillel', 'Donor (with Aubrey Epstein)', 'jewish_civic',
     'https://texashillel.org/donors/', ''),

    # === Robin Krumme ===
    ('Krumme, Robin', 'Shalom Austin JCC', 'Personal Trainer (employee)',
     'jewish_civic', 'https://shalomaustin.org/personaltraining/', 'Listed on Shalom Austin JCC fitness page'),

    # === Diane Land — additional Shalom Austin record (was already in DB for ADL) ===
    ('Land, Diane', 'Shalom Austin', 'Honor Roll Donor 2022-23 ($1.8K-$5K) with Steve Adler',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Diane Land and Hon. Steve Adler"'),

    # === OIL & GAS FINDINGS ===

    # Michael J Mazidi
    ('J Mazidi, Michael', 'Baker Botts L.L.P.', 'Senior Associate — Oilfield and Energy Services industry focus',
     'oil_gas_legal', 'https://www.bakerbotts.com/people/m/mazidi-michael',
     'M&A/securities work for Cabot Oil & Gas, Transocean, Halliburton, Liberty Energy. Houston-based.'),

    # AJ Durrani
    ('Durrani, AJ', 'Shell Oil (Shell-USA)', 'Regional Resource Volumes Manager, Shell-USA Unconventional Resources (retired 2011)',
     'oil_gas_major', 'https://execservicecorphouston.org/a-j-durrani',
     '34-year Shell career. Retired 2011. Houston-based donor.'),

    # Anuarbek Imanbaev
    ('Imanbaev, Anuarbek', 'Anadarko Petroleum Corporation', 'Former Petroleum Engineer / Exploration Project Manager (12+ years)',
     'oil_gas_major', 'https://cleantechnica.com/2019/12/26/the-kazakh-tesla-guy-who-brought-tesla-to-kazakhstan/',
     'UT Austin petroleum engineering grad. Worked oil/gas exploration for Anadarko 12+ years before transitioning to Tesla advocacy and real estate.'),
]

added = 0
for row in new_records:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} new affiliations from batch 4')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations: {cur.fetchone()[0]}')

# Show all the verified findings on Qadri donors so far
print()
print('=== ALL Qadri donors with verified Jewish civic / Israel ties ===')
cur.execute('''
    SELECT DISTINCT ca.canonical_name,
           SUM(CAST(cf.contribution_amount AS REAL)) as qadri_total,
           COUNT(DISTINCT ca.organization) as n_orgs
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name = ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE cf.recipient = 'Qadri, Zohaib' AND cf.correction != 'X'
      AND ca.category IN ('jewish_civic', 'pro_israel', 'liberal_zionist', 'adl', 'zionist_peace')
    GROUP BY ca.canonical_name
    ORDER BY qadri_total DESC
''')
for r in cur.fetchall():
    print(f'  {r[0]:<30} ${r[1]:>5,.0f} to Qadri  |  {r[2]} verified affiliations')

# Same for oil
print()
print('=== ALL Qadri donors with verified oil/gas ties ===')
cur.execute('''
    SELECT DISTINCT ca.canonical_name,
           SUM(CAST(cf.contribution_amount AS REAL)) as qadri_total,
           ca.organization, ca.role
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name = ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE cf.recipient = 'Qadri, Zohaib' AND cf.correction != 'X'
      AND ca.category LIKE 'oil_gas%'
    GROUP BY ca.canonical_name, ca.organization
    ORDER BY qadri_total DESC
''')
for r in cur.fetchall():
    print(f'  {r[0]:<25} ${r[1]:>5,.0f}  |  {r[2]} — {r[3][:50]}')

c.close()
