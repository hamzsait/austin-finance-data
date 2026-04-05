"""
fec_backfill_employers.py
=========================
Stages already-processed FEC donors for re-ingestion so their
fec_employer / fec_occupation / fec_sub_id columns get populated.

What it does:
  1. Finds donor_ids whose fec_contributions_raw rows are missing employer data
  2. Deletes those raw rows (they'll be re-inserted by fec_enrich.py)
  3. Resets fec_matched=0 for those donors so fec_enrich.py picks them up
  4. Preserves fec_partisan_lean / fec_total_dem / fec_total_rep in donor_identities
     (fec_enrich.py will overwrite with same values on re-run — safe)

After running this script, just run:
    python fec_enrich.py
(no --reset flag — it will only re-process the donors staged here)
"""
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("austin_finance.db", timeout=120)
conn.execute("PRAGMA journal_mode=WAL")
cur = conn.cursor()

# ── Apply schema upgrades if this is the first run after the column additions ──
for col_def in ["fec_employer TEXT", "fec_occupation TEXT", "fec_sub_id TEXT"]:
    try:
        conn.execute(f"ALTER TABLE fec_contributions_raw ADD COLUMN {col_def}")
        conn.commit()
    except Exception:
        pass

try:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fec_raw_sub ON fec_contributions_raw(fec_sub_id)")
    conn.commit()
except Exception:
    pass

# ── Find donors with NULL employer data in their raw rows ─────────────────────
cur.execute("""
    SELECT DISTINCT donor_id
    FROM fec_contributions_raw
    WHERE fec_employer IS NULL
""")
donor_ids = [r[0] for r in cur.fetchall()]
print(f"Donors with missing employer data in fec_contributions_raw: {len(donor_ids):,}")

if not donor_ids:
    print("Nothing to backfill.")
    conn.close()
    sys.exit(0)

# ── Snapshot their current lean scores so we can report what's preserved ──────
cur.execute(f"""
    SELECT COUNT(*), COUNT(fec_partisan_lean)
    FROM donor_identities
    WHERE donor_id IN ({','.join('?'*len(donor_ids))})
""", donor_ids)
total, has_lean = cur.fetchone()
print(f"  Of those: {total} donor_ids in donor_identities, {has_lean} have partisan lean scores (preserved)")

# ── Delete stale raw rows ──────────────────────────────────────────────────────
cur.execute(f"""
    DELETE FROM fec_contributions_raw
    WHERE donor_id IN ({','.join('?'*len(donor_ids))})
""", donor_ids)
deleted = cur.rowcount
print(f"  Deleted {deleted:,} stale rows from fec_contributions_raw")

# ── Reset fec_matched so fec_enrich.py will re-process these donors ───────────
cur.execute(f"""
    UPDATE donor_identities
    SET fec_matched = 0
    WHERE donor_id IN ({','.join('?'*len(donor_ids))})
""", donor_ids)
reset = cur.rowcount
print(f"  Reset fec_matched=0 for {reset:,} donor_ids")

conn.commit()
conn.close()

print(f"""
Done. {reset:,} donors staged for re-ingestion.

Next step:
    python fec_enrich.py

fec_enrich.py will re-fetch these donors and store fec_employer,
fec_occupation, and fec_sub_id alongside the partisan lean data.
Lean scores already in donor_identities are safe — they'll be
refreshed with the same values.
""")
