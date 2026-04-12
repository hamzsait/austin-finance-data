"""Build a simple HTML report of Mike Siegel's pro-Israel donor crossref."""
import json
import html
from collections import defaultdict

with open("siegel_cross_ref.json", encoding="utf-8") as f:
    data = json.load(f)

# Dedupe donors by name
unique_donors = {}
for m in data["matches"]:
    key = m["donor_name"]
    if key not in unique_donors:
        unique_donors[key] = {
            "name": key,
            "city": m["donor_city"] or "",
            "state": m["donor_state"] or "",
            "zip": m["donor_zip"] or "",
            "employer": m["donor_employer"] or "",
            "occupation": m["donor_occupation"] or "",
            "siegel_total": 0,
            "siegel_gifts": 0,
            "pi_committees": defaultdict(lambda: {"amount": 0, "category": "", "gifts": 0}),
        }
    unique_donors[key]["siegel_total"] += m["siegel_amount"] or 0
    unique_donors[key]["siegel_gifts"] += 1
    comm = unique_donors[key]["pi_committees"][m["pro_israel_committee"]]
    comm["amount"] += m["pi_amount"] or 0
    comm["category"] = m["category"]
    comm["gifts"] += 1

donors_list = sorted(unique_donors.values(), key=lambda x: -x["siegel_total"])

# Category totals
cat_totals = defaultdict(lambda: {"donors": 0, "siegel_amount": 0, "pi_amount": 0})
for d in donors_list:
    primary_cats = set(c["category"] for c in d["pi_committees"].values())
    for c in primary_cats:
        cat_totals[c]["donors"] += 1
    cat_totals_by_donor = defaultdict(float)
    for comm in d["pi_committees"].values():
        cat_totals_by_donor[comm["category"]] += comm["amount"]
    for c, amt in cat_totals_by_donor.items():
        cat_totals[c]["pi_amount"] += amt
    # Assign Siegel amount to dominant category (one category per donor)
    dominant = max(cat_totals_by_donor.items(), key=lambda x: x[1])[0] if cat_totals_by_donor else "liberal_zionist"
    cat_totals[dominant]["siegel_amount"] += d["siegel_total"]

total_siegel_amount = sum(d["siegel_total"] for d in donors_list)

# Committee-level totals
comm_totals = defaultdict(lambda: {"donors": 0, "scanned": 0, "matches": 0})
for cid, stats in data["pi_committee_stats"].items():
    comm_totals[stats["label"]] = stats

def fmt(n):
    return f"${n:,.0f}"

def esc(s):
    return html.escape(str(s or ""))

# Build HTML
CAT_COLORS = {
    "hawkish": "#ef4444",
    "liberal_zionist": "#7c3aed",
    "christian_zionist": "#f59e0b",
}
CAT_LABELS = {
    "hawkish": "Hawkish Pro-Israel (AIPAC-aligned)",
    "liberal_zionist": "Liberal Zionist (J Street / Bend the Arc)",
    "christian_zionist": "Christian Zionist",
}

