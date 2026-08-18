"""
mark_restatements.py
Suppress double-listed transactions the portal publishes once per report.

Two sources of duplication, both discovered 2026-08-17 (the SA repo hit the
same portal behavior — see san-antonio-finance-data PR #22):

1. Correction affidavits (CORCOH/CORPAC). A correction re-files the complete
   report, and the portal keeps BOTH filings' rows. fix_corrections_and_names.py
   used to blanket-zero the correction rows (correction='X'), which avoided the
   double-count but kept the STALE pre-correction values live and silently
   drifted as incremental fetches ingested new correction rows (63 unzeroed by
   2026-08-17). This script inverts the direction: when a correction instance
   covers >=50% of an earlier non-correction instance for the same recipient,
   the ORIGINAL report's rows are zeroed and the correction's rows are restored
   — the corrected filing is the authoritative one. Corrections with no
   matching original in the DB stay live (they are the only listing).

2. Overlapping ordinary reports (pre-election reports re-listed by the next
   semi-annual, double-submitted same-day filings). Among live rows, identical
   (donor, recipient, amount, date, type) twins spanning different report
   instances keep one instance's copies (most rows, then lowest instance id);
   the rest are zeroed. Repeat same-day gifts inside a single report are never
   touched — a report instance is the transaction_id prefix (R<timestamp>).

Mechanism: the repo-wide convention balanced_amount=0.0 — every consumer
already reads COALESCE(balanced_amount, contribution_amount) and filters > 0,
so no query changes are needed. Restores only touch rows whose
balanced_amount is exactly 0 (joint-split values are non-zero and preserved);
if a joint row was blanket-zeroed in the past, re-run build_joint_donors.py.

Idempotent — re-run after every ingest (fetch_data_incremental.py's runbook
step). --dry-run prints what would change.
"""
import argparse
import sqlite3
from collections import defaultdict

DB = "austin_finance.db"


def instance_key(txn_id, report_filed, recipient):
    """Report instance: transaction_id prefix (R<timestamp>). Travis County
    PDF rows have no portal transaction_id scheme; fall back to the report
    label + recipient so each PDF is its own instance."""
    if txn_id and "-" in txn_id:
        return txn_id.split("-")[0]
    return "RF:" + (report_filed or "") + "|" + (recipient or "")


def mark(db_path: str = DB, dry_run: bool = False):
    conn = sqlite3.connect(db_path, timeout=120)
    conn.execute("PRAGMA journal_mode=WAL")

    rows = conn.execute("""
        SELECT rowid, donor, recipient, contribution_amount, contribution_date,
               COALESCE(contribution_type,''), report_filed, transaction_id,
               balanced_amount, CAST(contribution_amount AS REAL)
        FROM campaign_finance""").fetchall()

    inst_rows = defaultdict(list)
    for r in rows:
        inst_rows[instance_key(r[7], r[6], r[2])].append(r)

    def is_correction(k):
        t = inst_rows[k][0][6] or ""
        return t.startswith("CORCOH") or t.startswith("CORPAC")

    def idkeys(k):
        return {(r[1], r[3], r[4], r[5]) for r in inst_rows[k]}

    by_rec = defaultdict(list)
    for k in inst_rows:
        by_rec[inst_rows[k][0][2]].append(k)

    # ── Pass 1: correction affidavits supersede the reports they re-file ─────
    superseded, matched_corr = set(), set()
    for k in inst_rows:
        if not is_correction(k):
            continue
        ck = idkeys(k)
        for o in by_rec[inst_rows[k][0][2]]:
            if o == k or is_correction(o):
                continue
            ok = idkeys(o)
            if ok and len(ck & ok) / len(ok) >= 0.5:
                superseded.add(o)
                matched_corr.add(k)

    zero_rowids = []       # rows to set balanced_amount = 0.0
    restore_rowids = []    # correction rows to restore (balanced_amount 0 -> NULL)
    for k in superseded:
        for r in inst_rows[k]:
            if r[8] is None or r[8] != 0:
                zero_rowids.append(r[0])
    for k in matched_corr:
        for r in inst_rows[k]:
            if r[8] == 0:
                restore_rowids.append(r[0])

    # ── Pass 2: identical twins across ordinary overlapping reports ─────────
    # Evaluate against post-pass-1 liveness.
    dead = set(zero_rowids)
    restored = set(restore_rowids)

    def live_amt(r):
        if r[0] in dead:
            return 0.0
        if r[0] in restored:
            return r[9] or 0.0
        eff = r[8] if r[8] is not None else r[9]
        return eff or 0.0

    groups = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if live_amt(r) > 0:
            k = instance_key(r[7], r[6], r[2])
            groups[(r[1], r[2], r[3], r[4], r[5])][k].append(r[0])
    twin_rowids = []
    for key, by_inst in groups.items():
        if sum(len(v) for v in by_inst.values()) < 2 or len(by_inst) < 2:
            continue
        keep = max(by_inst, key=lambda k2: (len(by_inst[k2]), k2))
        for k2, rids in by_inst.items():
            if k2 != keep:
                twin_rowids.extend(rids)

    print(f"[restate] correction instances matched: {len(matched_corr)} "
          f"superseding {len(superseded)} original report instances")
    print(f"[restate] rows to zero (superseded originals): {len(zero_rowids):,}")
    print(f"[restate] correction rows to restore:          {len(restore_rowids):,}")
    print(f"[restate] residual cross-report twins to zero: {len(twin_rowids):,}")

    if dry_run:
        print("[restate] --dry-run: no writes")
        return

    cur = conn.cursor()
    # A restored correction row can itself be a pass-2 twin (two corrections
    # covering the same original); the twin zeroing must win or re-runs would
    # oscillate between restoring and zeroing it.
    final_restore = set(restore_rowids) - set(twin_rowids)
    cur.executemany("UPDATE campaign_finance SET balanced_amount=0.0 WHERE rowid=?",
                    [(x,) for x in zero_rowids + twin_rowids])
    cur.executemany("UPDATE campaign_finance SET balanced_amount=NULL WHERE rowid=?",
                    [(x,) for x in final_restore])
    conn.commit()
    print("[restate] done")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--db", default=DB)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    mark(args.db, args.dry_run)


if __name__ == "__main__":
    main()
