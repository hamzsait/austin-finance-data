"""
Generate proisrael_council.json — pro-Israel donor network data for all
current Austin City Council members and the Mayor.
"""

import sqlite3, json, os

DB = os.path.join(os.path.dirname(__file__), "austin_finance.db")
OUT = os.path.join(os.path.dirname(__file__), "proisrael_council.json")

# Current council (2026) — recipient string must match campaign_finance.recipient
COUNCIL = [
    {"name": "Kirk Watson",           "recipient": "Watson, Kirk P.",               "district": "Mayor (At-Large)"},
    {"name": "Natasha Harper-Madison", "recipient": "Harper-Madison, Natasha N.",   "district": "District 1"},
    {"name": "Vanessa Fuentes",       "recipient": "Fuentes, Vanessa",              "district": "District 2"},
    {"name": "Jose Velasquez",        "recipient": "Velasquez, Jose",               "district": "District 3"},
    {"name": "Jose 'Chito' Vela",     "recipient": "Vela, Jose \"Chito\", III",     "district": "District 4"},
    {"name": "Ryan Alter",            "recipient": "Alter, Ryan",                   "district": "District 5"},
    {"name": "Mackenzie Kelly",       "recipient": "Kelly, Mackenzie",              "district": "District 6"},
    {"name": "Leslie Pool",           "recipient": "Pool, Leslie",                  "district": "District 7"},
    {"name": "Paige Ellis",           "recipient": "Ellis, Paige",                  "district": "District 8"},
    {"name": "Zohaib Qadri",          "recipient": "Qadri, Zohaib",                "district": "District 9"},
    {"name": "Marc Duchen",           "recipient": "Duchen, Marc",                  "district": "District 10"},
]

SPECTRUM_LABELS = {
    "hawkish_proisrael": "AIPAC-aligned / Hawkish Pro-Israel",
    "liberal_zionist":   "Liberal Zionist",
}

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pre-fetch committee names for display
    cur.execute("SELECT committee_id, committee_name, ip_category FROM fec_committee_cache WHERE ip_category IS NOT NULL")
    committees = {r["committee_id"]: {"name": r["committee_name"], "category": r["ip_category"]} for r in cur.fetchall()}

    results = []

    for member in COUNCIL:
        # Get donors with pro-Israel spectrum who donated to this council member
        cur.execute("""
            SELECT
                di.donor_id,
                di.canonical_name,
                di.ip_spectrum,
                di.ip_tier,
                di.ip_total,
                di.ip_committees,
                SUM(COALESCE(cf.balanced_amount, CAST(cf.contribution_amount AS REAL))) AS local_total,
                COUNT(*) AS num_donations
            FROM campaign_finance cf
            JOIN donor_identities di ON cf.donor_id = di.donor_id
            WHERE cf.recipient = ?
              AND di.ip_spectrum IS NOT NULL
              AND cf.correction != 'X'
            GROUP BY di.donor_id
            ORDER BY local_total DESC
        """, (member["recipient"],))

        donors = []
        total_local = 0.0
        total_local_hawkish = 0.0
        total_local_liberal = 0.0
        total_federal_ip = 0.0

        for row in cur.fetchall():
            local_amt = row["local_total"] or 0
            federal_amt = row["ip_total"] or 0
            total_local += local_amt
            total_federal_ip += federal_amt

            if row["ip_spectrum"] == "hawkish_proisrael":
                total_local_hawkish += local_amt
            else:
                total_local_liberal += local_amt

            # Resolve committee names
            comm_ids = (row["ip_committees"] or "").split(",")
            comm_list = []
            for cid in comm_ids:
                cid = cid.strip()
                if cid and cid in committees:
                    comm_list.append({
                        "id": cid,
                        "name": committees[cid]["name"],
                        "category": committees[cid]["category"],
                    })
                elif cid:
                    comm_list.append({"id": cid, "name": cid, "category": "unknown"})

            donors.append({
                "name": row["canonical_name"],
                "spectrum": row["ip_spectrum"],
                "spectrum_label": SPECTRUM_LABELS.get(row["ip_spectrum"], row["ip_spectrum"]),
                "tier": row["ip_tier"],
                "local_total": round(local_amt, 2),
                "federal_ip_total": round(federal_amt, 2),
                "num_local_donations": row["num_donations"],
                "committees": comm_list,
            })

        results.append({
            "name": member["name"],
            "district": member["district"],
            "recipient_key": member["recipient"],
            "total_from_ip_donors": round(total_local, 2),
            "total_hawkish": round(total_local_hawkish, 2),
            "total_liberal_zionist": round(total_local_liberal, 2),
            "total_federal_ip": round(total_federal_ip, 2),
            "donor_count": len(donors),
            "donors": donors,
        })

    # Sort by total descending
    results.sort(key=lambda x: x["total_from_ip_donors"], reverse=True)

    payload = {
        "generated": "2026-04-08",
        "methodology": (
            "This data identifies Austin campaign donors who ALSO donated to "
            "AIPAC PAC, United Democracy Project, or other pro-Israel committees "
            "at the federal level. The local dollar amounts shown are what these "
            "donors gave to Austin council campaigns — NOT money from AIPAC or "
            "any pro-Israel committee directly."
        ),
        "members": results,
    }

    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {OUT}")
    print(f"\nSummary:")
    for m in results:
        print(f"  {m['district']:20s} {m['name']:30s} ${m['total_from_ip_donors']:>10,.2f}  ({m['donor_count']} donors)")

if __name__ == "__main__":
    main()
