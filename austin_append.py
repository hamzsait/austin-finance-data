"""Incrementally absorb new/amended City of Austin contributions from the
Socrata feed WITHOUT touching existing rows' enrichment.

The feed (3kfv-biw6) was re-scoped to 2022+ and is no longer a superset of our
DB — fetch_data.py's DROP+rebuild must never run again. This script:
  1. pages all feed rows with date_reported > our high-water mark (minus a
     30-day overlap window to catch late amendments),
  2. upserts by transaction_id: new ids -> INSERT (donor_id NULL for later
     resolution); changed rows -> UPDATE data columns, PRESERVING donor_id /
     employer_id / is_joint stamps,
  3. reports new recipients (possible new candidates) and row counts.

Usage: python austin_append.py [--dry-run] [--since YYYY-MM-DD]
"""
import argparse, json, sqlite3, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta

DB = "austin_finance.db"
API = "https://data.austintexas.gov/resource/3kfv-biw6.json"
PAGE = 5000

# columns we mirror from the feed (feed field name == column name)
DATA_COLS = ["donor", "recipient", "contribution_amount", "contribution_date",
             "donor_type", "city_state_zip", "contribution_year",
             "contribution_type", "date_reported", "report_filed",
             "view_report", "transaction_id", "donor_reported_occupation",
             "donor_reported_employer", "in_kind_description",
             "out_of_state_pac", "correction"]

def fetch_page(where, offset):
    q = urllib.parse.urlencode({
        "$where": where, "$order": "transaction_id", "$limit": PAGE, "$offset": offset})
    with urllib.request.urlopen(f"{API}?{q}", timeout=120) as r:
        return json.load(r)

def norm(rec):
    out = {}
    for c in DATA_COLS:
        v = rec.get(c, "")
        if isinstance(v, dict):  # view_report url object
            v = str(v)
        out[c] = str(v) if v is not None else ""
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--since", default=None)
    args = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=120)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if args.since:
        since = args.since
    else:
        hi = cur.execute("""SELECT MAX(date_reported) FROM campaign_finance
                            WHERE transaction_id NOT LIKE 'TRAVIS-%'""").fetchone()[0]
        since = (datetime.fromisoformat(hi.split("T")[0]) - timedelta(days=30)).strftime("%Y-%m-%d")
    where = f"date_reported > '{since}'"
    print(f"fetching feed rows where {where}")

    rows, offset = [], 0
    while True:
        page = fetch_page(where, offset)
        rows.extend(page)
        print(f"  fetched {len(rows)} rows...", flush=True)
        if len(page) < PAGE:
            break
        offset += PAGE
    print(f"feed rows in window: {len(rows)}")

    known = {r[0]: r[1] for r in cur.execute(
        """SELECT transaction_id, donor || '|' || contribution_amount || '|' ||
                  contribution_date || '|' || recipient
           FROM campaign_finance WHERE transaction_id NOT LIKE 'TRAVIS-%'""")}
    known_recipients = {r[0] for r in cur.execute(
        "SELECT DISTINCT recipient FROM campaign_finance")}

    inserts, updates, unchanged = [], [], 0
    new_recipients = {}
    for rec in rows:
        n = norm(rec)
        tid = n["transaction_id"]
        if not tid:
            continue
        sig = f"{n['donor']}|{n['contribution_amount']}|{n['contribution_date']}|{n['recipient']}"
        if tid not in known:
            inserts.append(n)
            if n["recipient"] not in known_recipients:
                new_recipients.setdefault(n["recipient"], 0)
                new_recipients[n["recipient"]] += float(n["contribution_amount"] or 0)
        elif known[tid] != sig:
            updates.append(n)
        else:
            unchanged += 1

    print(f"new: {len(inserts)}, amended: {len(updates)}, unchanged: {unchanged}")
    if new_recipients:
        print("NEW RECIPIENTS (possible new candidates):")
        for r, amt in sorted(new_recipients.items(), key=lambda x: -x[1]):
            print(f"  {r}: ${amt:,.0f}")

    if args.dry_run:
        print("DRY RUN — no writes")
        return

    cur.executemany(
        f"INSERT INTO campaign_finance ({','.join(DATA_COLS)}) VALUES ({','.join('?'*len(DATA_COLS))})",
        [tuple(n[c] for c in DATA_COLS) for n in inserts])
    set_clause = ", ".join(f"{c}=?" for c in DATA_COLS if c != "transaction_id")
    cur.executemany(
        f"UPDATE campaign_finance SET {set_clause} WHERE transaction_id=?",
        [tuple(n[c] for c in DATA_COLS if c != "transaction_id") + (n["transaction_id"],)
         for n in updates])
    conn.commit()
    print(f"committed. rows needing identity resolution: "
          f"{cur.execute('SELECT COUNT(*) FROM campaign_finance WHERE donor_id IS NULL AND employer_id IS NULL AND transaction_id NOT LIKE \"TRAVIS-%\" AND contribution_year >= \"2026\"').fetchone()[0]}")

if __name__ == "__main__":
    main()
