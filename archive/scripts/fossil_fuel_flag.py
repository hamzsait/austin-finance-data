"""
Fossil Fuel / Energy Industry Political Money Spectrum Tracker
===============================================================
Flags Austin campaign finance donors by their contributions to
fossil fuel and clean-energy FEC committees across the following
spectrum categories:

  FOSSIL FUEL SIDE
    - oil_gas_major        : Integrated majors (Exxon, Chevron, BP, Shell, etc.)
    - oil_gas_independent  : Independents / E&P / drillers / services
                             (Pioneer, Devon, EOG, Halliburton, Schlumberger, Hess, etc.)
    - oil_gas_midstream    : Pipelines & midstream (Energy Transfer, Enterprise Products,
                             Kinder Morgan, Williams Companies, Cheniere LNG, etc.)
    - coal                 : Coal producers (Peabody, Alliance Resource Partners, Westmoreland)
    - oil_lobbying         : Industry trade groups and fossil-fuel-aligned dark money
                             (API PAC, IPAA Wildcatters, Koch PAC, AFP Action, NOIA, etc.)

  CLIMATE / CLEAN ENERGY COUNTER-BALANCE
    - climate_action       : Climate and clean energy PACs (LCV, Sierra Club, NextGen,
                             Climate Hawks, EDF Action, Sunrise, Solar Energy Industries,
                             Climate Cabinet, Jane Fonda Climate PAC, etc.)

Writes results to:
  donor_identities.ff_spectrum, .ff_tier, .ff_total, .ff_committees
  fec_committee_cache.fossil_category

Also cross-references employer data to surface Austin donors who WORK at
fossil fuel companies (Phase 3), and reports Texas oil family name matches
(Phase 4).

Research notes & sources:
  - FEC.gov committee search: https://www.fec.gov/data/committees/
  - OpenSecrets PAC profiles:  https://www.opensecrets.org/
  - American Petroleum Institute PAC:     FEC C00483677
    https://www.fec.gov/data/committee/C00483677/
  - IPAA Wildcatters Fund:                FEC C00246306
    https://www.fec.gov/data/committee/C00246306/
  - ExxonMobil PAC:                       FEC C00121368
  - Chevron Employees PAC:                FEC C00035006
  - ConocoPhillips SPIRIT PAC:            FEC C00112896
  - Shell USA Employees PAWC:             FEC C00039503
  - BP North America PAC:                 FEC C00060103
  - Occidental Petroleum PAC:             FEC C00083857
  - Halliburton PAC (HALPAC):             FEC C00035691
  - Pioneer Natural Resources PAC:        FEC C00420950
  - Marathon Petroleum PAC:               FEC C00496307
  - Marathon Oil (MEPAC):                 FEC C00040568
  - Phillips 66 PAC:                      FEC C00513549
  - Valero Energy PAC:                    FEC C00109546
  - Devon Energy (DEC PAC):               FEC C00354753
  - Anadarko Petroleum PAC:               FEC C00231951
  - Hess PAC:                             FEC C00557322
  - Continental Resources PAC:            FEC C00551184
  - Murphy Oil PAC:                       FEC C00145722
  - Coterra Energy PAC:                   FEC C00486050
  - Expand Energy (fka Chesapeake):       FEC C00389288
  - Energy Transfer PAC:                  FEC C00438754
  - Enterprise Products Partners PAC:     FEC C00496752
  - Williams Companies PAC:               FEC C00040394
  - Cheniere Energy PAC:                  FEC C00430157
  - Kinder Morgan KMPAC:                  FEC C00779520
  - American Gas Association PAC:         FEC C00007450
  - ONE Gas PAC:                          FEC C00554444
  - United Gas Pipe Line PAC:             FEC C00228866
  - Liquid Energy Pipeline Assn PAC:      FEC C00486779
  - Columbia Pipeline Group PAC:          FEC C00575340
  - SIGMA (petrol marketers) PAC:         FEC C00120030
  - California Indep Petroleum Assn PAC:  FEC C00318766
  - Petroleum Alliance of Oklahoma PAC:   FEC C00444430
  - NOIA PAC (offshore):                  FEC C00409565
  - Peabody Energy PAC:                   FEC C00110478
  - Alliance Resource Partners PAC:       FEC C00330233
  - Westmoreland Coal PAC:                FEC C00246686
  - Koch PAC (KOCHPAC):                   FEC C00236489
  - AFP Action (Americans for Prosperity):FEC C00687103

  Climate / clean energy counter-balance:
  - League of Conservation Voters Action: FEC C00252940
    https://www.fec.gov/data/committee/C00252940/
  - LCV Victory Fund:                     FEC C00486845
  - LCV Environmental Voter Inc:          FEC C00094870
  - Sierra Club Political Committee:      FEC C00135368
  - NextGen Climate Action Committee:     FEC C00547349
  - Climate Hawks Vote:                   FEC C00548461
  - Climate Cabinet PAC:                  FEC C00735183
  - Bipartisan Climate Fund:              FEC C00774497
  - VoteClimate.US PAC:                   FEC C00551382
  - Jane Fonda Climate PAC:               FEC C00806893
  - EDF Action Votes:                     FEC C00707844
  - Sunrise PAC:                          FEC C00674697
  - Solar Energy Industries Assn PAC:     FEC C00421982

  NOTE: American Energy Alliance / Institute for Energy Research are
  501(c)(4) / 501(c)(3) entities not registered as FEC PACs, so they
  have no FEC committee ID. Heartland Institute is 501(c)(3) — same.
  TXOGA PAC is a Texas state PAC (Texas Ethics Commission filer),
  not an FEC committee; similarly Permian Basin Petroleum Assn,
  Texas Alliance of Energy Producers PAC, and Texans for Lawsuit
  Reform PAC are state-level and not in the FEC database.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "austin_finance.db")


# ── Committee Definitions ─────────────────────────────────────────────────
# Mapping: committee_id -> (fossil_category, ff_spectrum, display_name)
#   fossil_category : fine-grained bucket stored on fec_committee_cache
#   ff_spectrum     : coarse direction ("fossil_fuel" or "climate_action")

FOSSIL_COMMITTEES = {
    # ====================================================================
    # FOSSIL FUEL SIDE
    # ====================================================================

    # === Oil & Gas Majors (integrated) ===
    "C00121368": ("oil_gas_major",     "fossil_fuel", "ExxonMobil PAC"),
    "C00035006": ("oil_gas_major",     "fossil_fuel", "Chevron Employees PAC"),
    "C00112896": ("oil_gas_major",     "fossil_fuel", "ConocoPhillips SPIRIT PAC"),
    "C00039503": ("oil_gas_major",     "fossil_fuel", "Shell USA Employees' PAWC"),
    "C00060103": ("oil_gas_major",     "fossil_fuel", "BP North America PAC"),
    "C00083857": ("oil_gas_major",     "fossil_fuel", "Occidental Petroleum PAC"),
    "C00109546": ("oil_gas_major",     "fossil_fuel", "Valero Energy PAC"),
    "C00513549": ("oil_gas_major",     "fossil_fuel", "Phillips 66 PAC"),
    "C00496307": ("oil_gas_major",     "fossil_fuel", "Marathon Petroleum PAC"),

    # === Oil & Gas Independents / E&P / Oilfield Services ===
    "C00420950": ("oil_gas_independent", "fossil_fuel", "Pioneer Natural Resources PAC"),
    "C00354753": ("oil_gas_independent", "fossil_fuel", "Devon Energy DEC PAC"),
    "C00231951": ("oil_gas_independent", "fossil_fuel", "Anadarko Petroleum PAC"),
    "C00557322": ("oil_gas_independent", "fossil_fuel", "Hess Corporation PAC"),
    "C00551184": ("oil_gas_independent", "fossil_fuel", "Continental Resources PAC"),
    "C00145722": ("oil_gas_independent", "fossil_fuel", "Murphy Oil PAC"),
    "C00040568": ("oil_gas_independent", "fossil_fuel", "Marathon Oil (MEPAC)"),
    "C00486050": ("oil_gas_independent", "fossil_fuel", "Coterra Energy PAC"),
    "C00389288": ("oil_gas_independent", "fossil_fuel", "Expand Energy (fka Chesapeake) PAC"),
    "C00035691": ("oil_gas_independent", "fossil_fuel", "Halliburton PAC (HALPAC)"),

    # === Oil & Gas Midstream / Pipelines / LNG ===
    "C00438754": ("oil_gas_midstream", "fossil_fuel", "Energy Transfer PAC"),
    "C00496752": ("oil_gas_midstream", "fossil_fuel", "Enterprise Products Partners PAC"),
    "C00779520": ("oil_gas_midstream", "fossil_fuel", "Kinder Morgan KMPAC"),
    "C00040394": ("oil_gas_midstream", "fossil_fuel", "Williams Companies PAC"),
    "C00430157": ("oil_gas_midstream", "fossil_fuel", "Cheniere Energy PAC"),
    "C00228866": ("oil_gas_midstream", "fossil_fuel", "United Gas Pipe Line PAC"),
    "C00554444": ("oil_gas_midstream", "fossil_fuel", "ONE Gas PAC"),
    "C00486779": ("oil_gas_midstream", "fossil_fuel", "Liquid Energy Pipeline Assn PAC"),
    "C00575340": ("oil_gas_midstream", "fossil_fuel", "Columbia Pipeline Group PAC"),

    # === Coal ===
    "C00110478": ("coal", "fossil_fuel", "Peabody Energy PAC"),
    "C00330233": ("coal", "fossil_fuel", "Alliance Resource Partners PAC"),
    "C00246686": ("coal", "fossil_fuel", "Westmoreland Coal PAC"),

    # === Oil & Gas Lobbying / Industry Groups / Aligned Dark Money ===
    "C00483677": ("oil_lobbying", "fossil_fuel", "American Petroleum Institute PAC"),
    "C00246306": ("oil_lobbying", "fossil_fuel", "IPAA Wildcatters Fund"),
    "C00007450": ("oil_lobbying", "fossil_fuel", "American Gas Association PAC"),
    "C00409565": ("oil_lobbying", "fossil_fuel", "NOIA PAC (offshore)"),
    "C00444430": ("oil_lobbying", "fossil_fuel", "Petroleum Alliance of Oklahoma PAC"),
    "C00318766": ("oil_lobbying", "fossil_fuel", "California Indep Petroleum Assn PAC"),
    "C00120030": ("oil_lobbying", "fossil_fuel", "SIGMA (petroleum marketers) PAC"),
    "C00236489": ("oil_lobbying", "fossil_fuel", "KOCHPAC"),
    "C00687103": ("oil_lobbying", "fossil_fuel", "AFP Action (Americans for Prosperity)"),

    # ====================================================================
    # CLIMATE / CLEAN ENERGY COUNTER-BALANCE
    # ====================================================================
    "C00252940": ("climate_action", "climate_action", "League of Conservation Voters Action Fund"),
    "C00486845": ("climate_action", "climate_action", "LCV Victory Fund"),
    "C00094870": ("climate_action", "climate_action", "LCV Environmental Voter Inc"),
    "C00135368": ("climate_action", "climate_action", "Sierra Club Political Committee"),
    "C00547349": ("climate_action", "climate_action", "NextGen Climate Action Committee"),
    "C00548461": ("climate_action", "climate_action", "Climate Hawks Vote"),
    "C00735183": ("climate_action", "climate_action", "Climate Cabinet PAC"),
    "C00774497": ("climate_action", "climate_action", "Bipartisan Climate Fund"),
    "C00551382": ("climate_action", "climate_action", "VoteClimate.US PAC"),
    "C00806893": ("climate_action", "climate_action", "Jane Fonda Climate PAC"),
    "C00707844": ("climate_action", "climate_action", "EDF Action Votes"),
    "C00674697": ("climate_action", "climate_action", "Sunrise PAC"),
    "C00421982": ("climate_action", "climate_action", "Solar Energy Industries Assn PAC"),
}


# Cleaned, precise set of resolved_employer_display values representing
# fossil fuel / oil-and-gas employers found in the Austin donor pool.
# (Avoiding false positives like "Civitas Learning", "Coalition", "T-Mobile".)
FOSSIL_FUEL_EMPLOYERS = {
    # Majors
    "ExxonMobil", "Exxon Mobil", "Exxon",
    "Chevron",
    "ConocoPhillips", "Conocophillips", "Conocophillips Company",
    "Shell", "Shell Oil Company",
    "BP",
    "Occidental Petroleum",
    # Independents / oilfield services
    "Schlumberger",
    "Pioneer Natural Resources",
    "Fasken Oil and Ranch Ltd.",
    "Hammerhead Oil & Gas",
    "Venado Oil and Gas",
    "Middleton oil co",
    "Broaddus Petroleum",
    "LUCAS PETROLEUM GROUP",
    "Cactus Drilling",
    "Drilling Info",
    # Generic oil & gas self-identifications
    "Austin Oil & Gas",
    "Austin Consulting Petroleum Engineers",
    "Oil & Gas",
    "Oil & Gas Geologist",
    "Oil & Gas Investments",
    "Oil & Gas Production",
    "Oil & Gas Services",
    "Oil & gas accountant",
    "PGH Environmental & Petroleum Engineers",
    "Petroleum Engineer",
    "Petroleum Landman",
    "RFR Texas Petroleum",
    "Sole Proprieter/Petroleum Engineer",
    # Midstream / pipelines / utilities gas
    "DT Midstream",
    "Texas Gas Service",
    "Texas Pipeline Association",
    "Plains Pipeline, LP",
    "Pipeline Marketing",
    "US Pipeline, Inc.",
}

# Texas oil family / figure name patterns (Phase 4)
TEXAS_OIL_FIGURES = [
    ("Wilks",           "Farris/Dan Wilks - frac sand billionaires"),
    ("Rees-Jones",      "Trevor Rees-Jones - Chief Oil & Gas"),
    ("Rees Jones",      "Trevor Rees-Jones - Chief Oil & Gas"),
    ("Tim Dunn",        "Tim Dunn - CrownQuest Operating"),
    ("Dunn, Timothy",   "Tim Dunn - CrownQuest Operating"),
    ("Kelcy Warren",    "Kelcy Warren - Energy Transfer Partners"),
    ("Warren, Kelcy",   "Kelcy Warren - Energy Transfer Partners"),
    ("Harold Hamm",     "Harold Hamm - Continental Resources"),
    ("Hamm, Harold",    "Harold Hamm - Continental Resources"),
]


# ── Schema migration ──────────────────────────────────────────────────────

def add_columns(conn):
    """Add ff_* columns to donor_identities and fossil_category to committee cache."""
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(donor_identities)")
    existing = {row[1] for row in cur.fetchall()}
    new_cols = [
        ("ff_spectrum",   "TEXT"),
        ("ff_tier",       "INTEGER"),
        ("ff_total",      "REAL DEFAULT 0"),
        ("ff_committees", "TEXT"),
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing:
            cur.execute(f"ALTER TABLE donor_identities ADD COLUMN {col_name} {col_type}")
            print(f"  Added donor_identities.{col_name}")
        else:
            print(f"  Column donor_identities.{col_name} already exists")

    cur.execute("PRAGMA table_info(fec_committee_cache)")
    existing_cc = {row[1] for row in cur.fetchall()}
    if "fossil_category" not in existing_cc:
        cur.execute("ALTER TABLE fec_committee_cache ADD COLUMN fossil_category TEXT")
        print("  Added fec_committee_cache.fossil_category")
    else:
        print("  Column fec_committee_cache.fossil_category already exists")

    conn.commit()


def flag_committees(conn):
    """Set fossil_category on fec_committee_cache for known fossil/climate committees."""
    cur = conn.cursor()
    cur.execute("UPDATE fec_committee_cache SET fossil_category = NULL")
    flagged = 0
    missing = 0
    for cid, (category, _spec, name) in FOSSIL_COMMITTEES.items():
        cur.execute(
            "UPDATE fec_committee_cache SET fossil_category = ? WHERE committee_id = ?",
            (category, cid),
        )
        if cur.rowcount > 0:
            print(f"  Flagged {cid} ({name[:45]}) -> {category}")
            flagged += 1
        else:
            print(f"  -- {cid} ({name[:45]}) not in cache")
            missing += 1
    conn.commit()
    print(f"  Total committees flagged in cache: {flagged}  (missing: {missing})")


# ── Donor scoring ─────────────────────────────────────────────────────────

def score_donors(conn):
    """Score every donor based on their FEC contributions to fossil/climate committees."""
    cur = conn.cursor()

    cur.execute("""
        UPDATE donor_identities
        SET ff_spectrum = NULL, ff_tier = NULL, ff_total = 0, ff_committees = NULL
    """)

    cid_list = list(FOSSIL_COMMITTEES.keys())
    placeholders = ",".join(["?"] * len(cid_list))

    cur.execute(f"""
        SELECT
            r.donor_id,
            r.committee_id,
            SUM(r.contribution_amount) AS total_to_committee
        FROM fec_contributions_raw r
        WHERE r.committee_id IN ({placeholders})
        GROUP BY r.donor_id, r.committee_id
    """, cid_list)

    donor_data = {}
    for donor_id, committee_id, total in cur.fetchall():
        if donor_id not in donor_data:
            donor_data[donor_id] = {
                "fossil_fuel": 0.0,
                "climate_action": 0.0,
                "committees": set(),
                "categories": set(),
                "total": 0.0,
            }
        category, spectrum, _ = FOSSIL_COMMITTEES[committee_id]
        donor_data[donor_id][spectrum] += total
        donor_data[donor_id]["committees"].add(committee_id)
        donor_data[donor_id]["categories"].add(category)
        donor_data[donor_id]["total"] += total

    print(f"\n  Found {len(donor_data)} donors with fossil/climate committee contributions")

    # Tier definition (parallels IP spectrum):
    #   Tier 1 = direct industry giving AND (3+ committees OR gave to a major integrated oil PAC)
    #   Tier 2 = multi-PAC (2+ committees) OR single major-integrated PAC
    #   Tier 3 = single committee, not a major
    major_integrated = {cid for cid, v in FOSSIL_COMMITTEES.items() if v[0] == "oil_gas_major"}

    updated = 0
    for donor_id, data in donor_data.items():
        # Spectrum: whichever side received more $
        spectrum = "fossil_fuel" if data["fossil_fuel"] >= data["climate_action"] else "climate_action"

        committees = data["committees"]
        n = len(committees)
        hit_major = bool(committees & major_integrated)

        if n >= 3 or (hit_major and n >= 2):
            tier = 1
        elif n >= 2 or hit_major:
            tier = 2
        else:
            tier = 3

        committee_str = ",".join(sorted(committees))

        cur.execute("""
            UPDATE donor_identities
            SET ff_spectrum = ?, ff_tier = ?, ff_total = ?, ff_committees = ?
            WHERE donor_id = ?
        """, (spectrum, tier, data["total"], committee_str, donor_id))
        updated += cur.rowcount

    conn.commit()
    print(f"  Updated {updated} donor records with fossil fuel spectrum scores")
    return donor_data


# ── Reports ───────────────────────────────────────────────────────────────

def report_summary(conn):
    cur = conn.cursor()

    print("\n" + "=" * 72)
    print("FOSSIL FUEL / CLEAN ENERGY SPECTRUM — DB-WIDE SUMMARY")
    print("=" * 72)

    # Category-level breakdown (using fine-grained fossil_category via committees)
    cid_list = list(FOSSIL_COMMITTEES.keys())
    placeholders = ",".join(["?"] * len(cid_list))

    cur.execute(f"""
        SELECT cc.fossil_category,
               COUNT(DISTINCT r.donor_id) AS donors,
               COUNT(*) AS n_contribs,
               SUM(r.contribution_amount) AS total
        FROM fec_contributions_raw r
        JOIN fec_committee_cache cc ON cc.committee_id = r.committee_id
        WHERE cc.fossil_category IS NOT NULL
        GROUP BY cc.fossil_category
        ORDER BY total DESC
    """)
    print(f"\n{'Category':<22} {'Donors':>8} {'Contribs':>10} {'Total $':>16}")
    print("-" * 60)
    for row in cur.fetchall():
        cat = row[0] or "(none)"
        print(f"{cat:<22} {row[1]:>8,} {row[2]:>10,} {row[3]:>16,.2f}")

    # Spectrum-level (fossil_fuel vs climate_action) from donor_identities
    cur.execute("""
        SELECT ff_spectrum, COUNT(*), SUM(ff_total), AVG(ff_total)
        FROM donor_identities
        WHERE ff_spectrum IS NOT NULL
        GROUP BY ff_spectrum
        ORDER BY SUM(ff_total) DESC
    """)
    print(f"\n{'Spectrum':<20} {'Donors':>8} {'Total $':>16} {'Avg $':>12}")
    print("-" * 60)
    for row in cur.fetchall():
        print(f"{row[0]:<20} {row[1]:>8,} {row[2]:>16,.2f} {row[3]:>12,.2f}")

    # Tier breakdown
    cur.execute("""
        SELECT ff_tier, COUNT(*), SUM(ff_total)
        FROM donor_identities
        WHERE ff_spectrum IS NOT NULL
        GROUP BY ff_tier
        ORDER BY ff_tier
    """)
    print(f"\n{'Tier':<40} {'Donors':>8} {'Total $':>16}")
    print("-" * 68)
    tier_labels = {
        1: "Tier 1 (3+ cmtes or major + multi)",
        2: "Tier 2 (2+ cmtes or any major)",
        3: "Tier 3 (single non-major PAC)",
    }
    for row in cur.fetchall():
        label = tier_labels.get(row[0], f"Tier {row[0]}")
        print(f"{label:<40} {row[1]:>8,} {row[2]:>16,.2f}")

    # Top donors per spectrum
    for spectrum in ["fossil_fuel", "climate_action"]:
        cur.execute("""
            SELECT canonical_name, canonical_employer, ff_total, ff_tier, ff_committees
            FROM donor_identities
            WHERE ff_spectrum = ?
            ORDER BY ff_total DESC
            LIMIT 10
        """, (spectrum,))
        rows = cur.fetchall()
        if rows:
            print(f"\n--- Top 10 donors: {spectrum.upper()} ---")
            print(f"{'Name':<30} {'Employer':<28} {'FF $':>10} {'Tier':>4}  Committees")
            print("-" * 110)
            for r in rows:
                cids = r[4].split(",") if r[4] else []
                cnames = [FOSSIL_COMMITTEES[c][2][:22] for c in cids if c in FOSSIL_COMMITTEES]
                print(f"{(r[0] or 'N/A')[:29]:<30} {(r[1] or '')[:27]:<28} "
                      f"{r[2] or 0:>10,.2f} {r[3] or 0:>4}  {', '.join(cnames)}")


def report_qadri(conn):
    cur = conn.cursor()

    print("\n" + "=" * 72)
    print("QADRI DONOR FOSSIL FUEL SPECTRUM REPORT")
    print("=" * 72)

    # Qadri donors, showing both local gift and ff totals
    cur.execute("""
        SELECT
            di.canonical_name,
            di.canonical_employer,
            SUM(CAST(cf.contribution_amount AS REAL)) AS local_total,
            di.ff_spectrum,
            di.ff_tier,
            di.ff_total,
            di.ff_committees
        FROM campaign_finance cf
        JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE cf.recipient = 'Qadri, Zohaib'
          AND (cf.correction IS NULL OR cf.correction = '')
        GROUP BY di.donor_id, di.canonical_name, di.canonical_employer,
                 di.ff_spectrum, di.ff_tier, di.ff_total, di.ff_committees
        ORDER BY di.ff_total DESC NULLS LAST, local_total DESC
    """)
    rows = cur.fetchall()

    ff_donors = [r for r in rows if r[3] is not None]
    print(f"\nTotal unique Qadri donors: {len(rows)}")
    print(f"Qadri donors flagged on fossil/climate spectrum: {len(ff_donors)}")

    if ff_donors:
        print(f"\n{'Name':<25} {'Employer':<25} {'Local $':>9} {'Spectrum':<15} "
              f"{'Tier':>4} {'FF $':>10}  Committees")
        print("-" * 130)
        for r in ff_donors:
            cids = r[6].split(",") if r[6] else []
            cnames = [FOSSIL_COMMITTEES[c][2][:20] for c in cids if c in FOSSIL_COMMITTEES]
            print(f"{(r[0] or 'N/A')[:24]:<25} "
                  f"{(r[1] or '')[:24]:<25} "
                  f"{r[2] or 0:>9,.2f} "
                  f"{(r[3] or 'N/A'):<15} "
                  f"{r[4] or 0:>4} "
                  f"{r[5] or 0:>10,.2f}  "
                  f"{', '.join(cnames)}")

    # Spectrum cross-tab for Qadri
    cur.execute("""
        SELECT COALESCE(di.ff_spectrum, 'no_ff_activity') AS spectrum,
               COUNT(DISTINCT di.donor_id) AS n_donors,
               SUM(CAST(cf.contribution_amount AS REAL)) AS local_total
        FROM campaign_finance cf
        JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE cf.recipient = 'Qadri, Zohaib'
          AND (cf.correction IS NULL OR cf.correction = '')
        GROUP BY COALESCE(di.ff_spectrum, 'no_ff_activity')
        ORDER BY local_total DESC
    """)
    print("\n--- Qadri donors by fossil/climate spectrum ---")
    print(f"{'Spectrum':<20} {'Donors':>8} {'Local $ to Qadri':>20}")
    print("-" * 52)
    for r in cur.fetchall():
        print(f"{r[0]:<20} {r[1]:>8,} {(r[2] or 0):>20,.2f}")

    # Fine-grained Qadri category report
    cur.execute(f"""
        SELECT cc.fossil_category,
               COUNT(DISTINCT di.donor_id) AS donors,
               SUM(r.contribution_amount) AS ff_total
        FROM campaign_finance cf
        JOIN donor_identities di ON cf.donor_id = di.donor_id
        JOIN fec_contributions_raw r ON r.donor_id = di.donor_id
        JOIN fec_committee_cache cc  ON cc.committee_id = r.committee_id
        WHERE cf.recipient = 'Qadri, Zohaib'
          AND (cf.correction IS NULL OR cf.correction = '')
          AND cc.fossil_category IS NOT NULL
        GROUP BY cc.fossil_category
        ORDER BY ff_total DESC
    """)
    rows = cur.fetchall()
    if rows:
        print("\n--- Qadri donors' FF giving by fine-grained category ---")
        print(f"{'Category':<22} {'Donors':>8} {'Cmte $':>14}")
        print("-" * 46)
        for r in rows:
            print(f"{r[0]:<22} {r[1]:>8,} {r[2] or 0:>14,.2f}")


# ── Phase 3: Employer cross-reference ─────────────────────────────────────

def report_employer_matches(conn):
    cur = conn.cursor()

    print("\n" + "=" * 72)
    print("PHASE 3: AUSTIN DONORS EMPLOYED BY FOSSIL FUEL COMPANIES")
    print("=" * 72)

    placeholders = ",".join(["?"] * len(FOSSIL_FUEL_EMPLOYERS))
    emp_list = list(FOSSIL_FUEL_EMPLOYERS)

    cur.execute(f"""
        SELECT canonical_name, resolved_employer_display, canonical_employer,
               total_donated, ff_spectrum, ff_tier, ff_total
        FROM donor_identities
        WHERE resolved_employer_display IN ({placeholders})
        ORDER BY total_donated DESC
    """, emp_list)
    rows = cur.fetchall()

    print(f"\nDonors with fossil fuel employer match: {len(rows)}")
    if rows:
        print(f"\n{'Name':<28} {'Employer':<30} {'Local $':>10} {'FF Spectrum':<15} {'FF Tier':>7} {'FF $':>10}")
        print("-" * 108)
        for r in rows:
            print(f"{(r[0] or 'N/A')[:27]:<28} "
                  f"{(r[1] or '')[:29]:<30} "
                  f"{r[3] or 0:>10,.2f} "
                  f"{(r[4] or '-'):<15} "
                  f"{(str(r[5]) if r[5] else '-'):>7} "
                  f"{r[6] or 0:>10,.2f}")

    # By employer count
    cur.execute(f"""
        SELECT resolved_employer_display,
               COUNT(DISTINCT donor_id) AS donors,
               SUM(total_donated) AS local_total
        FROM donor_identities
        WHERE resolved_employer_display IN ({placeholders})
        GROUP BY resolved_employer_display
        ORDER BY local_total DESC
    """, emp_list)
    print("\n--- By employer ---")
    print(f"{'Employer':<36} {'Donors':>8} {'Local $ total':>16}")
    print("-" * 64)
    for r in cur.fetchall():
        print(f"{(r[0] or '')[:35]:<36} {r[1]:>8,} {r[2] or 0:>16,.2f}")

    # Qadri overlap: fossil-employed donors who gave to Qadri
    cur.execute(f"""
        SELECT di.canonical_name, di.resolved_employer_display,
               SUM(CAST(cf.contribution_amount AS REAL)) AS qadri_given,
               di.ff_spectrum, di.ff_total
        FROM campaign_finance cf
        JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE cf.recipient = 'Qadri, Zohaib'
          AND (cf.correction IS NULL OR cf.correction = '')
          AND di.resolved_employer_display IN ({placeholders})
        GROUP BY di.donor_id
        ORDER BY qadri_given DESC
    """, emp_list)
    rows = cur.fetchall()
    print(f"\n--- Qadri donors whose employer is a fossil fuel company: {len(rows)} ---")
    if rows:
        print(f"{'Name':<28} {'Employer':<30} {'$ to Qadri':>11} {'FF Spectrum':<14} {'FF $':>10}")
        print("-" * 100)
        for r in rows:
            print(f"{(r[0] or 'N/A')[:27]:<28} "
                  f"{(r[1] or '')[:29]:<30} "
                  f"{r[2] or 0:>11,.2f} "
                  f"{(r[3] or '-'):<14} "
                  f"{r[4] or 0:>10,.2f}")


# ── Phase 4: Texas oil family / figure lookup ─────────────────────────────

def report_texas_oil_figures(conn):
    cur = conn.cursor()
    print("\n" + "=" * 72)
    print("PHASE 4: TEXAS OIL FAMILY / FIGURE NAME CHECK")
    print("=" * 72)

    any_found = False
    for pat, desc in TEXAS_OIL_FIGURES:
        cur.execute("""
            SELECT canonical_name, canonical_employer, total_donated, fec_total_donations
            FROM donor_identities
            WHERE UPPER(canonical_name) LIKE ?
        """, ("%" + pat.upper() + "%",))
        rows = cur.fetchall()
        if rows:
            # Filter plausible matches — warn if employer looks unrelated
            plausible = [r for r in rows if r[1] and any(k in (r[1] or "").lower() for k in
                ["oil", "gas", "petroleum", "energy", "drilling", "resources", "midstream"])]
            print(f"\n  {pat}  -- {desc}")
            for r in rows:
                plaus = "PLAUSIBLE" if r in plausible else "unlikely (employer mismatch)"
                print(f"    {r[0]:<30}  emp='{(r[1] or '')[:30]}'  "
                      f"local=${r[2] or 0:,.0f}  fec_n={r[3] or 0}  [{plaus}]")
            any_found = True

    if not any_found:
        print("\n  No matches found for any Texas oil family / figure name pattern.")
        print("  (As expected — these mega-donors give to federal/state races, not to")
        print("   Austin City Council, and do not reside within Austin city limits.)")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    print("=" * 72)
    print("STEP 1: Adding columns")
    print("=" * 72)
    add_columns(conn)

    print("\n" + "=" * 72)
    print("STEP 2: Flagging fossil/climate committees in fec_committee_cache")
    print("=" * 72)
    flag_committees(conn)

    print("\n" + "=" * 72)
    print("STEP 3: Scoring donors on fossil/climate spectrum")
    print("=" * 72)
    score_donors(conn)

    print("\n" + "=" * 72)
    print("STEP 4: Summary report")
    print("=" * 72)
    report_summary(conn)

    report_qadri(conn)
    report_employer_matches(conn)
    report_texas_oil_figures(conn)

    conn.close()
    print("\n\nDone. Fossil fuel spectrum data written to austin_finance.db.")


if __name__ == "__main__":
    main()
