"""Refresh austin_landing.json card stats from built <slug>_data.json files.

Counterpart of san-antonio-finance-data/_update_landing.py: updates
raised / donors / empPct / topGroups on cards whose profile data exists so the
landing always matches the published profiles (the cards had drifted to a
2026-07-17 snapshot — 14 of them disagreed with their own profile pages by
2026-08-17). Leaves every other card field alone; does not flip `soon` cards.
Run after build_candidate.py, then update_landing_cycles.py for the on-ballot
cycle stamps.

Usage: python refresh_landing_cards.py [slug ...]   (no args = every card)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.join(ROOT, "austin_landing.json")


def fmt_money(n: float) -> str:
    if n >= 1e6:
        return f"${n / 1e6:.1f}M"
    if n >= 1e3:
        return f"${round(n / 1e3)}K"
    return f"${round(n)}"


def main():
    only = set(sys.argv[1:])
    with open(LANDING, encoding="utf-8") as f:
        landing = json.load(f)

    for c in landing["candidates"]:
        slug = c.get("slug")
        if only and slug not in only:
            continue
        path = os.path.join(ROOT, f"{slug}_data.json")
        if c.get("soon") or not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        hero = d["hero"]
        groups = [g for g in d["interest_groups"] if g["label"] != "Unknown"][:4]
        top = max((g["total"] for g in groups), default=1) or 1
        c["raised"] = fmt_money(hero["total_raised"])
        c["donors"] = f"{hero['unique_donors']:,}"
        c["empPct"] = f"{hero['employer_affiliated_pct']:.1f}%"
        c["topGroups"] = [{"label": g["label"], "amt": fmt_money(g["total"]),
                           "w": max(1, round(100 * g["total"] / top))} for g in groups]
        print(f"  {slug:15} {c['raised']} / {c['donors']} donors / {c['empPct']} affiliated")

    with open(LANDING, "w", encoding="utf-8", newline="\n") as f:
        json.dump(landing, f, indent=1, ensure_ascii=False)
    print("landing cards refreshed")


if __name__ == "__main__":
    main()
