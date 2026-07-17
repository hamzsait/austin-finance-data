import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Barbara Foster Austin", {"contributor_name": "Barbara Foster", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Presidio Ranch employer", {"contributor_employer": "PRESIDIO RANCH", "contributor_state": "TX"}),
    ("Olivia Henderson Austin", {"contributor_name": "Olivia Henderson", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Yonilda Varner", {"contributor_name": "Varner", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Yonilda any", {"contributor_name": "Yonilda"}),
    ("Lauren Harper Houston", {"contributor_name": "Lauren Harper", "contributor_city": "HOUSTON", "contributor_state": "TX"}),
    ("Paul Eberle Elm Grove", {"contributor_name": "Paul Eberle", "contributor_state": "WI"}),
    ("Todd Routh Austin", {"contributor_name": "Routh", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Kell Cahoon", {"contributor_name": "Cahoon", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("David Pierce Parallel", {"contributor_employer": "PARALLEL", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
]

for label, extra in queries:
    print("=" * 25, label)
    p = {"per_page": 30, "sort": "-contribution_receipt_date"}
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
