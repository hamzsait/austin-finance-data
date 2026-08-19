"""
fec_dedup_pass.py
Repair FEC receipts attributed to more than one donor identity.
Kept in sync with the SA repo's sa_fec_dedup_pass.py.

The 2026-08-19 identity-fragmentation scan found 3,080 Austin clusters
where two or more donor_ids share literal fec_sub_id rows in
fec_contributions_raw: the same federal receipt counted once per fragment,
multiplying every FEC-derived number (partisan lean, ip/ff/gun spectrum
totals) by the fragment count — e.g. Robert Epstein's AIPAC-spectrum total
appeared 4x.

A shared sub_id proves double-attribution but NOT that the fragments are one
person: two different local "Maria Garcia"s can both fuzzy-match the same
federal receipt (the adjudicated Salazar pair in the SA repo is exactly this).
So the pass has three arms:

  MERGE  — fragments that are near-certainly the same person: compatible
           names PLUS person-level corroboration (same zip5, employer token
           overlap) or a distinctive name pattern (compound surname split
           "Bar Yadin"/"Yadin", spacing/hyphen variant, reversed name).
           Mechanics ported from the SA repo's sa_identity_merge.py:
           remap campaign_finance.donor_id/donor_id_2,
           fec_contributions_raw.donor_id (UNIQUE(donor_id, fec_sub_id)
           absorbs the duplicate receipts), texas_contributions_raw
           .austin_donor_id, joint_donations.donor_id_1/2; fold identity
           rows (LOCAL aggregates are disjoint row sets and are SUMMED;
           enrichment columns are COALESCEd, never summed); record in
           identity_merges; delete losers.
  STRIP  — name-compatible but uncorroborated (or name-conflicting)
           fragments stay separate people; each shared sub_id is assigned
           to the donor whose canonical zip5 matches the FEC row's
           contributor zip (then employer-token match, then confirm_score
           margin >= 10), and the duplicate rows are deleted from the rest.
           Kills the double-count without guessing about identity.
  REVIEW — shared sub_ids with no decisive owner are left in place and
           written to fec_dedup_review.csv for human adjudication.

After the pass, fec_total_dem/rep/other/donations and fec_partisan_lean are
recomputed from the deduped raw table for every touched donor. The
spectrum flags are NOT recomputed here — re-run the (idempotent, local)
tec_partisan_aggregate.py, ip_spectrum_flag.py, fossil_fuel_flag.py and
gun_lobby_flag.py afterwards, then rebuild profiles.

Idempotent: a second run finds no shared sub_ids in the merged/stripped
clusters and only re-reports the review remainder.

Usage:
    python fec_dedup_pass.py --dry-run   # print the plan, write review CSV
    python fec_dedup_pass.py             # apply
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "austin_finance.db"

# Same nickname map as fec_enrich.py (inlined: this script must stay stdlib-only).
NICKNAMES = {
    "bill": "william", "billy": "william", "will": "william",
    "bob": "robert", "rob": "robert", "bobby": "robert",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "tom": "thomas", "tommy": "thomas",
    "mike": "michael", "mick": "michael",
    "dick": "richard", "rick": "richard", "ricky": "richard",
    "dave": "david",
    "joe": "joseph", "joey": "joseph",
    "sue": "susan", "susie": "susan",
    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth",
    "kate": "katherine", "kathy": "katherine",
    "chris": "christopher",
    "dan": "daniel", "danny": "daniel",
    "sam": "samuel",
    "ed": "edward", "ted": "edward",
    "ben": "benjamin",
    "nick": "nicholas",
    "tony": "anthony",
    "andy": "andrew",
    "alex": "alexander",
    "greg": "gregory",
    "ken": "kenneth",
    "steve": "steven", "stephen": "steven",
    "matt": "matthew",
    "jeff": "jeffrey",
    "jerry": "gerald",
    "chuck": "charles", "charlie": "charles",
    "hank": "henry",
    "jack": "john", "jon": "john", "johnny": "john",
    "peggy": "margaret", "meg": "margaret",
    "frank": "francis",
    "fred": "frederick",
    "jake": "jacob",
    "ron": "ronald",
    "tim": "timothy",
    "phil": "philip",
    "don": "donald",
    "pam": "pamela",
    "deb": "deborah", "debbie": "deborah",
}

EMP_STOPWORDS = {
    "inc", "llc", "llp", "lp", "ltd", "co", "corp", "company", "the", "of",
    "and", "group", "self", "employed", "selfemployed", "retired", "none",
    "na", "n/a", "not", "unemployed", "homemaker", "owner", "president",
    "attorney", "consultant",
}

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq", "dds"}

ENRICHED_FIELDS = ("resolved_industry", "resolved_employer_display",
                   "fec_partisan_lean", "fec_matched", "tec_matched",
                   "ip_spectrum", "ff_spectrum", "gun_spectrum")

# Pairs a human has ruled to be DIFFERENT people — never auto-merge them.
# (None adjudicated for Austin yet; the SA repo carries the Salazar pair.)
ADJUDICATED_SEPARATE: set = set()

# Sub_ids attributed to 2+ donors, set by plan(); donor_info() excludes them
# when building trail evidence.
SHARED_SUBIDS: set = set()


def to_ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def norm_tokens(s: str) -> list[str]:
    s = to_ascii(s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return [t for t in s.split() if t]


def parse_name(name: str) -> tuple[str, str, list[str]]:
    """'Last Words, First Middle...' -> (last, first, middles). No comma:
    whole string as last (entities)."""
    if "," in (name or ""):
        last_part, _, rest = name.partition(",")
        last_toks = [t for t in norm_tokens(last_part) if t not in SUFFIXES]
        rest_toks = [t for t in norm_tokens(rest) if t not in SUFFIXES]
        # Leading stray initial glued onto the surname ("J Wylie, Albert")
        if len(last_toks) >= 2 and len(last_toks[0]) == 1:
            last_toks = last_toks[1:]
        first = rest_toks[0] if rest_toks else ""
        return " ".join(last_toks), first, rest_toks[1:]
    # Comma-less "First [Middle] Last" ("Joe Liemandt") — take the final
    # token as the surname so it can match its "Last, First" twin.
    toks = [t for t in norm_tokens(name) if t not in SUFFIXES]
    if 2 <= len(toks) <= 3:
        return toks[-1], toks[0], toks[1:-1]
    return " ".join(toks), "", []


def nick(first: str) -> str:
    return NICKNAMES.get(first, first)


def zip5(z: str | None) -> str:
    m = re.match(r"\D*(\d{5})", z or "")
    return m.group(1) if m else ""


def emp_tokens(emp: str | None) -> set[str]:
    return {t for t in norm_tokens(emp or "") if t not in EMP_STOPWORDS and len(t) > 1}


def name_pattern(a: dict, b: dict) -> str | None:
    """Classify how two donor names relate. Returns pattern tag or None
    (incompatible)."""
    la, fa, ma = a["nparse"]
    lb, fb, mb = b["nparse"]
    if not la or not lb:
        return None
    if la == lb and fa == fb:
        # Conflicting middle initials = different people (John A vs John B)
        if ma and mb and ma[0][0] != mb[0][0]:
            return None
        return "exact" if (ma == mb) else "mi-variant"
    if la.replace(" ", "") == lb.replace(" ", "") and fa == fb:
        return "spacing"
    if fa and fa == fb:
        # Compound surname split: one's full surname is the last word of the other's
        wa, wb = la.split(), lb.split()
        if (len(wa) > 1 and wa[-1] == lb) or (len(wb) > 1 and wb[-1] == la):
            return "compound"
    if la == lb and fa and fb and nick(fa) == nick(fb):
        if ma and mb and ma[0][0] != mb[0][0]:
            return None
        return "nickname"
    if fa and fb and la == fb and fa == lb:
        return "reversed"
    return None


JOINT_RE = re.compile(r"\b(?:&|and)\b", re.I)


def strong_link(a: dict, b: dict) -> str | None:
    """Merge-grade link: compatible names + person-level corroboration, or a
    distinctive pattern that is corroboration by itself."""
    # Joint-donor strings ("Krumme, Robin & Gregg") interact with the joint/
    # shadow-row machinery — never fold them into an individual. Two exact
    # copies of the same joint identity may still merge with each other.
    if frozenset({a["id"], b["id"]}) in ADJUDICATED_SEPARATE:
        return None
    a_joint = bool(JOINT_RE.search(a["name"]))
    b_joint = bool(JOINT_RE.search(b["name"]))
    if a_joint or b_joint:
        na = " ".join(norm_tokens(a["name"]))
        nb = " ".join(norm_tokens(b["name"]))
        return "exact-joint" if (a_joint and b_joint and na == nb) else None
    pat = name_pattern(a, b)
    if pat is None:
        return None
    if pat in ("spacing", "compound", "reversed"):
        return pat
    if (a["zip5"] and a["zip5"] == b["zip5"]) or (a["emp"] & b["emp"]):
        return pat
    # Mover corroboration from the federal record trail: the same FEC
    # contributor was recorded at BOTH donors' addresses. A mis-matched
    # doppelganger fails this — its own zip never shows up in the other
    # fragment's federal rows.
    if (a["zip5"] and b["zip5"] and
            a["zip5"] in b["fzips"] and b["zip5"] in a["fzips"]):
        return "fec-span"
    if (a["emp"] and b["emp"] and
            (a["emp"] & b["femps"]) and (b["emp"] & a["femps"])):
        return "fec-span-emp"
    # One side has no canonical zip/employer at all (thin fragment — PO box
    # or unparseable address): accept the one-directional trail check, but
    # only for byte-identical names, where a doppelganger is least likely.
    if pat == "exact":
        if a["zip5"] and not b["zip5"] and a["zip5"] in b["fzips"]:
            return "fec-span-thin"
        if b["zip5"] and not a["zip5"] and b["zip5"] in a["fzips"]:
            return "fec-span-thin"
        if a["emp"] and not b["emp"] and (a["emp"] & b["femps"]):
            return "fec-span-thin-emp"
        if b["emp"] and not a["emp"] and (b["emp"] & a["femps"]):
            return "fec-span-thin-emp"
    return None


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def load_components(cur) -> tuple[list[list[str]], set[str]]:
    """Connected components of donor_ids linked by shared fec_sub_ids, plus
    the set of every shared sub_id (needed to compute exclusive trails)."""
    dsu = DSU()
    linked = set()
    shared_subids = set()
    for sub_id, ids_csv in cur.execute("""
        SELECT fec_sub_id, GROUP_CONCAT(DISTINCT donor_id)
        FROM fec_contributions_raw
        WHERE fec_sub_id IS NOT NULL AND fec_sub_id != ''
        GROUP BY fec_sub_id HAVING COUNT(DISTINCT donor_id) > 1
    """):
        shared_subids.add(sub_id)
        ids = ids_csv.split(",")
        linked.update(ids)
        for other in ids[1:]:
            dsu.union(ids[0], other)
    comps = defaultdict(list)
    for did in linked:
        comps[dsu.find(did)].append(did)
    return [sorted(v) for v in comps.values() if len(v) > 1], shared_subids


def donor_info(cur, ids: list[str]) -> dict[str, dict]:
    out = {}
    ph = ",".join("?" * len(ids))
    for row in cur.execute(f"""
        SELECT donor_id, canonical_name, canonical_zip, canonical_employer,
               record_count FROM donor_identities WHERE donor_id IN ({ph})""", ids):
        out[row[0]] = {
            "id": row[0], "name": row[1] or "", "zip5": zip5(row[2]),
            "emp": emp_tokens(row[3]), "records": row[4] or 0,
            "nparse": parse_name(row[1] or ""),
        }
    # ids present in fec_contributions_raw but missing from donor_identities
    # (shouldn't happen; treat as bare ids so the strip arm can still run)
    for did in ids:
        out.setdefault(did, {"id": did, "name": "", "zip5": "", "emp": set(),
                             "records": 0, "nparse": ("", "", [])})
    # Federal record trail per donor — from rows EXCLUSIVE to that donor
    # (shared rows are the very duplication in question: two doppelgangers
    # holding the same mis-matched receipt set would each "corroborate" the
    # other from it, which is how the adjudicated Salazar pair would falsely
    # merge). Only receipts nobody else holds count as trail evidence.
    for did in ids:
        out[did]["fzips"] = set()
        out[did]["femps"] = set()
    for did, sid, fzip, femp in cur.execute(f"""
        SELECT donor_id, fec_sub_id, fec_contributor_zip, fec_employer
        FROM fec_contributions_raw WHERE donor_id IN ({ph})""", ids):
        if sid in SHARED_SUBIDS:
            continue
        z = zip5(fzip)
        if z:
            out[did]["fzips"].add(z)
        out[did]["femps"] |= emp_tokens(femp)
    return out


def plan(cur):
    """Build the merge groups and the strip/review row plan."""
    global SHARED_SUBIDS
    comps, SHARED_SUBIDS = load_components(cur)
    print(f"[fec-dedup] {len(comps)} shared-receipt components "
          f"({sum(len(c) for c in comps)} donor_ids)")

    merge_groups = []          # list[list[donor_id]] — each merges to one person
    strip_components = []      # components (post-merge grouping) needing row assignment
    link_tags = Counter()

    for comp in comps:
        info = donor_info(cur, comp)
        sub = DSU()
        for i, a in enumerate(comp):
            for b in comp[i + 1:]:
                tag = strong_link(info[a], info[b])
                if tag:
                    sub.union(a, b)
                    link_tags[tag] += 1
        groups = defaultdict(list)
        for did in comp:
            groups[sub.find(did)].append(did)
        gs = [sorted(g) for g in groups.values()]
        for g in gs:
            if len(g) > 1:
                merge_groups.append(g)
        if len(gs) > 1:
            # After merging, distinct persons still share receipts -> strip arm
            strip_components.append((comp, [g[0] for g in gs], info))

    print(f"[fec-dedup] merge: {len(merge_groups)} people from "
          f"{sum(len(g) for g in merge_groups)} ids "
          f"(links: {dict(link_tags)})")
    print(f"[fec-dedup] strip: {len(strip_components)} components keep 2+ people")
    return merge_groups, strip_components


def pick_winner(cur, group: list[str]) -> str:
    rows = {}
    ph = ",".join("?" * len(group))
    cols = ["donor_id", "record_count"] + list(ENRICHED_FIELDS)
    for row in cur.execute(
            f"SELECT {', '.join(cols)} FROM donor_identities WHERE donor_id IN ({ph})",
            group):
        rows[row[0]] = dict(zip(cols, row))

    def rank(did):
        r = rows.get(did, {})
        enriched = sum(1 for f in ENRICHED_FIELDS if r.get(f))
        return (-enriched, -(r.get("record_count") or 0), did)
    return min(group, key=rank)


def apply_merges(cur, merge_groups: list[list[str]]) -> dict[str, str]:
    ident_cols = [r[1] for r in cur.execute("PRAGMA table_info(donor_identities)")]
    summed = {"total_donated", "record_count"}
    special = summed | {"donor_id", "canonical_name", "canonical_zip",
                        "canonical_employer", "campaigns", "campaign_count",
                        "first_seen", "last_seen"}
    coalesce_cols = [c for c in ident_cols if c not in special]

    def ident_row(did):
        row = cur.execute(
            f"SELECT {', '.join(ident_cols)} FROM donor_identities WHERE donor_id=?",
            (did,)).fetchone()
        return dict(zip(ident_cols, row)) if row else {}

    winner_of = {}
    for group in merge_groups:
        winner = pick_winner(cur, group)
        for l in group:
            if l != winner:
                winner_of[l] = winner

    cur.execute("""CREATE TABLE IF NOT EXISTS identity_merges (
                       merged_donor_id TEXT PRIMARY KEY,
                       into_donor_id   TEXT NOT NULL,
                       person_key      TEXT,
                       merged_at       TEXT)""")

    # Remap every table that references a merged id. UPDATE OR REPLACE:
    # fec_contributions_raw is UNIQUE(donor_id, fec_sub_id), so the colliding
    # duplicate receipts are absorbed here — that IS the dedup.
    cur.execute("CREATE TEMP TABLE _idmap (old TEXT PRIMARY KEY, new TEXT)")
    cur.executemany("INSERT INTO _idmap VALUES (?,?)", sorted(winner_of.items()))
    remaps = [("campaign_finance", "donor_id"),
              ("campaign_finance", "donor_id_2"),
              ("fec_contributions_raw", "donor_id"),
              ("texas_contributions_raw", "austin_donor_id"),
              ("joint_donations", "donor_id_1"),
              ("joint_donations", "donor_id_2")]
    for table, col in remaps:
        if not cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                           (table,)).fetchone():
            continue
        pre = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        n = cur.execute(
            f"""UPDATE OR REPLACE {table}
                SET {col} = (SELECT new FROM _idmap WHERE old = {col})
                WHERE {col} IN (SELECT old FROM _idmap)""").rowcount
        absorbed = pre - cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if n:
            print(f"[fec-dedup] remapped {n:,} rows in {table}.{col}"
                  + (f" ({absorbed:,} duplicate rows absorbed)" if absorbed else ""))
    cur.execute("DROP TABLE _idmap")

    # Fold identity rows. Local aggregates are disjoint per donor_id -> SUM;
    # enrichment columns COALESCE by (winner, then record_count) precedence —
    # never summed: fragments matched the SAME federal records, and the fec_*
    # numbers are recomputed from the deduped raw table afterwards anyway.
    for group in merge_groups:
        winner = next(w for w in group if w not in winner_of)
        rows = {d: ident_row(d) for d in group}
        ordered = [winner] + sorted((d for d in group if d != winner),
                                    key=lambda d: (-(rows[d].get("record_count") or 0), d))
        campaigns = sorted({c for d in group
                            for c in (rows[d].get("campaigns") or "").split("|") if c})
        first_seen = min((rows[d].get("first_seen") for d in group
                          if rows[d].get("first_seen")), default="")
        last_seen = max((rows[d].get("last_seen") for d in group
                         if rows[d].get("last_seen")), default="")
        # Canonical name from the most common raw donor string post-remap:
        # keeps compound surnames like "Bar Yadin" intact, which the
        # name-matched civic_affiliations bucket depends on. Ties break on
        # quality — penalize joint strings, glued leading initials, and
        # shouting caps — so "Lopez, Steven" beats "Steven Lopez, Steven".
        def name_quality(n: str) -> tuple:
            penalty = 0
            if JOINT_RE.search(n):
                penalty += 4
            head = n.split(",")[0].strip()
            if re.match(r"^[A-Za-z]\.? ", head):
                penalty += 2
            if n.isupper():
                penalty += 1
            return (-penalty, len(n))
        names = Counter(r[0] for r in cur.execute(
            "SELECT donor FROM campaign_finance WHERE donor_id=? AND donor IS NOT NULL",
            (winner,)))
        best_name = (max(names.items(), key=lambda kv: (kv[1], *name_quality(kv[0])))[0]
                     if names else rows[ordered[0]].get("canonical_name"))
        updates = {
            "canonical_name": best_name,
            "canonical_zip": next((rows[d].get("canonical_zip") for d in ordered
                                   if rows[d].get("canonical_zip")), ""),
            "canonical_employer": next((rows[d].get("canonical_employer") for d in ordered
                                        if rows[d].get("canonical_employer")), ""),
            "total_donated": round(sum(rows[d].get("total_donated") or 0 for d in group), 2),
            "record_count": sum(rows[d].get("record_count") or 0 for d in group),
            "campaigns": "|".join(campaigns),
            "campaign_count": len(campaigns),
            "first_seen": first_seen,
            "last_seen": last_seen,
        }
        for col in coalesce_cols:
            updates[col] = next((rows[d].get(col) for d in ordered
                                 if rows[d].get(col) is not None), None)
        sets = ", ".join(f"{c}=?" for c in updates)
        cur.execute(f"UPDATE donor_identities SET {sets} WHERE donor_id=?",
                    (*updates.values(), winner))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur.executemany("DELETE FROM donor_identities WHERE donor_id=?",
                    [(l,) for l in winner_of])
    cur.executemany(
        """INSERT OR REPLACE INTO identity_merges
           (merged_donor_id, into_donor_id, person_key, merged_at)
           VALUES (?,?,'fec-dedup-shared-subid',?)""",
        [(l, w, now) for l, w in winner_of.items()])
    print(f"[fec-dedup] merged {len(winner_of)} donor_ids into "
          f"{len(merge_groups)} people")
    return winner_of


def strip_rows(cur, strip_components, winner_of, dry_run, review_path):
    """Assign each still-shared sub_id to one owner; delete the other copies.
    Undecidable sub_ids go to the review CSV, rows left in place."""
    deleted = 0
    review = []
    resolved = lambda d: winner_of.get(d, d)

    for comp, _reps, info in strip_components:
        if len({resolved(d) for d in comp}) < 2:
            continue
        # Query over the ORIGINAL component ids and resolve each row to its
        # post-merge owner: in --dry-run the merges haven't been applied, so
        # rows still sit under loser ids; after a real merge those ids simply
        # hold no rows and the resolution is a no-op.
        ph = ",".join("?" * len(comp))
        shared = defaultdict(list)   # sub_id -> [(resolved_donor, row_id, fec_zip, fec_emp, score)]
        for did, rid, sid, fzip, femp, score in cur.execute(f"""
            SELECT donor_id, id, fec_sub_id, fec_contributor_zip, fec_employer,
                   confirm_score
            FROM fec_contributions_raw
            WHERE donor_id IN ({ph}) AND fec_sub_id IN (
                SELECT fec_sub_id FROM fec_contributions_raw
                WHERE donor_id IN ({ph})
                GROUP BY fec_sub_id HAVING COUNT(DISTINCT donor_id) > 1)
            """, comp + comp):
            shared[sid].append((resolved(did), rid, zip5(fzip), emp_tokens(femp), score or 0))

        # Component-level trail ownership: across ALL receipts this federal
        # contributor trail contains, which donors' canonical zips ever
        # appear? If exactly one, the whole trail is that donor's — receipts
        # whose own row zip matches neither donor (PO box, third address)
        # follow the trail owner instead of stalling in review.
        trail_zips = {r[2] for rows in shared.values() for r in rows if r[2]}
        trail_owners = sorted({d for rows in shared.values() for r in rows
                               for d in [r[0]]
                               if info.get(d, {}).get("zip5") and
                               info[d]["zip5"] in trail_zips})

        for sid, rows in shared.items():
            dids = sorted({r[0] for r in rows})
            if len(dids) < 2:
                continue
            fec_zip = next((r[2] for r in rows if r[2]), "")
            fec_emp = next((r[3] for r in rows if r[3]), set())
            zip_hits = [d for d in dids if fec_zip and info.get(d, {}).get("zip5") == fec_zip]
            emp_hits = [d for d in dids
                        if fec_emp and info.get(d, {}).get("emp", set()) & fec_emp]
            owner = None
            how = None
            if len(zip_hits) == 1:
                owner, how = zip_hits[0], "zip"
            elif len(emp_hits) == 1:
                owner, how = emp_hits[0], "employer"
            elif len(trail_owners) == 1 and trail_owners[0] in dids:
                owner, how = trail_owners[0], "trail"
            else:
                by_score = sorted({d: max(r[4] for r in rows if r[0] == d)
                                   for d in dids}.items(), key=lambda kv: -kv[1])
                if len(by_score) > 1 and by_score[0][1] - by_score[1][1] >= 10:
                    owner, how = by_score[0][0], "confirm_score"
            if owner:
                losers = [(r[1],) for r in rows if r[0] != owner]
                if not dry_run:
                    cur.executemany("DELETE FROM fec_contributions_raw WHERE id=?", losers)
                deleted += len(losers)
            else:
                for d in dids:
                    review.append({
                        "fec_sub_id": sid, "donor_id": d,
                        "donor_name": info.get(d, {}).get("name", ""),
                        "donor_zip": info.get(d, {}).get("zip5", ""),
                        "fec_zip": fec_zip,
                        "amount": next((r for r in cur.execute(
                            "SELECT contribution_amount FROM fec_contributions_raw "
                            "WHERE donor_id=? AND fec_sub_id=?", (d, sid))), [""])[0],
                    })

    with open(review_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fec_sub_id", "donor_id", "donor_name",
                                          "donor_zip", "fec_zip", "amount"])
        w.writeheader()
        w.writerows(review)
    n_review = len({r["fec_sub_id"] for r in review})
    print(f"[fec-dedup] strip: {'would delete' if dry_run else 'deleted'} "
          f"{deleted:,} duplicate receipt rows; {n_review} sub_ids -> review "
          f"({review_path.name})")
    return deleted


def recompute_fec_aggregates(cur):
    """Rebuild fec_total_* and fec_partisan_lean from the deduped raw table
    for every donor that currently has raw rows or non-zero stored totals."""
    cur.execute("""
        CREATE TEMP TABLE _fec_agg AS
        SELECT r.donor_id,
               SUM(CASE WHEN c.classification='Dem' THEN r.contribution_amount ELSE 0 END) dem,
               SUM(CASE WHEN c.classification='Rep' THEN r.contribution_amount ELSE 0 END) rep,
               SUM(CASE WHEN COALESCE(c.classification,'Other') NOT IN ('Dem','Rep')
                        THEN r.contribution_amount ELSE 0 END) other,
               COUNT(*) n
        FROM fec_contributions_raw r
        LEFT JOIN fec_committee_cache c ON c.committee_id = r.committee_id
        GROUP BY r.donor_id""")
    n = cur.execute("""
        UPDATE donor_identities SET
            fec_total_dem = COALESCE((SELECT dem FROM _fec_agg WHERE donor_id=donor_identities.donor_id), 0),
            fec_total_rep = COALESCE((SELECT rep FROM _fec_agg WHERE donor_id=donor_identities.donor_id), 0),
            fec_total_other = COALESCE((SELECT other FROM _fec_agg WHERE donor_id=donor_identities.donor_id), 0),
            fec_total_donations = COALESCE((SELECT n FROM _fec_agg WHERE donor_id=donor_identities.donor_id), 0),
            fec_partisan_lean = (SELECT CASE WHEN dem+rep > 0 THEN dem*1.0/(dem+rep) END
                                 FROM _fec_agg WHERE donor_id=donor_identities.donor_id)
        WHERE fec_matched = 1""").rowcount
    cur.execute("DROP TABLE _fec_agg")
    print(f"[fec-dedup] recomputed FEC aggregates for {n:,} fec_matched donors")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    merge_groups, strip_components = plan(cur)

    if args.dry_run:
        for g in merge_groups[:40]:
            names = [cur.execute(
                "SELECT canonical_name FROM donor_identities WHERE donor_id=?",
                (d,)).fetchone() for d in g]
            print("  MERGE:", " | ".join((r[0] if r else d) for r, d in zip(names, g)))
        if len(merge_groups) > 40:
            print(f"  ... {len(merge_groups) - 40} more merge groups")

    winner_of = {}
    if not args.dry_run and merge_groups:
        winner_of = apply_merges(cur, merge_groups)
    elif args.dry_run:
        for g in merge_groups:
            w = pick_winner(cur, g)
            for l in g:
                if l != w:
                    winner_of[l] = w

    strip_rows(cur, strip_components, winner_of, args.dry_run,
               ROOT / "fec_dedup_review.csv")

    if not args.dry_run:
        recompute_fec_aggregates(cur)
        conn.commit()
        print("[fec-dedup] committed. Now re-run: tec_partisan_aggregate.py, "
              "ip_spectrum_flag.py, fossil_fuel_flag.py, gun_lobby_flag.py, "
              "then rebuild profiles.")
    else:
        conn.rollback()
        print("[fec-dedup] --dry-run: no changes written")
    conn.close()


if __name__ == "__main__":
    main()
