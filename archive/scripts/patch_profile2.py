import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

html = open('profile_qadri.html', encoding='utf-8').read()
donations = open('qadri_all_donations.json', encoding='utf-8').read()

# ── New INTEREST_GROUPS ───────────────────────────────────────────────────────
NEW_IG = """const INTEREST_GROUPS = [
  // Non-employer categories (shown in bars, excluded from donut)
  {"label":"Not Employed",            "donors":494,  "total":88921,  "color":"#6b7280", "noDonut":true},
  {"label":"Self-Employed",           "donors":109,  "total":23436,  "color":"#78716c", "noDonut":true},
  {"label":"Student",                 "donors":8,    "total":660,    "color":"#38bdf8", "noDonut":true},
  {"label":"Unknown / Unclassified",  "donors":21,   "total":4205,   "color":"#1f2937", "noDonut":true},
  // Industry-affiliated (shown in donut + bars)
  {"label":"Real Estate",             "donors":249,  "total":74893,  "color":"#f59e0b"},
  {"label":"Technology",              "donors":508,  "total":71849,  "color":"#4f8ef7"},
  {"label":"Legal",                   "donors":223,  "total":53693,  "color":"#a78bfa"},
  {"label":"Nonprofit / Advocacy",    "donors":466,  "total":51309,  "color":"#34d399"},
  {"label":"Healthcare",              "donors":212,  "total":36886,  "color":"#f472b6"},
  {"label":"Consulting / PR",         "donors":196,  "total":29127,  "color":"#94a3b8"},
  {"label":"Government",              "donors":196,  "total":25801,  "color":"#818cf8"},
  {"label":"Finance",                 "donors":139,  "total":24406,  "color":"#fbbf24"},
  {"label":"Education",               "donors":181,  "total":23146,  "color":"#22d3ee"},
  {"label":"Engineering",             "donors":123,  "total":20535,  "color":"#6b7280"},
  {"label":"Hospitality / Events",    "donors":89,   "total":15007,  "color":"#fb923c"},
  {"label":"Construction",            "donors":33,   "total":13250,  "color":"#d97706"},
  {"label":"Energy / Environment",    "donors":47,   "total":7500,   "color":"#ef4444"},
  {"label":"Retail / Media / Other",  "donors":174,  "total":22799,  "color":"#374151"},
];"""

# ── New NOTABLE_FIRMS ─────────────────────────────────────────────────────────
NEW_NF = """const NOTABLE_FIRMS = [
  {"firm":"Endeavor Real Estate",   "industry":"Real Estate",  "tags":"real-estate-development",  "donors":25,"total":17420},
  {"firm":"Armbrust & Brown",       "industry":"Legal",        "tags":"real-estate-development",  "donors":23,"total":17300},
  {"firm":"City of Austin",         "industry":"Government",   "tags":"",                          "donors":21,"total":7269},
  {"firm":"InKind",                 "industry":"Technology",   "tags":"tech-startup-ecosystem",    "donors":9, "total":7000},
  {"firm":"Riverside",              "industry":"Real Estate",  "tags":"real-estate-development",   "donors":9, "total":5900},
  {"firm":"Civilitude",             "industry":"Engineering",  "tags":"real-estate-development",   "donors":10,"total":5290},
  {"firm":"Harutunian Engineering", "industry":"Engineering",  "tags":"",                          "donors":5, "total":4500},
  {"firm":"University of Texas",    "industry":"Education",    "tags":"higher-education",           "donors":27,"total":4207},
  {"firm":"Texas Legislature",      "industry":"Government",   "tags":"",                          "donors":18,"total":4131},
  {"firm":"Travis County",          "industry":"Government",   "tags":"",                          "donors":14,"total":3971},
  {"firm":"Ascension Seton",        "industry":"Healthcare",   "tags":"",                          "donors":6, "total":3275},
  {"firm":"Presidium",              "industry":"Real Estate",  "tags":"real-estate-development",   "donors":3, "total":2700},
  {"firm":"Broadview Capital",      "industry":"Finance",      "tags":"real-estate-development",   "donors":3, "total":2700},
  {"firm":"Journeyman Construction","industry":"Construction", "tags":"real-estate-development",   "donors":2, "total":2700},
  {"firm":"Encotech",               "industry":"Engineering",  "tags":"real-estate-development",   "donors":4, "total":2650},
  {"firm":"State of Texas",         "industry":"Government",   "tags":"",                          "donors":7, "total":2275},
  {"firm":"HillCo Partners",        "industry":"Consulting",   "tags":"political-consulting",      "donors":3, "total":1850},
  {"firm":"Rice University",        "industry":"Education",    "tags":"higher-education",           "donors":3, "total":1775},
  {"firm":"HDR Engineering",        "industry":"Engineering",  "tags":"",                          "donors":3, "total":1700},
  {"firm":"C3 Presents",            "industry":"Entertainment","tags":"hospitality-entertainment",  "donors":3, "total":1600},
];"""

