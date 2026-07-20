/* D3 donor research driver: runs headless `claude -p --model
 * claude-opus-4-8` donor-research jobs over all pending d3batch_*.json files
 * (the >=$100 lifetime District 3 donor pool: Velasquez + Shah) with a worker
 * pool, retries, and usage-limit-aware global backoff. Same pattern and same
 * v3 mandatory/balanced instructions as d1_research/_run_d1_research.js.
 *
 * Logs per-batch token usage + cost to _d3_usage_log.jsonl.
 * Globs only d3batch_* in this directory -- does not touch other research dirs.
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const TRAVIS = path.join(ROOT, '..', 'travis_research');
const POOL = 4;
const JOB_TIMEOUT_MS = 20 * 60 * 1000;
const MAX_TRIES = 3;
const FAST_FAIL_S = 30;
const MODEL = 'claude-opus-4-8';
const MAX_BUDGET_USD = '25';
const USAGE_LOG = path.join(ROOT, '_d3_usage_log.jsonl');

const failures = {};
const sleep = ms => new Promise(r => setTimeout(r, ms));

function pendingBatches() {
  return fs.readdirSync(ROOT)
    .filter(f => /^d3batch_\d+\.json$/.test(f))
    .filter(f => !fs.existsSync(path.join(ROOT, f.replace('.json', '_results.json'))))
    .filter(f => (failures[f] || 0) < MAX_TRIES)
    .sort();
}

function prompt(batchFile) {
  const out = batchFile.replace('.json', '_results.json');
  return `Read ${path.join(TRAVIS, '_research_instructions_v3.md')} and follow it exactly, including the MANDATORY affiliation-search checklist and the balanced-spectrum category set (pro-Israel AND pro-Palestine, oil/gas, gun rights/control, military-defense).

Task: holistic web research on the DONORS in ${path.join(ROOT, batchFile)} (donor batch format; note the dollar field is "site_total" — here it means total given across the two 2026 Austin City Council District 3 campaigns: incumbent José Velásquez, who is defending the seat, and challenger Neha Shah. Most Velásquez donors date to his 2022 run). These are donors to candidates in a live municipal race. Research each; corroborate identity with zip/location/donation pattern before classifying. For every donor, regardless of amount, run the FEC PAC-contribution search, the Texas lobbyist registry search, and a full bio-page read, then record any affiliations found across the full balanced category set. Use the categorize-by-employer fallback (no forced affiliation guess) when no public profile is discoverable beyond a generic occupation.

These are private individuals donating to a local race, not public figures. Record only affiliations that are documented in public records (FEC filings, lobbyist registries, organizational leadership pages, published bios). Do not infer political or religious affiliation from a name, a zip code, or an employer alone.

Write results to ${path.join(ROOT, out)} (JSON array, donor-batch output format, including the searches_run field per donor).`;
}

function goodOutput(batchFile) {
  const inPath = path.join(ROOT, batchFile);
  const outPath = path.join(ROOT, batchFile.replace('.json', '_results.json'));
  try {
    const input = JSON.parse(fs.readFileSync(inPath, 'utf8'));
    const out = JSON.parse(fs.readFileSync(outPath, 'utf8').replace(/^﻿/, ''));
    if (!Array.isArray(out)) return 'not an array';
    const ids = new Set(out.map(o => o.donor_id));
    const missing = input.filter(d => !ids.has(d.donor_id)).length;
    if (missing > input.length / 2) return `missing ${missing}/${input.length} donor_ids`;
    return null;
  } catch (e) { return 'bad json: ' + e.message.slice(0, 80); }
}

function logUsage(batchFile, envelope, secs) {
  fs.appendFileSync(USAGE_LOG, JSON.stringify({
    batch: batchFile,
    model: MODEL,
    secs,
    total_cost_usd: envelope && envelope.total_cost_usd,
    usage: envelope && envelope.usage,
    subtype: envelope && envelope.subtype,
    at: new Date().toISOString(),
  }) + '\n');
}

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

let pausePromise = null;
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

function runJob(batchFile) {
  return new Promise(resolve => {
    const child = spawn('claude',
      ['-p', '--model', MODEL, '--allowedTools', 'Read,Write,WebSearch,WebFetch,ToolSearch',
       '--output-format', 'json', '--max-budget-usd', MAX_BUDGET_USD],
      { shell: true, stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    const t = setTimeout(() => { try { child.kill(); } catch {} }, JOB_TIMEOUT_MS);
    child.stdout.on('data', d => { stdout += d; });
    child.stderr.on('data', d => { stderr += d; });
    child.on('close', code => {
      clearTimeout(t);
      const outPath = path.join(ROOT, batchFile.replace('.json', '_results.json'));
      let envelope = null;
      try { envelope = JSON.parse(stdout.trim().split('\n').pop()); } catch {}
      // On failure, persist the real stderr/stdout tail instead of inferring a cause.
      if (!fs.existsSync(outPath) || goodOutput(batchFile)) {
        fs.appendFileSync(path.join(ROOT, '_d3_job_errors.log'),
          `\n===== ${batchFile} exit=${code} at ${new Date().toISOString()} =====\n` +
          `--- stderr (last 2000) ---\n${stderr.slice(-2000)}\n` +
          `--- stdout (last 2000) ---\n${stdout.slice(-2000)}\n`);
      }
      if (!fs.existsSync(outPath)) { resolve({ bad: `no output (exit ${code})`, envelope }); return; }
      const bad = goodOutput(batchFile);
      if (bad) { try { fs.unlinkSync(outPath); } catch {} resolve({ bad, envelope }); return; }
      resolve({ bad: null, envelope });
    });
    child.stdin.write(prompt(batchFile));
    child.stdin.end();
  });
}

async function main() {
  let done = 0, spend = 0;
  while (true) {
    const pending = pendingBatches();
    if (!pending.length) break;
    console.log(`CYCLE: ${pending.length} batches pending`);
    let idx = 0;
    await Promise.all(Array.from({ length: Math.min(POOL, pending.length) }, async () => {
      while (idx < pending.length) {
        const b = pending[idx++];
        let fastFails = 0;
        while (true) {
          const t0 = Date.now();
          const { bad, envelope } = await runJob(b);
          const secs = Math.round((Date.now() - t0) / 1000);
          if (!bad) {
            done++;
            spend += (envelope && envelope.total_cost_usd) || 0;
            logUsage(b, envelope, secs);
            console.log(`OK ${done} ${b} [${secs}s] cost=$${envelope && envelope.total_cost_usd} running=$${spend.toFixed(2)}`);
            break;
          }
          if (secs < FAST_FAIL_S && fastFails < 12) {
            fastFails++;
            await limitPause();
            continue;
          }
          failures[b] = (failures[b] || 0) + 1;
          console.log(`RETRY(${failures[b]}) ${b}: ${bad} [${secs}s]`);
          break;
        }
      }
    }));
  }
  const dead = Object.entries(failures).filter(([b, n]) => n >= MAX_TRIES);
  console.log(`ALL DONE. completed this run: ${done}. total spend: $${spend.toFixed(2)}. failed: ${dead.length}`);
  for (const [b] of dead) console.log('FAILED ' + b);
}

main().catch(e => { console.log('DRIVER ERROR ' + e.message); process.exit(1); });
