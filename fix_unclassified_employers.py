"""
Fix employer_identities entries that are blocking donor identity resolution.
Two passes:
  1. Classify real named companies/orgs that have industry=NULL
  2. Wire common noise strings (REQUESTED, SELF EMPLOYEED, etc.) to proper noise categories
Then re-run the resolver for all affected donor_ids.
"""
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# ── 1. Real companies with known industries ───────────────────────────────────
COMPANY_FIXES = [
    # Technology
    ("Rubrik",                          "Technology",            "tech-startup-ecosystem"),
    ("Mercado",                         "Technology",            "tech-startup-ecosystem"),
    ("Expedia.com",                     "Technology",            None),
    ("TrainATech",                      "Technology",            "tech-startup-ecosystem"),
    ("Accurate CAD and Technical Services", "Engineering",       None),
    ("Unchained Capital",               "Finance",               "tech-startup-ecosystem"),
    ("Affinity Design",                 "Technology",            None),
    ("Churchill Forge",                 "Technology",            None),

    # Real Estate
    ("Marcus & Millichap",              "Real Estate",           "real-estate-development"),
    ("NRP Group",                       "Real Estate",           "real-estate-development"),
    ("The NRP Group",                   "Real Estate",           "real-estate-development"),
    ("NRP Holdings, Inc., NRP Holdings, LLC", "Real Estate",     "real-estate-development"),
    ("Southern Consolidated LLC",       "Real Estate",           "real-estate-development"),
    ("Arbor Contract Carpet",           "Construction",          None),
    ("Texas Materials",                 "Construction",          None),
    ("Valor Fire Protection",           "Construction",          None),
    ("Redi Carpet",                     "Construction",          None),

    # Healthcare
    ("Greco Dermatology",               "Healthcare",            None),
    ("Terry Black's BBQ",               "Hospitality / Events",  None),

    # Nonprofit / Advocacy
    ("Non Profit",                      "Nonprofit / Advocacy",  None),
    ("Austin Neighborhood Organization","Nonprofit / Advocacy",  None),
    ("AGE of Central Texas",            "Nonprofit / Advocacy",  None),
    ("CAPSA",                           "Nonprofit / Advocacy",  None),
    ("www.hillcountryconservancy.org",  "Nonprofit / Advocacy",  None),
    ("STJones, LLC",                    "Nonprofit / Advocacy",  None),

    # Energy
    ("Customized Energy Solutions",     "Energy / Environment",  None),

    # Government
    ("Government Affairs",              "Government",            None),
    ("State Government",                "Government",            None),
    ("US POSTAL SERVICE",               "Government",            None),

    # Media / Retail
    ("Austin American-Statesmn",        "Retail / Media / Other","media"),
    ("Neiman Marcus",                   "Retail / Media / Other","retail"),
    ("Flying Threads",                  "Retail / Media / Other","retail"),
    ("TC Bar",                          "Hospitality / Events",  None),
    ("Stitch Fix",                      "Retail / Media / Other","retail"),

    # Finance
    ("Watkins Insurance",               "Finance",               None),
    ("The Madwave Trust",               "Finance",               None),
]

updated = 0
for canonical, industry, tags in COMPANY_FIXES:
    cur.execute(
        "UPDATE employer_identities SET industry=?, interest_tags=? WHERE canonical_name=?",
        (industry, tags, canonical)
    )
    if cur.rowcount:
        print(f"  OK  [{canonical}] → {industry}")
        updated += cur.rowcount
print(f"\nCompany fixes: {updated} rows")

# ── 2. Noise strings → proper noise categories ────────────────────────────────
# Get canonical IDs for Self-Employed and Not Employed
cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name='Not Employed'")
not_emp_id = cur.fetchone()[0]
cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name='Self-Employed'")
self_emp_id = cur.fetchone()[0]

# Entries that should be classified directly on the employer_identities record
NOISE_FIXES = [
    # Not Employed
    ("REQUESTED",                       "Not Employed",  "not-employed"),
    ("Stay at Home Mom",                "Not Employed",  "not-employed"),
    ("Not Required",                    "Not Employed",  "not-employed"),
    ("**Best Effort to locate",         "Not Employed",  "not-employed"),
    ("Community Volunteer",             "Not Employed",  "not-employed"),
    ("Volunteer",                       "Not Employed",  "not-employed"),
    ("Not working",                     "Not Employed",  "not-employed"),
    ("Private",                         "Self-Employed", "self-employed"),

    # Self-Employed / job-title-as-employer
    ("SELF EMPLOYEED",                  "Self-Employed", "self-employed"),
    ("Self / Self",                     "Self-Employed", "self-employed"),
    ("Co-Founder",                      "Self-Employed", "self-employed"),
    ("Managing Principal",              "Self-Employed", "self-employed"),
    ("Executive Director",              "Nonprofit / Advocacy", None),
    ("Government",                      "Government",    None),
]

