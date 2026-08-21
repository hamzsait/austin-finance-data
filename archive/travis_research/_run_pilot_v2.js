/* Phase 2 pilot v2 driver: same as _run_pilot.js but points at the
 * mandatory-checklist instructions (_research_instructions_v2.md) and the
 * v2 15-donor batch (8 sensitive + 7 fresh delta). Does not touch
 * _run_research.js, _run_pilot.js, or any donorbatch3/donorbatch4_pilot file.
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const BATCH = 'donorbatch4_pilot_v2.json';
const OUT = 'donorbatch4_pilot_v2_results.json';
const JOB_TIMEOUT_MS = 20 * 60 * 1000;
const MODEL = process.argv[2] || 'claude-sonnet-5';

function prompt(batchFile, outFile) {
  return `Read ${path.join(ROOT, '_research_instructions_v2.md')} and follow it exactly, including the MANDATORY affiliation-search checklist section.

Task: holistic web research on the DONORS in ${path.join(ROOT, batchFile)} (donor batch format; note the dollar field is "site_total" — total given across all decodepolitics.org profiles, city and county). These are unidentified donors to Austin City Council and Travis County officials. Research each; corroborate identity with zip/location/donation pattern before classifying. For every donor you MUST run the FEC PAC-contribution search, the Texas lobbyist registry search, and a full bio-page read as described in the instructions, then record any AIPAC/ADL/pro-Israel/oil/gun/military-defense affiliations you find.

Write results to ${path.join(ROOT, outFile)} (JSON array, donor-batch output format, including the searches_run field per donor).`;
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
  console.log(`RUNNING pilot v2 on model=${MODEL} ...`);
  const r = await runJob();
  fs.writeFileSync(path.join(ROOT, '_pilot_v2_run_log.txt'),
    `model: ${MODEL}\nexit: ${r.code}\nseconds: ${r.secs}\n\n--- stdout ---\n${r.stdout}\n\n--- stderr ---\n${r.stderr}\n`);
  const outPath = path.join(ROOT, OUT);
  if (!fs.existsSync(outPath)) {
    console.log(`NO OUTPUT written. exit=${r.code} secs=${r.secs}. See _pilot_v2_run_log.txt`);
    process.exit(1);
  }
  console.log(`DONE in ${r.secs}s, exit=${r.code}. Output: ${OUT}`);
}

main();
