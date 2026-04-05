"""
Two-stage employer classifier:
  Stage 1: Keyword rules → high-confidence auto-classify
  Stage 2: Collect low-confidence remainder for LLM review
"""

import sqlite3, re, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = "austin_finance.db"

# ── Keyword rules ─────────────────────────────────────────────────────────────
# Each rule: (pattern, industry, interest_tags, confidence)
# Patterns are matched against lowercased canonical_name
# First match wins — order matters (more specific first)

RULES = [
    # ── Government ──────────────────────────────────────────────────────────
    (r'\b(city of|county|isd|independent school district|state of|dept of|department of'
     r'|commission|authority|bureau|federal|u\.?s\.? (army|navy|air force|government)'
     r'|public works|apd|txdot|atcems|hhs|hhsc|tceq|tdcj|dfps)\b',
     "Government", None, 0.9),

    # ── Education ───────────────────────────────────────────────────────────
    (r'\b(university|college|school district|community college|academy|institute of'
     r'|seminary|law school)\b',
     "Education", "higher-education", 0.85),

    # ── Healthcare ──────────────────────────────────────────────────────────
    (r'\b(hospital|health system|medical center|clinic|healthcare|medical group'
     r'|pharmacy|dental|orthodontic|pediatric|oncology|radiology|surgery|surgical'
     r'|anesthesia|psychiatry|therapy|therapist|counseling|rehab|rehabilitation'
     r'|hospice|nursing|home health|urgent care|physician|physicians)\b',
     "Healthcare", None, 0.85),

    # ── Legal ────────────────────────────────────────────────────────────────
    (r'\b(law firm|law office|law group|attorneys at law|lawyer|lawyers)\b',
     "Legal", None, 0.9),
    # LLP/PLLC/PC firms — likely legal but lower confidence without "law" keyword
    (r'\b(llp|pllc)\b',
     "Legal", None, 0.75),

    # ── Real Estate (specific) ───────────────────────────────────────────────
    (r'\b(real estate|realty|realtor|realtors|properties|property management'
     r'|property company|homebuilder|home builder|residential development'
     r'|land development|land company|title company|escrow|mortgage company'
     r'|apartment|apartments|multifamily|multi.family|townhome|townhomes'
     r'|housing development|housing corp|reit|commercial real estate)\b',
     "Real Estate", "real-estate-development", 0.9),

    # ── Construction ────────────────────────────────────────────────────────
    (r'\b(construction|builders|builder|contractor|contractors|excavat'
     r'|concrete|masonry|roofing|plumbing|hvac|electrical contractor'
     r'|general contractor|site work|paving|grading)\b',
     "Construction", "real-estate-development", 0.85),

    # ── Engineering ─────────────────────────────────────────────────────────
    (r'\b(engineering|engineers|surveying|surveyors|geotechnical|structural'
     r'|civil engineering|land planning|landscape architect)\b',
     "Engineering", None, 0.85),

    # ── Architecture / Design ────────────────────────────────────────────────
    (r'\b(architect|architects|architecture|urban design|urban planning|planning firm)\b',
     "Architecture", None, 0.85),

    # ── Finance ──────────────────────────────────────────────────────────────
    (r'\b(bank|bancorp|bancshares|financial|capital management|asset management'
     r'|wealth management|investment management|private equity|venture capital'
     r'|hedge fund|insurance company|credit union|mortgage bank|securities'
     r'|brokerage|financial services|financial group)\b',
     "Finance", None, 0.85),

    # ── Technology ───────────────────────────────────────────────────────────
    (r'\b(software|technology|technologies|tech inc|saas|cloud|cyber|digital'
     r'|semiconductor|semiconductors|computing|artificial intelligence|machine learning'
     r'|data analytics|information systems|it services|telecom|telecommunications)\b',
     "Technology", "tech-startup-ecosystem", 0.8),

    # ── Energy / Environment ─────────────────────────────────────────────────
    (r'\b(oil|gas|petroleum|energy company|power company|electric company'
     r'|renewable|solar|wind energy|pipeline|utility|utilities|midstream'
     r'|exploration|drilling|oilfield)\b',
     "Energy / Environment", "energy-mineral-rights", 0.85),

    # ── Labor / Unions ───────────────────────────────────────────────────────
    (r'\b(union|afl.cio|seiu|teamsters|ufcw|ibew|uaw|afscme|cwa local'
     r'|workers (association|alliance|federation)|labor council|trades council)\b',
     "Labor", "progressive-money", 0.9),

    # ── Nonprofit / Advocacy ─────────────────────────────────────────────────
    (r'\b(foundation(?! communities)|nonprofit|non.profit|coalition|alliance'
     r'|advocacy|action fund|action committee|political action|pac\b'
     r'|civic|community organization|community development|social services'
     r'|community health|food bank|habitat for humanity)\b',
     "Nonprofit", None, 0.75),

    # ── Consulting / PR ──────────────────────────────────────────────────────
    (r'\b(consulting|consultants|strategies|strategic|communications group'
     r'|public affairs|public relations|government relations|lobbying|lobbyist'
     r'|advisory group|advisory services|management consulting)\b',
     "Consulting / PR", None, 0.8),

    # ── Media ────────────────────────────────────────────────────────────────
    (r'\b(media|publishing|press|newspaper|magazine|broadcast|television|tv'
     r'|radio|studio|studios|film|photo|photography|advertising agency)\b',
     "Media", None, 0.8),

    # ── Hospitality / Entertainment ──────────────────────────────────────────
    (r'\b(hotel|resort|inn|motel|spa|restaurant|cafe|coffee|bar |pub |brewery'
     r'|distillery|winery|catering|events company|event center|venue'
     r'|entertainment group|concert|theater|theatre)\b',
     "Hospitality / Entertainment", "hospitality-entertainment", 0.8),

    # ── Retail ───────────────────────────────────────────────────────────────
    (r'\b(grocery|supermarket|retail|store|shop |boutique|dealership'
     r'|auto dealer|car dealer)\b',
     "Retail", None, 0.8),

    # ── Transportation ───────────────────────────────────────────────────────
    (r'\b(airline|airlines|freight|logistics|trucking|transit|transportation company'
     r'|shipping|railroad|rail company)\b',
     "Transportation", None, 0.8),
]

