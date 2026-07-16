/* Extraction driver: run headless `claude -p` vision-extraction jobs over all
 * pending chunks with a parallel pool, retries, and JSON validation.
 * Progress lines go to stdout (one per completed chunk).
 * Re-runs _make_chunks.py each cycle to pick up newly rendered reports.
 */
const { spawn, execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const PY = 'C:\\Users\\Hamza Sait\\AppData\\Local\\Microsoft\\WindowsApps\\python3.13.exe';
const PAGES_ROOT = 'C:\\Users\\HAMZAS~1\\AppData\\Local\\Temp\\claude\\C--Users-Hamza-Sait-Electoral-austin-finance-data\\bca7901c-5f3c-4d08-a629-e850b78c00ac\\scratchpad\\pages';
const POOL = 4;
const JOB_TIMEOUT_MS = 12 * 60 * 1000;
const MAX_TRIES = 3;
const FAST_FAIL_S = 30;       // failure under this = infra problem, not content

// Global usage-limit pause: when jobs fast-fail, ALL workers wait together,
// then a cheap probe call must succeed before work resumes. Fast failures
// never count toward a chunk's MAX_TRIES.
let pausePromise = null;
const sleep = ms => new Promise(r => setTimeout(r, ms));
function probe() {
  return new Promise(resolve => {
    const child = spawn('claude', ['-p', '--model', 'sonnet'],
      { shell: true, stdio: ['pipe', 'pipe', 'pipe'] });
    const t = setTimeout(() => { try { child.kill(); } catch {} resolve(false); }, 120000);
    let out = '';
    child.stdout.on('data', d => { out += d; });
    child.on('close', code => { clearTimeout(t); resolve(code === 0 && /OK/i.test(out)); });
    child.stdin.write('Say OK and nothing else.');
    child.stdin.end();
  });
}
function limitPause() {
  if (!pausePromise) {
    pausePromise = (async () => {
      let ms = 5 * 60 * 1000;
      while (true) {
        console.log(`USAGE-LIMIT PAUSE ${Math.round(ms / 60000)}min`);
        await sleep(ms);
        if (await probe()) break;
        ms = Math.min(ms * 2, 60 * 60 * 1000);
      }
      console.log('LIMIT LIFTED, resuming');
      pausePromise = null;
    })();
  }
  return pausePromise;
}
const TOTAL_PAGES_EXPECTED = 3692; // 3694 minus ACTA(1) + Conflicts(1) skips

const failures = {};

function refreshChunks() {
  try {
    execFileSync(PY, [path.join(ROOT, '_make_chunks.py'), PAGES_ROOT], { stdio: 'pipe' });
  } catch (e) {
    console.log('WARN _make_chunks failed: ' + e.message.split('\n')[0]);
  }
  return JSON.parse(fs.readFileSync(path.join(ROOT, '_chunks.json'), 'utf8'));
}

function prompt(c) {
  const dir = path.dirname(c.pages[0]);
  const last = c.first_page + c.pages.length - 1;
  const p = n => 'p' + String(n).padStart(4, '0') + '.png';
  return `First Read the instruction file: ${path.join(ROOT, '_extraction_instructions.md')} - follow it exactly.

Chunk id: ${c.id}
Page images (Read each, in order): files ${p(c.first_page)} through ${p(last)} (${c.pages.length} pages) in
${dir}
('page' field = the number in the filename.)

Write output JSON to: ${c.out}`;
}

function goodOutput(c) {
  try {
    const d = JSON.parse(fs.readFileSync(c.out, 'utf8').replace(/^﻿/, ''));
    const got = new Set(d.pages.map(pg => pg.page));
    for (let i = c.first_page; i < c.first_page + c.pages.length; i++)
      if (!got.has(i)) return `missing page ${i}`;
    return null;
  } catch (e) { return 'bad json: ' + e.message; }
}

function runJob(c) {
  return new Promise(resolve => {
    const child = spawn('claude', ['-p', '--model', 'sonnet', '--allowedTools', 'Read,Write'],
      { shell: true, stdio: ['pipe', 'pipe', 'pipe'] });
    const t = setTimeout(() => { try { child.kill(); } catch {} }, JOB_TIMEOUT_MS);
    let err = '';
    child.stderr.on('data', d => { err += d; });
    child.stdout.on('data', () => {});
    child.on('close', code => {
      clearTimeout(t);
      if (!fs.existsSync(c.out)) return resolve(`no output (exit ${code}) ${err.slice(0, 120)}`);
      const bad = goodOutput(c);
      if (bad) { try { fs.unlinkSync(c.out); } catch {} return resolve(bad); }
      resolve(null);
    });
    child.stdin.write(prompt(c));
    child.stdin.end();
  });
}

async function main() {
  let done = 0;
  for (let cycle = 1; ; cycle++) {
    const chunks = refreshChunks();
    const pending = chunks.filter(c =>
      !fs.existsSync(c.out) && (failures[c.id] || 0) < MAX_TRIES);
    const chunkedPages = chunks.reduce((s, c) => s + c.pages.length, 0);
    const renderDone = chunkedPages >= TOTAL_PAGES_EXPECTED;
    console.log(`CYCLE ${cycle}: ${chunks.length} chunks known, ${pending.length} pending, render ${renderDone ? 'complete' : chunkedPages + '/' + TOTAL_PAGES_EXPECTED}`);
    if (!pending.length) {
      if (renderDone) break;
      await new Promise(r => setTimeout(r, 60000));
      continue;
    }
    // pool
    let idx = 0;
    async function worker(w) {
      while (idx < pending.length) {
        const c = pending[idx++];
        while (true) {
          const t0 = Date.now();
          const bad = await runJob(c);
          const secs = Math.round((Date.now() - t0) / 1000);
          if (!bad) {
            done++;
            console.log(`OK ${done} ${c.id} [${secs}s]`);
            break;
          }
          if (secs < FAST_FAIL_S) {
            // usage limit / infra — wait globally, then retry same chunk;
            // never burns a try
            await limitPause();
            continue;
          }
          failures[c.id] = (failures[c.id] || 0) + 1;
          console.log(`RETRY(${failures[c.id]}) ${c.id}: ${bad} [${secs}s]`);
          break;
        }
      }
    }
    await Promise.all(Array.from({ length: Math.min(POOL, pending.length) }, (_, w) => worker(w)));
  }
  const dead = Object.entries(failures).filter(([id, n]) => n >= MAX_TRIES &&
    !fs.existsSync(path.join(ROOT, 'extracted', 'raw', id + '.json')));
  console.log(`ALL DONE. completed this run: ${done}. permanently failed: ${dead.length}`);
  for (const [id] of dead) console.log('FAILED ' + id);
}

main().catch(e => { console.log('DRIVER ERROR ' + e.message); process.exit(1); });
