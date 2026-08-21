import json, urllib.request, urllib.parse, collections

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Leonard Wilson AUSTIN", {"contributor_name": "Leonard Wilson", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Kerri Oswald TX", {"contributor_name": "Oswald", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Jeanne Nielson TX", {"contributor_name": "Nielson", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Jim Camp MANCHACA", {"contributor_name": "Camp", "contributor_city": "MANCHACA", "contributor_state": "TX"}),
    ("Wendell Bell AUSTIN", {"contributor_name": "Wendell Bell", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Amy Geraci AUSTIN", {"contributor_name": "Geraci", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Vitanza LAKEWAY", {"contributor_name": "Vitanza", "contributor_state": "TX"}),
    ("Schlicher AUSTIN", {"contributor_name": "Schlicher", "contributor_state": "TX"}),
    ("Momand AUSTIN", {"contributor_name": "Momand", "contributor_state": "TX"}),
    ("Grover Bynum", {"contributor_name": "Bynum", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Jason Embry", {"contributor_name": "Embry", "contributor_state": "TX"}),
]

for label, extra in queries:
    print("=" * 30, label)
    p = {"per_page": 40, "sort": "-contribution_receipt_date"}
    p.update(extra)
    for k in keys:
        try:
            d = q(p, k)
        except Exception as e:
            print("  key err:", e)
            continue
        print("  total:", d.get('pagination', {}).get('count'))
        emps = collections.Counter()
        for r in d.get('results', []):
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'), "| $", r.get('contribution_receipt_amount'),
                  "|", (r.get('committee') or {}).get('name'))
            emps[(r.get('contributor_employer'), r.get('contributor_occupation'))] += 1
        print("  --- emp/occ counts:", emps.most_common(8))
        break
