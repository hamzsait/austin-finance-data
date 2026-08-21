"""
Classify the remaining 431 unclassified employer_identities entries
found in Qadri's donor pool.
"""
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# First, get the self-employed and not-employed employer_ids
cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name='Self-Employed'")
self_emp_id = cur.fetchone()[0]
cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name='Not Employed'")
not_emp_id = cur.fetchone()[0]

# ── 1. Personal names / job titles → Individual (not-employed category) ──────
# These are people who listed their own name or job title as employer
PERSONAL_NAMES_AND_TITLES = [
    "Tamer Barazi", "Sami Khaleeq", "Michelle Skupin", "Meredith Hull",
    "Christina Black", "Brita wallace", "Greg Gonzalez", "Pete Gilcrease",
    "Luke Warford", "Winston O'Neal", "Shenghao Wang", "Justin Phillips",
    "Junaid Ikram", "Greg Casar for Congress", "Annick Beaudet",
    "Sophia Mirto", "Asif Cochinwala", "Parissa", "Zohaib Qadri",
    "Dave Pantos Esq. LLC", "May Matson Taylor Ph.D. Psychologist",
    "Irfan R. Qureshi MD PA", "Audrey Nath MD PLLC",
    # Job titles
    "Design Manager", "Critical Products Manager", "Regional Administrator",
    "Higher Education Policy Analyst", "Teaching Assistant",
    # Ambiguous single-word
    "Company", "Employed", "Nonprofit", "Finance", "RE", "GC", "IV",
    "WF", "PH", "MS", "LV", "QP", "FGC", "IDM", "LPC", "COJ", "COSA",
    "TFN", "VCU", "NYU", "UNT", "ISD",
]

