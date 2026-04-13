"""Build pro-Israel donor cross-reference page for Jose Velasquez (Austin D3)."""
import sqlite3, json, html
from collections import defaultdict

c = sqlite3.connect('austin_finance.db', timeout=10)
cur = c.cursor()

RECIPIENT = 'Velasquez, Jose'
SLUG = 'velasquez'

# Get total stats
cur.execute(f'''
    SELECT COUNT(DISTINCT di.canonical_name), SUM(CAST(cf.contribution_amount AS REAL))
    FROM donor_identities di JOIN campaign_finance cf ON cf.donor_id=di.donor_id
    WHERE cf.recipient=? AND cf.correction!='X'
''', (RECIPIENT,))
total_donors, total_raised = cur.fetchone()

# Get donors with IP spectrum (FEC pro-Israel PAC giving)
cur.execute('''
    SELECT di.canonical_name, di.ip_spectrum, di.ip_total, di.ip_committees,
           SUM(CAST(cf.contribution_amount AS REAL)) as local_total,
           MAX(cf.city_state_zip) as loc
    FROM donor_identities di
    JOIN campaign_finance cf ON cf.donor_id=di.donor_id
    WHERE cf.recipient=? AND cf.correction!='X' AND di.ip_spectrum IS NOT NULL
    GROUP BY di.canonical_name ORDER BY local_total DESC
''', (RECIPIENT,))
ip_donors = cur.fetchall()

# Get committee names for display
comm_names = {}
cur.execute("SELECT committee_id, committee_name, ip_category FROM fec_committee_cache WHERE ip_category IS NOT NULL")
for r in cur.fetchall():
    comm_names[r[0]] = (r[1], r[2])

# Get donors with civic affiliations
cur.execute('''
    SELECT ca.canonical_name, ca.organization, ca.role, ca.category, ca.source_url,
           SUM(CAST(cf.contribution_amount AS REAL)) as local_total
    FROM civic_affiliations ca
    JOIN donor_identities di ON di.canonical_name=ca.canonical_name
    JOIN campaign_finance cf ON cf.donor_id=di.donor_id
    WHERE cf.recipient=? AND cf.correction!='X'
      AND ca.category IN ('jewish_civic','pro_israel','liberal_zionist','aipac_direct','adl','zionist_peace','oil_gas_major','oil_gas_independent','oil_gas_services','oil_gas_legal','oil_gas_industry_association','oil_gas_academic')
    GROUP BY ca.canonical_name, ca.organization
    ORDER BY local_total DESC
''', (RECIPIENT,))
civic_rows = cur.fetchall()

# Group civic by person
civic_by_person = defaultdict(lambda: {"orgs": [], "total": 0})
for r in civic_rows:
    name = r[0]
    civic_by_person[name]["orgs"].append({"org": r[1], "role": r[2], "category": r[3], "source": r[4]})
    civic_by_person[name]["total"] = r[5]

# FEC partisan lean
cur.execute('''
    SELECT COUNT(DISTINCT CASE WHEN di.fec_partisan_lean>=0.6 THEN di.donor_id END),
           COUNT(DISTINCT CASE WHEN di.fec_partisan_lean<=0.4 THEN di.donor_id END),
           COUNT(DISTINCT CASE WHEN di.fec_partisan_lean>0.4 AND di.fec_partisan_lean<0.6 THEN di.donor_id END),
           COUNT(DISTINCT CASE WHEN di.fec_partisan_lean IS NOT NULL THEN di.donor_id END)
    FROM donor_identities di JOIN campaign_finance cf ON cf.donor_id=di.donor_id
    WHERE cf.recipient=? AND cf.correction!='X'
''', (RECIPIENT,))
dem, rep, mixed, total_lean = cur.fetchone()

c.close()

def fmt(n): return f"${n:,.0f}"
def esc(s): return html.escape(str(s or ""))

CAT_COLORS = {"hawkish_proisrael":"#ef4444","liberal_zionist":"#7c3aed","pro_palestine":"#059669",
              "jewish_civic":"#60a5fa","pro_israel":"#ef4444","aipac_direct":"#ef4444","adl":"#60a5fa",
              "oil_gas_major":"#f59e0b","oil_gas_independent":"#f59e0b","oil_gas_services":"#f59e0b",
              "oil_gas_legal":"#f59e0b","oil_gas_industry_association":"#f59e0b","oil_gas_academic":"#f59e0b"}