# ── New TOP_DONORS ─────────────────────────────────────────────────────────────
NEW_TD = """const TOP_DONORS = [
  {"name":"Poteet, Brian",    "employer":"Cutsforth Inc",         "tags":"tech-startup-ecosystem", "total":1650,"count":8},
  {"name":"Ali, Jawad",       "employer":"Ascension Seton",       "tags":"",                       "total":1600,"count":4},
  {"name":"Ahmed, Shakeel",   "employer":"Not Employed",          "tags":"not-employed",           "total":1560,"count":4},
  {"name":"Handal, Edgar",    "employer":"NVIDIA",                "tags":"tech-startup-ecosystem", "total":1500,"count":7},
  {"name":"Siddiqui, Eiman",  "employer":"American Express",      "tags":"",                       "total":1500,"count":5},
  {"name":"Dadoush, Hashem",  "employer":"Kyle ER",               "tags":"",                       "total":1450,"count":5},
  {"name":"Kazi, Fayez",      "employer":"Civilitude",            "tags":"real-estate-development","total":1400,"count":4},
  {"name":"Khan, Aayla",      "employer":"Rutgers University",    "tags":"higher-education",       "total":1400,"count":4},
  {"name":"Mehdi, Wafa",      "employer":"Baylor Scott & White",  "tags":"",                       "total":1400,"count":20},
  {"name":"Qadri, Zara",      "employer":"MD Anderson",           "tags":"",                       "total":1400,"count":6},
  {"name":"Qazi, Sheheryaar", "employer":"CGI",                   "tags":"tech-startup-ecosystem", "total":1400,"count":6},
  {"name":"Rana, Ayesha",     "employer":"DPS (Govt.)",           "tags":"",                       "total":1400,"count":6},
  {"name":"Shakeel, Haris",   "employer":"Delta Hotels",          "tags":"hospitality-entertainment","total":1400,"count":20},
  {"name":"Wang, Shenghao",   "employer":"Eversheds Sutherland",  "tags":"",                       "total":1400,"count":6},
  {"name":"Baqai, Maheen",    "employer":"Linda Welsh Realty",    "tags":"real-estate-development","total":1350,"count":5},
  {"name":"Bhojani, Salman",  "employer":"Bhojani Law PLLC",      "tags":"",                       "total":1350,"count":3},
  {"name":"Kahn, David",      "employer":"ColinaWest Real Estate","tags":"real-estate-development","total":1350,"count":3},
  {"name":"Malik, Zeeshan",   "employer":"Malik Legal Group",     "tags":"",                       "total":1350,"count":3},
];"""

# ── Apply regex replacements ──────────────────────────────────────────────────
for pat, replacement in [
    (r'const INTEREST_GROUPS = \[[\s\S]+?\];', NEW_IG),
    (r'const NOTABLE_FIRMS = \[[\s\S]+?\];', NEW_NF),
    (r'const TOP_DONORS = \[[\s\S]+?\];', NEW_TD),
    (r'const ALL_DONATIONS = \[[\s\S]+?\];', 'const ALL_DONATIONS = ' + donations + ';'),
]:
    new_html = re.sub(pat, replacement, html, count=1, flags=re.DOTALL)
    if new_html == html:
        print(f'MISS: {pat[:50]}')
    else:
        print(f'OK:   {pat[:50]}')
        html = new_html

# ── String replacements ───────────────────────────────────────────────────────
string_patches = [
    (
        'person-level industry &middot; 99.3% classified',
        'person-level industry &middot; 99.3% classified'
    ),
    (
        '98.3% of donors classified',
        'person-level industry &middot; 99.3% classified'
    ),
    (
        'employer-affiliated donors only &middot; 69.3% of total raised',
        'employer-affiliated donors &middot; 80.1% of total raised'
    ),
    (
        'employer-affiliated donors only · 69.3% of total raised',
        'employer-affiliated donors · 80.1% of total raised'
    ),
    (
        '>18.6%<',
        '>12.7%<'
    ),
]
for old, new in string_patches:
    if old in html:
        html = html.replace(old, new, 1)
        print(f'OK str: {old[:60]}')

# methodology note
OLD_NOTE = 'Campaign finance records are sourced from Austin City Clerk filings. Donors are matched to\n      employer identities using fuzzy name matching; employers are classified by industry and political\n      interest group. <strong style="color:var(--text)">99.2% of contribution dollars are now classified</strong>'
NEW_NOTE_START = 'Campaign finance records are sourced from Austin City Clerk filings. Each donor is resolved to a person-level identity\n      &mdash; their full giving history across all campaigns determines their primary industry, so a freelance data engineer\n      who listed &ldquo;Not Employed&rdquo; is still attributed to Technology based on occupation signals.\n      <strong style="color:var(--text)">99.3% of contribution dollars are classified</strong>'

if OLD_NOTE in html:
    html = html.replace(OLD_NOTE, NEW_NOTE_START, 1)
    print('OK: methodology start')

# Fix the rest of the methodology note
OLD_NOTE2 = '"Individual Donors" (30.7%) captures self-employed, retired, and not-employed donors who gave in a\n      personal capacity rather than through an organized employer network. The funding source donut shows\n      only employer-affiliated industry money. "Firms with 3+ donors" highlights organizations that may have\n      coordinated giving, though individual donations are legally independent.'
NEW_NOTE2 = '"Not Employed" ($89K, 15.1%) reflects donors for whom no sector signal exists across their entire filing history.\n      "Self-Employed" ($23K, 4.0%) are verified independent contractors/freelancers with no determinable sector.\n      The industry donut shows employer-affiliated money (80.1% of total). "Firms with 3+ donors" highlights\n      organizations that may have coordinated giving, though individual donations are legally independent.'

if OLD_NOTE2 in html:
    html = html.replace(OLD_NOTE2, NEW_NOTE2, 1)
    print('OK: methodology body')

with open('profile_qadri.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Done. File size: {len(html.encode())//1024} KB')
