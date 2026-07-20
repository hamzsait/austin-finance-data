"""Build Opus research batch inputs for the 2026 District 3 donor pool.

Pool = donors to the two D3 candidates (Velasquez, Shah) who gave >= $100
across those two campaigns (lifetime basis — Velasquez's donor base is mostly
his 2022 run, and his live profile displays lifetime donors; see
D3_EXPANSION_PLAN.md SSD) and are not already covered by a prior research batch
or an existing civic_affiliations row. Unlike the D1 prep, prior coverage must
also include the 31 D1 batches (plan SS0.6), or D3 would re-scrub shared donors.

Output format matches travis_research/donorbatch5_*.json exactly so the same
v3 instructions and result-apply path work unchanged. The dollar field is named
"site_total" for that reason -- here it means total given across the two D3
campaigns, which is what the instructions' corroboration step keys on.

Outputs: d3_research/d3batch_NN.json (20 donors each)
"""
import glob
import json
import os
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "..", "austin_finance.db")
TRAVIS = os.path.join(ROOT, "..", "travis_research")
D1 = os.path.join(ROOT, "..", "d1_research")
BATCH = 20
MIN_TOTAL = 100

CANDIDATES = [
    "Velasquez, Jose",
    "Shah, Neha",
]

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ── Prior coverage: every donor_id ever submitted to a research batch ────────
covered_ids = set()
for pattern in (os.path.join(TRAVIS, "donorbatch*.json"),
                os.path.join(D1, "d1batch_*.json")):
    for f in sorted(glob.glob(pattern)):
        if f.endswith("_results.json"):
            continue
        try:
            rows = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(rows, list):
            covered_ids.update(r["donor_id"] for r in rows
                               if isinstance(r, dict) and r.get("donor_id"))
try:
    covered_ids.update(json.load(
        open(os.path.join(TRAVIS, "_pilot_covered_ids.json"), encoding="utf-8")))
except Exception:
    pass

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

pool = [d for d in donors
        if d["donor_id"] not in covered_ids
        and (d["canonical_name"] or "").strip().lower() not in aff_names]

print(f"donors >= ${MIN_TOTAL} across the 2 D3 campaigns: {len(donors)}")
print(f"already covered by prior research:              {len(donors) - len(pool)}")
print(f"POOL TO SCRUB:                                  {len(pool)}")

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
    out = os.path.join(ROOT, f"d3batch_{i // BATCH + 1:02d}.json")
    json.dump(chunk, open(out, "w", encoding="utf-8"), indent=1)

print(f"wrote {(len(pool) + BATCH - 1) // BATCH} batches of {BATCH} to {ROOT}")
