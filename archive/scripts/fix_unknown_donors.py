"""
Recover Qadri unknown donors in two phases:

Phase 1 - Create "Self-Employed" and "Not Employed" employer identities,
           then wire campaign_finance records to them.

Phase 2 - Classify recoverable employer strings that are real businesses
           not yet in the employer_identities table (or matched with wrong canonical).
"""

import sqlite3, sys, io, re, uuid
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# ── Phase 1: Self-employed + Not Employed categories ─────────────────────────

SELF_EMP_STRINGS = {
    "self", "self employed", "self-employed", "self employed", "self-employed",
    "selfemployed", "self employ", "self - employed", "self employment",
    "self empolyed", "self employd", "independent", "independent contractor",
    "freelance", "freelancer", "sole proprietor",
}

NOT_EMPLOYED_STRINGS = {
    "not employed", "not-employed", "notemployed", "unemployed", "n/a",
    "na", "none", "not applicable", "", "retired", "student", "homemaker",
    "stay at home", "stay-at-home", "sahm", "volunteer", "not required",
}

def make_employer(canonical, industry, tags=None, record_count=0):
    """Insert a synthetic employer_identity if it doesn't exist."""
    cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name=?", (canonical,))
    row = cur.fetchone()
    if row:
        # Ensure it's classified
        cur.execute("UPDATE employer_identities SET industry=?, interest_tags=? WHERE canonical_name=?",
                    (industry, tags, canonical))
        return row[0]
    eid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO employer_identities (employer_id, canonical_name, industry, interest_tags, record_count)
        VALUES (?, ?, ?, ?, ?)
    """, (eid, canonical, industry, tags, record_count))
    return eid

# Create the two synthetic employers
self_emp_id  = make_employer("Self-Employed",  "Individual", "self-employed")
not_emp_id   = make_employer("Not Employed",   "Individual", "not-employed")
conn.commit()
print(f"Self-Employed employer_id: {self_emp_id}")
print(f"Not Employed  employer_id: {not_emp_id}")

# Wire campaign_finance records for self-employed patterns
def wire_strings(target_strings, employer_id, label):
    updated = 0
    for raw in target_strings:
        for variant in [raw, raw.title(), raw.upper(), raw.capitalize()]:
            cur.execute("""
                UPDATE campaign_finance
                SET employer_id = ?
                WHERE employer_id IS NULL
                  AND TRIM(LOWER(donor_reported_employer)) = ?
            """, (employer_id, raw.lower().strip()))
        updated += cur.rowcount
    conn.commit()
    print(f"  Wired {cur.rowcount} → {label}  (ran {len(target_strings)} patterns)")

# Self-employed
updated_self = 0
for s in SELF_EMP_STRINGS:
    cur.execute("""
        UPDATE campaign_finance SET employer_id=?
        WHERE employer_id IS NULL
          AND TRIM(LOWER(COALESCE(donor_reported_employer,''))) = ?
    """, (self_emp_id, s))
    updated_self += cur.rowcount

conn.commit()
print(f"Self-Employed wired: {updated_self} records")

# Not employed (including retired, student, blank)
updated_not = 0
for s in NOT_EMPLOYED_STRINGS:
    cur.execute("""
        UPDATE campaign_finance SET employer_id=?
        WHERE employer_id IS NULL
          AND TRIM(LOWER(COALESCE(donor_reported_employer,''))) = ?
    """, (not_emp_id, s))
    updated_not += cur.rowcount

# Also wire NULL employer field
cur.execute("""
    UPDATE campaign_finance SET employer_id=?
    WHERE employer_id IS NULL
      AND (donor_reported_employer IS NULL OR TRIM(donor_reported_employer) = '')
