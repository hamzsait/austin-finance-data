"""
Texas Ethics Commission (TEC) Campaign Finance Scraper
=======================================================

Prototype ingestor for Texas state-level campaign finance data into the
existing austin_finance.db. Phase-1 scope: download the TEC bulk CSV archive,
parse one contributions shard, load a sample into new tables, and demonstrate
cross-referencing Austin city donors against Texas state donors.

Data source:
    https://prd.tecprd.ethicsefile.com/public/cf/public/TEC_CF_CSV.zip
    (~1 GB zipped, ~8.3 GB uncompressed, 99 contrib shards,
     historical back to 2000-07-01)

Schema docs: CFS-ReadMe.txt inside the zip.
No API key. No rate limits. Public domain.
"""

from __future__ import annotations

import csv
import os
import sqlite3
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT          = Path(r"C:\Users\Hamza Sait\Electoral\austin-finance-data")
DB_PATH       = ROOT / "austin_finance.db"
TEC_DIR       = ROOT / "tec_data"
ZIP_PATH      = TEC_DIR / "TEC_CF_CSV.zip"
BULK_URL      = "https://prd.tecprd.ethicsefile.com/public/cf/public/TEC_CF_CSV.zip"

# Hand-curated filer IDs for high-value target PACs (found via filers.csv).
# filerTypeCd meaning: GPAC=General-Purpose PAC, SPAC=Specific-Purpose PAC,
#                      MPAC=Modified-filing PAC, DCE=Direct Campaign Expend.,
#                      COH=Candidate/Office-Holder
TARGET_COMMITTEES = {
    "00070864": "Texas Oil and Gas Association Good Government Committee (TXOGA)",
    "00028135": "Texans for Lawsuit Reform PAC",
    "00015555": "Associated Republicans of Texas Campaign Fund",
    "00089881": "Defend Texas Liberty",
    "00061927": "Empower Texans PAC (terminated)",
    "00015666": "Texas Trial Lawyers Association PAC",
    "00015487": "Texas REALTORS Political Action Committee (TREPAC)",
    "00017303": "Texas Apartment Association PAC",
    "00015700": "GHBA HOME-PAC",
    "00035370": "Austin Board of REALTORS Political Action Committee",
}

# Schemas not yet located in bulk file (may be federal-only or unregistered):
#   Texas Alliance of Energy Producers PAC
#   Permian Basin Petroleum Association PAC
#   Texans for Vehicle Choice
# TODO: recheck against cover.csv filerName variations, or use FEC fallback.


# ---------------------------------------------------------------------------
# Step 1: Download
# ---------------------------------------------------------------------------

