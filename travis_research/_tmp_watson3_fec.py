import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Nan Golding TX", {"contributor_name": "Nan Golding", "contributor_state": "TX"}),
    ("Nan Golding ANY", {"contributor_name": "Nan Golding"}),
    ("Golding Austin", {"contributor_name": "Golding", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("DiQuinzio ANY", {"contributor_name": "DiQuinzio"}),
    ("Subramaniam Murali ANY", {"contributor_name": "Murali Subramaniam"}),
    ("InTEC employer", {"contributor_employer": "INTEC"}),
    ("JadCo employer", {"contributor_employer": "JADCO"}),
]

for label, extra in queries:
    print("=" * 25, label)
    p = {"per_page": 50, "sort": "-contribution_receipt_date"}
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
