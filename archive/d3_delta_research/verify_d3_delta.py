"""Verify the D3 delta research corpus before applying it (runbook step 11.5).

Read-only against the DB. Checks every d3delta_NN_results.json:
  * parses; row count == input batch row count
  * every result donor_id is in its input batch (a mistyped UUID would pass
    the driver's >50 %-missing check and then match nothing in the apply)
  * every industry is a taxonomy label (or null)
  * every affiliation has org + source_url (+ category in the allowed set)
  * confidence distribution, affiliation category counts, spectrum rows
  * cost per batch and total from _d3_delta_usage_log.jsonl
and writes _d3_delta_overridden_labels.csv: the current heuristic label of
every donor whose high/medium verdict the widened apply gate will overwrite
(so the override is reversible with one UPDATE per row).

Usage: python verify_d3_delta.py
"""
import csv
import glob
import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Works from the repo root (active run) or from archive/<dir>/ (archived copy).
REPO = ROOT.parent.parent if ROOT.parent.name == "archive" else ROOT.parent
DB = REPO / "austin_finance.db"
PREFIX = "d3delta_"

TAXONOMY = {
    "Government", "Healthcare", "Real Estate", "Energy / Environment", "Finance",
    "Retail", "Transportation", "Nonprofit / Advocacy", "Technology",
    "Consulting / PR", "Construction", "Venture Capital", "Media", "Education",
    "Engineering", "Labor", "Legal", "Hospitality / Events", "Architecture",
    "Entertainment", "Self-Employed", "Not Employed", "Student",
}
AFF_CATS = {
    "aipac_direct", "pro_israel", "liberal_zionist", "jewish_civic",
    "palestine_solidarity", "pro_palestine_advocacy", "oil_gas", "gun_rights",
    "gun_control", "military_defense", "civic", "business", "political",
}
SPECTRUM = {"oil_gas", "military_defense", "gun_rights", "gun_control",
            "aipac_direct", "pro_israel", "liberal_zionist", "jewish_civic",
            "palestine_solidarity", "pro_palestine_advocacy"}

problems = []
conf = Counter()
inds = Counter()
cats = Counter()
searches_false = 0
n_rows = n_with_industry = n_aff_donors = n_aff_rows = 0
spectrum_rows = []
results = {}   # donor_id -> (batch, row)

inputs = sorted(f for f in glob.glob(str(ROOT / f"{PREFIX}[0-9]*.json"))
                if not f.endswith("_results.json"))
for inp in inputs:
    b = Path(inp).name
    out = inp.replace(".json", "_results.json")
    if not Path(out).exists():
        problems.append(f"{b}: no results file")
        continue
    batch = json.load(open(inp, encoding="utf-8"))
    in_ids = {r["donor_id"] for r in batch}
    try:
        rows = json.load(open(out, encoding="utf-8-sig"))
    except Exception as e:
        problems.append(f"{b}: results do not parse: {e}")
        continue
    if not isinstance(rows, list):
        problems.append(f"{b}: results not a list")
        continue
    if len(rows) != len(batch):
        problems.append(f"{b}: {len(rows)} result rows vs {len(batch)} input rows")
    out_ids = [r.get("donor_id") for r in rows]
    for did in out_ids:
        if did not in in_ids:
            problems.append(f"{b}: result donor_id {did!r} not in input batch")
    for did in in_ids - set(out_ids):
        problems.append(f"{b}: input donor_id {did} has no result row")
    if len(set(out_ids)) != len(out_ids):
        problems.append(f"{b}: duplicate donor_ids in results")
    for r in rows:
        n_rows += 1
        results[r.get("donor_id")] = (b, r)
        c = r.get("confidence")
        conf[c] += 1
        if c not in ("high", "medium", "low"):
            problems.append(f"{b}: {r.get('name')} bad confidence {c!r}")
        ind = r.get("industry")
        if ind is not None:
            n_with_industry += 1
            inds[ind] += 1
            if ind not in TAXONOMY:
                problems.append(f"{b}: {r.get('name')} industry {ind!r} not in taxonomy")
        sr = r.get("searches_run") or {}
        if not sr:
            problems.append(f"{b}: {r.get('name')} missing searches_run")
        elif not all(sr.get(k) for k in ("fec_pac", "tx_lobbyist", "bio_full_read")):
            searches_false += 1
        affs = r.get("affiliations") or []
        if affs:
            n_aff_donors += 1
        for a in affs:
            n_aff_rows += 1
            cat = a.get("category")
            cats[cat] += 1
            if not a.get("org") or not a.get("source_url"):
                problems.append(f"{b}: {r.get('name')} affiliation missing org/source_url: {a}")
            if cat not in AFF_CATS:
                problems.append(f"{b}: {r.get('name')} affiliation category {cat!r} not allowed")
            if cat in SPECTRUM:
                spectrum_rows.append((b, r.get("name"), cat, a.get("org"), a.get("role"), a.get("source_url")))

