import json
from collections import Counter

TAX = {'Government','Healthcare','Real Estate','Energy / Environment','Finance','Retail',
       'Transportation','Nonprofit / Advocacy','Technology','Consulting / PR','Construction',
       'Venture Capital','Media','Education','Engineering','Labor','Legal',
       'Hospitality / Events','Architecture','Entertainment','Self-Employed','Not Employed','Student'}
CATS = {'aipac_direct','pro_israel','liberal_zionist','jewish_civic','oil_gas','gun_rights',
        'gun_control','military_defense','civic','business','political'}
KEYS = {'donor_id','name','resolved_employer','industry','confidence','evidence','source_url','affiliations'}

inp = json.load(open('donorbatch3_40.json'))
out = json.load(open('donorbatch3_40_results.json'))

assert [d['donor_id'] for d in inp] == [d['donor_id'] for d in out], 'donor_id order/set mismatch'
for r in out:
    assert set(r) == KEYS, (r['name'], set(r) ^ KEYS)
    assert r['industry'] is None or r['industry'] in TAX, r['industry']
    assert r['confidence'] in {'high','medium','low'}, r['confidence']
    for a in r['affiliations']:
        assert a['category'] in CATS, a
        assert set(a) == {'org','role','category','source_url'}, a

print('rows:', len(out), '| confidence:', dict(Counter(r['confidence'] for r in out)))
print('industries:', dict(Counter(r['industry'] for r in out)))
print('affiliations:', sum(len(r['affiliations']) for r in out))
print('VALID')
