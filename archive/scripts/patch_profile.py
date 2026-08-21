"""
Patch profile_qadri.html to add:
 1. Drawer CSS
 2. Drawer HTML (overlay panel)
 3. ALL_DONATIONS embedded data
 4. Drawer open/close/render JS
 5. Click handlers on bars, donut, firms, top-donors
"""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

html = open("profile_qadri.html", encoding="utf-8").read()
donations_json = open("qadri_all_donations.json", encoding="utf-8").read()

# ── 1. CSS to inject before </style> ─────────────────────────────────────────
DRAWER_CSS = """
  /* ── Clickable rows ── */
  .ig-row { cursor: pointer; border-radius: 4px; transition: background 0.12s; }
  .ig-row:hover { background: var(--surface2); }
  .year-col { cursor: pointer; }
  .year-col:hover .year-bar { filter: brightness(1.15); }
  .firm-row { cursor: pointer; }
  .firm-row:hover { background: var(--surface2); border-radius: 4px; }
  tr.clickable-row { cursor: pointer; }
  tr.clickable-row:hover td { background: rgba(79,142,247,0.06) !important; }

  /* ── Drawer backdrop ── */
  .drawer-backdrop {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.55); z-index: 200;
    animation: fadeIn 0.2s ease;
  }
  .drawer-backdrop.open { display: block; }

  /* ── Drawer panel ── */
  .drawer {
    position: fixed; top: 0; right: 0;
    width: min(700px, 96vw); height: 100vh;
    background: var(--surface);
    border-left: 1px solid var(--border);
    z-index: 201;
    transform: translateX(100%);
    transition: transform 0.22s cubic-bezier(.4,0,.2,1);
    display: flex; flex-direction: column;
  }
  .drawer.open { transform: translateX(0); }

  .drawer-header {
    padding: 18px 22px 14px;
    border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: flex-start;
    flex-shrink: 0; gap: 12px;
  }
  .drawer-title { font-size: 16px; font-weight: 700; }
  .drawer-sub { font-size: 12px; color: var(--muted); margin-top: 3px; }
  .drawer-close {
    background: none; border: 1px solid var(--border); color: var(--muted);
    width: 30px; height: 30px; border-radius: 5px; cursor: pointer;
    font-size: 18px; line-height: 1; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    transition: color 0.1s, border-color 0.1s;
  }
  .drawer-close:hover { color: var(--text); border-color: var(--text); }

  .drawer-controls {
    padding: 10px 22px; border-bottom: 1px solid var(--border);
    display: flex; gap: 8px; flex-shrink: 0;
  }
  .drawer-search {
    flex: 1; background: var(--surface2); border: 1px solid var(--border);
    border-radius: 6px; padding: 7px 11px; color: var(--text); font-size: 13px;
  }
  .drawer-search::placeholder { color: var(--muted); }
  .drawer-search:focus { outline: none; border-color: var(--accent); }

  .drawer-sort-sel {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 6px; padding: 7px 10px; color: var(--text);
    font-size: 13px; cursor: pointer; min-width: 140px;
  }
  .drawer-sort-sel:focus { outline: none; }

  .drawer-body { overflow-y: auto; flex: 1; }

  .dtable {
    width: 100%; border-collapse: collapse; font-size: 13px;
  }
  .dtable thead th {
    position: sticky; top: 0;
    background: var(--surface2);
    padding: 8px 14px; text-align: left;
    font-weight: 600; color: var(--muted);
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px;
    border-bottom: 1px solid var(--border);
    user-select: none; white-space: nowrap;
  }
  .dtable tbody td {
    padding: 8px 14px;
    border-bottom: 1px solid rgba(46,51,71,0.5);
    vertical-align: top;
  }
  .dtable tbody tr:hover td { background: var(--surface2); }
  .dtable .td-name { font-weight: 500; }
  .dtable .td-emp { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .dtable .td-date { color: var(--muted); font-size: 12px; white-space: nowrap; }
  .dtable .td-amt { font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; text-align: right; }
  .dtable .td-loc { color: var(--muted); font-size: 11px; max-width: 130px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dtable th:nth-child(2), .dtable td:nth-child(2) { text-align: right; }
  .dtable .sort-active { color: var(--text); }
  .dtable .sort-active::after { color: var(--accent); font-size: 10px; margin-left: 2px; }
  .dtable .sort-asc::after { content: '↑'; }
  .dtable .sort-desc::after { content: '↓'; }

  .drawer-footer {
    padding: 9px 22px; border-top: 1px solid var(--border);
    font-size: 12px; color: var(--muted); flex-shrink: 0;
    display: flex; justify-content: space-between; align-items: center;
  }
  .drawer-footer strong { color: var(--text); }

  @keyframes fadeIn { from { opacity:0 } to { opacity:1 } }
"""

