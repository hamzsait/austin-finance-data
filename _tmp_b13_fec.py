import json, urllib.request, urllib.parse, collections

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Powell-Gould Lisa 78757", {"contributor_name": "Powell-Gould", "contributor_state": "TX"}),
    ("Powell Gould Lisa", {"contributor_name": "Lisa Gould", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("New Joe 78735", {"contributor_name": "Joe New", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Valdez Ruben 78736", {"contributor_name": "Ruben Valdez", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Claybrook JoEllen 78731", {"contributor_name": "Claybrook", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Mudd Steve 78745", {"contributor_name": "Mudd", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Timmermann Barth", {"contributor_name": "Timmermann", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Knox Bruce", {"contributor_name": "Bruce Knox", "contributor_state": "TX"}),
    ("Clark Thomas Vacasa", {"contributor_employer": "VACASA", "contributor_state": "TX"}),
    ("Dixit Puneet", {"contributor_name": "Dixit", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Benkendorfer Susan", {"contributor_name": "Benkendorfer", "contributor_state": "TX"}),
    ("Carter Graham", {"contributor_name": "Graham Carter", "contributor_state": "TX"}),
    ("Allensworth Anne", {"contributor_name": "Allensworth", "contributor_state": "TX"}),
]

for label, extra in queries:
    print("=" * 30, label)
    p = {"per_page": 100, "sort": "-contribution_receipt_date"}
    p.update(extra)
    for k in keys:
        try:
            d = q(p, k)
        except Exception as e:
            print("  key err:", e)
            continue
        print("  total:", d.get('pagination', {}).get('count'))
        # summarize distinct name|zip|emp|occ
        seen = collections.Counter()
        for r in d.get('results', []):
            seen[(r.get('contributor_name'), r.get('contributor_city'), (r.get('contributor_zip') or '')[:5],
                  r.get('contributor_employer'), r.get('contributor_occupation'))] += 1
        for kk, n in seen.most_common(40):
            print("  ", n, "x |", " | ".join(str(x) for x in kk))
        # recent committees
        cms = collections.Counter((r.get('committee') or {}).get('name') for r in d.get('results', []))
        print("   committees:", dict(list(cms.most_common(8))))
        break
