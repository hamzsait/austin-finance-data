import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Shane Finnegan TX", {"contributor_name": "Shane Finnegan", "contributor_state": "TX"}),
    ("Finnegan 78738", {"contributor_name": "Finnegan", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("employer TREND MICRO", {"contributor_employer": "TREND MICRO"}),
    ("Rejimon Varghese", {"contributor_name": "Rejimon Varghese"}),
    ("Varghese NC Qorvo", {"contributor_name": "Varghese", "contributor_state": "NC", "contributor_employer": "QORVO"}),
    ("employer QORVO", {"contributor_employer": "QORVO", "contributor_state": "NC"}),
    ("Leslie Timmerman TX", {"contributor_name": "Leslie Timmerman", "contributor_state": "TX"}),
    ("Tommy Azopardi", {"contributor_name": "Azopardi", "contributor_state": "TX"}),
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
