import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Dyer Austin", {"contributor_name": "Dyer", "contributor_city": "AUSTIN", "contributor_state": "TX", "contributor_zip": "78731"}),
    ("Nicholas Dyer TX", {"contributor_name": "Nicholas Dyer", "contributor_state": "TX"}),
    ("Alex Ward 78746", {"contributor_name": "Ward", "contributor_state": "TX", "contributor_zip": "78746"}),
    ("Alex Ward TX", {"contributor_name": "Alex Ward", "contributor_state": "TX"}),
    ("Alexander Ward TX", {"contributor_name": "Alexander Ward", "contributor_state": "TX"}),
    ("Petkas TX", {"contributor_name": "Petkas", "contributor_state": "TX"}),
    ("Rudy 78733", {"contributor_name": "Rudy", "contributor_state": "TX", "contributor_zip": "78733"}),
    ("Watkins 78703", {"contributor_name": "Watkins", "contributor_state": "TX", "contributor_zip": "78703"}),
    ("Marc Nathan TX", {"contributor_name": "Nathan", "contributor_city": "AUSTIN", "contributor_state": "TX", "contributor_zip": "78759"}),
    ("Lamy 78746", {"contributor_name": "Lamy", "contributor_state": "TX", "contributor_zip": "78746"}),
]

for label, extra in queries:
    print("=" * 25, label)
    p = {"per_page": 40, "sort": "-contribution_receipt_date"}
    p.update(extra)
    for k in keys:
        try:
            d = q(p, k)
        except Exception as e:
            print("  key err:", e)
            continue
        print("  total:", d.get('pagination', {}).get('count'))
        for r in d.get('results', []):
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'), "| $", r.get('contribution_receipt_amount'),
                  "|", (r.get('committee') or {}).get('name'))
        break
