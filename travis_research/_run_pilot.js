/* Phase 2 pilot driver: run the SAME research instructions used for
 * donorbatch3 (Opus baseline) against donorbatch4_pilot.json on Sonnet 5,
 * to compare quality/cost/latency. Copied from _run_research.js and
 * trimmed to a single job (no pool/backoff needed for one 30-donor batch).
 * Does not touch _run_research.js or any donorbatch3 file.
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const BATCH = 'donorbatch4_pilot.json';
const OUT = 'donorbatch4_pilot_results.json';
const JOB_TIMEOUT_MS = 20 * 60 * 1000;
const MODEL = process.argv[2] || 'claude-sonnet-5';

function prompt(batchFile, outFile) {
  return `Read ${path.join(ROOT, '_research_instructions.md')} and follow it exactly.

Task: holistic web research on the DONORS in ${path.join(ROOT, batchFile)} (donor batch format; note the dollar field is "site_total" — total given across all decodepolitics.org profiles, city and county). These are unidentified donors to Austin City Council and Travis County officials. Research each; corroborate identity with zip/location/donation pattern before classifying. Record any AIPAC/ADL/pro-Israel/oil/gun/military-defense affiliations you encounter.

Write results to ${path.join(ROOT, outFile)} (JSON array, donor-batch output format).`;
}

function runJob() {
  return new Promise(resolve => {
    const t0 = Date.now();
    const child = spawn('claude',
      ['-p', '--model', MODEL, '--allowedTools', 'Read,Write,WebSearch,WebFetch,ToolSearch'],
      { shell: true, stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    const t = setTimeout(() => { try { child.kill(); } catch {} }, JOB_TIMEOUT_MS);
    child.stdout.on('data', d => { stdout += d; });
    child.stderr.on('data', d => { stderr += d; });
    child.on('close', code => {
      clearTimeout(t);
      const secs = Math.round((Date.now() - t0) / 1000);
      resolve({ code, secs, stdout, stderr });
    });
    child.stdin.write(prompt(BATCH, OUT));
    child.stdin.end();
  });
}

async function main() {
  console.log(`RUNNING pilot on model=${MODEL} ...`);
  const r = await runJob();
  fs.writeFileSync(path.join(ROOT, '_pilot_run_log.txt'),
    `model: ${MODEL}\nexit: ${r.code}\nseconds: ${r.secs}\n\n--- stdout ---\n${r.stdout}\n\n--- stderr ---\n${r.stderr}\n`);
  const outPath = path.join(ROOT, OUT);
  if (!fs.existsSync(outPath)) {
    console.log(`NO OUTPUT written. exit=${r.code} secs=${r.secs}. See _pilot_run_log.txt`);
    process.exit(1);
  }
  console.log(`DONE in ${r.secs}s, exit=${r.code}. Output: ${OUT}`);
}

main();
