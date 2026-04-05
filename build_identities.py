"""
Full donor identity resolution pipeline.

Steps:
  1. Load all individual donor records, normalize
  2. Block via two strategies:
       A. (last_name, zip5)              — primary
       B. (soundex(last), zip5)          — spelling variants
  3. Score all candidate pairs (Last 30 / First 30 / ZIP 30 / Employer 10)
     Hard floor: first_score < 0.78 or last_score < 0.78 → cap at 0.69
  4. Union-Find clustering → stable donor_id per person
  5. Write to DB:
       donor_identities   — one row per resolved person
       review_queue       — flagged pairs (0.70–0.84) for manual review
       campaign_finance   — updated with donor_id + match_confidence
"""

import sqlite3
import re
import unicodedata
import uuid
from collections import defaultdict
from rapidfuzz import fuzz
from jellyfish import soundex

DB = "austin_finance.db"

# ── Nickname table ─────────────────────────────────────────────────────────────
NICKNAMES = {
    "bill": "william", "billy": "william", "will": "william", "willy": "william",
    "bob": "robert", "rob": "robert", "bobby": "robert",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "tom": "thomas", "tommy": "thomas",
    "mike": "michael", "mick": "michael", "mickey": "michael",
    "dick": "richard", "rick": "richard", "ricky": "richard",
    "dave": "david", "davy": "david",
    "joe": "joseph", "joey": "joseph",
    "sue": "susan", "susie": "susan", "suzy": "susan",
    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth",
    "kate": "katherine", "kathy": "katherine", "kat": "katherine",
    "katie": "kathryn",
    "chris": "christopher",
    "dan": "daniel", "danny": "daniel",
    "pat": "patricia", "patty": "patricia",
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
    "jerry": "gerald", "gerry": "gerald",
    "chuck": "charles", "charlie": "charles",
    "harry": "harold",
    "hank": "henry",
    "jack": "john",
    "peggy": "margaret", "meg": "margaret", "maggie": "margaret", "peg": "margaret",
    "cathy": "catherine", "cat": "catherine",
    "barb": "barbara", "babs": "barbara",
    "cindy": "cynthia",
    "dot": "dorothy", "dottie": "dorothy",
    "frank": "francis",
    "fred": "frederick",
    "jake": "jacob",
    "lenny": "leonard",
    "lou": "louis",
    "nan": "nancy",
    "nat": "nathaniel",
    "ray": "raymond",
    "ron": "ronald", "ronnie": "ronald",
    "russ": "russell",
    "stu": "stuart",
    "tim": "timothy", "timmy": "timothy",
    "vince": "vincent",
    "walt": "walter",
    "phil": "philip",
    "jan": "janet",
    "lew": "lewis",
    "julia": "julie",
    "jay": "james",
    "max": "maximilian",
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
    "don": "donald",
    "pam": "pamela",
    "mandy": "amanda",
}

NOISE_EMPLOYERS = {
    "city of austin", "retired", "self", "self employed", "self-employed",
    "selfemployed", "not employed", "not-employed", "na", "n/a", "none",
    "unknown", "best efforts", "n a", "homemaker", "student", "unemployed",
    "housewife", "various", "austin police department", "retire",
}

# ── Normalisation helpers ──────────────────────────────────────────────────────
def to_ascii(s):
    try:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    except Exception:
        return s

def normalize_name(raw):
    s = to_ascii(raw or "").lower().strip()
    s = re.sub(r"[^a-z ,]", "", s)
    if "," in s:
        parts = s.split(",", 1)
        last  = parts[0].strip()
        first = parts[1].strip().split()[0] if parts[1].strip() else ""
    else:
        tokens = s.split()
        last  = tokens[-1] if tokens else ""
        first = tokens[0]  if len(tokens) > 1 else ""
    first = NICKNAMES.get(first, first)
    return last, first

def normalize_zip(city_state_zip):
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", city_state_zip or "")
    return m.group(1) if m else ""

def normalize_employer(emp):
    s = to_ascii(emp or "").lower().strip()
    s = re.sub(r"\b(inc|llc|corp|co|ltd|pc|lp|pllc|pa)\.?\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return "" if s in NOISE_EMPLOYERS else s

def normalize_occupation(occ):
    s = to_ascii(occ or "").lower().strip()
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# ── Union-Find ─────────────────────────────────────────────────────────────────
class UnionFind:
    def __init__(self):
        self.parent = {}
        self.rank   = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x]   = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

# ── Scoring ────────────────────────────────────────────────────────────────────
FLOOR = 0.78

