import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

batch4 = [
  # Ones already classified but aliases remain unclassified
  ("USAA",              "Finance", None),
  ("Walmart",           "Retail", None),
  ("Boeing",            "Technology", None),
  ("Aspirus",           "Healthcare", None),
  ("Yardi",             "Technology", "real-estate-development"),
  ("Square",            "Technology", "tech-startup-ecosystem"),
  ("Humana",            "Healthcare", None),
  ("CenterPoint Energy","Energy / Environment", None),

  # Technology
  ("Cox",               "Technology", None),          # Cox Communications/Enterprises
  ("Cox Automotive",    "Technology", None),
  ("Run the World",     "Technology", "tech-startup-ecosystem"),
  ("GLG",               "Consulting / PR", None),     # Gerson Lehrman Group alias
  ("AWS",               "Technology", None),
  ("Axis Communications","Technology", None),
  ("American Innovations","Technology", None),
  ("Pushnami",          "Technology", "tech-startup-ecosystem"),
  ("Juniper Square",    "Technology", "real-estate-development"),
  ("BottomLine Solutions","Technology", None),
  ("Cybereason",        "Technology", None),
  ("Enthought",         "Technology", "tech-startup-ecosystem"),
  ("EBSCO Information Services","Technology", None),
  ("Gartner",           "Technology", None),
  ("Logitech",          "Technology", None),
  ("Synopsys",          "Technology", None),
  ("TIBCO",             "Technology", "tech-startup-ecosystem"),
  ("Twilio",            "Technology", None),
  ("Tarro",             "Technology", "tech-startup-ecosystem"),
  ("Think Company",     "Technology", None),
  ("Vast",              "Technology", "tech-startup-ecosystem"),
  ("CivicActions",      "Technology", "progressive-money"),
  ("LV Collective",     "Technology", "tech-startup-ecosystem"),   # Austin proptech/coliving
  ("eCab",              "Technology", None),
  ("Acceleros",         "Technology", None),
  ("MagRabbit",         "Technology", None),

  # Healthcare
  ("MAP",               "Healthcare", None),          # could be medical assoc.
  ("UPMC",              "Healthcare", None),
  ("New York Life Insurance","Finance", None),
  ("Texas Mutual",      "Finance", None),             # workers comp insurance
  ("American Cancer Society","Nonprofit", "health-equity"),
  ("Pediatrix",         "Healthcare", None),
  ("OACT",              "Healthcare", None),
  ("Fringe Benefit Group","Finance", None),
  ("NRG Energy",        "Energy / Environment", "fossil-fuel-advocacy"),
  ("BSW",               "Healthcare", None),          # Baylor Scott & White alias
  ("Austin Anesthesiology","Healthcare", None),
  ("Private Practice",  "Healthcare", None),
  ("Bilinguistics",     "Healthcare", None),          # speech-language pathology

  # Finance / Investment
  ("Long View Equity",  "Finance", "real-estate-development"),
  ("OakPoint",          "Finance", "real-estate-development"),
  ("AFO Capital",       "Finance", None),
  ("Raptor Resources",  "Finance", "energy-mineral-rights"),
  ("Royalty Clearinghouse","Finance","energy-mineral-rights"),
  ("SGI Ventures",      "Finance", "real-estate-development"),
  ("SP Partners",       "Finance", "real-estate-development"),
  ("ESW Capital",       "Finance", "tech-startup-ecosystem"),
  ("Hays Finance",      "Finance", None),
  ("Hennessy Advisors", "Finance", None),
  ("Wildhorn Capital",  "Finance", "real-estate-development"),
  ("Wilson Capital",    "Finance", "real-estate-development"),
  ("Moonshots Capital", "Finance", "tech-startup-ecosystem"),
  ("The Liberty Group", "Real Estate", "real-estate-development"),  # Austin apt REIT
  ("Seamless Capital",  "Finance", "real-estate-development"),
  ("Sothebys",          "Real Estate", "luxury-real-estate"),
  ("Churchill Mortgage","Finance", None),
  ("Related Companies", "Real Estate", "real-estate-development|multifamily-housing"),
  ("SCPG",              "Real Estate", "real-estate-development"),
  ("Heller",            "Finance", None),

  # Real Estate / Construction
  ("Saigebrook Development","Real Estate","real-estate-development"),
  ("Inspire Development","Real Estate","real-estate-development"),
  ("StoryBuilt",        "Construction","homebuilders|real-estate-development"),
  ("Azalea Development","Real Estate","real-estate-development"),
  ("Development 2000, Inc.","Real Estate","real-estate-development"),
  ("Ledgestone Development Group","Real Estate","real-estate-development"),
  ("Larry Peel Company","Construction","real-estate-development"),
  ("Wuest Group",       "Real Estate","real-estate-development"),
  ("Bramlett Residential","Real Estate","real-estate-development"),
  ("AUSTIN METAL & IRON","Construction",None),
  ("Continental Automotive Group","Retail",None),
  ("Charles Maund",     "Retail", None),   # car dealership
  ("KWIK mart",         "Retail", None),
  ("Century A/C",       "Construction", None),
  ("Crystal Clear Pools","Construction",None),

  # Legal
  ("Malik Legal Group PLLC","Legal",None),
  ("Law Offices of Jeanine Lehman PC","Legal",None),
  ("Holt Major Lackey, PLLC","Legal",None),
  ("Reeves $ Brightwell LLP","Legal",None),
  ("The Jones Firm",    "Legal", None),
  ("Morgan Lewis",      "Legal", None),
  ("Almanza Blackburn Dickie & Mitchell","Legal",None),

  # Engineering / Architecture
  ("Nelsen Partners",   "Engineering", "real-estate-development"),
  ("Baxter Planning",   "Consulting / PR", "real-estate-development"),
  ("KSA",               "Engineering", None),
  ("DWG",               "Engineering", None),
  ("CSW",               "Engineering", None),

  # Consulting / PR
  ("GSD&M",             "Consulting / PR", None),
  ("MWSW",              "Consulting / PR", None),
  ("Ryan",              "Consulting / PR", None),    # Ryan LLC - tax/govt services
  ("The Davis Group",   "Consulting / PR", "political-consulting"),
  ("Adisa Communications","Consulting / PR","political-consulting"),
  ("Hahn Public Communications","Consulting / PR","political-consulting"),
  ("New West Communications","Consulting / PR","political-consulting"),
  ("McWilliams Governmental Affairs","Consulting / PR","political-consulting"),
  ("Opportunity Austin","Consulting / PR", None),   # Austin Chamber econ dev arm
  ("THLA",              "Nonprofit", "hospitality-entertainment"),  # TX Hotel & Lodging Assoc
  ("ECPR Texas",        "Consulting / PR", "political-consulting"),

  # Government
  ("LISD",              "Government", None),    # Leander ISD
  ("Texas Municipal Power Agency","Government",None),
  ("Austin Community Foundation","Nonprofit",None),
  ("LBJ Foundation",    "Nonprofit", None),
  ("Carl & Marie Jo Anderson Charitable Foundation","Nonprofit",None),

  # Nonprofit
  ("Texas Organizing Project","Nonprofit","progressive-money"),
  ("Steve Adler Campaign","Nonprofit","progressive-money"),
  ("TRLA",              "Nonprofit", "progressive-money"),   # TX RioGrande Legal Aid alias
  ("TLSC",              "Nonprofit", "progressive-money"),   # TX Legal Services Center alias
  ("BCL of Texas",      "Nonprofit", "progressive-money"),   # Business & Community Lenders
  ("New Consensus",     "Nonprofit", "progressive-money"),
  ("Affordable Central Texas","Nonprofit","progressive-money"),
  ("Utah Democrats",    "Nonprofit", "progressive-money"),
  ("Rowing Dock",       "Hospitality / Entertainment","hospitality-entertainment"),
  ("The Omelettry",     "Hospitality / Entertainment","hospitality-entertainment"),
  ("Joe W Fly Co",      "Construction", None),
  ("The Trail Conservancy","Nonprofit","transit-trails"),
  ("Waller Creek Conservancy","Nonprofit","transit-trails"),
  ("Open Road Renewables","Energy / Environment", None),
  ("Shell",             "Energy / Environment","fossil-fuel-advocacy|energy-mineral-rights"),
  ("ConocoPhillips",    "Energy / Environment","fossil-fuel-advocacy|energy-mineral-rights"),
  ("American Express",  "Finance", None),
  ("REI",               "Retail", None),
  ("Communications Workers of America","Labor","progressive-money"),
  ("UA Plumbers + Pipefitters Local 286 PAC Fund","Labor","progressive-money"),
  ("Ford",              "Technology", None),
  ("NAPA",              "Retail", None),
  ("Central Austin Management Group","Real Estate","real-estate-development"),
  ("Bonner Carrington", "Real Estate","real-estate-development"),
  ("Bluff springs enterprise","Real Estate","real-estate-development"),
  ("Foresight",         "Real Estate","real-estate-development"),
  ("Southwest Destructors","Construction",None),
  ("Austin Pickle Ranch","Hospitality / Entertainment","hospitality-entertainment"),
  ("Moore & Associates","Engineering","real-estate-development"),
  ("KIND",              "Technology", "tech-startup-ecosystem"),  # KIND Financial Austin
  ("LAN",               "Engineering",None),
  ("Harney Management Partners","Consulting / PR",None),
  ("Ellis & Salazar",   "Legal",None),
  ("Texas Democrats",   "Nonprofit","progressive-money"),
  ("MEM & Assoc.",      "Consulting / PR",None),
  ("Family Sports",     "Hospitality / Entertainment","hospitality-entertainment"),
  ("Generation SERVE",  "Nonprofit","progressive-money"),
  ("Cunningham Allen Inc.","Consulting / PR",None),
  ("TAB",               "Nonprofit",None),    # Texas Association of Business
  ("Capitol City Insurance","Finance",None),
  ("Century Natural Resources","Energy / Environment","energy-mineral-rights"),
  ("ACT Security",      "Construction",None),
  ("ASAP Interiors",    "Construction",None),
  ("ATX Energy",        "Energy / Environment",None),
  ("BASE",              "Technology","tech-startup-ecosystem"),
  ("DBC",               "Consulting / PR",None),
  ("Donna R Davis CPA", "Finance",None),
  ("FBHG",              "Finance","real-estate-development"),
  ("JDI",               "Real Estate","real-estate-development"),
  ("MAXTAB",            "Technology",None),
  ("MAYA",              "Technology",None),
  ("MPREG",             "Healthcare",None),
  ("OACT",              "Healthcare",None),
  ("RCCP",              "Nonprofit",None),
  ("RNA",               "Healthcare",None),
  ("Steve T. Matthews Company","Construction",None),
  ("Robert M Howard Inc","Construction",None),
  ("Thomas Graphics",   "Media",None),
  ("Titanium Payments", "Technology","tech-startup-ecosystem"),
  ("Jamie Turner Designs","Media",None),
  ("BRKARTSTUDIO",      "Media",None),
  ("CRAFTCORPS",        "Construction",None),
  ("AmC Company",       "Technology",None),
]

updated = 0
not_found = []
for canonical, industry, tags in batch4:
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
print(f"Not in DB: {len(not_found)}")

cur.execute("SELECT SUM(record_count) FROM employer_identities WHERE industry IS NOT NULL")
cr = cur.fetchone()[0] or 0
cur.execute("SELECT SUM(record_count) FROM employer_identities")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM employer_identities WHERE industry IS NOT NULL")
classified = cur.fetchone()[0]
print(f"Total classified: {classified:,}")
print(f"Record coverage: {cr:,} / {total:,} = {cr/total*100:.1f}%")
conn.close()