# ── 2. Drawer HTML to inject before </body> ───────────────────────────────────
DRAWER_HTML = """
<div class="drawer-backdrop" id="drawerBackdrop" onclick="closeDrawer()"></div>
<div class="drawer" id="drawer">
  <div class="drawer-header">
    <div>
      <div class="drawer-title" id="drawerTitle"></div>
      <div class="drawer-sub" id="drawerSub"></div>
    </div>
    <button class="drawer-close" onclick="closeDrawer()">&#x2715;</button>
  </div>
  <div class="drawer-controls">
    <input class="drawer-search" id="drawerSearch" type="text" placeholder="Search donor, employer, city…" />
    <select class="drawer-sort-sel" id="drawerSortSel">
      <option value="1-desc">Date (newest)</option>
      <option value="1-asc">Date (oldest)</option>
      <option value="2-desc">Amount (highest)</option>
      <option value="2-asc">Amount (lowest)</option>
      <option value="0-asc">Donor (A→Z)</option>
      <option value="3-asc">Employer (A→Z)</option>
    </select>
  </div>
  <div class="drawer-body">
    <table class="dtable">
      <thead>
        <tr>
          <th>Donor / Employer</th>
          <th style="text-align:right">Amount</th>
          <th>Date</th>
          <th>Location</th>
        </tr>
      </thead>
      <tbody id="drawerTbody"></tbody>
    </table>
  </div>
  <div class="drawer-footer">
    <span id="drawerCount"></span>
    <span id="drawerTotal"></span>
  </div>
</div>
"""

