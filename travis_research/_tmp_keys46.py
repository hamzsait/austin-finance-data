import json, glob
from collections import Counter

ks = Counter()
n = 0
for f in glob.glob('donorbatch3_*_results.json'):
    for d in json.load(open(f, encoding='utf-8')):
        n += 1
        ks.update(d.keys())
print(n, dict(ks))
