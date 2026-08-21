// Refresh austin_landing.json: recompute raised/donors/empPct/topGroups for
// every live slug from its fresh {slug}_data.json; add morales; set gomez race.
const fs = require('fs');
const ROOT = 'C:/Users/Hamza Sait/Electoral/austin-finance-data/';
const landing = JSON.parse(fs.readFileSync(ROOT + 'austin_landing.json', 'utf8'));

function money(n) {
  if (n >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return '$' + Math.round(n / 1e3) + 'K';
  return '$' + Math.round(n);
}

const NEW = {
  morales: { slug: 'morales', photo: 'tc-morales', name: 'George Morales III',
             district: 'Commissioner Pct 4', race: 'Travis County', href: '/austin/morales/' },
};
for (const c of Object.values(NEW)) {
  if (!landing.candidates.some(x => x.slug === c.slug)) landing.candidates.push(c);
}
// order: morales before gomez in county block
const gi = landing.candidates.findIndex(c => c.slug === 'gomez');
const mi = landing.candidates.findIndex(c => c.slug === 'morales');
if (gi >= 0 && mi > gi) {
  const [m] = landing.candidates.splice(mi, 1);
  landing.candidates.splice(gi, 0, m);
}

for (const c of landing.candidates) {
  const path = ROOT + c.slug + '_data.json';
  if (!fs.existsSync(path)) { console.log('skip (no data json):', c.slug); continue; }
  const d = JSON.parse(fs.readFileSync(path, 'utf8'));
  c.raised = money(d.hero.total_raised);
  c.donors = d.hero.unique_donors.toLocaleString('en-US');
  c.empPct = d.hero.employer_affiliated_pct + '%';
  const groups = (d.interest_groups || []).filter(g => !/^unknown$/i.test(g.label)).slice(0, 4);
  const max = Math.max(...groups.map(g => g.total), 1);
  c.topGroups = groups.map(g => ({ label: g.label, amt: money(g.total),
                                   w: Math.max(8, Math.round(100 * g.total / max)) }));
}
const gz = landing.candidates.find(c => c.slug === 'gomez');
if (gz) gz.race = 'Retired June 2026';

landing.updated = new Date().toISOString().slice(0, 10);
fs.writeFileSync(ROOT + 'austin_landing.json', JSON.stringify(landing, null, 1));

let raised = 0, donors = 0;
for (const c of landing.candidates) {
  const r = c.raised.replace('$', '');
  raised += r.endsWith('M') ? parseFloat(r) * 1e6 : parseFloat(r) * 1e3;
  donors += parseInt(c.donors.replace(/,/g, ''));
}
console.log('candidates:', landing.candidates.length,
            '| site raised ~' + money(raised), '| donor rows', donors.toLocaleString());
const m = landing.candidates.find(c => c.slug === 'morales');
console.log('morales:', JSON.stringify(m));
