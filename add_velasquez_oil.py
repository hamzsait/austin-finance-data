"""Load Velasquez Oil & Gas findings.

Methodology: scanned velasquez_batch_{1-4}.txt for O&G-industry employer strings
(supermajors, independents, midstream, oilfield services, refineries, TX O&G
law/lobby firms, TXOGA, Permian operators). Pure oil/gas company hits: zero.
The Austin donor base skews heavily to Endeavor Real Estate Group (Austin
commercial developer — NOT Endeavor Energy Resources, the Permian E&P),
Armbrust & Brown (real estate law, not O&G), Presidium / Riverside Resources
(real estate). Ambiguous names were WebSearch-verified and ruled out:
  - "Butler Family Interests" (William Harris, CFO) = former Austin Mayor Roy
    Butler's real estate holdings; holds some passive TX mineral rights but
    primary business is real estate, no exec role at an O&G company.
  - "Grayco / John Gray III" (Houston) = multifamily real estate developer.
  - "Solomon Ortiz Jr / Ortiz Holdings" (Corpus Christi) = lobbying/consulting,
    no disclosed O&G clients. Ortiz Int'l Center (conv. hall named after his
    father) hosts TXOGA events, but Ortiz Jr is not in O&G exec/board role.
  - "Texas Disposal Systems" (Leticia Mendoza) = waste mgmt, not O&G.
  - "Southwest Desalination Assn" (Jeffrey Frazier) = water, not O&G.
  - "Texas Hotel & Lodging Assn" (Scott Joslove) = hospitality trade group.
  - "Tristan Castaneda" = Longbow Partners equity partner + ex Baker Botts TX
    gov-rel head (10 yrs). Baker Botts has heavy O&G practice, but F Minus
    does NOT list Castaneda as the registered lobbyist for Longbow's O&G
    clients (Enterprise Products / Targa). Leaving off — no current
    specifically-O&G role documented.

Verified finds (3): three Longbow Partners lobbyists whom F Minus / Texas
Ethics Commission filings show as registered state-level lobbyists for fossil-
fuel midstream clients Enterprise Products Partners LP and/or Targa Resources.
This is direct, current O&G industry-association representation.
"""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # William "Robert" Peeler Jr — Longbow Partners Managing Partner; registered
    # Texas lobbyist for Enterprise Products Partners LP (midstream pipeline)
    # and Targa Resources (midstream NGL/natural-gas processing). Donor is
    # "Peeler, William" $400 batch_2 line 99, employer "attorney longbow
    # partners", Austin 78703. Same person — Austin, attorney, Longbow.
    ('Peeler, William', 'Longbow Partners LLP (on behalf of Enterprise Products Partners LP)',
     'Managing Partner / Registered Texas Lobbyist for O&G midstream client',
     'oil_gas_industry_association',
     'https://fminus.org/clients/longbow-consulting-partners-llc-dba-longbow-partners/',
     'F Minus database (sourced from Texas Ethics Commission filings) lists '
     'Peeler Jr., William Robert as registered lobbyist for Enterprise Products '
     'Partners LP. Peeler is Managing Partner at Longbow. Austin-based match.'),
    ('Peeler, William', 'Longbow Partners LLP (on behalf of Targa Resources)',
     'Managing Partner / Registered Texas Lobbyist for O&G midstream client',
     'oil_gas_industry_association',
     'https://fminus.org/clients/longbow-consulting-partners-llc-dba-longbow-partners/',
     'F Minus lists Peeler Jr., William Robert as registered TX lobbyist for '
     'Targa Resources (midstream NGL / natural gas processor).'),

    # Jennifer Perkins — Longbow Partners partner (joined 2022); registered
    # Texas lobbyist for Enterprise Products Partners LP and Targa Resources.
    # Donor "Perkins, Jennifer" $150 batch_3 line 96, employer "longbow
    # partner", Austin 78775. Bio confirms Austin-based partner at Longbow.
    ('Perkins, Jennifer', 'Longbow Partners LLP (on behalf of Enterprise Products Partners LP)',
     'Partner / Registered Texas Lobbyist for O&G midstream client',
     'oil_gas_industry_association',
     'https://fminus.org/clients/longbow-consulting-partners-llc-dba-longbow-partners/',
     'F Minus / TEC filings: Perkins, Jennifer L. registered TX lobbyist for '
     'Enterprise Products Partners LP. Longbow bio confirms Austin partner '
     'since 2022. Practice areas include "produced water recycling" (oilfield '
     'wastewater). Donor address Austin 78775.'),
    ('Perkins, Jennifer', 'Longbow Partners LLP (on behalf of Targa Resources)',
     'Partner / Registered Texas Lobbyist for O&G midstream client',
     'oil_gas_industry_association',
     'https://fminus.org/clients/longbow-consulting-partners-llc-dba-longbow-partners/',
     'F Minus lists Perkins, Jennifer L. as registered TX lobbyist for Targa '
     'Resources (midstream natural gas processor).'),

    # Robert "Ben" Stratmann — Longbow Partners government affairs; registered
    # Texas lobbyist for Enterprise Products Partners LP. Donor "Stratmann,
    # Robert" $150 batch_3 line 93, employer "consultant", Austin 78757. Only
    # one Robert Stratmann working as consultant in Austin — his Longbow bio
    # lists "natural resources" as an expertise area.
    ('Stratmann, Robert', 'Longbow Partners LLP (on behalf of Enterprise Products Partners LP)',
     'Government Affairs / Registered Texas Lobbyist for O&G midstream client',
     'oil_gas_industry_association',
     'https://fminus.org/clients/longbow-consulting-partners-llc-dba-longbow-partners/',
     'F Minus / TEC: Stratmann, Robert Benjamin registered TX lobbyist for '
     'Enterprise Products Partners LP. Longbow bio (Austin) notes "natural '
     'resources" among expertise. Donor listed as "consultant" Austin 78757 '
     '— matches Longbow government-affairs role.'),
]

added = 0
for row in new:
    cur.execute(
        'INSERT OR IGNORE INTO civic_affiliations '
        '(canonical_name, organization, role, category, source_url, notes) '
        'VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount:
        added += 1
c.commit()
print(f'Added {added} Oil & Gas Velasquez findings')

# Show Velasquez contribution totals for flagged donors
print()
print('=== Velasquez donors with verified O&G industry ties ===')
cur.execute('''
    SELECT ca.canonical_name, ca.role,
           SUM(CAST(cf.contribution_amount AS REAL)) as vel_total
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name = ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE cf.recipient = 'Velasquez, Jose' AND cf.correction != 'X'
      AND ca.category LIKE 'oil_gas%'
    GROUP BY ca.canonical_name
    ORDER BY vel_total DESC
''')
for r in cur.fetchall():
    print(f'  {r[0]:<25} ${r[2]:>6,.0f} | {r[1][:80]}')
c.close()
