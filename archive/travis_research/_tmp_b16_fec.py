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
    ("Aldrich Robert AUSTIN", {"contributor_name": "Robert Aldrich", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Gonzalez Andres SAN ANTONIO", {"contributor_name": "Andres Gonzalez", "contributor_city": "SAN ANTONIO", "contributor_state": "TX"}),
    ("Girard Michael TX", {"contributor_name": "Michael Girard", "contributor_state": "TX"}),
    ("Albert Steven TX", {"contributor_name": "Steven Albert", "contributor_state": "TX"}),
    ("Baldwin Stephen GREELEY CO", {"contributor_name": "Stephen Baldwin", "contributor_city": "GREELEY", "contributor_state": "CO"}),
    ("Martinez Michael AUSTIN", {"contributor_name": "Michael Martinez", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Deyoung Claire TX", {"contributor_name": "Deyoung Claire", "contributor_state": "TX"}),
    ("Simmons Thomas AUSTIN", {"contributor_name": "Thomas Simmons", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Carter Darryl TX", {"contributor_name": "Darryl Carter", "contributor_state": "TX"}),
    ("Joseph Brian TX", {"contributor_name": "Brian Joseph", "contributor_state": "TX"}),
    ("Zeller Charles AUSTIN", {"contributor_name": "Charles Zeller", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
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
    for (n, c, z, e, o), cnt in combos.most_common(15):
        print(f"   [{cnt}x] {n} | {c} {z} | EMP: {e} | OCC: {o}")
