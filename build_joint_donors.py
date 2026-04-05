"""
Joint donor resolution pipeline.

Detects couple/joint donations (& / and / /), parses each person out,
resolves them against existing donor_identities, creates new identities
where none exist, then updates campaign_finance and writes joint_donations.
"""

import sqlite3
import re
import uuid
import unicodedata
from rapidfuzz import fuzz

DB = "austin_finance.db"

NICKNAMES = {
    "bill": "william", "billy": "william", "will": "william",
    "bob": "robert", "rob": "robert", "bobby": "robert",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "tom": "thomas", "tommy": "thomas",
    "mike": "michael", "mick": "michael",
    "dick": "richard", "rick": "richard",
    "dave": "david",
    "joe": "joseph",
    "sue": "susan", "susie": "susan",
    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth",
    "kate": "katherine", "kathy": "katherine", "katie": "kathryn", "kat": "katherine",
    "chris": "christopher",
    "dan": "daniel", "danny": "daniel",
    "pat": "patricia",
    "sam": "samuel",
    "ed": "edward", "eddie": "edward", "ted": "edward",
    "ben": "benjamin",
    "nick": "nicholas",
    "tony": "anthony",
    "andy": "andrew",
    "alex": "alexander",
    "greg": "gregory",
    "ken": "kenneth",
    "steve": "steven",
    "matt": "matthew",
    "jeff": "jeffrey",
    "jerry": "gerald",
    "chuck": "charles", "charlie": "charles",
    "harry": "harold",
    "hank": "henry",
    "jack": "john",
    "peggy": "margaret", "meg": "margaret", "maggie": "margaret",
    "cathy": "catherine",
    "barb": "barbara",
    "cindy": "cynthia",
    "dot": "dorothy",
    "fred": "frederick",
    "jake": "jacob",
    "lou": "louis",
    "nan": "nancy",
    "ray": "raymond",
    "ron": "ronald",
    "phil": "philip",
    "jan": "janet",
    "lew": "lewis",
    "julia": "julie",
    "don": "donald",
    "pam": "pamela",
    "mandy": "amanda",
    "tami": "tamara", "tammy": "tamara",
    "teri": "teresa", "terri": "teresa", "terrie": "teresa",
    "gene": "eugene",
    "louie": "louis",
    "johnny": "john", "jon": "john",
    "missy": "melissa",
    "lori": "laura", "lorri": "laura",
    "trish": "patricia",
    "dee": "diana",
    "bev": "beverly",
    "deb": "deborah", "debbie": "deborah",
    "barbie": "barbara",
    "hal": "harold",
    "len": "leonard",
    "val": "valerie",
    "drew": "andrew",
}

NOISE_EMPLOYERS = {
    "city of austin", "retired", "self", "self employed", "self-employed",
    "selfemployed", "not employed", "not-employed", "na", "n/a", "none",
    "unknown", "best efforts", "n a", "homemaker", "student", "unemployed",
    "housewife", "various", "austin police department", "retire",
}

JOINT_SEP = re.compile(r'\s*(?:&|/|\band\b)\s*', re.IGNORECASE)
# Entity keywords — if name contains these, skip joint parsing
ENTITY_KEYWORDS = re.compile(
    r'\b(pac|llc|lp|llp|pllc|inc|corp|ltd|pc|association|assoc|trust|'
    r'committee|union|foundation|institute|company|co\.|group|partners|'
    r'properties|management|builders|contractors|engineers|planners|'
    r'consulting|services|council|network|networks|ventures|holdings|'
    r'industries|solutions|enterprises|agency|bureau|department)\b',
    re.IGNORECASE
)

# ── Helpers ────────────────────────────────────────────────────────────────────
def to_ascii(s):
    try:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    except Exception:
        return s

def norm_str(s):
    return to_ascii(s or "").lower().strip()

def normalize_first(first):
    f = re.sub(r"[^a-z]", "", norm_str(first))
    return NICKNAMES.get(f, f)

def normalize_zip(city_state_zip):
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", city_state_zip or "")
    return m.group(1) if m else ""

