"""Build Opus research batch inputs for the 2026 District 3 DELTA donor pool.

Delta scrub: the original D3 scrub (archive/d3_research, 28 batches, 2026)
covered the Velasquez + Shah donor pool as of that run. The October 2026
filings added donors who were never researched, and two more D3 candidates
(Romero, Skinner) now have finance data. This prep rebuilds the same pool with
the same rule as archive/d3_research/_prep_d3_batches.py -- donors to the D3
candidates the race page renders with finance data (Velasquez, Shah, Romero,
Skinner) who gave >= $100 across those campaigns, lifetime (no cycle window;
Velasquez's 2022 donors are in, as in the original scrub), positive
COALESCE(balanced_amount, contribution_amount) rows only, grouped by donor_id
(no individual/entity filter, no special joint handling) -- and removes
everyone already covered by:

  * any prior research batch input (travis donorbatch*, d1batch_*, d3batch_*,
    d1delta_*, _pilot_covered_ids.json), with donor_ids remapped through
    identity_merges (FEC dedups merge batch ids into other donor_ids; without
    the remap those donors would be re-scrubbed),
  * an existing civic_affiliations row (matched on lowercased canonical_name,
    as the original prep did),
  * a resolved_confidence already set by an LLM research pass
    ('llm-research-%'), which is what the apply step writes.

Gavino Fernandez (2022 rows only) is on the D3 roster with has_data=false, so
his donors are NOT in the pool (the precedent rule is "candidates with finance
data on the race page"); the script reports how many donors he would add.

Output format matches travis_research/donorbatch5_*.json exactly so the same
v3 instructions and result-apply path work unchanged. The dollar field is named
"site_total" for that reason -- here it means total given across the D3
campaigns, which is what the instructions' corroboration step keys on.

Read-only against the DB (opened with mode=ro).

Outputs: d3_delta_research/d3delta_NN.json (20 donors each) -- the prefix is
deliberately different from d3batch_ so the driver can never collide with the
finished archive set.
"""
import glob
import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Works from the repo root (active run) or from archive/<dir>/ (archived copy).
REPO = ROOT.parent.parent if ROOT.parent.name == "archive" else ROOT.parent
DB = REPO / "austin_finance.db"
ARCHIVE = REPO / "archive"
TRAVIS = ARCHIVE / "travis_research"
BATCH = 20
MIN_TOTAL = 100
PREFIX = "d3delta_"

CANDIDATES = [
    "Velasquez, Jose",
    "Shah, Neha",
    "Romero, Eduardo",
    "Skinner, Brock D.",
]
# On the D3 roster but has_data=false (2022 rows only); reported, not pooled.
FERNANDEZ = "Fernandez, Gavino"

COVERAGE_GLOBS = {
    "travis batches": str(TRAVIS / "donorbatch*.json"),
    "d1 batches":     str(ARCHIVE / "d1_research" / "d1batch_*.json"),
    "d3 batches":     str(ARCHIVE / "d3_research" / "d3batch_*.json"),
    "d1 delta batches": str(ARCHIVE / "d1_delta_research" / "d1delta_*.json"),
}

conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ── Prior coverage: every donor_id ever submitted to a research batch ────────
covered_by = {}          # source label -> set of donor_ids (as written in the batch files)
for label, pattern in COVERAGE_GLOBS.items():
    ids = set()
    for f in sorted(glob.glob(pattern)):
        if f.endswith("_results.json"):
            continue
        try:
            rows = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(rows, list):
            ids.update(r["donor_id"] for r in rows
                       if isinstance(r, dict) and r.get("donor_id"))
    covered_by[label] = ids
try:
    covered_by["pilot covered ids"] = set(json.load(
        open(TRAVIS / "_pilot_covered_ids.json", encoding="utf-8")))
except Exception:
    covered_by["pilot covered ids"] = set()

batch_ids = set().union(*covered_by.values())

# ── identity_merges remap: merged_donor_id -> into_donor_id, transitively ────
merge_map = dict(cur.execute(
    "SELECT merged_donor_id, into_donor_id FROM identity_merges").fetchall())


def resolve(did):
    seen = set()
    while did in merge_map and did not in seen:
        seen.add(did)
        did = merge_map[did]
    return did


# into_donor_ids that are covered only because a batch id was merged into them
remapped_targets = {resolve(d) for d in batch_ids} - batch_ids
covered_ids = batch_ids | remapped_targets

# civic_affiliations keys on canonical_name, not donor_id -- match on name so the
# check survives the July identity migration (which reissued most donor_ids).
aff_names = {r[0].strip().lower() for r in
             cur.execute("SELECT canonical_name FROM civic_affiliations "
                         "WHERE canonical_name IS NOT NULL")}

