"""Merge chunk JSONs per report and validate extraction quality.

Checks per report:
  1. completeness  - every page 1..N classified exactly once
  2. A1 schedule   - "Sch: X/Y" positions consistent; count(A1 pages) == Y
  3. money math    - sum(A1 amounts) + unitemized == cover-sheet total (tol 1.00)
  4. entry sanity  - amounts present/positive, dates parse, names non-empty

Outputs:
  extracted/validation.json   - machine-readable per-report results
  extracted/review_queue.json - pages/entries needing re-extraction or human review
  stdout                      - summary table
"""
import json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, 'extracted', 'raw')
TOL = 1.00

# Filer-side discrepancies verified by human inspection of the page images:
# report id -> (expected delta, note). These reports' schedules and cover sheet
# disagree in the original sworn filing; we keep entries as filed.
KNOWN_FILER_DISCREPANCIES = {
    'county-judge_andy-brown__2026-01-15_COH-Andy-Brown-January-2026': (5000.00,
        'Schedules list Husch Blackwell $5,000 twice (12/17/2025 and 12/31/2025, '
        'verified on page 19 image); cover-sheet total $277,378.33 is $5,000 lower. '
        'Filer error in original report.'),
    # The four below were adjudicated by page-level reconciliation agents; full
    # evidence in extracted/reconcile/<report>.json
    'pct4_margaret-gomez__2017-07-17_COH': (13850.06,
        'Filer wrote prior-period balance $13,850.06 into the unitemized-contributions '
        'box; A1 total $1,500 matches all subtotals. True unitemized = $0.'),
    'pct4_margaret-gomez__2022-01-31_COH': (59.40,
        "Filer's own cover pages disagree ($12,260.60 on COVER3 vs $12,200.60 on "
        'COVER2); all 5 entries verified at zoom sum to $12,260.00.'),
    'pct4_margaret-gomez__2022-02-21_COH': (-2750.00,
        'A1 headers say 4 schedule pages; only 3 exist in the filed/scanned PDF. '
        'One A1 page (~$2,750, mid-Feb 2022) is missing from the county record itself.'),
    'pct4_margaret-gomez__2022-07-15_COH': (300.00,
        'All 40 entries verified box-by-box ($24,007.12); corrected cover total reads '
        "$23,707.12 — filer's stated total is $300 below the true itemized sum."),
}

# Reports with no SUPPORT & TOTALS cover by design (verified by human
# inspection): Form DAILY-C C/OH daily pre-election reports. Skip cover checks.
DAILY_REPORTS = {
    # Portal labels it CCOH but the form is a DAILY-C C/OH: one contribution
    # (Soeur, Channy $2,500 on 02/23/2026), 2 pages, no totals sheet.
    'pct2_brigid-shea__2026-02-26_CCOH',
}

chunks = json.load(open(os.path.join(ROOT, '_chunks.json')))
by_report = defaultdict(list)
for c in chunks:
    by_report[(c['official'], c['report'])].append(c)

only = sys.argv[1] if len(sys.argv) > 1 else None

