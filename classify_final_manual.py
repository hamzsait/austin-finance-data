import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

known = [
    ("Go Austin Vamos Austin",              "Nonprofit",            "progressive-money|health-equity"),
    ("Gottesman Residential",               "Real Estate",          "real-estate-development"),
    ("Rivendale Homes",                     "Construction",         "real-estate-development|homebuilders"),
    ("Shoal Creek Conservancy",             "Nonprofit",            None),
    ("The Cooks' Nook",                     "Hospitality / Entertainment", "hospitality-entertainment"),
    ("WSP USA",                             "Engineering",          None),
    ("Ardent Residential",                  "Real Estate",          "real-estate-development|multifamily-housing"),
    ("Flooring Warehouse",                  "Retail",               None),
    ("Garza EMC",                           "Engineering",          "real-estate-development"),
    ("Kairoi Residential",                  "Real Estate",          "real-estate-development|multifamily-housing"),
    ("PIXIU Investments",                   "Finance",              "real-estate-development"),
    ("Scott Felder Homes",                  "Construction",         "real-estate-development|homebuilders"),
    ("Senox Corporation",                   "Construction",         "real-estate-development"),
    ("Stanford Campaigns",                  "Consulting / PR",      "political-consulting"),
    ("Terrile, Cannatti & Chambers, LLP",   "Legal",                None),
    ("Timberline",                          "Real Estate",          "real-estate-development"),
    ("VOCAL-TX",                            "Nonprofit",            "progressive-money"),
    ("Austin FC",                           "Entertainment",        "hospitality-entertainment"),
    ("Aspirus",                             "Healthcare",           None),
    ("Austin Radiological Assoc.",          "Healthcare",           None),
    ("Boeing",                              "Technology",           None),
    ("CapRidge Partners",                   "Real Estate",          "real-estate-development"),
    ("Capstone Title",                      "Real Estate",          "real-estate-development"),
    ("Covenant Presbetarian Church",        "Nonprofit",            None),
    ("Impact Floors",                       "Construction",         None),
    ("Integral Care",                       "Healthcare",           None),
    ("Sabre Commercial",                    "Real Estate",          "real-estate-development"),
    ("Taylor Morrison",                     "Construction",         "real-estate-development|homebuilders"),
    ("The Steam Team",                      "Retail",               None),
    ("Twin Liquors",                        "Retail",               None),
    ("USAA",                                "Finance",              None),
    ("Walmart",                             "Retail",               None),
    ("Willis Co",                           "Real Estate",          "real-estate-development"),
    ("BS&W",                                "Healthcare",           None),
    ("Clinical Pathology Associates",       "Healthcare",           None),
    ("Concentric AI",                       "Technology",           "tech-startup-ecosystem"),
    ("Delta hotels Iselin N.J",             "Hospitality / Entertainment", "hospitality-entertainment"),
    ("Entrust",                             "Technology",           "tech-startup-ecosystem"),
    ("Environment Texas",                   "Nonprofit",            "progressive-money"),
    ("Foley & Lardner LLP",                 "Legal",                None),
    ("Guadalupe Neighborhood Development Corporation", "Nonprofit",  "progressive-money"),
    ("Independence Title",                  "Real Estate",          "real-estate-development"),
    ("Intracorp Homes",                     "Real Estate",          "real-estate-development"),
    ("Raba Kistner",                        "Engineering",          None),
    ("SUSE",                                "Technology",           "tech-startup-ecosystem"),
    ("Texas Global Equity",                 "Finance",              "real-estate-development"),
    ("The Bingham Group",                   "Consulting / PR",      "political-consulting"),
    ("The Sutton Company",                  "Real Estate",          "real-estate-development"),
    ("Allensworth",                         "Legal",                "real-estate-development"),
    ("Clarite",                             "Technology",           "tech-startup-ecosystem"),
    ("Great Minds",                         "Education",            "higher-education"),
    ("McAllister",                          "Real Estate",          "real-estate-development"),
    ("Austin Turning Point",                "Nonprofit",            "progressive-money"),
    ("Morrison & Head",                     "Engineering",          "real-estate-development"),
    ("USAA",                                "Finance",              None),
    ("Natural Magick Co-Op",               "Retail",               None),
    ("Ben Ralph",                           "Real Estate",          "real-estate-development"),
    ("Safeway Certifications",              "Consulting / PR",      None),
    ("Austin FC",                           "Entertainment",        "hospitality-entertainment"),
    ("Alori Properties",                    "Real Estate",          "real-estate-development"),
    ("Pecan Street Association",            "Nonprofit",            None),
    ("Pecan Street Advisors",               "Consulting / PR",      None),
    ("Stonewall Democrats of Austin PAC",   "Nonprofit",            "progressive-money"),
    ("Liberal Austin Democrats",            "Nonprofit",            "progressive-money"),
    ("Texas Democratic Party",              "Nonprofit",            "progressive-money"),
    ("CWA-COPE PCC",                        "Labor",                "progressive-money"),
    ("Austinites for Equity",               "Nonprofit",            "progressive-money"),
    ("Downtown Austin Alliance",            "Nonprofit",            None),
    ("Austin Creative Alliance",            "Nonprofit",            None),
    ("Ballet Austin",                       "Nonprofit",            None),
    ("LCRA",                                "Government",           None),
    ("Teacher Retirement System of Texas",  "Government",           None),
    ("Collective Campaigns",                "Consulting / PR",      "political-consulting|progressive-money"),
    ("Al Braden Photographer",              "Media",                "progressive-money"),
    ("Ending Community Homelessness Coalition", "Nonprofit",        "progressive-money|homelessness-services"),
    ("Asian American Cultural Center",      "Nonprofit",            "progressive-money"),
    ("Girls Empowerment Network",           "Nonprofit",            "progressive-money"),
    ("Progress Texas",                      "Nonprofit",            "progressive-money"),
    ("Texas Civil Rights Project",          "Nonprofit",            "progressive-money"),
    ("GRASSROOTS LEADERSHIP",               "Nonprofit",            "progressive-money"),
    ("Texas Health Action",                 "Healthcare",           "progressive-money"),
    ("Capital Factory",                     "Nonprofit",            "tech-startup-ecosystem|progressive-money"),
    ("Creating Common Ground",              "Nonprofit",            "progressive-money"),
    ("PODER",                               "Nonprofit",            "progressive-money"),
    ("Just Liberty",                        "Nonprofit",            "progressive-money"),
    ("BikeTexas",                           "Nonprofit",            "progressive-money|transit-trails"),
    ("Ground Game Texas",                   "Nonprofit",            "progressive-money"),
    ("Charles Schwab",                      "Finance",              None),
    ("Microsoft",                           "Technology",           "tech-startup-ecosystem"),
    ("SalesForce",                          "Technology",           "tech-startup-ecosystem"),
    ("Facebook",                            "Technology",           "tech-startup-ecosystem"),
    ("Holland & Knight",                    "Legal",                None),
    ("Smith Robertson",                     "Legal",                None),
    ("Coats Rose P.C.",                     "Legal",                "real-estate-development"),
    ("DUGGINS WREN MANN & ROMERO",          "Legal",                None),
    ("Perales Allmon & Ice",                "Legal",                None),
    ("Goranson Bain Ausley",                "Legal",                None),
    ("Eric Winters Goff LLC",               "Legal",                None),
    ("Coleman & Assoc",                     "Legal",                "real-estate-development"),
    ("Huitt Zollars",                       "Engineering",          None),
    ("STG Design",                          "Architecture",         "real-estate-development"),
    ("MWM DesignGroup",                     "Architecture",         "real-estate-development"),
    ("Asakura Robinson",                    "Engineering",          None),
    ("Cushman & Wakefield",                 "Real Estate",          "real-estate-development"),
    ("W2 Real Estate Partners",             "Real Estate",          "real-estate-development"),
    ("Greystar",                            "Real Estate",          "real-estate-development|multifamily-housing"),
    ("DMA Development Company",             "Real Estate",          "real-estate-development"),
    ("Barshop & Oles",                      "Real Estate",          "real-estate-development"),
    ("El Buen Samaritano",                  "Nonprofit",            "progressive-money"),
    ("Capital A Housing",                   "Nonprofit",            "progressive-money"),
    ("Foundation Communities",              "Nonprofit",            "progressive-money"),
    ("Every Texan",                         "Nonprofit",            "progressive-money"),
    ("Red Line Parkway Initiative",         "Nonprofit",            "progressive-money|transit-trails|urbanist"),
    ("GAVA",                                "Nonprofit",            "progressive-money|health-equity"),
    ("ECHO",                                "Nonprofit",            "progressive-money|homelessness-services"),
    ("Farm & City",                         "Nonprofit",            "progressive-money|yimby|urbanist"),
    ("Buie & Co",                           "Consulting / PR",      "political-consulting"),
    ("Thrower Design",                      "Consulting / PR",      "real-estate-development"),
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

# Final unknown count
cur.execute("""
    SELECT canonical_name, record_count FROM employer_identities
    WHERE industry IS NULL AND record_count >= 5
    ORDER BY record_count DESC
""")
remaining = cur.fetchall()
noise = {"requested","not required","texas","nonprofit","home","anonymous","owner",
         "principal","stay at home mom","quality assurance","various","unknown","none",
         "self","retired","writer","state","austin","various","n/a"}
genuine = [(n, c) for n, c in remaining
           if "/" not in n and len(n.strip()) > 3
           and n.lower().strip() not in noise]

print(f"Remaining genuinely unknown (5+ records): {len(genuine)}")
for i, (n, c) in enumerate(genuine[:40], 1):
    print(f"  {i:>3}. [{c:3d}] {n}")

cur.execute("SELECT SUM(record_count) FROM employer_identities WHERE industry IS NOT NULL")
cr = cur.fetchone()[0] or 0
cur.execute("SELECT SUM(record_count) FROM employer_identities")
total = cur.fetchone()[0]
print(f"\nRecord coverage: {cr:,} / {total:,} = {cr/total*100:.1f}%")
conn.close()
