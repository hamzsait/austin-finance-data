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
    "Family":                   "#f43f5e",
    "Unknown / Unclassified":   "#1f2937",
    "Unknown":                  "#1f2937",
}

NOISE_INDUSTRIES = {"Not Employed", "Self-Employed", "Student", "Unknown", "Unknown / Unclassified", "Family"}
NO_DONUT = {"Not Employed", "Self-Employed", "Student", "Unknown / Unclassified", "Family"}

# Industries that roll up into "Retail / Media / Other" in the profile
OTHER_INDS = {"Retail", "Media", "Architecture", "Transportation", "Entertainment",
              "Labor", "Venture Capital", "Retail / Media / Other"}

# Election cycle definitions per candidate slug
# Each cycle: label, start_year (None = beginning of time), end_year (None = present)
CANDIDATE_CYCLES = {
    # Rule: a cycle ends at the election year and the next cycle starts the
    # following January. Austin runs 4-year staggered terms.
    # Districts 1,3,5,8,9 — last elected 2022, reelection 2026
    'qadri':        [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2022},
                     {'label': 'This Cycle',   'election_year': 2026, 'start_year': 2023, 'end_year': None}],
    'velasquez':    [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2022},
                     {'label': 'This Cycle',   'election_year': 2026, 'start_year': 2023, 'end_year': None}],
    'ellis':        [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2022},
                     {'label': 'This Cycle',   'election_year': 2026, 'start_year': 2023, 'end_year': None}],
    'harpermadison':[{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2022},
                     {'label': 'This Cycle',   'election_year': 2026, 'start_year': 2023, 'end_year': None}],
    'alter':        [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2022},
                     {'label': 'This Cycle',   'election_year': 2026, 'start_year': 2023, 'end_year': None}],
    'ganguly':      [{'label': 'Initial Run',  'election_year': 2022, 'start_year': None, 'end_year': 2022},
                     {'label': 'This Cycle',   'election_year': 2026, 'start_year': 2023, 'end_year': None}],
    # Districts 2,4,6,7,10 — last elected 2024, reelection 2028
    # Siegel is challenging D7 2026 (open/held seat); old money through 2024,
    # current cycle 2025+.
    'siegel':       [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2024},
                     {'label': 'This Cycle',   'election_year': 2026, 'start_year': 2025, 'end_year': None}],
    'israel':       [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2024},
                     {'label': 'This Cycle',   'election_year': 2028, 'start_year': 2025, 'end_year': None}],
    'fuentes':      [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2024},
                     {'label': 'This Cycle',   'election_year': 2028, 'start_year': 2025, 'end_year': None}],
    'llanes':       [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2024},
                     {'label': 'This Cycle',   'election_year': 2028, 'start_year': 2025, 'end_year': None}],
    'kelly':        [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2024},
                     {'label': 'This Cycle',   'election_year': 2028, 'start_year': 2025, 'end_year': None}],
    'guerrero':     [{'label': 'Initial Run',  'election_year': 2024, 'start_year': None, 'end_year': 2024},
                     {'label': 'This Cycle',   'election_year': 2028, 'start_year': 2025, 'end_year': None}],
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

    # ── Partisan lean (FEC data) ─────────────────────────────────────────────
    partisan_rows = cur.execute(f"""
        SELECT di.fec_partisan_lean,
               SUM(CAST(cf.contribution_amount AS REAL)) as amount
        FROM donor_identities di
        JOIN campaign_finance cf ON cf.donor_id = di.donor_id
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        WHERE {BASE_WHERE} AND di.fec_partisan_lean IS NOT NULL
        GROUP BY di.donor_id
    """, base_params).fetchall()

    partisan_lean = None
    if partisan_rows:
        buckets = [
            {"label": "Strong D",  "min": 0.9, "max": 1.01, "donors": 0, "total": 0},
            {"label": "Lean D",    "min": 0.6, "max": 0.9,  "donors": 0, "total": 0},
            {"label": "Mixed",     "min": 0.4, "max": 0.6,  "donors": 0, "total": 0},
            {"label": "Lean R",    "min": 0.1, "max": 0.4,  "donors": 0, "total": 0},
            {"label": "Strong R",  "min": -0.01, "max": 0.1, "donors": 0, "total": 0},
        ]
        total_dem_donors = 0
        total_rep_donors = 0
        total_mixed_donors = 0
        total_lean_amount = 0
        weighted_lean_sum = 0

        for lean, amt in partisan_rows:
            amt = amt or 0
            for b in buckets:
                if b["min"] <= lean < b["max"]:
                    b["donors"] += 1
                    b["total"] += round(amt, 2)
                    break
            if lean >= 0.6:
                total_dem_donors += 1
            elif lean <= 0.4:
                total_rep_donors += 1
            else:
                total_mixed_donors += 1
            if amt > 0:
                weighted_lean_sum += lean * amt
                total_lean_amount += amt

        weighted_avg = round(weighted_lean_sum / total_lean_amount, 3) if total_lean_amount > 0 else None
        # Per-donor detail for drill-down
        donor_details = cur.execute(f"""
            SELECT di.donor_id, di.canonical_name, di.fec_partisan_lean,
                   di.fec_total_dem, di.fec_total_rep, di.fec_total_other,
                   di.fec_total_donations,
                   SUM(CAST(cf.contribution_amount AS REAL)) as local_total
            FROM donor_identities di
            JOIN campaign_finance cf ON cf.donor_id = di.donor_id
            LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
            WHERE {BASE_WHERE} AND di.fec_partisan_lean IS NOT NULL
            GROUP BY di.donor_id
            ORDER BY (di.fec_total_dem + di.fec_total_rep) DESC
        """, base_params).fetchall()

        donors_list = []
        donor_ids_with_fec = []
        for d in donor_details:
            donors_list.append({
                "id": d[0], "name": d[1], "lean": round(d[2], 3),
                "dem": round(d[3] or 0, 0), "rep": round(d[4] or 0, 0),
                "other": round(d[5] or 0, 0), "fec_n": d[6] or 0,
                "local": round(d[7] or 0, 0),
            })
            donor_ids_with_fec.append(d[0])

        # Committee-level aggregates per donor
        donor_committees = {}
        if donor_ids_with_fec:
            placeholders = ",".join("?" * len(donor_ids_with_fec))
            comm_rows = cur.execute(f"""
                SELECT fcr.donor_id, fcc.committee_name, fcc.classification,
                       SUM(fcr.contribution_amount) as total, COUNT(*) as n
                FROM fec_contributions_raw fcr
                LEFT JOIN fec_committee_cache fcc ON fcc.committee_id = fcr.committee_id
                WHERE fcr.donor_id IN ({placeholders})
                  AND fcr.contribution_amount > 0
                GROUP BY fcr.donor_id, fcr.committee_id
                ORDER BY total DESC
            """, donor_ids_with_fec).fetchall()
            for row in comm_rows:
                did = row[0]
                if did not in donor_committees:
                    donor_committees[did] = []
                donor_committees[did].append({
                    "name": row[1] or "Unknown Committee",
                    "party": row[2] or "Other",
                    "total": round(row[3], 0),
                    "n": row[4],
                })

        partisan_lean = {
            "matched_donors": len(partisan_rows),
            "total_donors": unique_donors,
            "dem_donors": total_dem_donors,
            "rep_donors": total_rep_donors,
            "mixed_donors": total_mixed_donors,
            "weighted_lean": weighted_avg,
            "buckets": buckets,
            "donors": donors_list,
            "donor_committees": donor_committees,
        }
        print(f"  Partisan lean: {len(partisan_rows)} donors matched, "
              f"D={total_dem_donors} R={total_rep_donors} M={total_mixed_donors}, "
              f"weighted={weighted_avg}")

    # ── Israel/Palestine donor spectrum ──────────────────────────────────────
    ip_spectrum = None
    ip_rows = cur.execute(f"""
        SELECT di.donor_id, di.canonical_name, di.ip_spectrum, di.ip_tier,
               di.ip_total, di.ip_committees,
               SUM(CAST(cf.contribution_amount AS REAL)) as local_total,
               di.fec_partisan_lean
        FROM donor_identities di
        JOIN campaign_finance cf ON cf.donor_id = di.donor_id
        LEFT JOIN employer_identities ei ON cf.employer_id = ei.employer_id
        WHERE {BASE_WHERE} AND di.ip_spectrum IS NOT NULL
        GROUP BY di.donor_id
        ORDER BY di.ip_total DESC
    """, base_params).fetchall()

    if ip_rows:
        # Build committee name lookup
        comm_names = {}
        for cid, cname in cur.execute("SELECT committee_id, committee_name FROM fec_committee_cache WHERE ip_category IS NOT NULL").fetchall():
            comm_names[cid] = cname

        categories = {}
        donors_by_cat = {}
        for row in ip_rows:
            cat = row[2]
            if cat not in categories:
                categories[cat] = {"donors": 0, "ip_total": 0, "local_total": 0}
                donors_by_cat[cat] = []
            categories[cat]["donors"] += 1
            categories[cat]["ip_total"] += row[4] or 0
            categories[cat]["local_total"] += row[6] or 0
            comm_list = []
            if row[5]:
                for cid in row[5].split(","):
                    comm_list.append({"id": cid.strip(), "name": comm_names.get(cid.strip(), cid.strip())})
            donors_by_cat[cat].append({
                "name": row[1], "tier": row[3],
                "ip_total": round(row[4] or 0, 0),
                "local_total": round(row[6] or 0, 0),
                "partisan_lean": round(row[7], 3) if row[7] is not None else None,
                "committees": comm_list,
            })

        # Order: hawkish first, then liberal zionist, then pro-palestine
        cat_order = ["hawkish_proisrael", "liberal_zionist", "pro_palestine"]
        cat_labels = {
            "hawkish_proisrael": "Pro-Israel (AIPAC-aligned)",
            "liberal_zionist": "Liberal Zionist",
            "pro_palestine": "Pro-Palestine",
        }

        spectrum_list = []
        for cat in cat_order:
            if cat in categories:
                spectrum_list.append({
                    "key": cat,
                    "label": cat_labels.get(cat, cat),
                    "donors": categories[cat]["donors"],
                    "ip_total": round(categories[cat]["ip_total"], 0),
                    "local_total": round(categories[cat]["local_total"], 0),
                    "donor_list": donors_by_cat[cat],
                })

        ip_spectrum = {
            "total_flagged": len(ip_rows),
            "categories": spectrum_list,
        }
        for s in spectrum_list:
            print(f"  IP spectrum: {s['label']}: {s['donors']} donors, "
                  f"${s['ip_total']:,.0f} federal, ${s['local_total']:,.0f} local")

    # ── Verified civic affiliations ──────────────────────────────────────────
    # Pulls organizational roles (board memberships, honors, employer ties)
    # from the civic_affiliations table for donors to THIS candidate.
    # Matches on last-name + first-name (with common nickname aliases).
    civic_affiliations_payload = None
    # Only proceed if the civic_affiliations table exists
    has_civic_table = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='civic_affiliations'"
    ).fetchone() is not None

    if has_civic_table:
        # Common nicknames → canonical first names for matching
        NICKNAME_ALIASES = {
            "jeff": "jeffrey", "jeffrey": "jeff",
            "rick": "richard", "richard": "rick", "ricky": "richard",
            "dave": "david", "david": "dave",
            "mike": "michael", "michael": "mike",
            "bob": "robert", "robert": "bob", "rob": "robert",
            "bill": "william", "william": "bill",
            "chris": "christopher", "christopher": "chris",
            "steve": "steven", "steven": "steve", "stephen": "steve",
            "dan": "daniel", "daniel": "dan",
            "tom": "thomas", "thomas": "tom",
            "ed": "edward", "edward": "ed", "eddie": "edward",
            "andy": "andrew", "andrew": "andy",
            "val": "valerie", "valerie": "val",
            "lil": "lily", "lily": "lillian",
            "kim": "kimberly", "kimberly": "kim",
            "laurie": "laura", "laura": "laurie",
            "lauren": "laurence",
        }

        def name_key(canon_name):
            """Return a comparable (last, first_normalized) tuple."""
            if not canon_name or "," not in canon_name:
                return None
            last, first = canon_name.split(",", 1)
            last = last.strip().lower()
            first = first.strip().lower()
            # Strip middle initial/name
            first = first.split()[0] if first else ""
            # Remove trailing period
            first = first.rstrip(".")
            return (last, first)

        # Pull all Qadri donors with local totals
        donor_rows = cur.execute(f"""
            SELECT di.canonical_name,
                   ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)), 0) as local_total,
                   COUNT(*) as gift_count
            FROM campaign_finance cf
            JOIN donor_identities di ON cf.donor_id = di.donor_id
            WHERE {BASE_WHERE}
              AND di.canonical_name IS NOT NULL
              AND di.canonical_name != ''
            GROUP BY di.canonical_name
        """, base_params).fetchall()

        # Aggregate local totals per name_key
        donor_totals = {}  # {(last, first): {name, total, gifts}}
        for cname, total, gifts in donor_rows:
            key = name_key(cname)
            if not key:
                continue
            if key not in donor_totals or (total or 0) > donor_totals[key]["total"]:
                donor_totals[key] = {"name": cname, "total": int(total or 0), "gifts": int(gifts or 0)}

        # Also index by last-name + nickname-normalized-first for alias matching
        donor_alias_index = {}  # {(last, alias_first): donor_key}
        for key in donor_totals.keys():
            last, first = key
            donor_alias_index[(last, first)] = key
            if first in NICKNAME_ALIASES:
                donor_alias_index[(last, NICKNAME_ALIASES[first])] = key
            # First initial fallback (only if first name has 2+ chars)
            if len(first) >= 1:
                donor_alias_index.setdefault((last, first[0]), key)

        # Pull all civic_affiliations rows
        ca_rows = cur.execute("""
            SELECT canonical_name, organization, role, category, source_url, notes
            FROM civic_affiliations
            ORDER BY canonical_name
        """).fetchall()

        # Group by matched donor_key
        donor_affils = {}  # {donor_key: {name, total, gifts, rows: [...]}}
        for ca_name, org, role, category, source_url, notes in ca_rows:
            ca_key = name_key(ca_name)
            if not ca_key:
                continue
            # Try exact match first
            matched = None
            if ca_key in donor_totals:
                matched = ca_key
            else:
                # Alias match
                if ca_key in donor_alias_index:
                    matched = donor_alias_index[ca_key]
                else:
                    last, first = ca_key
                    # Nickname alias reverse lookup
                    if first in NICKNAME_ALIASES:
                        alt_first = NICKNAME_ALIASES[first]
                        if (last, alt_first) in donor_totals:
                            matched = (last, alt_first)
                        elif (last, alt_first) in donor_alias_index:
                            matched = donor_alias_index[(last, alt_first)]

            if not matched:
                continue

            if matched not in donor_affils:
                donor_affils[matched] = {
                    "donor_name": donor_totals[matched]["name"],
                    "local_total": donor_totals[matched]["total"],
                    "gifts": donor_totals[matched]["gifts"],
                    "categories": set(),
                    "rows": [],
                    "has_aipac_direct": False,
                    "has_jewish_civic": False,
                    "has_oil_gas": False,
                    "has_pro_israel": False,
                    "has_liberal_zionist": False,
                    "has_adl": False,
                }
            cat = category or ""
            donor_affils[matched]["categories"].add(cat)
            donor_affils[matched]["rows"].append({
                "org": org,
                "role": role or "",
                "category": cat,
                "source": source_url or "",
                "notes": notes or "",
            })
            if cat == "aipac_direct":
                donor_affils[matched]["has_aipac_direct"] = True
            if cat == "jewish_civic":
                donor_affils[matched]["has_jewish_civic"] = True
            if cat == "pro_israel":
                donor_affils[matched]["has_pro_israel"] = True
            if cat == "liberal_zionist":
                donor_affils[matched]["has_liberal_zionist"] = True
            if cat.startswith("oil_gas"):
                donor_affils[matched]["has_oil_gas"] = True
            # ADL detection via organization name (no dedicated ADL category)
            if org and ("anti-defamation league" in org.lower() or "adl" in org.lower()):
                donor_affils[matched]["has_adl"] = True

        # Build bucket lists. A donor can appear in multiple buckets if they
        # have roles in multiple categories — but each row only attaches to
        # its own category inside that bucket.
        def bucket_entry(d, row_filter):
            """Build a donor entry with only rows matching row_filter()."""
            rows = [r for r in d["rows"] if row_filter(r)]
            if not rows:
                return None
            # Sort: primary/direct roles first (board member, chair, founder), then alphabetical
            PRIORITY_KEYWORDS = ["chair", "founder", "president", "board", "director",
                                 "trustee", "national", "namesake", "honoree"]
            def row_priority(r):
                role_lower = (r["role"] or "").lower()
                for i, kw in enumerate(PRIORITY_KEYWORDS):
                    if kw in role_lower:
                        return (0, i, r["org"])
                return (1, 99, r["org"])
            rows.sort(key=row_priority)
            return {
                "donor_name": d["donor_name"],
                "local_total": d["local_total"],
                "gifts": d["gifts"],
                "organizations": rows,
            }

        def sort_donors(entries):
            """Sort donors by local_total desc, then name."""
            return sorted(entries, key=lambda e: (-e["local_total"], e["donor_name"]))

        # AIPAC-direct: only donors with an aipac_direct or pro_israel (AIPAC board) row
        aipac_donors = []
        for d in donor_affils.values():
            if d["has_aipac_direct"] or d["has_pro_israel"]:
                entry = bucket_entry(d, lambda r: r["category"] in ("aipac_direct", "pro_israel"))
                if entry:
                    aipac_donors.append(entry)

        # ADL (Anti-Defamation League) — split out as its own bucket. Matches any
        # category=='jewish_civic' row whose org name contains ADL/Anti-Defamation League.
        def is_adl_row(r):
            org_lc = (r.get("org") or "").lower()
            return r["category"] == "jewish_civic" and (
                "anti-defamation" in org_lc or "adl" in org_lc
            )
        adl_donors = []
        for d in donor_affils.values():
            if d["has_adl"]:
                entry = bucket_entry(d, is_adl_row)
                if entry:
                    adl_donors.append(entry)

        # Liberal Zionist (J Street, OneVoice, PeaceWorks, National Jewish Democratic Council)
        liberal_zionist_donors = []
        for d in donor_affils.values():
            if d["has_liberal_zionist"]:
                entry = bucket_entry(d, lambda r: r["category"] == "liberal_zionist")
                if entry:
                    liberal_zionist_donors.append(entry)

        # Oil & Gas (all oil_gas_* categories)
        oil_gas_donors = []
        for d in donor_affils.values():
            if d["has_oil_gas"]:
                entry = bucket_entry(d, lambda r: r["category"].startswith("oil_gas"))
                if entry:
                    oil_gas_donors.append(entry)

        # ADL-specific sub-count (donors with an ADL board/role affiliation)
        adl_donors_count = sum(1 for d in donor_affils.values() if d["has_adl"])

        civic_affiliations_payload = {
            "total_donors_with_affiliations": len(donor_affils),
            "total_adl": adl_donors_count,
            "total_aipac_direct": len(aipac_donors),
            "total_liberal_zionist": len(liberal_zionist_donors),
            "total_oil_gas": len(oil_gas_donors),
            "by_category": {
                "aipac_direct": sort_donors(aipac_donors),
                "adl": sort_donors(adl_donors),
                "liberal_zionist": sort_donors(liberal_zionist_donors),
                "oil_gas": sort_donors(oil_gas_donors),
            },
        }
        print(f"  Civic affiliations: {len(donor_affils)} donors matched")
        print(f"    ADL board/honor: {adl_donors_count}")
        print(f"    AIPAC direct:    {len(aipac_donors)}")
        print(f"    Liberal Zionist: {len(liberal_zionist_donors)}")
        print(f"    Oil & Gas:       {len(oil_gas_donors)}")

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
        "partisan_lean": partisan_lean,
        "ip_spectrum": ip_spectrum,
        "civic_affiliations": civic_affiliations_payload,
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
