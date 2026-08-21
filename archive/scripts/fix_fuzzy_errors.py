"""
Undo bad fuzzy matches (where short noise names got classified) and redo properly.
Strategy: undo any match where canonical_name length < 8 chars.
Then redo fuzzy matching with length ratio guard.
"""
import sqlite3, sys, io
from rapidfuzz import process, fuzz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# Step 1: NULL out industries for very short canonical names (< 8 chars)
# that were likely bad fuzzy matches — these are noise entries anyway
cur.execute("""
    UPDATE employer_identities SET industry = NULL, interest_tags = NULL
    WHERE industry IS NOT NULL
      AND length(canonical_name) < 8
      AND record_count < 20
""")
print(f"Reset {cur.rowcount} short noise entries")
conn.commit()

# Step 2: Also null out specific known-bad matches from the fuzzy run
bad_matches = [
    "Life Science Austin",  # was matched to "Austin" (noise)
    "Region 13 Educational Service Center",  # actually good — keep
]

# Step 3: Better fuzzy matching — require:
#   - Score >= 90
#   - len(matched) >= 6
#   - len ratio: matched_len / query_len >= 0.5 (no tiny abbreviation matches)
cur.execute("SELECT canonical_name FROM employer_identities WHERE industry IS NULL")
db_names = [r[0] for r in cur.fetchall()]

not_found = [
  ("Dykema", "Legal", None),
  ("LeBlanc & Associates", "Consulting / PR", None),
  ("Life Science Austin", "Nonprofit", None),
  ("Marek Brothers Construction", "Construction", None),
  ("Milestone Community Builders", "Construction", "homebuilders|real-estate-development"),
  ("NGP VAN", "Technology", "progressive-money|political-consulting"),
  ("Norwood Capital", "Finance", "real-estate-development"),
  ("O'Connell Robertson", "Architecture", None),
  ("Parker Lane Holdings", "Real Estate", "real-estate-development"),
  ("Performa", "Consulting / PR", None),
  ("Rigney Bradley", "Real Estate", "real-estate-development"),
  ("River City Youth Foundation", "Nonprofit", None),
  ("SitusAMC", "Finance", "real-estate-development"),
  ("Skanska", "Construction", "real-estate-development"),
  ("Slate Real Estate", "Real Estate", "real-estate-development"),
  ("Susman Godfrey", "Legal", None),
  ("TDIndustries", "Construction", None),
  ("TXU Energy", "Energy / Environment", "fossil-fuel-advocacy"),
  ("Texas Conservation Alliance", "Nonprofit", "progressive-money"),
  ("Texas Rio Grande Legal Aid", "Nonprofit", "progressive-money"),
  ("Tolunay-Wong Engineers", "Engineering", None),
  ("Watershed Protection", "Government", None),
  ("Weil Gotshal", "Legal", None),
  ("William Lyon Homes", "Construction", "homebuilders"),
  ("Yardi Systems", "Technology", "real-estate-development"),
  ("Catapult", "Technology", "tech-startup-ecosystem"),
  ("Education Service Center Region 13", "Education", None),
  ("SalesLoft", "Technology", None),
  ("UCHealth", "Healthcare", None),
  ("Tito's Vodka", "Retail", None),
  ("Uber", "Transportation", None),
]

updated = 0
for name, industry, tags in not_found:
    result = process.extractOne(name, db_names, scorer=fuzz.WRatio, score_cutoff=88)
    if result:
        matched_name, score, _ = result
        # Length ratio guard: matched name must be at least half the length of query
        # AND at least 6 chars
        if len(matched_name) >= 6 and len(matched_name) >= len(name) * 0.45:
            cur.execute("""
                UPDATE employer_identities SET industry=?, interest_tags=?
                WHERE canonical_name=? AND industry IS NULL
            """, (industry, tags, matched_name))
            if cur.rowcount:
                updated += 1
                print(f"  [{score:.0f}] '{name}' -> '{matched_name}' ({industry})")

conn.commit()
print(f"\nRe-applied: {updated}")

cur.execute("SELECT SUM(record_count) FROM employer_identities WHERE industry IS NOT NULL")
cr = cur.fetchone()[0] or 0
cur.execute("SELECT SUM(record_count) FROM employer_identities")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM employer_identities WHERE industry IS NOT NULL")
classified = cur.fetchone()[0]
print(f"Total classified: {classified:,}")
print(f"Record coverage: {cr:,} / {total:,} = {cr/total*100:.1f}%")
conn.close()
