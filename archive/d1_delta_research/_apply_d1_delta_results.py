"""Apply D1 DELTA donor research results to the DB.

Mirrors archive/d1_research/_apply_d1_results.py exactly -- same columns, same
confidence gate, same dedup rule -- but globs d1delta_*_results.json in this
directory and resolves the DB from the repo root (the archived copy pointed at
archive/austin_finance.db, which does not exist).

  d1delta_*_results.json -> donor_identities.resolved_industry /
  resolved_employer_display / resolved_confidence, plus civic_affiliations rows

Only high/medium confidence verdicts are applied; low stays unclassified.
Idempotent: re-applying overwrites the same fields; affiliations are deduped
on (canonical_name, organization). The donor_identities UPDATE fires where
the existing label is NULL or came from a heuristic classifier (anything but
'llm-research-%'), so it never overwrites an earlier research verdict.

Usage (from this directory or anywhere -- paths resolve from the script):
    python _apply_d1_delta_results.py            # apply
    python _apply_d1_delta_results.py --dry-run  # report only, no writes
                                                 # (opens the DB read-only)
"""
import glob
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Works from the repo root (active run) or from archive/<dir>/ (archived copy).
REPO = ROOT.parent.parent if ROOT.parent.name == "archive" else ROOT.parent
DB = REPO / "austin_finance.db"
DRY = "--dry-run" in sys.argv

if DRY:
    # Read-only connection: a dry run cannot write even by accident.
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=120)
else:
    conn = sqlite3.connect(str(DB), timeout=120)
cur = conn.cursor()

d_applied = d_skipped = aff_added = aff_dup = no_name = 0
cat_counts = {}
files = sorted(glob.glob(str(ROOT / "d1delta_*_results.json")))

for f in files:
    for v in json.load(open(f, encoding="utf-8-sig")):
        if v.get("industry") and v.get("confidence") in ("high", "medium"):
            if not DRY:
                # 2026-11-09 gate change (option b): a sourced high/medium
                # research verdict overrides heuristic labels (employer,
                # fec-employer, occupation, *-incr, cross-identity) but never
                # an earlier llm-research verdict. Previous labels for the
                # donors this overrode are in _d1_delta_overridden_labels.csv.
                # Was: WHERE donor_id=? AND resolved_industry IS NULL
                cur.execute("""UPDATE donor_identities SET resolved_industry=?,
                               resolved_employer_display=?, resolved_confidence=?
                               WHERE donor_id=? AND (resolved_industry IS NULL
                                 OR resolved_confidence IS NULL
                                 OR resolved_confidence NOT LIKE 'llm-research-%')""",
                            (v["industry"], v.get("resolved_employer"),
                             f"llm-research-{v['confidence']}", v["donor_id"]))
                d_applied += cur.rowcount
            else:
                d_applied += 1
        else:
            d_skipped += 1

        name = cur.execute("SELECT canonical_name FROM donor_identities WHERE donor_id=?",
                           (v["donor_id"],)).fetchone()
        for a in v.get("affiliations") or []:
            if not name or not name[0] or not a.get("org"):
                no_name += 1
                continue
            dup = cur.execute("""SELECT 1 FROM civic_affiliations
                                 WHERE canonical_name=? AND organization=?""",
                              (name[0], a["org"])).fetchone()
            if dup:
                aff_dup += 1
                continue
            cat_counts[a.get("category") or "(uncategorized)"] = \
                cat_counts.get(a.get("category") or "(uncategorized)", 0) + 1
            if not DRY:
                cur.execute("""INSERT INTO civic_affiliations
                               (canonical_name, organization, role, category, source_url, notes, added_at)
                               VALUES (?,?,?,?,?,?,?)""",
                            (name[0], a["org"], a.get("role"), a.get("category"),
                             a.get("source_url"), v.get("evidence"),
                             datetime.now(timezone.utc).isoformat()))
            aff_added += 1

if not DRY:
    conn.commit()
conn.close()

print(f"{'DRY RUN -- no writes' if DRY else 'APPLIED'}  ({len(files)} result files)")
print(f"donors: {d_applied} resolved, {d_skipped} left null (low/no confidence)")
print(f"civic_affiliations: {aff_added} added, {aff_dup} already present, {no_name} skipped (no name/org)")
if cat_counts:
    print("by category:")
    for k, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"   {k:34} {n}")
