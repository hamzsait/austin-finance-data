import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
html = open('profile_qadri.html', encoding='utf-8').read()

# 1. CSS for sort buttons
SORT_CSS = """
  .sort-bar { display:flex; gap:6px; margin-bottom:10px; }
  .sort-btn {
    padding:3px 10px; font-size:11px; border-radius:4px; cursor:pointer;
    border:1px solid var(--border); background:var(--surface2); color:var(--muted);
    transition:all 0.15s;
  }
  .sort-btn.active { background:var(--accent); color:#fff; border-color:var(--accent); }
"""
html = html.replace('</style>', SORT_CSS + '</style>', 1)
print('OK: CSS injected')

# 2. Sort controls above igBars
old = '<div id="igBars"></div>'
new = """<div class="sort-bar">
      <span style="font-size:11px;color:var(--muted);align-self:center;margin-right:4px">Sort:</span>
      <button class="sort-btn active" onclick="renderBars('total',this)">Amount</button>
      <button class="sort-btn" onclick="renderBars('donors',this)">Donors</button>
      <button class="sort-btn" onclick="renderBars('label',this)">A\u2013Z</button>
    </div>
    <div id="igBars"></div>"""
if old in html:
    html = html.replace(old, new, 1)
    print('OK: sort controls injected')
else:
    print('MISS: igBars div')

# 3. Replace the IIFE with a named reusable renderBars function
old_start = '// \u2500\u2500 Interest group bars \u2500'
old_end = '  });\n})();'

start_idx = html.find(old_start)
end_idx = html.find(old_end, start_idx) + len(old_end)

if start_idx != -1 and end_idx > start_idx:
    NEW_RENDERER = """// \u2500\u2500 Interest group bars \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
function renderBars(sortKey, btnEl) {
  if (btnEl) {
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
    btnEl.classList.add('active');
  }
  const el = document.getElementById('igBars');
  el.innerHTML = '';
  const sorted = [...INTEREST_GROUPS].sort((a, b) => {
    if (sortKey === 'label')  return a.label.localeCompare(b.label);
    if (sortKey === 'donors') return b.donors - a.donors;
    return b.total - a.total;
  });
  const maxTotal = Math.max(...INTEREST_GROUPS.map(g => g.total));
  sorted.forEach(g => {
    const pct = (g.total / maxTotal * 100).toFixed(1);
    const row = document.createElement('div');
    row.className = 'ig-row';
    row.title = 'Click to see individual donations';
    row.innerHTML =
      '<div class="ig-label" title="' + g.label + '">' + g.label + '</div>' +
      '<div class="ig-bar-wrap"><div class="ig-bar" style="width:' + pct + '%;background:' + g.color + '"></div></div>' +
      '<div class="ig-amount" style="color:' + (g.label === 'Unknown / Unclassified' ? 'var(--muted)' : g.color) + '">' + fmt(g.total) + '</div>' +
      '<div class="ig-donors">' + g.donors + ' donors</div>';
    row.onclick = () => openDrawer(makeFilter(g.label), g.label, g.color);
    el.appendChild(row);
  });
}
renderBars('total');"""
    html = html[:start_idx] + NEW_RENDERER + html[end_idx:]
    print('OK: renderer refactored to renderBars()')
else:
    print(f'MISS: renderer block (start={start_idx}, end={end_idx})')

open('profile_qadri.html', 'w', encoding='utf-8').write(html)
print(f'Saved: {len(html.encode())//1024} KB')
