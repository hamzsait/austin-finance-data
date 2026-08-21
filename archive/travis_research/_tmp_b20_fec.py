import os, requests
from dotenv import load_dotenv
load_dotenv()
KEY = os.getenv("FEC_API_KEY_1")
BASE = "https://api.open.fec.gov/v1/schedules/schedule_a/"

def q(**kw):
    p = {"api_key": KEY, "per_page": 20, "sort": "-contribution_receipt_date"}
    p.update(kw)
    r = requests.get(BASE, params=p, timeout=60)
    r.raise_for_status()
    return r.json()

def show(title, js):
    res = js.get("results", [])
    print(f"\n===== {title} — {js['pagination']['count']} total, showing {len(res)} =====")
    for c in res:
        print(f"{c.get('contribution_receipt_date','')[:10]} | {c.get('contributor_name')} | "
              f"{c.get('contributor_city')}, {c.get('contributor_state')} {str(c.get('contributor_zip'))[:5]} | "
              f"emp={c.get('contributor_employer')} | occ={c.get('contributor_occupation')} | "
              f"${c.get('contribution_receipt_amount')} -> {c.get('committee',{}).get('name')}")

show("WALKER LYNN 78746", q(contributor_name="WALKER, LYNN", contributor_state="TX"))
show("employer WALKER ENERGY", q(contributor_employer="WALKER ENERGY"))
show("EILAND GRAY", q(contributor_name="EILAND", contributor_state="TX"))
show("ERWIN ANDY TX", q(contributor_name="ERWIN, ANDY", contributor_state="TX"))
show("GOTTESMAN GRANT", q(contributor_name="GOTTESMAN", contributor_state="TX"))
show("RANGABASHYAM", q(contributor_name="RANGABASHYAM"))
show("SCHOENBAUM BRIAN TX", q(contributor_name="SCHOENBAUM", contributor_state="TX"))
show("FLESCHMAN", q(contributor_name="FLESCHMAN"))
