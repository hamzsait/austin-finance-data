"""
Dual-employer attribution: employer_id_2

For donors who listed two employers separated by ' / ', this script:
  1. Adds employer_id_2 column to campaign_finance (if not present)
  2. For each compound row, splits into left/right employer strings
  3. Skips rows where the right side is blank/None/self/requested
  4. Fuzzy-matches each side against employer_identities canonical names
  5. Re-assigns employer_id  from the left half
  6. Assigns   employer_id_2 from the right half
  7. Leaves employer_id_2 NULL for single-employer rows

Attribution rule:
  - Single person with two employers → both clusters get FULL donation credit
  - Queries should use: WHERE employer_id = X OR employer_id_2 = X
"""

import sqlite3
import re
import unicodedata
from rapidfuzz import fuzz, process

DB = "austin_finance.db"

# Strings on the right side of " / " that mean "no second employer"
NULL_EMPLOYERS = {
    "", "none", "n/a", "na", "no", "not", "requested", "not required",
    "self", "self-employed", "self employed", "selfemployed",
    "retired", "homemaker", "student", "unemployed", "volunteer",
    "not applicable", "not available", "unknown", "various",
    # Job titles that appear in employer field
    "creative director", "managing director", "managing partner",
    "account manager", "account executive", "attorney", "consultant",
    "physician", "teacher", "professor", "engineer", "developer",
    "writer", "editor", "architect", "designer", "analyst",
    "manager", "director", "partner", "associate", "coordinator",
    "specialist", "officer", "executive", "president", "owner",
    "marketer", "musician", "contractor",
    # Data artifacts — not real employers
    "requested", "request", "reqeusted", "provided upon request",
    # Retired / inactive
    "retired", "ret", "formerly",
}

LEGAL_SUFFIXES = re.compile(
    r'\b(pllc|llc|llp|lllp|lp|pc|pa|inc|corp|co|ltd|plc|na|'
    r'incorporated|limited|associates|association|assoc|'
    r'group|partners|partnership|ventures|holdings|enterprises|'
    r'solutions|services|systems|consulting|consultants|'
    r'international|global|national|management|properties|'
    r'industries|technologies|technology)\b\.?',
    re.IGNORECASE
)

