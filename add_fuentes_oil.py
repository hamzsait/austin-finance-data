"""Load Fuentes Oil & Gas findings.

Methodology: scanned fuentes_batch_{1-5}.txt for O&G-industry employer strings
(supermajors, independents, midstream, oilfield services, refineries, TX O&G
law/lobby firms, TXOGA, Permian operators). Like the Velasquez donor base,
Fuentes's donors are dominated by Austin real estate (Endeavor Real Estate
Group — NOT Endeavor Energy Resources, the Permian E&P), Armbrust & Brown
(real estate law), Presidium / Riverside Resources (real estate), and
progressive legal/nonprofit donors. Ambiguous names were WebSearch-verified
and ruled out:

  - "Van Wilks" (batch_1 line 72, $450, occupation "muscian") = Austin blues
    guitarist, Texas Music Hall of Fame inductee. NOT one of the Wilks brothers
    (Farris/Dan) fracking billionaires.
  - "Bob Gregory / Kay Gregory / Adam Gregory" (Texas Disposal Systems) = solid
    waste / landfill / composting. NOT O&G (same ruling as Velasquez file).
  - "Danny Pena" (batch_4 line 148, $100, "cactus drilling motorman" San
    Angelo) = rig hand at Cactus Drilling (legit Permian drilling contractor),
    but rank-and-file worker, not executive/board/lobbying role per scope.
  - "Houston Terry" (batch_3 line 129, $200, "haliburton procurement" [sic])
    = procurement staffer at Halliburton, Houston. Individual contributor, not
    executive/board/lobbying role per scope.
  - "Edmund Lee" (batch_3 line 144, $200, "analyst engie sr trading" Houston)
    = Senior Natural Gas Scheduler/Analyst at ENGIE North America. ENGIE does
    have gas trading operations, but Lee is an individual-contributor analyst,
    not executive/board/lobbying role. Also ENGIE is primarily a renewables
    utility; gas trading is secondary.
  - "Cesar Leyva" (batch_4 line 124, $100, "attorney elkins llp vinson"
    Houston 77018) = associate at Vinson & Elkins Houston. V&E is the premier
    TX energy law firm, but Leyva appears as an associate on a solar energy
    deal (2018 Goldman Sachs $350M solar financing) — no public documentation
    ties him personally to a current specifically-O&G matter. Same standard as
    Velasquez file applied (Castaneda/Baker Botts was excluded for same
    reason). Associate-level, practice area not publicly confirmed as O&G.
  - "Jessica Huynh" (batch_5 line 36, "attorney smith vinson") = attorney at
    Smith & Vinson Law Firm (criminal defense), NOT Vinson & Elkins.
  - "LaRessa Quintana" (batch_3 line 57, Jackson Walker gov affairs) = ran
    Fuentes's own City Council campaign; Jackson Walker GR team (state/local
    advocacy, AISD trustee). Jackson Walker firm has an O&G practice but
    Quintana's role is general government relations with no public O&G client
    attribution. Same ruling as Castaneda/Velasquez precedent.
  - "Marc Rodriguez" (batch_2 line 140, "lobbyist Offices of Marc A Rodriguez"
    / Texas Lobby Partners) = TX contract lobbyist. Disclosed client list
    (Apple, CPS Energy muni utility, SAWS water, Texas Central rail, Las
    Vegas Sands, Maverick Co., etc.) contains no O&G / fossil-fuel clients.
  - "Greg Knaupe" (batch_3 line 72, "attorney gr knaupe lobbyist") — Austin
    lobbyist; no public O&G client registrations found.

Verified find (1): William "Bill" Miller, co-founder of HillCo Partners
(Austin). F Minus (sourced from Texas Ethics Commission) lists Miller as
registered TX lobbyist for Intercontinental Terminals Company, LLC (ITC) —
Deer Park/Pasadena TX bulk petroleum & petrochemical storage terminals (19M
barrels capacity; stores fuel oil, bunker oil, distillates, benzene, toluene,
xylene, methanol; serves "global petrochemical and petroleum markets"). ITC
is wholly owned by Mitsui & Co. and is core fossil-fuel midstream/storage
infrastructure — directly analogous to the Enterprise Products / Targa
midstream clients that caused Longbow lobbyists to be flagged in the
Velasquez file.

Note: F Minus also lists Miller as lobbyist for Summit Next Gen, LLC
(categorized "Fossil fuels"), but that company produces sustainable aviation
fuel (SAF) from ethanol feedstock — it is an alternative/biofuel project
displacing fossil jet fuel, not a fossil fuel producer itself. Not flagged,
per user's rule to exclude non-petroleum energy.
"""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # William "Bill" Miller — HillCo Partners co-founder, registered Texas
    # lobbyist for Intercontinental Terminals Company LLC (bulk petroleum /
    # petrochemical storage, Deer Park & Pasadena TX — 19M barrel capacity).
    # Donor "Miller, William" $450 batch_1 line 47, employer "consultant
    # hillco partners", Austin 78703 (HillCo HQ zip). Public face / co-founder
    # of HillCo per SourceWatch, Texas Monthly "25 Most Powerful People in
    # Texas" twice.
    ('Miller, William', 'HillCo Partners (on behalf of Intercontinental Terminals Company, LLC)',
     'Co-Founder / Registered Texas Lobbyist for O&G midstream-storage client',
     'oil_gas_industry_association',
     'https://fminus.org/lobbyists/miller-william-j/',
     'F Minus database (sourced from Texas Ethics Commission filings) lists '
     'William J. Miller at HillCo Partners as registered TX lobbyist for '
     'Intercontinental Terminals Company, LLC (ITC) — Mitsui-owned bulk '
     'petroleum/petrochemical storage terminals at Deer Park & Pasadena TX, '
     '19M barrels capacity, serving "global petrochemical and petroleum '
     'markets" (fuel oil, bunker oil, distillates, BTX, methanol). Midstream '
     'fossil-fuel storage infrastructure — directly analogous to the '
     'Enterprise Products / Targa midstream clients flagged in Velasquez '
     'file. Miller is HillCo co-founder (1998, with Buddy Jones); donor '
     'address Austin 78703 matches HillCo HQ.'),
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
print(f'Added {added} Oil & Gas Fuentes findings')

# Show Fuentes contribution totals for flagged donors
print()
print('=== Fuentes donors with verified O&G industry ties ===')
cur.execute('''
    SELECT ca.canonical_name, ca.role,
           SUM(CAST(cf.contribution_amount AS REAL)) as fue_total
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name = ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id = di.donor_id
    WHERE cf.recipient = 'Fuentes, Vanessa' AND cf.correction != 'X'
      AND ca.category LIKE 'oil_gas%'
    GROUP BY ca.canonical_name
    ORDER BY fue_total DESC
''')
for r in cur.fetchall():
    print(f'  {r[0]:<25} ${r[2]:>6,.0f} | {r[1][:80]}')
c.close()
