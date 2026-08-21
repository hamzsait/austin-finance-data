import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Jessup Lisa 78746", {"contributor_name": "Jessup", "contributor_state": "TX", "contributor_city": "AUSTIN"}),
    ("Smith Haley 78703", {"contributor_name": "Haley Smith", "contributor_state": "TX", "contributor_city": "AUSTIN"}),
    ("Reimers Brandy 78703", {"contributor_name": "Reimers", "contributor_state": "TX"}),
    ("Galindo Angela 77807", {"contributor_name": "Angela Galindo", "contributor_state": "TX"}),
    ("Mauro Katherine 78703", {"contributor_name": "Mauro", "contributor_state": "TX", "contributor_city": "AUSTIN"}),
    ("Pound Ashley 78741", {"contributor_name": "Pound", "contributor_state": "TX", "contributor_city": "AUSTIN"}),
    ("Whitworth Scott 78701", {"contributor_name": "Scott Whitworth", "contributor_state": "TX"}),
    ("Klutts Clayton 78703", {"contributor_name": "Klutts", "contributor_state": "TX"}),
    ("Jackson Clark 78652", {"contributor_name": "Clark Jackson", "contributor_state": "TX"}),
    ("Miller Jennifer 78732", {"contributor_name": "Jennifer Miller", "contributor_state": "TX", "contributor_city": "AUSTIN"}),
    ("Sathyasuba IL", {"contributor_name": "Sathyasuba", "contributor_state": "IL"}),
    ("Baskaran IL", {"contributor_name": "Baskaran", "contributor_state": "IL"}),
    ("Kuppan IL", {"contributor_name": "Kuppan", "contributor_state": "IL"}),
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
