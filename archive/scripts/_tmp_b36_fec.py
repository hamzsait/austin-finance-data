import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Tani Sanchez", {"contributor_name": "Tani Sanchez"}),
    ("Sanchez Houston 77056", {"contributor_name": "Sanchez", "contributor_city": "HOUSTON", "contributor_employer": "SANCHEZ OIL"}),
    ("Michelle Carbajal TX", {"contributor_name": "Michelle Carbajal", "contributor_state": "TX"}),
    ("Rhonda Bratton TX", {"contributor_name": "Rhonda Bratton", "contributor_state": "TX"}),
    ("Nancy Maxwell TX", {"contributor_name": "Nancy Maxwell", "contributor_state": "TX"}),
    ("Justin Jaffe TX", {"contributor_name": "Justin Jaffe", "contributor_state": "TX"}),
    ("Mary Mearig", {"contributor_name": "Mary Mearig"}),
    ("Stafford Wood", {"contributor_name": "Stafford Wood"}),
    ("Rachel Demkowicz", {"contributor_name": "Demkowicz"}),
    ("Susanne DeJernett", {"contributor_name": "DeJernett"}),
    ("Elizabeth Factor", {"contributor_name": "Elizabeth Factor"}),
    ("Jeff Markim", {"contributor_name": "Markim"}),
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
        for r in d.get('results', []):
            print("  ", r.get('contributor_name'), "|", r.get('contributor_city'), r.get('contributor_zip'),
                  "| EMP:", r.get('contributor_employer'), "| OCC:", r.get('contributor_occupation'),
                  "|", r.get('contribution_receipt_date'), "| $", r.get('contribution_receipt_amount'),
                  "|", (r.get('committee') or {}).get('name'))
        break