def download_bulk_zip(force: bool = False) -> Path:
    TEC_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists() and not force:
        size_mb = ZIP_PATH.stat().st_size / 1024 / 1024
        print(f"[download] already have {ZIP_PATH.name} ({size_mb:.0f} MB) -- skip")
        return ZIP_PATH

    print(f"[download] GET {BULK_URL}")
    req = urllib.request.Request(BULK_URL, headers={"User-Agent": "austin-finance-research/0.1"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r, open(ZIP_PATH, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        read = 0
        next_mark = 100 * 1024 * 1024
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            read += len(chunk)
            if read >= next_mark:
                pct = (read / total * 100) if total else 0
                print(f"  {read/1024/1024:>5.0f} MB / {total/1024/1024:>5.0f} MB  {pct:5.1f}%")
                next_mark += 100 * 1024 * 1024
    print(f"[download] done in {time.time()-t0:.0f}s")
    return ZIP_PATH


# ---------------------------------------------------------------------------
# Step 2: Schema
# ---------------------------------------------------------------------------

TEC_CONTRIB_COLUMNS = [
    "recordType", "formTypeCd", "schedFormTypeCd", "reportInfoIdent",
    "receivedDt", "infoOnlyFlag", "filerIdent", "filerTypeCd", "filerName",
    "contributionInfoId", "contributionDt", "contributionAmount",
    "contributionDescr", "itemizeFlag", "travelFlag",
    "contributorPersentTypeCd", "contributorNameOrganization",
    "contributorNameLast", "contributorNameSuffixCd", "contributorNameFirst",
    "contributorNamePrefixCd", "contributorNameShort",
    "contributorStreetCity", "contributorStreetStateCd",
    "contributorStreetCountyCd", "contributorStreetCountryCd",
    "contributorStreetPostalCode", "contributorStreetRegion",
    "contributorEmployer", "contributorOccupation", "contributorJobTitle",
    "contributorPacFein", "contributorOosPacFlag",
    "contributorLawFirmName", "contributorSpouseLawFirmName",
    "contributorParent1LawFirmName", "contributorParent2LawFirmName",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create Texas tables. Non-destructive; existing schema untouched."""
    cur = conn.cursor()

    # Committee / filer dimension (analogous to fec_committee_cache).
    cur.execute("""
    CREATE TABLE IF NOT EXISTS texas_committees (
        filer_ident        TEXT PRIMARY KEY,      -- TEC filerIdent
        filer_type_cd      TEXT,                  -- GPAC/SPAC/MPAC/COH/DCE/...
        filer_name         TEXT,
        committee_status   TEXT,
        committee_class    TEXT,                  -- our tag: target/office_holder/other
        fetched_at         TEXT
    )
    """)

    # Raw contributions (analogous to fec_contributions_raw).
    cur.execute("""
    CREATE TABLE IF NOT EXISTS texas_contributions_raw (
        id                       INTEGER PRIMARY KEY AUTOINCREMENT,
        contribution_info_id     TEXT UNIQUE,     -- TEC contributionInfoId
        report_info_ident        TEXT,
        received_dt              TEXT,
        filer_ident              TEXT NOT NULL,   -- recipient committee/COH
        filer_type_cd            TEXT,
        filer_name               TEXT,
        contribution_dt          TEXT,            -- YYYYMMDD string, kept raw
        contribution_amount      REAL,
        contribution_descr       TEXT,
        itemize_flag             TEXT,
        -- contributor (the donor)
        contributor_type         TEXT,            -- INDIVIDUAL / ENTITY
        contributor_org          TEXT,
        contributor_last         TEXT,
        contributor_first        TEXT,
        contributor_suffix       TEXT,
        contributor_city         TEXT,
        contributor_state        TEXT,
        contributor_zip          TEXT,
        contributor_country      TEXT,
        contributor_employer     TEXT,
        contributor_occupation   TEXT,
        contributor_pac_fein     TEXT,
        oos_pac_flag             TEXT,
        -- normalized match key for cross-reference with donor_identities
        canonical_name           TEXT,            -- 'Last, First' (matches Austin format)
        canonical_zip5           TEXT,
        austin_donor_id          TEXT,            -- FK into donor_identities.donor_id
        match_confidence         TEXT,
        source                   TEXT DEFAULT 'texas_state',
        ingested_at              TEXT DEFAULT (datetime('now'))
    )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_contrib_filer ON texas_contributions_raw(filer_ident)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_contrib_canon ON texas_contributions_raw(canonical_name, canonical_zip5)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_contrib_austin ON texas_contributions_raw(austin_donor_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_contrib_date ON texas_contributions_raw(contribution_dt)")

    conn.commit()


# ---------------------------------------------------------------------------
# Step 3: Parse / load
# ---------------------------------------------------------------------------

def _canonical_name(row: dict) -> str | None:
    """Build 'Last, First' matching Austin donor_identities.canonical_name."""
    if (row.get("contributorPersentTypeCd") or "").upper() != "INDIVIDUAL":
        return None
    last = (row.get("contributorNameLast") or "").strip()
    first = (row.get("contributorNameFirst") or "").strip()
    if not last:
        return None
    return f"{last}, {first}".strip(", ").strip()


def _zip5(raw: str | None) -> str | None:
    if not raw:
        return None
    s = "".join(ch for ch in raw if ch.isdigit())
    return s[:5] if len(s) >= 5 else (s or None)


def load_target_committees(conn: sqlite3.Connection) -> None:
    """Seed texas_committees with the hand-curated target list."""
    cur = conn.cursor()
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    for fid, name in TARGET_COMMITTEES.items():
        cur.execute("""
            INSERT INTO texas_committees(filer_ident, filer_name, committee_class, fetched_at)
            VALUES (?, ?, 'target', ?)
            ON CONFLICT(filer_ident) DO UPDATE SET
                filer_name=excluded.filer_name,
                committee_class='target',
                fetched_at=excluded.fetched_at
        """, (fid, name, now))
    conn.commit()


def ingest_contrib_shard(
    conn: sqlite3.Connection,
    shard_member: str = "contribs_99.csv",
    only_target_committees: bool = True,
    limit: int | None = None,
) -> tuple[int, int]:
    """Read one contribs_##.csv out of the zip and insert into raw table.

    Returns (rows_scanned, rows_inserted).
    """
    shard_path = TEC_DIR / shard_member
    if not shard_path.exists():
        print(f"[ingest] extracting {shard_member} from zip")
        with zipfile.ZipFile(ZIP_PATH) as z:
            z.extract(shard_member, TEC_DIR)

    targets = set(TARGET_COMMITTEES.keys())
    cur = conn.cursor()

    inserted = 0
    skipped_dupe = 0
    scanned = 0
    start_changes = conn.total_changes
    batch: list[tuple] = []
    BATCH = 2000

    sql = """
        INSERT OR IGNORE INTO texas_contributions_raw (
            contribution_info_id, report_info_ident, received_dt,
            filer_ident, filer_type_cd, filer_name,
            contribution_dt, contribution_amount, contribution_descr, itemize_flag,
            contributor_type, contributor_org,
            contributor_last, contributor_first, contributor_suffix,
            contributor_city, contributor_state, contributor_zip, contributor_country,
            contributor_employer, contributor_occupation,
            contributor_pac_fein, oos_pac_flag,
            canonical_name, canonical_zip5
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    with open(shard_path, encoding="utf-8", errors="replace", newline="") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            scanned += 1
            if only_target_committees and row.get("filerIdent") not in targets:
                continue
            try:
                amt = float(row.get("contributionAmount") or 0)
            except ValueError:
                amt = 0.0
            canon = _canonical_name(row)
            zip5 = _zip5(row.get("contributorStreetPostalCode"))
            batch.append((
                row.get("contributionInfoId"),
                row.get("reportInfoIdent"),
                row.get("receivedDt"),
                row.get("filerIdent"),
                row.get("filerTypeCd"),
                row.get("filerName"),
                row.get("contributionDt"),
                amt,
                row.get("contributionDescr"),
                row.get("itemizeFlag"),
                row.get("contributorPersentTypeCd"),
                row.get("contributorNameOrganization"),
                row.get("contributorNameLast"),
                row.get("contributorNameFirst"),
                row.get("contributorNameSuffixCd"),
                row.get("contributorStreetCity"),
                row.get("contributorStreetStateCd"),
                row.get("contributorStreetPostalCode"),
                row.get("contributorStreetCountryCd"),
                row.get("contributorEmployer"),
                row.get("contributorOccupation"),
                row.get("contributorPacFein"),
                row.get("contributorOosPacFlag"),
                canon,
                zip5,
            ))
            if len(batch) >= BATCH:
                before = conn.total_changes
                cur.executemany(sql, batch)
                inserted += conn.total_changes - before
                batch.clear()
                conn.commit()
            if limit and scanned >= limit:
                break

    if batch:
        before = conn.total_changes
        cur.executemany(sql, batch)
        inserted += conn.total_changes - before
        conn.commit()

    # Note: with INSERT OR IGNORE, rows skipped on the conflict path don't
    # bump total_changes, so `inserted` reflects new rows only.
    return scanned, inserted


# ---------------------------------------------------------------------------
# Step 4: Cross-reference with Austin donors
# ---------------------------------------------------------------------------

def link_to_austin_donors(conn: sqlite3.Connection) -> int:
    """Match texas_contributions_raw rows to donor_identities via
    (canonical_name, canonical_zip5). Done in Python with an in-memory dict
    because donor_identities has no secondary index and correlated subqueries
    are O(N*M) slow on 150k+ rows."""
    cur = conn.cursor()

    print("[link] loading donor_identities into memory...")
    t0 = time.time()
    by_name_zip: dict[tuple[str, str], str] = {}
    by_name: dict[str, list[str]] = {}
    for donor_id, name, zipc in cur.execute(
        "SELECT donor_id, canonical_name, canonical_zip FROM donor_identities"
    ):
        if not name:
            continue
        name_n = name.strip()
        if zipc:
            by_name_zip[(name_n, zipc.strip())] = donor_id
        by_name.setdefault(name_n, []).append(donor_id)
    print(f"[link]   {len(by_name):,} distinct names, {len(by_name_zip):,} name+zip keys "
          f"in {time.time()-t0:.1f}s")

    # Walk texas rows and resolve.
    exact = 0
    name_only = 0
    updates: list[tuple[str, str, int]] = []
    for rid, cname, czip in cur.execute(
        "SELECT id, canonical_name, canonical_zip5 FROM texas_contributions_raw "
        "WHERE canonical_name IS NOT NULL AND austin_donor_id IS NULL"
    ):
        hit = by_name_zip.get((cname, czip)) if czip else None
        if hit:
            updates.append((hit, "name+zip5", rid))
            exact += 1
            continue
        candidates = by_name.get(cname)
        if candidates and len(candidates) == 1:
            updates.append((candidates[0], "name_only", rid))
            name_only += 1

    print(f"[link] applying {len(updates):,} matches...")
    cur.executemany(
        "UPDATE texas_contributions_raw "
        "   SET austin_donor_id = ?, match_confidence = ? "
        " WHERE id = ?",
        updates,
    )
    conn.commit()

    print(f"[link] exact name+zip5 matches: {exact}")
    print(f"[link] unique-name fallback matches: {name_only}")
    return exact + name_only


# ---------------------------------------------------------------------------
# Step 5: Reports
# ---------------------------------------------------------------------------

def report(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    print("\n=== Texas committees ingested ===")
    for r in cur.execute("""
        SELECT t.filer_ident, t.filer_name,
               COUNT(r.id) AS rows,
               ROUND(SUM(r.contribution_amount),2) AS total,
               MIN(r.contribution_dt), MAX(r.contribution_dt)
          FROM texas_committees t
          LEFT JOIN texas_contributions_raw r ON r.filer_ident = t.filer_ident
         GROUP BY t.filer_ident
         ORDER BY total DESC NULLS LAST
    """):
        print("  ", r)

    print("\n=== Top 10 donors to target committees in this shard ===")
    for r in cur.execute("""
        SELECT canonical_name, contributor_city, contributor_zip,
               COUNT(*) AS n, ROUND(SUM(contribution_amount),2) AS total
          FROM texas_contributions_raw
         WHERE canonical_name IS NOT NULL
         GROUP BY canonical_name, contributor_zip
         ORDER BY total DESC
         LIMIT 10
    """):
        print("  ", r)

    print("\n=== CROSS-REFERENCE: Austin city donors who also gave to Texas state PACs ===")
    cur.execute("""
        SELECT COUNT(DISTINCT austin_donor_id)
          FROM texas_contributions_raw
         WHERE austin_donor_id IS NOT NULL
    """)
    n_cross = cur.fetchone()[0]
    print(f"  Distinct Austin donors with Texas state activity: {n_cross}")

    print("\n  Top 15 overlapping donors (Austin total vs Texas-in-shard):")
    for r in cur.execute("""
        SELECT di.canonical_name, di.canonical_zip,
               ROUND(di.total_donated,2)              AS austin_total,
               ROUND(SUM(tx.contribution_amount),2)   AS texas_total_in_shard,
               COUNT(tx.id)                           AS texas_rows,
               GROUP_CONCAT(DISTINCT tx.filer_name)   AS texas_committees
          FROM donor_identities di
          JOIN texas_contributions_raw tx ON tx.austin_donor_id = di.donor_id
         GROUP BY di.donor_id
         ORDER BY (di.total_donated + SUM(tx.contribution_amount)) DESC
         LIMIT 15
    """):
        print("  ", r)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"db: {DB_PATH}")
    download_bulk_zip()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    ensure_schema(conn)
    load_target_committees(conn)

    # Prototype: process a single shard.
    # contribs_99.csv is the newest shard (recent activity) per TEC ordering;
    # change to contribs_01..contribs_99 or a loop for full ingest.
    shard = os.environ.get("TEC_SHARD", "contribs_99.csv")
    print(f"\n[ingest] shard = {shard}  (target committees only)")
    t0 = time.time()
    scanned, inserted = ingest_contrib_shard(conn, shard, only_target_committees=True)
    print(f"[ingest] scanned {scanned:,} rows, inserted {inserted:,} in {time.time()-t0:.1f}s")

    link_to_austin_donors(conn)
    report(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# RESEARCH REPORT & PIPELINE SCOPE
# ---------------------------------------------------------------------------
#
# Phase 1 - Data availability
# ---------------------------
# * TEC publishes a single consolidated bulk ZIP:
#     https://prd.tecprd.ethicsefile.com/public/cf/public/TEC_CF_CSV.zip
#   reachable from https://www.ethics.state.tx.us/search/cf/ under
#   "Download Campaign Finance Reports Data". Regenerated nightly.
# * Size: ~966 MB zipped, ~8.27 GB uncompressed, 135 files.
# * Format: CSV, header row included, UTF-8, standard quoting.
# * Schema documented in CFS-ReadMe.txt (record layouts) and
#   CFS-Codes.txt (lookup code meanings) both inside the zip.
# * Historical coverage: electronically-filed reports from 2000-07-01
#   onward. Older reports (pre-2000) are paper-only.
# * No API key, no rate limit, public domain. Requires only a browser
#   User-Agent header to avoid a 403 from the CDN.
# * File layout:
#     - filers.csv           ~8.8 MB    filer/committee dimension (132 cols)
#     - spacs.csv            ~106 KB    specific-purpose committee index
#     - cover.csv            ~192 MB    cover sheet (report totals)
#     - contribs_01..99.csv  ~6.9 GB    RCPT records, sharded by hash of ID
#     - cont_ss.csv, cont_t.csv         semi-annual & terminal-report contribs
#     - expend_01..13.csv    ~1.1 GB    EXPN records (campaign expenditures)
#     - pledges/loans/debts/travel/assets/credits/purpose/notices/cand
#
# Phase 2 - Target committees located by filerIdent
# -------------------------------------------------
# FOUND (loaded into texas_committees):
#   00070864  Texas Oil and Gas Association Good Government Committee (TXOGA)
#   00028135  Texans for Lawsuit Reform PAC
#   00015555  Associated Republicans of Texas Campaign Fund
#   00089881  Defend Texas Liberty
#   00061927  Empower Texans PAC (terminated)
#   00015666  Texas Trial Lawyers Association PAC
#   00015487  Texas REALTORS PAC (this is TREPAC; TREPAC is the nickname)
#   00017303  Texas Apartment Association PAC
#   00015700  GHBA HOME-PAC (Greater Houston HBA HOME-PAC; Austin HBA
#             dissolved its HOMEPAC; filer 00015509 is terminated)
#   00035370  Austin Board of REALTORS PAC (bonus Austin-focused find)
#
# NOT FOUND in TEC bulk data - follow up required:
#   * Texas Alliance of Energy Producers PAC    -- likely registered federally
#   * Permian Basin Petroleum Association PAC   -- ditto
#   * Texans for Vehicle Choice                 -- name variant not matched
#   These may already be covered in fec_contributions_raw; cross-check via
#   FEC committee search before assuming absence.
#
# Phase 3 - Schema decision
# -------------------------
# Chose OPTION 1 (new tables) over adding source column to campaign_finance:
#   * campaign_finance already has 25 Austin-specific cols; polluting it
#     with TEC fields (36 cols) would bloat every Austin query.
#   * fec_contributions_raw pattern is the same separation and works.
#   * Cross-reference happens via donor_identities (the canonical person
#     dimension). We add austin_donor_id FK on texas_contributions_raw so
#     JOINs are trivial.
# New tables created (both guarded by IF NOT EXISTS):
#   texas_committees         dimension, seeded from TARGET_COMMITTEES
#   texas_contributions_raw  fact, includes canonical_name/zip5 for matching
#
# Phase 4 - Prototype results (contribs_99.csv only)
# --------------------------------------------------
# * Scanned 271,352 contribution rows, inserted 11,458 rows matching target
#   committees in ~2.2s.
# * Total across the 5 target committees present in this shard: $5,057,503
#     TREPAC                10,416 rows  $   678,117
#     TTLA PAC                 845 rows  $ 1,972,616
#     Texans for Lawsuit Reform 15 rows  $ 2,083,100  (includes 3 x $500k+)
#     Texas Apt Assn PAC       159 rows  $   278,635
#     GHBA HOME-PAC             23 rows  $    45,033
# * Donor linking to Austin donor_identities: 400 row matches -> 305 distinct
#   Austin donors (70 name+zip5, 330 unique-name-only). Done in Python with
#   an in-memory dict because donor_identities.canonical_name has no index.
# * Highest-overlap donors include trial lawyers (Stewart, Garcia, Harvey)
#   and TREPAC-donor realtors already active in Austin council races.
#
# Phase 5 - Full pipeline scope
# -----------------------------
# * Contribution rows total (projection from contribs_99 row density):
#     ~33.8 million rows across 101 contribution files
# * Expenditure rows: ~6-8 million (1.07 GB of expend_*.csv)
# * Full end-to-end ingest time estimate at current 123k rows/sec parse
#   + 40k rows/sec insert with indexes:
#     - Parse all contribs:            ~5 minutes
#     - Insert all (no filter):       ~15-20 minutes
#     - Index build:                    ~5 minutes
#     TOTAL: ~30-40 min for everything; ~3-5 min if we keep the
#     target-only filter and just sweep for the 10 committees.
# * Storage: raw contributions at ~150 bytes/row avg -> ~5 GB extra on
#   austin_finance.db. Running target-only keeps it under 100 MB.
# * Recommended strategy:
#     1. Loop all 101 contrib shards with only_target_committees=True to
#        capture full history of the 10 target PACs (~500k rows est.).
#     2. Expand TARGET_COMMITTEES over time as new interests are flagged.
#     3. For expenditures, ingest the same 10 filerIdents from expend_*.csv
#        to see WHICH candidates these PACs bankroll.
#     4. Join expend.candidate -> cand.csv -> filers.csv to resolve
#        recipient offices (statewide / lege / local).
#     5. Add a nightly refresh job that re-downloads the zip and re-ingests
#        only rows with receivedDt > last_run.
#
# Phase 6 - Known limitations / follow-ups
# ----------------------------------------
# * Name-only fallback can produce false matches for common names
#   ('Smith, John' with 1 Austin row will match any Texas 'Smith, John').
#   Mitigation: already restricting to names that are unique in Austin,
#   but consider adding city match as a tiebreaker.
# * donor_identities.canonical_zip is 5-digit while TEC is ZIP+4; our
#   _zip5() strips the extension so the exact-match path works.
# * In-kind contributions and pledges use separate record types (PLDG)
#   not yet ingested.
# * "Corrections" / amended reports: TEC uses infoOnlyFlag='Y' to mark
#   superseded rows. We currently keep all rows; for totals we should
#   filter infoOnlyFlag != 'Y'.
# * filerTypeCd 'COH' (candidate office-holder) contributions not targeted
#   yet, so we currently only see PAC receipts, not e.g. Governor Abbott's
#   direct contributions. Add his filerIdent to TARGET_COMMITTEES when
#   useful, or add an allow-by-type mode.
# * Texas Alliance of Energy Producers / Permian Basin Petroleum Assn PAC
#   not found - these are likely federal-only. Check FEC committee cache.
