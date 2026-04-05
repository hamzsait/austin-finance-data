"""
Employer identity canonicalization pipeline.

Steps:
  1. Collect all unique employer strings from individual donors
     AND all entity donor names from ENTITY records
  2. Normalize (strip suffixes, punctuation, noise)
  3. Block by (first_token, first6_chars) to generate candidate pairs
  4. Score with token_sort_ratio + token_set_ratio
     (handles both word-order variation AND subset cases like
      'Endeavor' vs 'Endeavor Real Estate Group')
  5. Union-Find clustering → stable employer_id
  6. Cross-match entity donor names against employer_identities
     so firm PAC donations link to employee donations
  7. Write employer_identities, employer_review_queue
  8. Tag campaign_finance with employer_id + employer_match_confidence
"""

import sqlite3
import re
import uuid
import unicodedata
from collections import defaultdict
from rapidfuzz import fuzz

DB = "austin_finance.db"

# ── Legal suffix / noise stripping ────────────────────────────────────────────
LEGAL_SUFFIXES = re.compile(
    r'\b(pllc|llc|llp|lllp|lp|pc|pa|inc|corp|co|ltd|plc|na|'
    r'incorporated|limited|associates|association|assoc|'
    r'group|partners|partnership|ventures|holdings|enterprises|'
    r'solutions|services|systems|consulting|consultants|'
    r'international|global|national|management|properties|'
    r'industries|technologies|technology)\b\.?',
    re.IGNORECASE
)

# Tokens that, when present in one string but not the other, signal different orgs.
# Restricted to: geographic place names, demographic identifiers, and specific
# function words that indicate categorically different entities under the same brand.
# Industry words (realty, development, medical, counseling) are intentionally excluded
# because they often just describe variants of the same organisation.
# If strings differ on ANY of these, score is penalised × 0.65.
DISCRIMINATING_TOKENS = {
    # Geographic — US cities / states that distinguish separate chapters/offices
    "chicago", "dallas", "houston", "denver", "atlanta", "miami",
    "seattle", "portland", "boston", "phoenix", "detroit", "cleveland",
    "minneapolis", "nashville", "charlotte", "raleigh", "richmond",
    "virginia", "wisconsin", "illinois", "colorado", "georgia", "florida",
    "california", "michigan", "ohio", "oregon", "washington",
    "central", "north", "south", "east", "west", "northern", "southern",
    "eastern", "western",
    # Demographic / community identity — distinct chapters of advocacy orgs
    "asian", "black", "hispanic", "latino", "latina", "african",
    "women", "woman", "veteran", "disabled", "lgbtq", "indigenous",
    # Specific function words — categorically different entities sharing a brand
    "attorney", "attorneys", "clerk", "governor", "lieutenant",
    "forge", "mortgage", "church", "school",
}

# Words so generic they add no discriminating signal when alone
NOISE_EMPLOYERS = {
    "self", "self employed", "self-employed", "selfemployed",
    "retired", "retire", "not employed", "not-employed", "unemployed",
    "na", "n/a", "none", "unknown", "best efforts", "n a",
    "homemaker", "student", "housewife", "various",
    "best effort", "not applicable", "not available",
    "information requested", "information not available",
}

# Job title phrases — people filling employer field with their title instead
JOB_TITLES = re.compile(
    r'^(attorney|attorney at law|lawyer|counsel|counselor|'
    r'software engineer|software developer|software designer|engineer|'
    r'marketing manager|marketing director|marketing|'
    r'real estate investor|real estate agent|real estate broker|'
    r'business owner|business|independent contractor|contractor|'
    r'consultant|freelance|freelancer|'
    r'physician|doctor|nurse|nurse practitioner|dentist|therapist|'
    r'professor|teacher|educator|faculty|'
    r'accountant|cpa|financial advisor|'
    r'architect|designer|'
    r'manager|director|executive|officer|president|ceo|cfo|coo|'
    r'sales|sales representative|sales manager|'
    r'campaign worker|campaign|'
    r'investor|entrepreneur|'
    r'retired attorney|retired teacher|retired engineer|retired professor)$',
    re.IGNORECASE
)

def to_ascii(s):
    try:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    except Exception:
        return s

