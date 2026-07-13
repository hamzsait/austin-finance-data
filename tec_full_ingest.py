"""
Run the TEC scraper on ALL contribution shards (contribs_01..contribs_99).
Designed to be polite to the FEC bot — runs one shard at a time, commits between.
"""
import subprocess, sys, os, time, sqlite3

ROOT = r"C:\Users\Hamza Sait\Electoral\austin-finance-data"
SCRAPER = os.path.join(ROOT, "texas_finance_scraper.py")
DB = os.path.join(ROOT, "austin_finance.db")
PYTHON = sys.executable
LOG = os.path.join(ROOT, "tec_ingest_log.txt")

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# Generate shard names: contribs_01.csv .. contribs_99.csv
shards = [f"contribs_{i:02d}.csv" for i in range(1, 100)]

log(f"Starting full TEC ingest: {len(shards)} shards")

for i, shard in enumerate(shards, 1):
    log(f"--- shard {i}/{len(shards)}: {shard} ---")
    env = os.environ.copy()
    env["TEC_SHARD"] = shard
    try:
        result = subprocess.run(
            [PYTHON, SCRAPER],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min per shard
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            log(f"  WARN: shard {shard} returned {result.returncode}")
            log(f"  stderr: {result.stderr[:300]}")
        else:
            # Extract key stats from output
            for line in result.stdout.split("\n"):
                if "ingest" in line.lower() or "linked" in line.lower() or "matched" in line.lower():
                    log(f"  {line.strip()}")
    except subprocess.TimeoutExpired:
        log(f"  TIMEOUT on {shard}")
    except Exception as e:
        log(f"  ERROR on {shard}: {e}")

    # Brief pause to let the FEC bot grab the lock if it needs to
    time.sleep(3)

# Final report
log("=" * 60)
log("Final cross-reference report")
conn = sqlite3.connect(DB, timeout=30)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM texas_contributions_raw")
log(f"Total Texas contributions ingested: {cur.fetchone()[0]:,}")
cur.execute("SELECT COUNT(DISTINCT austin_donor_id) FROM texas_contributions_raw WHERE austin_donor_id IS NOT NULL")
log(f"Distinct Austin donors with TEC matches: {cur.fetchone()[0]:,}")
cur.execute("""
    SELECT tc.filer_name, COUNT(*) as n, SUM(tcr.contribution_amount) as total
    FROM texas_contributions_raw tcr
    JOIN texas_committees tc ON tc.filer_ident = tcr.filer_ident
    GROUP BY tcr.filer_ident
    ORDER BY total DESC
""")
log("Per-committee totals:")
for r in cur.fetchall():
    log(f"  {r[0]}: {r[1]:,} contribs, ${r[2]:,.0f}")
conn.close()
log("=" * 60)
log("FULL TEC INGEST COMPLETE")
