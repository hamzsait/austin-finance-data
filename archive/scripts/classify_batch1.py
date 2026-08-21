import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# Seed interest_groups reference table
interest_groups = [
    ("real-estate-development",   "Real Estate Development",      "Developers, builders, brokers, title companies, and related interests with financial stakes in Austin zoning, permitting, and development policy.", "industry"),
    ("multifamily-housing",       "Multifamily Housing",          "Apartment developers and property managers focused on high-density residential construction.", "industry"),
    ("luxury-real-estate",        "Luxury Real Estate",           "High-end residential real estate brokers and developers.", "industry"),
    ("homebuilders",              "Homebuilders",                 "Residential single-family homebuilders.", "industry"),
    ("outdoor-advertising",       "Outdoor Advertising",          "Billboard and signage companies with interests in limiting local sign regulation.", "industry"),
    ("anti-regulation",           "Anti-Regulation",              "Organizations with documented opposition to local government regulation.", "industry"),
    ("energy-mineral-rights",     "Energy / Mineral Rights",      "Oil, gas, and mineral rights holders and energy sector interests.", "industry"),
    ("private-equity",            "Private Equity",               "Private equity and investment firms.", "industry"),
    ("insurance-finance",         "Insurance / Finance",          "Insurance consulting and financial services interests.", "industry"),
    ("tech-startup-ecosystem",    "Tech / Startup Ecosystem",     "Austin tech startups, accelerators, and venture capital community.", "industry"),
    ("higher-education",          "Higher Education",             "Universities and academic institutions.", "industry"),
    ("hospitality-entertainment", "Hospitality / Entertainment",  "Hotels, restaurants, live events, and entertainment industry.", "industry"),
    ("political-consulting",      "Political Consulting",         "Campaign strategy, communications, and public affairs firms.", "industry"),
    ("conservative-policy",       "Conservative Policy",          "Think tanks and advocacy groups promoting free-market, limited-government, or socially conservative positions.", "conservative"),
    ("fossil-fuel-advocacy",      "Fossil Fuel Advocacy",         "Organizations that advocate for fossil fuel industry interests or oppose climate regulation.", "conservative"),
    ("republican-money",          "Republican Money",             "Organizations, PACs, or donors with documented alignment with Republican candidates and causes.", "conservative"),
    ("progressive-money",         "Progressive Money",            "Organizations, PACs, or donors with documented alignment with progressive/Democratic candidates and causes.", "progressive"),
    ("school-choice",             "School Choice",                "Advocates for vouchers, charter schools, and alternatives to traditional public schools.", "conservative"),
]

cur.executemany("""
    INSERT OR IGNORE INTO interest_groups (tag, display_name, description, political_lean)
    VALUES (?, ?, ?, ?)
""", interest_groups)
print(f"Seeded {len(interest_groups)} interest group tags")

