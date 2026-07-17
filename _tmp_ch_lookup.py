import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Courtney Hill TX", {"contributor_name": "Courtney Hill", "contributor_state": "TX"}),
    ("Hill Courtney Austin", {"contributor_name": "Hill, Courtney", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("employer Good Shepherd Episcopal School", {"contributor_employer": "GOOD SHEPHERD EPISCOPAL SCHOOL"}),
    ("employer GSES TX", {"contributor_employer": "GSES", "contributor_state": "TX"}),
    ("zip 78763 Hill", {"contributor_name": "Hill", "contributor_zip": "78763"}),
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
        for r in d.get('results', []):
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'), "| $", r.get('contribution_receipt_amount'),
                  "|", (r.get('committee') or {}).get('name'))
        break
