import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Ferguson Kent 78701", {"contributor_name": "Kent Ferguson", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Smith Haley Austin", {"contributor_name": "Haley Smith", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Archer Jack Austin", {"contributor_name": "Jack Archer", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Chamberlin Anastasia", {"contributor_name": "Chamberlin", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Leger Janine", {"contributor_name": "Leger", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Palandino Pamela", {"contributor_name": "Palandino", "contributor_state": "TX"}),
    ("Paladino Pamela", {"contributor_name": "Pamela Paladino", "contributor_state": "TX"}),
    ("Midgley Leslie", {"contributor_name": "Leslie Midgley", "contributor_state": "TX"}),
    ("Garcia Buddy", {"contributor_name": "Buddy Garcia", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Factor Mallory", {"contributor_name": "Mallory Factor", "sort": "-contribution_receipt_date"}),
    ("Rodell Leonard", {"contributor_name": "Rodell", "contributor_state": "TX"}),
    ("Le Kevin 78741", {"contributor_name": "Kevin Le", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("ECR employer", {"contributor_employer": "ECR", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
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
