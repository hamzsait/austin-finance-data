import json, urllib.request, urllib.parse, collections

keys = []
for line in open('.env'):
    line = line.strip()
    if line.startswith('FEC_API_KEY'):
        keys.append(line.split('=', 1)[1])

def q(params):
    last = None
    for k in keys:
        url = ("https://api.open.fec.gov/v1/schedules/schedule_a/?"
               + urllib.parse.urlencode(params) + "&api_key=" + k)
        try:
            return json.load(urllib.request.urlopen(url))
        except Exception as e:
            last = e
            continue
    print("   ALL KEYS FAILED:", last)
    return {}

queries = [
    ("Goodman Barry TX", {"contributor_name": "Barry Goodman", "contributor_state": "TX"}),
    ("Schneider John AUSTIN", {"contributor_name": "John Schneider", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Simmons Amelia AUSTIN", {"contributor_name": "Simmons Amelia", "contributor_state": "TX"}),
    ("Simmons Amy AUSTIN", {"contributor_name": "Amy Simmons", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Priske Joseph TX", {"contributor_name": "Priske", "contributor_state": "TX"}),
    ("Hamon Clark TX", {"contributor_name": "Hamon Clark", "contributor_state": "TX"}),
    ("Barksdale Jacqueline AUSTIN", {"contributor_name": "Jacqueline Barksdale", "contributor_state": "TX"}),
    ("Hinojosa Daniel AUSTIN", {"contributor_name": "Daniel Hinojosa", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Attal Jeff TX", {"contributor_name": "Attal", "contributor_state": "TX"}),
    ("Arethimmappa TX", {"contributor_name": "Arethimmappa", "contributor_state": "TX"}),
    ("Panzer Debra TX", {"contributor_name": "Panzer", "contributor_state": "TX"}),
    ("Lipscomb Amanda TX", {"contributor_name": "Amanda Lipscomb", "contributor_state": "TX"}),
    ("Anguamea TX", {"contributor_name": "Anguamea", "contributor_state": "TX"}),
]

for label, extra in queries:
    print("=" * 30, label)
    p = {"per_page": 40, "sort": "-contribution_receipt_date"}
    p.update(extra)
    d = q(p)
    print("  total:", d.get('pagination', {}).get('count'))
    combos = collections.Counter()
    for r in d.get('results', []):
        combos[(r.get('contributor_name'), r.get('contributor_city'),
                (r.get('contributor_zip') or '')[:5],
                r.get('contributor_employer'), r.get('contributor_occupation'))] += 1
    for (n, c, z, e, o), cnt in combos.most_common(12):
        print(f"   [{cnt}x] {n} | {c} {z} | EMP: {e} | OCC: {o}")