CAT_LABELS = {"hawkish_proisrael":"Pro-Israel (AIPAC-aligned)","liberal_zionist":"Liberal Zionist",
              "jewish_civic":"Jewish Civic","pro_israel":"Pro-Israel","aipac_direct":"AIPAC Direct",
              "oil_gas_major":"Oil & Gas","oil_gas_independent":"Oil & Gas","oil_gas_services":"Oil & Gas",
              "oil_gas_legal":"Oil & Gas Legal","oil_gas_industry_association":"Oil & Gas Industry",
              "oil_gas_academic":"Oil & Gas Academic"}

# Count categories
jewish_civic_count = len(set(r[0] for r in civic_rows if r[3] in ('jewish_civic','pro_israel','liberal_zionist','aipac_direct','adl','zionist_peace')))
oil_count = len(set(r[0] for r in civic_rows if 'oil_gas' in (r[3] or '')))
ip_hawkish = [d for d in ip_donors if d[1]=='hawkish_proisrael']
ip_liberal = [d for d in ip_donors if d[1]=='liberal_zionist']

page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Jose Velasquez (D3) — Pro-Israel &amp; Industry Donor Profile</title>
<style>
:root{{--bg:#0b1120;--card:#131c2e;--surface:#1a2438;--border:#2a3449;--text:#e5e7eb;--muted:#94a3b8;--accent:#60a5fa}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;margin:0;padding:20px;line-height:1.5}}
.wrap{{max-width:900px;margin:0 auto}}
h1{{margin:0 0 6px;font-size:26px}} h2{{margin:24px 0 12px;font-size:18px;color:var(--accent)}}
.sub{{color:var(--muted);font-size:14px;margin-bottom:20px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px;margin-bottom:16px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px}}
.stat{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px}}
.stat-val{{font-size:20px;font-weight:700}} .stat-lbl{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.3px;margin-top:3px}}
.notice{{background:var(--surface);border-left:3px solid var(--accent);padding:10px 14px;border-radius:4px;font-size:12px;color:var(--muted);margin-bottom:16px}}
.notice strong{{color:var(--text)}}
.donor-card{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px}}
.donor-name{{font-weight:600;font-size:14px}} .donor-meta{{color:var(--muted);font-size:11px;margin-top:2px}}
.org-list{{margin-top:8px;font-size:12px}}
.org-item{{padding:4px 0;border-top:1px solid var(--border)}}
.org-item:first-child{{border-top:none}}
.tag{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.3px;margin-right:4px}}
.tag-hawkish{{background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3)}}
.tag-liberal{{background:rgba(124,58,237,0.15);color:#7c3aed;border:1px solid rgba(124,58,237,0.3)}}
.tag-jewish{{background:rgba(96,165,250,0.15);color:#60a5fa;border:1px solid rgba(96,165,250,0.3)}}
.tag-oil{{background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.3)}}
a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
footer{{text-align:center;color:var(--muted);font-size:11px;margin-top:40px;padding:20px 0;border-top:1px solid var(--border)}}
@media(max-width:700px){{body{{padding:12px}}h1{{font-size:20px}}.stat-val{{font-size:16px}}}}
</style></head><body><div class="wrap">

<h1>Jose Velasquez (Austin District 3)</h1>
<div class="sub">Pro-Israel, Jewish Civic, and Oil &amp; Gas donor connections — based on FEC cross-reference and verified organizational affiliations.</div>

<div class="notice">
<strong>Methodology.</strong> This shows (1) Velasquez donors who also donated to pro-Israel PACs at the federal level (FEC Schedule A cross-reference), and (2) Velasquez donors with verified public board memberships or roles at Jewish civic / Israel advocacy / oil &amp; gas organizations. All data is from public FEC records and verified source-linked organizational roles.
</div>

<div class="stats">
  <div class="stat"><div class="stat-val">{total_donors:,}</div><div class="stat-lbl">Unique Donors</div></div>
  <div class="stat"><div class="stat-val">{fmt(total_raised)}</div><div class="stat-lbl">Total Raised</div></div>
  <div class="stat"><div class="stat-val">{len(ip_donors)}</div><div class="stat-lbl">Pro-Israel PAC Donors</div></div>
  <div class="stat"><div class="stat-val">{jewish_civic_count}</div><div class="stat-lbl">Jewish Civic Ties</div></div>
  <div class="stat"><div class="stat-val">{oil_count}</div><div class="stat-lbl">Oil &amp; Gas Ties</div></div>
</div>
"""

# Section 1: IP Spectrum (FEC PAC cross-reference)
if ip_donors:
    page += '<div class="card"><h2 style="margin-top:0">FEC Pro-Israel PAC Cross-Reference</h2>'
    page += '<p style="font-size:12px;color:var(--muted)">Velasquez donors who also donated to pro-Israel committees at the federal level.</p>'
    for d in ip_donors:
        name, spectrum, ip_total, ip_comms, local_total, loc = d
        tag_class = "hawkish" if "hawkish" in spectrum else "liberal"
        tag_label = "Pro-Israel Hawkish" if "hawkish" in spectrum else "Liberal Zionist"
        comms_display = []
        if ip_comms:
            for cid in ip_comms.split(","):
                cid = cid.strip()
                cn = comm_names.get(cid, (cid, ""))
                comms_display.append(cn[0])
        page += f'''<div class="donor-card">
          <div class="donor-name">{esc(name)} <span class="tag tag-{tag_class}">{tag_label}</span></div>
          <div class="donor-meta">{esc(loc)} &middot; {fmt(local_total)} to Velasquez &middot; {fmt(ip_total)} to pro-Israel PACs</div>
          <div class="donor-meta">Committees: {", ".join(comms_display)}</div>
        </div>'''
    page += '</div>'

# Section 2: Civic affiliations (Jewish civic + Oil)
if civic_by_person:
    page += '<div class="card"><h2 style="margin-top:0">Verified Organizational Affiliations</h2>'
    page += '<p style="font-size:12px;color:var(--muted)">Velasquez donors with verified public board memberships or roles at relevant organizations.</p>'

    for name, info in sorted(civic_by_person.items(), key=lambda x: -x[1]["total"]):
        page += f'<div class="donor-card"><div class="donor-name">{esc(name)}</div>'
        page += f'<div class="donor-meta">{fmt(info["total"])} to Velasquez</div>'
        page += '<div class="org-list">'
        for org in info["orgs"]:
            cat = org["category"] or ""
            if "oil_gas" in cat:
                tag = '<span class="tag tag-oil">Oil &amp; Gas</span>'
            elif cat in ("aipac_direct","pro_israel","hawkish_proisrael"):
                tag = '<span class="tag tag-hawkish">Pro-Israel</span>'
            elif cat == "liberal_zionist":
                tag = '<span class="tag tag-liberal">Liberal Zionist</span>'
            else:
                tag = '<span class="tag tag-jewish">Jewish Civic</span>'
            src = f' — <a href="{esc(org["source"])}" target="_blank">source</a>' if org["source"] and org["source"] != "Multiple sources" else ""
            page += f'<div class="org-item">{tag} <strong>{esc(org["org"])}</strong> — {esc(org["role"])}{src}</div>'
        page += '</div></div>'
    page += '</div>'

# Partisan lean
page += f'''<div class="card">
<h2 style="margin-top:0">FEC Partisan Lean</h2>
<p style="font-size:12px;color:var(--muted)">{total_lean} of {total_donors} donors matched in FEC records. D={dem}, R={rep}, M={mixed}.</p>
</div>'''

page += f'''
<footer>Generated from public FEC data and verified organizational records &middot; Austin Finance Transparency Project</footer>
</div></body></html>'''

with open(f"{SLUG}.html", "w", encoding="utf-8") as f:
    f.write(page)
print(f"Wrote {SLUG}.html ({len(page):,} chars)")
print(f"  IP donors: {len(ip_donors)}, Civic donors: {len(civic_by_person)}, Oil: {oil_count}")
