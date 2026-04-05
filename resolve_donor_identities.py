"""
Build resolved_industry on donor_identities — per-donor_id only.

Resolution per donor_id using ONLY that identity's own transactions:
  1. Named real employer with known industry (across ALL campaigns for this donor_id)
  2. Occupation string → industry inference
  3. NULL if unresolvable (query falls back to transaction-level employer)

No cross-name merging — that causes false positives when different people
share the same canonical_name.
"""

import sqlite3, sys, io, re
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# ── Add/reset columns ─────────────────────────────────────────────────────────
for col, dtype in [
    ("resolved_industry",        "TEXT"),
    ("resolved_employer_display","TEXT"),
    ("resolved_confidence",      "TEXT"),
]:
    try:
        cur.execute(f"ALTER TABLE donor_identities ADD COLUMN {col} {dtype}")
    except Exception:
        pass

# Reset any previous run
cur.execute("UPDATE donor_identities SET resolved_industry=NULL, resolved_employer_display=NULL, resolved_confidence=NULL")
conn.commit()
print("Columns reset.")

# ── Noise sets ────────────────────────────────────────────────────────────────
NOISE_INDUSTRIES = {"Not Employed", "Self-Employed", "Student", "Unknown", "Individual", None}
NOISE_EMPLOYERS = {
    "not employed", "not-employed", "self employed", "self-employed",
    "(self employed)", "selfemployed", "retired", "student", "homemaker",
    "stay at home", "unemployed", "n/a", "na", "none", "", "not applicable",
    "freelance", "freelancer", "independent", "independent contractor",
    "sole proprietor", "self", "myself", "business owner", "owner",
}

