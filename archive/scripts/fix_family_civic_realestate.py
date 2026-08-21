"""
fix_family_civic_realestate.py
- Reclassifies Qadri family (same last name) -> Family
- Reclassifies Shamsi/Sait donors (confirmed property owners) -> Real Estate
- Reclassifies Levinson, Kimberly (Austin Downtown Commission VP) -> Government
"""
import sqlite3

DB = "austin_finance.db"

FIXES = [
    # --- Qadri family (candidate's family, same last name) ---
    ("816bd583-e0fb-4ba0-984a-471cdbba2016", "Family", "Candidate Family", "Qadri, Farah - candidate family"),
    ("444d13da-3b62-4b41-87fd-564ce12f01ea", "Family", "Candidate Family", "Qadri, Zoha - candidate family"),
    ("78dafd6a-4ae7-4ee5-bfd4-9aadc3c7d3f8", "Family", "Candidate Family", "Qadri, Zoha - candidate family"),
    ("ae65302f-34cc-4b75-b786-a5cee0ff6201", "Family", "Candidate Family", "Qadri, Zoha - candidate family"),

    # --- Shamsi family (user's family, confirmed property owners in Austin) ---
    ("7fc5a410-c446-4990-988b-aa62e3793bdf", "Real Estate", "Private Property Owner", "Sabiha Shamsi - multiple Austin properties (BuildZoom, Woodland Oaks Ct, Longview St)"),
    ("f5fcc476-538f-412e-afc0-3d9caf036515", "Real Estate", "Private Property Owner", "Sabiha Shamsi - multiple Austin properties"),
    ("cc534fb2-99bc-485c-b005-a37fed0b19ba", "Real Estate", "Private Property Owner", "Shamsi, Farhat - property owner family member"),
    ("b559cc3a-6fce-4f72-88c0-2122fee67a6a", "Real Estate", "Private Property Owner", "Shamsi, Naila - multiple Austin properties (Woodland Oaks Ct)"),
    ("7d3666d3-458c-4b06-ab01-69551d78fdea", "Real Estate", "Private Property Owner", "Shamsi, Naila - multiple Austin properties"),
    ("a8e5cff2-1d17-4cfa-8f41-0817bc25ac89", "Real Estate", "Private Property Owner", "Shamsi, Naila - multiple Austin properties"),
    ("f14dccc5-80ec-40ca-b8fb-7f22a04cdbad", "Real Estate", "Private Property Owner", "Syed, Shamsi - family member, property owner"),
    ("5a43326e-cc61-4a58-bb79-901f28741ea2", "Real Estate", "Private Property Owner", "Syed, Shamsi - family member, property owner"),

    # --- Sait family (confirmed property owners) ---
    ("33b850ce-6141-4216-845e-d29fdd22face", "Real Estate", "Private Property Owner", "Sait, Esa - property owner"),
    ("e960d4b2-85d1-46e4-a5e6-06715135ef98", "Real Estate", "Private Property Owner", "Sait, Esa - property owner"),
    ("1476077f-6f9f-40b1-ae7a-343b5e9dceec", "Real Estate", "Private Property Owner", "Sait, Esa - property owner"),

    # --- Levinson, Kimberly - Austin Downtown Commission VP + Neighborhood Assoc president ---
    ("d08f2c5f-8aca-40f7-97aa-9a8d1a25d64b", "Government", "Austin Downtown Commission", "VP Downtown Commission, Chair Pedestrian Advisory Council, president Downtown Austin Neighborhood Assoc"),
    ("eb29931b-1c65-4ebc-ae4d-e1ec53fe92d6", "Government", "Austin Downtown Commission", "VP Downtown Commission, Chair Pedestrian Advisory Council, president Downtown Austin Neighborhood Assoc"),
]

def main():
    con = sqlite3.connect(DB, timeout=30)
    cur = con.cursor()

    updated = 0
    skipped = 0
    for donor_id, industry, employer_display, notes in FIXES:
        cur.execute("""
            UPDATE donor_identities
            SET resolved_industry = ?,
                resolved_employer_display = ?,
                resolved_confidence = 'manual'
            WHERE donor_id = ?
              AND resolved_industry IS NULL
        """, (industry, employer_display, donor_id))
        if cur.rowcount:
            print(f"  OK {donor_id[:8]}  -> {industry:<22}  {notes[:70]}")
            updated += 1
        else:
            cur.execute("SELECT canonical_name, resolved_industry FROM donor_identities WHERE donor_id=?", (donor_id,))
            row = cur.fetchone()
            if row:
                print(f"  ~  {donor_id[:8]}  {row[0]} already={row[1]} (skipped)")
            else:
                print(f"  !  {donor_id[:8]}  NOT FOUND")
            skipped += 1

    con.commit()
    con.close()
    print(f"\nDone. Updated {updated}, skipped {skipped}.")

if __name__ == "__main__":
    main()
