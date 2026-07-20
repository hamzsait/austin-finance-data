"""Industry backfill for Neha Shah's donors ahead of the D3 race page
(D3_EXPANSION_PLAN.md SSC/SSE — her filings are five weeks old, so the global
enrichment passes left 27 of 57 donors industry-unresolved).

Two passes, mirroring fix_unclassified_employers.py:
  1. Classify employer_identities rows (global — these companies were
     researched and verified individually; sources in comments).
  2. Donor-level resolution for Shah's donors only: employer-classified
     donors inherit the employer industry; donors whose employer string is
     noise/ambiguous resolve via their reported occupation.

Idempotent — safe to re-run, including on the canonical DB after the
d3-race-page branch merges (worktree DBs are separate copies).

Left unresolved on purpose (no usable employer or occupation; the deferred
affiliation scrub is the right tool): Earp, Hulsey, Sandstrom, Vaze.
Also left alone: the shared 'Confidential' and 'Air' employer rows — too
ambiguous to classify globally; their Shah donors resolve via occupation.

Usage: python d3_research/_backfill_shah_employers.py [--dry-run]
"""
import argparse, sqlite3, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

conn = sqlite3.connect("austin_finance.db")
cur = conn.cursor()

# ── 1. Employer classifications (matched on LOWER(canonical_name)) ──────────
# (name, industry, interest_tags) — verified 2026-07-19:
#   Wayground = edtech, formerly Quizizz (wayground.com/home/from-quizizz-to-wayground)
#   Xtrium = Austin AI/materials-science startup (xtrium.ai/team)
#   CGISF = Consulate General of India, San Francisco (cgisf.gov.in)
#   Urban Sports Ventures = owns/operates Urban Axes venues incl. Austin
#   VS Health Group = biopharma market-access consulting (vshealthgroup.com)
#   GLIDE = SF social-services nonprofit (glide.org), not the app startup
#   Teads = adtech/video advertising platform (merged with Outbrain 2025)
#   MITRE = nonprofit FFRDC operator; systems-engineering R&D for US gov
#   Qcells = solar manufacturer; Agiloft = contract-management software
EMPLOYER_FIXES = [
    ("wayground",              "Technology",            "tech-startup-ecosystem"),
    ("xtrium",                 "Technology",            "tech-startup-ecosystem"),
    ("tech",                   "Technology",            None),
    ("agiloft",                "Technology",            None),
    ("mitre corporation",      "Technology",            None),
    ("teads",                  "Media",                 None),
    ("cgisf",                  "Government",            None),
    ("vs health group",        "Healthcare",            None),
    ("urban sports ventures",  "Hospitality / Events",  None),
    ("glide",                  "Nonprofit / Advocacy",  None),
    ("higher education",       "Education",             "higher-education"),
    ("qcells",                 "Energy / Environment",  None),
    ("constellation brands",   "Retail / Media / Other", None),
]

emp_updated = 0
for name, industry, tags in EMPLOYER_FIXES:
    cur.execute(
        "UPDATE employer_identities SET industry=?, interest_tags=COALESCE(?, interest_tags) "
        "WHERE LOWER(canonical_name)=? AND (industry IS NULL OR industry=?)",
        (industry, tags, name, industry))
    if cur.rowcount:
        print(f"  employer  [{name}] -> {industry}")
        emp_updated += cur.rowcount
print(f"employer_identities updated: {emp_updated}")

# ── 2. Donor-level resolution, scoped to Shah's unresolved donors ────────────
shah_unresolved = {r[0] for r in cur.execute("""
    SELECT DISTINCT di.donor_id
    FROM campaign_finance cf JOIN donor_identities di ON di.donor_id = cf.donor_id
    WHERE cf.recipient = 'Shah, Neha' AND di.resolved_industry IS NULL""")}
print(f"Shah donors still unresolved: {len(shah_unresolved)}")

updates = []  # (industry, display, confidence, donor_id)

# 2a. inherit newly-classified employer industries
for donor_id, industry, emp_name in cur.execute("""
    SELECT DISTINCT di.donor_id, ei.industry, ei.canonical_name
    FROM campaign_finance cf
    JOIN donor_identities di ON di.donor_id = cf.donor_id
    JOIN employer_identities ei ON ei.employer_id = cf.employer_id
    WHERE cf.recipient = 'Shah, Neha' AND di.resolved_industry IS NULL
      AND ei.industry IS NOT NULL""").fetchall():
    updates.append((industry, emp_name, "manual", donor_id))

# 2b. occupation/manual calls for noise or missing employer strings
#     (occupation text is the donor's own filing; Kashi Coves researched but
#     unidentifiable — Mehta's occupation 'Real Estate & Property Management'
#     is decisive on its own)
OCCUPATION_CALLS = {
    "Nakell, Stacy":     ("Healthcare",    "Lotus Therapy, LLC"),
    "Mehta, Mona":       ("Real Estate",   "Kashi Coves"),
    "Schiff, David":     ("Technology",    "defense tech"),
    "Shakra, Fatima":    ("Technology",    "IT Professional"),
    "Karim, Sarah":      ("Self-Employed", "Self-Employed"),
    "Yacob, Suzie":      ("Self-Employed", "Self-Employed"),
    "CLIFFORD, JORDAN":  ("Self-Employed", "Self-Employed"),
    "Millican, James":   ("Self-Employed", "Self-Employed"),
}
claimed = {u[3] for u in updates}
for name, (industry, display) in OCCUPATION_CALLS.items():
    row = cur.execute(
        "SELECT donor_id FROM donor_identities WHERE canonical_name=? AND resolved_industry IS NULL",
        (name,)).fetchone()
    if row and row[0] in shah_unresolved and row[0] not in claimed:
        updates.append((industry, display, "manual", row[0]))

for industry, display, conf, donor_id in updates:
    print(f"  donor {donor_id[:10]}  -> {industry:22} [{display}]")
print(f"donor_identities updates: {len(updates)}")

if args.dry_run:
    print("DRY RUN — rolling back")
    conn.rollback()
else:
    cur.executemany("""
        UPDATE donor_identities
        SET resolved_industry=?, resolved_employer_display=?, resolved_confidence=?
        WHERE donor_id=? AND resolved_industry IS NULL""", updates)
    conn.commit()

n = cur.execute("""
    SELECT COUNT(DISTINCT di.donor_id)
    FROM campaign_finance cf JOIN donor_identities di ON di.donor_id = cf.donor_id
    WHERE cf.recipient='Shah, Neha' AND di.resolved_industry IS NOT NULL""").fetchone()[0]
print(f"Shah donors resolved after run: {n}/57")
conn.close()