# ── Pool ────────────────────────────────────────────────────────────────────
ph = ",".join("?" * len(CANDIDATES))
donors = cur.execute(f"""
    SELECT di.donor_id, di.canonical_name, di.canonical_zip,
           di.fec_partisan_lean, di.fec_total_donations,
           di.resolved_confidence,
           SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)) AS site_total,
           GROUP_CONCAT(DISTINCT cf.recipient) AS recipients,
           GROUP_CONCAT(DISTINCT cf.donor_reported_occupation) AS occupations,
           GROUP_CONCAT(DISTINCT cf.donor_reported_employer) AS employers,
           GROUP_CONCAT(DISTINCT cf.city_state_zip) AS locations,
           MIN(cf.contribution_date) AS first_gift,
           MAX(cf.contribution_date) AS last_gift
    FROM campaign_finance cf
    JOIN donor_identities di ON di.donor_id = cf.donor_id
    WHERE cf.recipient IN ({ph})
      AND cf.donor_id IS NOT NULL
      AND COALESCE(cf.balanced_amount, cf.contribution_amount) > 0
    GROUP BY di.donor_id
    HAVING site_total >= ?
    ORDER BY site_total DESC
""", (*CANDIDATES, MIN_TOTAL)).fetchall()
fernandez_n = cur.execute("""
    SELECT COUNT(*) FROM (
      SELECT donor_id, SUM(COALESCE(balanced_amount, contribution_amount)) AS t
      FROM campaign_finance
      WHERE recipient = ? AND donor_id IS NOT NULL
        AND COALESCE(balanced_amount, contribution_amount) > 0
      GROUP BY donor_id HAVING t >= ?)""", (FERNANDEZ, MIN_TOTAL)).fetchone()[0]
conn.close()


def skip_reasons(d):
    """All reasons this pool donor is already covered (may be several)."""
    did = d["donor_id"]
    reasons = [label for label, ids in covered_by.items() if did in ids]
    if did in remapped_targets:
        reasons.append("identity_merges remap")
    if (d["canonical_name"] or "").strip().lower() in aff_names:
        reasons.append("civic_affiliations name match")
    if (d["resolved_confidence"] or "").startswith("llm-research-"):
        reasons.append("llm-research confidence")
    return reasons


pool, covered, blank = [], [], []
reason_any = Counter()       # non-exclusive: a donor can count in several
reason_first = Counter()     # exclusive: first reason in priority order
for d in donors:
    reasons = skip_reasons(d)
    if reasons:
        covered.append(d)
        reason_any.update(reasons)
        reason_first[reasons[0]] += 1
    elif not (d["canonical_name"] or "").strip():
        # Not in the archived prep: identities with an empty canonical_name
        # (joint-shadow half-rows whose second half never got a name) cannot be
        # researched, and the apply step keys civic_affiliations on the name.
        # Report them for identity cleanup instead of spending a batch slot.
        blank.append(d)
    else:
        pool.append(d)

print(f"donors >= ${MIN_TOTAL} across the 4 D3 campaigns: {len(donors)}")
print(f"  (not pooled: {FERNANDEZ} has_data=false, 2022 only -- would add {fernandez_n} donors >= ${MIN_TOTAL})")
print(f"already covered by prior research:              {len(covered)}")
print(f"    {'source':32} {'exclusive':>9}   any-match")
for label, n in reason_first.most_common():
    print(f"    {label:32} {n:9}   {reason_any[label]}")
for label in reason_any:
    if label not in reason_first:
        print(f"    {label:32} {0:9}   {reason_any[label]}")
print(f"blank canonical_name (excluded, fix identity):  {len(blank)}")
for d in blank:
    print(f"    {d['donor_id']}  ${d['site_total']:.2f}  gave_to={d['recipients']}  "
          f"first={d['first_gift'][:10]}")
print(f"POOL TO SCRUB:                                  {len(pool)}")

# recipients is a GROUP_CONCAT with commas inside the names ("Skinner, Brock D."),
# so test membership against the candidate strings rather than splitting.
per_cand = Counter()
for d in pool:
    for c in CANDIDATES:
        if c in (d["recipients"] or ""):
            per_cand[c] += 1
print("uncovered donors by candidate (a donor can count for several):")
for c in CANDIDATES:
    print(f"    {c:28} {per_cand[c]}")

for i in range(0, len(pool), BATCH):
    chunk = [{
        "donor_id": d["donor_id"],
        "name": d["canonical_name"],
        "zip": d["canonical_zip"],
        "site_total": round(d["site_total"], 2),
        "gave_to": d["recipients"],
        "occupations": (d["occupations"] or "")[:150],
        "employer_strings": (d["employers"] or "")[:150],
        "locations": (d["locations"] or "")[:150],
        "first_gift": d["first_gift"],
        "last_gift": d["last_gift"],
        "fec_partisan_lean": d["fec_partisan_lean"],
        "fec_donation_count": d["fec_total_donations"] or 0,
    } for d in pool[i:i + BATCH]]
    out = ROOT / f"{PREFIX}{i // BATCH + 1:02d}.json"
    json.dump(chunk, open(out, "w", encoding="utf-8"), indent=1)

print(f"wrote {(len(pool) + BATCH - 1) // BATCH} batches of {BATCH} to {ROOT}")
