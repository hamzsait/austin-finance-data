import os, json, requests
from dotenv import load_dotenv
load_dotenv()
KEYS = [k for k in (os.getenv(f"FEC_API_KEY_{i}") for i in range(1, 10)) if k]
key = KEYS[0]
for nm in ["FLESCHMAN, SANFORD", "FLESCHMAN, SANDY", "FLESCHMAN"]:
    r = requests.get("https://api.open.fec.gov/v1/schedules/schedule_a/", params={
        "api_key": key, "contributor_name": nm, "per_page": 100,
        "sort": "-contribution_receipt_date"})
    if r.status_code != 200:
        print(nm, "HTTP", r.status_code); continue
    res = r.json().get("results", [])
    print(f"\n=== {nm}: {len(res)} rows ===")
    for x in res:
        print(json.dumps({
            "name": x.get("contributor_name"),
            "city": x.get("contributor_city"),
            "st": x.get("contributor_state"),
            "zip": x.get("contributor_zip"),
            "emp": x.get("contributor_employer"),
            "occ": x.get("contributor_occupation"),
            "cmte": x.get("committee", {}).get("name") if x.get("committee") else x.get("committee_id"),
            "date": (x.get("contribution_receipt_date") or "")[:10],
            "amt": x.get("contribution_receipt_amount"),
        }))
