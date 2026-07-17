import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("WARD ALEX TX", {"contributor_name": "ALEX WARD", "contributor_state": "TX"}),
    ("WARD ALEXANDER TX", {"contributor_name": "ALEXANDER WARD", "contributor_state": "TX"}),
    ("WARD WEST LAKE HILLS", {"contributor_name": "WARD", "contributor_city": "WEST LAKE HILLS", "contributor_state": "TX"}),
    ("WATKINS SANDY TX", {"contributor_name": "SANDY WATKINS", "contributor_state": "TX"}),
    ("WATKINS HSW employer", {"contributor_employer": "HSW", "contributor_state": "TX"}),
]

for label, extra in queries:
    print("=" * 25, label)
    p = {"per_page": 100, "sort": "-contribution_receipt_date"}
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
            sig = (r.get('contributor_name'), r.get('contributor_zip'),
                   r.get('contributor_employer'), r.get('contributor_occupation'))
            if sig in seen:
                continue
            seen.add(sig)
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'), "| $", r.get('contribution_receipt_amount'),
                  "|", (r.get('committee') or {}).get('name'))
        break