def normalize_employer(raw):
    """Return normalized employer string, or '' if noise/job title/empty."""
    s = to_ascii(raw or "").lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s in NOISE_EMPLOYERS:
        return ""
    # strip legal suffixes
    s = LEGAL_SUFFIXES.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s or s in NOISE_EMPLOYERS:
        return ""
    # filter job titles masquerading as employers
    if JOB_TITLES.match(s):
        return ""
    return s

def score_employers(a, b):
    """
    Combined score for two normalized employer strings.
    token_sort_ratio handles word-order variation.
    token_set_ratio handles subset cases (Endeavor vs Endeavor Real Estate Group).

    Short-string guard: if one string is a single token and the other is
    multi-token, require a higher bar (0.92) to avoid 'Anderson' absorbing
    'Anderson Coffee' or 'Bartlett' absorbing 'Bartlett Cocke General'.
    """
    if not a or not b:
        return 0.0

    tokens_a = a.split()
    tokens_b = b.split()
    is_asymmetric = (len(tokens_a) == 1) != (len(tokens_b) == 1)

    sort_score = fuzz.token_sort_ratio(a, b) / 100.0
    set_score  = fuzz.token_set_ratio(a, b)  / 100.0
    score = round(0.60 * sort_score + 0.40 * set_score, 4)

    # Penalise single-token vs multi-token matches unless very tight
    if is_asymmetric and score < 0.92:
        score = round(score * 0.75, 4)

    # Discriminating token penalty: tokens unique to each side
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    unique_a = set_a - set_b
    unique_b = set_b - set_a
    disc_a = unique_a & DISCRIMINATING_TOKENS
    disc_b = unique_b & DISCRIMINATING_TOKENS
    if disc_a or disc_b:
        score = round(score * 0.65, 4)

    # Sequential identifier check: strings identical except trailing digit/id
    # e.g. "oflp 1" vs "oflp 2" — cap at 0.60
    strip_trailing = re.compile(r'\s*\d+\s*$')
    base_a = strip_trailing.sub("", a).strip()
    base_b = strip_trailing.sub("", b).strip()
    if base_a == base_b and a != b:
        return min(score, 0.60)

    return score

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

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()

    # ── 1. Collect employer strings ────────────────────────────────────────────
    print("Collecting employer strings...")

    # Individual donor employers
    cur.execute("""
        SELECT donor_reported_employer, COUNT(*) as cnt
        FROM campaign_finance
        WHERE donor_type IN ('INDIVIDUAL','Individual')
        AND donor_reported_employer != '' AND donor_reported_employer IS NOT NULL
        GROUP BY donor_reported_employer
    """)
    ind_employers = {row[0]: row[1] for row in cur.fetchall()}

    # Entity donor names (these may match employer strings)
    cur.execute("""
        SELECT donor, SUM(CAST(contribution_amount AS REAL)) as total,
               COUNT(*) as cnt
        FROM campaign_finance
        WHERE donor_type IN ('ENTITY','Entity')
        AND donor != '' AND donor IS NOT NULL
        GROUP BY donor
    """)
    entity_donors = {row[0]: {"total": row[1] or 0, "cnt": row[2]}
                     for row in cur.fetchall()}

    print(f"  {len(ind_employers):,} unique individual employer strings")
    print(f"  {len(entity_donors):,} unique entity donor names")

    # ── 2. Build normalized records ────────────────────────────────────────────
    print("Normalizing...")

    # Track: norm_string → list of (raw_string, source, weight)
    # source: 'individual' or 'entity'
    records = []   # {idx, raw, norm, source, frequency}

    seen_norms = {}  # norm → first idx (for dedup within same source)

    for raw, cnt in ind_employers.items():
        norm = normalize_employer(raw)
        if not norm:
            continue
        if norm in seen_norms:
            records[seen_norms[norm]]["frequency"] += cnt
            records[seen_norms[norm]]["raw_variants"].append(raw)
        else:
            idx = len(records)
            seen_norms[norm] = idx
            records.append({
                "idx": idx, "raw": raw, "norm": norm,
                "source": "individual", "frequency": cnt,
                "raw_variants": [raw]
            })

    # Entity donors get their own entries (not deduplicated against individual employers yet)
    entity_start = len(records)
    entity_norm_to_idx = {}
    for raw, meta in entity_donors.items():
        norm = normalize_employer(raw)
        if not norm:
            continue
        idx = len(records)
        entity_norm_to_idx[norm] = idx
        records.append({
            "idx": idx, "raw": raw, "norm": norm,
            "source": "entity", "frequency": meta["cnt"],
            "entity_total": meta["total"],
            "raw_variants": [raw]
        })

    print(f"  {len(records):,} normalized employer records "
          f"({entity_start} individual, {len(records)-entity_start} entity)")

    # ── 3. Blocking ────────────────────────────────────────────────────────────
    print("Blocking...")

    seen_pairs = set()
    candidate_pairs = []

    def add_block(block_dict, max_block=30):
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

    # Block A: first normalized token
    block_a = defaultdict(list)
    for r in records:
        tokens = r["norm"].split()
        if tokens:
            block_a[tokens[0]].append(r["idx"])
    add_block(block_a)
    after_a = len(candidate_pairs)
    print(f"  Block A (first token):  {after_a:,} pairs")

    # Block B: first 6 chars of normalized name
    block_b = defaultdict(list)
    for r in records:
        if len(r["norm"]) >= 4:
            block_b[r["norm"][:6]].append(r["idx"])
    add_block(block_b)
    print(f"  Block B (first 6 chars): {len(candidate_pairs):,} pairs (+{len(candidate_pairs)-after_a:,})")

    print(f"  Total candidate pairs: {len(candidate_pairs):,}")

    # ── 4. Score ───────────────────────────────────────────────────────────────
    print("Scoring...")
    uf            = UnionFind()
    review_rows   = []
    auto_count    = 0
    review_count  = 0
    AUTO_THRESHOLD   = 0.85
    REVIEW_LOW       = 0.65

    for idx, (i, j) in enumerate(candidate_pairs):
        if idx % 50000 == 0 and idx > 0:
            print(f"  {idx:,} / {len(candidate_pairs):,} scored...")
        a = records[i]
        b = records[j]
        s = score_employers(a["norm"], b["norm"])

        if s >= AUTO_THRESHOLD:
            uf.union(i, j)
            auto_count += 1
        elif s >= REVIEW_LOW:
            review_rows.append((
                a["raw"], b["raw"],
                a["norm"], b["norm"],
                a["source"], b["source"],
                round(s, 4)
            ))
            review_count += 1

    print(f"  Auto-matched: {auto_count:,}  |  Review queue: {review_count:,}")

    # ── 5. Build employer_identities ───────────────────────────────────────────
    print("Building employer_identities...")

    cluster_map = defaultdict(list)
    for r in records:
        root = uf.find(r["idx"])
        cluster_map[root].append(r)

    def most_common_raw(members):
        """Pick canonical name = highest frequency individual employer, or entity name."""
        ind = [m for m in members if m["source"] == "individual"]
        if ind:
            return max(ind, key=lambda m: m["frequency"])["raw"]
        return max(members, key=lambda m: m["frequency"])["raw"]

    employer_id_by_idx = {}
    identity_rows      = []

    root_to_eid = {}
    for root, members in cluster_map.items():
        eid = str(uuid.uuid4())
        root_to_eid[root] = eid
        for m in members:
            employer_id_by_idx[m["idx"]] = eid

        canonical  = most_common_raw(members)
        variants   = "|".join(sorted(set(
            v for m in members for v in m["raw_variants"]
        )))
        has_entity = any(m["source"] == "entity" for m in members)
        entity_names = "|".join(
            m["raw"] for m in members if m["source"] == "entity"
        )
        total_freq = sum(m["frequency"] for m in members)

        identity_rows.append((
            eid, canonical, variants,
            None,           # industry — to be filled in a future session
            1 if has_entity else 0,
            entity_names,
            total_freq      # record_count proxy
        ))

    # ── 6. Write employer_identities ──────────────────────────────────────────
    print("Writing to database...")

    cur.execute("DROP TABLE IF EXISTS employer_identities")
    cur.execute("""
        CREATE TABLE employer_identities (
            employer_id         TEXT PRIMARY KEY,
            canonical_name      TEXT,
            name_variants       TEXT,
            industry            TEXT,
            has_entity_donor    INTEGER DEFAULT 0,
            entity_donor_names  TEXT,
            record_count        INTEGER,
            total_individual_donated  REAL DEFAULT 0,
            total_entity_donated      REAL DEFAULT 0,
            individual_donor_count    INTEGER DEFAULT 0,
            campaign_count            INTEGER DEFAULT 0,
            campaigns                 TEXT,
            first_seen          TEXT,
            last_seen           TEXT
        )
    """)
    cur.executemany("""
        INSERT INTO employer_identities
        (employer_id, canonical_name, name_variants, industry,
         has_entity_donor, entity_donor_names, record_count)
        VALUES (?,?,?,?,?,?,?)
    """, identity_rows)

    # ── 7. employer_review_queue ───────────────────────────────────────────────
    cur.execute("DROP TABLE IF EXISTS employer_review_queue")
    cur.execute("""
        CREATE TABLE employer_review_queue (
            employer_a      TEXT,
            employer_b      TEXT,
            norm_a          TEXT,
            norm_b          TEXT,
            source_a        TEXT,
            source_b        TEXT,
            score           REAL,
            resolved        INTEGER DEFAULT 0,
            same_entity     INTEGER DEFAULT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO employer_review_queue VALUES (?,?,?,?,?,?,?,0,NULL)",
        review_rows
    )

    # ── 8. Tag campaign_finance ────────────────────────────────────────────────
    print("Tagging campaign_finance records...")

    # Build raw → employer_id lookup
    raw_to_eid = {}
    for r in records:
        eid = employer_id_by_idx.get(r["idx"])
        if eid:
            for variant in r["raw_variants"]:
                raw_to_eid[variant] = eid

    for col in ["employer_id", "employer_match_confidence"]:
        try:
            cur.execute(f"ALTER TABLE campaign_finance ADD COLUMN {col} TEXT")
        except Exception:
            cur.execute(f"UPDATE campaign_finance SET {col} = NULL")

    # Individual donors — match on employer field
    cur.execute("""
        SELECT rowid, donor_reported_employer
        FROM campaign_finance
        WHERE donor_type IN ('INDIVIDUAL','Individual')
        AND donor_reported_employer != '' AND donor_reported_employer IS NOT NULL
    """)
    ind_rows = cur.fetchall()

    ind_updates = []
    for rowid, emp_raw in ind_rows:
        eid = raw_to_eid.get(emp_raw)
        if eid:
            norm = normalize_employer(emp_raw)
            # confidence: exact if raw string matched directly
            conf = "exact"
            ind_updates.append((eid, conf, rowid))

    cur.executemany(
        "UPDATE campaign_finance SET employer_id=?, employer_match_confidence=? WHERE rowid=?",
        ind_updates
    )

    # Entity donors — match on donor name
    cur.execute("""
        SELECT rowid, donor
        FROM campaign_finance
        WHERE donor_type IN ('ENTITY','Entity')
        AND donor != '' AND donor IS NOT NULL
    """)
    ent_rows = cur.fetchall()

    ent_updates = []
    for rowid, donor_raw in ent_rows:
        eid = raw_to_eid.get(donor_raw)
        if eid:
            ent_updates.append((eid, "exact", rowid))

    cur.executemany(
        "UPDATE campaign_finance SET employer_id=?, employer_match_confidence=? WHERE rowid=?",
        ent_updates
    )

    # ── 9. Back-fill financial stats on employer_identities ───────────────────
    print("Back-filling financial stats...")

    # Aggregate individual stats in one pass
    cur.execute("""
        SELECT employer_id,
               SUM(CAST(contribution_amount AS REAL)),
               COUNT(DISTINCT donor_id),
               COUNT(DISTINCT recipient),
               GROUP_CONCAT(DISTINCT recipient),
               MIN(contribution_date),
               MAX(contribution_date)
        FROM campaign_finance
        WHERE employer_id IS NOT NULL
        AND donor_type IN ('INDIVIDUAL','Individual')
        GROUP BY employer_id
    """)
    ind_stats = {r[0]: r[1:] for r in cur.fetchall()}

    # Aggregate entity stats in one pass
    cur.execute("""
        SELECT employer_id,
               SUM(CAST(contribution_amount AS REAL)),
               COUNT(DISTINCT recipient),
               MIN(contribution_date),
               MAX(contribution_date)
        FROM campaign_finance
        WHERE employer_id IS NOT NULL
        AND donor_type IN ('ENTITY','Entity')
        GROUP BY employer_id
    """)
    ent_stats = {r[0]: r[1:] for r in cur.fetchall()}

    # Build update rows
    stat_updates = []
    cur.execute("SELECT employer_id FROM employer_identities")
    for (eid,) in cur.fetchall():
        # ind: (sum, donor_count, camp_count, camp_names, first, last)
        ind = ind_stats.get(eid, (0, 0, 0, None, None, None))
        # ent: (sum, camp_count, first, last)
        ent = ent_stats.get(eid, (0, 0, None, None))
        ind_total   = ind[0] or 0
        donor_count = ind[1] or 0
        camp_count  = (ind[2] or 0)
        dates = [d for d in [ind[4], ind[5], ent[2], ent[3]] if d]
        first_seen = min(dates) if dates else None
        last_seen  = max(dates) if dates else None
        stat_updates.append((
            ind_total, ent[0] or 0,
            donor_count, camp_count,
            first_seen, last_seen,
            eid
        ))

    cur.executemany("""
        UPDATE employer_identities SET
            total_individual_donated = ?,
            total_entity_donated     = ?,
            individual_donor_count   = ?,
            campaign_count           = ?,
            first_seen               = ?,
            last_seen                = ?
        WHERE employer_id = ?
    """, stat_updates)

    # Campaign names need a separate pass (GROUP_CONCAT per employer)
    cur.execute("""
        SELECT employer_id, GROUP_CONCAT(DISTINCT recipient)
        FROM campaign_finance
        WHERE employer_id IS NOT NULL
        GROUP BY employer_id
    """)
    camp_updates = cur.fetchall()
    cur.executemany(
        "UPDATE employer_identities SET campaigns=? WHERE employer_id=?",
        [(r[1], r[0]) for r in camp_updates]
    )

    conn.commit()

    # ── Summary ────────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM employer_identities")
    total_emp = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM employer_identities WHERE has_entity_donor = 1")
    linked = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM employer_review_queue")
    rq = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM campaign_finance WHERE employer_id IS NOT NULL")
    tagged = cur.fetchone()[0]

    print(f"\n=== DONE ===")
    print(f"  Canonical employer identities:  {total_emp:,}")
    print(f"  Linked to entity donors:        {linked:,}")
    print(f"  Review queue entries:           {rq:,}")
    print(f"  campaign_finance records tagged: {tagged:,}")

    print(f"\n=== TOP 15 EMPLOYERS BY COMBINED GIVING ===\n")
    cur.execute("""
        SELECT canonical_name,
               individual_donor_count,
               ROUND(total_individual_donated, 2) as ind_total,
               ROUND(total_entity_donated, 2) as ent_total,
               ROUND(total_individual_donated + total_entity_donated, 2) as combined,
               campaign_count,
               has_entity_donor
        FROM employer_identities
        ORDER BY combined DESC
        LIMIT 15
    """)
    print(f"  {'Employer':<45} {'Donors':>7} {'Ind $':>12} {'Entity $':>12} {'Combined':>12} {'Camps':>6} {'PAC?':>5}")
    print("  " + "-"*102)
    for r in cur.fetchall():
        pac = "YES" if r[6] else ""
        print(f"  {r[0][:44]:<45} {r[1]:>7,} {r[2]:>12,.0f} {r[3]:>12,.0f} {r[4]:>12,.0f} {r[5]:>6} {pac:>5}")

    print(f"\n=== REVIEW QUEUE SAMPLE (top 20 by score) ===\n")
    cur.execute("""
        SELECT DISTINCT employer_a, employer_b, source_a, source_b, score
        FROM employer_review_queue
        ORDER BY score DESC LIMIT 20
    """)
    for r in cur.fetchall():
        print(f"  [{r[4]:.3f}] [{r[2]}/{r[3]}]  '{r[0]}'")
        print(f"           vs  '{r[1]}'")

    conn.close()

if __name__ == "__main__":
    main()
