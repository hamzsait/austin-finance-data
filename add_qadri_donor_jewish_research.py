"""Load ADL/Jewish civic findings on Qadri's top 100 donors."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new_records = [
    # === David Kahn (ColinaWest, Austin FC owner) ===
    ('Kahn, David', 'Greater Austin Jewish Community (Shalom Austin)', 'Past Board Member',
     'jewish_civic', 'https://www.austinfc.com/news/david-kahn',
     'Austin FC owner bio confirms past board service. ColinaWest Real Estate Managing Partner. Austin resident since 1983.'),
    ('Kahn, David', 'Shalom Austin Jewish Foundation', 'Joshua Society donor ($10K-$18K) 2022-23',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Andrea Koplowitz Kahn and David Kahn"'),
    ('Kahn, David', 'Downtown Austin Alliance', 'Past Board Member',
     'civic', 'https://www.austinfc.com/news/david-kahn', 'Per Austin FC bio'),
    ('Kahn, David', 'Broadway Bank', 'Past Board Member',
     'business', 'https://www.austinfc.com/news/david-kahn', 'Per Austin FC bio'),
    ('Kahn, David', 'Austin FC', 'Part Owner', 'business',
     'https://www.austinfc.com/news/david-kahn', 'MLS soccer franchise'),
    ('Kahn, David', 'ColinaWest Real Estate', 'Managing Partner', 'business',
     'https://www.austinfc.com/news/david-kahn', ''),

    # === Daryl Kunik (TOPO, multi-gen Shalom Austin) ===
    ('Kunik, Daryl', 'Shalom Austin Jewish Foundation', 'Major Donor ($25K-$50K) 2022-23',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Dana & Daryl Kunik". Multi-year top-tier donor.'),
    ('Kunik, Daryl', 'Burt Kunik JAMen Forum (Shalom Austin)', 'Family namesake / participant',
     'jewish_civic', 'https://shalomaustin.org/2025/02/25/jamen-jo25/',
     'Son of late Burt Kunik, founder/chair of Shalom Austin Jewish Austin Men program. Program renamed in his fathers honor; Daryl spoke at tribute event.'),
    ('Kunik, Daryl', 'TOPO (TOPO-DG)', 'Real Estate Developer', 'business',
     'https://www.topo-dg.com/about-topo', 'Austin commercial real estate firm'),

    # === Kimberly Levinson (already partially in DB as Government — add Jewish ties) ===
    ('Levinson, Kimberly', 'Temple Beth Shalom (Austin Reform)', 'Patron / Member',
     'jewish_civic', 'https://www.bethshalomaustin.org/tribute-party',
     'Listed as "Adam & Kimberly Levinson" under Patrons on TBS Tribute Party donor list. Publicly identified TBS as "my temple" on LinkedIn. Not currently on board.'),
    ('Levinson, Kimberly', 'KBL Consulting', 'Principal', 'business',
     'https://www.linkedin.com/in/kimberly-levinson-11b49214', ''),
    ('Levinson, Kimberly', 'City of Austin Downtown Commission', 'Vice Chair', 'political',
     'https://www.austintexas.gov/department/downtown-commission', ''),

    # === James Talarico (qualified — attended 2019 AIPAC event, since disavowed) ===
    ('Talarico, James', 'AIPAC', 'Attended 2019 event (since publicly disavowed)',
     'jewish_political', 'https://jewishinsider.com/2026/01/talarico-who-now-disavows-aipac-attended-groups-event-in-2019/',
     'TX State Rep & 2026 US Senate candidate. Per Jewish Insider: attended AIPAC event in 2019 but has since publicly disavowed AIPAC, pledged to oppose offensive arms to Israel, called Israeli conduct in Gaza "war crimes." Current posture J-Street-adjacent liberal critic, NOT current AIPAC ally.'),
]

added = skipped = 0
for row in new_records:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
    else: skipped += 1

c.commit()
print(f'Added {added} new affiliations (skipped {skipped} duplicates)')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations now: {cur.fetchone()[0]}')

# Show new findings cross-referenced with their Qadri donations
print()
print('=== New findings: Qadri donors with verified Jewish civic ties ===')
new_names = ['Kahn, David', 'Kunik, Daryl', 'Levinson, Kimberly', 'Talarico, James']
for name in new_names:
    cur.execute('''
        SELECT SUM(CAST(cf.contribution_amount AS REAL)) as total
        FROM donor_identities di
        JOIN campaign_finance cf ON cf.donor_id = di.donor_id
        WHERE di.canonical_name = ? AND cf.recipient = 'Qadri, Zohaib' AND cf.correction != 'X'
    ''', (name,))
    total = cur.fetchone()[0] or 0
    cur.execute('SELECT COUNT(*) FROM civic_affiliations WHERE canonical_name = ?', (name,))
    n_affil = cur.fetchone()[0]
    print(f'  {name:<22} ${total:>6,.0f} to Qadri  |  {n_affil} verified affiliations')

c.close()