def score_pair(a, b):
    last_score  = fuzz.token_sort_ratio(a["last"],  b["last"])  / 100.0
    first_score = fuzz.token_sort_ratio(a["first"], b["first"]) / 100.0

    if last_score < FLOOR or first_score < FLOOR:
        return round(min(0.50 * last_score + 0.50 * first_score, 0.69), 4)

    if a["zip5"] and b["zip5"]:
        zip_score = 1.0 if a["zip5"] == b["zip5"] else 0.0
    else:
        zip_score = 0.5

    if a["emp_occ"] and b["emp_occ"]:
        emp_score = fuzz.token_sort_ratio(a["emp_occ"], b["emp_occ"]) / 100.0
    else:
        emp_score = 0.5

    return round(0.30 * last_score + 0.30 * first_score + 0.30 * zip_score + 0.10 * emp_score, 4)

# ── Main pipeline ──────────────────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()

    # ── 1. Load all individual records ────────────────────────────────────────
    print("Loading records...")
    cur.execute("""
        SELECT rowid, donor, city_state_zip, donor_reported_employer, donor_reported_occupation
        FROM campaign_finance
        WHERE donor_type IN ('INDIVIDUAL','Individual') AND donor LIKE '%,%'
    """)
    raw_rows = cur.fetchall()
    print(f"  {len(raw_rows):,} individual records")

    records = []
    for rowid, raw_name, zip_raw, emp_raw, occ_raw in raw_rows:
        last, first = normalize_name(raw_name)
        if not last or not first:
            continue
        zip5    = normalize_zip(zip_raw)
        emp     = normalize_employer(emp_raw)
        occ     = normalize_occupation(occ_raw)
        emp_occ = " ".join(sorted(set((emp + " " + occ).split())))
        records.append({
            "rowid": rowid,
            "raw":   raw_name,
            "last":  last,
            "first": first,
            "zip5":  zip5,
            "emp_occ": emp_occ,
        })

    print(f"  {len(records):,} normalized records")

    # ── 2. Blocking ───────────────────────────────────────────────────────────
    print("Blocking...")
    seen_pairs = set()
    candidate_pairs = []

    def add_block(block_dict, max_block=50):
        for members in block_dict.values():
            if len(members) < 2 or len(members) > max_block:
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    key  = (min(a, b), max(a, b))
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        candidate_pairs.append(key)

    # Block A: exact last_name + zip5
    block_a = defaultdict(list)
    for i, r in enumerate(records):
        if r["last"] and r["zip5"]:
            block_a[(r["last"], r["zip5"])].append(i)
    add_block(block_a)
    print(f"  Block A (last+zip):     {len(candidate_pairs):,} pairs")

    # Block B: soundex(last) + zip5  — catches spelling variants
    count_before = len(candidate_pairs)
    block_b = defaultdict(list)
    for i, r in enumerate(records):
        if r["last"] and r["zip5"]:
            try:
                sdx = soundex(r["last"])
            except Exception:
                continue
            block_b[(sdx, r["zip5"])].append(i)
    add_block(block_b)
    print(f"  Block B (soundex+zip):  {len(candidate_pairs):,} pairs (+{len(candidate_pairs)-count_before:,})")

    print(f"  Total candidate pairs:  {len(candidate_pairs):,}")

    # ── 3. Score all pairs ────────────────────────────────────────────────────
    print("Scoring...")
    uf           = UnionFind()
    review_rows  = []
    auto_count   = 0
    review_count = 0

    for idx, (i, j) in enumerate(candidate_pairs):
        if idx % 100000 == 0 and idx > 0:
            print(f"  {idx:,} / {len(candidate_pairs):,} scored...")
        a = records[i]
        b = records[j]
        s = score_pair(a, b)

        if s >= 0.83:
            uf.union(i, j)
            auto_count += 1
        elif s >= 0.65:
            review_rows.append((a["raw"], b["raw"], a["zip5"], b["zip5"],
                                a["emp_occ"], b["emp_occ"], round(s, 4)))
            review_count += 1

    print(f"  Auto-matched pairs:  {auto_count:,}")
    print(f"  Review queue pairs:  {review_count:,}")

    # ── 4. Assign donor_ids via Union-Find clusters ───────────────────────────
    print("Clustering...")
    root_to_id = {}
    for i in range(len(records)):
        root = uf.find(i)
        if root not in root_to_id:
            root_to_id[root] = str(uuid.uuid4())

    for i, r in enumerate(records):
        r["donor_id"] = root_to_id[uf.find(i)]

    # ── 5. Build donor_identities ─────────────────────────────────────────────
    print("Building donor_identities...")
    identity_map = defaultdict(lambda: {
        "names": [], "zips": [], "employers": [],
        "total": 0.0, "recipients": set(),
        "first_seen": "9999", "last_seen": "0000",
        "rowids": []
    })

    # Pull contribution amounts and dates per rowid
    cur.execute("""
        SELECT rowid, contribution_amount, contribution_date, recipient
        FROM campaign_finance
        WHERE donor_type IN ('INDIVIDUAL','Individual') AND donor LIKE '%,%'
    """)
    financial = {row[0]: row[1:] for row in cur.fetchall()}

    for r in records:
        did  = r["donor_id"]
        meta = identity_map[did]
        meta["names"].append(r["raw"])
        if r["zip5"]:
            meta["zips"].append(r["zip5"])
        if r["emp_occ"]:
            meta["employers"].append(r["emp_occ"])
        meta["rowids"].append(r["rowid"])

        fin = financial.get(r["rowid"])
        if fin:
            amt, date, recipient = fin
            try:
                meta["total"] += float(amt or 0)
            except Exception:
                pass
            if date:
                if date < meta["first_seen"]: meta["first_seen"] = date
                if date > meta["last_seen"]:  meta["last_seen"]  = date
            if recipient:
                meta["recipients"].add(recipient)

    def most_common(lst):
        if not lst: return ""
        return max(set(lst), key=lst.count)

    # ── 6. Write to DB ────────────────────────────────────────────────────────
    print("Writing to database...")

    cur.execute("DROP TABLE IF EXISTS donor_identities")
    cur.execute("""
        CREATE TABLE donor_identities (
            donor_id            TEXT PRIMARY KEY,
            canonical_name      TEXT,
            canonical_zip       TEXT,
            canonical_employer  TEXT,
            total_donated       REAL,
            campaign_count      INTEGER,
            campaigns           TEXT,
            record_count        INTEGER,
            first_seen          TEXT,
            last_seen           TEXT
        )
    """)

    identity_rows = []
    donor_id_lookup = {}   # rowid → donor_id

    for did, meta in identity_map.items():
        canonical_name     = most_common(meta["names"])
        canonical_zip      = most_common(meta["zips"])
        canonical_employer = most_common(meta["employers"])
        campaigns          = "|".join(sorted(meta["recipients"]))
        first_seen         = meta["first_seen"] if meta["first_seen"] != "9999" else ""
        last_seen          = meta["last_seen"]  if meta["last_seen"]  != "0000" else ""

        identity_rows.append((
            did, canonical_name, canonical_zip, canonical_employer,
            round(meta["total"], 2), len(meta["recipients"]), campaigns,
            len(meta["rowids"]), first_seen, last_seen
        ))
        for rowid in meta["rowids"]:
            donor_id_lookup[rowid] = did

    cur.executemany("""
        INSERT INTO donor_identities VALUES (?,?,?,?,?,?,?,?,?,?)
    """, identity_rows)

    # Add donor_id + match_confidence to campaign_finance (drop first if re-running)
    try:
        cur.execute("ALTER TABLE campaign_finance ADD COLUMN donor_id TEXT")
    except Exception:
        cur.execute("UPDATE campaign_finance SET donor_id = NULL")
    try:
        cur.execute("ALTER TABLE campaign_finance ADD COLUMN match_confidence TEXT")
    except Exception:
        cur.execute("UPDATE campaign_finance SET match_confidence = NULL")

    update_rows = []
    for r in records:
        cluster_size = len(identity_map[r["donor_id"]]["rowids"])
        confidence   = "exact" if cluster_size == 1 else "high"
        update_rows.append((r["donor_id"], confidence, r["rowid"]))

    cur.executemany("""
        UPDATE campaign_finance SET donor_id=?, match_confidence=? WHERE rowid=?
    """, update_rows)

    # Review queue table
    cur.execute("DROP TABLE IF EXISTS review_queue")
    cur.execute("""
        CREATE TABLE review_queue (
            donor_a     TEXT,
            donor_b     TEXT,
            zip_a       TEXT,
            zip_b       TEXT,
            emp_occ_a   TEXT,
            emp_occ_b   TEXT,
            score       REAL,
            resolved    INTEGER DEFAULT 0
        )
    """)
    cur.executemany("INSERT INTO review_queue VALUES (?,?,?,?,?,?,?,0)", review_rows)

    conn.commit()
    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    total_identities = len(identity_map)
    merged = sum(1 for m in identity_map.values() if len(m["rowids"]) > 1)
    print(f"\n=== DONE ===")
    print(f"  Records processed:     {len(records):,}")
    print(f"  Unique donor_ids:      {total_identities:,}")
    print(f"  Merged identities:     {merged:,}  (same person, multiple records)")
    print(f"  Singleton identities:  {total_identities - merged:,}  (one record only)")
    print(f"  Review queue entries:  {review_count:,}")
    print(f"\n  Tables written: donor_identities, review_queue")
    print(f"  campaign_finance updated with donor_id + match_confidence")

if __name__ == "__main__":
    main()
