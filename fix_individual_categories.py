"""
Split the Individual bucket properly:
 - Self-Employed  → industry='Self-Employed'
 - Not Employed   → industry='Not Employed'  (retired, n/a, blank, none, unemployed)
 - Student        → industry='Student'  (split out from Not Employed)
 - Personal names → industry='Self-Employed' (listed own name = sole proprietor)
 - Job titles     → proper industry where guessable, else NULL (Unknown)
 - Ambiguous codes (GC, IV, RE…) → NULL (Unknown)
"""
import sqlite3, sys, io, uuid
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# ── 1. Change industry on the two synthetic employer entries ──────────────────
cur.execute("UPDATE employer_identities SET industry='Self-Employed' WHERE canonical_name='Self-Employed'")
cur.execute("UPDATE employer_identities SET industry='Not Employed'  WHERE canonical_name='Not Employed'")
print("Renamed Self-Employed / Not Employed industry values")

# ── 2. Also fix any other Individual entries with these tags ──────────────────
cur.execute("UPDATE employer_identities SET industry='Self-Employed' WHERE industry='Individual' AND interest_tags='self-employed'")
cur.execute("UPDATE employer_identities SET industry='Not Employed'  WHERE industry='Individual' AND interest_tags='not-employed'")
print("Re-tagged remaining Individual/self-employed and Individual/not-employed entries")

# ── 3. Create Student identity and wire records ───────────────────────────────
cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name='Student'")
row = cur.fetchone()
if row:
    student_id = row[0]
else:
    student_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO employer_identities (employer_id, canonical_name, industry, interest_tags, record_count)
        VALUES (?, 'Student', 'Student', 'student', 0)
    """, (student_id,))

cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name='Not Employed'")
not_emp_id = cur.fetchone()[0]

# Move student records from Not Employed to Student
wired_students = 0
for raw in ["student", "Student", "STUDENT"]:
    cur.execute("""
        UPDATE campaign_finance SET employer_id=?
        WHERE employer_id=?
          AND LOWER(TRIM(COALESCE(donor_reported_employer,''))) = 'student'
    """, (student_id, not_emp_id))
    wired_students += cur.rowcount

print(f"Student records wired: {wired_students}")

# ── 4. Personal names → Self-Employed ─────────────────────────────────────────
# These donors listed their own name as employer → sole proprietor / self-employed
cur.execute("SELECT employer_id FROM employer_identities WHERE canonical_name='Self-Employed'")
self_emp_id = cur.fetchone()[0]

PERSONAL_NAMES = [
    "Tamer Barazi", "Sami Khaleeq", "Michelle Skupin", "Meredith Hull",
    "Christina Black", "Brita wallace", "Greg Gonzalez", "Pete Gilcrease",
    "Luke Warford", "Winston O'Neal", "Shenghao Wang", "Justin Phillips",
    "Junaid Ikram", "Annick Beaudet", "Sophia Mirto", "Asif Cochinwala",
    "Parissa", "Dave Pantos Esq. LLC", "May Matson Taylor Ph.D. Psychologist",
    "Irfan R. Qureshi MD PA", "Audrey Nath MD PLLC", "Greg Casar for Congress",
    "Zohaib Qadri",
]
updated_names = 0
for name in PERSONAL_NAMES:
    cur.execute("""
        UPDATE employer_identities SET industry='Self-Employed', interest_tags='self-employed'
        WHERE canonical_name=?
    """, (name,))
    updated_names += cur.rowcount
print(f"Personal names → Self-Employed: {updated_names}")

# ── 5. Truly ambiguous/meaningless entries → NULL (Unknown) ──────────────────
AMBIGUOUS = [
    "Company", "Employed", "RE", "GC", "IV", "WF", "PH", "MS", "LV", "QP",
    "FGC", "IDM", "LPC", "COJ", "COSA", "TFN", "Nonprofit", "Finance",
    "Primcipeam", "JW",
]
reset_ambiguous = 0
for name in AMBIGUOUS:
    cur.execute("""
        UPDATE employer_identities SET industry=NULL, interest_tags=NULL
        WHERE canonical_name=?
    """, (name,))
    reset_ambiguous += cur.rowcount
print(f"Ambiguous entries reset to Unknown: {reset_ambiguous}")

# ── 6. Fix misclassified entries that should be in real industries ─────────────
FIXES = [
    # (canonical, industry, tags)
    ("NYU",                 "Education",    "higher-education"),
    ("VCU",                 "Education",    "higher-education"),
    ("ISD",                 "Government",   None),
    ("Regional Administrator", "Government", None),
    ("Teaching Assistant",  "Education",    None),
    ("Myself",              "Self-Employed","self-employed"),
    ("Luke Warford",        "Self-Employed","self-employed"),   # TX Railroad Commissioner candidate → self-employed
    ("Annick Beaudet",      "Government",   None),   # Austin city official
    ("Audrey Nath MD PLLC", "Healthcare",   None),
    ("Irfan R. Qureshi MD PA", "Healthcare", None),
    ("Dave Pantos Esq. LLC","Legal",        None),
    ("May Matson Taylor Ph.D. Psychologist", "Healthcare", None),
]
updated_fixes = 0
for canonical, industry, tags in FIXES:
    cur.execute("""
        UPDATE employer_identities SET industry=?, interest_tags=?
        WHERE canonical_name=?
    """, (industry, tags, canonical))
    updated_fixes += cur.rowcount
print(f"Industry-specific fixes: {updated_fixes}")

# For job titles: classify by what they imply
JOB_TITLE_FIXES = [
    ("Design Manager",           "Technology",   None),
    ("Critical Products Manager","Technology",   None),
    ("Higher Education Policy Analyst", "Education", None),
]
for canonical, industry, tags in JOB_TITLE_FIXES:
    cur.execute("UPDATE employer_identities SET industry=?, interest_tags=? WHERE canonical_name=?",
                (industry, tags, canonical))

conn.commit()

# ── Report ─────────────────────────────────────────────────────────────────────
print()
print("=== QADRI DONOR BREAKDOWN ===")
cur.execute("""
    SELECT COALESCE(ei.industry, 'Unknown') as bucket,
           COUNT(*) as n,
           SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)) as total
    FROM campaign_finance cf
    LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
    WHERE cf.recipient LIKE '%Qadri%' AND cf.contribution_year >= 2022
    GROUP BY bucket ORDER BY total DESC
""")
rows = cur.fetchall()
grand = sum(r[2] or 0 for r in rows)
for r in rows:
    pct = (r[2] or 0) / grand * 100
    print(f"  {r[0]:<35} ${r[2]:>9,.0f}  {pct:>5.1f}%  {r[1]:>6} records")
print(f"  {'TOTAL':<35} ${grand:>9,.0f}")
conn.close()