html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Mike Siegel — Pro-Israel Donor Cross-Reference</title>
<style>
  :root {{
    --bg:#0b1120; --card:#131c2e; --surface:#1a2438; --border:#2a3449;
    --text:#e5e7eb; --muted:#94a3b8; --accent:#60a5fa;
    --hawkish:#ef4444; --liberal:#7c3aed; --christian:#f59e0b;
  }}
  *{{box-sizing:border-box}}
  body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;margin:0;padding:20px;line-height:1.5}}
  .wrap{{max-width:1100px;margin:0 auto}}
  h1{{margin:0 0 6px;font-size:28px}}
  .sub{{color:var(--muted);font-size:14px;margin-bottom:24px}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:18px}}
  .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}}
  .stat{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px}}
  .stat-val{{font-size:22px;font-weight:700;line-height:1.1}}
  .stat-lbl{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.3px;margin-top:4px}}
  .notice{{background:var(--surface);border-left:3px solid var(--accent);padding:12px 16px;border-radius:4px;font-size:13px;color:var(--muted);margin-bottom:18px}}
  .notice strong{{color:var(--text)}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{text-align:left;padding:10px 8px;border-bottom:2px solid var(--border);color:var(--muted);font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:0.3px}}
  td{{padding:10px 8px;border-bottom:1px solid var(--border);vertical-align:top}}
  tr:hover td{{background:rgba(255,255,255,0.02)}}
  .tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.3px;margin-right:4px}}
  .tag-hawkish{{background:rgba(239,68,68,0.15);color:var(--hawkish);border:1px solid rgba(239,68,68,0.3)}}
  .tag-liberal_zionist{{background:rgba(124,58,237,0.15);color:var(--liberal);border:1px solid rgba(124,58,237,0.3)}}
  .tag-christian_zionist{{background:rgba(245,158,11,0.15);color:var(--christian);border:1px solid rgba(245,158,11,0.3)}}
  .donor-name{{font-weight:600;color:var(--text)}}
  .donor-meta{{color:var(--muted);font-size:11px;margin-top:2px}}
  .amount{{color:var(--accent);font-weight:600;text-align:right}}
  .pi-list{{font-size:11px;color:var(--muted)}}
  .cat-breakdown{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:16px}}
  .cat-block{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px;border-left:4px solid}}
  .cat-block h4{{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:0.3px}}
  .cat-block .num{{font-size:22px;font-weight:700}}
  .cat-block .lbl{{font-size:11px;color:var(--muted);margin-top:4px}}
  .committee-list{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px;font-size:12px}}
  .committee-list table{{margin:0}}
  .committee-list td, .committee-list th{{padding:4px 8px;font-size:11px}}
  .zero{{color:var(--muted)}}
  footer{{text-align:center;color:var(--muted);font-size:11px;margin-top:40px;padding:20px 0;border-top:1px solid var(--border)}}
  @media (max-width: 700px){{
    body{{padding:12px}}
    h1{{font-size:22px}}
    .stat-val{{font-size:18px}}
    th,td{{padding:6px 4px}}
    .donor-meta{{font-size:10px}}
  }}
</style>
</head>
<body>
<div class="wrap">

<h1>Mike Siegel — Pro-Israel PAC Donor Cross-Reference</h1>
<div class="sub">Individual donors who gave to Mike Siegel's congressional campaigns AND donated to pro-Israel political committees at the federal level.</div>

<div class="notice">
<strong>What this shows.</strong> This report cross-references Mike Siegel's FEC-reported individual donors with donors to 13 pro-Israel political committees across the spectrum (AIPAC-aligned, liberal Zionist, Christian Zionist).
Matches are by donor name + ZIP code. Source: Federal Election Commission Schedule A data.
<strong>This does not mean any PAC donated directly to Siegel</strong> — it shows overlap between Siegel's individual donor base and the individual donor bases of pro-Israel committees.
</div>

<div class="stats">
  <div class="stat"><div class="stat-val">{data['total_siegel_records_scanned']:,}</div><div class="stat-lbl">Siegel contribution records</div></div>
  <div class="stat"><div class="stat-val">{data['unique_siegel_donors_scanned']:,}</div><div class="stat-lbl">Unique Siegel donors</div></div>
  <div class="stat"><div class="stat-val">{len(donors_list)}</div><div class="stat-lbl">Matched with Pro-Israel PACs</div></div>
  <div class="stat"><div class="stat-val">{fmt(total_siegel_amount)}</div><div class="stat-lbl">From matched donors (to Siegel)</div></div>
</div>

<div class="card">
  <h3 style="margin-top:0">Category Breakdown</h3>
  <div class="cat-breakdown">
"""

for cat_key in ["hawkish", "liberal_zionist", "christian_zionist"]:
    totals = cat_totals.get(cat_key, {"donors": 0, "siegel_amount": 0, "pi_amount": 0})
    color = CAT_COLORS[cat_key]
    html_output += f"""
    <div class="cat-block" style="border-left-color:{color}">
      <h4 style="color:{color}">{CAT_LABELS[cat_key]}</h4>
      <div class="num">{totals['donors']} donors</div>
      <div class="lbl">{fmt(totals['siegel_amount'])} to Siegel &middot; {fmt(totals['pi_amount'])} to pro-Israel PACs</div>
    </div>
"""

html_output += """
  </div>
</div>

<div class="card">
  <h3 style="margin-top:0">Per-Committee Scan Results</h3>
  <div class="committee-list">
  <table>
    <thead><tr><th>Pro-Israel Committee</th><th style="text-align:right">Donors Scanned</th><th style="text-align:right">Matches with Siegel Donors</th></tr></thead>
    <tbody>
"""

# Sort committees: matches desc
comm_sorted = sorted(
    data['pi_committee_stats'].items(),
    key=lambda x: -x[1]['matches']
)
for cid, stats in comm_sorted:
    match_class = '' if stats['matches'] > 0 else 'class="zero"'
    html_output += f'      <tr><td>{esc(stats["label"])}</td><td style="text-align:right"><span {match_class}>{stats["donors_scanned"]:,}</span></td><td style="text-align:right"><strong>{stats["matches"]}</strong></td></tr>\n'

html_output += """
    </tbody>
  </table>
  </div>
