"""
generate_profile_data.py
Generate {slug}_data.json and {slug}_all_donations.json for any candidate
in the Austin campaign finance database.

Usage:
    python generate_profile_data.py --candidate "Qadri"
    python generate_profile_data.py --candidate "Watson"
"""

import argparse
import json
import sqlite3
import sys
import io
import os
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = "C:/Users/Hamza Sait/Electoral/austin-finance-data/austin_finance.db"

INDUSTRY_COLORS = {
    "Real Estate":              "#f59e0b",
    "Technology":               "#4f8ef7",
    "Legal":                    "#a78bfa",
    "Nonprofit / Advocacy":     "#34d399",
    "Healthcare":               "#f472b6",
    "Consulting / PR":          "#94a3b8",
    "Government":               "#818cf8",
    "Finance":                  "#fbbf24",
    "Education":                "#22d3ee",
    "Engineering":              "#6b7280",
    "Hospitality / Events":     "#fb923c",
    "Construction":             "#d97706",
    "Energy / Environment":     "#ef4444",
    "Media":                    "#60a5fa",
    "Retail":                   "#a3e635",
    "Architecture":             "#e879f9",
    "Transportation":           "#34d399",
    "Entertainment":            "#f97316",
    "Labor":                    "#14b8a6",
    "Venture Capital":          "#8b5cf6",
    "Retail / Media / Other":   "#374151",
    "Not Employed":             "#6b7280",
    "Self-Employed":            "#78716c",
    "Student":                  "#38bdf8",
    "Unknown / Unclassified":   "#1f2937",
    "Unknown":                  "#1f2937",
}

NOISE_INDUSTRIES = {"Not Employed", "Self-Employed", "Student", "Unknown", "Unknown / Unclassified"}
NO_DONUT = {"Not Employed", "Self-Employed", "Student", "Unknown / Unclassified"}

# Industries that roll up into "Retail / Media / Other" in the profile
OTHER_INDS = {"Retail", "Media", "Architecture", "Transportation", "Entertainment",
              "Labor", "Venture Capital", "Retail / Media / Other"}

# Election cycle definitions per candidate slug
# Each cycle: label, start_year (None = beginning of time), end_year (None = present)
CANDIDATE_CYCLES = {
    # Districts 1,3,5,8,9 — elected 2022, reelection 2026
    'qadri':        [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2023},
                     {'label': 'Reelection',   'election_year': 2026, 'start_year': 2024, 'end_year': None}],
    'siegel':       [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2023},
                     {'label': 'Reelection',   'election_year': 2026, 'start_year': 2024, 'end_year': None}],
    'ganguly':      [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2023},
                     {'label': 'Reelection',   'election_year': 2026, 'start_year': 2024, 'end_year': None}],
    'harpermadison':[{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2023},
                     {'label': 'Reelection',   'election_year': 2026, 'start_year': 2024, 'end_year': None}],
    'alter':        [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2023},
                     {'label': 'Reelection',   'election_year': 2026, 'start_year': 2024, 'end_year': None}],
    'ellis':        [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2023},
                     {'label': 'Reelection',   'election_year': 2026, 'start_year': 2024, 'end_year': None}],
    # Districts 2,4,6,10 — elected 2024, reelection 2028
    'israel':       [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2025},
                     {'label': 'Reelection',   'election_year': 2028, 'start_year': 2026, 'end_year': None}],
    'fuentes':      [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2025},
                     {'label': 'Reelection',   'election_year': 2028, 'start_year': 2026, 'end_year': None}],
    'velasquez':    [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2025},
                     {'label': 'Reelection',   'election_year': 2028, 'start_year': 2026, 'end_year': None}],
    'llanes':       [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2025},
                     {'label': 'Reelection',   'election_year': 2028, 'start_year': 2026, 'end_year': None}],
    'kelly':        [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2025},
                     {'label': 'Reelection',   'election_year': 2028, 'start_year': 2026, 'end_year': None}],
    'guerrero':     [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2025},
                     {'label': 'Reelection',   'election_year': 2028, 'start_year': 2026, 'end_year': None}],
    # Mayor
    'watson':       [{'label': 'Term 1',       'election_year': 2022, 'start_year': None, 'end_year': 2025},
                     {'label': 'Reelection',   'election_year': 2026, 'start_year': 2026, 'end_year': None}],
}


