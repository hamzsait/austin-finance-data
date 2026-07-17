import json, urllib.request, urllib.parse, time

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Van Jobe TX", {"contributor_name": "Jobe", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Jarod Kilgore", {"contributor_name": "Kilgore", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Robert Simmons Austin", {"contributor_name": "Robert Simmons", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Richard Hass SATX", {"contributor_name": "Hass", "contributor_city": "SAN ANTONIO", "contributor_state": "TX"}),
    ("Richard Hass Austin", {"contributor_name": "Hass", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("John Scanlan Austin", {"contributor_name": "Scanlan", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Daniel Bullock Austin", {"contributor_name": "Bullock", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Andrew Brown Austin", {"contributor_name": "Andrew Brown", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Scott Baker Austin", {"contributor_name": "Scott Baker", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
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
        seen = set()
        for r in d.get('results', []):
            sig = (r.get('contributor_name'), r.get('contributor_zip'),
                   r.get('contributor_employer'), r.get('contributor_occupation'))
            if sig in seen:
                continue
            seen.add(sig)
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'))
        break
    time.sleep(0.5)
