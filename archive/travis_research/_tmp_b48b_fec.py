import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Lindenmuth any TX", {"contributor_name": "Lindenmuth", "contributor_state": "TX"}),
    ("Gerald Lindenmuth nationwide", {"contributor_name": "Gerald Lindenmuth"}),
    ("Lindenmuth employer", {"contributor_employer": "LINDENMUTH"}),
    ("Benyousef any", {"contributor_name": "Benyousef"}),
    ("Ben-Musa any", {"contributor_name": "Ben-Musa"}),
    ("Round Rock Soccer employer", {"contributor_employer": "ROUND ROCK SOCCER"}),
    ("Hill DC designer", {"contributor_name": "Hill", "contributor_city": "WASHINGTON", "contributor_state": "DC", "contributor_occupation": "DESIGNER"}),
    ("Tyler Hill nationwide", {"contributor_name": "Tyler Hill"}),
    ("Transparent employer", {"contributor_employer": "TRANSPARENT"}),
    ("Mitchell Hill employer", {"contributor_employer": "MITCHELL HILL"}),
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
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_state'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'), "| $", r.get('contribution_receipt_amount'),
                  "|", (r.get('committee') or {}).get('name'))
        break
