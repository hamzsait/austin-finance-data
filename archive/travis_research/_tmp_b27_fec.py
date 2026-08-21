import json, urllib.request, urllib.parse, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Sherrod Jesse MONROVIA CA", {"contributor_name": "Sherrod Jesse", "contributor_city": "MONROVIA", "contributor_state": "CA"}),
    ("Wilson Randall AUSTIN TX", {"contributor_name": "Randall Wilson", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Holley Janna TX", {"contributor_name": "Janna Holley", "contributor_state": "TX"}),
    ("Meade Bailey AUSTIN TX", {"contributor_name": "Bailey Meade", "contributor_state": "TX"}),
    ("Walters Bill/William AUSTIN TX", {"contributor_name": "Walters William", "contributor_city": "AUSTIN", "contributor_state": "TX"}),
    ("Weir Jaspar", {"contributor_name": "Jaspar Weir"}),
    ("Beckham Bell", {"contributor_name": "Bell Beckham"}),
    ("Keese Stacy TX", {"contributor_name": "Stacy Keese", "contributor_state": "TX"}),
    ("Synnott James TX", {"contributor_name": "James Synnott", "contributor_state": "TX"}),
    ("Tung Caleb", {"contributor_name": "Caleb Tung"}),
    ("Pielet Uri", {"contributor_name": "Uri Pielet"}),
    ("Meserole Greg TX", {"contributor_name": "Meserole", "contributor_state": "TX"}),
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
