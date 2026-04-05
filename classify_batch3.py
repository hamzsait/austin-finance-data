import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

batch3 = [
  # ── Noise / non-employers (set to a catch-all so they stop appearing) ────────
  # We'll skip these — they genuinely have no industry

  # ── Technology ────────────────────────────────────────────────────────────────
  ("ARM",               "Technology", "tech-startup-ecosystem"),   # ARM Holdings (chip IP)
  ("GM",                "Technology", None),                        # General Motors
  ("SafeTX",            "Technology", None),
  ("SUSE",              "Technology", "tech-startup-ecosystem"),
  ("Entrust",           "Technology", "tech-startup-ecosystem"),
  ("Pegalo",            "Technology", None),
  ("Rapid7",            "Technology", None),
  ("Rouser",            "Technology", None),
  ("Wexum",             "Technology", None),
  ("AlertMedia",        "Technology", "tech-startup-ecosystem"),    # Austin startup
  ("AthenaHealth",      "Technology", None),                        # healthcare tech
  ("BigCommerce",       "Technology", "tech-startup-ecosystem"),    # Austin ecommerce SaaS
  ("Civitech",          "Technology", "progressive-money|political-consulting"),
  ("LinkedIn",          "Technology", None),
  ("TikTok",            "Technology", None),
  ("Twitter",           "Technology", None),
  ("CareerBuilder",     "Technology", None),
  ("Roku",              "Technology", None),
  ("Tokyo Electron America", "Technology", None),
  ("Adobe",             "Technology", None),
  ("GoDaddy",           "Technology", None),
  ("PayPal",            "Technology", None),
  ("SAP",               "Technology", None),
  ("Spotify",           "Technology", None),
  ("Tesla",             "Technology", None),
  ("3M",                "Technology", None),
  ("Alereon",           "Technology", "tech-startup-ecosystem"),
  ("Pearson",           "Technology", None),                        # education tech
  ("SHI",               "Technology", None),                        # SHI International IT
  ("Iodine",            "Technology", "tech-startup-ecosystem"),
  ("BuildASign.com",    "Technology", "tech-startup-ecosystem"),
  ("Zilliant",          "Technology", "tech-startup-ecosystem"),
  ("Civitas Learning",  "Technology", "tech-startup-ecosystem"),
  ("Qualia",            "Technology", "real-estate-development"),   # title/closing software
  ("Knox Networks",     "Technology", None),
  ("Circuit of the Americas", "Hospitality / Entertainment", "hospitality-entertainment"),
  ("Khoros",            "Technology", "tech-startup-ecosystem"),
  ("CloudFlare",        "Technology", None),
  ("ARRIS",             "Technology", None),
  ("AccelaVue",         "Technology", None),
  ("Datablocks",        "Technology", None),
  ("SwipeTrack",        "Technology", None),
  ("Moonshots Capital", "Finance", "tech-startup-ecosystem"),
  ("fibercove",         "Technology", "tech-startup-ecosystem"),
  ("CGI",               "Technology", None),
  ("BlueLabs Analytics","Technology", "progressive-money|political-consulting"),
  ("Bonterra",          "Technology", "progressive-money"),         # nonprofit tech (formerly EveryAction)
  ("Khoros",            "Technology", "tech-startup-ecosystem"),
  ("ETS Lindgren",      "Technology", None),
  ("Dun and Bradstreet","Technology", None),
  ("LegalMatch",        "Technology", None),
  ("Qcue",              "Technology", "tech-startup-ecosystem"),
  ("iGrafx",            "Technology", None),
  ("REV.COM",           "Technology", "tech-startup-ecosystem"),    # Austin transcription startup
  ("Legacy DCS",        "Technology", None),
  ("AMC Company",       "Technology", None),
  ("E&Y",               "Consulting / PR", None),                   # Ernst & Young
  ("Stantec",           "Engineering", None),
  ("Garver",            "Engineering", "real-estate-development"),

  # ── Healthcare ────────────────────────────────────────────────────────────────
  ("BS&W",              "Healthcare", None),   # Baylor Scott & White
  ("Humana",            "Healthcare", None),
  ("Centene Corporation","Healthcare", None),
  ("Walgreens",         "Healthcare", None),
  ("Pfizer",            "Healthcare", None),
  ("Cigna",             "Healthcare", None),
  ("USACS",             "Healthcare", None),    # US Anesthesia Centers
  ("Texas Ophthalmological Association", "Healthcare", None),
  ("Schlumberger",      "Energy / Environment", "energy-mineral-rights"),
  ("Pisklak Orthodontics", "Healthcare", None),
  ("Children's Optimal Health", "Healthcare", None),
  ("CommUnityCare",     "Healthcare", None),
  ("St David's",        "Healthcare", None),

  # ── Finance / Insurance ───────────────────────────────────────────────────────
  ("Q2",                "Technology", "tech-startup-ecosystem"),   # Q2 Holdings (fintech)
  ("State Farm",        "Finance", None),
  ("JP Morgan",         "Finance", None),
  ("JPMORGAN CHASE",    "Finance", None),
  ("Unum",              "Finance", None),
  ("Fiducial",          "Finance", None),
  ("Moonshots Capital", "Finance", "tech-startup-ecosystem"),
  ("AFO Capital",       "Finance", None),
  ("Seamless Capital",  "Finance", "real-estate-development"),
  ("River City Capital Partners", "Finance", "real-estate-development"),
  ("Herd Partners",     "Finance", None),
  ("Longbow",           "Finance", None),
  ("ESO",               "Technology", "tech-startup-ecosystem"),   # ESO Solutions Austin
  ("Linder Insurance",  "Finance", None),
  ("IntelliMark",       "Consulting / PR", None),

  # ── Real Estate ───────────────────────────────────────────────────────────────
  ("Amherst",           "Real Estate", "real-estate-development|multifamily-housing"),
  ("Carr Development",  "Real Estate", "real-estate-development"),
  ("Stewart Title",     "Real Estate", "real-estate-development"),
  ("ZYDECO DEVELOPMENT","Real Estate", "real-estate-development"),
  ("DEN Property Group","Real Estate", "real-estate-development"),
  ("Schlosser Development", "Real Estate", "real-estate-development"),
  ("Blackridge",        "Real Estate", "real-estate-development"),
  ("LDG Development",   "Real Estate", "real-estate-development|multifamily-housing"),
  ("Killam Company",    "Real Estate", "real-estate-development"),
  ("Harren Interests",  "Real Estate", "real-estate-development"),
  ("Marketplace RE Group", "Real Estate", "real-estate-development"),
  ("Rainier",           "Real Estate", "real-estate-development"),
  ("Prominent Title",   "Real Estate", "real-estate-development"),
  ("WeWork",            "Real Estate", None),
  ("Dillon Joyce Ltd",  "Real Estate", "real-estate-development"),
  ("HFF",               "Real Estate", "real-estate-development"),  # Holliday Fenoglio Fowler
  ("3423 Holdings LLC", "Real Estate", "real-estate-development"),
  ("Crockett Holdings, LLC", "Real Estate", "real-estate-development"),
  ("Main Street Renewal","Real Estate", "real-estate-development|multifamily-housing"),
  ("Current Investments","Real Estate", "real-estate-development"),
  ("Marbella Interests", "Real Estate", "real-estate-development"),
  ("Mathias Partners",  "Real Estate", "real-estate-development"),
  ("Hill Co. Partners", "Real Estate", "real-estate-development"),
  ("HACA",              "Government",  None),                        # Housing Authority of the City of Austin
  ("GNDC",              "Nonprofit",   "progressive-money"),         # Guadalupe Neighborhood Dev Corp alias

  # ── Construction ─────────────────────────────────────────────────────────────
  ("Big State Electric","Construction", None),
  ("Hensel Phelps",     "Construction", None),
  ("Wes Peoples Homes", "Construction", "homebuilders"),
  ("WhitWorth Homes",   "Construction", "homebuilders"),
  ("Centro Development LLC", "Real Estate", "real-estate-development"),
  ("Starling Development", "Real Estate", "real-estate-development"),
  ("ALIARO",            "Real Estate", "real-estate-development"),

  # ── Legal ─────────────────────────────────────────────────────────────────────
  ("K&L Gates",         "Legal", None),
  ("Davis Kaufman",     "Legal", None),
  ("Carlson Law",       "Legal", None),
  ("Ellwanger Law",     "Legal", None),
  ("Howry Breen & Herman","Legal", None),
  ("Almanza Blackburn Dickie & Mitchell", "Legal", None),
  ("Maxwell Locke & Ritter", "Legal", None),   # actually CPA/accounting firm
  ("Sprouse Shrader Smith", "Legal", None),
  ("The Hay Legal Group PLLC","Legal", None),
  ("ALESHIRE LAW PC",   "Legal", None),
  ("Brim, Robinett, Cantu & Brim, P.C.", "Legal", None),
  ("Wittliff Cutter",   "Legal", "progressive-money"),  # Austin civil rights firm
  ("DLA Piper",         "Legal", None),
  ("Frederick, Perales, Allmon & Rockwell P.C.", "Legal", None),
  ("Savrick Schumann Johnson McGarr", "Legal", None),
  ("De Leon Law PLLC",  "Legal", None),
  ("Deats Durst & Owen","Legal", "progressive-money"),  # Austin labor/employment firm
  ("Lorenz & Lorenz",   "Legal", None),
  ("Kemp Smith LLP",    "Legal", None),
  ("King & Spalding",   "Legal", None),
  ("O'Melveny and Myers","Legal", None),
  ("Kuhn Hobbs PLLC",   "Legal", "political-consulting"),  # government affairs/lobbying
  ("Maxwell Locke & Ritter","Finance", None),   # CPA firm
  ("Siegel Yee Brunner & Mehta", "Legal", None),
  ("Michael Curry PC",  "Legal", None),
  ("Andy Brown & Associates PLLC", "Legal", None),
  ("Cammack and Strong, PC", "Legal", None),

  # ── Engineering / Architecture ────────────────────────────────────────────────
  ("Gensler",           "Architecture", None),
  ("Design Workshop",   "Architecture", None),
  ("Freese and Nichols","Engineering", None),
  ("STV",               "Engineering", None),
  ("Aguirre & Fields",  "Engineering", "real-estate-development"),
  ("Rudd and Wisdom",   "Engineering", None),
  ("Heldenfels Enterprises","Engineering", None),
  ("KTCivil",           "Engineering", "real-estate-development"),
  ("Doucet & Assoc.",   "Engineering", "real-estate-development"),
  ("Land Use Solutions","Consulting / PR", "real-estate-development"),

  # ── Consulting / Government Affairs ──────────────────────────────────────────
  ("GSD&M",             "Consulting / PR", None),    # major Austin ad agency
  ("Mercury",           "Consulting / PR", "political-consulting"),  # Mercury Public Affairs
  ("Giant Noise",       "Consulting / PR", None),    # Austin PR firm
  ("Jones-Dilworth Inc.","Consulting / PR", None),
  ("McWilliams Governmental Affairs", "Consulting / PR", "political-consulting"),
  ("Capitol Services",  "Consulting / PR", "political-consulting"),
  ("EPIC",              "Healthcare", None),          # EPIC Systems EMR
  ("Glasshouse Policy", "Consulting / PR", "political-consulting"),
  ("SOS Alliance",      "Consulting / PR", None),
  ("Blue Sky Co",       "Consulting / PR", None),
  ("Delisi Communications","Consulting / PR", "political-consulting"),
  ("Y Strategy",        "Consulting / PR", None),
  ("Statewide Research","Consulting / PR", None),
  ("Good Company Associates","Consulting / PR", None),
  ("HMWK Global",       "Consulting / PR", None),
  ("McWilliams Governmental Affairs","Consulting / PR","political-consulting"),
  ("Potomac Economics", "Consulting / PR", None),

  # ── Media ─────────────────────────────────────────────────────────────────────
  ("Texas Monthly",     "Media", None),
  ("LIQUIDITY SERVICES","Technology", None),  # online auction marketplace

  # ── Energy ────────────────────────────────────────────────────────────────────
  ("Chevron",           "Energy / Environment", "fossil-fuel-advocacy|energy-mineral-rights"),
  ("USA Compression",   "Energy / Environment", "energy-mineral-rights"),
  ("Enverus",           "Technology", "energy-mineral-rights"),    # energy data analytics
  ("Harren Interests",  "Energy / Environment", "energy-mineral-rights"),
  ("Lonsdale Enterprises","Energy / Environment", "energy-mineral-rights"),

  # ── Government ────────────────────────────────────────────────────────────────
  ("US Army",           "Government", None),
  ("USPS",              "Government", None),
  ("Texas Comptroller", "Government", None),
  ("TSBVI",             "Government", None),   # TX School for Blind/Visually Impaired
  ("PFISD",             "Government", None),   # Pflugerville ISD
  ("Rockwall OSD",      "Government", None),
  ("UC Berkeley",       "Education",  "higher-education"),
  ("Texas State",       "Education",  "higher-education"),
  ("Austin Fire Department","Government", None),

  # ── Nonprofit / Advocacy ─────────────────────────────────────────────────────
  ("Common Cause Texas","Nonprofit", "progressive-money"),
  ("AAYHF",             "Nonprofit", "health-equity"),
  ("AFSSA",             "Nonprofit", None),
  ("Ecology Action",    "Nonprofit", "progressive-money"),
  ("MOVE Texas",        "Nonprofit", "progressive-money"),
  ("Austin Voices for Education and Youth","Nonprofit","progressive-money"),
  ("Democratic Socialists of America","Nonprofit","progressive-money"),
  ("Latinitas",         "Nonprofit", "progressive-money"),
  ("Education Austin",  "Labor", "progressive-money"),    # Austin teachers union affiliate
  ("DigiDems",          "Nonprofit", "progressive-money|political-consulting"),
  ("Democrasexy",       "Nonprofit", "progressive-money"),
  ("Out Youth",         "Nonprofit", "progressive-money"),
  ("Austin LGBT Chamber of Commerce","Nonprofit", None),
  ("Texas Grants Reaource Center","Nonprofit", None),
  ("The Fairness Project","Nonprofit","progressive-money"),
  ("Texans for Reasonable Solutions","Nonprofit", None),
  ("EDF",               "Nonprofit", "progressive-money"),  # Environmental Defense Fund
  ("The SAFE Alliance", "Nonprofit", None),   # Austin domestic violence/sexual assault org
  ("Shalom Austin",     "Nonprofit", None),
  ("EarthShare Texas",  "Nonprofit", "progressive-money"),
  ("Farmshare Austin",  "Nonprofit", None),
  ("Sustainable Food Center","Nonprofit", None),
  ("Habitat for Humanity","Nonprofit","progressive-money"),
  ("NAACP",             "Nonprofit", "progressive-money"),
  ("LIUNA",             "Labor", "progressive-money"),    # Laborers International
  ("Laborers Local 1095","Labor", "progressive-money"),
  ("Stand Up America",  "Nonprofit", "progressive-money"),
  ("Texas Democracy Foundation","Nonprofit","progressive-money"),
  ("Victim Safety First","Nonprofit", None),
  ("America's Service Commissions","Nonprofit", None),
  ("Austin Achieve",    "Education", None),
  ("TDFPS",             "Government", None),   # TX Dept of Family & Protective Services
  ("TCSAAL",            "Nonprofit", None),
  ("Austin History Center","Nonprofit", None),
  ("St David's Foundation","Nonprofit","health-equity"),

  # ── Labor / Campaigns ─────────────────────────────────────────────────────────
  ("Austin Firefighters Association","Labor", "progressive-money"),
  ("Austin Parks Foundation","Nonprofit", None),
  ("Austin Firefighters PAC","Labor", "progressive-money"),
  ("Austin Police Association PAC","Labor", None),
  ("José Garza Campaign","Nonprofit", "progressive-money"),
  ("Lloyd Doggett for Congress","Nonprofit","progressive-money"),
  ("Brigid Shea Campaign","Nonprofit", "progressive-money"),
  ("Cassandra Hernandez for Texas","Nonprofit","progressive-money"),
  ("Beto for Texas",    "Nonprofit", "progressive-money"),
  ("MOVE Texas",        "Nonprofit", "progressive-money"),

  # ── Hospitality / Entertainment ───────────────────────────────────────────────
  ("Marriott",          "Hospitality / Entertainment", "hospitality-entertainment"),
  ("Juan In A Million", "Hospitality / Entertainment", "hospitality-entertainment"),  # Austin restaurant
  ("Esther's Follies",  "Hospitality / Entertainment", "hospitality-entertainment"),
  ("Texas Beer Company","Hospitality / Entertainment", "hospitality-entertainment"),
  ("Salty Sow",         "Hospitality / Entertainment", "hospitality-entertainment"),
  ("Stepstone Hospitality","Hospitality / Entertainment","hospitality-entertainment"),
  ("Visit Austin",      "Nonprofit", None),
  ("Austin Convention Center","Government", None),

  # ── Retail ────────────────────────────────────────────────────────────────────
  ("IKEA",              "Retail", None),
  ("Bicycle Sport Shop","Retail", None),
  ("Whole Earth Provision Co.", "Retail", None),
  ("Seguin Chevrolet",  "Retail", None),
  ("Dixie Carpet",      "Retail", None),
  ("Gap Inc",           "Retail", None),
  ("Safe Streets Austin","Nonprofit", "progressive-money"),

  # ── Other professional / misc ─────────────────────────────────────────────────
  ("Newmark",           "Real Estate", "real-estate-development"),   # Newmark commercial RE
  ("IKEA",              "Retail", None),
  ("INC Research",      "Healthcare", None),   # clinical research org
  ("Parkland Community Health Plan","Healthcare", None),
  ("Jaylor Services",   "Consulting / PR", None),
  ("John Lewis Company","Construction", None),
  ("The R. M. Meadows Co.","Construction", None),
  ("Trellis",           "Nonprofit", "progressive-money"),   # Travis County child welfare
  ("TOI",               "Consulting / PR", None),
  ("KAC",               "Consulting / PR", None),
  ("SPF",               "Real Estate", "real-estate-development"),
  ("HEI",               "Real Estate", "real-estate-development"),   # HEI Hotels & Resorts
  ("APF",               "Nonprofit", None),
  ("ARA",               "Real Estate", "real-estate-development"),   # ARA Newmark
  ("PCM",               "Technology", None),
  ("TRS",               "Government", None),   # Teacher Retirement System
]

updated = 0
not_found = []
for canonical, industry, tags in batch3:
    cur.execute("""
        UPDATE employer_identities SET industry=?, interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (industry, tags, canonical))
    if cur.rowcount:
        updated += 1
    else:
        cur.execute("SELECT 1 FROM employer_identities WHERE canonical_name=?", (canonical,))
        if not cur.fetchone():
            not_found.append(canonical)

conn.commit()
print(f"Updated: {updated}")
if not_found:
    print(f"Not in DB ({len(not_found)}): {not_found[:10]}")

cur.execute("SELECT SUM(record_count) FROM employer_identities WHERE industry IS NOT NULL")
cr = cur.fetchone()[0] or 0
cur.execute("SELECT SUM(record_count) FROM employer_identities")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM employer_identities WHERE industry IS NOT NULL")
classified = cur.fetchone()[0]
print(f"Total classified: {classified:,}")
print(f"Record coverage: {cr:,} / {total:,} = {cr/total*100:.1f}%")
conn.close()
