"""Gun-lobby spectrum flags — mirrors ip_spectrum_flag.py / fossil_fuel_flag.py.

Classifies known gun-policy committees in fec_committee_cache (gun_category)
and scores every donor's FEC giving into a gun_spectrum on donor_identities:
  gun_rights   - NRA-PVF, GOA, NAGR, state rifle associations, NSSF (industry)
  gun_control  - Everytown, Giffords, Brady, Stop Gun Violence PAC

Columns added: donor_identities.gun_spectrum / gun_tier / gun_total /
gun_committees; fec_committee_cache.gun_category.

Tiers: 1 = NRA-PVF direct or 3+ gun committees; 2 = 2 committees; 3 = 1.
Full recompute, idempotent, pure SQL — re-run any time after fec_enrich.py.

Only committees verified present in fec_committee_cache are listed (i.e. some
Austin/Travis donor actually gave to them). Deliberately EXCLUDED look-alikes:
"Texas Young Guns Victory Fund" (GOP candidate program, not gun policy),
"Brady Victory Fund"/"Brady Duke for Congress"/"Friends of Brady Walkinshaw"
(candidate committees), "Giffords for Congress" (candidate committee),
"God, Guns, Life PAC" (novelty micro-PAC).
"""
import sqlite3

DB = "austin_finance.db"

# committee_id -> (gun_category, gun_spectrum, display_name)
GUN_COMMITTEES = {
    # ── Gun rights ────────────────────────────────────────────────────────
    "C00053553": ("gun_rights_national", "gun_rights", "NRA Political Victory Fund"),
    "C00030999": ("gun_rights_national", "gun_rights", "Gun Owners of America Campaign Committee"),
    "C00481200": ("gun_rights_national", "gun_rights", "National Association for Gun Rights PAC"),
    "C00380998": ("gun_rights_state",    "gun_rights", "Texas State Rifle Association Federal PAC"),
    "C00480863": ("gun_industry",        "gun_rights", "NSSF PAC (National Shooting Sports Foundation)"),
    # ── Gun control ───────────────────────────────────────────────────────
    "C00688655": ("gun_control", "gun_control", "Everytown for Gun Safety Victory Fund"),
    "C00540443": ("gun_control", "gun_control", "Giffords PAC"),
    "C00674093": ("gun_control", "gun_control", "Brady PAC"),
    "C00113449": ("gun_control", "gun_control", "Brady Campaign Voter Education Fund"),
    "C00819912": ("gun_control", "gun_control", "Stop Gun Violence PAC"),
}

NRA_DIRECT = {"C00053553"}


def add_columns(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(donor_identities)")
    existing = {row[1] for row in cur.fetchall()}
    for col_name, col_type in [("gun_spectrum", "TEXT"), ("gun_tier", "INTEGER"),
                               ("gun_total", "REAL DEFAULT 0"), ("gun_committees", "TEXT")]:
        if col_name not in existing:
            cur.execute(f"ALTER TABLE donor_identities ADD COLUMN {col_name} {col_type}")
            print(f"  Added donor_identities.{col_name}")
    cur.execute("PRAGMA table_info(fec_committee_cache)")
    if "gun_category" not in {row[1] for row in cur.fetchall()}:
        cur.execute("ALTER TABLE fec_committee_cache ADD COLUMN gun_category TEXT")
        print("  Added fec_committee_cache.gun_category")
    conn.commit()


def flag_committees(conn):
    cur = conn.cursor()
    cur.execute("UPDATE fec_committee_cache SET gun_category = NULL")
    flagged = 0
    for cid, (category, _, name) in GUN_COMMITTEES.items():
        cur.execute("UPDATE fec_committee_cache SET gun_category = ? WHERE committee_id = ?",
                    (category, cid))
        if cur.rowcount > 0:
            print(f"  Flagged {cid} ({name}) -> {category}")
            flagged += 1
        else:
            print(f"  Committee {cid} ({name}) not in cache")
    conn.commit()
    print(f"  Total committees flagged: {flagged}")


def score_donors(conn):
    cur = conn.cursor()
    cur.execute("""UPDATE donor_identities SET gun_spectrum = NULL, gun_tier = NULL,
                   gun_total = 0, gun_committees = NULL""")
    cids = list(GUN_COMMITTEES.keys())
    ph = ",".join("?" * len(cids))
    cur.execute(f"""SELECT r.donor_id, r.committee_id, SUM(r.contribution_amount)
                    FROM fec_contributions_raw r WHERE r.committee_id IN ({ph})
                    GROUP BY r.donor_id, r.committee_id""", cids)
    donor_data = {}
    for donor_id, committee_id, total in cur.fetchall():
        d = donor_data.setdefault(donor_id, {"gun_rights": 0.0, "gun_control": 0.0,
                                             "committees": set(), "total": 0.0})
        _, spectrum, _ = GUN_COMMITTEES[committee_id]
        d[spectrum] += total
        d["committees"].add(committee_id)
        d["total"] += total

    print(f"\n  Found {len(donor_data)} donors with gun-committee contributions")
    updated = 0
    for donor_id, d in donor_data.items():
        spectrum = "gun_rights" if d["gun_rights"] >= d["gun_control"] else "gun_control"
        if d["committees"] & NRA_DIRECT or len(d["committees"]) >= 3:
            tier = 1
        elif len(d["committees"]) >= 2:
            tier = 2
        else:
            tier = 3
        cur.execute("""UPDATE donor_identities SET gun_spectrum=?, gun_tier=?,
                       gun_total=?, gun_committees=? WHERE donor_id=?""",
                    (spectrum, tier, d["total"], ",".join(sorted(d["committees"])), donor_id))
        updated += cur.rowcount
    conn.commit()
    print(f"  Updated {updated} donor records with gun spectrum scores")


def report(conn):
    cur = conn.cursor()
    print("\n  Spectrum breakdown:")
    for row in cur.execute("""SELECT gun_spectrum, gun_tier, COUNT(*), SUM(gun_total)
                              FROM donor_identities WHERE gun_spectrum IS NOT NULL
                              GROUP BY 1, 2 ORDER BY 1, 2"""):
        print(f"    {row[0]} tier {row[1]}: {row[2]} donors, ${row[3]:,.0f}")


def main():
    conn = sqlite3.connect(DB, timeout=120)
    print("Adding columns...")
    add_columns(conn)
    print("Flagging committees...")
    flag_committees(conn)
    print("Scoring donors...")
    score_donors(conn)
    report(conn)
    conn.close()


if __name__ == "__main__":
    main()
