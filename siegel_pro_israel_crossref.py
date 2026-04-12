"""
Cross-reference Mike Siegel's donors against pro-Israel PAC donors.
Fast version: fetches top N donors per committee and cross-references by name+zip.
"""
import requests
import time
import json
import sys
import io
from collections import defaultdict

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

API_KEY = "HATnmUvyw55nkfKvbTg7x5uOKA7t9qqrgWM4sEJ2"
BASE = "https://api.open.fec.gov/v1"

# How many pages per committee (100 per page)
MAX_PAGES_SIEGEL = 100  # ~10K records
MAX_PAGES_PROISRAEL = 50  # ~5K records per PAC

SIEGEL_COMMITTEES = {
    "C00662668": "Mike Siegel for Congress",
    "C00753517": "Mike Siegel Victory Fund",
}

PRO_ISRAEL_COMMITTEES = {
    "C00797670": ("AIPAC PAC", "hawkish"),
    "C00799031": ("United Democracy Project (UDP)", "hawkish"),
    "C00699470": ("Pro-Israel America PAC", "hawkish"),
    "C00710848": ("DMFI PAC (Democratic Majority for Israel)", "hawkish"),
    "C00247403": ("NORPAC", "hawkish"),
    "C00345132": ("Republican Jewish Coalition PAC", "hawkish"),
    "C00687657": ("American Pro-Israel PAC", "hawkish"),
    "C00548628": ("ZOA PAC", "hawkish"),
    "C00141747": ("Friends of Israel PAC (FIPAC)", "hawkish"),
    "C00441949": ("J Street PAC", "liberal_zionist"),
    "C00573253": ("Bend the Arc Jewish Action PAC", "liberal_zionist"),
    "C00306670": ("National Jewish Democratic Council PAC", "liberal_zionist"),
    "C90020926": ("CUFI Action Fund", "christian_zionist"),
}


def fetch_donors(committee_id, label, max_pages=50):
    """Fetch donors to a committee, paginated by last_index."""
    all_rows = []
    last_index = None
    last_date = None
    page = 0
    while page < max_pages:
        page += 1
        params = {
            "api_key": API_KEY,
            "committee_id": committee_id,
            "per_page": 100,
            "sort": "-contribution_receipt_date",
            "is_individual": "true",
        }
        if last_index:
            params["last_index"] = last_index
            params["last_contribution_receipt_date"] = last_date
        try:
            r = requests.get(f"{BASE}/schedules/schedule_a/", params=params, timeout=60)
        except Exception as e:
            print(f"    [ERR] {type(e).__name__}", flush=True)
            time.sleep(5)
            continue
        if r.status_code == 429:
            print(f"    [429] sleep 60", flush=True)
            time.sleep(60)
            continue
        if r.status_code != 200:
            print(f"    [{r.status_code}]", flush=True)
            break
        data = r.json()
        results = data.get("results", [])
        all_rows.extend(results)
        if page == 1:
            total = data.get("pagination", {}).get("count", "?")
            print(f"    [{label[:20]}] total={total} fetching={max_pages*100}", flush=True)
        pag = data.get("pagination", {})
        last_idx_obj = pag.get("last_indexes") or {}
        last_index = last_idx_obj.get("last_index")
        last_date = last_idx_obj.get("last_contribution_receipt_date")
        if not last_index or len(results) == 0:
            break
        time.sleep(0.25)
    return all_rows


def normalize_key(name, zip_code):
    if not name:
        return None
    name = name.upper().strip()
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        last = parts[0]
        first_tokens = parts[1].split() if len(parts) > 1 else []
        first = first_tokens[0] if first_tokens else ""
    else:
        tokens = name.split()
        if len(tokens) >= 2:
            last = tokens[-1]
            first = tokens[0]
        else:
            last = name
            first = ""
    last = last.replace(".", "").strip()
    first_initial = first[:1] if first else ""
    zip5 = (zip_code or "")[:5]
    return f"{last}|{first_initial}|{zip5}"


def main():
    print("=" * 60)
    print("Mike Siegel ↔ Pro-Israel PAC Cross-Reference")
    print("=" * 60)

    # Step 1: Fetch Siegel donors
    print("\nStep 1: Fetching Siegel donors...")
    siegel_donors = []
    for cid, label in SIEGEL_COMMITTEES.items():
        print(f"  {cid} - {label}")
        rows = fetch_donors(cid, label, max_pages=MAX_PAGES_SIEGEL)
        for r in rows:
            r["_source"] = label
        siegel_donors.extend(rows)
        print(f"  -> {len(rows):,} records")

    print(f"\n  Siegel grand total: {len(siegel_donors):,}")

    # Index by (last_name, first_initial, zip5)
    siegel_index = defaultdict(list)
    for row in siegel_donors:
        key = normalize_key(row.get("contributor_name"), row.get("contributor_zip"))
        if key:
            siegel_index[key].append(row)
    print(f"  Unique Siegel donors (by key): {len(siegel_index):,}")

    # Step 2: For each pro-Israel committee, fetch and cross-reference
    print("\nStep 2: Cross-referencing pro-Israel PACs...")
    matches = []
    pi_committee_stats = {}

    for pi_cid, (pi_label, pi_cat) in PRO_ISRAEL_COMMITTEES.items():
        print(f"\n  {pi_label} ({pi_cid}, {pi_cat})")
        pi_donors = fetch_donors(pi_cid, pi_label, max_pages=MAX_PAGES_PROISRAEL)
        if not pi_donors:
            pi_committee_stats[pi_cid] = {"label": pi_label, "donors_scanned": 0, "matches": 0}
            continue

        pi_matches = 0
        for pi_row in pi_donors:
            key = normalize_key(pi_row.get("contributor_name"), pi_row.get("contributor_zip"))
            if key and key in siegel_index:
                for s_row in siegel_index[key]:
                    matches.append((pi_label, pi_cat, s_row, pi_row))
                    pi_matches += 1

        pi_committee_stats[pi_cid] = {"label": pi_label, "donors_scanned": len(pi_donors), "matches": pi_matches}
        print(f"    Scanned {len(pi_donors):,}, matches {pi_matches}")

    print(f"\n\nTotal cross-reference matches: {len(matches)}")

    # Save JSON
    output = {
        "candidate": "Mike Siegel",
        "siegel_committees": SIEGEL_COMMITTEES,
        "pro_israel_committees": {k: {"name": v[0], "category": v[1]} for k, v in PRO_ISRAEL_COMMITTEES.items()},
        "total_siegel_records_scanned": len(siegel_donors),
        "unique_siegel_donors_scanned": len(siegel_index),
        "pi_committee_stats": pi_committee_stats,
        "matches": [
            {
                "pro_israel_committee": label,
                "category": cat,
                "donor_name": s.get("contributor_name"),
                "donor_city": s.get("contributor_city"),
                "donor_state": s.get("contributor_state"),
                "donor_zip": s.get("contributor_zip"),
                "donor_employer": s.get("contributor_employer"),
                "donor_occupation": s.get("contributor_occupation"),
                "siegel_amount": s.get("contribution_receipt_amount"),
                "siegel_date": (s.get("contribution_receipt_date") or "")[:10],
                "siegel_committee": s.get("_source"),
                "pi_amount": pi.get("contribution_receipt_amount"),
                "pi_date": (pi.get("contribution_receipt_date") or "")[:10],
            }
            for (label, cat, s, pi) in matches
        ],
    }

    with open("siegel_cross_ref.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved siegel_cross_ref.json")


if __name__ == "__main__":
    main()
