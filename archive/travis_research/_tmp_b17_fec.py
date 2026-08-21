import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Hudkins Michael AZ", {"contributor_name": "Michael Hudkins", "contributor_state": "AZ"}),
    ("Chapin Jessica Austin", {"contributor_name": "Jessica Chapin", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Braun Peggy Austin", {"contributor_name": "Peggy Braun", "contributor_state": "TX"}),
    ("Sesil Joseph", {"contributor_name": "Sesil"}),
    ("Gaston Jennifer Austin", {"contributor_name": "Jennifer Gaston", "contributor_state": "TX"}),
    ("Santis Rosa Austin", {"contributor_name": "Rosa Santis", "contributor_state": "TX"}),
    ("Barton Mary Austin", {"contributor_name": "Mary Barton", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Rhode Patrick Austin", {"contributor_name": "Patrick Rhode", "contributor_state": "TX"}),
    ("Young Patricia Austin", {"contributor_name": "Patricia Young Brown", "contributor_state": "TX"}),
    ("Koubaa Mohamed", {"contributor_name": "Koubaa", "contributor_state": "TX"}),
    ("Hufford Amy Austin", {"contributor_name": "Amy Hufford", "contributor_state": "TX"}),
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
            sig = (r.get('contributor_name'), r.get('contributor_city'), r.get('contributor_zip'),
                   r.get('contributor_employer'), r.get('contributor_occupation'))
            if sig in seen:
                continue
            seen.add(sig)
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'))
        break
