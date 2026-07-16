"""Build the chunk plan: split every rendered report into ~15-page agent jobs.

Writes _chunks.json: [{id, official, report, pages: [abs png paths], out}]
Skips non-C/OH docs (ACTA, Conflicts Disclosure) — no contribution schedules.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES_ROOT = sys.argv[1]
OUT_ROOT = os.path.join(ROOT, 'extracted', 'raw')
CHUNK_SIZE = 20

SKIP = {
    'pct2_brigid-shea/2026-02-21_ACTA.pdf',
    'pct3_ann-howard/2022-06-16_Conflicts-Disclosure-Statement.pdf',
    'pct4_george-morales/2025-07-26_ACTA.pdf',
    'pct4_george-morales-constable/2017-07-14_ACTA.pdf',
}

inv = json.load(open(os.path.join(ROOT, '_inventory.json')))
chunks = []
for r in inv:
    key = r['official'] + '/' + r['file']
    if key in SKIP:
        continue
    stem = r['file'][:-4]
    pagedir = os.path.join(PAGES_ROOT, r['official'], stem)
    pngs = sorted(os.listdir(pagedir)) if os.path.isdir(pagedir) else []
    if len(pngs) != r['pages']:
        print(f"NOT-READY {key}: {len(pngs)}/{r['pages']} rendered")
        continue
    for start in range(0, len(pngs), CHUNK_SIZE):
        part = pngs[start:start + CHUNK_SIZE]
        cid = f"{r['official']}__{stem}__p{start+1:04d}-p{start+len(part):04d}"
        chunks.append({
            'id': cid,
            'official': r['official'],
            'report': stem,
            'first_page': start + 1,
            'pages': [os.path.join(pagedir, p) for p in part],
            'out': os.path.join(OUT_ROOT, cid + '.json'),
        })

os.makedirs(OUT_ROOT, exist_ok=True)
json.dump(chunks, open(os.path.join(ROOT, '_chunks.json'), 'w'), indent=1)
print('chunks:', len(chunks), ' reports:', len(inv) - len(SKIP),
      ' pages:', sum(len(c['pages']) for c in chunks))
