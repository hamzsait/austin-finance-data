import json, urllib.request, urllib.parse

keys = []
for line in open('.env'):
    if line.startswith('FEC_API_KEY'):
        keys.append(line.strip().split('=', 1)[1])

def q(params, key):
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/?" + urllib.parse.urlencode(params) + "&api_key=" + key
    return json.load(urllib.request.urlopen(url))

queries = [
    ("Goodman 78732", {"contributor_name": "Goodman", "contributor_zip": "78732"}),
    ("Lui Tat 78660", {"contributor_name": "Lui", "contributor_zip": "78660"}),
    ("McQueen Vanessa 78704", {"contributor_name": "McQueen", "contributor_zip": "78704"}),
    ("Young Dalton 78703", {"contributor_name": "Dalton Young", "contributor_state": "TX"}),
    ("Bradley Sharon 79109", {"contributor_name": "Sharon Bradley", "contributor_zip": "79109"}),
    ("Waxman Joel 78704", {"contributor_name": "Waxman", "contributor_zip": "78704"}),
    ("Matthews Stephanie TAB", {"contributor_name": "Stephanie Matthews", "contributor_state": "TX"}),
    ("Scarborough John 78703", {"contributor_name": "Scarborough", "contributor_zip": "78703"}),
    ("Gimbel 78703", {"contributor_name": "Gimbel", "contributor_zip": "78703"}),
    ("Scaglione 78751", {"contributor_name": "Scaglione", "contributor_zip": "78751"}),
    ("Engle Ryan 78735", {"contributor_name": "Engle", "contributor_zip": "78735"}),
]

for label, extra in queries:
    print("=" * 25, label)
    p = {"per_page": 40, "sort": "-contribution_receipt_date"}
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
