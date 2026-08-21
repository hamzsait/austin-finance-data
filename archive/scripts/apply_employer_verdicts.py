"""
Apply manual review verdicts for the 0.80–0.85 employer score band,
then merge confirmed-same employer_identities clusters.
"""

import sqlite3
import uuid
from collections import defaultdict

DB = "austin_finance.db"

# ── Pairs explicitly confirmed as DIFFERENT during manual review ───────────────
# All other pairs in the 0.80–0.85 band default to same_entity = 1.
DIFFERENT_PAIRS = {
    # noise / job titles
    ("Dun  & Bradstreet", "Dun and Broadstreet"),
    ("Public Relations", "Public Relations Consultant"),
    ("Public Relations", "Public Relations, Sponsorship"),
    ("Chief Officer", "Chief Strategy Officer"),
    ("Chief Financial Officer", "Chief Officer"),
    ("Managing Director", "Managing Director-Investments"),
    ("Public Affairs Executive", "Public affairs"),
    ("Engineering Firm", "Engineering Mgr"),
    ("Senior Director of Marketing", "Senior Marketing"),
    ("Senior Director of Marketing", "Senior director"),
    ("Senior Digital Marketing Manager", "Senior Marketing"),
    ("Civil Engineer", "Civil Team Engineers"),
    ("Director of Operations", "Director of Partner Relations"),
    ("Business Analyst", "Business Intelligence Analyst"),
    ("Government Affairs Manager", "Governmental Affairs"),
    ("Government & Regulatory Affairs Direct", "Government Affairs"),
    ("Policy Analyst", "Policy researcher/analyst"),
    ("Vice President", "Vice President, Controller"),
    ("Urban Planner", "Urban Planning"),
    ("Real Estate", "Real Estate Partner"),
    ("Real Estate", "Real Estate Appraiser"),
    ("Real Estate", "Real Estate Developer"),
    ("Real Estate", "Real Estate Commission"),
    ("Real Estate Developer", "Real Estate Development and Management"),
    ("Real Estate Developer", "Real estate development self"),
    ("Real Estate Community Development", "Real Estate Development Associate"),
    ("Self Real Estate Development", "Self real estate"),
    ("Self / Self", "Self/Spouse"),
    ("Web Developer", "Web Developer & Analytics"),
    ("Construction", "Constructive Ventures"),
    ("Developer", "Development"),
    ("Software Enginer", "Software Manager"),
    ("Founder and Principal Consultant", "Founder/Principal"),
    ("Non Profit", "Non-profit manager"),
    ("Non Profit", "non-profit director"),
    ("Non profit leader", "Non-profit manager"),
    ("Attorney/CPA", "attorney / attorney"),
    ("None Other", "None/none"),
    ("Unemployer", "Unemplyed"),
    ("Unemplyed", "unemployef"),
    ("Hospital", "Hospitality"),
    # different companies / orgs
    ("Big Media", "Big Medium"),
    ("John Bryant Campaign", "John Bucy Campaign"),
    ("Accentcare", "Accenture"),
    ("CONTRACT", "Contractors Inc"),
    ("Citizenarts", "Citizens Inc."),
    ("Strategic Assoc Management", "Strategist"),
    ("Plains Capital Bank", "Plains National Bank"),
    ("Veterans Affairs Administration", "Veterans Healthcare Administration"),
    ("Community Arts", "Community affairs"),
    ("Community Arts", "Community Brands"),
    ("Community Activist", "Community Arts"),
    ("ApartmentData.com", "Apartments.com"),
    ("Pecan Street Advisors", "Pecan Street Association"),
    ("Center for Budget & Policy Priorities", "Center for Public Policy Priorities"),
    ("First Onsite", "First United"),
    ("First Bank & Trust", "First State Bank"),
    ("Native Smart Properties", "Native Solar"),
    ("ONE Gas", "One A"),
    ("One A", "One Man"),
    ("One A", "One Gas Inc."),
    ("One A", "One Gas, Inc"),
    ("Realty Austin", "Realty Haus"),
    ("Greater Austin Homes LLC", "Greater Austin YMCA"),
    ("Greater Austin Homes LLC", "Greater Austin Orthopaedics"),
    ("The Stewart Law Firm", "The Stratton Law Firm, PLLC"),
    ("Urban Institute", "Urban Land Institute Austin"),
    ("Pennsylvania House Democratic Campaign Committee", "Pennsylvania House Democratic Caucus"),
    ("SouthState Bank", "Southside Bank"),
    ("The Mullen Firm PLLC", "The Mundy Firm PLLC"),
    ("Sheryl Cole & Assoc", "Sheryl Cole Campaign"),
    ("Sheryl Cole & Associates LLC", "Sheryl Cole Campaign"),
    ("Sheryl Cole & Associates, LLC", "Sheryl Cole Campaign"),
    ("Mt. Sinai Baptist Church", "Mt. Vernon Baptist Church"),
    ("Affordable housing", "Affordable Sound"),
    ("Affordable Housing Visions for Texas, Inc.", "Affordable housing"),
    ("Affordable housing", "Affordable Sounds"),
    ("Advantest", "Advantis Global"),
    ("Connect", "Connectors"),
    ("Global Strategy Group", "Strategic Assoc Management"),
    ("InterNet Properties", "Internews"),
    ("PELOTONIA", "PelotonU"),
    ("Service", "ServiceMac"),
    ("Service", "ServiceNow"),
    ("The University Of Texas at Arlington", "The University og Texas at Austin"),
    ("Studio A Group", "Studio Image, Inc."),
    ("Studio A Group", "Studio KFS LLC"),
    ("Studio 8", "Studio KFS LLC"),
    ("Studio KFS LLC", "Studio 8"),
    ("Friends of the Children Austin", "Friends of the Children Texas"),
    ("New York City Council", "New York City DOE"),
    ("Unitarian Universalist Association", "Unitarian Universalist Ministry for Earth"),
    ("Fritz Bryce PLLC", "Fritz Byrne"),
    ("Global Information Technology, Inc.", "Informatica"),
    ("Blue Sky Co", "Blue Sky Scrubs"),
    ("KB Homes", "KB Kustom Homes"),
    ("Asian American Community Partnership", "Asian American journalist association"),
    ("Asian American Community Partnership", "Asian American journalists association"),
    ("Asian American Community Partnership", "Asian American PAC"),
    ("U.S. Department of State", "U.S. Department of the Treasury"),
    ("The University of Texas School of Law", "The University of Texas at Austin Dell Medical School"),
    ("Cypress Invest", "Cypress Point"),
    ("REAL Strategies", "Real Storage"),
    ("Andy Brown & Associates PLLC", "Andy Brown Campaign"),
    ("Department of Defense", "Department of Defense Dependents Schools"),
    ("Taylor Collective", "Taylor Creative Solutions"),
    ("The Brannan Firm", "The Bratton Firm PC"),
    ("Credit Union Department", "Credit Union National Association"),
    ("The Resource Foundation", "The Resource Group"),
    ("Opportunity Austin", "Opportunity Hub"),
    ("Opportunity Hub", "Opportunity Austin"),
    ("Blue Edge Strategies", "Blue Roots Strategies"),
    ("Charles Butt Foundation", "Charles Moore Foundation"),
    ("Hill Country Conservancy", "Hill Country Counseling"),
    ("Hill Country Counseling", "Hill Country Conservancy"),
    ("Southern Company", "Southern Leasing & Rental Company"),
    ("Black + Motal Architecture and Urban Design", "Black and Vernon Architecture"),
    ("KIPP Austin Public Schools", "KIPP Bay Area Public Schools"),
    ("The University Of Texas at Austin", "The University of Texas System"),
    ("Dell Children's Medical Center", "Dell Seton Medical Center"),
    ("Red Fort Strategies", "Red River Strategies"),
    ("Affinity Answers", "Affinity Waste Solutions"),
    ("Barton Law Office", "Barton Roscher Law"),
    ("Blue Haven", "Blue Heron Holdings"),
    ("Capitol Chevy", "Capitol Core Group"),
    ("CommUnity Care", "Community Care Collaborative"),
    ("Department of Health", "Department of Neurology, UT Health Austin"),
    ("El Paso County", "el paso"),
    ("El Patio", "el paso"),
    ("Free Lance", "free lunch"),
    ("Global Wildlife Conservation", "National Wildlife Federation"),
    ("Legacy MCS", "Legacy PAC"),
    ("Alchemer", "Alchemy"),
    ("Centurion", "CenturyLink"),
    ("City Austin", "City auto"),
    ("Energy Services", "EnergyHub"),
    ("Engine", "Engineeer"),
    ("Engineeer", "Engineering"),
    ("Experian", "Experis"),
    ("Global Transplant Solutions", "Transplace"),
    ("Goodwill", "Goodwin Management, Inc."),
    ("Goodwill", "Goodwin Partners"),
    ("Intern", "Internews"),
    ("Person", "Personify"),
    ("Spectra Group inc", "Spectrum"),
}

