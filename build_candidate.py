"""
build_candidate.py
Repeatable driver that turns an already-enriched candidate in austin_finance.db
into a publishable static profile:

    1. Exports {slug}_data.json + {slug}_all_donations.json (via generate_profile_data)
    2. Materializes profile_{slug}.html from profile_template.html (injects PROFILE_SLUG)
    3. Prints the stats needed to fill / flip the candidate's index.html card

It does NOT re-run enrichment (identity, employer, FEC, flags) — that is a global
pass already applied across the DB. This driver is the export → render → wire-up tail.

Usage:
    python build_candidate.py --all-remaining         # build every incumbent below
    python build_candidate.py --slug vela             # build just one from the roster
    python build_candidate.py --recipient "Alter, Ryan" --slug alter   # ad-hoc

Pass an EXACT recipient string as the fragment (LIKE '%exact%' == exact match) to
avoid collisions like "Alter" (Ryan vs Alison) or "Vela" (matches "Velasquez").
"""

import argparse
import os

# generate_profile_data reconfigures sys.stdout to UTF-8 on import; importing it
# once here is enough (re-wrapping stdout again closes the shared buffer under GC).
import generate_profile_data as gpd

ROOT = "C:/Users/Hamza Sait/Electoral/austin-finance-data"
TEMPLATE = os.path.join(ROOT, "profile_template.html")

# Remaining current incumbents not yet live. recipient = exact string in the DB.
# district / race / display are used only for the printed index-card snippet.
ROSTER = [
    {"slug": "watson", "recipient": "Watson, Kirk P.",         "display": "Kirk Watson",        "district": "Mayor",       "race": "2022 Race"},
    {"slug": "vela",   "recipient": 'Vela, Jose "Chito", III', "display": "José Vela",      "district": "District 4",   "race": "2024 Race"},
    {"slug": "alter",  "recipient": "Alter, Ryan",             "display": "Ryan Alter",         "district": "District 5",   "race": "2022 Race"},
    {"slug": "laine",  "recipient": "Laine, Krista M.",        "display": "Krista Laine",       "district": "District 6",   "race": "2024 Race"},
    {"slug": "ellis",  "recipient": "Ellis, Paige",            "display": "Paige Ellis",        "district": "District 8",   "race": "2022 Race"},
    {"slug": "duchen", "recipient": "Duchen, Marc",            "display": "Marc Duchen",        "district": "District 10",  "race": "2024 Race"},
]


def make_profile_html(slug: str) -> str:
    """Copy profile_template.html to profile_{slug}.html with PROFILE_SLUG injected."""
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()

    marker = "// Override this in copies: const PROFILE_SLUG = 'watson';"
    if marker not in html:
        raise RuntimeError("Template slug marker not found — did profile_template.html change?")
    html = html.replace(marker, f"const PROFILE_SLUG = '{slug}';")

    out_path = os.path.join(ROOT, f"profile_{slug}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def fmt_money(n: int) -> str:
    """$3,203,912 -> $3.2M ; $357,094 -> $357K (matches existing card style)."""
    if n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"${round(n/1_000)}K"
    return f"${n}"


def build_one(entry: dict):
    slug = entry["slug"]
    print("=" * 78)
    print(f"BUILD  {entry['display']}  ({entry['district']})  slug={slug}")
    print("=" * 78)

    data_payload, _ = gpd.generate(entry["recipient"], ROOT, slug_override=slug)
    html_path = make_profile_html(slug)
    print(f"Rendered: {html_path}")

    hero = data_payload["hero"]
    raised = fmt_money(hero["total_raised"])
    donors = f"{hero['unique_donors']:,}"
    empct = f"{hero['employer_affiliated_pct']}%"

    card = (
        f'    <a class="card" href="profile_{slug}.html">\n'
        f'      <div class="card-name">{entry["display"]} <span class="badge badge-live">Live</span></div>\n'
        f'      <div class="card-meta">{entry["district"]} · {entry["race"]}</div>\n'
        f'      <div class="card-stats">\n'
        f'        <div><div class="stat-val">{raised}</div><div class="stat-lbl">Raised</div></div>\n'
        f'        <div><div class="stat-val">{donors}</div><div class="stat-lbl">Donors</div></div>\n'
        f'        <div><div class="stat-val">{empct}</div><div class="stat-lbl">Employer-affiliated</div></div>\n'
        f'      </div>\n'
        f'    </a>'
    )
    print("\n--- index.html card ------------------------------------------------------")
    print(card)
    print("--------------------------------------------------------------------------\n")
    return entry, hero


def main():
    p = argparse.ArgumentParser(description="Build a static profile for an enriched candidate")
    p.add_argument("--all-remaining", action="store_true", help="Build every candidate in ROSTER")
    p.add_argument("--slug", help="Build one candidate from ROSTER by slug")
    p.add_argument("--recipient", help="Ad-hoc: exact recipient string (requires --slug)")
    args = p.parse_args()

    if args.recipient:
        if not args.slug:
            p.error("--recipient requires --slug")
        build_one({"slug": args.slug, "recipient": args.recipient,
                   "display": args.slug.title(), "district": "?", "race": "?"})
        return

    if args.slug:
        entry = next((e for e in ROSTER if e["slug"] == args.slug), None)
        if not entry:
            p.error(f"slug '{args.slug}' not in ROSTER: {[e['slug'] for e in ROSTER]}")
        build_one(entry)
        return

    if args.all_remaining:
        results = [build_one(e) for e in ROSTER]
        print("\n\n#### SUMMARY — all remaining incumbents built ####")
        for entry, hero in results:
            print(f"  {entry['display']:20} {entry['district']:12} "
                  f"${hero['total_raised']:>10,}  {hero['unique_donors']:>5} donors  "
                  f"{hero['employer_affiliated_pct']}% empl")
        return

    p.error("nothing to do: pass --all-remaining, --slug, or --recipient")


if __name__ == "__main__":
    main()