# ── Occupation → industry rules (regex, industry, label) ─────────────────────
OCC_RULES = [
    # Technology
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

    # Healthcare
    (r'\bphysician\b|\bdoctor\b|\b(family|internal)\s*medicine\b',          "Healthcare"),
    (r'\b(registered\s*)?nurse\b|\bRN\b|\bNP\b|\bCRNA\b|\bCRNP\b',          "Healthcare"),
    (r'\bdentist\b|\bdds\b|\bdmd\b|\bdental\b',                             "Healthcare"),
    (r'\bpharmacist\b|\bpharmd\b',                                          "Healthcare"),
    (r'\b(physical|occupational|speech.language)\s*therapist\b',            "Healthcare"),
    (r'\bpsychologist\b|\bpsychiatrist\b|\bLCSW\b|\bLPC\b|\btherapist\b',   "Healthcare"),
    (r'\bsurgeon\b|\borthopaedic\b|\bcardiol\b|\bneurolog\b',               "Healthcare"),
    (r'\boptometrist\b|\bophthalmologist\b',                                "Healthcare"),
    (r'\bchiropractor\b|\bDC\b(?!\s*Comics)',                               "Healthcare"),
    (r'\bhealthcare\s*(admin|exec|director|manager|consultant)\b',          "Healthcare"),
    (r'\bpublic\s*health\b|\bepidemiolog\b',                                "Healthcare"),
    (r'\bveterinar\b|\bDVM\b',                                              "Healthcare"),
    (r'\bmedical\s*(director|officer|researcher|writer)\b',                 "Healthcare"),
    (r'\bPA-C\b|\bphysician\s*assistant\b',                                 "Healthcare"),

    # Legal
    (r'\battorney\b|\blawyer\b|\bcounsel\b|\besq\.?\b',                     "Legal"),
    (r'\bparalegal\b|\blegal\s*(assistant|secretary)\b',                    "Legal"),
    (r'\bjudge\b|\bmagistrate\b|\bjustice\b',                               "Legal"),
    (r'\blaw\s*(clerk|professor|student)\b',                                "Legal"),

    # Education
    (r'\bprofessor\b|\bfaculty\b|\blecturer\b|\bassoc\.\s*prof\b',          "Education"),
    (r'\bteacher\b|\beducator\b|\bteaching\s*assistant\b|\binstructor\b',   "Education"),
    (r'\bprincipal\b|\bsuperintendent\b|\bschool\s*(admin|director)\b',     "Education"),
    (r'\b(academic|education)\s*(research|director|dean|coordinator)\b',    "Education"),
    (r'\bcurriculum\b|\beducation\s*policy\b',                              "Education"),

    # Government / Politics
    (r'\bstate\s*rep(resentative)?\b|\blegislator\b|\bsenator\b',           "Government"),
    (r'\bcity\s*(council|manager|planner|official|employee)\b',             "Government"),
    (r'\bfederal\s*(employee|agent|officer|official)\b',                    "Government"),
    (r'\bpolice\s*(officer|chief|detective|captain)\b',                     "Government"),
    (r'\bfire(fighter|man|woman|captain)\b|\bfire\s*dept\b',                "Government"),
    (r'\bmilitary\b|\bnavy\b|\barmy\b|\bair\s*force\b|\bUSN\b|\bUSAF\b',    "Government"),
    (r'\bpublic\s*(administrator|servant|official|policy)\b',               "Government"),

    # Finance
    (r'\baccountant\b|\bcpa\b|\bCFO\b|\bauditor\b',                         "Finance"),
    (r'\bfinancial\s*(advisor|planner|analyst|consultant|director)\b',      "Finance"),
    (r'\bbanker\b|\bbank\s*(officer|manager|executive)\b',                  "Finance"),
    (r'\binsurance\s*(agent|broker|adjuster|exec)\b',                       "Finance"),
    (r'\binvestment\s*(banker|analyst|manager|advisor)\b',                  "Finance"),
    (r'\bCFA\b|\bCFP\b|\bwealth\s*manager\b',                               "Finance"),
    (r'\bventure\s*(capitalist|partner)\b|\bVC\b',                          "Finance"),

    # Real Estate
    (r'\brealtor\b|\breal\s*estate\s*(agent|broker|investor)\b',            "Real Estate"),
    (r'\bproperty\s*(manager|developer|investor|owner)\b',                  "Real Estate"),
    (r'\bmortgage\s*(broker|banker|officer)\b',                             "Real Estate"),

    # Engineering / Architecture
    (r'\b(civil|structural|mechanical|electrical|environmental|chemical)\s*engineer\b', "Engineering"),
    (r'\barchitect\b(?!ure)',                                                "Architecture"),
    (r'\blandscape\s*(architect|designer)\b',                               "Architecture"),
    (r'\burban\s*(planner|designer)\b',                                     "Engineering"),

    # Consulting / PR
    (r'\bpolitical\s*(consultant|strategist|director|operativ)\b',          "Consulting / PR"),
    (r'\bpublic\s*relations\b|\bpr\s*(director|manager|exec)\b',            "Consulting / PR"),
    (r'\blobbyist\b|\bgovernmental\s*affairs\b|\bpublic\s*affairs\b',       "Consulting / PR"),
    (r'\bmanagement\s*consultant\b|\bconsulting\b',                         "Consulting / PR"),

    # Nonprofit
    (r'\bnonprofit\b|\bnon.profit\b|\b501c\b',                              "Nonprofit"),
    (r'\bcommunity\s*organizer\b|\badvocacy\b|\bactivist\b',                "Nonprofit"),
    (r'\bsocial\s*(worker|services)\b',                                     "Nonprofit"),

    # Media
    (r'\bjournalist\b|\breporter\b|\bnewspaper\b|\bnews\s*anchor\b',        "Media"),
    (r'\bwriter\b|\bauthor\b|\beditor\b|\bcopywriter\b',                    "Media"),
    (r'\bfilmmaker\b|\bdirector\b|\bproducer\b|\bvideographer\b',           "Media"),
    (r'\bphotographer\b|\bphotojournalist\b',                               "Media"),
    (r'\bpodcast(er)?\b|\bcontent\s*creator\b',                             "Media"),

    # Hospitality / Entertainment
    (r'\bchef\b|\bcook\b|\bculi\b|\bpastry\b',                              "Hospitality / Entertainment"),
    (r'\brestaurant\s*(owner|manager)\b',                                   "Hospitality / Entertainment"),
    (r'\bhotel\s*(manager|exec|director)\b',                                "Hospitality / Entertainment"),
    (r'\bmusician\b|\bperformer\b|\bactor\b|\bcomposer\b',                  "Hospitality / Entertainment"),
    (r'\bevent\s*(planner|coordinator|manager)\b',                          "Hospitality / Entertainment"),

    # Energy
    (r'\benergy\s*(engineer|analyst|consultant|manager|exec)\b',            "Energy / Environment"),
    (r'\b(petroleum|oil\s*&?\s*gas|upstream|downstream)\b',                 "Energy / Environment"),
    (r'\brenewable\b|\bsolar\b|\bwind\s*energy\b|\bclean\s*energy\b',       "Energy / Environment"),
    (r'\bgeologist\b|\bgeophysicist\b',                                     "Energy / Environment"),

    # Construction / Trades
    (r'\bcontractor\b|\bconstruction\s*(manager|exec|superintendent)\b',    "Construction"),
    (r'\bplumber\b|\belectrician\b|\bcarpenter\b|\bHVAC\b',                 "Construction"),
    (r'\bbuilder\b|\bdeveloper\b(?!\s*software)',                           "Construction"),
]

