import os, requests
from dotenv import load_dotenv
load_dotenv()
KEY = os.getenv("FEC_API_KEY_1")

def look(last, first, zips=None, city=None):
    p = {"api_key": KEY, "contributor_name": last + ", " + first,
         "per_page": 30, "sort": "-contribution_receipt_date"}
    if zips: p["contributor_zip"] = zips
    if city: p["contributor_city"] = city
    r = requests.get("https://api.open.fec.gov/v1/schedules/schedule_a/", params=p, timeout=40)
    if r.status_code != 200:
        print(last, first, "HTTP", r.status_code, r.text[:200]); return
    d = r.json()
    print("\n=== " + last + ", " + first + "  zip=" + str(zips) + "  n=" + str(d["pagination"]["count"]))
    seen = set()
    for it in d["results"]:
        k = (it.get("contributor_occupation"), it.get("contributor_employer"),
             it.get("contributor_city"), it.get("contributor_zip"))
        if k in seen: continue
        seen.add(k)
        print("   ", (it.get("contribution_receipt_date") or "")[:10], "|",
              it.get("contributor_name"), "|", it.get("contributor_city"), it.get("contributor_zip"), "|",
              it.get("contributor_occupation"), "@", it.get("contributor_employer"), "|",
              (it.get("committee") or {}).get("name"))

look("PRICE", "LAURA", zips="66209")
look("WHITLEY", "MEGAN", zips="78735")
look("BUECHLER", "WILLIAM", zips="78746")
look("EPSTEIN", "SUSAN", zips="78746")
look("DELK", "MARIA", zips="78749")
look("CORDERO", "CALISTA")
