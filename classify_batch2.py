import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# All the clear ones from the next 80 unclassified employers
batch2 = [
    # Government
    ("HHSC",                                        "Government",           None),
    ("Health and Human Svc Dept",                   "Government",           None),
    ("ACC",                                         "Education",            "higher-education"),
    ("TCEQ",                                        "Government",           None),
    ("COA",                                         "Government",           None),
    ("Texas Education Agency",                      "Government",           None),
    ("TXDOT",                                       "Government",           None),
    ("Williamson County",                           "Government",           None),
    ("IRS",                                         "Government",           None),
    ("Austin Energy",                               "Government",           None),
    ("UT System",                                   "Education",            "higher-education"),
    ("Dell Medical School",                         "Education",            "higher-education"),
    ("Texas State University",                      "Education",            "higher-education"),
    ("Leander ISD",                                 "Education",            "higher-education"),
    # Technology
    ("Atlassian",                                   "Technology",           "tech-startup-ecosystem"),
    ("Intel",                                       "Technology",           "tech-startup-ecosystem"),
    ("SILICON LABS",                                "Technology",           "tech-startup-ecosystem"),
    ("META INC.",                                   "Technology",           "tech-startup-ecosystem"),
    ("Accenture",                                   "Technology",           "tech-startup-ecosystem"),
    ("WalkMe",                                      "Technology",           "tech-startup-ecosystem"),
    ("Cisco",                                       "Technology",           "tech-startup-ecosystem"),
    ("National Instruments",                        "Technology",           "tech-startup-ecosystem"),
    ("Qualcomm",                                    "Technology",           "tech-startup-ecosystem"),
    ("General Motors",                              "Technology",           None),
    ("Tipit",                                       "Technology",           "tech-startup-ecosystem"),
    # Healthcare
    ("HCA",                                         "Healthcare",           None),
    ("Texas Oncology",                              "Healthcare",           None),
    ("USAP",                                        "Healthcare",           None),
    # Real Estate
    ("AQUILA Commercial",                           "Real Estate",          "real-estate-development"),
    ("Keller Williams",                             "Real Estate",          "real-estate-development"),
    ("Realty Austin",                               "Real Estate",          "real-estate-development"),
    ("COMPASS",                                     "Real Estate",          "real-estate-development"),
    ("Cumby Group",                                 "Real Estate",          "real-estate-development"),
    ("TOPO",                                        "Real Estate",          "real-estate-development"),
    ("JONES LANG LASALLE",                          "Real Estate",          "real-estate-development"),
    ("David WEekley Homes",                         "Construction",         "real-estate-development|homebuilders"),
    ("White Construction Company",                  "Construction",         "real-estate-development"),
    ("TREPAC/Texas Association of REALTORS Political Action Committee", "Nonprofit", "real-estate-development"),
    ("Concierge Auctions",                          "Real Estate",          "real-estate-development|luxury-real-estate"),
    # Engineering
    ("Harutunian Engineering",                      "Engineering",          "real-estate-development"),
    ("Encotech",                                    "Engineering",          "real-estate-development"),
    ("Makel Engineering Inc.",                      "Engineering",          "real-estate-development"),
    ("HNTB",                                       "Engineering",          None),
    ("Halff",                                       "Engineering",          None),
    ("CobbFendley",                                 "Engineering",          None),
    ("GarzaEMC",                                    "Engineering",          None),
    ("Page",                                        "Engineering",          None),
    # Legal
    ("Baker  Botts",                                "Legal",                "energy-mineral-rights"),
    ("RICHARDS RODRIGUEZ & SKEITH",                "Legal",                "real-estate-development"),
    ("Hanna & Plaut",                               "Legal",                None),
    ("Enoch Kever",                                 "Legal",                None),
    ("Hendler Flores Law",                          "Legal",                None),
    # Finance
    ("VCFO",                                        "Finance",              None),
    ("Wells Fargo",                                 "Finance",              None),
    ("Independent Financial",                       "Finance",              None),
    ("IBC Bank",                                    "Finance",              None),
    ("8VC",                                         "Venture Capital",      "tech-startup-ecosystem"),
    ("Prophet Capital",                             "Finance",              "real-estate-development"),
    # Nonprofit / Advocacy
    ("Austin Habitat For Humanity",                 "Nonprofit",            "progressive-money"),
    ("Texas Freedom Network",                       "Nonprofit",            "progressive-money"),
    ("Texas Appleseed",                             "Nonprofit",            "progressive-money"),
    ("Ground Game Texas",                           "Nonprofit",            "progressive-money"),
    ("Texas Council for Developmental Disabilities","Nonprofit",            None),
    ("Trail Of Lights Foundation",                  "Nonprofit",            None),
    ("VOTE PAC",                                    "Nonprofit",            None),
    # Hospitality
    ("Lake Austin Spa Resort",                      "Hospitality / Entertainment", "hospitality-entertainment"),
    # Retail
    ("H-E-B",                                       "Retail",               None),
    # Publishing / Media
    ("Park Place Publications",                     "Media",                None),
    ("Choice Magazine Listening",                   "Nonprofit",            None),
    # Other
    ("Austin Convention Enterprises",               "Hospitality / Entertainment", "hospitality-entertainment"),
    ("McLean & Howard",                             "Consulting / PR",      None),
]

updated = 0
not_found = []
for canonical, industry, tags in batch2:
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
