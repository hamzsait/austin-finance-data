import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Timothy Collins 78703", {"contributor_name": "Collins, Timothy", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Susan Kellner TX", {"contributor_name": "Kellner, Susan", "contributor_state": "TX"}),
    ("David Near TX", {"contributor_name": "Near, David", "contributor_state": "TX"}),
    ("Isabel Wehbe", {"contributor_name": "Wehbe", "contributor_state": "TX"}),
    ("Caroline Cryer", {"contributor_name": "Cryer, Caroline", "contributor_state": "TX"}),
    ("Delaine Teeple", {"contributor_name": "Teeple", "contributor_state": "TX"}),
    ("Ramon Medina Perez", {"contributor_name": "Medina", "contributor_city": "AUSTIN", "contributor_state": "TX", "contributor_zip": "78754"}),
    ("Meredith Sanger", {"contributor_name": "Sanger, Meredith", "contributor_state": "TX"}),
    ("Bennett Maddox", {"contributor_name": "Maddox, Bennett", "contributor_state": "TX"}),
    ("Kevin Fincher", {"contributor_name": "Fincher, Kevin", "contributor_state": "TX"}),
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
