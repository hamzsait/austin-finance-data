"""
Incremental fetch from the Austin City Clerk Socrata feed.

Replaces fetch_data.py for all routine refreshes. fetch_data.py is kept only as a
historical artifact and MUST NOT be run: it DROPs campaign_finance and rebuilds it
from the feed. That is now destructive on two counts —

  1. The feed was re-scoped to 2022+ (117,737 rows as of 2026-07-17) while the DB
     holds 240,686 rows going back to 2014. A rebuild silently discards all
     pre-2022 history, which the publisher no longer serves.
  2. campaign_finance carries 8 enrichment columns (donor_id, employer_id, ...)
     and 7,039 Travis County rows ingested from PDFs. Neither exists upstream.

This script is strictly additive:
  - INSERTs only transaction_ids not already present.
  - Never UPDATEs, DELETEs, or DROPs. Existing rows are untouched, including
    their enrichment columns.
  - Writes only the 17 feed-sourced columns; enrichment columns on new rows are
    left NULL for the downstream incremental resolvers to fill.
"""

import sqlite3
import time

import requests

API_URL = "https://data.austintexas.gov/resource/3kfv-biw6.json"
DB_PATH = "austin_finance.db"
BATCH_SIZE = 10000

# The 17 feed-sourced columns, in DB order. Deliberately explicit rather than
# inferred: inference is what let the old script silently drop the enrichment
# columns. Anything not in this list is never written by this script.
API_COLUMNS = [
    "donor",
    "recipient",
    "contribution_amount",
    "contribution_date",
    "donor_type",
    "city_state_zip",
    "contribution_year",
    "contribution_type",
    "date_reported",
    "report_filed",
    "view_report",
    "transaction_id",
    "donor_reported_occupation",
    "donor_reported_employer",
    "in_kind_description",
    "out_of_state_pac",
    "correction",
]


def fetch_all_records():
    records = []
    offset = 0

    while True:
        params = {"$limit": BATCH_SIZE, "$offset": offset, "$order": ":id"}
        resp = requests.get(API_URL, params=params, timeout=60)
        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            break

        records.extend(batch)
        print(f"  Fetched {len(records)} records so far...")

        if len(batch) < BATCH_SIZE:
            break

        offset += BATCH_SIZE
        time.sleep(0.2)

    return records


