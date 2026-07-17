import json, urllib.request, urllib.parse

keys = []
for line in open('../.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Patrizi 78704", {"contributor_name": "Patrizi", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Beeman Cynthia", {"contributor_name": "Beeman", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Barton Rachel", {"contributor_name": "Rachel Barton", "contributor_state": "TX"}),
    ("Rejimon", {"contributor_name": "Rejimon"}),
    ("Sams Shay", {"contributor_name": "Sams", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Arledge Walker", {"contributor_name": "Arledge", "contributor_state": "TX"}),
    ("Fleschman", {"contributor_name": "Fleschman", "contributor_state": "TX"}),
    ("Wehner Austin", {"contributor_name": "Wehner", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Gitcho", {"contributor_name": "Gitcho"}),
    ("Coffee Elizabeth 78748", {"contributor_name": "Coffee", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Williams Wimberley", {"contributor_name": "Williams", "contributor_city": "WIMBERLEY", "contributor_state": "TX"}),
    ("Garcia Jennifer CEC", {"contributor_employer": "CEC", "contributor_state": "TX"}),
]

for label, extra in queries:
    print("=" * 30, label)
    p = {"per_page": 30, "sort": "-contribution_receipt_date"}
    p.update(extra)
    for k in keys:
        try:
            d = q(p, k)
        except Exception as e:
            print("  key err:", e)
            continue
        print("  total:", d.get('pagination', {}).get('count'))
        seen = set()
        for r in d.get('results', []):
            sig = (r.get('contributor_name'), r.get('contributor_zip'), r.get('contributor_employer'), r.get('contributor_occupation'))
            if sig in seen:
                continue
            seen.add(sig)
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date', '')[:10], "| $", r.get('contribution_receipt_amount'),
                  "|", (r.get('committee') or {}).get('name'))
        break
