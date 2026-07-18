"""
build_race.py
Repeatable driver that turns a race entry in austin_races.json into a published
race view page:

    1. Computes per-candidate cycle stats from austin_finance.db
       -> austin_race_stats.json  (keyed by candidate slug)
    2. Materializes austin/<race_id>/index.html from race_template.html
       (injects RACE_ID + OG meta), same pattern as build_candidate.py

Adding District 3/5/8/9 later is a data change: add a race entry to
austin_races.json, then run `python build_race.py --race district3`.
No new page logic.

Stats are computed on a CYCLE basis (contributions from cycle_start_year
forward), not lifetime, so a candidate who has run before -- Ramos ran for this
same seat in 2022 -- is compared on this race only. Comparing his lifetime
total against a first-time candidate's would overstate his position in this
race by roughly a third.

Usage:
    python build_race.py --race district1
    python build_race.py --all
    python build_race.py --race district1 --html-only
"""

import argparse
import json
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "austin_finance.db")
TEMPLATE = os.path.join(ROOT, "race_template.html")
RACES_JSON = os.path.join(ROOT, "austin_races.json")
STATS_JSON = os.path.join(ROOT, "austin_race_stats.json")


def load_races():
    with open(RACES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def candidate_stats(cur, recipient: str, cycle_start_year: int):
    """Cycle-basis hero stats + top industries for one candidate."""
    row = cur.execute("""
        SELECT ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount))) AS raised,
               COUNT(DISTINCT cf.donor_id) AS donors,
               COUNT(*) AS contributions,
               MIN(cf.contribution_date) AS first_gift,
               MAX(cf.contribution_date) AS last_gift
        FROM campaign_finance cf
        WHERE cf.recipient = ?
          AND cf.contribution_year >= ?
          AND COALESCE(cf.balanced_amount, cf.contribution_amount) > 0
    """, (recipient, cycle_start_year)).fetchone()

    raised, donors, contributions, first_gift, last_gift = row
    if not donors:
        return None

    igs = cur.execute("""
        SELECT di.resolved_industry,
               ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount)))
        FROM campaign_finance cf
        JOIN donor_identities di ON di.donor_id = cf.donor_id
        WHERE cf.recipient = ?
          AND cf.contribution_year >= ?
          AND di.resolved_industry IS NOT NULL
          AND COALESCE(cf.balanced_amount, cf.contribution_amount) > 0
        GROUP BY 1 ORDER BY 2 DESC LIMIT 4
    """, (recipient, cycle_start_year)).fetchall()

    top = max((g[1] for g in igs), default=0) or 1
    return {
        "raised": int(raised or 0),
        "donors": donors,
        "contributions": contributions,
        "avg": round((raised or 0) / donors, 2),
        "first_gift": (first_gift or "")[:10],
        "last_gift": (last_gift or "")[:10],
        "topGroups": [
            {"label": g[0], "amt": int(g[1]), "w": round(g[1] / top * 100)}
            for g in igs
        ],
    }


def build_stats(races) -> dict:
    """Recompute stats for every candidate across every race; write STATS_JSON."""
    conn = sqlite3.connect(DB_PATH, timeout=120)
    cur = conn.cursor()
    stats = {}
    for race in races["races"]:
        cycle = race.get("cycle_start_year", 2025)
        for c in race["candidates"]:
            if not c.get("slug") or not c.get("recipient"):
                continue
            s = candidate_stats(cur, c["recipient"], cycle)
            if s is None:
                print(f"  ! {c['name']}: no rows from {cycle} forward — card renders as pending")
                continue
            stats[c["slug"]] = s
            print(f"  {c['name']:22} ${s['raised']:>8,}  {s['donors']:>4} donors  "
                  f"avg ${s['avg']:>7,.0f}  {s['first_gift']}..{s['last_gift']}")
    conn.close()
    with open(STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=1)
    print(f"wrote {STATS_JSON} ({len(stats)} candidates)")
    return stats


def og_meta_for(race, stats) -> dict:
    live = [c for c in race["candidates"] if c.get("slug") and c["slug"] in stats]
    total = sum(stats[c["slug"]]["raised"] for c in live)
    n = len(race["candidates"])
    return {
        "title": f"{race['seat']} 2026 — Austin Campaign Finance — decode(politics):",
        "desc": (
            f"{n} candidates are running for Austin City Council {race['seat']}, an open seat. "
            f"${total:,} raised so far this cycle, decoded donor by donor."
        ),
        "alt": f"Austin City Council {race['seat']} 2026 candidates — campaign money decoded by decode(politics):",
    }


def make_race_html(race, stats) -> str:
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()

    new_html, n = re.subn(
        r"const RACE_ID = '[^']*';",
        f"const RACE_ID = '{race['race_id']}';",
        html, count=1,
    )
    if n != 1:
        raise RuntimeError("RACE_ID line not found in race_template.html")

    og = og_meta_for(race, stats)
    new_html = (
        new_html.replace("__RACE_ID__", race["race_id"])
        .replace("__OG_TITLE__", og["title"])
        .replace("__OG_DESC__", og["desc"])
        .replace("__OG_ALT__", og["alt"])
    )

    out_dir = os.path.join(ROOT, "austin", race["race_id"])
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    return out_path


def main():
    p = argparse.ArgumentParser(description="Build a race view page from austin_races.json")
    p.add_argument("--race", help="race_id to build (e.g. district1)")
    p.add_argument("--all", action="store_true", help="build every race in austin_races.json")
    p.add_argument("--html-only", action="store_true", help="skip stat recompute; reuse austin_race_stats.json")
    args = p.parse_args()

    races = load_races()

    if args.html_only:
        with open(STATS_JSON, "r", encoding="utf-8") as f:
            stats = json.load(f)
        print(f"reusing {STATS_JSON} ({len(stats)} candidates)")
    else:
        print("Computing candidate cycle stats...")
        stats = build_stats(races)

    targets = races["races"] if args.all else [r for r in races["races"] if r["race_id"] == args.race]
    if not targets:
        p.error(f"race '{args.race}' not found. Available: "
                f"{[r['race_id'] for r in races['races']]}")

    for race in targets:
        path = make_race_html(race, stats)
        print(f"Rendered: {path}  ->  /austin/{race['race_id']}/")


if __name__ == "__main__":
    main()