noise_updated = 0
for canonical, industry, tags in NOISE_FIXES:
    cur.execute(
        "UPDATE employer_identities SET industry=?, interest_tags=? WHERE canonical_name=?",
        (industry, tags, canonical)
    )
    if cur.rowcount:
        print(f"  OK  [{canonical}] → {industry}")
        noise_updated += cur.rowcount
print(f"\nNoise fixes: {noise_updated} rows")

conn.commit()

# ── 3. Re-resolve affected donor_ids ─────────────────────────────────────────
print("\nRe-resolving affected donor_ids...")

from collections import defaultdict
import re

NOISE_INDUSTRIES = {"Not Employed", "Self-Employed", "Student", "Unknown", "Individual", None}
NOISE_EMPLOYERS = {
    "not employed", "not-employed", "self employed", "self-employed",
    "(self employed)", "selfemployed", "retired", "student", "homemaker",
    "stay at home", "unemployed", "n/a", "na", "none", "", "not applicable",
    "freelance", "freelancer", "independent", "independent contractor",
    "sole proprietor", "self", "myself", "business owner", "owner",
}

OCC_RULES = [
    (r'\bdata\s*(engineer|scientist|analyst|director|manager|architect)\b', "Technology"),
    (r'\bsoftware\s*(engineer|developer|architect|manager|lead)\b',         "Technology"),
    (r'\b(product|program|engineering)\s*manager\b',                        "Technology"),
    (r'\b(full.?stack|frontend|backend|web|mobile)\s*developer\b',          "Technology"),
    (r'\b(devops|sre|cloud|platform|infrastructure)\s*(engineer)?\b',       "Technology"),
    (r'\b(ux|ui)\s*(designer|researcher|engineer|lead)\b',                  "Technology"),
    (r'\bcybersecurity\b|\binfosec\b|\bsecurity\s*engineer\b',              "Technology"),
    (r'\bml\s*engineer\b|\bmachine\s*learning\b|\bai\s*(engineer|researcher)\b', "Technology"),
    (r'\btech(nology)?\s*(director|executive|lead|consultant)\b',           "Technology"),
    (r'\bcomputer\s*(scientist|engineer|programmer)\b',                     "Technology"),
    (r'\bit\s*(director|manager|specialist|consultant)\b',                  "Technology"),
    (r'\bprogrammer\b|\bcoder\b',                                           "Technology"),
    (r'\bphysician\b|\bdoctor\b|\b(family|internal)\s*medicine\b',          "Healthcare"),
    (r'\b(registered\s*)?nurse\b|\bRN\b|\bNP\b|\bCRNA\b|\bCRNP\b',          "Healthcare"),
    (r'\bdentist\b|\bdds\b|\bdmd\b|\bdental\b',                             "Healthcare"),
    (r'\bpharmacist\b|\bpharmd\b',                                          "Healthcare"),
    (r'\b(physical|occupational|speech.language)\s*therapist\b',            "Healthcare"),
    (r'\bpsychologist\b|\bpsychiatrist\b|\bLCSW\b|\bLPC\b|\btherapist\b',   "Healthcare"),
    (r'\bsurgeon\b|\borthopaedic\b|\bcardiol\b|\bneurolog\b',               "Healthcare"),
    (r'\boptometrist\b|\bophthalmologist\b',                                "Healthcare"),
    (r'\bchiropractor\b',                                                   "Healthcare"),
    (r'\bhealthcare\s*(admin|exec|director|manager|consultant)\b',          "Healthcare"),
    (r'\bpublic\s*health\b|\bepidemiolog\b',                                "Healthcare"),
    (r'\bveterinar\b|\bDVM\b',                                              "Healthcare"),
    (r'\bmedical\s*(director|officer|researcher|writer)\b',                 "Healthcare"),
    (r'\bPA-C\b|\bphysician\s*assistant\b',                                 "Healthcare"),
    (r'\battorney\b|\blawyer\b|\bcounsel\b|\besq\.?\b',                     "Legal"),
    (r'\bparalegal\b|\blegal\s*(assistant|secretary)\b',                    "Legal"),
    (r'\bjudge\b|\bmagistrate\b|\bjustice\b',                               "Legal"),
    (r'\blaw\s*(clerk|professor|student)\b',                                "Legal"),
    (r'\bprofessor\b|\bfaculty\b|\blecturer\b|\bassoc\.\s*prof\b',          "Education"),
    (r'\bteacher\b|\beducator\b|\bteaching\s*assistant\b|\binstructor\b',   "Education"),
    (r'\bprincipal\b|\bsuperintendent\b|\bschool\s*(admin|director)\b',     "Education"),
    (r'\b(academic|education)\s*(research|director|dean|coordinator)\b',    "Education"),
    (r'\bcurriculum\b|\beducation\s*policy\b',                              "Education"),
    (r'\bstate\s*rep(resentative)?\b|\blegislator\b|\bsenator\b',           "Government"),
    (r'\bcity\s*(council|manager|planner|official|employee)\b',             "Government"),
    (r'\bfederal\s*(employee|agent|officer|official)\b',                    "Government"),
    (r'\bpolice\s*(officer|chief|detective|captain)\b',                     "Government"),
    (r'\bfire(fighter|man|woman|captain)\b|\bfire\s*dept\b',                "Government"),
    (r'\bmilitary\b|\bnavy\b|\barmy\b|\bair\s*force\b|\bUSN\b|\bUSAF\b',    "Government"),
    (r'\bpublic\s*(administrator|servant|official|policy)\b',               "Government"),
    (r'\baccountant\b|\bcpa\b|\bCFO\b|\bauditor\b',                         "Finance"),
    (r'\bfinancial\s*(advisor|planner|analyst|consultant|director)\b',      "Finance"),
    (r'\bbanker\b|\bbank\s*(officer|manager|executive)\b',                  "Finance"),
    (r'\binsurance\s*(agent|broker|adjuster|exec)\b',                       "Finance"),
    (r'\binvestment\s*(banker|analyst|manager|advisor)\b',                  "Finance"),
    (r'\bCFA\b|\bCFP\b|\bwealth\s*manager\b',                               "Finance"),
    (r'\bventure\s*(capitalist|partner)\b|\bVC\b',                          "Finance"),
    (r'\brealtor\b|\breal\s*estate\s*(agent|broker|investor)\b',            "Real Estate"),
    (r'\bproperty\s*(manager|developer|investor|owner)\b',                  "Real Estate"),
    (r'\bmortgage\s*(broker|banker|officer)\b',                             "Real Estate"),
    (r'\b(civil|structural|mechanical|electrical|environmental|chemical)\s*engineer\b', "Engineering"),
    (r'\barchitect\b(?!ure)',                                               "Engineering"),
    (r'\burban\s*(planner|designer)\b',                                     "Engineering"),
    (r'\bpolitical\s*(consultant|strategist|director|operativ)\b',          "Consulting / PR"),
    (r'\bpublic\s*relations\b|\bpr\s*(director|manager|exec)\b',            "Consulting / PR"),
    (r'\blobbyist\b|\bgovernmental\s*affairs\b|\bpublic\s*affairs\b',       "Consulting / PR"),
    (r'\bmanagement\s*consultant\b|\bconsulting\b',                         "Consulting / PR"),
    (r'\bnonprofit\b|\bnon.profit\b|\b501c\b',                              "Nonprofit / Advocacy"),
    (r'\bcommunity\s*organizer\b|\badvocacy\b|\bactivist\b',                "Nonprofit / Advocacy"),
    (r'\bsocial\s*(worker|services)\b',                                     "Nonprofit / Advocacy"),
    (r'\bjournalist\b|\breporter\b|\bnewspaper\b|\bnews\s*anchor\b',        "Retail / Media / Other"),
    (r'\bwriter\b|\bauthor\b|\beditor\b|\bcopywriter\b',                    "Retail / Media / Other"),
    (r'\bfilmmaker\b|\bvideographer\b',                                     "Retail / Media / Other"),
    (r'\bphotographer\b|\bphotojournalist\b',                               "Retail / Media / Other"),
    (r'\bpodcast(er)?\b|\bcontent\s*creator\b',                             "Retail / Media / Other"),
    (r'\bchef\b|\bcook\b|\bculi\b|\bpastry\b',                              "Hospitality / Events"),
    (r'\brestaurant\s*(owner|manager)\b',                                   "Hospitality / Events"),
    (r'\bhotel\s*(manager|exec|director)\b',                                "Hospitality / Events"),
    (r'\bmusician\b|\bperformer\b|\bactor\b|\bcomposer\b',                  "Hospitality / Events"),
    (r'\bevent\s*(planner|coordinator|manager)\b',                          "Hospitality / Events"),
    (r'\benergy\s*(engineer|analyst|consultant|manager|exec)\b',            "Energy / Environment"),
    (r'\b(petroleum|oil\s*&?\s*gas|upstream|downstream)\b',                 "Energy / Environment"),
    (r'\brenewable\b|\bsolar\b|\bwind\s*energy\b|\bclean\s*energy\b',       "Energy / Environment"),
    (r'\bgeologist\b|\bgeophysicist\b',                                     "Energy / Environment"),
    (r'\bcontractor\b|\bconstruction\s*(manager|exec|superintendent)\b',    "Construction"),
    (r'\bplumber\b|\belectrician\b|\bcarpenter\b|\bHVAC\b',                 "Construction"),
]
OCC_COMPILED = [(re.compile(p, re.I), ind) for p, ind in OCC_RULES]

