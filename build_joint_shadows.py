"""
build_joint_shadows.py
Credit spouse #2 of every joint contribution.

build_joint_donors.py stores a joint gift ("Armbrust, David/Cheryl") as ONE
row: donor_id = person 1, donor_id_2 = person 2, balanced_amount = half the
gift. No published query reads donor_id_2, so person 2's half was counted
nowhere (~$251K across all recipients as of 2026-08-18). This script:

1. Re-splits joint rows that count at FULL value (balanced_amount NULL or
   equal to the full amount) back to their half share. These crept in when
   mark_restatements.py restored correction-affidavit joint rows to NULL
   before it was joint-aware (fixed alongside this script).
2. Rebuilds SHADOW ROWS: one derived campaign_finance row per live joint
   contribution, carrying person 2's half — donor/donor_id are person 2
   (canonical identity name), employer_id is the parent's employer_id_2
   (build_employer_id2.py's right-hand employer), balanced_amount is the
   remainder half (parent half + shadow half == full amount exactly), and
   transaction_id gains a '-J2' suffix portal ids can never collide with.
   Flagged is_joint_shadow=1.

Shadows are derived data: the pass DELETEs and rebuilds all of them from the
current live parents, so it is idempotent and self-heals after any marking
change. mark_restatements.py ignores is_joint_shadow=1 rows entirely —
liveness always flows parent -> shadow, never the reverse. RUN ORDER:
mark_restatements.py first, then this (fetch_data_incremental.py does both).
"""
import sqlite3

DB = "austin_finance.db"

COPY_COLS = [
    "donor_type", "city_state_zip", "contribution_amount", "contribution_date",
    "contribution_year", "contribution_type", "date_reported", "report_filed",
    "view_report", "donor_reported_occupation", "donor_reported_employer",
    "in_kind_description", "out_of_state_pac", "correction", "match_confidence",
]


def build(db_path: str = DB, dry_run: bool = False):
    conn = sqlite3.connect(db_path, timeout=120)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(campaign_finance)")}
    if "is_joint_shadow" not in cols:
        cur.execute("ALTER TABLE campaign_finance ADD COLUMN is_joint_shadow INTEGER DEFAULT 0")

    # ── 1. Re-split joint parents counting at full value ────────────────────
    resplit = cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(CAST(contribution_amount AS REAL)/2),0)
        FROM campaign_finance
        WHERE is_joint=1 AND donor_id_2 IS NOT NULL
          AND COALESCE(is_joint_shadow,0)=0
          AND CAST(contribution_amount AS REAL) > 0
          AND (balanced_amount IS NULL
               OR ABS(balanced_amount - CAST(contribution_amount AS REAL)) < 0.011)
    """).fetchone()
    print(f"[joint] parents to re-split to half value: {resplit[0]:,} (-${resplit[1]:,.2f})")
    if not dry_run:
        cur.execute("""
            UPDATE campaign_finance
            SET balanced_amount = ROUND(CAST(contribution_amount AS REAL)/2, 2)
            WHERE is_joint=1 AND donor_id_2 IS NOT NULL
              AND COALESCE(is_joint_shadow,0)=0
              AND CAST(contribution_amount AS REAL) > 0
              AND (balanced_amount IS NULL
                   OR ABS(balanced_amount - CAST(contribution_amount AS REAL)) < 0.011)
        """)

    # ── 2. Rebuild shadow rows from live joint parents ──────────────────────
    canonical = dict(cur.execute(
        "SELECT donor_id, canonical_name FROM donor_identities"))
    parsed2 = dict(cur.execute(
        "SELECT rowid_cf, parsed_name_2 FROM joint_donations"))

    parents = cur.execute(f"""
        SELECT rowid, donor, recipient, transaction_id, donor_id_2, employer_id_2,
               balanced_amount, CAST(contribution_amount AS REAL),
               {', '.join(COPY_COLS)}
        FROM campaign_finance
        WHERE is_joint=1 AND donor_id_2 IS NOT NULL
          AND COALESCE(is_joint_shadow,0)=0
          AND COALESCE(balanced_amount, CAST(contribution_amount AS REAL)) > 0
    """).fetchall()

    inserts = []
    for p in parents:
        rowid, donor, recipient, txn, did2, eid2, bal, full = p[:8]
        half2 = round((full or 0.0) - (bal if bal is not None else round((full or 0.0) / 2, 2)), 2)
        if half2 <= 0:
            continue
        name2 = canonical.get(did2) or parsed2.get(rowid) or donor
        inserts.append((name2, recipient, txn + "-J2" if txn else None,
                        did2, half2) + p[8:] + (eid2,))

    n_shadow = cur.execute(
        "SELECT COUNT(*) FROM campaign_finance WHERE is_joint_shadow=1").fetchone()[0]
    print(f"[joint] shadow rows: {n_shadow:,} existing -> {len(inserts):,} rebuilt "
          f"(+${sum(i[4] for i in inserts):,.2f} credited to spouse #2)")

    if dry_run:
        print("[joint] --dry-run: no writes")
        return

    cur.execute("DELETE FROM campaign_finance WHERE is_joint_shadow=1")
    cur.executemany(f"""
        INSERT INTO campaign_finance
            (donor, recipient, transaction_id, donor_id, balanced_amount,
             {', '.join(COPY_COLS)},
             employer_id, is_joint, is_joint_shadow)
        VALUES ({', '.join('?' * (6 + len(COPY_COLS)))}, 1, 1)
    """, inserts)
    conn.commit()
    print("[joint] done")


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    ap.add_argument("--db", default=DB)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    build(args.db, args.dry_run)


if __name__ == "__main__":
    main()
