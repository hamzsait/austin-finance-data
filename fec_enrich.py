"""
FEC Federal Donation Enrichment
================================
Queries the FEC /schedules/schedule_a/ endpoint for each local donor,
confirms identity via fuzzy matching, classifies committees as Dem/Rep/Other,
then writes partisan lean scores to donor_identities.

Usage:
    python fec_enrich.py              # process top 2000 donors
    python fec_enrich.py --dry-run    # print results, no DB writes
    python fec_enrich.py --limit 50   # process top N donors
    python fec_enrich.py --reset      # clear fec_matched=1 flags (re-process all)
"""

import sqlite3, re, sys, io, time, argparse, unicodedata
from collections import deque
from datetime import datetime, timezone
import requests
from rapidfuzz import fuzz

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

# ── Config ─────────────────────────────────────────────────────────────────────
DB           = "austin_finance.db"
FEC_API_KEYS = [
    "HATnmUvyw55nkfKvbTg7x5uOKA7t9qqrgWM4sEJ2",
    "Pzl0uV3zoid7fK7hAHajSjmfAy8hYlqpBcuRHiAm",
]
FEC_API_KEY  = FEC_API_KEYS[0]  # kept for backward compat
FEC_BASE     = "https://api.open.fec.gov/v1"
TOP_N        = 2000
MATCH_THRESHOLD = 75   # composite score floor (0-100)
LARGE_SET_THRESHOLD = 300   # if result count > this, add zip filter

NICKNAMES = {
    "bill": "william", "billy": "william", "will": "william",
    "bob": "robert", "rob": "robert", "bobby": "robert",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "tom": "thomas", "tommy": "thomas",
    "mike": "michael", "mick": "michael",
    "dick": "richard", "rick": "richard",
    "dave": "david",
    "joe": "joseph", "joey": "joseph",
    "sue": "susan", "susie": "susan",
    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth",
    "kate": "katherine", "kathy": "katherine",
    "chris": "christopher",
    "dan": "daniel", "danny": "daniel",
    "sam": "samuel",
    "ed": "edward", "ted": "edward",
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
    "hank": "henry",
    "jack": "john", "jon": "john", "johnny": "john",
    "peggy": "margaret", "meg": "margaret",
    "frank": "francis",
    "fred": "frederick",
    "jake": "jacob",
    "ron": "ronald",
    "tim": "timothy",
    "phil": "philip",
    "don": "donald",
    "pam": "pamela",
    "deb": "deborah", "debbie": "deborah",
    "gene": "eugene",
    "drew": "andrew",
}

SUFFIX_STRIP = re.compile(r'\b(jr|sr|ii|iii|iv|dr|mr|mrs|ms|prof|rev|hon)\.?\b', re.IGNORECASE)
DEM_PATTERNS = re.compile(
    r'\b(democrat|democratic|dccc|dscc|dlcc|actblue|emily.?s list|'
    r'planned parenthood|moveon|sierra club|afscme|seiu|nea|afl.cio|'
    r'progressive|nrdc action|lgbtq|biden|obama|clinton|pelosi|'
    r'wendell|majority pac|house majority|senate majority)\b', re.IGNORECASE)
REP_PATTERNS = re.compile(
    r'\b(republican|gop|rnc|nrcc|nrsc|rslc|trump|maga|heritage action|'
    r'club for growth|tea party|freedom works|susan b anthony|nra|'
    r'nfib|associated builders|american energy alliance|winred|'
    r'mitt romney|mcconnell|mccarthy)\b', re.IGNORECASE)


# ── Rate limiter ───────────────────────────────────────────────────────────────
class RateLimiter:
    def __init__(self, max_calls=1000, window_seconds=600):
        self.max_calls = max_calls
        self.window = window_seconds
        self.timestamps = deque()

    def wait(self):
        now = time.time()
        while self.timestamps and now - self.timestamps[0] > self.window:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.max_calls:
            sleep_for = self.window - (now - self.timestamps[0]) + 0.5
            print(f"  [rate limit] sleeping {sleep_for:.1f}s ...", flush=True)
            time.sleep(sleep_for)
        self.timestamps.append(time.time())