batch1 = [
    ("Armbrust  & Brown",                                "Legal",                "real-estate-development"),
    ("Endeavor Real Estate",                             "Real Estate",          "real-estate-development"),
    ("Heritage Title Company",                           "Real Estate",          "real-estate-development"),
    ("JOURNEYMAN CONSTRUCTION INC",                      "Construction",         "real-estate-development"),
    ("Norwood Capital Inc.",                             "Finance",              "real-estate-development"),
    ("MileStone Community Builders",                     "Construction",         "real-estate-development|homebuilders"),
    ("Entrepreneurs Foundation",                         "Nonprofit",            "tech-startup-ecosystem|progressive-money"),
    ("Entrepreneurs Foundation of Central Texas",        "Nonprofit",            "tech-startup-ecosystem|progressive-money"),
    ("JAMES AND SARAH MANSOUR FOUNDATION",               "Foundation",           "real-estate-development"),
    ("GREGORY K. AND DAWN STONE CROUCH FAMILY, LTD.",   "Finance",              "insurance-finance"),
    ("Moreland",                                         "Real Estate",          "real-estate-development|luxury-real-estate"),
    ("Reagan Advertising",                               "Media",                "outdoor-advertising|anti-regulation"),
    ("Danly Properties",                                 "Real Estate",          "real-estate-development"),
    ("Butler Family Interests",                          "Finance",              "energy-mineral-rights"),
    ("J Pinnelli & Company",                             "Construction",         "real-estate-development"),
    ("Harris Preston & Partners",                        "Finance",              "private-equity"),
    ("Live Oak - Gottesman, LLC",                        "Real Estate",          "real-estate-development"),
    ("Oden Hughes",                                      "Real Estate",          "real-estate-development|multifamily-housing"),
    ("Vianovo",                                          "Consulting / PR",      "political-consulting|republican-money"),
    ("SXSW",                                             "Entertainment",        "hospitality-entertainment"),
    ("Notley",                                           "Nonprofit",            "tech-startup-ecosystem|progressive-money"),
    ("University of Texas at Austin",                    "Education",            "higher-education"),
    ("Stratus",                                          "Real Estate",          "real-estate-development"),
    ("Riverside Resources",                              "Real Estate",          "real-estate-development"),
    ("Pearlstone",                                       "Real Estate",          "real-estate-development"),
    ("TPPF",                                             "Nonprofit",            "republican-money|conservative-policy|fossil-fuel-advocacy"),
    ("Vista Equity Partners",                            "Finance",              "private-equity"),
    ("Civilitude",                                       "Engineering",          "real-estate-development"),
    ("Impossible Ventures",                              "Venture Capital",      "tech-startup-ecosystem"),
    ("Presidium",                                        "Real Estate",          "real-estate-development|multifamily-housing"),
    ("UrbanSpace",                                       "Real Estate",          "real-estate-development"),
    ("Generational Commercial Properties",               "Real Estate",          "real-estate-development"),
    ("Routh Development Group",                          "Real Estate",          "real-estate-development"),
    ("Lee Real Estate",                                  "Real Estate",          "real-estate-development"),
    ("SLATE Real Estate Partners",                       "Real Estate",          "real-estate-development"),
    ("Trammell Crow Company",                            "Real Estate",          "real-estate-development"),
    ("Corridor Title",                                   "Real Estate",          "real-estate-development"),
    ("T Stacy & Associates Inc.",                        "Real Estate",          "real-estate-development"),
    ("Strub Residential",                                "Real Estate",          "real-estate-development"),
    ("F&F Income Properties",                            "Real Estate",          "real-estate-development"),
    ("Savy Realty",                                      "Real Estate",          "real-estate-development"),
    ("Casteltop Capital",                                "Finance",              "real-estate-development"),
    ("Norwood Investments",                              "Finance",              "real-estate-development"),
    ("DPR Construction",                                 "Construction",         "real-estate-development"),
    ("Cody Builders Supply",                             "Construction",         "real-estate-development"),
    ("Katz Builder",                                     "Construction",         "real-estate-development"),
    ("Austin Metal and Iron",                            "Construction",         "real-estate-development"),
    ("CP & Y, Inc.",                                     "Engineering",          "real-estate-development"),
    ("Hejl, Lee & Associates",                           "Engineering",          "real-estate-development"),
    ("Oracle",                                           "Technology",           "tech-startup-ecosystem"),
    ("IBM",                                              "Technology",           "tech-startup-ecosystem"),
    ("DELL",                                             "Technology",           "tech-startup-ecosystem"),
    ("APPLE",                                            "Technology",           "tech-startup-ecosystem"),
    ("NVIDIA",                                           "Technology",           "tech-startup-ecosystem"),
    ("AMD",                                              "Technology",           "tech-startup-ecosystem"),
    ("NXP",                                              "Technology",           "tech-startup-ecosystem"),
    ("Google",                                           "Technology",           "tech-startup-ecosystem"),
    ("Amazon",                                           "Technology",           "tech-startup-ecosystem"),
    ("Indeed",                                           "Technology",           "tech-startup-ecosystem"),
    ("Airbnb",                                           "Technology",           "hospitality-entertainment"),
    ("VM Ware",                                          "Technology",           "tech-startup-ecosystem"),
    ("360Connect",                                       "Technology",           "tech-startup-ecosystem"),
    ("InKind",                                           "Technology",           "hospitality-entertainment"),
    ("University of Texas System",                       "Education",            "higher-education"),
    ("AUSTIN COMMUNITY COLLEGE",                         "Education",            "higher-education"),
    ("Concordia University",                             "Education",            "higher-education"),
    ("St Edward's University",                           "Education",            "higher-education"),
    ("Round Rock ISD",                                   "Education",            "higher-education"),
    ("Austin ISD",                                       "Education",            "higher-education"),
    ("City of Austin",                                   "Government",           None),
    ("Travis County",                                    "Government",           None),
    ("STATE OF TEXAS",                                   "Government",           None),
    ("Texas Legislature",                                "Government",           None),
    ("Austin Police Department",                         "Government",           None),
    ("Texas Comptroller of Public Accounts",             "Government",           None),
    ("Texas Department of Transportation",               "Government",           None),
    ("Ascension Seton",                                  "Healthcare",           None),
    ("Baylor Scott & White",                             "Healthcare",           None),
    ("Central Health",                                   "Healthcare",           None),
    ("US Anesthesia Partners",                           "Healthcare",           None),
    ("SAFE ALLIANCE",                                    "Nonprofit",            "progressive-money"),
    ("ACLU of Texas",                                    "Nonprofit",            "progressive-money"),
    ("Workers Defense Project",                          "Nonprofit",            "progressive-money"),
    ("KIPP Austin Public Schools",                       "Education",            None),
    ("Southwest Laborers District Council",              "Labor",                "progressive-money"),
    ("AFSCME Local 1624",                                "Labor",                "progressive-money"),
    ("CWA",                                              "Labor",                "progressive-money"),
    ("IBEW PAC Voluntary Fund",                          "Labor",                "progressive-money"),
    ("Winstead",                                         "Legal",                "real-estate-development"),
    ("Locke Lord",                                       "Legal",                "real-estate-development"),
    ("Jackson Walker",                                   "Legal",                "real-estate-development"),
    ("DuBOIS BRYANT & Campbell LLP",                     "Legal",                "real-estate-development"),
    ("Scott Douglass & McConnico",                       "Legal",                "real-estate-development"),
    ("Graves Dougherty Hearon & Moody",                  "Legal",                "real-estate-development"),
    ("McGinnis Lochridge",                               "Legal",                "real-estate-development"),
    ("METCALFE WOLFF STUART & Williams, LLP",            "Legal",                "real-estate-development"),
    ("Drenner Group",                                    "Legal",                "real-estate-development"),
    ("HillCo",                                           "Consulting / PR",      "political-consulting"),
    ("RECA",                                             "Nonprofit",            "real-estate-development"),
    ("Austin Board of REALTORS",                         "Nonprofit",            "real-estate-development"),
    ("HEB",                                              "Retail",               None),
    ("Whole Foods Market",                               "Retail",               None),
    ("AT&T",                                             "Technology",           None),
    ("Lyft",                                             "Technology",           None),
    ("Deloitte",                                         "Consulting / PR",      None),
    ("C3 Presents",                                      "Entertainment",        "hospitality-entertainment"),
    ("ActBlue",                                          "Nonprofit",            "progressive-money"),
    ("TEXAS DISPOSAL SYSTEMS",                           "Energy / Environment", None),
    ("HDR Engineering",                                  "Engineering",          None),
    ("Pape Dawson Engineers",                            "Engineering",          None),
    ("Carollo Engineers Inc.",                           "Engineering",          None),
    ("Lockwood, Andrews & Newnam, Inc.",                 "Engineering",          None),
    ("CAS Consulting",                                   "Engineering",          None),
    ("Frost Bank",                                       "Finance",              None),
    ("JLL",                                              "Real Estate",          "real-estate-development"),
    ("CBRE",                                             "Real Estate",          "real-estate-development"),
    ("HPI",                                              "Real Estate",          "real-estate-development"),
    ("Stream Realty",                                    "Real Estate",          "real-estate-development"),
    ("Balcones Resources",                               "Energy / Environment", None),
    ("Hill Country Conservancy",                         "Nonprofit",            "progressive-money"),
    ("SAVE OUR SPRINGS ALLIANCE",                        "Nonprofit",            "progressive-money"),
    ("Bike Austin",                                      "Nonprofit",            "progressive-money"),
    ("HUSCH BLACKWELL",                                  "Legal",                "real-estate-development"),
    ("Linebarger",                                       "Legal",                None),
    ("Fritz Byrne Head & Gilstrap",                      "Legal",                "real-estate-development"),
    ("Loewy Law Firm",                                   "Legal",                None),
    ("Thompson & Knight",                                "Legal",                "real-estate-development"),
    ("Hunton Andrews & Kurth",                           "Legal",                "real-estate-development"),
    ("Alexander Dubose & Jefferson",                     "Legal",                None),
    ("Balch & Bingham",                                  "Legal",                None),
]

updated = 0
not_found = []
for canonical, industry, tags in batch1:
    cur.execute("""
        UPDATE employer_identities SET industry = ?, interest_tags = ?
        WHERE canonical_name = ?
    """, (industry, tags, canonical))
    if cur.rowcount:
        updated += 1
    else:
        not_found.append(canonical)

conn.commit()
print(f"Updated {updated} employer identities")
if not_found:
    print(f"Not found ({len(not_found)}):")
    for n in not_found:
        print(f"  - {n}")

cur.execute("SELECT COUNT(*) FROM employer_identities WHERE industry IS NOT NULL")
print(f"\nTotal classified: {cur.fetchone()[0]}")
cur.execute("""
    SELECT industry, COUNT(*) as orgs, SUM(record_count) as records
    FROM employer_identities WHERE industry IS NOT NULL
    GROUP BY industry ORDER BY records DESC
""")
print("\nBy industry:")
for row in cur.fetchall():
    print(f"  {row[0]:<30} {row[1]:>4} orgs  {row[2]:>8,} records")

conn.close()
