import json, urllib.request, urllib.parse, collections, os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

def pull(extra, pages=4):
    rows, last = [], None
    p = {"per_page": 100, "sort": "-contribution_receipt_date"}
    p.update(extra)
    for _ in range(pages):
        got = None
        for k in keys:
            try:
                got = q(p, k); break
            except Exception as e:
                print("   key err:", e)
        if not got: break
        rows.extend(got.get('results', []))
        pg = got.get('pagination', {})
        rows_total = pg.get('count')
        li = pg.get('last_indexes')
        if not li: break
        p.update(li)
    return rows, rows_total

queries = [
    ("SCANLAN, JOHN / TX", {"contributor_name": "SCANLAN, JOHN", "contributor_state": "TX"}),
    ("BULLOCK, DANIEL / TX", {"contributor_name": "BULLOCK, DANIEL", "contributor_state": "TX"}),
    ("BROWN, ANDREW / AUSTIN TX", {"contributor_name": "BROWN, ANDREW", "contributor_state": "TX", "contributor_city": "AUSTIN"}),
]

for label, extra in queries:
    print("=" * 30, label)
    rows, total = pull(extra)
    print("  API total count:", total, "| pulled:", len(rows))
    profile = collections.Counter()
    for r in rows:
        profile[(r.get('contributor_city'), (r.get('contributor_zip') or '')[:5],
                 r.get('contributor_employer'), r.get('contributor_occupation'))] += 1
    for (city, zp, emp, occ), n in profile.most_common(40):
        print(f"  n={n:4d} | {city} {zp} | EMP: {emp} | OCC: {occ}")
    yrs = collections.Counter((r.get('contribution_receipt_date') or '')[:4] for r in rows)
    print("  years:", dict(sorted(yrs.items())))