def infer_from_occupation(occ_str):
    if not occ_str:
        return None
    s = occ_str.strip().lower()
    if s in ("not employed", "not applicable", "n/a", "na", "none", "", "retired",
             "student", "homemaker", "stay at home", "unemployed", "freelance",
             "self employed", "self-employed", "business owner", "owner",
             "independent contractor", "independent"):
        return None
    for pattern, industry in OCC_COMPILED:
        if pattern.search(occ_str):
            return industry
    return None

# Find all donor_ids currently unresolved
cur.execute("SELECT donor_id FROM donor_identities WHERE resolved_industry IS NULL")
unresolved_ids = {r[0] for r in cur.fetchall()}
print(f"  {len(unresolved_ids):,} currently unresolved donor_ids")

# Load their transactions (now with updated employer classifications)
cur.execute("""
    SELECT
        cf.donor_id,
        LOWER(TRIM(COALESCE(cf.donor_reported_employer, ''))) as raw_emp,
        COALESCE(ei.industry, 'Unknown') as industry,
        COALESCE(ei.canonical_name, '') as emp_canonical,
        cf.donor_reported_occupation,
        ROUND(COALESCE(cf.balanced_amount, cf.contribution_amount), 2) as amt
    FROM campaign_finance cf
    LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    WHERE cf.donor_id IN (SELECT donor_id FROM donor_identities WHERE resolved_industry IS NULL)
""")
by_donor = defaultdict(list)
for donor_id, raw_emp, industry, emp_can, occ, amt in cur.fetchall():
    by_donor[donor_id].append((raw_emp, industry, emp_can, occ, amt or 0))

