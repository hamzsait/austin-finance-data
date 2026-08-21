import requests
import sqlite3
import json
import time

API_URL = "https://data.austintexas.gov/resource/3kfv-biw6.json"
DB_PATH = "austin_finance.db"
BATCH_SIZE = 10000

def fetch_all_records():
    records = []
    offset = 0

    while True:
        params = {
            "$limit": BATCH_SIZE,
            "$offset": offset,
            "$order": ":id"
        }
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

def infer_columns(records):
    cols = {}
    for r in records:
        for k, v in r.items():
            if k not in cols:
                if isinstance(v, int):
                    cols[k] = "INTEGER"
                elif isinstance(v, float):
                    cols[k] = "REAL"
                else:
                    cols[k] = "TEXT"
    return cols

def store_to_db(records, db_path):
    if not records:
        print("No records to store.")
        return

    cols = infer_columns(records)
    col_defs = ", ".join(f'"{c}" {t}' for c, t in cols.items())

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(f'DROP TABLE IF EXISTS campaign_finance')
    cur.execute(f'CREATE TABLE campaign_finance ({col_defs})')

    col_names = list(cols.keys())
    placeholders = ", ".join("?" * len(col_names))
    quoted_cols = ", ".join(f'"{c}"' for c in col_names)
    insert_sql = f"INSERT INTO campaign_finance ({quoted_cols}) VALUES ({placeholders})"

    rows = [
        tuple(str(r.get(c, "")) if cols[c] == "TEXT" else r.get(c) for c in col_names)
        for r in records
    ]

    cur.executemany(insert_sql, rows)
    conn.commit()

    count = cur.execute("SELECT COUNT(*) FROM campaign_finance").fetchone()[0]
    print(f"\nStored {count} records in '{db_path}' -> table: campaign_finance")
    print(f"Columns ({len(col_names)}): {', '.join(col_names)}")

    conn.close()

if __name__ == "__main__":
    print("Fetching Austin campaign finance data...")
    records = fetch_all_records()
    print(f"\nTotal records fetched: {len(records)}")
    store_to_db(records, DB_PATH)
    print("Done.")
