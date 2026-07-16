"""Assemble validated extraction JSONs into final contribution CSVs.

- One CSV per official + combined travis_contributions.csv
- Dedupe: if two reports by the same official cover the identical period,
  the later-submitted one supersedes IF it contains full schedules (>= as many
  A1 pages). Otherwise both are kept and the collision goes to the review queue
  (e.g. a 2-page correction affidavit never silently replaces a full report).
- Only reports with status PASS/PASS* are emitted; others are listed as excluded.
"""
import csv, json, os, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, 'extracted', 'raw')
OUT = os.path.join(ROOT, 'extracted')

OFFICIALS = {
    'county-judge_andy-brown':  ('Brown, Andy',       'Travis County Judge'),
    'pct1_jeff-travillion':     ('Travillion, Jeff',  'Travis County Commissioner, Precinct 1'),
    'pct2_brigid-shea':         ('Shea, Brigid',      'Travis County Commissioner, Precinct 2'),
    'pct3_ann-howard':          ('Howard, Ann',       'Travis County Commissioner, Precinct 3'),
    'pct4_margaret-gomez':      ('Gomez, Margaret',   'Travis County Commissioner, Precinct 4'),
    # Morales holds Pct 4 since Gómez's June 2026 retirement; constable-era
    # filings are the same person's earlier office (one recipient, one profile).
    'pct4_george-morales':           ('Morales, George', 'Travis County Commissioner, Precinct 4'),
    'pct4_george-morales-constable': ('Morales, George', 'Travis County Constable, Precinct 4'),
}

validation = {r['report']: r for r in json.load(open(os.path.join(OUT, 'validation.json')))}
chunks = json.load(open(os.path.join(ROOT, '_chunks.json')))
by_report = defaultdict(list)
for c in chunks:
    by_report[(c['official'], c['report'])].append(c)

manifest = {(m['folder'], m['file'][:-4]): m for m in json.load(open(os.path.join(ROOT, 'manifest.json')))}

def norm_date(d):
    if not d: return None
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', d.strip())
    if not m: return d
    mo, dy, yr = m.groups()
    yr = ('20' + yr if int(yr) < 50 else '19' + yr) if len(yr) == 2 else yr
    return f'{yr}-{int(mo):02d}-{int(dy):02d}'

# ---- collect rows per report -------------------------------------------------
report_rows = {}
excluded, notes = [], []
for (official, report), cs in sorted(by_report.items()):
    rid = f'{official}__{report}'
    v = validation.get(rid)
    if not v or v['status'] not in ('PASS', 'PASS*'):
        excluded.append({'report': rid, 'status': v['status'] if v else 'NOT VALIDATED'})
        continue
    rows = []
    for c in cs:
        data = json.load(open(c['out'], encoding='utf-8-sig'))
        for p in data['pages']:
            if p['type'] not in ('A1', 'A2'):
                continue
            for e in p.get('entries', []):
                rows.append({
                    'official_slug': official,
                    'recipient': OFFICIALS[official][0],
                    'office': OFFICIALS[official][1],
                    'donor': (e.get('name') or '').strip(),
                    'contribution_amount': e.get('amount'),
                    'contribution_date': norm_date(e.get('date')),
                    'city_state_zip': e.get('city_state_zip'),
                    'donor_occupation': e.get('occupation'),
                    'donor_employer': e.get('employer'),
                    'contribution_type': 'in-kind' if p['type'] == 'A2' else 'monetary',
                    'in_kind_description': e.get('in_kind_description'),
                    'out_of_state_pac': bool(e.get('oos_pac')),
                    'uncertain': bool(e.get('uncertain')),
                    'report_file': report + '.pdf',
                    'report_type': v.get('report_type'),
                    'period_from': norm_date(v['period'][0]),
                    'period_through': norm_date(v['period'][1]),
                    'date_submitted': (manifest.get((official, report)) or {}).get('datesubmitted'),
                    'page': p['page'],
                })
    report_rows[rid] = {'official': official, 'report': report, 'rows': rows, 'v': v}

# ---- dedupe overlapping periods ---------------------------------------------
superseded = set()
by_official_period = defaultdict(list)
for rid, r in report_rows.items():
    key = (r['official'], r['v']['period'][0], r['v']['period'][1])
    by_official_period[key].append(rid)
for key, rids in by_official_period.items():
    if len(rids) < 2 or key[1] is None:
        continue
    # prefer latest submission; only supersede if replacement has full schedules
    rids_sorted = sorted(rids, key=lambda x: report_rows[x]['v']['report'])  # date prefix sorts
    winner = rids_sorted[-1]
    for loser in rids_sorted[:-1]:
        if report_rows[winner]['v']['a1_pages'] >= report_rows[loser]['v']['a1_pages']:
            superseded.add(loser)
            notes.append(f'{loser} superseded by {winner} (same period {key[1]}-{key[2]})')
        else:
            notes.append(f'REVIEW: {winner} covers same period as {loser} but has fewer '
                         f'A1 pages — kept BOTH; check for double-count')

# ---- write CSVs ---------------------------------------------------------------
FIELDS = ['official_slug', 'recipient', 'office', 'donor', 'contribution_amount',
          'contribution_date', 'city_state_zip', 'donor_occupation', 'donor_employer',
          'contribution_type', 'in_kind_description', 'out_of_state_pac', 'uncertain',
          'report_file', 'report_type', 'period_from', 'period_through',
          'date_submitted', 'page']

all_rows = []
per_official = defaultdict(list)
for rid, r in sorted(report_rows.items()):
    if rid in superseded:
        continue
    all_rows.extend(r['rows'])
    per_official[r['official']].extend(r['rows'])

os.makedirs(OUT, exist_ok=True)
def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)

write_csv(os.path.join(OUT, 'travis_contributions.csv'), all_rows)
for off, rows in per_official.items():
    write_csv(os.path.join(OUT, f'{off}.csv'), rows)

summary = {
    'total_rows': len(all_rows),
    'total_amount': round(sum(r['contribution_amount'] or 0 for r in all_rows), 2),
    'by_official': {o: {'rows': len(rs),
                        'amount': round(sum(r['contribution_amount'] or 0 for r in rs), 2)}
                    for o, rs in sorted(per_official.items())},
    'reports_included': len(report_rows) - len(superseded),
    'superseded': sorted(superseded),
    'excluded': excluded,
    'notes': notes,
}
json.dump(summary, open(os.path.join(OUT, 'assembly_summary.json'), 'w'), indent=1)
print(json.dumps(summary, indent=1))