OCC_COMPILED = [(re.compile(p, re.I), ind) for p, ind in OCC_RULES]

def infer_from_occupation(occ_str):
    if not occ_str:
        return None
    s = occ_str.strip().lower()
    if s in ("not employed", "not applicable", "n/a", "na", "none", "", "retired",
             "student", "homemaker", "stay at home", "unemployed", "freelance",
             "self employed", "self-employed", "business owner", "owner",
             "independent contractor", "independent", "not employed"):
        return None
    for pattern, industry in OCC_COMPILED:
        if pattern.search(occ_str):
            return industry
    return None

# ── Load all transactions grouped by donor_id ────────────────────────────────
print("Loading transactions...")
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
    WHERE cf.donor_id IS NOT NULL
""")
by_donor = defaultdict(list)
for donor_id, raw_emp, industry, emp_can, occ, amt in cur.fetchall():
    by_donor[donor_id].append((raw_emp, industry, emp_can, occ, amt or 0))

print(f"  {len(by_donor):,} donor_ids with transactions")

# ── Resolve each donor_id independently ──────────────────────────────────────
updates = []
stats = defaultdict(int)

for donor_id, txns in by_donor.items():
    # Step 1: real named employer with non-noise industry
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

    # Step 2: occupation inference
    occ_hits = {}
    for raw_emp, industry, emp_can, occ, amt in txns:
        inf = infer_from_occupation(occ)
        if inf:
            occ_hits[inf] = occ_hits.get(inf, 0) + amt

    if occ_hits:
        best_ind = max(occ_hits, key=lambda k: occ_hits[k])
        # Find representative occupation string for display
        occ_str = next((occ for _, _, _, occ, _ in txns if infer_from_occupation(occ) == best_ind), "")
        updates.append((best_ind, occ_str, "occupation", donor_id))
        stats["occupation"] += 1
        continue

    stats["unresolved"] += 1

print(f"\nResolution results:")
print(f"  Via named employer:  {stats['employer']:,}")
print(f"  Via occupation:      {stats['occupation']:,}")
print(f"  Unresolved:          {stats['unresolved']:,}")
print(f"  Total updates:       {len(updates):,}")

# ── Write to DB ───────────────────────────────────────────────────────────────
cur.executemany("""
    UPDATE donor_identities
    SET resolved_industry=?, resolved_employer_display=?, resolved_confidence=?
    WHERE donor_id=?
""", updates)
conn.commit()
print(f"Written to DB.")

# ── Spot-check Hamza Sait ─────────────────────────────────────────────────────
print("\n── Spot check: Sait, Hamza ──")
cur.execute("""
    SELECT donor_id, canonical_name, canonical_zip, canonical_employer,
           resolved_industry, resolved_employer_display, resolved_confidence
    FROM donor_identities WHERE canonical_name = 'Sait, Hamza'
""")
for r in cur.fetchall():
    print(f"  {r[0][:8]}  zip={r[2]}  was=[{r[3]}]")
    print(f"    → resolved={r[4]}  via={r[6]}  display=[{r[5]}]")

# ── Qadri breakdown using resolved_industry ────────────────────────────────────
print("\n── Qadri profile breakdown (person-level industry) ──")
cur.execute("""
    SELECT
        COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
        SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)) as total,
        COUNT(*) as n
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
    marker = " ← was Unknown/Not Employed/Self-Employed" if r[0] not in (
        "Real Estate","Technology","Nonprofit","Legal","Healthcare",
        "Government","Finance","Engineering","Education",
        "Hospitality / Entertainment","Construction","Energy / Environment",
        "Retail","Media","Architecture","Transportation","Entertainment","Labor",
        "Student","Consulting / PR"
    ) else ""
    print(f"  {r[0]:<35} ${r[1]:>9,.0f}  {pct:>5.1f}%  {r[2]:>5}{marker}")
print(f"  {'TOTAL':<35} ${grand:>9,.0f}")
conn.close()
