"""Incremental donor/employer identity resolution for newly-ingested CITY rows
(donor_id IS NULL), matching against EXISTING identities — same logic and
thresholds as travis_ingest.py (which see). Never drops or re-mints existing
identities; new identities get the 'tcv-' prefix so downstream targeted FEC
runs can find them.

Scope: campaign_finance rows with donor_id IS NULL AND employer_id IS NULL
AND date_reported > --since (default 2026-03-09, the pre-July-refresh high
water mark).

Usage: python city_resolve_incremental.py [--dry-run] [--since YYYY-MM-DD]
"""
import argparse, re, sqlite3, uuid
from collections import defaultdict

import build_identities as BI
import build_employer_identities as BE
from build_joint_donors import ENTITY_KEYWORDS, JOINT_SEP

DB = "austin_finance.db"
AUTO, REVIEW_LOW, EMP_AUTO = 0.83, 0.65, 0.85

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--since", default="2026-03-09")
args = ap.parse_args()

conn = sqlite3.connect(DB, timeout=120)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

new_rows = cur.execute("""
    SELECT rowid, * FROM campaign_finance
    WHERE donor_id IS NULL AND employer_id IS NULL
      AND transaction_id NOT LIKE 'TRAVIS-%' AND date_reported > ?""",
    (args.since,)).fetchall()
print(f"rows to resolve: {len(new_rows)}")

# ---- index existing identities --------------------------------------------
existing = cur.execute(
    "SELECT donor_id, canonical_name, canonical_zip, canonical_employer FROM donor_identities").fetchall()
by_last = defaultdict(list)
for e in existing:
    last, first = BI.normalize_name(e["canonical_name"] or "")
    if last:
        by_last[last].append({
            "donor_id": e["donor_id"], "last": last, "first": first,
            "name": e["canonical_name"],
            "zip5": (e["canonical_zip"] or "")[:5] if re.match(r"^\d{5}", e["canonical_zip"] or "") else "",
            "emp_occ": (e["canonical_employer"] or "").lower(),
        })

def classify_donor(name, dtype):
    if dtype and dtype.upper() == "ENTITY":
        return "ENTITY"
    if not name or ENTITY_KEYWORDS.search(name):
        return "ENTITY"
    if "," in name and re.search(r"(&|\band\b|/)", name.split(",", 1)[1], re.I):
        return "JOINT"
    return "INDIVIDUAL"

def resolve_person(raw_name, csz, emp, occ):
    last, first = BI.normalize_name(raw_name)
    zip5 = BI.normalize_zip(csz)
    emp_occ = " ".join(sorted(set(
        (BI.normalize_employer(emp) + " " + BI.normalize_occupation(occ)).split())))
    me = {"last": last, "first": first, "zip5": zip5, "emp_occ": emp_occ}
    best, best_s = None, 0.0
    for cand in by_last.get(last, []):
        s = BI.score_pair(me, cand)
        if s > best_s:
            best, best_s = cand, s
    if best and best_s >= AUTO:
        return best["donor_id"], f"city26-match-{best_s:.2f}", False, (last, first, zip5)
    if best and best_s >= REVIEW_LOW:
        cur.execute("""INSERT INTO review_queue (donor_a, donor_b, zip_a, zip_b,
                       emp_occ_a, emp_occ_b, score, resolved) VALUES (?,?,?,?,?,?,?,?)""",
                    (raw_name, best["name"], zip5, best["zip5"], emp_occ, best["emp_occ"],
                     best_s, "city26-pending"))
    return None, None, True, (last, first, zip5)

def mint_identity(sample, prows):
    did = "tcv-" + str(uuid.uuid4())
    total = sum(float(x["contribution_amount"] or 0) for x in prows)
    camps = sorted({x["recipient"] for x in prows})
    dates = sorted(x["contribution_date"] for x in prows if x["contribution_date"])
    emp_occ = " ".join(sorted(set((BI.normalize_employer(sample["donor_reported_employer"]) + " " +
                                   BI.normalize_occupation(sample["donor_reported_occupation"])).split())))
    cur.execute("""INSERT INTO donor_identities
        (donor_id, canonical_name, canonical_zip, canonical_employer, total_donated,
         campaign_count, campaigns, record_count, first_seen, last_seen, fec_matched)
        VALUES (?,?,?,?,?,?,?,?,?,?,0)""",
        (did, sample["donor"].strip(), BI.normalize_zip(sample["city_state_zip"]), emp_occ,
         total, len(camps), "|".join(camps), len(prows),
         dates[0] if dates else None, dates[-1] if dates else None))
    return did

def recompute_identity(donor_id):
    agg = cur.execute("""SELECT SUM(CAST(contribution_amount AS REAL)), COUNT(*),
                         MIN(contribution_date), MAX(contribution_date)
                         FROM campaign_finance WHERE donor_id=? OR donor_id_2=?""",
                      (donor_id, donor_id)).fetchone()
    camps = sorted({r[0] for r in cur.execute(
        "SELECT DISTINCT recipient FROM campaign_finance WHERE donor_id=? OR donor_id_2=?",
        (donor_id, donor_id))})
    cur.execute("""UPDATE donor_identities SET total_donated=?, record_count=?,
        campaign_count=?, campaigns=?, first_seen=?, last_seen=? WHERE donor_id=?""",
        (agg[0] or 0, agg[1], len(camps), "|".join(camps), agg[2], agg[3], donor_id))

