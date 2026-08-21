import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

known = [
    ("Unity",                           "Technology",           "tech-startup-ecosystem"),
    ("Capital One",                     "Finance",              None),
    ("Experian",                        "Technology",           "tech-startup-ecosystem"),
    ("Norton Rose Fulbright",           "Legal",                None),
    ("AECOM",                           "Engineering",          None),
    ("Dunaway",                         "Engineering",          "real-estate-development"),
    ("Sherwin Williams",                "Retail",               None),
    ("Brown Distributing",              "Retail",               None),
    ("Momark Development",              "Real Estate",          "real-estate-development"),
    ("JCI RESIDENTIAL, LLC",           "Real Estate",          "real-estate-development"),
    ("Diamond Ventures",               "Real Estate",          "real-estate-development"),
    ("Smith and Vinson",               "Legal",                None),
    ("Weisbart Springer Hayes",        "Legal",                None),
    ("Braun & Gresham",                "Legal",                "real-estate-development"),
    ("Transwestern",                   "Real Estate",          "real-estate-development"),
    ("Atwell",                         "Engineering",          "real-estate-development"),
    ("CVS/Aetna",                      "Healthcare",           None),
    ("Emerson Industrial Automation",  "Technology",           None),
    ("FedEx Express",                  "Transportation",       None),
    ("Castletop Capital",              "Finance",              "real-estate-development"),
    ("TWC",                            "Government",           None),
    ("BGE",                            "Engineering",          "real-estate-development"),
    ("Blizco Productions",             "Media",                None),
    ("WP Engine",                      "Technology",           "tech-startup-ecosystem"),
    ("Procore",                        "Technology",           "tech-startup-ecosystem"),
    ("Q2 Holdings",                    "Technology",           "tech-startup-ecosystem"),
    ("SolarWinds",                     "Technology",           "tech-startup-ecosystem"),
    ("HomeAway",                       "Technology",           "tech-startup-ecosystem"),
    ("Bazaarvoice",                    "Technology",           "tech-startup-ecosystem"),
    ("Opcity",                         "Technology",           "real-estate-development"),
    ("Momark Development",             "Real Estate",          "real-estate-development"),
    ("Brookfield Residential",         "Real Estate",          "real-estate-development|homebuilders"),
    ("Alliance Residential",           "Real Estate",          "real-estate-development|multifamily-housing"),
    ("Roscoe Properties",              "Real Estate",          "real-estate-development"),
    ("Stonelake Capital",              "Finance",              "real-estate-development"),
    ("Munsch Hardt Kopf & Harr",       "Legal",                "real-estate-development"),
    ("Lloyd Gosselink",                "Legal",                None),
    ("Haynes & Boone",                 "Legal",                None),
    ("Vinson & Elkins",                "Legal",                "energy-mineral-rights"),
    ("Bleyl Engineering",              "Engineering",          "real-estate-development"),
    ("Terracon",                       "Engineering",          "real-estate-development"),
    ("CommUnity Care",                 "Healthcare",           None),
    ("Austin Regional Clinic",         "Healthcare",           None),
    ("Dimensional Fund Advisors",      "Finance",              None),
    ("TexPIRG",                        "Nonprofit",            "progressive-money"),
    ("Texas Impact",                   "Nonprofit",            "progressive-money"),
    ("Central Texas Food Bank",        "Nonprofit",            None),
    ("Caritas of Austin",              "Nonprofit",            None),
    ("Front Steps",                    "Nonprofit",            "progressive-money|homelessness-services"),
    ("The Other Ones Foundation",      "Nonprofit",            "progressive-money|homelessness-services"),
    ("Texas Campaign for the Environment", "Nonprofit",        "progressive-money"),
    ("Live Nation",                    "Entertainment",        "hospitality-entertainment"),
    ("Omni Hotels",                    "Hospitality / Entertainment", "hospitality-entertainment"),
    ("Austin American-Statesman",      "Media",                None),
    ("KUT",                            "Media",                None),
    ("KXAN",                           "Media",                None),
    ("Austin Chronicle",               "Media",                None),
    ("Lower Colorado River Authority", "Government",           None),
    ("Travis Central Appraisal District","Government",         None),
    ("Austin Water",                   "Government",           None),
    ("CapMetro",                       "Government",           None),
    ("O-SDA",                          "Nonprofit",            "progressive-money"),
    ("Thrive FP",                      "Finance",              None),
    ("Sysco",                          "Retail",               None),
    ("Castletop Capital",              "Finance",              "real-estate-development"),
    ("Collective Campaigns",           "Consulting / PR",      "political-consulting|progressive-money"),
    ("Idea Carver",                    "Finance",              "real-estate-development"),
    ("RedLeaf",                        "Real Estate",          "real-estate-development"),
    ("COS",                            "Government",           None),
    ("Smith and Vinson",               "Legal",                None),
    ("Huitt Zollars",                  "Engineering",          None),
]

updated = 0
for canonical, industry, tags in known:
    cur.execute("""
        UPDATE employer_identities SET industry=?, interest_tags=?
        WHERE canonical_name=? AND industry IS NULL
    """, (industry, tags, canonical))
    if cur.rowcount:
        updated += 1

conn.commit()
print(f"Updated {updated} employers")

# Remaining genuinely unknown
cur.execute("""
    SELECT canonical_name, record_count FROM employer_identities
    WHERE industry IS NULL AND record_count >= 5
    ORDER BY record_count DESC
""")
remaining = [(n, c) for n, c in cur.fetchall()
             if "/" not in n and len(n.strip()) > 3
             and n.lower().strip() not in {
                 "requested","not required","texas","nonprofit","home","anonymous",
                 "owner","principal","stay at home mom","quality assurance","various",
                 "unknown","n/a","none","self","retired"
             }]
print(f"\nGenuinely unknown (5+ records): {len(remaining)}")
for i, (n, cnt) in enumerate(remaining[:60], 1):
    print(f"  {i:>3}. [{cnt:3d}] {n}")

cur.execute("SELECT SUM(record_count) FROM employer_identities WHERE industry IS NOT NULL")
cr = cur.fetchone()[0] or 0
cur.execute("SELECT SUM(record_count) FROM employer_identities")
total = cur.fetchone()[0]
print(f"\nRecord coverage: {cr:,} / {total:,} = {cr/total*100:.1f}%")
conn.close()