# ── Build a lookup set that checks both orderings ─────────────────────────────
def is_different(a, b):
    return (a, b) in DIFFERENT_PAIRS or (b, a) in DIFFERENT_PAIRS

# ── Union-Find ────────────────────────────────────────────────────────────────
class UnionFind:
    def __init__(self):
        self.parent = {}
        self.rank   = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x]   = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

def main():
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()

    # ── Step 1: Apply verdicts to review queue ────────────────────────────────
    print("Applying verdicts to employer_review_queue...")

    # Default all 0.80-0.85 pairs to same_entity=1
    cur.execute("""
        UPDATE employer_review_queue
        SET same_entity = 1, resolved = 1
        WHERE score >= 0.80 AND score < 0.85
    """)
    total_marked = cur.rowcount
    print(f"  Defaulted {total_marked} pairs to same_entity=1")

    # Override known different pairs
    different_count = 0
    cur.execute("""
        SELECT rowid, employer_a, employer_b
        FROM employer_review_queue
        WHERE score >= 0.80 AND score < 0.85
    """)
    rows = cur.fetchall()
    diff_rowids = []
    for rowid, ea, eb in rows:
        if is_different(ea, eb):
            diff_rowids.append(rowid)

    if diff_rowids:
        placeholders = ",".join("?" * len(diff_rowids))
        cur.execute(f"""
            UPDATE employer_review_queue
            SET same_entity = 0
            WHERE rowid IN ({placeholders})
        """, diff_rowids)
        different_count = cur.rowcount

    print(f"  Overrode {different_count} pairs to same_entity=0 (false positives)")

    same_count = total_marked - different_count
    print(f"  Final: {same_count} same, {different_count} different")

    # ── Step 2: Load all same_entity=1 pairs for merging ─────────────────────
    print("\nLoading all confirmed-same pairs for merging...")
    cur.execute("""
        SELECT employer_a, employer_b
        FROM employer_review_queue
        WHERE same_entity = 1 AND resolved = 1
    """)
    same_pairs = cur.fetchall()
    print(f"  {len(same_pairs):,} pairs to merge")

    # ── Step 3: Load existing employer_id mapping ─────────────────────────────
    print("Loading employer identity map...")
    cur.execute("""
        SELECT employer_id, canonical_name, name_variants, record_count
        FROM employer_identities
    """)
    identity_rows = cur.fetchall()

    # Build: canonical_name → employer_id
    name_to_id = {}
    id_to_info = {}
    for eid, cname, variants, cnt in identity_rows:
        name_to_id[cname] = eid
        # Also map all variants
        if variants:
            for v in variants.split("|"):
                v = v.strip()
                if v:
                    name_to_id[v] = eid
        id_to_info[eid] = {"canonical": cname, "count": cnt or 0}

    print(f"  {len(id_to_info):,} existing employer identities")

    # ── Step 4: Union-Find merging ────────────────────────────────────────────
    print("Running union-find on confirmed-same pairs...")
    uf = UnionFind()

    # Initialize all known employer_ids
    for eid in id_to_info:
        uf.find(eid)

    merged = 0
    unresolved = 0
    for ea, eb in same_pairs:
        id_a = name_to_id.get(ea)
        id_b = name_to_id.get(eb)
        if id_a and id_b and id_a != id_b:
            root_a = uf.find(id_a)
            root_b = uf.find(id_b)
            if root_a != root_b:
                uf.union(id_a, id_b)
                merged += 1
        elif not id_a or not id_b:
            unresolved += 1

    print(f"  {merged} new merges applied")
    if unresolved:
        print(f"  {unresolved} pairs had unresolvable employer names (skipped)")

    # ── Step 5: Build new cluster → canonical mapping ─────────────────────────
    print("Building merged clusters...")
    clusters = defaultdict(list)
    for eid in id_to_info:
        root = uf.find(eid)
        clusters[root].append(eid)

    # For each cluster with >1 member, pick canonical = highest record_count
    merges_needed = {root: members for root, members in clusters.items()
                     if len(members) > 1 and root in id_to_info}

    # But only update clusters that actually changed (contain newly merged pairs)
    changed_ids = set()
    for ea, eb in same_pairs:
        id_a = name_to_id.get(ea)
        id_b = name_to_id.get(eb)
        if id_a and id_b:
            changed_ids.add(id_a)
            changed_ids.add(id_b)

    new_merges = {root: members for root, members in merges_needed.items()
                  if any(m in changed_ids for m in members)}
    print(f"  {len(new_merges)} clusters to update in database")

    # ── Step 6: Apply merges to employer_identities + campaign_finance ─────────
    print("Applying merges...")
    total_records_retagged = 0

    for root, members in new_merges.items():
        # Pick canonical = member with highest record_count
        canonical_id = max(members, key=lambda x: id_to_info.get(x, {}).get("count", 0))

        # Collect all non-canonical member IDs
        others = [m for m in members if m != canonical_id]

        if not others:
            continue

        # Merge name_variants
        all_variants = set()
        canonical_name = id_to_info[canonical_id]["canonical"]
        for m in members:
            info = id_to_info.get(m, {})
            cname = info.get("canonical", "")
            if cname:
                all_variants.add(cname)
            cur.execute("SELECT name_variants FROM employer_identities WHERE employer_id = ?", (m,))
            row = cur.fetchone()
            if row and row[0]:
                for v in row[0].split("|"):
                    v = v.strip()
                    if v:
                        all_variants.add(v)

        new_variants = "|".join(sorted(all_variants))

        # Retag campaign_finance records from other members → canonical_id
        others_ph = ",".join("?" * len(others))
        cur.execute(f"""
            UPDATE campaign_finance
            SET employer_id = ?
            WHERE employer_id IN ({others_ph})
        """, [canonical_id] + others)
        total_records_retagged += cur.rowcount

        # Update canonical identity's variants
        cur.execute("""
            UPDATE employer_identities
            SET name_variants = ?
            WHERE employer_id = ?
        """, (new_variants, canonical_id))

        # Delete merged-away identities
        cur.execute(f"""
            DELETE FROM employer_identities
            WHERE employer_id IN ({others_ph})
        """, others)

    conn.commit()

    # ── Step 7: Refresh record counts ─────────────────────────────────────────
    print("Refreshing record counts...")
    cur.execute("""
        SELECT employer_id, COUNT(*) as cnt
        FROM campaign_finance
        WHERE employer_id IS NOT NULL
        GROUP BY employer_id
    """)
    counts = {row[0]: row[1] for row in cur.fetchall()}

    for eid, cnt in counts.items():
        cur.execute("""
            UPDATE employer_identities SET record_count = ? WHERE employer_id = ?
        """, (cnt, eid))

    conn.commit()
    conn.close()

    print(f"\n=== DONE ===")
    print(f"  New merges applied:        {merged}")
    print(f"  Clusters updated:          {len(new_merges)}")
    print(f"  Records retagged:          {total_records_retagged:,}")
    print(f"  Remaining identities:      {len(id_to_info) - sum(len(m)-1 for m in new_merges.values())}")

if __name__ == "__main__":
    main()