def normalize_employer(emp):
    s = norm_str(emp)
    s = re.sub(r"\b(inc|llc|corp|co|ltd|pc|lp|pllc|pa)\.?\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return "" if s in NOISE_EMPLOYERS else s

def normalize_occupation(occ):
    s = norm_str(occ)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def parse_joint_name(raw):
    """
    Returns (name1_str, name2_str) as 'Last, First' strings, or None.

    Handles:
      Standard:
        'Armbrust, David/Cheryl'              → ('Armbrust, David', 'Armbrust, Cheryl')
        'Garcia, Manuel & Maria Ester'         → ('Garcia, Manuel', 'Garcia, Maria Ester')
        'Martin, Matthew & Sarah Mussey'       → ('Martin, Matthew', 'Mussey, Sarah')
        'Jones, Annette & Kenneth'             → ('Jones, Annette', 'Jones, Kenneth')
      Different last names:
        'Coffin/Forbath, Judy/William'         → ('Coffin, Judy', 'Forbath, William')
        'Cortes / Olson, Andrew / Patrick'     → ('Cortes, Andrew', 'Olson, Patrick')
        'Bojo & Kremer, Leah & Brian'          → ('Bojo, Leah', 'Kremer, Brian')
      Reversed (First Last format):
        'David and Cheryl Armbrust'            → ('Armbrust, David', 'Armbrust, Cheryl')
        'Sheryl and Kevin, Cole'               → ('Cole, Sheryl', 'Cole, Kevin')
      First names first, last at end:
        'Jeanne & Jay, Carpenter'              → ('Carpenter, Jeanne', 'Carpenter, Jay')
    """
    if not JOINT_SEP.search(raw):
        return None

    # Skip entity names
    if ENTITY_KEYWORDS.search(raw):
        return None

    raw = raw.strip()
    parts = JOINT_SEP.split(raw, maxsplit=1)
    if len(parts) != 2:
        return None

    left  = parts[0].strip()
    right = parts[1].strip()

    # ── Pattern 1: 'Last1/Last2, First1/First2' or 'Last1 & Last2, First1 & First2'
    # Both sides of the comma contain a separator → different last names
    if "," in raw:
        comma_idx = raw.index(",")
        before_comma = raw[:comma_idx]
        after_comma  = raw[comma_idx+1:].strip()
        if JOINT_SEP.search(before_comma) and JOINT_SEP.search(after_comma):
            lasts  = [x.strip() for x in JOINT_SEP.split(before_comma)]
            firsts = [x.strip() for x in JOINT_SEP.split(after_comma)]
            if len(lasts) == 2 and len(firsts) == 2 and all(lasts) and all(firsts):
                return f"{lasts[0]}, {firsts[0]}", f"{lasts[1]}, {firsts[1]}"

    # ── Pattern 2: Standard 'Last, First1 & First2' or 'Last, First1/First2'
    if "," in left:
        left_last, left_first = [x.strip() for x in left.split(",", 1)]
        if not left_last or not left_first:
            return None
        name1 = f"{left_last}, {left_first}"
        # Right side: inherited last name or new last name
        if "," in right:
            r_last, r_first = [x.strip() for x in right.split(",", 1)]
            name2 = f"{r_last}, {r_first}"
        else:
            tokens = right.split()
            if not tokens:
                return None
            if len(tokens) == 1:
                name2 = f"{left_last}, {right}"
            else:
                possible_last  = tokens[-1]
                possible_first = " ".join(tokens[:-1])
                if possible_last and possible_last[0].isupper() and possible_last.lower() not in NICKNAMES:
                    name2 = f"{possible_last}, {possible_first}"
                else:
                    name2 = f"{left_last}, {right}"
        return name1, name2

    # ── Pattern 3: 'First1 & First2, Last'  (first names before comma)
    if "," in right and not "," in left:
        # e.g. left='Jeanne', right='Jay, Carpenter' or right='Jay Carpenter'
        # OR left='Jeanne', right='Jay, Carpenter' means sep split gave us last name
        r_parts = right.split(",", 1)
        if len(r_parts) == 2:
            second_first = r_parts[0].strip()
            shared_last  = r_parts[1].strip()
            if shared_last and second_first:
                return f"{shared_last}, {left}", f"{shared_last}, {second_first}"

    # ── Pattern 4: No comma at all — 'First1 and First2 Last' or 'First Last1 and Last2'
    if "," not in raw:
        tokens_l = left.split()
        tokens_r = right.split()
        # 'David and Cheryl Armbrust' → left='David', right='Cheryl Armbrust'
        if len(tokens_r) >= 2:
            shared_last = tokens_r[-1]
            first2      = " ".join(tokens_r[:-1])
            first1      = left
            return f"{shared_last}, {first1}", f"{shared_last}, {first2}"
        # 'Vasumathi and Gopal, Guthikonda' handled above in pattern 3
        if len(tokens_l) >= 2:
            shared_last = tokens_l[-1]
            first1      = " ".join(tokens_l[:-1])
            first2      = right
            return f"{shared_last}, {first1}", f"{shared_last}, {first2}"

    return None


def score_against_identity(first, last, zip5, emp_occ, candidate):
    """Score a parsed individual against an existing donor_identities row."""
    c_last, c_first = [x.strip() for x in candidate["canonical_name"].split(",", 1)] \
        if "," in (candidate["canonical_name"] or "") else ("", "")
    c_last  = norm_str(c_last)
    c_first = normalize_first(c_first)

    last_score  = fuzz.token_sort_ratio(last, c_last)   / 100.0
    first_score = fuzz.token_sort_ratio(first, c_first) / 100.0

    if last_score < 0.78 or first_score < 0.78:
        return 0.0

    c_zip = candidate["canonical_zip"] or ""
    zip_score = (1.0 if zip5 == c_zip else 0.0) if (zip5 and c_zip) else 0.5

    c_emp = candidate["canonical_employer"] or ""
    emp_score = fuzz.token_sort_ratio(emp_occ, c_emp) / 100.0 if (emp_occ and c_emp) else 0.5

    return round(0.30 * last_score + 0.30 * first_score + 0.30 * zip_score + 0.10 * emp_score, 4)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()

    # ── Schema additions ───────────────────────────────────────────────────────
    for col, typ in [("is_joint", "INTEGER DEFAULT 0"),
                     ("donor_id_2", "TEXT"),
                     ("balanced_amount", "REAL")]:
        try:
            cur.execute(f"ALTER TABLE campaign_finance ADD COLUMN {col} {typ}")
        except Exception:
            cur.execute(f"UPDATE campaign_finance SET {col} = NULL")

    cur.execute("DROP TABLE IF EXISTS joint_donations")
    cur.execute("""
        CREATE TABLE joint_donations (
            transaction_id  TEXT,
            rowid_cf        INTEGER,
            donor_id_1      TEXT,
            donor_id_2      TEXT,
            parsed_name_1   TEXT,
            parsed_name_2   TEXT,
            full_amount     REAL,
            balanced_amount REAL
        )
    """)

    # ── Load identities for lookup ─────────────────────────────────────────────
    print("Loading existing donor identities...")
    cur.execute("SELECT donor_id, canonical_name, canonical_zip, canonical_employer FROM donor_identities")
    identities = [
        {"donor_id": r[0], "canonical_name": r[1], "canonical_zip": r[2], "canonical_employer": r[3]}
        for r in cur.fetchall()
    ]

    # Build a fast index: (norm_last, norm_first) → list of identity indices
    from collections import defaultdict
    last_index = defaultdict(list)
    for idx, iden in enumerate(identities):
        if "," in (iden["canonical_name"] or ""):
            raw_last = iden["canonical_name"].split(",", 1)[0].strip()
            last_index[norm_str(raw_last)].append(idx)

    # ── Load all records and detect joint entries ──────────────────────────────
    print("Scanning for joint donor entries...")
    cur.execute("""
        SELECT rowid, donor, transaction_id, contribution_amount,
               city_state_zip, donor_reported_employer, donor_reported_occupation,
               donor_id
        FROM campaign_finance
        WHERE donor_type NOT IN ('ENTITY','Entity')
        AND (donor LIKE '%&%' OR donor LIKE '%/%' OR donor LIKE '% and %')
    """)
    candidates = cur.fetchall()
    print(f"  {len(candidates):,} candidate records with joint separators")

    joint_records   = []
    joint_cf_updates = []
    new_identities  = {}   # canonical_name → donor_id (for newly minted)

    parsed_count = 0
    skip_count   = 0

    for rowid, donor, txn_id, amt_raw, zip_raw, emp_raw, occ_raw, existing_did in candidates:
        result = parse_joint_name(donor)
        if not result:
            skip_count += 1
            continue

        name1_raw, name2_raw = result
        parsed_count += 1

        try:
            full_amount = float(amt_raw or 0)
        except Exception:
            full_amount = 0.0
        balanced = round(full_amount / 2, 2)

        zip5    = normalize_zip(zip_raw)
        emp     = normalize_employer(emp_raw)
        occ     = normalize_occupation(occ_raw)
        emp_occ = " ".join(sorted(set((emp + " " + occ).split())))

        def resolve_name(name_raw):
            """Find or create a donor_id for a parsed name."""
            if "," not in name_raw:
                return None, name_raw
            last_raw, first_raw = [x.strip() for x in name_raw.split(",", 1)]
            last  = norm_str(last_raw)
            first = normalize_first(first_raw)

            # Search candidates in last-name index
            best_score = 0.0
            best_id    = None
            for idx in last_index.get(last, []):
                s = score_against_identity(first, last, zip5, emp_occ, identities[idx])
                if s > best_score:
                    best_score = s
                    best_id    = identities[idx]["donor_id"]

            if best_score >= 0.83:
                return best_id, name_raw

            # No match — mint new identity (or reuse one we already minted this run)
            canonical = f"{last_raw.title()}, {first_raw.title()}"
            if canonical in new_identities:
                return new_identities[canonical], name_raw

            new_id = str(uuid.uuid4())
            new_identities[canonical] = new_id
            return new_id, name_raw

        did1, pname1 = resolve_name(name1_raw)
        did2, pname2 = resolve_name(name2_raw)

        # donor_id on main record = person 1 (or existing if already set)
        final_did1 = did1 or existing_did or str(uuid.uuid4())
        final_did2 = did2 or str(uuid.uuid4())

        joint_records.append((
            txn_id, rowid, final_did1, final_did2,
            pname1, pname2, full_amount, balanced
        ))
        joint_cf_updates.append((1, final_did1, final_did2, balanced, rowid))

    print(f"  Parsed as joint:  {parsed_count:,}")
    print(f"  Skipped (no split found): {skip_count:,}")
    print(f"  New identities minted: {len(new_identities):,}")

    # ── Write new identities to donor_identities ───────────────────────────────
    print("Writing new identities...")
    new_id_rows = [
        (did, canonical, "", "", 0.0, 0, "", 0, "", "")
        for canonical, did in new_identities.items()
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO donor_identities
        (donor_id, canonical_name, canonical_zip, canonical_employer,
         total_donated, campaign_count, campaigns, record_count, first_seen, last_seen)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, new_id_rows)

    # ── Write joint_donations ──────────────────────────────────────────────────
    print("Writing joint_donations table...")
    cur.executemany("INSERT INTO joint_donations VALUES (?,?,?,?,?,?,?,?)", joint_records)

    # ── Update campaign_finance ────────────────────────────────────────────────
    print("Updating campaign_finance...")
    cur.executemany("""
        UPDATE campaign_finance
        SET is_joint=?, donor_id=?, donor_id_2=?, balanced_amount=?
        WHERE rowid=?
    """, joint_cf_updates)

    conn.commit()

    # ── Summary ────────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM joint_donations")
    jcount = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM campaign_finance WHERE is_joint=1")
    cf_joint = cur.fetchone()[0]

    cur.execute("""
        SELECT jd.parsed_name_1, jd.parsed_name_2, jd.full_amount, jd.balanced_amount,
               cf.recipient, cf.contribution_date
        FROM joint_donations jd
        JOIN campaign_finance cf ON jd.rowid_cf = cf.rowid
        LIMIT 12
    """)
    print("\n=== SAMPLE JOINT DONATIONS ===\n")
    for r in cur.fetchall():
        print(f"  {r[4]}  |  {r[5][:10]}")
        print(f"    Person 1: {r[0]}")
        print(f"    Person 2: {r[1]}")
        print(f"    Full: ${r[2]:,.2f}   Balanced: ${r[3]:,.2f}")
        print()

    conn.close()
    print(f"=== DONE ===")
    print(f"  Joint donation records:  {jcount:,}")
    print(f"  campaign_finance flagged: {cf_joint:,}")
    print(f"  New identities minted:   {len(new_identities):,}")

if __name__ == "__main__":
    main()
