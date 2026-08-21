import json

d = json.load(open('watson_all_donations.json'))
rows = d if isinstance(d, list) else d.get('donations') or d.get('rows') or []
print('type', type(d), 'n', len(rows))
if rows:
    print('sample keys:', list(rows[0].keys()))
for r in rows:
    s = json.dumps(r).lower()
    if 'lamy' in s or 'gilkey' in s:
        print(json.dumps(r, indent=1))