# ── 3. JS to inject – data + drawer logic ─────────────────────────────────────
DRAWER_JS = f"""
// ── All donations: [donor, date, amt, employer, industry, location] ───────────
const ALL_DONATIONS = {donations_json};

const OTHER_INDS = new Set(['Retail','Media','Architecture','Transportation','Entertainment','Labor']);

function industryColor(ind) {{
  const g = INTEREST_GROUPS.find(x => x.label === ind) ||
            (OTHER_INDS.has(ind) ? INTEREST_GROUPS.find(x => x.label === 'Retail / Media / Other') : null);
  return g ? g.color : '#4b5563';
}}

function makeFilter(label) {{
  if (label === 'Retail / Media / Other') return d => OTHER_INDS.has(d[4]);
  return d => d[4] === label;
}}

// ── Drawer state ──────────────────────────────────────────────────────────────
let _drawerData = [];
let _sortCol = 1, _sortAsc = false, _query = '';

function openDrawer(filterFn, title, color) {{
  _drawerData = ALL_DONATIONS.filter(filterFn);
  _sortCol = 1; _sortAsc = false; _query = '';

  const total = _drawerData.reduce((s, d) => s + (d[2] || 0), 0);
  const titleEl = document.getElementById('drawerTitle');
  titleEl.textContent = title;
  titleEl.style.color = color || 'var(--text)';
  document.getElementById('drawerSub').textContent =
    _drawerData.length.toLocaleString() + ' contributions · ' + fmt(total) + ' total';

  document.getElementById('drawerSearch').value = '';
  document.getElementById('drawerSortSel').value = '1-desc';
  _renderDrawer();

  document.getElementById('drawer').classList.add('open');
  document.getElementById('drawerBackdrop').classList.add('open');
  document.body.style.overflow = 'hidden';
}}

function closeDrawer() {{
  document.getElementById('drawer').classList.remove('open');
  document.getElementById('drawerBackdrop').classList.remove('open');
  document.body.style.overflow = '';
}}

function _renderDrawer() {{
  const q = _query.toLowerCase();
  let rows = q
    ? _drawerData.filter(d =>
        (d[0]||'').toLowerCase().includes(q) ||
        (d[3]||'').toLowerCase().includes(q) ||
        (d[5]||'').toLowerCase().includes(q))
    : _drawerData;

  rows = [...rows].sort((a, b) => {{
    let va = a[_sortCol] ?? '', vb = b[_sortCol] ?? '';
    if (typeof va === 'string') {{ va = va.toLowerCase(); vb = (vb+'').toLowerCase(); }}
    if (va < vb) return _sortAsc ? -1 : 1;
    if (va > vb) return _sortAsc ? 1 : -1;
    return 0;
  }});

  const tbody = document.getElementById('drawerTbody');
  tbody.innerHTML = '';
  rows.forEach(d => {{
    const color = industryColor(d[4]);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div class="td-name">${{d[0] || ''}}</div>
        ${{d[3] ? `<div class="td-emp">${{d[3]}}</div>` : ''}}
      </td>
      <td><span class="td-amt" style="color:${{color}}">${{fmt(d[2])}}</span></td>
      <td class="td-date">${{(d[1]||'').slice(0,10)}}</td>
      <td class="td-loc" title="${{d[5]||''}}">${{d[5]||''}}</td>
    `;
    tbody.appendChild(tr);
  }});

  const shown = rows.length;
  const shownTotal = rows.reduce((s, d) => s + (d[2] || 0), 0);
  document.getElementById('drawerCount').innerHTML =
    q ? `<strong>${{shown.toLocaleString()}}</strong> of ${{_drawerData.length.toLocaleString()}} shown`
      : `<strong>${{shown.toLocaleString()}}</strong> contributions`;
  document.getElementById('drawerTotal').innerHTML =
    `Total: <strong>${{fmt(shownTotal)}}</strong>`;
}}

document.getElementById('drawerSearch').addEventListener('input', e => {{
  _query = e.target.value; _renderDrawer();
}});

document.getElementById('drawerSortSel').addEventListener('change', e => {{
  const [col, dir] = e.target.value.split('-');
  _sortCol = +col; _sortAsc = dir === 'asc'; _renderDrawer();
}});

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeDrawer(); }});
"""

# ── 4. Modify year bars forEach to add click ──────────────────────────────────
OLD_YEAR_BARS = "    const bar = document.createElement('div');\n    bar.className = 'year-bar' + (isActive ? ' active' : '');\n    bar.style.height = pct;\n    bar.title = `${d.year}: ${d.count} donations · ${fmt(d.total)}`;"
NEW_YEAR_BARS = """    const bar = document.createElement('div');
    bar.className = 'year-bar' + (isActive ? ' active' : '');
    bar.style.height = pct;
    bar.title = `${d.year}: ${d.count} donations · ${fmt(d.total)}`;
    col.onclick = () => openDrawer(don => don[1] && don[1].startsWith(d.year), `${d.year} Donations`, '#4f8ef7');"""

# ── 5. Modify donut to add onClick ────────────────────────────────────────────
OLD_DONUT = """      cutout: '68%',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const g = classified[ctx.dataIndex];
              const total = classified.reduce((s,x)=>s+x.total,0);
              const pct = (g.total/total*100).toFixed(1);
              return ` ${fmt(g.total)} (${pct}%) · ${g.donors} donors`;
            }
          }
        }
      }"""
NEW_DONUT = """      cutout: '68%',
      onClick: (evt, elements) => {
        if (!elements.length) return;
        const g = classified[elements[0].index];
        openDrawer(makeFilter(g.label), g.label, g.color);
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const g = classified[ctx.dataIndex];
              const total = classified.reduce((s,x)=>s+x.total,0);
              const pct = (g.total/total*100).toFixed(1);
              return ` ${fmt(g.total)} (${pct}%) · ${g.donors} records`;
            }
          }
        }
      }"""

# ── 6. Modify ig-row to add click + cursor hint ───────────────────────────────
OLD_IG_ROW = """    const row = document.createElement('div');
    row.className = 'ig-row';
    row.innerHTML = `
      <div class="ig-label" title="${g.label}">${g.label}</div>
      <div class="ig-bar-wrap">
        <div class="ig-bar" style="width:${pct}%;background:${g.color}"></div>
      </div>
      <div class="ig-amount" style="color:${g.label==='Unknown / Unclassified'?'var(--muted)':g.color}">${fmt(g.total)}</div>
      <div class="ig-donors">${g.donors} donors</div>
    `;
    el.appendChild(row);"""
