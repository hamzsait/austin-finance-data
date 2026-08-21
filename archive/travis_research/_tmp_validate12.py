import json
from collections import Counter

inp = json.load(open('donorbatch3_12.json'))
out = json.load(open('donorbatch3_12_results.json'))

TAX = {'Government','Healthcare','Real Estate','Energy / Environment','Finance','Retail',
       'Transportation','Nonprofit / Advocacy','Technology','Consulting / PR','Construction',
       'Venture Capital','Media','Education','Engineering','Labor','Legal',
       'Hospitality / Events','Architecture','Entertainment','Self-Employed','Not Employed','Student'}
CATS = {'aipac_direct','pro_israel','liberal_zionist','jewish_civic','oil_gas','gun_rights',
        'gun_control','military_defense','civic','business','political'}
FLAG = CATS - {'civic','business','political'}

print('in', len(inp), 'out', len(out))
print('ids match order:', [d['donor_id'] for d in inp] == [d['donor_id'] for d in out])

for d in out:
    assert d['industry'] is None or d['industry'] in TAX, ('BAD INDUSTRY', d['name'], d['industry'])
    assert d['confidence'] in ('high','medium','low'), d
    for k in ('donor_id','name','resolved_employer','industry','confidence','evidence','source_url','affiliations'):
        assert k in d, (d['name'], k)
    for a in d['affiliations']:
        assert a['category'] in CATS, ('BAD CAT', a)
        assert set(a) == {'org','role','category','source_url'}, a
print('schema OK')

print('confidence:', dict(Counter(d['confidence'] for d in out)))
print('industry:', dict(Counter(str(d['industry']) for d in out)))
print('flagged:', [(d['name'], a['org'], a['category']) for d in out for a in d['affiliations'] if a['category'] in FLAG])