def slugify(name: str) -> str:
    """Simple slug: lowercase, alphanumeric only."""
    return "".join(c.lower() for c in name if c.isalnum() or c == "_")


def find_recipient(cur, candidate_fragment: str):
    """Find the exact recipient string(s) matching the candidate fragment."""
    rows = cur.execute(
        """SELECT DISTINCT recipient, COUNT(*) as n
           FROM campaign_finance
           WHERE recipient LIKE ? AND contribution_year >= 2021
           GROUP BY recipient ORDER BY n DESC""",
        (f"%{candidate_fragment}%",)
    ).fetchall()
    return rows


def build_year_clause(cycle):
    """Return (extra_sql, extra_params) for filtering by cycle start/end year."""
    clauses = []
    params = []
    if cycle['start_year'] is not None:
        clauses.append("cf.contribution_year >= ?")
        params.append(cycle['start_year'])
    if cycle['end_year'] is not None:
        clauses.append("cf.contribution_year <= ?")
        params.append(cycle['end_year'])
    return clauses, params


def build_cycle_data(cur, candidate_fragment, cycle, by_year_data):
    """Run the same queries as the main profile but filtered to a cycle's year range.
    Returns dict with hero, interest_groups, notable_firms, top_donors."""

    year_clauses, year_params = build_year_clause(cycle)

    # Build WHERE clause
    where_parts = [
        "cf.recipient LIKE ?",
        "COALESCE(cf.balanced_amount, cf.contribution_amount) > 0",
    ]
    base_params = [f"%{candidate_fragment}%"]

    if year_clauses:
        where_parts.extend(year_clauses)
        base_params.extend(year_params)

    WHERE = " AND ".join(where_parts)
    params = tuple(base_params)

    # ── Hero stats ────────────────────────────────────────────────────────────
    hero_row = cur.execute(f"""
        SELECT
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total_raised,
            COUNT(DISTINCT cf.donor_id) as unique_donors,
            COUNT(*) as total_contributions
        FROM campaign_finance cf
        WHERE {WHERE}
    """, params).fetchone()

    total_raised = int(hero_row[0] or 0)
    unique_donors = int(hero_row[1] or 0)
    total_contributions = int(hero_row[2] or 0)

    # Employer-affiliated %
    noise_total = cur.execute(f"""
        SELECT ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0)
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {WHERE}
          AND COALESCE(di.resolved_industry, ei.industry, 'Unknown') IN
              ('Not Employed','Self-Employed','Student','Unknown','Unknown / Unclassified')
    """, params).fetchone()[0] or 0

    employer_affiliated_pct = round((total_raised - noise_total) / total_raised * 100, 1) if total_raised else 0.0

    # Top industry
    top_industry_row = cur.execute(f"""
        SELECT COALESCE(di.resolved_industry, ei.industry, 'Unknown') as ind,
               ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as tot
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {WHERE}
          AND COALESCE(di.resolved_industry, ei.industry, 'Unknown') NOT IN
              ('Not Employed','Self-Employed','Student','Unknown','Unknown / Unclassified')
        GROUP BY 1 ORDER BY 2 DESC LIMIT 1
    """, params).fetchone()
    top_industry = top_industry_row[0] if top_industry_row else "Unknown"

    hero = {
        "total_raised": total_raised,
        "unique_donors": unique_donors,
        "total_contributions": total_contributions,
        "employer_affiliated_pct": employer_affiliated_pct,
        "top_industry": top_industry,
    }

    # ── Interest groups ───────────────────────────────────────────────────────
    ig_rows = cur.execute(f"""
        SELECT
            COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total,
            COUNT(DISTINCT cf.donor_id) as donors
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {WHERE}
        GROUP BY 1 ORDER BY 2 DESC
    """, params).fetchall()

    other_total = 0
    main_groups = []
    for ind, total, donors in ig_rows:
        if ind in OTHER_INDS and ind != "Retail / Media / Other":
            other_total += int(total)
        elif ind == "Retail / Media / Other":
            other_total += int(total)
        else:
            main_groups.append((ind, int(total), int(donors)))

    if other_total > 0:
        other_donors_count = cur.execute(f"""
            SELECT COUNT(DISTINCT cf.donor_id)
            FROM campaign_finance cf
            LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
            LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
            WHERE {WHERE}
              AND COALESCE(di.resolved_industry, ei.industry, 'Unknown') IN
                  ('Retail','Media','Architecture','Transportation','Entertainment',
                   'Labor','Venture Capital','Retail / Media / Other')
        """, params).fetchone()[0] or 0
        main_groups.append(("Retail / Media / Other", other_total, other_donors_count))

    main_groups.sort(key=lambda x: -x[1])

    interest_groups = []
    for ind, total, donors in main_groups:
        entry = {
            "label": ind,
            "donors": donors,
            "total": total,
            "color": INDUSTRY_COLORS.get(ind, "#94a3b8"),
        }
        if ind in NO_DONUT:
            entry["noDonut"] = True
        interest_groups.append(entry)

    # ── Notable firms ─────────────────────────────────────────────────────────
    notable_rows = cur.execute(f"""
        SELECT
            COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, '') as firm,
            COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
            COALESCE(ei.interest_tags, '') as tags,
            COUNT(DISTINCT cf.donor_id) as donors,
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {WHERE}
          AND COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, '') != ''
          AND COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, '')
              NOT IN ('Not Employed', 'Self-Employed', 'Student', 'Unknown', 'Retired', 'Homemaker', 'N/A')
        GROUP BY firm
        HAVING COUNT(DISTINCT cf.donor_id) >= 3
        ORDER BY total DESC
        LIMIT 20
    """, params).fetchall()

    notable_firms = []
    for firm, industry, tags, donors, total in notable_rows:
        notable_firms.append({
            "firm": firm,
            "industry": industry,
            "tags": tags or "",
            "donors": int(donors),
            "total": int(total),
            "color": INDUSTRY_COLORS.get(industry, "#94a3b8"),
        })

    # ── Top donors ────────────────────────────────────────────────────────────
    top_donor_rows = cur.execute(f"""
        SELECT
            di.canonical_name as name,
            COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, '') as employer,
            COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
            COALESCE(ei.interest_tags, '') as tags,
            COUNT(*) as cnt,
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {WHERE}
          AND cf.donor_type = 'INDIVIDUAL'
          AND di.canonical_name IS NOT NULL
          AND di.canonical_name != ''
        GROUP BY cf.donor_id
        ORDER BY total DESC
        LIMIT 10
    """, params).fetchall()

    top_donors = []
    for name, employer, industry, tags, cnt, total in top_donor_rows:
        top_donors.append({
            "name": name or "",
            "employer": employer or "",
            "industry": industry or "",
            "tags": tags or "",
            "total": int(total),
            "count": int(cnt),
        })

    # ── Build year_range string ───────────────────────────────────────────────
    if cycle['start_year'] is None:
        # Use earliest year from by_year data
        years = [int(y['year']) for y in by_year_data if y['total'] > 0]
        start_str = str(min(years)) if years else "?"
    else:
        start_str = str(cycle['start_year'])

    if cycle['end_year'] is None:
        end_str = "present"
    else:
        end_str = str(cycle['end_year'])

    year_range = f"{start_str}\u2013{end_str}"

    return {
        "label": cycle['label'],
        "election_year": cycle['election_year'],
        "year_range": year_range,
        "hero": hero,
        "interest_groups": interest_groups,
        "notable_firms": notable_firms,
        "top_donors": top_donors,
    }


