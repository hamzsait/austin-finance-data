import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Nicholas Dyer TX", {"contributor_name": "Nicholas Dyer", "contributor_state": "TX"}),
    ("Nick Dyer TX", {"contributor_name": "Nick Dyer", "contributor_state": "TX"}),
    ("Dyer Austin 78731", {"contributor_name": "Dyer", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Marc Nathan TX", {"contributor_name": "Marc Nathan", "contributor_state": "TX"}),
    ("Nathan Austin 78759", {"contributor_name": "Nathan", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Egan Nelson employer", {"contributor_employer": "EGAN NELSON", "contributor_state": "TX"}),
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
            nm = (r.get('contributor_name') or '')
            zp = str(r.get('contributor_zip') or '')
            print("  ", nm, "|", r.get('contributor_city'), zp,
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'), "| $", r.get('contribution_receipt_amount'),
                  "|", (r.get('committee') or {}).get('name'))
        break
