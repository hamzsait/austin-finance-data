import json
from collections import Counter

a = json.load(open('donorbatch3_44.json'))
b = json.load(open('donorbatch3_44_results.json'))
print('in', len(a), 'out', len(b))
print('ids match:', [x['donor_id'] for x in a] == [x['donor_id'] for x in b])
print(Counter(x['confidence'] for x in b))
print(Counter(x['industry'] for x in b))
required = {'donor_id', 'name', 'resolved_employer', 'industry', 'confidence', 'evidence', 'source_url', 'affiliations'}
for x in b:
    missing = required - set(x)
    if missing:
        print('MISSING', x['name'], missing)
