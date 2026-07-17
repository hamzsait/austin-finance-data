import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Schlotter William 78750", {"contributor_name": "Schlotter", "contributor_state": "TX"}),
    ("Scott Jeff 78737", {"contributor_name": "Jeff Scott", "contributor_state": "TX", "contributor_city": "AUSTIN"}),
    ("Borth Margaret 78731", {"contributor_name": "Borth", "contributor_state": "TX"}),
    ("Kruger David 78731", {"contributor_name": "David Kruger", "contributor_state": "TX"}),
    ("Kath Melissa 78757", {"contributor_name": "Kath", "contributor_state": "TX"}),
    ("Cunningham Brock 78734", {"contributor_name": "Brock Cunningham", "contributor_state": "TX"}),
    ("Dargenio Cassandra 78704", {"contributor_name": "Dargenio", "contributor_state": "TX"}),
    ("Erwin Andrew 78750", {"contributor_name": "Andrew Erwin", "contributor_state": "TX"}),
    ("Douglass Holly Jordan GA", {"contributor_name": "Douglass Holly", "contributor_state": "GA"}),
    ("Johnson Erika 78731", {"contributor_name": "Erika Johnson", "contributor_state": "TX", "contributor_city": "AUSTIN"}),
    ("Spencer Jim 78746", {"contributor_name": "Spencer", "contributor_state": "TX", "contributor_city": "AUSTIN", "contributor_employer": "SPECIALLY"}),
    ("Dow Melanie 78701", {"contributor_name": "Melanie Dow", "contributor_state": "TX"}),
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
