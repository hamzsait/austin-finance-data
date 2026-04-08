"""
fix_not_employed_research.py
Reclassifies donors previously lumped as "Not Employed" where research
revealed actual employment / industry.
"""
import sqlite3

DB = "austin_finance.db"

# Each entry: (donor_id, industry, employer_display, notes)
FIXES = [
    # --- Confirmed via employer field / occupation field ---
    ("05f0c927-4aa5-44a4-8a48-ee595be66187", "Technology",            "FloatMe",                         "CRO at FloatMe fintech startup Austin"),
    ("dff9d8d8-aeb4-4c57-adad-31d900ca3250", "Technology",            "FloatMe",                         "CRO at FloatMe fintech startup Austin"),
    ("701b19bf-110f-4dea-8ce7-531b66eb500a", "Healthcare",            "MD Anderson",                     "PA/Advanced Practice Provider at MD Anderson"),
    ("3b369fcc-2335-42ab-9709-af3f94825812", "Healthcare",            "TLC Staffing",                    "COO/CEO TLC Staffing (medical staffing, Victoria TX)"),
    ("0e00d0e3-04ee-466c-bde8-507dcfdce62e", "Healthcare",            "Self (Periodontist)",              "Dr. Syed Shere, DDS, periodontist Houston TX"),
    ("02e0d61c-b076-49a6-aefe-cdd0e56e3a2d", "Energy / Environment",  "Pine Gate Renewables",            "Senior Manager at Pine Gate Renewables"),
    ("8d7745df-7712-4b24-9e6d-aa0984f68355", "Government",            "Friends of Doug Gansler",         "Campaign Manager for MD Gov candidate"),
    ("df4ebb24-dc39-4d54-b478-8b2360113266", "Nonprofit / Advocacy",  "The Asian American Foundation",   "Chief of Staff at The Asian American Foundation"),
    ("2befac0b-705e-49f8-8881-fa0ca8e71ba0", "Nonprofit / Advocacy",  "Working Families Party",          "Organizer at Working Families Party"),
    ("3858b7b1-2aec-4af6-9d49-edf5c8feb5b7", "Nonprofit / Advocacy",  "Scholars Strategy Network",       "Health Policy Associate"),
    ("292e5a3f-cea6-48ab-a18f-403ad0cc4435", "Government",            "Self (TX RRC Candidate)",         "Luke Warford, 2022 TX Railroad Commission candidate"),
    ("a01e6208-6c34-47f8-a779-f4f4730318eb", "Government",            "Self (TX RRC Candidate)",         "Luke Warford, 2022 TX Railroad Commission candidate"),
    ("312f9317-7ba0-4ef1-b152-7753b95b35e0", "Finance",               "PIMCO",                           "Associate at PIMCO (major investment mgmt firm)"),
    ("9bc891c3-3144-4c2e-9100-5b6ae19aaef9", "Consulting / PR",       "Global Strategy Group",           "Research Associate at Global Strategy Group"),
    ("fbdad4a6-17a7-4770-8e10-c1cbdde0399d", "Media",                 "RLF",                             "Digital Marketing at RLF/IDM"),
    ("39e6d063-b0f0-43a2-8cba-c21a675a8db1", "Nonprofit / Advocacy",  "CACC",                            "Voting Rights work at CACC"),
    ("3ebff0a0-0649-4c83-bf07-0322f60d3958", "Technology",            "Cadence Design Systems",          "Engineer at Cadence (semiconductor EDA)"),
    ("574cec51-fc64-4f4a-9f48-8e451b79ad6c", "Technology",            "Need Bot",                        "CEO at Need Bot tech startup"),

    # --- Self-employed, clear industry from occupation ---
    ("2b257abf-7cf0-4f93-9c6a-6192bfc8f61d", "Real Estate",           "Self (Real Estate)",              "Occupation: Real estate"),
    ("2b3a878f-9e0a-4056-b542-76fea1bb013f", "Real Estate",           "Self (Real Estate)",              "Occupation: Real Estate"),
    ("a74fefc0-b40a-44ab-968b-2fa29332dace", "Finance",               "Self (Finance)",                  "Occupation: Finance"),
    ("add90caa-5ebe-4d0f-bf1b-5bc1e09bc18a", "Construction",          "Self (GC)",                       "Occupation: Construction, employer: GC"),
    ("b3c983fa-faea-41ab-928a-618780d24468", "Real Estate",           "Self (Real Estate)",              "Occupation: Real estate"),
    ("697e3983-66b7-40e8-bf7a-9ea372923ae7", "Healthcare",            "Self (Healthcare Mgmt)",          "Occupation: Healthcare Management"),
    ("db2acc93-cca4-4fdd-b4e0-9c456ddbebcc", "Healthcare",            "Self (Healthcare)",               "Occupation: Healthcare"),
    ("f941d56c-72a4-4a3c-9ad0-d845c2cb6c57", "Construction",          "Self (Construction)",             "Occupation: construction"),
    ("16667635-fd56-48de-9e0c-7edc77880fa4", "Real Estate",           "Self (Real Estate)",              "Occupation: Real Estate"),
    ("5a7e08a4-27d3-4848-aa1b-e80e851b4b6f", "Real Estate",           "Self (Real Estate)",              "Occupation: Real Estate"),
    ("f9d59b52-b51e-4d46-8b75-fd90f6f16dfe", "Legal",                 "Self (Attorney)",                 "Occupation: Atty"),
]

def main():
    con = sqlite3.connect(DB, timeout=30)
    cur = con.cursor()

    updated = 0
    for donor_id, industry, employer_display, notes in FIXES:
        cur.execute("""
            UPDATE donor_identities
            SET resolved_industry = ?,
                resolved_employer_display = ?,
                resolved_confidence = 'manual'
            WHERE donor_id = ?
              AND resolved_industry IS NULL
        """, (industry, employer_display, donor_id))
        rows = cur.rowcount
        if rows:
            print(f"  OK {donor_id[:8]}  -> {industry:<25}  [{notes}]")
        else:
            # Maybe already classified or wrong ID
            cur.execute("SELECT canonical_name, resolved_industry FROM donor_identities WHERE donor_id=?", (donor_id,))
            row = cur.fetchone()
            if row:
                print(f"  ~ {donor_id[:8]}  {row[0]} already={row[1]}  (skipped)")
            else:
                print(f"  ! {donor_id[:8]}  NOT FOUND in donor_identities")
        updated += rows

    con.commit()
    con.close()
    print(f"\nDone. Updated {updated} donor_identity rows.")

if __name__ == "__main__":
    main()
