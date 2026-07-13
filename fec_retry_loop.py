"""
FEC enrichment with auto-retry. Checks API health every 10 minutes,
runs enrichment when available, restarts on failure.
"""
import subprocess, sys, time, requests, os
import pathlib as _pathlib
from dotenv import load_dotenv

PYTHON = sys.executable
SCRIPT = os.path.join(os.path.dirname(__file__), "fec_enrich.py")
load_dotenv(_pathlib.Path(__file__).parent / ".env")
API_KEY = os.getenv("FEC_API_KEY_1") or os.environ["FEC_API_KEY_1"]
CHECK_INTERVAL = 300  # 5 minutes (was 10)
SHORT_RETRY = 60      # 1 minute on transient failure

def api_healthy():
    """Try up to 3 times with longer timeouts. FEC API is intermittent."""
    for attempt in range(3):
        try:
            r = requests.get("https://api.open.fec.gov/v1/schedules/schedule_a/",
                             params={"api_key": API_KEY, "contributor_name": "SMITH, JOHN",
                                     "contributor_state": "TX", "per_page": 1},
                             timeout=60)  # 60s instead of 30s
            if r.status_code == 200:
                return True
            print(f"  attempt {attempt+1}: status {r.status_code}", flush=True)
        except Exception as e:
            print(f"  attempt {attempt+1}: {type(e).__name__}", flush=True)
        if attempt < 2:
            time.sleep(10)
    return False

def run_enrichment():
    print(f"[{time.strftime('%H:%M:%S')}] Starting FEC enrichment batch (5000 donors)...", flush=True)
    result = subprocess.run([PYTHON, SCRIPT, "--limit", "5000"],
                           cwd=os.path.dirname(__file__),
                           capture_output=False, timeout=86400)  # 24hr max
    print(f"[{time.strftime('%H:%M:%S')}] Enrichment exited with code {result.returncode}", flush=True)
    return result.returncode

round_num = 0
while True:
    round_num += 1
    print(f"[{time.strftime('%H:%M:%S')}] Round {round_num}: checking FEC API...", flush=True)
    if api_healthy():
        print(f"[{time.strftime('%H:%M:%S')}] API is up. Running enrichment.", flush=True)
        code = run_enrichment()
        if code == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Batch completed successfully. Starting next round.", flush=True)
            continue  # immediately start next batch
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Batch failed (code {code}). Waiting {CHECK_INTERVAL}s...", flush=True)
    else:
        print(f"[{time.strftime('%H:%M:%S')}] API down. Retrying in {CHECK_INTERVAL}s...", flush=True)
    time.sleep(CHECK_INTERVAL)
