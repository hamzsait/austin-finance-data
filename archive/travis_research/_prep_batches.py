"""Build Opus research batch inputs for county Unknowns.

Stream A: unclassified employer_identities on county rows -> batches of 40
Stream B: top county donors with resolved_industry NULL -> batches of 10,
          with full context (zip, occupation, employer string if any, who they
          gave to, when, how much).
Outputs: travis_research/empbatch_NN.json, donorbatch_NN.json
"""
import json, os, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "..", "austin_finance.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ── Stream A: employers ──────────────────────────────────────────────────────
emps = cur.execute("""
    SELECT ei.employer_id, ei.canonical_name, ei.name_variants,
           SUM(CAST(cf.contribution_amount AS REAL)) AS county_total,
           COUNT(DISTINCT cf.donor_id) AS donor_count,
           GROUP_CONCAT(DISTINCT cf.donor_reported_occupation) AS occupations
    FROM campaign_finance cf
    JOIN employer_identities ei ON ei.employer_id = cf.employer_id
    WHERE cf.transaction_id LIKE 'TRAVIS-%' AND (ei.industry IS NULL OR ei.industry='')
    GROUP BY ei.employer_id ORDER BY county_total DESC
""").fetchall()
BATCH_A = 40
for i in range(0, len(emps), BATCH_A):
    batch = [{
        "employer_id": e["employer_id"], "name": e["canonical_name"],
        "variants": e["name_variants"], "county_total": round(e["county_total"]),
        "donor_count": e["donor_count"],
        "sample_occupations": (e["occupations"] or "")[:200],
    } for e in emps[i:i+BATCH_A]]
    json.dump(batch, open(os.path.join(ROOT, f"empbatch_{i//BATCH_A+1:02d}.json"), "w"), indent=1)
print(f"Stream A: {len(emps)} employers -> {(len(emps)+BATCH_A-1)//BATCH_A} batches")

# ── Stream B: donors ─────────────────────────────────────────────────────────
donors = cur.execute("""
    SELECT di.donor_id, di.canonical_name, di.canonical_zip, di.canonical_employer,
           di.fec_partisan_lean, di.fec_total_donations,
           SUM(CAST(cf.contribution_amount AS REAL)) AS county_total,
           GROUP_CONCAT(DISTINCT cf.recipient) AS recipients,
           GROUP_CONCAT(DISTINCT cf.donor_reported_occupation) AS occupations,
           GROUP_CONCAT(DISTINCT cf.donor_reported_employer) AS employers,
           GROUP_CONCAT(DISTINCT cf.city_state_zip) AS locations,
           MIN(cf.contribution_date) AS first_gift, MAX(cf.contribution_date) AS last_gift
    FROM campaign_finance cf
    JOIN donor_identities di ON di.donor_id = cf.donor_id
    WHERE cf.transaction_id LIKE 'TRAVIS-%' AND di.resolved_industry IS NULL
    GROUP BY di.donor_id ORDER BY county_total DESC LIMIT 200
""").fetchall()
BATCH_B = 10
for i in range(0, len(donors), BATCH_B):
    batch = [{
        "donor_id": d["donor_id"], "name": d["canonical_name"],
        "zip": d["canonical_zip"], "county_total": round(d["county_total"]),
        "gave_to": d["recipients"], "occupations": (d["occupations"] or "")[:150],
        "employer_strings": (d["employers"] or "")[:150],
        "locations": (d["locations"] or "")[:150],
        "first_gift": d["first_gift"], "last_gift": d["last_gift"],
        "fec_partisan_lean": d["fec_partisan_lean"],
        "fec_donation_count": d["fec_total_donations"],
    } for d in donors[i:i+BATCH_B]]
    json.dump(batch, open(os.path.join(ROOT, f"donorbatch_{i//BATCH_B+1:02d}.json"), "w"), indent=1)
print(f"Stream B: {len(donors)} donors -> {(len(donors)+BATCH_B-1)//BATCH_B} batches")
