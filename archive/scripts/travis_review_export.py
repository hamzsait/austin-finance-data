"""Export the travis-pending identity review queue as a human-reviewable CSV.

Each row: a county donor (kept as its own new identity) vs. the closest
existing Austin identity that scored 0.65-0.83 (below the auto-merge bar).
Fill the `decision` column with MERGE or SEPARATE (leave blank = SEPARATE),
then run:  python travis_apply_review.py travis_identity_review.csv
"""
import csv, sqlite3
from rapidfuzz import fuzz

DB = "austin_finance.db"
OUT = "travis_identity_review.csv"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

rows = cur.execute("""
    SELECT rowid AS qid, donor_a, donor_b, zip_a, zip_b, emp_occ_a, emp_occ_b, score
    FROM review_queue WHERE resolved='travis-pending' ORDER BY score DESC
""").fetchall()

def first_name(name):
    parts = (name or "").split(",")
    return parts[1].strip().split()[0].lower() if len(parts) > 1 and parts[1].strip() else ""

out = []
for r in rows:
    # county-side context: dollars + which official(s)
    a = cur.execute("""
        SELECT SUM(CAST(contribution_amount AS REAL)) AS amt,
               GROUP_CONCAT(DISTINCT recipient) AS recips
        FROM campaign_finance
        WHERE transaction_id LIKE 'TRAVIS-%' AND donor = ?""", (r["donor_a"],)).fetchone()
    # existing-identity context
    b = cur.execute("""
        SELECT total_donated, campaigns, fec_matched, fec_partisan_lean
        FROM donor_identities WHERE canonical_name = ? ORDER BY total_donated DESC LIMIT 1
    """, (r["donor_b"],)).fetchone()

    fa, fb = first_name(r["donor_a"]), first_name(r["donor_b"])
    fscore = fuzz.token_sort_ratio(fa, fb) / 100.0 if fa and fb else 0
    if fscore >= 0.9 and r["score"] >= 0.75:
        suggest = "MERGE?"
    elif fscore < 0.6:
        suggest = "SEPARATE"
    else:
        suggest = ""

    out.append({
        "decision": "",
        "suggested": suggest,
        "score": round(r["score"], 3),
        "county_donor": r["donor_a"],
        "county_zip": r["zip_a"],
        "county_emp_occ": r["emp_occ_a"],
        "county_total_$": round(a["amt"] or 0),
        "county_gave_to": a["recips"],
        "existing_identity": r["donor_b"],
        "existing_zip": r["zip_b"],
        "existing_emp_occ": r["emp_occ_b"],
        "existing_total_$": round((b["total_donated"] if b else 0) or 0),
        "existing_campaigns": (b["campaigns"] if b else "") or "",
        "existing_has_fec": (b["fec_matched"] if b else 0) or 0,
        "qid": r["qid"],
    })

# order: my-suggestion-first (MERGE? on top), then score
out.sort(key=lambda x: (x["suggested"] != "MERGE?", -x["score"]))
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader(); w.writerows(out)

n_merge = sum(1 for o in out if o["suggested"] == "MERGE?")
print(f"wrote {len(out)} pairs to {OUT}; {n_merge} suggested MERGE? (review those first)")
