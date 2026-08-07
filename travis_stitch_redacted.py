"""Link contributions whose address was fully redacted to the right donor identity.

Some Travis County filings are served with the ENTIRE address block blacked out
— not just the street, but city/state/zip too. travis_ingest.py needs a zip or
an employer to corroborate a name (score >= 0.83), so those rows can never match
and mint a fresh identity instead, splitting a real donor's history in two.

This script reassigns such rows to an existing identity, one explicitly declared
link at a time. Each link is recorded in review_queue with resolved =
'travis-redacted-stitch' so the judgment stays auditable, and the now-empty
minted identity is removed.

Deliberately NOT automatic: matching a bare name to an existing donor is a
judgment call. Every pair below was checked by hand against the page image and
the existing identity's employer/occupation.

Usage: python travis_stitch_redacted.py [--dry-run] [--db PATH]
"""
import argparse
import json
import os
import sqlite3
import sys

# (report_file, donor-as-filed) -> (existing donor_id, why this is the same person)
LINKS = {
    ("2026-07-17_COH.pdf", "Forrest, Hugh"): (
        "a223ba0662091420",
        "Existing identity: Forrest, Hugh — SXSW, zip 78731, 15 prior contributions. "
        "Only Hugh Forrest in the DB; a long-running Austin political donor."),
    ("2026-07-17_COH.pdf", "Guthikonda, Gopal"): (
        "52988df30fd4d0b1",
        "Existing identity: Guthikonda, Gopal — zip 78720, 45 prior contributions. "
        "A second identity (8b662801f49c60ce, zip 78759, 5 rows) is the same person "
        "at a different address; linked to the larger record. Both predate this run."),
    ("2026-07-17_COH.pdf", "Forbes, Thomas"): (
        "0585d656e38551dc",
        "Existing identity: Forbes, Thomas — Butler Snow LLP, zip 78701, 2 prior "
        "contributions. Only Thomas Forbes in the DB."),
    ("2026-07-22_COH.pdf", "Travillion Sr., Jeffrey"): (
        "8ba681ff8f374ba5",
        "Existing identity: Travillion, Jeffrey — Travis County, zip 78768, 3 prior "
        "contributions. This is the filer's own $0.46 contribution to his campaign; "
        "the 'Sr.' suffix is why the name did not normalize to a match."),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db", default="austin_finance.db")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    touched, relinked, dropped = set(), 0, 0
    for (report, donor), (target, why) in LINKS.items():
        rows = cur.execute(
            """SELECT rowid, donor_id, contribution_amount FROM campaign_finance
               WHERE transaction_id LIKE 'TRAVIS-%' AND report_filed LIKE ?
                 AND donor = ?""", (f"%{report}", donor)).fetchall()
        if not rows:
            print(f"  SKIP  no rows for {donor} in {report}")
            continue
        tgt = cur.execute("SELECT canonical_name FROM donor_identities WHERE donor_id=?",
                          (target,)).fetchone()
        if not tgt:
            print(f"  ERROR target identity {target} missing for {donor}")
            continue

        for r in rows:
            old = r["donor_id"]
            if old == target:
                print(f"  OK    {donor}: already linked")
                continue
            cur.execute("""UPDATE campaign_finance SET donor_id=?,
                           match_confidence='travis-redacted-stitch' WHERE rowid=?""",
                        (target, r["rowid"]))
            relinked += 1
            touched.add(target)
            # remove the identity minted for this row if nothing else references it
            if old:
                still = cur.execute(
                    """SELECT count(*) FROM campaign_finance
                       WHERE donor_id=? OR donor_id_2=?""", (old, old)).fetchone()[0]
                if still == 0 and old.startswith("tcv-"):
                    cur.execute("DELETE FROM donor_identities WHERE donor_id=?", (old,))
                    dropped += 1
                elif still == 0:
                    print(f"  NOTE  {old} now has no rows but is not a tcv- id; left in place")
                else:
                    touched.add(old)
            cur.execute("""INSERT INTO review_queue
                (donor_a, donor_b, zip_a, zip_b, emp_occ_a, emp_occ_b, score, resolved)
                VALUES (?,?,?,?,?,?,?,?)""",
                (donor, tgt["canonical_name"], "", "", "", why, 1.0,
                 "travis-redacted-stitch"))
        print(f"  LINK  {donor} ({report}) -> {target} [{len(rows)} row(s)]")

    # rebuild aggregates for every identity whose row set changed
    for did in touched:
        agg = cur.execute(
            """SELECT SUM(CAST(contribution_amount AS REAL)), COUNT(*),
                      MIN(contribution_date), MAX(contribution_date)
               FROM campaign_finance WHERE donor_id=? OR donor_id_2=?""",
            (did, did)).fetchone()
        camps = sorted({r[0] for r in cur.execute(
            "SELECT DISTINCT recipient FROM campaign_finance WHERE donor_id=? OR donor_id_2=?",
            (did, did))})
        cur.execute("""UPDATE donor_identities SET total_donated=?, record_count=?,
                       campaign_count=?, campaigns=?, first_seen=?, last_seen=?
                       WHERE donor_id=?""",
                    (agg[0] or 0, agg[1], len(camps), "|".join(camps),
                     agg[2], agg[3], did))

    print(f"\nrelinked rows: {relinked}; identities recomputed: {len(touched)}; "
          f"minted duplicates removed: {dropped}")
    if args.dry_run:
        print("DRY RUN - rolling back")
        conn.rollback()
    else:
        conn.commit()
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
