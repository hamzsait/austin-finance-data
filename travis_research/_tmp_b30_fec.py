import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Zeifman Clifford TX", {"contributor_name": "Zeifman", "contributor_state": "TX"}),
    ("Shafer Kristine TX", {"contributor_name": "Kristine Shafer", "contributor_state": "TX"}),
    ("Whitworth Scott TX", {"contributor_name": "Scott Whitworth", "contributor_state": "TX"}),
    ("Manley Paul TX", {"contributor_name": "Paul Manley", "contributor_state": "TX"}),
    ("Wehbe TX", {"contributor_name": "Wehbe", "contributor_state": "TX"}),
    ("Manasiya TX", {"contributor_name": "Manasiya", "contributor_state": "TX"}),
    ("Ressler Austin", {"contributor_name": "Ressler", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Eastridge Arianna", {"contributor_name": "Eastridge", "contributor_state": "TX"}),
    ("Boothe Lawson", {"contributor_name": "Booth", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Hunziker Hendrix Tracey", {"contributor_name": "Hendrix Tracey", "contributor_state": "TX"}),
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