def normalize(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"['\"]", "", s)
    s = LEGAL_SUFFIXES.sub(" ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def is_null_employer(s):
    n = normalize(s)
    # Skip blanks, known null strings, pure job titles, or very short strings
    return n in NULL_EMPLOYERS or len(n) <= 3

def fuzzy_lookup(raw, canonical_list, norm_to_id, id_to_canonical, threshold=82):
    """Return (employer_id, confidence) for best match above threshold, else (None, None)."""
    normed = normalize(raw)
    if not normed or is_null_employer(raw):
        return None, None
    # Require at least 4 meaningful characters after normalization
    if len(normed.replace(" ", "")) < 4:
        return None, None
    # Exact normalized match first
    if normed in norm_to_id:
        eid = norm_to_id[normed]
        # Reject if the canonical itself is a compound string (contains ' / ')
        if " / " in id_to_canonical.get(eid, ""):
            return None, None
        return eid, 1.0
    # Fuzzy search against normalized canonicals
    result = process.extractOne(
        normed,
        canonical_list,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
    )
    if result:
        matched_norm, score, _ = result
        eid = norm_to_id[matched_norm]
        # Reject if canonical is itself a compound string
        if " / " in id_to_canonical.get(eid, ""):
            return None, None
        return eid, round(score / 100, 4)
    return None, None


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Add employer_id_2 column if missing
    cur.execute("PRAGMA table_info(campaign_finance)")
    cols = {row["name"] for row in cur.fetchall()}
    if "employer_id_2" not in cols:
        cur.execute("ALTER TABLE campaign_finance ADD COLUMN employer_id_2 TEXT")
        print("Added employer_id_2 column")
    else:
        print("employer_id_2 column already exists")

    # 2. Load all employer identities into memory
    cur.execute("SELECT employer_id, canonical_name FROM employer_identities")
    identities = cur.fetchall()

    norm_to_id = {}
    id_to_canonical = {}
    for row in identities:
        normed = normalize(row["canonical_name"])
        if normed:
            norm_to_id[normed] = row["employer_id"]
        id_to_canonical[row["employer_id"]] = row["canonical_name"]

    # Canonical names that are data artifacts, not real employers
    BLOCKED_CANONICALS = {
        "REQUESTED", "Not Required", "Real Estate", "Home", "Government",
        "Government Affairs", "Government Relations", "Education",
        "Private", "Private Practice", "Managing Director", "Managing Partner",
        "Managing Principal", "Writer", "Writer & Editor",
    }
    blocked_ids = {row["employer_id"] for row in identities
                   if row["canonical_name"] in BLOCKED_CANONICALS}

    # Exclude compound canonicals and blocked artifact canonicals from lookup targets
    canonical_list = [n for n, eid in norm_to_id.items()
                      if " / " not in id_to_canonical.get(eid, "")
                      and eid not in blocked_ids]
    print(f"Loaded {len(canonical_list)} employer identities (excl. compound canonicals)")

    # 3. Find all compound employer rows
    cur.execute("""
        SELECT rowid, donor_reported_employer, employer_id
        FROM campaign_finance
        WHERE donor_reported_employer LIKE '% / %'
    """)
    compound_rows = cur.fetchall()
    print(f"Found {len(compound_rows)} compound employer rows")

    updated = skipped = no_match_right = no_match_left = 0

    for row in compound_rows:
        rowid = row["rowid"]
        full = row["donor_reported_employer"]

        # Split on first ' / '
        parts = full.split(" / ", 1)
        left_raw  = parts[0].strip()
        right_raw = parts[1].strip() if len(parts) > 1 else ""

        # Skip if left is also null-like (e.g. "Retired / Toni's Fun Learning")
        # — the person is retired; the right side is a family/hobby, not a real employer
        if is_null_employer(left_raw):
            skipped += 1
            continue

        # Skip if right is null-like
        if is_null_employer(right_raw):
            skipped += 1
            continue

        # Look up both sides
        left_id,  left_conf  = fuzzy_lookup(left_raw,  canonical_list, norm_to_id, id_to_canonical)
        right_id, right_conf = fuzzy_lookup(right_raw, canonical_list, norm_to_id, id_to_canonical)

        if not right_id:
            no_match_right += 1
            continue
        if not left_id:
            no_match_left += 1
            # Still write employer_id_2 even if left is unresolved
            cur.execute("""
                UPDATE campaign_finance
                SET employer_id_2 = ?
                WHERE rowid = ?
            """, (right_id, rowid))
            updated += 1
            continue

        # Update both employer_id (left) and employer_id_2 (right)
        cur.execute("""
            UPDATE campaign_finance
            SET employer_id = ?, employer_id_2 = ?
            WHERE rowid = ?
        """, (left_id, right_id, rowid))
        updated += 1

    conn.commit()

    print(f"\nResults:")
    print(f"  {updated:4d} rows updated with employer_id_2")
    print(f"  {skipped:4d} rows skipped (right side is null/self/etc)")
    print(f"  {no_match_right:4d} rows where right employer had no match")
    print(f"  {no_match_left:4d} rows where left employer had no match")

    # 4. Show a sample of what was matched
    print("\nSample matched pairs:")
    cur.execute("""
        SELECT cf.donor_reported_employer,
               ei1.canonical_name AS employer1,
               ei2.canonical_name AS employer2
        FROM campaign_finance cf
        JOIN employer_identities ei1 ON cf.employer_id   = ei1.employer_id
        JOIN employer_identities ei2 ON cf.employer_id_2 = ei2.employer_id
        WHERE cf.employer_id_2 IS NOT NULL
        LIMIT 30
    """)
    for r in cur.fetchall():
        print(f"  '{r['donor_reported_employer']}'")
        print(f"    -> [{r['employer1']}] + [{r['employer2']}]")

    conn.close()

if __name__ == "__main__":
    main()
