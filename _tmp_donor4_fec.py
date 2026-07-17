import os, requests
from dotenv import load_dotenv
load_dotenv()
KEY = os.getenv("FEC_API_KEY")

def q(**kw):
    p = {"api_key": KEY, "per_page": 40, "sort": "-contribution_receipt_date"}
    p.update(kw)
    r = requests.get("https://api.open.fec.gov/v1/schedules/schedule_a/", params=p, timeout=60)
    if r.status_code != 200:
        print("ERR", r.status_code, r.text[:200])
        return
    d = r.json()
    print("### total:", d["pagination"]["count"])
    for x in d["results"]:
        cm = x.get("committee") or {}
        vals = [x.get("contributor_name"), x.get("contributor_city"), x.get("contributor_zip"),
                x.get("contributor_occupation"), x.get("contributor_employer"), cm.get("name"),
                (x.get("contribution_receipt_date") or "")[:10], x.get("contribution_receipt_amount")]
        print(" | ".join(str(v) for v in vals))

print("=== VIVA LEARNING ===")
q(contributor_employer="Viva Learning")
print("\n=== TEO GELATO ===")
q(contributor_employer="Teo Gelato")
print("\n=== CHOATE GUY ===")
q(contributor_name="Choate, Guy", contributor_employer="Webb")