# ---- group person rows ----------------------------------------------------
person_rows = defaultdict(list)
joint_rows, entity_rows = [], []
for nr in new_rows:
    kind = classify_donor((nr["donor"] or "").strip(), nr["donor_type"])
    if kind == "INDIVIDUAL":
        last, first = BI.normalize_name(nr["donor"])
        person_rows[(last, first, BI.normalize_zip(nr["city_state_zip"]))].append(nr)
    elif kind == "JOINT":
        joint_rows.append(nr)
    else:
        entity_rows.append(nr)

matched = created = 0
matched_ids = set()
for (last, first, zip5), prows in person_rows.items():
    sample = prows[0]
    did, conf, is_new, key = resolve_person(sample["donor"], sample["city_state_zip"],
                                            sample["donor_reported_employer"],
                                            sample["donor_reported_occupation"])
    if is_new:
        did = mint_identity(sample, prows)
        conf = "city26-new"
        created += 1
        by_last[last].append({"donor_id": did, "last": last, "first": first,
                              "name": sample["donor"], "zip5": zip5, "emp_occ": ""})
    else:
        matched += 1
        matched_ids.add(did)
    cur.executemany("UPDATE campaign_finance SET donor_id=?, match_confidence=? WHERE rowid=?",
                    [(did, conf, x["rowid"]) for x in prows])

joint_n = 0
for nr in joint_rows:
    m = re.match(r"^\s*([^,]+),\s*(.+)$", nr["donor"] or "")
    if not m:
        continue
    last_raw, firsts = m.group(1), JOINT_SEP.split(m.group(2))
    ids = []
    for f in firsts[:2]:
        nm = f"{last_raw}, {f.strip()}"
        did, conf, is_new, _ = resolve_person(nm, nr["city_state_zip"],
                                              nr["donor_reported_employer"],
                                              nr["donor_reported_occupation"])
        if is_new:
            did = mint_identity({**{k: nr[k] for k in nr.keys()}, "donor": nm}, [nr])
        ids.append(did)
    cur.execute("""UPDATE campaign_finance SET donor_id=?, donor_id_2=?, is_joint=1,
                   balanced_amount=?, match_confidence='city26-joint' WHERE rowid=?""",
                (ids[0], ids[1] if len(ids) > 1 else None,
                 float(nr["contribution_amount"] or 0) / 2, nr["rowid"]))
    matched_ids.update(i for i in ids if i and not str(i).startswith("tcv-"))
    joint_n += 1

for did in matched_ids:
    recompute_identity(did)
print(f"individuals: {matched} matched, {created} new; joint: {joint_n}; entities: {len(entity_rows)}")

# ---- employers -------------------------------------------------------------
emps = cur.execute("SELECT employer_id, canonical_name, name_variants FROM employer_identities").fetchall()
variant_map = {}
by_token = defaultdict(list)
for e in emps:
    for v in set((e["name_variants"] or "").split("|")) | {e["canonical_name"] or ""}:
        nv = BE.normalize_employer(v)
        if nv:
            variant_map.setdefault(nv, e["employer_id"])
            by_token[nv.split()[0]].append((nv, e["employer_id"]))

def resolve_employer(raw):
    n = BE.normalize_employer(raw)
    if not n:
        return None, None
    if n in variant_map:
        return variant_map[n], "exact"
    best, best_s = None, 0.0
    for nv, eid in by_token.get(n.split()[0], []):
        s = BE.score_employers(n, nv)
        if s > best_s:
            best, best_s = eid, s
    if best and best_s >= EMP_AUTO:
        return best, f"city26-fuzzy-{best_s:.2f}"
    eid = "tcv-" + str(uuid.uuid4())
    cur.execute("""INSERT INTO employer_identities (employer_id, canonical_name, name_variants,
                   record_count, total_individual_donated, total_entity_donated) VALUES (?,?,?,0,0,0)""",
                (raw.strip(), ) if False else (eid, raw.strip(), raw.strip()))
    variant_map[n] = eid
    by_token[n.split()[0]].append((n, eid))
    return eid, "city26-new"

e_exact = e_fuzzy = e_new = 0
for nr in new_rows:
    kind = classify_donor((nr["donor"] or "").strip(), nr["donor_type"])
    raw = nr["donor"] if kind == "ENTITY" else nr["donor_reported_employer"]
    eid, conf = resolve_employer(raw or "")
    if not eid:
        continue
    cur.execute("UPDATE campaign_finance SET employer_id=?, employer_match_confidence=? WHERE rowid=?",
                (eid, conf, nr["rowid"]))
    if conf == "exact": e_exact += 1
    elif conf == "city26-new": e_new += 1
    else: e_fuzzy += 1
print(f"employer stamps: {e_exact} exact, {e_fuzzy} fuzzy, {e_new} new")

if args.dry_run:
    conn.rollback(); print("DRY RUN — rolled back")
else:
    conn.commit()
    n = cur.execute("""SELECT COUNT(*) FROM donor_identities
                       WHERE fec_matched=0 OR fec_matched IS NULL""").fetchone()[0]
    print(f"donors awaiting FEC (incl. backlog): {n}")
