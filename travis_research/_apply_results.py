"""Apply Opus research results to the DB.

- empbatch_*_results.json  -> employer_identities.industry / interest_tags
- donorbatch_*_results.json -> donor_identities.resolved_industry /
  resolved_employer_display / resolved_confidence, plus civic_affiliations rows
Only high/medium confidence verdicts are applied; low stays unclassified.
Idempotent: re-applying overwrites the same fields; affiliations are deduped
on (canonical_name, organization).
"""
import glob, json, os, sqlite3
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "..", "austin_finance.db")
conn = sqlite3.connect(DB, timeout=120)
cur = conn.cursor()

e_applied = e_skipped = 0
for f in sorted(glob.glob(os.path.join(ROOT, "empbatch_*_results.json"))):
    for v in json.load(open(f, encoding="utf-8-sig")):
        if v.get("industry") and v.get("confidence") in ("high", "medium"):
            cur.execute("""UPDATE employer_identities SET industry=?, interest_tags=?
                           WHERE employer_id=? AND (industry IS NULL OR industry='')""",
                        (v["industry"], v.get("interest_tags") or None, v["employer_id"]))
            e_applied += cur.rowcount
        else:
            e_skipped += 1

d_applied = d_skipped = aff_added = 0
for f in sorted(glob.glob(os.path.join(ROOT, "donorbatch*_results.json"))):
    for v in json.load(open(f, encoding="utf-8-sig")):
        if v.get("industry") and v.get("confidence") in ("high", "medium"):
            cur.execute("""UPDATE donor_identities SET resolved_industry=?,
                           resolved_employer_display=?, resolved_confidence=?
                           WHERE donor_id=? AND resolved_industry IS NULL""",
                        (v["industry"], v.get("resolved_employer"),
                         f"llm-research-{v['confidence']}", v["donor_id"]))
            d_applied += cur.rowcount
        else:
            d_skipped += 1
        name = cur.execute("SELECT canonical_name FROM donor_identities WHERE donor_id=?",
                           (v["donor_id"],)).fetchone()
        for a in v.get("affiliations") or []:
            if not name or not a.get("org"):
                continue
            dup = cur.execute("""SELECT 1 FROM civic_affiliations
                                 WHERE canonical_name=? AND organization=?""",
                              (name[0], a["org"])).fetchone()
            if dup:
                continue
            cur.execute("""INSERT INTO civic_affiliations
                           (canonical_name, organization, role, category, source_url, notes, added_at)
                           VALUES (?,?,?,?,?,?,?)""",
                        (name[0], a["org"], a.get("role"), a.get("category"),
                         a.get("source_url"), v.get("evidence"),
                         datetime.now(timezone.utc).isoformat()))
            aff_added += 1

conn.commit()
print(f"employers: {e_applied} classified, {e_skipped} left null (low/none)")
print(f"donors: {d_applied} resolved, {d_skipped} left null")
print(f"civic_affiliations added: {aff_added}")