NEW_IG_ROW = """    const row = document.createElement('div');
    row.className = 'ig-row';
    row.title = 'Click to see individual donations';
    row.innerHTML = `
      <div class="ig-label" title="${g.label}">${g.label}</div>
      <div class="ig-bar-wrap">
        <div class="ig-bar" style="width:${pct}%;background:${g.color}"></div>
      </div>
      <div class="ig-amount" style="color:${g.label==='Unknown / Unclassified'?'var(--muted)':g.color}">${fmt(g.total)}</div>
      <div class="ig-donors">${g.donors} records</div>
    `;
    row.onclick = () => openDrawer(makeFilter(g.label), g.label, g.color);
    el.appendChild(row);"""

# ── 7. Modify firm rows to add click ──────────────────────────────────────────
OLD_FIRM = """    row.className = 'firm-row';
    row.innerHTML = `"""
NEW_FIRM = """    row.className = 'firm-row';
    row.title = 'Click to see donations from this firm';
    row.onclick = () => openDrawer(d => d[3] === f.firm, f.firm, firmColor(f));
    row.innerHTML = `"""

# ── 8. Modify top-donor rows to add click ─────────────────────────────────────
OLD_DONOR_ROW = """    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div class="donor-name">${d.name}</div>
        ${d.employer ? `<div class="donor-employer">${d.employer}${tl ? ` · <span style="color:${tagColor(d.tags)}">${tl}</span>` : ''}</div>` : ''}
      </td>
      <td class="amount-cell">${fmt(d.total)}</td>
      <td class="count-cell">${d.count}×</td>
    `;
    tbody.appendChild(tr);"""
NEW_DONOR_ROW = """    const tr = document.createElement('tr');
    tr.className = 'clickable-row';
    tr.title = 'Click to see all donations from this person';
    tr.onclick = () => openDrawer(don => don[0] === d.name, d.name, '#4f8ef7');
    tr.innerHTML = `
      <td>
        <div class="donor-name">${d.name}</div>
        ${d.employer ? `<div class="donor-employer">${d.employer}${tl ? ` · <span style="color:${tagColor(d.tags)}">${tl}</span>` : ''}</div>` : ''}
      </td>
      <td class="amount-cell">${fmt(d.total)}</td>
      <td class="count-cell">${d.count}×</td>
    `;
    tbody.appendChild(tr);"""

# ── Apply all patches ──────────────────────────────────────────────────────────
errors = []
patches = [
    ("CSS injection",    "</style>",          DRAWER_CSS + "\n</style>"),
    ("Drawer HTML",      "</body>",            DRAWER_HTML + "\n</body>"),
    ("Year bar click",   OLD_YEAR_BARS,        NEW_YEAR_BARS),
    ("Donut onClick",    OLD_DONUT,            NEW_DONUT),
    ("IG row click",     OLD_IG_ROW,           NEW_IG_ROW),
    ("Firm row click",   OLD_FIRM,             NEW_FIRM),
    ("Donor row click",  OLD_DONOR_ROW,        NEW_DONOR_ROW),
]

for name, old, new in patches:
    if old not in html:
        errors.append(f"NOT FOUND: {name}")
        print(f"  SKIP (not found): {name}", file=sys.stderr)
    else:
        html = html.replace(old, new, 1)
        print(f"  OK: {name}", file=sys.stderr)

# Inject JS data + drawer functions before </script>
SCRIPT_CLOSE = "</script>\n</body>"
if SCRIPT_CLOSE in html:
    html = html.replace(SCRIPT_CLOSE, DRAWER_JS + "\n</script>\n</body>", 1)
    print("  OK: Drawer JS injected", file=sys.stderr)
else:
    errors.append("</script> close not found")

if errors:
    print("ERRORS:", errors, file=sys.stderr)

with open("profile_qadri.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Done. File size:", len(html.encode('utf-8'))//1024, "KB", file=sys.stderr)