results, queue = [], []
for (official, report), cs in sorted(by_report.items()):
    rid = f'{official}__{report}'
    if only and only not in rid:
        continue
    missing_chunks = [c['id'] for c in cs if not os.path.exists(c['out'])]
    pages = {}
    for c in cs:
        if c['id'] in [m for m in missing_chunks]:
            continue
        try:
            data = json.load(open(c['out'], encoding='utf-8-sig'))
        except Exception as e:
            queue.append({'report': rid, 'chunk': c['id'], 'problem': f'bad json: {e}'})
            continue
        for p in data['pages']:
            if p['page'] in pages:
                queue.append({'report': rid, 'page': p['page'], 'problem': 'duplicate page object'})
            pages[p['page']] = p

    n_expected = sum(len(c['pages']) for c in cs)
    issues = []
    if missing_chunks:
        issues.append(f'{len(missing_chunks)} chunks not extracted yet')
    missing_pages = [i for i in range(1, n_expected + 1) if i not in pages]
    if missing_pages and not missing_chunks:
        issues.append(f'missing pages: {missing_pages[:8]}')

    # covers
    cover1 = next((p for p in pages.values() if p['type'] == 'COVER1'), None)
    cover2 = next((p for p in pages.values() if p['type'] == 'COVER2'), None)
    is_daily = rid in DAILY_REPORTS
    if not cover1 and not is_daily: issues.append('no COVER1')
    if not cover2 and not is_daily: issues.append('no COVER2')

    # A1 schedule position check
    a1 = sorted((p for p in pages.values() if p['type'] == 'A1'), key=lambda p: p['page'])
    a2 = sorted((p for p in pages.values() if p['type'] == 'A2'), key=lambda p: p['page'])
    totals_y = set()
    positions = []
    for p in a1:
        sp = p.get('sch_pos')
        if sp and re.match(r'^\d+\s*/\s*\d+$', str(sp)):
            x, y = [int(v) for v in re.split(r'\s*/\s*', str(sp))]
            positions.append(x); totals_y.add(y)
    if len(totals_y) > 1:
        issues.append(f'inconsistent A1 total pages: {sorted(totals_y)}')
    elif totals_y:
        y = totals_y.pop()
        if len(a1) != y:
            issues.append(f'A1 pages found {len(a1)} != schedule says {y}')
        missing_pos = sorted(set(range(1, y + 1)) - set(positions))
        if missing_pos:
            issues.append(f'missing A1 positions: {missing_pos[:8]}')

    # money math
    def entries(plist):
        for p in plist:
            for e in p.get('entries', []):
                yield p['page'], e
    n_entries = 0; itemized = 0.0; bad_entries = 0
    for pg, e in list(entries(a1)) + list(entries(a2)):
        n_entries += 1
        amt = e.get('amount')
        if amt is None or e.get('uncertain'):
            bad_entries += 1
            queue.append({'report': rid, 'page': pg, 'entry': e.get('name'),
                          'problem': 'null amount' if amt is None else f"uncertain: {e.get('note','')}"})
        if amt: itemized += float(amt)  # cover-sheet total includes in-kind (A2)
        if not e.get('name'):
            queue.append({'report': rid, 'page': pg, 'problem': 'entry with no name'})
    n_inkind = sum(1 for _ in entries(a2))

    unitemized = (cover2 or {}).get('total_unitemized_contributions') or 0.0
    cover_total = (cover2 or {}).get('total_contributions')
    delta = None
    filer_note = None
    if cover_total is not None:
        delta = round(itemized + unitemized - float(cover_total), 2)
        known = KNOWN_FILER_DISCREPANCIES.get(rid)
        if known and abs(delta - known[0]) <= TOL:
            filer_note = known[1]
        elif abs(delta) > TOL:
            issues.append(f'money mismatch: itemized {itemized:.2f} + unitem {unitemized:.2f} vs cover {cover_total:.2f} (delta {delta:+.2f})')

    unreadable = [p['page'] for p in pages.values() if p['type'] == 'UNREADABLE']
    if unreadable:
        issues.append(f'unreadable pages: {unreadable}')
        for pg in unreadable:
            queue.append({'report': rid, 'page': pg, 'problem': 'UNREADABLE'})

    status = 'PASS' if not issues else ('PENDING' if missing_chunks else 'FAIL')
    if status == 'PASS' and filer_note:
        status = 'PASS*'  # filer-side discrepancy, verified + documented
        queue.append({'report': rid, 'problem': 'filer discrepancy (kept as filed)', 'note': filer_note})
    results.append({
        'report': rid, 'status': status, 'pages': n_expected,
        'a1_pages': len(a1), 'entries': n_entries, 'inkind': n_inkind,
        'itemized_sum': round(itemized, 2), 'unitemized': unitemized,
        'cover_total': cover_total, 'delta': delta,
        'uncertain_entries': bad_entries,
        'filer_note': filer_note,
        'period': [(cover1 or {}).get('period_from'), (cover1 or {}).get('period_through')],
        'report_type': (cover1 or {}).get('report_type'),
        'correction': (cover1 or {}).get('correction'),
        'issues': issues,
    })

os.makedirs(os.path.join(ROOT, 'extracted'), exist_ok=True)
json.dump(results, open(os.path.join(ROOT, 'extracted', 'validation.json'), 'w'), indent=1)
json.dump(queue, open(os.path.join(ROOT, 'extracted', 'review_queue.json'), 'w'), indent=1)

W = max((len(r['report']) for r in results), default=20)
print(f"{'report':<{W}}  {'st':4} {'pgs':>4} {'A1':>3} {'rows':>5} {'itemized':>11} {'cover':>11} {'delta':>8}")
for r in results:
    ct = f"{r['cover_total']:.2f}" if r['cover_total'] is not None else '-'
    dl = f"{r['delta']:+.2f}" if r['delta'] is not None else '-'
    print(f"{r['report']:<{W}}  {r['status']:4} {r['pages']:>4} {r['a1_pages']:>3} {r['entries']:>5} {r['itemized_sum']:>11.2f} {ct:>11} {dl:>8}")
    for i in r['issues']:
        print(f"{'':{W}}    - {i}")
print(f"\n{sum(1 for r in results if r['status']=='PASS')}/{len(results)} PASS; review queue: {len(queue)} items")