print(f"result files: {sum(1 for f in inputs if Path(f.replace('.json', '_results.json')).exists())}/{len(inputs)}")
print(f"rows: {n_rows}; with industry: {n_with_industry}; "
      f"donors with affiliations: {n_aff_donors}; affiliation rows: {n_aff_rows}")
print(f"confidence: {dict(conf)}")
print(f"searches_run with any false: {searches_false}")
print("industries:", dict(inds.most_common()))
print("affiliation categories:", dict(cats.most_common()))
print("spectrum rows (must all be spot-read):")
for s in spectrum_rows:
    print("   ", s)

# ── cost ──────────────────────────────────────────────────────────────────
log = ROOT / "_d3_delta_usage_log.jsonl"
if log.exists():
    total = 0.0
    print("cost per batch:")
    for line in open(log, encoding="utf-8"):
        if not line.strip():
            continue
        e = json.loads(line)
        c = e.get("total_cost_usd") or 0
        total += c
        print(f"    {e['batch']:18} ${c:6.2f}  {e.get('secs')}s  {e.get('model')}  {e.get('at')}")
    print(f"TOTAL ${total:.2f}")

# ── overridden-labels CSV (read-only DB) ─────────────────────────────────────
conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
cur = conn.cursor()
rows_out = []
would_apply = blocked_llm = 0
for did, (b, r) in results.items():
    if not (r.get("industry") and r.get("confidence") in ("high", "medium")):
        continue
    row = cur.execute("""SELECT donor_id, canonical_name, resolved_industry,
                                resolved_employer_display, resolved_confidence
                         FROM donor_identities WHERE donor_id=?""", (did,)).fetchone()
    if row is None:
        problems.append(f"{b}: donor_id {did} not in donor_identities")
        continue
    if (row[4] or "").startswith("llm-research-"):
        blocked_llm += 1
        continue
    would_apply += 1
    if row[2] is not None:
        rows_out.append([*row, r["industry"], r.get("resolved_employer"),
                         f"llm-research-{r['confidence']}", b])
csv_path = ROOT / "_d3_delta_overridden_labels.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["donor_id", "canonical_name", "prev_resolved_industry",
                "prev_resolved_employer_display", "prev_resolved_confidence",
                "new_resolved_industry", "new_resolved_employer_display",
                "new_resolved_confidence", "batch"])
    w.writerows(rows_out)
print(f"apply expectation: {would_apply} donor rows would be updated "
      f"({len(rows_out)} override an existing heuristic label -> {csv_path.name}; "
      f"{blocked_llm} blocked by an earlier llm-research verdict)")
print("overridden prior confidences:", dict(Counter(r[4] for r in rows_out)))
agree = sum(1 for r in rows_out if r[2] == r[5])
print(f"  of which heuristic label already agreed with the LLM verdict: {agree}")
conn.close()

print()
if problems:
    print(f"PROBLEMS ({len(problems)}):")
    for p in problems:
        print("   ", p)
else:
    print("NO PROBLEMS")