def to_cell(rec, col):
    """Serialize one feed value the way the existing 233,647 Socrata rows store it.

    view_report arrives as a dict; historical rows hold its Python repr, so we
    reproduce that rather than emit JSON and split the column into two formats.
    Absent sparse fields (in_kind_description, out_of_state_pac, correction) are
    stored as '' to match existing rows rather than NULL.
    """
    v = rec.get(col, "")
    return "" if v is None else str(v)


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    before_total = cur.execute("SELECT COUNT(*) FROM campaign_finance").fetchone()[0]
    before_pre2022 = cur.execute(
        "SELECT COUNT(*) FROM campaign_finance WHERE contribution_date < '2022-01-01'"
    ).fetchone()[0]
    before_travis = cur.execute(
        "SELECT COUNT(*) FROM campaign_finance WHERE transaction_id LIKE 'TRAVIS%'"
    ).fetchone()[0]
    before_donor_ids = cur.execute(
        "SELECT COUNT(DISTINCT donor_id) FROM campaign_finance WHERE donor_id IS NOT NULL"
    ).fetchone()[0]

    print("=== BASELINE ===")
    print(f"  campaign_finance rows:  {before_total:,}")
    print(f"  pre-2022 rows:          {before_pre2022:,}")
    print(f"  Travis County rows:     {before_travis:,}")
    print(f"  distinct donor_ids:     {before_donor_ids:,}")

    print("\nFetching Austin campaign finance data...")
    records = fetch_all_records()
    print(f"\nTotal records in feed: {len(records):,}")

    print("\nDiffing against existing transaction_ids...")
    existing = {
        t for (t,) in cur.execute("SELECT transaction_id FROM campaign_finance")
    }
    print(f"  {len(existing):,} transaction_ids already in DB")

    new_records = []
    seen = set()
    dupes_in_feed = 0
    missing_txn = 0

    for r in records:
        txn = r.get("transaction_id")
        if not txn:
            missing_txn += 1
            continue
        if txn in existing or txn in seen:
            if txn in seen:
                dupes_in_feed += 1
            continue
        seen.add(txn)
        new_records.append(r)

    print(f"  {len(new_records):,} genuinely new rows")
    if dupes_in_feed:
        print(f"  {dupes_in_feed:,} duplicate transaction_ids within the feed (skipped)")
    if missing_txn:
        print(f"  {missing_txn:,} feed rows with no transaction_id (skipped)")

    if not new_records:
        print("\nNothing to insert. DB unchanged.")
        conn.close()
        return

    quoted = ", ".join(f'"{c}"' for c in API_COLUMNS)
    placeholders = ", ".join("?" * len(API_COLUMNS))
    insert_sql = f"INSERT INTO campaign_finance ({quoted}) VALUES ({placeholders})"

    rows = [tuple(to_cell(r, c) for c in API_COLUMNS) for r in new_records]

    print(f"\nInserting {len(rows):,} rows (feed columns only)...")
    cur.executemany(insert_sql, rows)

    # Guard rails: any violation rolls the whole insert back.
    after_total = cur.execute("SELECT COUNT(*) FROM campaign_finance").fetchone()[0]
    after_pre2022 = cur.execute(
        "SELECT COUNT(*) FROM campaign_finance WHERE contribution_date < '2022-01-01'"
    ).fetchone()[0]
    after_travis = cur.execute(
        "SELECT COUNT(*) FROM campaign_finance WHERE transaction_id LIKE 'TRAVIS%'"
    ).fetchone()[0]
    after_donor_ids = cur.execute(
        "SELECT COUNT(DISTINCT donor_id) FROM campaign_finance WHERE donor_id IS NOT NULL"
    ).fetchone()[0]

    problems = []
    if after_total != before_total + len(rows):
        problems.append(
            f"row count {after_total:,} != expected {before_total + len(rows):,}"
        )
    if after_pre2022 != before_pre2022:
        problems.append(f"pre-2022 rows changed {before_pre2022:,} -> {after_pre2022:,}")
    if after_travis != before_travis:
        problems.append(f"Travis rows changed {before_travis:,} -> {after_travis:,}")
    if after_donor_ids < before_donor_ids:
        problems.append(
            f"distinct donor_ids shrank {before_donor_ids:,} -> {after_donor_ids:,}"
        )

    if problems:
        conn.rollback()
        print("\n!!! GUARD FAILED — rolled back, DB unchanged !!!")
        for p in problems:
            print(f"  - {p}")
        conn.close()
        raise SystemExit(1)

    conn.commit()

    print("\n=== DONE ===")
    print(f"  rows:               {before_total:,} -> {after_total:,}  (+{len(rows):,})")
    print(f"  pre-2022 rows:      {before_pre2022:,} (unchanged)")
    print(f"  Travis County rows: {before_travis:,} (unchanged)")
    print(f"  distinct donor_ids: {before_donor_ids:,} (unchanged; new rows have donor_id NULL)")
    print("\n  New rows carry NULL donor_id/employer_id — run the incremental")
    print("  identity resolvers next to attach them to existing identities.")

    # Counted from the inserted batch, not from `donor_id IS NULL` — plenty of
    # pre-existing rows (PACs, entities) legitimately carry a NULL donor_id.
    by_year = {}
    by_recipient = {}
    for r in new_records:
        y = r.get("contribution_year") or "(blank)"
        by_year[y] = by_year.get(y, 0) + 1
        rec = r.get("recipient") or "(blank)"
        by_recipient[rec] = by_recipient.get(rec, 0) + 1

    print("\n=== NEW ROWS BY YEAR ===")
    for y in sorted(by_year):
        print(f"  {y:<8} {by_year[y]:,}")

    print("\n=== NEW ROWS BY RECIPIENT (top 25) ===")
    for rec, n in sorted(by_recipient.items(), key=lambda kv: -kv[1])[:25]:
        print(f"  {n:>6,}  {rec}")

    dates = [r.get("contribution_date", "") for r in new_records if r.get("contribution_date")]
    reported = [r.get("date_reported", "") for r in new_records if r.get("date_reported")]
    if dates:
        print(f"\n  new contribution_date range: {min(dates)} .. {max(dates)}")
    if reported:
        print(f"  new date_reported range:     {min(reported)} .. {max(reported)}")

    with open("fetch_incremental_new_txns.txt", "w") as f:
        for r in new_records:
            f.write(r["transaction_id"] + "\n")
    print(f"\n  Wrote {len(new_records):,} new transaction_ids to fetch_incremental_new_txns.txt")
    print("  (downstream incremental steps key off this list)")

    conn.close()


if __name__ == "__main__":
    main()
