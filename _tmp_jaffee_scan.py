import csv, glob, sys

targets = ['JAFFE', 'UMATIYA']
rows = []
for f in sorted(glob.glob('tec_data/contribs_*.csv')):
    try:
        with open(f, newline='', encoding='utf-8', errors='replace') as fh:
            r = csv.DictReader(fh)
            for row in r:
                last = (row.get('contributorNameLast') or '').upper()
                org = (row.get('contributorNameOrganization') or '').upper()
                if any(t in last or t in org for t in targets):
                    rows.append((
                        f,
                        row.get('contributorNameLast'),
                        row.get('contributorNameFirst'),
                        row.get('contributorNameOrganization'),
                        row.get('contributorStreetCity'),
                        row.get('contributorStreetPostalCode'),
                        row.get('contributorOccupation'),
                        row.get('contributorEmployer'),
                        row.get('contributionAmount'),
                        row.get('contributionDt'),
                        row.get('filerName'),
                    ))
    except Exception as e:
        print('ERR', f, e, file=sys.stderr)

print('total', len(rows))
for x in rows:
    print(' | '.join(str(i) for i in x[1:]))