</div>

<div class="card">
  <h3 style="margin-top:0">Matched Donors — Sorted by Amount Given to Siegel</h3>
  <div style="overflow-x:auto">
  <table>
    <thead>
      <tr>
        <th>Donor</th>
        <th style="text-align:right">To Siegel</th>
        <th style="text-align:right">To Pro-Israel PACs</th>
        <th>Categories / Committees</th>
      </tr>
    </thead>
    <tbody>
"""

for d in donors_list:
    pi_total = sum(c["amount"] for c in d["pi_committees"].values())
    pi_comm_names = []
    categories = set()
    for comm_name, c in d["pi_committees"].items():
        cat = c["category"]
        categories.add(cat)
        pi_comm_names.append(f'{esc(comm_name)} ({fmt(c["amount"])})')

    cat_tags = "".join(
        f'<span class="tag tag-{c}">{CAT_LABELS[c].split("(")[0].strip()}</span>' for c in sorted(categories)
    )

    html_output += f"""
      <tr>
        <td>
          <div class="donor-name">{esc(d['name'])}</div>
          <div class="donor-meta">{esc(d['city'])}, {esc(d['state'])} {esc(d['zip'][:5] if d['zip'] else '')}</div>
          <div class="donor-meta">{esc(d['employer'])}{' · ' + esc(d['occupation']) if d['occupation'] else ''}</div>
        </td>
        <td class="amount">{fmt(d['siegel_total'])}<div class="donor-meta" style="color:var(--muted);font-size:10px">{d['siegel_gifts']} gifts</div></td>
        <td class="amount">{fmt(pi_total)}</td>
        <td>{cat_tags}<div class="pi-list" style="margin-top:4px">{' &middot; '.join(pi_comm_names)}</div></td>
      </tr>
"""

html_output += f"""
    </tbody>
  </table>
  </div>
</div>

<div class="card">
  <h3 style="margin-top:0">Methodology</h3>
  <p style="color:var(--muted);font-size:13px;line-height:1.6">
    <strong>Data source:</strong> Federal Election Commission (FEC) Schedule A individual contribution records, accessed via <a href="https://api.open.fec.gov" style="color:var(--accent)">api.open.fec.gov</a>.
  </p>
  <p style="color:var(--muted);font-size:13px;line-height:1.6">
    <strong>Committees scanned:</strong> Mike Siegel for Congress (C00662668) and Mike Siegel Victory Fund (C00753517) on the Siegel side. On the pro-Israel side: AIPAC PAC, United Democracy Project, Pro-Israel America PAC, DMFI PAC, NORPAC, Republican Jewish Coalition PAC, American Pro-Israel PAC, ZOA PAC, Friends of Israel PAC, J Street PAC, Bend the Arc Jewish Action PAC, National Jewish Democratic Council PAC, and CUFI Action Fund.
  </p>
  <p style="color:var(--muted);font-size:13px;line-height:1.6">
    <strong>Matching:</strong> Donors are matched by normalized last name + first-name initial + ZIP5. This is a conservative join that may miss some true matches (name variants) but avoids most false positives. A donor is counted once per committee even if they made multiple gifts.
  </p>
  <p style="color:var(--muted);font-size:13px;line-height:1.6">
    <strong>Coverage note:</strong> We scanned up to 5,000 most-recent donors per pro-Israel committee. Some committees (AIPAC PAC at 30K+, NORPAC at 17K+, J Street PAC at 87K+) have more donors than were scanned, so this is a floor, not a ceiling. Zero-match results for those committees are therefore indicative but not exhaustive.
  </p>
  <p style="color:var(--muted);font-size:13px;line-height:1.6">
    <strong>What this does NOT show:</strong> Any direct PAC-to-Siegel contributions (pro-Israel PACs typically don't give to progressive Democratic challengers). This report tracks overlap in individual donor bases, which is how "bundled" giving patterns become visible.
  </p>
</div>

<footer>
  Generated from public FEC data &middot; Mike Siegel cross-reference &middot; Austin Finance Transparency Project
</footer>

</div>
</body>
</html>
"""

with open("siegel.html", "w", encoding="utf-8") as f:
    f.write(html_output)

print(f"Wrote siegel.html ({len(html_output):,} chars)")
print(f"  {len(donors_list)} unique matched donors")
print(f"  Total Siegel $ from matched donors: {fmt(total_siegel_amount)}")