def generate(candidate_fragment: str, output_dir: str = "."):
    conn = sqlite3.connect(DB_PATH, timeout=120)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    # ── Identify recipient ────────────────────────────────────────────────────
    matches = find_recipient(cur, candidate_fragment)
    if not matches:
        print(f"ERROR: No recipient found matching '{candidate_fragment}'")
        conn.close()
        return

    # Use the one with the most records (likely the primary campaign account)
    recipient, count = matches[0]
    print(f"Found recipient: '{recipient}' ({count:,} total records)")
    if len(matches) > 1:
        print(f"  Also matched: {[r[0] for r in matches[1:]]}")

    # Build slug from the fragment (not the full name)
    slug = slugify(candidate_fragment)

    # Try to get a clean display name from canonical_name form
    # recipient is typically "Lastname, Firstname M." — build a nicer version
    candidate_name = recipient  # fallback

    # ── Base filter ───────────────────────────────────────────────────────────
    # All queries use this same WHERE clause
    BASE_WHERE = """
        cf.recipient LIKE ?
        AND cf.contribution_year >= 2022
        AND COALESCE(cf.balanced_amount, cf.contribution_amount) > 0
    """
    base_params = (f"%{candidate_fragment}%",)

    # ── Hero stats ────────────────────────────────────────────────────────────
    hero_row = cur.execute(f"""
        SELECT
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total_raised,
            COUNT(DISTINCT cf.donor_id) as unique_donors,
            COUNT(*) as total_contributions
        FROM campaign_finance cf
        WHERE {BASE_WHERE}
    """, base_params).fetchone()

    total_raised = int(hero_row[0] or 0)
    unique_donors = int(hero_row[1] or 0)
    total_contributions = int(hero_row[2] or 0)

    # Employer-affiliated % (exclude noise industries)
    noise_total = cur.execute(f"""
        SELECT ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0)
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {BASE_WHERE}
          AND COALESCE(di.resolved_industry, ei.industry, 'Unknown') IN
              ('Not Employed','Self-Employed','Student','Unknown','Unknown / Unclassified')
    """, base_params).fetchone()[0] or 0

    employer_affiliated_pct = round((total_raised - noise_total) / total_raised * 100, 1) if total_raised else 0.0

    # Top industry (by total, excluding noise)
    top_industry_row = cur.execute(f"""
        SELECT COALESCE(di.resolved_industry, ei.industry, 'Unknown') as ind,
               ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as tot
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {BASE_WHERE}
          AND COALESCE(di.resolved_industry, ei.industry, 'Unknown') NOT IN
              ('Not Employed','Self-Employed','Student','Unknown','Unknown / Unclassified')
        GROUP BY 1 ORDER BY 2 DESC LIMIT 1
    """, base_params).fetchone()
    top_industry = top_industry_row[0] if top_industry_row else "Unknown"

    hero = {
        "total_raised": total_raised,
        "unique_donors": unique_donors,
        "total_contributions": total_contributions,
        "employer_affiliated_pct": employer_affiliated_pct,
        "top_industry": top_industry,
    }

    # ── By year ───────────────────────────────────────────────────────────────
    by_year_rows = cur.execute(f"""
        SELECT
            CAST(cf.contribution_year AS TEXT) as yr,
            COUNT(*) as cnt,
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as tot
        FROM campaign_finance cf
        WHERE {BASE_WHERE}
        GROUP BY cf.contribution_year ORDER BY cf.contribution_year
    """, base_params).fetchall()

    by_year = [{"year": r[0], "count": int(r[1]), "total": int(r[2])} for r in by_year_rows]

    # ── Interest groups ───────────────────────────────────────────────────────
    ig_rows = cur.execute(f"""
        SELECT
            COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total,
            COUNT(DISTINCT cf.donor_id) as donors
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {BASE_WHERE}
        GROUP BY 1 ORDER BY 2 DESC
    """, base_params).fetchall()

    # Collapse "Other" industries into Retail / Media / Other
    other_total = 0
    other_donors = set()
    main_groups = []
    for ind, total, donors in ig_rows:
        if ind in OTHER_INDS and ind != "Retail / Media / Other":
            other_total += int(total)
            # donors here is COUNT(DISTINCT donor_id) per industry — we can't sum these
            # so we'll re-query for combined donors below
        elif ind == "Retail / Media / Other":
            other_total += int(total)
        else:
            main_groups.append((ind, int(total), int(donors)))

    # Re-query combined donor count for Other bucket
    if other_total > 0:
        other_donors_count = cur.execute(f"""
            SELECT COUNT(DISTINCT cf.donor_id)
            FROM campaign_finance cf
            LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
            LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
            WHERE {BASE_WHERE}
              AND COALESCE(di.resolved_industry, ei.industry, 'Unknown') IN
                  ('Retail','Media','Architecture','Transportation','Entertainment',
                   'Labor','Venture Capital','Retail / Media / Other')
        """, base_params).fetchone()[0] or 0
        main_groups.append(("Retail / Media / Other", other_total, other_donors_count))

    # Sort by total descending, build final list
    main_groups.sort(key=lambda x: -x[1])

    interest_groups = []
    for ind, total, donors in main_groups:
        entry = {
            "label": ind,
            "donors": donors,
            "total": total,
            "color": INDUSTRY_COLORS.get(ind, "#94a3b8"),
        }
        if ind in NO_DONUT:
            entry["noDonut"] = True
        interest_groups.append(entry)

    # ── Notable firms (employers with 3+ distinct donors, excluding noise labels) ──
    notable_rows = cur.execute(f"""
        SELECT
            COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, '') as firm,
            COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
            COALESCE(ei.interest_tags, '') as tags,
            COUNT(DISTINCT cf.donor_id) as donors,
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {BASE_WHERE}
          AND COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, '') != ''
          AND COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, '')
              NOT IN ('Not Employed', 'Self-Employed', 'Student', 'Unknown', 'Retired', 'Homemaker', 'N/A')
        GROUP BY firm
        HAVING COUNT(DISTINCT cf.donor_id) >= 3
        ORDER BY total DESC
        LIMIT 20
    """, base_params).fetchall()

    notable_firms = []
    for firm, industry, tags, donors, total in notable_rows:
        notable_firms.append({
            "firm": firm,
            "industry": industry,
            "tags": tags or "",
            "donors": int(donors),
            "total": int(total),
            "color": INDUSTRY_COLORS.get(industry, "#94a3b8"),
        })

    # ── Top donors ────────────────────────────────────────────────────────────
    # Only INDIVIDUAL donors with a resolved canonical name
    top_donor_rows = cur.execute(f"""
        SELECT
            di.canonical_name as name,
            COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, '') as employer,
            COALESCE(di.resolved_industry, ei.industry, 'Unknown') as industry,
            COALESCE(ei.interest_tags, '') as tags,
            COUNT(*) as cnt,
            ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as total
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {BASE_WHERE}
          AND cf.donor_type = 'INDIVIDUAL'
          AND di.canonical_name IS NOT NULL
          AND di.canonical_name != ''
        GROUP BY cf.donor_id
        ORDER BY total DESC
        LIMIT 10
    """, base_params).fetchall()

    top_donors = []
    for name, employer, industry, tags, cnt, total in top_donor_rows:
        top_donors.append({
            "name": name or "",
            "employer": employer or "",
            "industry": industry or "",
            "tags": tags or "",
            "total": int(total),
            "count": int(cnt),
        })

    # ── All donations ──────────────────────────────────────────────────────────
    all_donation_rows = cur.execute(f"""
        SELECT
            di.canonical_name,
            cf.contribution_date,
            ROUND(COALESCE(cf.balanced_amount, cf.contribution_amount), 2),
            COALESCE(di.resolved_employer_display, ei.canonical_name, cf.donor_reported_employer, ''),
            COALESCE(di.resolved_industry, ei.industry, 'Unknown'),
            TRIM(COALESCE(cf.city_state_zip, ''))
        FROM campaign_finance cf
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {BASE_WHERE}
        ORDER BY cf.contribution_date DESC
    """, base_params).fetchall()

    all_donations = [list(r) for r in all_donation_rows]

    # ── Election cycles ───────────────────────────────────────────────────────
    cycles = []
    if slug in CANDIDATE_CYCLES:
        for cycle_def in CANDIDATE_CYCLES[slug]:
            cycle_data = build_cycle_data(cur, candidate_fragment, cycle_def, by_year)
            cycles.append(cycle_data)
        print(f"  Built {len(cycles)} election cycles for '{slug}'")
    else:
        print(f"  No cycle definitions found for slug '{slug}' — cycles will be empty")

    conn.close()

    # ── Assemble meta ─────────────────────────────────────────────────────────
    generated_at = datetime.now(timezone.utc).isoformat()
    meta = {
        "candidate_name": candidate_name,
        "candidate_slug": slug,
        "office": "Austin City Council",
        "generated_at": generated_at,
    }

    # ── Write {slug}_data.json (everything except all_donations) ──────────────
    data_payload = {
        "meta": meta,
        "hero": hero,
        "by_year": by_year,
        "interest_groups": interest_groups,
        "notable_firms": notable_firms,
        "top_donors": top_donors,
        "cycles": cycles,
    }
    data_path = os.path.join(output_dir, f"{slug}_data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data_payload, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Written: {data_path}  ({os.path.getsize(data_path):,} bytes)")

    # ── Write {slug}_all_donations.json ───────────────────────────────────────
    donations_path = os.path.join(output_dir, f"{slug}_all_donations.json")
    donations_json = json.dumps(all_donations, separators=(",", ":"), ensure_ascii=False)
    with open(donations_path, "w", encoding="utf-8") as f:
        f.write(donations_json)
    print(f"Written: {donations_path}  ({os.path.getsize(donations_path):,} bytes, {len(all_donations):,} records)")

    # ── Verification summary ───────────────────────────────────────────────────
    print(f"\n=== Verification: {candidate_name} ===")
    print(f"  Total raised:          ${total_raised:,}")
    print(f"  Unique donors:         {unique_donors:,}")
    print(f"  Total contributions:   {total_contributions:,}")
    print(f"  Employer-affiliated:   {employer_affiliated_pct}%")
    print(f"  Top industry:          {top_industry}")
    print(f"  Interest groups:       {len(interest_groups)}")
    print(f"  Notable firms (3+):    {len(notable_firms)}")
    print(f"  Top donors (10):       {len(top_donors)}")
    print(f"  All donations rows:    {len(all_donations):,}")
    print(f"\n  By year:")
    for y in by_year:
        print(f"    {y['year']}: {y['count']:,} gifts, ${y['total']:,}")
    print(f"\n  Interest groups (top 5):")
    for g in interest_groups[:5]:
        print(f"    {g['label']}: ${g['total']:,} ({g['donors']} donors)")
    print(f"\n  Top donors (3):")
    for d in top_donors[:3]:
        print(f"    {d['name']}: ${d['total']:,} ({d['count']} gifts) @ {d['employer']}")

    # ── Cycle verification ────────────────────────────────────────────────────
    if cycles:
        print(f"\n  Election cycles ({len(cycles)}):")
        for c in cycles:
            h = c['hero']
            print(f"\n    [{c['label']}] {c['year_range']} (election {c['election_year']})")
            print(f"      Total raised:        ${h['total_raised']:,}")
            print(f"      Unique donors:       {h['unique_donors']:,}")
            print(f"      Employer-affiliated: {h['employer_affiliated_pct']}%")
            print(f"      Top industry:        {h['top_industry']}")
            print(f"      Top 3 industries:")
            for ig in c['interest_groups'][:3]:
                pct = round(ig['total'] / h['total_raised'] * 100, 1) if h['total_raised'] else 0
                print(f"        {ig['label']}: ${ig['total']:,} ({pct}%)")

        if len(cycles) >= 2:
            c0 = cycles[0]
            c1 = cycles[1]
            delta = round(c1['hero']['employer_affiliated_pct'] - c0['hero']['employer_affiliated_pct'], 1)
            sign = "+" if delta >= 0 else ""
            print(f"\n  Employer-affiliated delta ({c0['label']} → {c1['label']}): {sign}{delta} pts")

    return data_payload, all_donations


def main():
    parser = argparse.ArgumentParser(description="Generate profile JSON for a campaign finance candidate")
    parser.add_argument("--candidate", required=True, help="Candidate name fragment (e.g. 'Qadri')")
    parser.add_argument("--output-dir", default="C:/Users/Hamza Sait/Electoral/austin-finance-data",
                        help="Output directory for JSON files")
    args = parser.parse_args()

    generate(args.candidate, args.output_dir)


if __name__ == "__main__":
    main()
