import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Canonico any", {"contributor_name": "Canonico"}),
    ("Canonico TX", {"contributor_name": "Canonico", "contributor_state": "TX"}),
    ("Ardurra employer", {"contributor_employer": "ARDURRA"}),
    ("Champane Hicks any", {"contributor_name": "Champane"}),
    ("Hicks Austin 78746", {"contributor_name": "Champane Hicks", "contributor_state": "TX"}),
    ("Dirx employer", {"contributor_employer": "DIRX"}),
    ("Doug Jones Austin", {"contributor_name": "Doug Jones", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Douglas Jones Austin", {"contributor_name": "Douglas Jones", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Colliers Austin employer", {"contributor_employer": "COLLIERS", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
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