print(f"  {len(by_donor):,} donor_ids to re-evaluate")

updates = []
stats = defaultdict(int)
for donor_id, txns in by_donor.items():
    real = {}
    for raw_emp, industry, emp_can, occ, amt in txns:
        if industry not in NOISE_INDUSTRIES and raw_emp not in NOISE_EMPLOYERS:
            key = (industry, emp_can or raw_emp)
            real[key] = real.get(key, 0) + amt
    if real:
        best_ind, best_emp = max(real, key=lambda k: real[k])
        updates.append((best_ind, best_emp, "employer", donor_id))
        stats["employer"] += 1
        continue

    occ_hits = {}
    for raw_emp, industry, emp_can, occ, amt in txns:
        inf = infer_from_occupation(occ)
        if inf:
            occ_hits[inf] = occ_hits.get(inf, 0) + amt
    if occ_hits:
        best_ind = max(occ_hits, key=lambda k: occ_hits[k])
        occ_str = next((occ for _, _, _, occ, _ in txns if infer_from_occupation(occ) == best_ind), "")
        updates.append((best_ind, occ_str, "occupation", donor_id))
        stats["occupation"] += 1
        continue

    stats["still_unresolved"] += 1

print(f"\n  Newly resolved via employer:    {stats['employer']:,}")
print(f"  Newly resolved via occupation:  {stats['occupation']:,}")
print(f"  Still unresolved:               {stats['still_unresolved']:,}")

cur.executemany("""
    UPDATE donor_identities
    SET resolved_industry=?, resolved_employer_display=?, resolved_confidence=?
    WHERE donor_id=?
""", updates)
conn.commit()
print(f"  Written {len(updates):,} updates to donor_identities")

# ── 4. Spot-check Aaron Gonzales ──────────────────────────────────────────────
print("\n── Spot check: Gonzales, Aaron ──")
cur.execute("""
    SELECT di.donor_id, di.canonical_name, di.canonical_zip,
           di.resolved_industry, di.resolved_employer_display, di.resolved_confidence
    FROM donor_identities di
    WHERE di.canonical_name LIKE '%Gonzales%Aaron%'
""")
for r in cur.fetchall():
    print(f"  {r[0][:8]}  zip={r[2]}  → {r[3]}  via={r[5]}  display=[{r[4]}]")

# ── 5. Updated Qadri breakdown ────────────────────────────────────────────────
print("\n── Qadri breakdown (updated) ──")
cur.execute("""
    SELECT
        COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
        SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)) as total,
        COUNT(DISTINCT cf.donor_id) as donors
    FROM campaign_finance cf
    LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
    WHERE cf.recipient LIKE '%Qadri%' AND cf.contribution_year >= 2022
    GROUP BY 1 ORDER BY 2 DESC
""")
rows = cur.fetchall()
grand = sum(r[1] or 0 for r in rows)
for r in rows:
    pct = (r[1] or 0) / grand * 100
    print(f"  {r[0]:<35} ${r[1]:>9,.0f}  {pct:>5.1f}%  {r[2]:>5} donors")
print(f"  {'TOTAL':<35} ${grand:>9,.0f}")

conn.close()