# ── DB setup ───────────────────────────────────────────────────────────────────
def setup_db(conn):
    new_cols = [
        "fec_partisan_lean REAL",
        "fec_total_dem REAL DEFAULT 0",
        "fec_total_rep REAL DEFAULT 0",
        "fec_total_other REAL DEFAULT 0",
        "fec_total_donations INTEGER DEFAULT 0",
        "fec_matched INTEGER DEFAULT 0",
        "fec_matched_at TEXT",
    ]
    for col_def in new_cols:
        col_name = col_def.split()[0]
        try:
            conn.execute(f"ALTER TABLE donor_identities ADD COLUMN {col_def}")
        except Exception:
            pass  # already exists

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fec_committee_cache (
            committee_id    TEXT PRIMARY KEY,
            party_code      TEXT,
            committee_type  TEXT,
            committee_name  TEXT,
            classification  TEXT NOT NULL,
            fetched_at      TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fec_contributions_raw (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id                TEXT NOT NULL,
            committee_id            TEXT NOT NULL,
            contribution_amount     REAL,
            contribution_date       TEXT,
            fec_contributor_name    TEXT,
            fec_contributor_city    TEXT,
            fec_contributor_zip     TEXT,
            fec_employer            TEXT,
            fec_occupation          TEXT,
            fec_sub_id              TEXT,
            confirm_score           REAL,
            UNIQUE(donor_id, fec_sub_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fec_raw_sub ON fec_contributions_raw(fec_sub_id)")
    # Add columns to existing tables if they pre-date this schema change
    for col_def in ["fec_employer TEXT", "fec_occupation TEXT", "fec_sub_id TEXT"]:
        try:
            conn.execute(f"ALTER TABLE fec_contributions_raw ADD COLUMN {col_def}")
        except Exception:
            pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fec_raw_donor ON fec_contributions_raw(donor_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fec_raw_committee ON fec_contributions_raw(committee_id)")
    conn.commit()
    print("DB schema ready.")


# ── Name normalisation ─────────────────────────────────────────────────────────
def to_ascii(s):
    try:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    except Exception:
        return s

def _parse_name(raw):
    """Return (last, first) from any format."""
    s = to_ascii(raw or "").lower()
    s = SUFFIX_STRIP.sub("", s)
    s = re.sub(r"[^a-z ,'-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if "," in s:
        parts = s.split(",", 1)
        last  = parts[0].strip()
        first = parts[1].strip().split()[0] if parts[1].strip() else ""
    else:
        tokens = s.split()
        last   = tokens[-1] if tokens else ""
        first  = tokens[0] if len(tokens) > 1 else ""
    first = NICKNAMES.get(first, first)
    return last, first

def normalize_name_for_fec(canonical_name):
    """Returns (fec_query_str, last_norm, first_norm)."""
    last, first = _parse_name(canonical_name)
    query = f"{last.upper()}, {first.upper()}" if first else last.upper()
    return query, last, first

def parse_fec_name(fec_name):
    """Parse FEC response contributor_name → (last, first)."""
    # FEC format: "LAST, FIRST MIDDLE" all caps
    last, first = _parse_name(fec_name)
    return last, first


# ── FEC API calls ──────────────────────────────────────────────────────────────
# Key rotation state: track which key is active and when each was last 429'd
_key_index = 0
_key_cooldown = {}   # key -> timestamp when it's safe to use again

def _active_key():
    """Return the first key not currently in cooldown, rotating as needed."""
    global _key_index
    now = time.time()
    for _ in range(len(FEC_API_KEYS)):
        key = FEC_API_KEYS[_key_index % len(FEC_API_KEYS)]
        if now >= _key_cooldown.get(key, 0):
            return key
        _key_index += 1
    # All keys in cooldown — wait for the soonest one
    soonest_key = min(FEC_API_KEYS, key=lambda k: _key_cooldown.get(k, 0))
    wait = _key_cooldown[soonest_key] - now
    print(f"  [all keys cooling] waiting {wait:.0f}s ...", flush=True)
    time.sleep(wait + 1)
    return soonest_key

def api_get(session, url, params, rate_limiter, max_retries=8):
    global _key_index
    for attempt in range(max_retries):
        rate_limiter.wait()
        key = _active_key()
        params["api_key"] = key
        try:
            resp = session.get(url, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            _key_cooldown[key] = time.time() + retry_after + 5
            _key_index += 1   # try next key immediately
            print(f"  [429 key#{FEC_API_KEYS.index(key)+1}] rotating — cooldown {retry_after+5}s", flush=True)
        elif resp.status_code in (500, 503):
            time.sleep(min(2 ** attempt, 64))
        elif resp.status_code == 404:
            return None
        else:
            resp.raise_for_status()

    raise RuntimeError(f"Max retries exceeded for {url}")


def query_fec_schedule_a(session, name_query, local_zip, rate_limiter):
    """
    Return list of all matching FEC contribution rows for this donor.
    Adds zip filter if result count is large.
    """
    base_params = {
        "api_key":           _active_key(),
        "contributor_name":  name_query,
        "contributor_state": "TX",
        "per_page":          100,
        "sort":              "-contribution_receipt_date",
    }

    # First page — check if result set is too large
    data = api_get(session, f"{FEC_BASE}/schedules/schedule_a/", base_params, rate_limiter)
    if data is None:
        return []

    total_count = data.get("pagination", {}).get("count", 0)
    if total_count > LARGE_SET_THRESHOLD and local_zip:
        # Narrow by zip
        base_params["contributor_zip"] = local_zip[:5]
        data = api_get(session, f"{FEC_BASE}/schedules/schedule_a/", base_params, rate_limiter)
        if data is None:
            return []

    all_results = list(data.get("results", []))
    last_indexes = data.get("pagination", {}).get("last_indexes", {})

    # Paginate
    while last_indexes and len(data.get("results", [])) == 100:
        page_params = dict(base_params)
        page_params["last_index"] = last_indexes.get("last_index")
        page_params["last_contribution_receipt_date"] = last_indexes.get("last_contribution_receipt_date")
        data = api_get(session, f"{FEC_BASE}/schedules/schedule_a/", page_params, rate_limiter)
        if data is None:
            break
        all_results.extend(data.get("results", []))
        last_indexes = data.get("pagination", {}).get("last_indexes", {})

    return all_results


# ── Identity confirmation ──────────────────────────────────────────────────────
def confirm_match(local_last, local_first, local_zip, fec_row):
    """
    Return (bool, score) — whether this FEC row plausibly belongs to the local donor.
    """
    fec_last, fec_first = parse_fec_name(fec_row.get("contributor_name", ""))
    fec_city = re.sub(r"[^a-z]", "", (fec_row.get("contributor_city") or "").lower())
    fec_zip  = (fec_row.get("contributor_zip") or "")[:5]

    # Name scores
    last_score  = fuzz.token_sort_ratio(local_last,  fec_last)  if local_last  else 0
    first_score = fuzz.token_sort_ratio(local_first, fec_first) if local_first else 0

    # ZIP score (exact)
    zip_score = 100 if (local_zip and fec_zip and local_zip[:5] == fec_zip) else 0

    # Composite
    if local_first:
        composite = (0.45 * last_score + 0.30 * first_score +
                     0.15 * 100 +        # we already filtered by state=TX
                     0.10 * zip_score)
    else:
        composite = 0.70 * last_score + 0.30 * zip_score

    return composite >= MATCH_THRESHOLD, composite


# ── Committee classification ───────────────────────────────────────────────────
class CommitteeCache:
    def __init__(self, conn, session, rate_limiter):
        self.conn = conn
        self.session = session
        self.rl = rate_limiter
        self._mem = {}   # in-memory for this run

        # Pre-load from DB
        cur = conn.cursor()
        cur.execute("SELECT committee_id, classification FROM fec_committee_cache")
        for cid, cls in cur.fetchall():
            self._mem[cid] = cls

    def get(self, committee_id):
        if committee_id in self._mem:
            return self._mem[committee_id]
        cls = self._fetch(committee_id)
        self._mem[committee_id] = cls
        return cls

    def _fetch(self, committee_id):
        # Correct endpoint: singular /committee/{id}/, response is results[0]
        url = f"{FEC_BASE}/committee/{committee_id}/"
        params = {"api_key": _active_key()}
        data = api_get(self.session, url, params, self.rl)

        if data is None:
            classification = "Other"
            party_code = ""
            ctype = ""
            name = committee_id
        else:
            results = data.get("results", [])
            result = results[0] if results else {}
            party_code = (result.get("party") or "").upper()
            ctype      = (result.get("committee_type") or "").upper()
            name       = result.get("name", committee_id)

            if party_code in ("DEM", "D"):
                classification = "Dem"
            elif party_code in ("REP", "R"):
                classification = "Rep"
            elif DEM_PATTERNS.search(name):
                classification = "Dem"
            elif REP_PATTERNS.search(name):
                classification = "Rep"
            else:
                classification = "Other"

        # Cache in DB
        self.conn.execute("""
            INSERT OR REPLACE INTO fec_committee_cache
            (committee_id, party_code, committee_type, committee_name, classification, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (committee_id, party_code, ctype, name, classification,
              datetime.now(timezone.utc).isoformat()))
        self.conn.commit()
        return classification


# ── FEC employer → industry resolution ────────────────────────────────────────
# Employer strings FEC donors write that mean "no employer"
FEC_NOISE_EMPLOYERS = {
    '', 'NONE', 'N/A', 'NA', 'NOT EMPLOYED', 'NOT APPLICABLE', 'RETIRED',
    'SELF-EMPLOYED', 'SELF EMPLOYED', 'SELFEMPLOYED', 'HOMEMAKER', 'UNEMPLOYED',
    'DISABLED', 'STUDENT', 'INFORMATION REQUESTED', 'REQUESTED',
}

def resolve_from_fec_employers(conn):
    """
    For each unresolved donor_id that has confirmed FEC records with a real
    employer string, try to match that employer against employer_identities
    and apply the industry to donor_identities.

    Resolution priority:
      1. Exact canonical_name match in employer_identities (normalized)
      2. Case-insensitive substring match (employer_identities name inside FEC string)
    Applied only when the match yields a non-noise industry.
    Confidence tag: 'fec-employer'
    """
    cur = conn.cursor()

    # Load all employer_identities that have a real industry
    NOISE_IND = {'Not Employed', 'Self-Employed', 'Student', 'Unknown',
                 'Unknown / Unclassified', None}
    cur.execute("""
        SELECT employer_id, canonical_name, industry
        FROM employer_identities
        WHERE industry IS NOT NULL AND industry NOT IN
              ('Not Employed','Self-Employed','Student','Unknown','Unknown / Unclassified')
    """)
    known_employers = cur.fetchall()  # (employer_id, canonical_name, industry)
    # Index: normalized name -> (employer_id, industry)
    emp_index = {row[1].upper().strip(): (row[0], row[2]) for row in known_employers}

    # Noise employer strings that should never resolve — expanded set covers
    # short tokens ("SELF") that would otherwise match as substrings of real names
    FEC_EMP_NOISE = {
        '', 'NONE', 'N/A', 'NA', 'NOT EMPLOYED', 'NOT APPLICABLE', 'NOT PROVIDED',
        'INFORMATION REQUESTED', 'REQUESTED', 'REFUSED', 'UNKNOWN',
        'RETIRED', 'SELF', 'SELF EMPLOYED', 'SELF-EMPLOYED', 'SELFEMPLOYED',
        'HOMEMAKER', 'HOME MAKER', 'HOUSEWIFE', 'HOUSEHUSBAND',
        'UNEMPLOYED', 'DISABLED', 'STUDENT', 'VOLUNTEER',
        'RANCHER', 'FARMER', 'INVESTOR',  # too vague for employer lookup
    }

    # Find unresolved donor_ids with FEC employer data
    # Build placeholders dynamically so the noise set is applied in SQL
    noise_placeholders = ','.join('?' * len(FEC_EMP_NOISE))
    cur.execute(f"""
        SELECT fcr.donor_id, fcr.fec_employer, fcr.fec_occupation,
               SUM(fcr.contribution_amount) as total
        FROM fec_contributions_raw fcr
        JOIN donor_identities di ON fcr.donor_id = di.donor_id
        WHERE di.resolved_industry IS NULL
          AND fcr.fec_employer IS NOT NULL
          AND LENGTH(TRIM(fcr.fec_employer)) >= 4
          AND UPPER(TRIM(fcr.fec_employer)) NOT IN ({noise_placeholders})
        GROUP BY fcr.donor_id, fcr.fec_employer
        ORDER BY fcr.donor_id, total DESC
    """, list(FEC_EMP_NOISE))
    rows = cur.fetchall()

    # For each donor_id, keep the highest-total real employer
    best_emp = {}  # donor_id -> (fec_employer, fec_occupation, total)
    for donor_id, emp, occ, total in rows:
        emp_upper = emp.upper().strip()
        if emp_upper not in FEC_EMP_NOISE and donor_id not in best_emp:
            best_emp[donor_id] = (emp, occ, total)

    print(f"\nFEC employer resolution pass: {len(best_emp)} unresolved donor_ids with real FEC employer")

    resolved = 0
    for donor_id, (fec_emp, fec_occ, total) in best_emp.items():
        emp_upper = fec_emp.upper().strip()
        match_industry = None
        matched_emp_display = None

        # 1. Exact match against normalized employer_identities canonical_name
        if emp_upper in emp_index:
            _, match_industry = emp_index[emp_upper]
            matched_emp_display = fec_emp.title()

        # 2. One-directional substring: known canonical name appears INSIDE the FEC string
        #    (not the reverse — prevents short noise tokens matching long real names)
        if not match_industry:
            for canonical_upper, (eid, ind) in emp_index.items():
                # Require the known name to be at least 6 chars to avoid spurious matches
                if len(canonical_upper) >= 6 and canonical_upper in emp_upper:
                    match_industry = ind
                    matched_emp_display = fec_emp.title()
                    break

        if match_industry:
            cur.execute("""
                UPDATE donor_identities
                SET resolved_industry = ?,
                    resolved_employer_display = ?,
                    resolved_confidence = 'fec-employer'
                WHERE donor_id = ? AND resolved_industry IS NULL
            """, (match_industry, matched_emp_display, donor_id))
            if cur.rowcount:
                resolved += 1

    conn.commit()
    print(f"  Resolved {resolved} donor_ids via FEC employer data")
    return resolved


# ── Main pipeline ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--limit",    type=int, default=TOP_N)
    parser.add_argument("--reset",    action="store_true", help="Re-process already-matched donors")
    args = parser.parse_args()

    conn = sqlite3.connect(DB, timeout=120)  # wait up to 2 min for locks to clear
    conn.execute("PRAGMA journal_mode=WAL")   # allow concurrent readers
    conn.row_factory = sqlite3.Row
    setup_db(conn)

    if args.reset:
        conn.execute("UPDATE donor_identities SET fec_matched = 0")
        conn.commit()
        print("Reset all fec_matched flags.")

    # Load top donors by total donated
    where = "fec_matched = 0 OR fec_matched IS NULL"
    cur = conn.cursor()
    cur.execute(f"""
        SELECT donor_id, canonical_name, canonical_zip
        FROM donor_identities
        WHERE {where}
        ORDER BY total_donated DESC
        LIMIT ?
    """, (args.limit,))
    donors = [dict(row) for row in cur.fetchall()]
    print(f"Processing {len(donors)} donors (dry_run={args.dry_run})")

    session = requests.Session()
    session.headers.update({"User-Agent": "Austin Finance Research / contact@example.com"})
    rate_limiter = RateLimiter(max_calls=1600, window_seconds=600)  # 2 keys × 800 calls/10min each
    committee_cache = CommitteeCache(conn, session, rate_limiter)

    stats = {"matched": 0, "no_history": 0, "ambiguous": 0, "api_errors": 0}

    for i, donor in enumerate(donors, 1):
        donor_id  = donor["donor_id"]
        cname     = donor["canonical_name"]
        local_zip = (donor["canonical_zip"] or "")[:5]

        fec_query, local_last, local_first = normalize_name_for_fec(cname)
        if not local_last:
            # Can't query — mark as processed with no data
            if not args.dry_run:
                conn.execute("""
                    UPDATE donor_identities SET fec_matched=1, fec_matched_at=?
                    WHERE donor_id=?
                """, (datetime.now(timezone.utc).isoformat(), donor_id))
                conn.commit()
            continue

        if i % 50 == 0:
            print(f"  [{i}/{len(donors)}] Processing: {cname} ...", flush=True)

        try:
            raw_rows = query_fec_schedule_a(session, fec_query, local_zip, rate_limiter)
        except Exception as e:
            print(f"  [ERROR] {cname}: {e}", flush=True)
            stats["api_errors"] += 1
            continue

        if not raw_rows:
            stats["no_history"] += 1
            if not args.dry_run:
                conn.execute("""
                    UPDATE donor_identities SET fec_matched=1, fec_total_donations=0,
                    fec_matched_at=? WHERE donor_id=?
                """, (datetime.now(timezone.utc).isoformat(), donor_id))
                conn.commit()
            continue

        # Confirm matches
        confirmed = []
        for row in raw_rows:
            ok, score = confirm_match(local_last, local_first, local_zip, row)
            if ok:
                confirmed.append((row, score))

        if not confirmed:
            stats["no_history"] += 1
            if not args.dry_run:
                conn.execute("""
                    UPDATE donor_identities SET fec_matched=1, fec_total_donations=0,
                    fec_matched_at=? WHERE donor_id=?
                """, (datetime.now(timezone.utc).isoformat(), donor_id))
                conn.commit()
            continue

        # Classify committees and aggregate
        dem_total = rep_total = other_total = 0.0
        raw_inserts = []

        for row, score in confirmed:
            committee_id = row.get("committee_id", "")
            amount       = row.get("contribution_receipt_amount") or 0.0
            if amount <= 0:
                continue   # skip refunds for now

            if committee_id:
                classification = committee_cache.get(committee_id)
            else:
                classification = "Other"

            if classification == "Dem":
                dem_total += amount
            elif classification == "Rep":
                rep_total += amount
            else:
                other_total += amount

            raw_inserts.append((
                donor_id, committee_id, amount,
                row.get("contribution_receipt_date"),
                row.get("contributor_name"),
                row.get("contributor_city"),
                row.get("contributor_zip"),
                (row.get("contributor_employer") or "").strip() or None,
                (row.get("contributor_occupation") or "").strip() or None,
                row.get("sub_id"),
                score
            ))

        total_count = len(raw_inserts)
        if dem_total + rep_total > 0:
            lean = dem_total / (dem_total + rep_total)
        else:
            lean = None

        if args.dry_run:
            lean_str = f"{lean:.2f}" if lean is not None else "None (no D/R donations)"
            print(f"  {cname}: D=${dem_total:,.0f}  R=${rep_total:,.0f}  "
                  f"O=${other_total:,.0f}  lean={lean_str}")
        else:
            conn.executemany("""
                INSERT OR REPLACE INTO fec_contributions_raw
                (donor_id, committee_id, contribution_amount, contribution_date,
                 fec_contributor_name, fec_contributor_city, fec_contributor_zip,
                 fec_employer, fec_occupation, fec_sub_id, confirm_score)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, raw_inserts)
            conn.execute("""
                UPDATE donor_identities
                SET fec_partisan_lean=?, fec_total_dem=?, fec_total_rep=?,
                    fec_total_other=?, fec_total_donations=?,
                    fec_matched=1, fec_matched_at=?
                WHERE donor_id=?
            """, (lean, dem_total, rep_total, other_total, total_count,
                  datetime.now(timezone.utc).isoformat(), donor_id))
            conn.commit()

        stats["matched"] += 1

    print(f"\nDone. matched={stats['matched']}  no_history={stats['no_history']}  "
          f"errors={stats['api_errors']}")

    if not args.dry_run:
        resolve_from_fec_employers(conn)

    if not args.dry_run:
        cur.execute("""
            SELECT
              COUNT(*) FILTER (WHERE fec_matched=1) as processed,
              COUNT(*) FILTER (WHERE fec_partisan_lean IS NOT NULL) as has_lean,
              COUNT(*) FILTER (WHERE fec_partisan_lean >= 0.6) as dem_leaning,
              COUNT(*) FILTER (WHERE fec_partisan_lean <= 0.4) as rep_leaning
            FROM donor_identities
        """)
        row = cur.fetchone()
        print(f"\nDB summary:")
        print(f"  Processed: {row[0]:,}")
        print(f"  Has FEC lean: {row[1]:,}")
        print(f"  Dem-leaning (>=0.6): {row[2]:,}")
        print(f"  Rep-leaning (<=0.4): {row[3]:,}")

    conn.close()


if __name__ == "__main__":
    main()