# Compile all patterns
COMPILED = [(re.compile(p, re.IGNORECASE), industry, tags, conf)
            for p, industry, tags, conf in RULES]

# Additional interest tag rules applied AFTER industry is set
INTEREST_RULES = [
    # Real-estate-adjacent law firms
    (r'\b(real estate|land use|zoning|property|development|title)\b', "real-estate-development"),
    # Progressive orgs
    (r'\b(progressive|democrat|democratic|equity|justice|rights|environment'
     r'|conservation|planned parenthood|aclu|habitat|workers defense|advocacy)\b', "progressive-money"),
    # Conservative orgs
    (r'\b(republican|conservative|liberty|freedom|heritage|family values|gun)\b', "republican-money"),
    # Healthcare nonprofit
    (r'\b(community health|community clinic|free clinic|health equity)\b', "health-equity"),
]
INTEREST_COMPILED = [(re.compile(p, re.IGNORECASE), tag) for p, tag in INTEREST_RULES]


def classify(name):
    """Returns (industry, tags, confidence) or (None, None, 0) if no match."""
    for pattern, industry, tags, conf in COMPILED:
        if pattern.search(name):
            # Apply additional interest tag rules
            extra_tags = set()
            if tags:
                extra_tags.update(tags.split("|"))
            for ip, itag in INTEREST_COMPILED:
                if ip.search(name):
                    extra_tags.add(itag)
            final_tags = "|".join(sorted(extra_tags)) if extra_tags else None
            return industry, final_tags, conf
    return None, None, 0.0


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT employer_id, canonical_name, record_count
        FROM employer_identities
        WHERE industry IS NULL
        ORDER BY record_count DESC
    """)
    unclassified = cur.fetchall()
    print(f"Unclassified employers: {len(unclassified)}")

    auto_classified = []
    needs_review = []
    CONFIDENCE_THRESHOLD = 0.80

    for row in unclassified:
        name = row["canonical_name"]
        industry, tags, conf = classify(name)
        if industry and conf >= CONFIDENCE_THRESHOLD:
            auto_classified.append((industry, tags, row["employer_id"], name, row["record_count"]))
        elif industry:
            needs_review.append((name, row["record_count"], industry, tags, conf, "low_confidence"))
        else:
            needs_review.append((name, row["record_count"], None, None, 0.0, "no_match"))

    # Write auto-classified
    cur.executemany("""
        UPDATE employer_identities SET industry=?, interest_tags=? WHERE employer_id=?
    """, [(ind, tags, eid) for ind, tags, eid, _, _ in auto_classified])
    conn.commit()

    print(f"\nAuto-classified: {len(auto_classified)}")
    print(f"Needs review:    {len(needs_review)}")

    # Show distribution of auto-classified
    from collections import Counter
    dist = Counter(ind for ind, *_ in auto_classified)
    print("\nAuto-classified by industry:")
    for ind, cnt in dist.most_common():
        print(f"  {ind:<30} {cnt:>4}")

    # Show needs-review, filtered to 3+ records (smaller set for LLM)
    review_worthy = [(n, cnt, ind, tags, conf, reason)
                     for n, cnt, ind, tags, conf, reason in needs_review
                     if cnt >= 3]
    print(f"\nNeeds review (3+ records): {len(review_worthy)}")
    print("\nTop unresolved (by record count):")
    for name, cnt, ind, tags, conf, reason in sorted(review_worthy, key=lambda x: -x[1])[:40]:
        hint = f"[{ind}? {conf:.0%}]" if ind else "[no match]"
        print(f"  [{cnt:3d}] {hint:25s} {name}")

    # Save review list to file for LLM pass
    with open("employer_review_needed.json", "w", encoding="utf-8") as f:
        json.dump([{"name": n, "record_count": cnt, "hint_industry": ind,
                    "hint_tags": tags, "confidence": conf, "reason": reason}
                   for n, cnt, ind, tags, conf, reason in review_worthy], f, indent=2)
    print(f"\nSaved {len(review_worthy)} employers to employer_review_needed.json")

    # Final coverage stats
    cur.execute("SELECT COUNT(*) FROM employer_identities WHERE industry IS NOT NULL")
    classified = cur.fetchone()[0]
    cur.execute("SELECT SUM(record_count) FROM employer_identities WHERE industry IS NOT NULL")
    classified_records = cur.fetchone()[0]
    cur.execute("SELECT SUM(record_count) FROM employer_identities")
    total_records = cur.fetchone()[0]
    print(f"\nFinal: {classified} employers classified")
    print(f"Record coverage: {classified_records:,} / {total_records:,} = {classified_records/total_records*100:.1f}%")

    conn.close()


if __name__ == "__main__":
    main()
