"""
update_landing_cycles.py
Stamp each austin_landing.json card with on_ballot (is this person on this
November's ballot?) and, when they are, their current-cycle raised/donors.

The landing page then shows on-ballot members' cards as "raised this cycle"
and everyone else as "raised overall" — the same split the profile pages use
for their default cycle view. Re-run after refreshing the DB.
"""

import json
import os
import sqlite3
from datetime import datetime

from generate_profile_data import CANDIDATE_CYCLES

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "austin_finance.db")
LANDING = os.path.join(ROOT, "austin_landing.json")


def fmt_money(n: float) -> str:
    if n >= 1e6:
        return f"${n / 1e6:.1f}M"
    if n >= 1e3:
        return f"${round(n / 1e3)}K"
    return f"${round(n)}"


def current_cycle(slug):
    """The cycle on this November's ballot, or None. 'Final Term' is a
    wind-down (Gómez retired), not a campaign."""
    cycles = CANDIDATE_CYCLES.get(slug, [])
    if not cycles:
        return None
    last = cycles[-1]
    if last["election_year"] == datetime.now().year and last["label"] != "Final Term":
        return last
    return None


def main():
    with open(LANDING, encoding="utf-8") as f:
        landing = json.load(f)

    conn = sqlite3.connect(DB_PATH, timeout=120)
    cur = conn.cursor()

    for c in landing["candidates"]:
        slug = c.get("slug")
        cyc = current_cycle(slug)
        c["on_ballot"] = cyc is not None
        if cyc is None:
            c.pop("raised_cycle", None)
            c.pop("donors_cycle", None)
            c["show_cycle"] = False
            continue
        # Recipient string lives in the profile data snapshot.
        with open(os.path.join(ROOT, f"{slug}_data.json"), encoding="utf-8") as f:
            recipient = json.load(f)["meta"]["candidate_name"]
        params = [recipient]
        start_clause = ""
        if cyc["start_year"] is not None:
            start_clause = "AND cf.contribution_year >= ?"
            params.append(cyc["start_year"])
        raised, donors = cur.execute(f"""
            SELECT ROUND(SUM(COALESCE(cf.balanced_amount, cf.contribution_amount))),
                   COUNT(DISTINCT cf.donor_id)
            FROM campaign_finance cf
            WHERE cf.recipient = ? {start_clause}
              AND COALESCE(cf.balanced_amount, cf.contribution_amount) > 0
        """, params).fetchone()
        c["raised_cycle"] = fmt_money(raised or 0)
        c["donors_cycle"] = f"{donors or 0:,}"
        # A $0 cycle (Harper-Madison holds a 2026 slot in the roster but has
        # raised nothing and isn't seeking re-election) falls back to the
        # overall display rather than advertising an empty campaign.
        c["show_cycle"] = bool(raised)
        print(f"  {slug:15} on ballot — {c['raised_cycle']} this cycle "
              f"({c['donors_cycle']} donors) vs {c['raised']} overall"
              + ("" if raised else "  [zero — card stays on overall]"))

    conn.close()
    with open(LANDING, "w", encoding="utf-8") as f:
        json.dump(landing, f, indent=1, ensure_ascii=False)
    on = sum(1 for c in landing["candidates"] if c["on_ballot"])
    print(f"wrote {LANDING} — {on}/{len(landing['candidates'])} on this November's ballot")


if __name__ == "__main__":
    main()