""", (not_emp_id,))
updated_not += cur.rowcount
conn.commit()
print(f"Not Employed  wired: {updated_not} records")

# ── Phase 2: Classify recoverable real employers ──────────────────────────────
# These are real businesses with recognizable names that just weren't in our DB

recoverable = [
    # (raw_string,               canonical,                      industry,           tags)
    ("latakoo",                  "Latakoo",                      "Technology",       "tech-startup-ecosystem"),
    ("Volkswagen Group of America","Volkswagen",                  "Technology",       None),
    ("Bhojani Law PLLC",         "Bhojani Law PLLC",             "Legal",            None),
    ("LSI",                      "LSI",                          "Technology",       None),
    ("Capsule",                  "Capsule",                      "Technology",       "tech-startup-ecosystem"),
    ("cornerstone on demand",    "Cornerstone OnDemand",         "Technology",       "tech-startup-ecosystem"),
    ("United air",               "United Airlines",              "Transportation",   None),
    ("UTIMCO",                   "UTIMCO",                       "Finance",          "higher-education"),
    ("Texas HDC",                "Texas HDC",                    "Nonprofit",        "progressive-money"),
    ("Terry Black's Barbecue",   "Terry Black's BBQ",            "Hospitality / Entertainment","hospitality-entertainment"),
    ("Terry Black's BBQ",        "Terry Black's BBQ",            "Hospitality / Entertainment","hospitality-entertainment"),
    ("Submersive",               "Submersive",                   "Technology",       "tech-startup-ecosystem"),
    ("Spencer Fane",             "Spencer Fane",                 "Legal",            None),
    ("Shawarma Point",           "Shawarma Point",               "Hospitality / Entertainment","hospitality-entertainment"),
    ("RP Holdings",              "RP Holdings",                  "Real Estate",      "real-estate-development"),
    ("Q & S Institute",          "Q & S Institute",              "Education",        None),
    ("Prequel LLC",              "Prequel LLC",                  "Technology",       "tech-startup-ecosystem"),
    ("Pearlstonepartners",       "Pearlstone Partners",          "Finance",          "real-estate-development"),
    ("Patient Privacy Rights",   "Patient Privacy Rights",       "Nonprofit",        None),
    ("Outreach Strategists LLC", "Outreach Strategists",         "Consulting / PR",  "political-consulting"),
    ("Museum of Ice Cream",      "Museum of Ice Cream",          "Hospitality / Entertainment","hospitality-entertainment"),
    ("Mana Foods",               "Mana Foods",                   "Retail",           None),
    ("Kyle ER",                  "Kyle ER",                      "Healthcare",       None),
    ("Kiva",                     "Kiva",                         "Nonprofit",        "progressive-money"),
    ("Greysteel",                "Greysteel",                    "Real Estate",      "real-estate-development"),
    ("Flintco",                  "Flintco",                      "Construction",     None),
    ("DPS",                      "DPS",                          "Government",       None),
    ("Culhane Meadows",          "Culhane Meadows",              "Legal",            None),
    ("Club Capital",             "Club Capital",                 "Finance",          None),
    ("ColinaWest",               "Colina West",                  "Real Estate",      "real-estate-development"),
    ("CharityStack",             "CharityStack",                 "Technology",       "progressive-money"),
    ("Capital A",                "Capital A Housing",            "Nonprofit",        "progressive-money"),
    ("Cap A Housing",            "Capital A Housing",            "Nonprofit",        "progressive-money"),
    ("C3 Presents/Live Nation",  "Live Nation",                  "Hospitality / Entertainment","hospitality-entertainment"),
    ("Brick Row",                "Brick Row",                    "Real Estate",      "real-estate-development"),
    ("Big Plan",                 "Big Plan",                     "Consulting / PR",  None),
    ("Abraham Watkins Nichols Agosto Aziz & Stogner", "Abraham Watkins", "Legal",   None),
    ("UH",                       "University of Houston",        "Education",        "higher-education"),
    ("Hologic",                  "Hologic",                      "Healthcare",       None),
    ("AM Capital",               "AM Capital",                   "Finance",          "real-estate-development"),
    ("Austin TeamCo LLC",        "Austin TeamCo LLC",            "Hospitality / Entertainment","hospitality-entertainment"),
    ("Austin TeamCo",            "Austin TeamCo LLC",            "Hospitality / Entertainment","hospitality-entertainment"),
    ("Benchmark",                "Benchmark",                    "Finance",          "tech-startup-ecosystem"),
    ("true insurance solutions", "True Insurance Solutions",     "Finance",          None),
    ("True insurance solutions", "True Insurance Solutions",     "Finance",          None),
    ("Straub Services",          "Straub Services",              "Construction",     None),
    ("Worlds Gold & Diamonds Inc","Worlds Gold & Diamonds",      "Retail",           None),
    ("VKD",                      "VKD",                          "Real Estate",      "real-estate-development"),
    ("EMG",                      "EMG",                          "Consulting / PR",  None),
    ("ACS",                      "ACS",                          "Technology",       None),
    ("AM Capital",               "AM Capital",                   "Finance",          "real-estate-development"),
    ("Chegoonian Enterprises",   "Chegoonian Enterprises",       "Real Estate",      "real-estate-development"),
    ("RE",                       None,                           None,               None),  # skip - too ambiguous
    ("GC",                       None,                           None,               None),  # skip - too ambiguous
]

wired_phase2 = 0
for raw, canonical, industry, tags in recoverable:
    if canonical is None:
        continue

    # Ensure employer_identities has this entry
    cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name=?", (canonical,))
    row = cur.fetchone()
    if row:
        eid = row[0]
        if industry:
            cur.execute("UPDATE employer_identities SET industry=?, interest_tags=? WHERE employer_id=? AND industry IS NULL",
                        (industry, tags, eid))
    else:
        eid = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO employer_identities (employer_id, canonical_name, industry, interest_tags, record_count)
            VALUES (?, ?, ?, ?, 0)
        """, (eid, canonical, industry, tags))

    # Wire campaign_finance records
    cur.execute("""
        UPDATE campaign_finance SET employer_id=?
        WHERE employer_id IS NULL
          AND TRIM(donor_reported_employer) = ?
    """, (eid, raw))
    wired_phase2 += cur.rowcount