# Redirect these to not-employed category (they're individuals, not employers)
for name in PERSONAL_NAMES_AND_TITLES:
    # Set industry but DON'T change employer_id links - just classify the entry
    cur.execute("""
        UPDATE employer_identities SET industry='Individual', interest_tags='not-employed'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 2. Self-employed variants missed by Phase 1 ──────────────────────────────
SELF_EMP_VARIANTS = [
    "Freelance/self-employed", "Self Employed / Consultant & Partner",
    "Independent", "Sole Proprietor",
]
for name in SELF_EMP_VARIANTS:
    cur.execute("""
        UPDATE employer_identities SET industry='Individual', interest_tags='self-employed'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# Also wire campaign_finance records for these variants to self_emp_id
SELF_EMP_RAW_MISSED = [
    "(Self Employed)", "freelance/self-employed", "self employed / consultant & partner",
    "Myself",
]
wired_self = 0
for raw in SELF_EMP_RAW_MISSED:
    cur.execute("""
        UPDATE campaign_finance SET employer_id=?
        WHERE employer_id IS NULL
          AND LOWER(TRIM(COALESCE(donor_reported_employer,''))) = LOWER(?)
    """, (self_emp_id, raw))
    wired_self += cur.rowcount
    # Also try exact match
    cur.execute("""
        UPDATE campaign_finance SET employer_id=?
        WHERE employer_id IS NULL
          AND TRIM(donor_reported_employer) = ?
    """, (self_emp_id, raw))
    wired_self += cur.rowcount

# ── 3. Technology companies ───────────────────────────────────────────────────
TECH = [
    ("latakoo",                 "tech-startup-ecosystem"),
    ("DRONIZE",                 "tech-startup-ecosystem"),
    ("Cornerstone on demand",   "tech-startup-ecosystem"),
    ("Embrace.ai",              "tech-startup-ecosystem"),
    ("Dialpad",                 "tech-startup-ecosystem"),
    ("Waymo",                   "tech-startup-ecosystem"),
    ("Airtable",                "tech-startup-ecosystem"),
    ("Canva",                   "tech-startup-ecosystem"),
    ("GitLab",                  "tech-startup-ecosystem"),
    ("Alteryx",                 "tech-startup-ecosystem"),
    ("Samsara",                 "tech-startup-ecosystem"),
    ("Argo AI",                 "tech-startup-ecosystem"),
    ("Tudu",                    "tech-startup-ecosystem"),
    ("Manifold",                "tech-startup-ecosystem"),
    ("CareerPlug",              "tech-startup-ecosystem"),
    ("DEX AI",                  "tech-startup-ecosystem"),
    ("Daylight Labs Inc",       "tech-startup-ecosystem"),
    ("Remagine Labs",           "tech-startup-ecosystem"),
    ("Datafiniti",              "tech-startup-ecosystem"),
    ("ChannelFore",             "tech-startup-ecosystem"),
    ("Buurst",                  "tech-startup-ecosystem"),
    ("Alchemer",                "tech-startup-ecosystem"),
    ("Frequence",               "tech-startup-ecosystem"),
    ("Sprinklr",                "tech-startup-ecosystem"),
    ("Celtra",                  "tech-startup-ecosystem"),
    ("OneTrust",                "tech-startup-ecosystem"),
    ("Performio",               "tech-startup-ecosystem"),
    ("Grassroots Analytics",    "tech-startup-ecosystem"),
    ("YouGov Blue",             "tech-startup-ecosystem"),
    ("smartDigs Austin",        "tech-startup-ecosystem"),
    ("joinunified.us",          "tech-startup-ecosystem"),
    ("AdQuick",                 "tech-startup-ecosystem"),
    ("Comdata",                 None),
    ("Comcast",                 None),
    ("Verizon",                 None),
    ("Volkswagen Group of America", None),   # Auto → Technology
    ("Joby Aviation",           "tech-startup-ecosystem"),
    ("SK Infotech",             None),
    ("Vectra AI",               "tech-startup-ecosystem"),
    ("Babylon",                 "tech-startup-ecosystem"),
    ("Teladoc",                 None),
    ("WebPT Inc.",              "tech-startup-ecosystem"),
    ("Optimum",                 None),
    ("Titan",                   None),
    ("AmC Company",             None),
    ("Knime",                   "tech-startup-ecosystem"),
    ("Aledade",                 "tech-startup-ecosystem"),
    ("Cloudera",                "tech-startup-ecosystem"),
    ("Ebay",                    None),
    ("Tawkify",                 "tech-startup-ecosystem"),
    ("Talem",                   "tech-startup-ecosystem"),
    ("AllSource PPS",           None),
    ("Blueprint Interactive",   "tech-startup-ecosystem"),
    ("Purifyou",                "tech-startup-ecosystem"),
    ("Unified",                 "tech-startup-ecosystem"),
    ("Branch",                  "tech-startup-ecosystem"),
    ("Aimbest ins svcs",        None),
    ("Schneider electric",      None),
    ("Hitachi Vantara",         None),
    ("Bose Professional",       None),
    ("Middle Seat",             "political-consulting"),
    ("SAS",                     None),
]
for name, tags in TECH:
    cur.execute("""
        UPDATE employer_identities SET industry='Technology', interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (tags, name))

# ── 4. Healthcare ─────────────────────────────────────────────────────────────
HEALTH = [
    "Embracia Health", "Vital Foot & Ankle", "One Step Diagnostic",
    "DetoxPRo", "Kelsey Seybold", "Orlando Health", "Jersey heart center",
    "Jackson and coker", "Merck", "Lockheed Martin",  # LM has health div
    "Capital Health", "Dr Eric Tiblier PA", "DR ERIC TIBLIER PA",
    "ERIC TIBLIER MD PA", "Audrey Nath MD PLLC", "Austin Palliative Care",
    "Vital Farms",  # food/health
    "Joni K Wallace DDS", "JPS", "MDA", "Kelsey Seybold", "TCH",
    "UCSF", "Sugar land internal medicine", "Sonic Reference Laboratory",
    "TX DX Center", "DHCS", "Texas endovascular", "OACT",
]
for name in HEALTH:
    cur.execute("""
        UPDATE employer_identities SET industry='Healthcare'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 5. Finance / Investment ───────────────────────────────────────────────────
FINANCE = [
    ("True insurance solutions",    None),
    ("FBRMgmt",                     "real-estate-development"),
    ("Turnbridge Equities",         "real-estate-development"),
    ("Club Capital",                None),
    ("Wolfe Capital",               None),
    ("Tristan Ventures",            "tech-startup-ecosystem"),
    ("Fiducial business centers",   None),
    ("KPMG",                        None),
    ("Goldman Sachs",               None),
    ("EY",                          None),
    ("BDO",                         None),
    ("Marsh USA",                   None),
    ("New York Life Insurance",     None),
    ("American Modern",             None),
    ("Professional liability insurance services inc", None),
    ("SLB",                         "energy-mineral-rights"),  # Schlumberger
    ("Valerity",                    "real-estate-development"),
    ("Homstrom Holdings LLC",       "real-estate-development"),
    ("Delve Residential Inc",       "real-estate-development"),
    ("Nicholas Residential",        "real-estate-development"),
    ("Isthmus Peak",                "real-estate-development"),
    ("Explore Ranches",             "real-estate-development"),
    ("FRB",                         None),   # Federal Reserve Bank
    ("American Payroll Association", None),
    ("Nationwide",                  None),
    ("Longevity Partners",          None),
]
for name, tags in FINANCE:
    cur.execute("""
        UPDATE employer_identities SET industry='Finance', interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (tags, name))

# ── 6. Real Estate ────────────────────────────────────────────────────────────
REAL_ESTATE = [
    "ColinaWest", "Zeenit Development", "Pearlstonepartners",
    "FBRMgmt", "Delve Residential Inc", "Nicholas Residential",
    "Isthmus Peak", "Homstrom Holdings LLC", "Douglas elliman",
    "AMC Design Group Inc.", "smartDigs Austin", "AusBos Social Housing",
    "Stravaro LLC",
]
for name in REAL_ESTATE:
    cur.execute("""
        UPDATE employer_identities SET industry='Real Estate', interest_tags='real-estate-development'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 7. Legal ──────────────────────────────────────────────────────────────────
LEGAL = [
    "Abraham Watkins Nichols Agosto Aziz & Stogner",
    "Okoro Law PLLC", "Patton Boggs", "Latham & Watkins LLP",
    "McDermott Will & Emery", "Sheppard Mullin", "Maynard Nexsen",
    "Parker Hudson", "Joseph S. Jaworski P.C.", "Daniel Stark",
    "Goodwin & Goodwin", "Mathews & Freeland", "Dave Pantos Esq. LLC",
    "Law offices of Omar khawaja pllcp", "Alfred Stanley & Associates",
    "Irfan R. Qureshi MD PA",
]
for name in LEGAL:
    cur.execute("""
        UPDATE employer_identities SET industry='Legal'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 8. Education ──────────────────────────────────────────────────────────────
EDUCATION = [
    ("UH",          "higher-education"),   # Univ of Houston
    ("UTH",         "higher-education"),   # UT Health
    ("UTexas",      "higher-education"),
    ("Harvard",     "higher-education"),
    ("NYU",         "higher-education"),
    ("UCSF",        "higher-education"),
    ("VCU",         "higher-education"),
    ("UNT",         "higher-education"),
    ("MSU Denver",  "higher-education"),
    ("Texas Legislative Council", None),
    ("IDEA Public Schools",       None),
    ("Harmony Public Schools",    None),
    ("Griffin School",            None),
    ("TX Ed Partners",            None),
    ("Raise Your Hand Texas",     None),
    ("kla school of sweetwater",  None),
    ("Harry Ransom Center",       "higher-education"),
    ("Academic Programs International", "higher-education"),
    ("The Annette Strauss Institute",   None),
    ("Lindamood Bell",            None),
    ("Texas A&M Forest Service",  "higher-education"),
]
for name, tags in EDUCATION:
    cur.execute("""
        UPDATE employer_identities SET industry='Education', interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (tags, name))

# ── 9. Nonprofit ──────────────────────────────────────────────────────────────
NONPROFITS = [
    # Progressive/advocacy
    ("Capital A",                       "progressive-money"),
    ("Cap A Housing",                   "progressive-money"),
    ("Captial A",                       "progressive-money"),   # typo variant
    ("Cap A",                           "progressive-money"),
    ("Texas House Democratic Caucus",   "progressive-money"),
    ("Texas Blue Action",               "progressive-money"),
    ("House Democratic Caucus",         "progressive-money"),
    ("Democratic National Committee",   "progressive-money"),
    ("New Jersey State Democratic Committee", "progressive-money"),
    ("Run For Something Texas",         "progressive-money"),
    ("Our Fight Our Future PAC",        "progressive-money"),
    ("Our Revolution Texas",            "progressive-money"),
    ("Texas Gun Sense",                 "progressive-money"),
    ("Jolt Action",                     "progressive-money"),
    ("MOVE Texas Action Fund",          "progressive-money"),
    ("Fair Elections Center",           "progressive-money"),
    ("Fair Shot Texas",                 "progressive-money"),
    ("Blue Action",                     "progressive-money"),
    ("State Voices",                    "progressive-money"),
    ("Emgage",                          "progressive-money"),
    ("Emerge-USA",                      "progressive-money"),
    ("Rise AAPI",                       "progressive-money"),
    ("Indian American Impact Fund",     "progressive-money"),
    ("Local Progress Impact Lab",       "progressive-money"),
    ("Climate Power",                   "progressive-money"),
    ("350.org",                         "progressive-money"),
    ("The IMPACT FUND",                 "progressive-money"),
    ("Brigid Alliance",                 "progressive-money"),
    ("Un-PAC",                          "progressive-money"),
    ("Americans United",                None),
    ("Southern Coalition for Social Justice", "progressive-money"),
    ("Trade Justice Ed Fund",           "progressive-money"),
    ("People Power and Light",          "progressive-money"),
    ("Civic Nation",                    "progressive-money"),
    ("GPS Impact",                      "progressive-money"),
    ("YouGov Blue",                     "progressive-money"),
    ("Middle Seat",                     "political-consulting"),
    # Healthcare nonprofit
    ("Embracia Health",                 "health-equity"),
    ("Jeremiah Program",                "progressive-money"),
    ("Front Steps Keep Austin Housed",  "homelessness-services"),
    ("City Forward Collective",         "progressive-money"),
    ("Rupani Foundation",               None),
    ("The Scott Foundation",            None),
    ("Danaher Lynch Services Foundation", None),
    ("Charity Navigator",               None),
    ("The Wilderness Society",          None),
    ("Unitarian Society of Germantown", None),
    ("Welcoming Neighbors Network",     "progressive-money"),
    ("Victoria Islamic Center",         None),
    ("National Audubon Society",        None),
    ("Raindrop Foundation",             None),
    ("SOS Leadership",                  None),
    ("Facing Abuse in Community Environments", None),
    ("NDWA Labs",                       "progressive-money"),
    ("Aunt Bertha",                     "progressive-money"),  # social services referral
    ("Elizabeth Warren for President",  "progressive-money"),
    ("Empower Project",                 "progressive-money"),
    ("AHRC",                            None),
    ("The Sentencing Project",          "progressive-money"),
    ("Woori Juntos",                    "progressive-money"),
    ("American Institutes for Research", None),
    ("Solidarity",                      "progressive-money"),
    ("CCS Fundraising",                 None),
    ("Waid Environmental",              None),
    ("Austin Theatre Alliance",         "hospitality-entertainment"),
    ("Austin Opera",                    "hospitality-entertainment"),
    ("Austin Public Library",           None),
    ("Austin Chamber",                  None),
    ("Covenant Presbeterian",           None),
    ("Memorial Loop",                   "transit-trails"),
    ("NMSHSA",                          None),
    ("NMSDC",                           None),
    ("Hispanic Scholarship Consortium", None),
    ("Asian American journalist association", None),
    ("The Advocates",                   "progressive-money"),
    ("DLFF",                            None),
    ("Movability",                      "transit-trails"),
    ("The First Ask",                   "progressive-money"),
    ("Watershed Analytics",             None),
    ("People???s Concern",             "progressive-money"),
    ("Episcopal Community Services",    "progressive-money"),
    ("Emgage",                          "progressive-money"),
    ("Facing Abuse in Community Environments", None),
    ("CCTX",                            None),
    ("Consort Inc.",                    None),
    ("Pandamonium Design",              None),
]
for name, tags in NONPROFITS:
    cur.execute("""
        UPDATE employer_identities SET industry='Nonprofit', interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (tags, name))

# ── 10. Political campaigns → Consulting/PR ───────────────────────────────────
CAMPAIGNS = [
    "James Talarico Campaign", "Salman Bhojani Campaign",
    "John Bucy Campaign", "Collier Committee", "Collier for Lt. Governor",
    "Alex Dominguez Campaign", "Andy Kim for Congress",
    "Jay Kleberg for Texas Land Commissioner", "Gandhi For Texas",
    "Sheila Jackson Lee For Congress Campaign Account Election Committee",
    "Doug Greco for Austin Mayor", "Chris Mann for Kansas",
    "Casten for Congress", "JB for Governor", "Josh Kaul for AG",
    "Abdul for Michigan", "Chris Mann for Kansas", "Daniela for Austin",
    "Celia For Austin", "Christian Menefee for Congress",
    "Greg Casar for Congress", "Bhojani for texas",
    "Warren for President", "Elizabeth Warren for President",
    "House of Reps", "US Senate", "Political Campaign",
    "New York City", "NYC", "PANYNJ", "NYC HHC",
    "NYC Dept. of City Planning",
    "Office of Congressman Lloyd Doggett",
    "Rep. Goodwin",
]
for name in CAMPAIGNS:
    cur.execute("""
        UPDATE employer_identities SET industry='Nonprofit', interest_tags='progressive-money'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 11. Energy ────────────────────────────────────────────────────────────────
ENERGY = [
    ("Pattern energy",      "energy-mineral-rights"),
    ("Pattern",             "energy-mineral-rights"),
    ("RWE Renewables Americas", None),
    ("Sunnova",             None),
    ("Riz Energy",          None),
    ("Embark Energy",       None),
    ("Treaty Oak Clean Energy", None),
    ("1st Choice Energy",   None),
    ("OPTERRA Energy Solutions", None),
    ("Caelus Energy",       "energy-mineral-rights"),
    ("DTE Energy",          None),
    ("ENGIE",               None),
    ("BP",                  "fossil-fuel-advocacy"),
    ("RMI",                 None),   # Rocky Mountain Institute
    ("Edtech Ventures",     None),
]
for name, tags in ENERGY:
    cur.execute("""
        UPDATE employer_identities SET industry='Energy / Environment', interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (tags, name))

# ── 12. Hospitality / Entertainment ──────────────────────────────────────────
HOSPITALITY = [
    "Terry Black's BBQ", "C3 Presents/Live Nation", "Austin TeamCo",
    "Museum of Ice Cream", "Shawarma Point", "Zydeco",
    "Woom Bikes USA",  # cycling/recreation
    "Life Time",       # fitness
    "On Location",
    "Gold's Gym",
    "Chili's Grill and Bar",
    "Wendys",
    "via 313",        # Austin pizza
    "Soho house",
    "Starbucks",
    "Airbnb",
    "Visit San Antonio",
    "Austin Pickle Ranch",
    "Family Sports",
    "HEAT Bootcamp",
    "Funktion dance complex",
    "Graftek Imaging",
    "Mike Calvert Toyota",  # auto dealer / retail
    "kings antiques",
    "Booda Organics",
]
for name in HOSPITALITY:
    cur.execute("""
        UPDATE employer_identities SET industry='Hospitality / Entertainment', interest_tags='hospitality-entertainment'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 13. Transportation ────────────────────────────────────────────────────────
TRANSPORT = [
    "Transport ATX", "United air", "Austin charter services",
    "Houston-Galveston Area Council",
]
for name in TRANSPORT:
    cur.execute("""
        UPDATE employer_identities SET industry='Transportation'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 14. Consulting / PR ────────────────────────────────────────────────────────
CONSULTING = [
    ("Outreach Strategists LLC",    "political-consulting"),
    ("Politics United Marketing",   "political-consulting"),
    ("Saldana PR",                  "political-consulting"),
    ("Nor'easter Strategy Group",   "political-consulting"),
    ("Evergreen Strategy Group",    "political-consulting"),
    ("Collier Committee",           "political-consulting"),
    ("George P Johnson",            None),
    ("Dieste Inc",                  None),
    ("GLG",                         None),
    ("TetraTech",                   None),
    ("FBC",                         None),
    ("FBC- The Generosity Experts", None),
    ("Apil Services LLC",           None),
    ("Baxter Planning",             "real-estate-development"),
    ("Chasesource",                 None),
    ("CCS Fundraising",             None),
    ("Harney Management Partners",  None),
    ("MEA Tran Enterprises",        None),
    ("Gemini Diversifed Services",  None),
    ("Experis",                     None),
    ("Magnit",                      None),
    ("Just Global",                 None),
]
for name, tags in CONSULTING:
    cur.execute("""
        UPDATE employer_identities SET industry='Consulting / PR', interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (tags, name))

# ── 15. Labor / Unions ────────────────────────────────────────────────────────
LABOR = [
    "International Brotherhood of Electrical Workers Political Action Committee",
]
for name in LABOR:
    cur.execute("""
        UPDATE employer_identities SET industry='Labor', interest_tags='progressive-money'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 16. Retail ────────────────────────────────────────────────────────────────
RETAIL = [
    "Worlds Gold & Diamonds Inc", "Ainsworth Pet Nutrition",
    "Made In", "Vital Farms", "Woom Bikes USA",
    "Mike Calvert Toyota", "kings antiques", "Monster Worldwide",
]
for name in RETAIL:
    cur.execute("""
        UPDATE employer_identities SET industry='Retail'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 17. Government ────────────────────────────────────────────────────────────
GOVT = [
    "Texas Legislative Council", "Travis Counyt",  # Travis County typo
    "U.S. Dep't of Homeland Security", "SOAH",
    "Soah", "JPS",  # JPS Health Network (public hospital)
    "NASA", "FRB",
]
for name in GOVT:
    cur.execute("""
        UPDATE employer_identities SET industry='Government'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 18. Media ─────────────────────────────────────────────────────────────────
MEDIA = [
    "ABC13", "Airwaves",
]
for name in MEDIA:
    cur.execute("""
        UPDATE employer_identities SET industry='Media'
        WHERE canonical_name=? AND industry IS NULL
    """, (name,))

# ── 19. Construction / Engineering ───────────────────────────────────────────
ENGINEERING = [
    ("Arcadis",         None),
    ("Lockheed Martin", None),   # defense/engineering
    ("Maas Verde Landscape Restoration", None),
    ("DBIA SW",         None),
]
for name, tags in ENGINEERING:
    cur.execute("""
        UPDATE employer_identities SET industry='Engineering', interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (tags, name))

conn.commit()

# ── Report ─────────────────────────────────────────────────────────────────────
cur.execute("""
    SELECT
        COALESCE(ei.industry, 'Unknown') as bucket,
        COUNT(*) as n,
        SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)) as total
    FROM campaign_finance cf
    LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    WHERE cf.recipient LIKE '%Qadri%' AND cf.contribution_year >= 2022
    GROUP BY bucket
    ORDER BY total DESC
""")
rows = cur.fetchall()
grand_total = sum(r[2] or 0 for r in rows)
print(f"\n=== QADRI DONOR BREAKDOWN AFTER CLASSIFICATION ===")
print(f"{'Industry':<35} {'Amount':>10}  {'%':>5}  {'Records':>7}")
print("-" * 65)
for r in rows:
    pct = (r[2] or 0) / grand_total * 100
    print(f"{r[0]:<35} ${r[2]:>9,.0f}  {pct:>4.1f}%  {r[1]:>7}")
print(f"\nTotal: ${grand_total:,.0f}")

cur.execute("""
    SELECT COUNT(*), SUM(COALESCE(balanced_amount, contribution_amount))
    FROM campaign_finance cf
    WHERE cf.recipient LIKE '%Qadri%'
      AND cf.employer_id IS NULL
      AND cf.contribution_year >= 2022
""")
r = cur.fetchone()
print(f"\nStill NULL employer_id: {r[0]} records, ${r[1] or 0:,.0f}")

# How many canonical names still unclassified in Qadri's pool?
cur.execute("""
    SELECT COUNT(DISTINCT ei.canonical_name)
    FROM campaign_finance cf
    JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    WHERE cf.recipient LIKE '%Qadri%'
      AND cf.contribution_year >= 2022
      AND ei.industry IS NULL
""")
print(f"Still unclassified canonical names in Qadri pool: {cur.fetchone()[0]}")

conn.close()
print(f"\nDone. Self-emp extra wired: {wired_self}")
