import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params):
    for k in keys:
        url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + k
        try:
            return json.load(urllib.request.urlopen(url))
        except Exception as e:
            print("  key err:", e)
    return None

queries = [
    ("RANGABASHYAM any", {"contributor_name": "RANGABASHYAM"}),
    ("BASHYAM TX", {"contributor_name": "BASHYAM", "contributor_state": "TX"}),
    ("employer INTERNATIONAL MARKETING TX", {"contributor_employer": "INTERNATIONAL MARKETING", "contributor_state": "TX"}),
    ("zip 78733 employer IMTS", {"contributor_employer": "IMTS", "contributor_state": "TX"}),
]

for label, extra in queries:
    print("=" * 30, label)
    p = {"per_page": 50, "sort": "-contribution_receipt_date"}
    p.update(extra)
    d = q(p)
    if not d:
        continue
    print("  total:", d.get('pagination', {}).get('count'))
    for r in d.get('results', []):
        cm = r.get('committee') or {}
        print("   |", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_state'), r.get('contributor_zip'),
              "|", r.get('contributor_employer'), "/", r.get('contributor_occupation'),
              "|", r.get('contribution_receipt_date'), r.get('contribution_receipt_amount'),
              "|", cm.get('name'))
