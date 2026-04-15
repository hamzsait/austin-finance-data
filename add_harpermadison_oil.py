"""Load Harper-Madison Oil & Gas findings.

Methodology: scanned harpermadison_batch_{1-5}.txt (641 donors $100+) for
employer-column hits on O&G industry (supermajors, independents, midstream,
oilfield services, refineries, TX O&G law/lobby firms, TXOGA, Permian
operators). Austin donor base skews heavily to real-estate (Endeavor Real
Estate Group, Pearlstone Partners, Riverside Resources — all verified as
NOT Endeavor Energy Resources / not O&G), engineering firms (Civilitude,
CobbFendley, Carollo — CobbFendley does some gas-pipeline work but no
specific donor flagged for O&G project staffing), and real-estate law
(Armbrust & Brown, Winstead — not O&G).

Ambiguous names WebSearch-verified and ruled out:
  - Cassidy, Brian ($400 batch_2 line 125, "attorney llp locke lord"):
    Managing Partner of Locke Lord Austin office. Firm has deep O&G/midstream
    practice (Kinder Morgan, Kinetik, WhiteWater Midstream, etc.) and Cassidy
    is a registered TX lobbyist (TEC id confirmed 2017-2023+), but his
    personal practice is administrative/regulatory law for TRANSPORTATION
    and UTILITY INFRASTRUCTURE (public-private partnerships, procurement —
    e.g. past-chair Real Estate Council of Austin). No public record of him
    representing O&G clients personally. Following Velasquez-file precedent
    (Castaneda / Baker Botts: firm-level O&G does not equal person-level
    O&G). Excluded.
  - Buoy, Kang ($350 batch_3 line 65, "afton chemical corporation processing"):
    Verified as Kang C. Buoy, Plant Manager / Supply Planning at Afton
    Chemical (NewMarket Corp subsidiary, Richmond VA HQ). Afton Chemical
    manufactures PETROLEUM ADDITIVES (fuel additives, engine oils, driveline
    fluids) sold into refineries and the fuel-distribution channel. Borderline
    — adjacent to refining but classified as SPECIALTY CHEMICALS, not an O&G
    producer/midstream/refiner per se. Buoy's role is operations engineering,
    not executive/board/lobbying. Scope excludes petroleum-adjacent chemical
    suppliers; excluded.
  - Getter, Kerry ($350 batch_3 line 71, "balcones ceo resources"): CEO of
    Balcones Resources = recycling / materials-recovery (top-50 North
    American recycler). NOT oil & gas. Excluded.
  - Gregory, Bob ($450 batch_1 line 86, "ceo disposal systems texas"): Texas
    Disposal Systems = solid-waste management (same ruled out for Velasquez).
    Excluded.
  - Claunch, Dave ($250 batch_4 line 30, "ceo liaison resources"): Liaison
    Creative + Marketing = Austin creative marketing firm (founder/CEO 1991);
    Claunch is also mayor of West Lake Hills. Not O&G. Excluded.
  - Arndt, Timothy ($261 batch_4 line 10, "360 energy mgr project savers"):
    360 Energy Savers LLC = Austin energy-efficiency / weatherization / HVAC
    contractor for Austin Energy rebate programs. Generic energy-efficiency,
    not fossil fuel. Excluded per scope.
  - Hawkins III, Albert ($350 batch_3 line 42, "albert consultant consulting
    hawkins policy public"): Former TX HHS Executive Commissioner (2003-09)
    now running Albert Hawkins Public Policy Consulting + Strategic Alliance
    Partner at Schlueter Group. Practice areas per firm bio are health &
    human-services policy, financing, operations — no O&G client disclosed.
    Excluded.
  - Shell, Kayla ($100 batch_4 line 134, "attorney dell"): Surname only
    (attorney at Dell Technologies). Excluded (not Shell Oil).
  - Warren, Chad ($106 batch_4 line 111, "205 events iatse local technician"):
    IATSE Local 205 stagehand. Not Kelcy Warren. Excluded.
  - CobbFendley donors (Khoury Sandra, Hastings-Dawkins Julie, Warth Dan,
    Hoff Scott): CobbFendley does do some oil/gas-pipeline engineering
    (upstream/midstream/downstream), but it's a large multi-practice firm
    (also transportation, water, surveying). These donors' titles are VP /
    EVP / senior engineer without documented O&G-specific practice. Excluded
    without individual-level evidence.
  - Carollo donors (Michael Hani, Hoff Scott second entry): Carollo Engineers
    = water/wastewater specialty firm. Not O&G. Excluded.
  - Paul, Nate ($350 batch_3 line 46, "ceo class holdings world"): Nate Paul
    / World Class Holdings = Austin real-estate investor (FBI-investigated).
    Real estate, not O&G.
  - Endeavor donors (~15 entries): all "Endeavor Real Estate Group" /
    "Endeavor Estate Group" = Austin commercial developer, NOT Endeavor
    Energy Resources (Midland-based Permian E&P). Per CLAUDE.md critical
    disambiguation. Excluded.
  - Riverside Resources donors (Lepore, Joseph, Maebius): Riverside Resources
    = Austin real estate (per Velasquez doc). Excluded.

Verified finds (2):
  - Gary Bagwell: president of Bagwell Co (Amarillo TX oil royalty trading
    firm since 1996; 5 employees; listed as operator on 2 active TX leases
    at thedrillings.com).
  - Anthony Precourt: managing partner of Precourt Capital Management
    (energy-sector family-office private-investment firm; inherited Precourt
    family O&G wealth — father Jay A. Precourt was Tejas Gas Corp CEO/Vice
    Chair 1986-99 and Halliburton/Apache board director).
"""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # Gary Bagwell — president of Bagwell Co, Amarillo TX oil royalty
    # trading firm (oil & gas mineral/royalty acquisition + trading since
    # 1996). Donor "Bagwell, Gary" $263 batch_4 line 7, employer "bagwell
    # company engineer", Amarillo 79101. Bagwell Co address 801 S Fillmore
    # St #630 Amarillo 79101 matches donor zip. Corporationwiki + D&B
    # confirm Gary D. Bagwell as president/primary contact. TheDrillings
    # shows Gary Bagwell of Amarillo TX as "operating rights" holder on
    # 2 authorized TX oil & gas leases. Small independent oil/royalty
    # operator — direct O&G industry role at executive level.
    ('Bagwell, Gary', 'Bagwell Co (Amarillo, TX)',
     'President / Oil & Gas Royalty Trader; TX mineral-rights lessee',
     'oil_gas_independent',
     'https://www.dandb.com/businessdirectory/bagwellco-amarillo-tx-15949344.html',
     'D&B profile: Bagwell Co has been "providing Oil Royalty Traders from '
     'Amarillo" since 1996; 5 employees, ~$508K annual revenue; Gary Bagwell '
     'listed as primary contact (president). Amarillo 79101 location '
     'matches donor address. TheDrillings.com lists Gary Bagwell of '
     'Amarillo TX as operating-rights holder on 2 active oil & gas leases. '
     'Donor occupation "bagwell company engineer" reflects his petroleum-'
     'engineer background running the royalty firm.'),

    # Anthony Precourt — managing partner of Precourt Capital Management,
    # a family-office private investment firm founded 2008 "focusing on
    # the energy sector" (per Wikipedia and secondary bios) with stated
    # targeting of oil, gas, and related industries. Donor "Precourt,
    # Anthony" $400 batch_2 line 59, employer "capital management manager
    # precourt", Austin 78746. Best known now as founder/CEO of Austin FC
    # (MLS), but his donor-listed occupation is Precourt Capital
    # (managing partner) and the firm remains his family-office vehicle.
    # Inherited O&G wealth: father Jay A. Precourt (d. 2024) was Vice
    # Chair/CEO of Tejas Gas Corp 1986-99 (sold to Shell 1997), founder/
    # director of ScissorTail Energy, Hamilton Oil, and longtime
    # Halliburton + Apache board director.
    ('Precourt, Anthony', 'Precourt Capital Management',
     'Managing Partner of energy-sector family-office investment firm',
     'oil_gas_independent',
     'https://en.wikipedia.org/wiki/Anthony_Precourt',
     'Wikipedia: Anthony Precourt "is a managing partner of Precourt '
     'Capital Management, a private investment management firm" which '
     'he "started... in 2008, focusing on the energy sector." Precourt '
     'family fortune from oil & gas — father Jay A. Precourt was Tejas '
     'Gas Corp CEO/Vice Chair, Hamilton Oil exec, and Halliburton + '
     'Apache board director. Anthony is Austin-based (donor zip 78746 '
     'Westlake Hills). Donor employer "capital management manager '
     'precourt" = Precourt Capital Management, managing partner role.'),
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
print(f'Added {added} Oil & Gas Harper-Madison findings')

# Show Harper-Madison contribution totals for flagged donors
print()
print('=== Harper-Madison donors with verified O&G industry ties ===')
cur.execute('''
    SELECT ca.canonical_name, ca.role,
           SUM(CAST(cf.contribution_amount AS REAL)) as hm_total
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name = ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE cf.recipient = 'Harper-Madison, Natasha' AND cf.correction != 'X'
      AND ca.category LIKE 'oil_gas%'
    GROUP BY ca.canonical_name
    ORDER BY hm_total DESC
''')
for r in cur.fetchall():
    print(f'  {r[0]:<25} ${r[2]:>6,.0f} | {r[1][:80]}')
c.close()