conn.commit()
print(f"Phase 2 wired: {wired_phase2} records with real employer classifications")

# ── Results ───────────────────────────────────────────────────────────────────
print()
print("=== QADRI UNKNOWN BUCKET AFTER FIX ===")
cur.execute("""
    SELECT
        COALESCE(ei.industry, 'Unknown') as bucket,
        COALESCE(ei.interest_tags, '') as tags,
        COUNT(*) as n,
        SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)) as total
    FROM campaign_finance cf
    LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    WHERE cf.recipient LIKE '%Qadri%' AND cf.contribution_year >= 2022
    GROUP BY bucket, tags
    ORDER BY total DESC
""")
grand_total = 0
rows = cur.fetchall()
for r in rows:
    grand_total += r[3] or 0

print(f"{'Bucket':<35} {'Amount':>10}  {'%':>5}  {'Records':>7}")
print("-" * 65)
for r in rows:
    pct = (r[3] or 0) / grand_total * 100
    print(f"{r[0]:<35} ${r[3]:>9,.0f}  {pct:>4.1f}%  {r[2]:>7}")

print(f"\nTotal: ${grand_total:,.0f}")

# Remaining truly unknown (no employer_id, not self/not-employed)
cur.execute("""
    SELECT COUNT(*), SUM(COALESCE(balanced_amount, contribution_amount))
    FROM campaign_finance cf
    WHERE cf.recipient LIKE '%Qadri%'
      AND cf.employer_id IS NULL
      AND cf.contribution_year >= 2022
""")
r = cur.fetchone()
print(f"\nStill unmatched (employer_id=NULL): {r[0]} records, ${r[1] or 0:,.0f}")

conn.close()
