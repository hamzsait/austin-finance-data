"""Ingest Travis County contributions into campaign_finance + INCREMENTAL
identity resolution against the existing donor/employer identity tables.

Why incremental: build_identities.py / build_employer_identities.py are
full-rebuild scripts — running them would drop donor_identities (losing all
FEC/TEC/IP/FF enrichment + manual verdicts) and remint every donor_id,
orphaning fec_contributions_raw. This script instead reuses their exact
normalization + scoring logic to match new rows against EXISTING identities:
  match score >= 0.83  -> reuse existing donor_id (same threshold as builder)
  0.65 <= score < 0.83 -> review_queue entry, new identity minted
  else                 -> new identity (fec_matched=0 so fec_enrich picks it up)

Idempotent: deletes/reinserts all TRAVIS-% rows and any identities it minted
(match_confidence LIKE 'travis-%') on each run.

Usage: python travis_ingest.py [--dry-run]
"""
import csv, json, re, sqlite3, sys, uuid
from collections import defaultdict

import build_identities as BI            # normalize_name/zip, score_pair, NICKNAMES
import build_employer_identities as BE   # normalize_employer, score_employers
from build_joint_donors import ENTITY_KEYWORDS, JOINT_SEP

DB = "austin_finance.db"
CSV_PATH = r"travis_county_filings\extracted\travis_contributions.csv"
PORTAL = "https://traviscountytx.easyvotecampaignfinance.com/home/publicfilings"
DRY = "--dry-run" in sys.argv

AUTO, REVIEW_LOW = 0.83, 0.65
EMP_AUTO = 0.85

def classify_donor(name):
    """-> 'ENTITY' | 'INDIVIDUAL' | 'JOINT'"""
    if not name:
        return "ENTITY"
    if ENTITY_KEYWORDS.search(name):
        return "ENTITY"
    # "Last, First & First2" or "Last, First and First2"
    if "," in name and re.search(r"(&|\band\b|/)", name.split(",", 1)[1], re.I):
        return "JOINT"
    if "," in name:
        return "INDIVIDUAL"
    # no comma, no entity keyword: 2-4 tokens looks like "First Last"
    toks = name.split()
    if 2 <= len(toks) <= 4 and not re.search(r"\d", name):
        return "INDIVIDUAL"
    return "ENTITY"

def contribution_type(row):
    if row["contribution_type"] == "in-kind":
        return "Non-Monetary (In-Kind) Political Contribution"
    return "Monetary Political Contribution"

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    print(f"CSV rows: {len(rows)}")

    # ---------- Phase A: wipe prior travis ingest (idempotent) ----------
    prior_ids = [r[0] for r in cur.execute(
        "SELECT donor_id FROM donor_identities WHERE match_confidence LIKE 'travis-%'")] \
        if cur.execute("SELECT 1 FROM pragma_table_info('donor_identities') WHERE name='match_confidence'").fetchone() else []
    cur.execute("DELETE FROM campaign_finance WHERE transaction_id LIKE 'TRAVIS-%'")
    print(f"removed prior travis rows: {cur.rowcount}")
    # identities minted by a previous run of THIS script are tagged in campaigns
    cur.execute("DELETE FROM donor_identities WHERE donor_id LIKE 'tcv-%'")
    print(f"removed prior travis identities: {cur.rowcount}")
    cur.execute("DELETE FROM employer_identities WHERE employer_id LIKE 'tcv-%'")
    print(f"removed prior travis employer identities: {cur.rowcount}")
    cur.execute("DELETE FROM review_queue WHERE resolved = 'travis-pending'")

    # ---------- Phase B: insert campaign_finance rows ----------
    inserts = []
    seq = defaultdict(int)
    for r in rows:
        if not r["donor"].strip():
            continue  # 1-2 unreadable-name rows stay in the PDF review queue
        kind = classify_donor(r["donor"].strip())
        key = f"{r['official_slug']}-{r['report_file'][:-4]}-p{r['page']}"
        seq[key] += 1
        txid = f"TRAVIS-{key}-{seq[key]:02d}"
        inserts.append({
            "donor": r["donor"].strip(),
            "recipient": r["recipient"],
            "contribution_amount": r["contribution_amount"],
            "contribution_date": r["contribution_date"],
            "donor_type": "ENTITY" if kind == "ENTITY" else "INDIVIDUAL",
            "_kind": kind,
            "city_state_zip": r["city_state_zip"] or "",
            "contribution_year": (r["contribution_date"] or "")[:4],
            "contribution_type": contribution_type(r),
            "date_reported": r["date_submitted"] or "",
            "report_filed": f"Travis County C/OH: {r['report_file']}",
            "view_report": json.dumps({"url": PORTAL, "description": "View Report"}),
            "transaction_id": txid,
            "donor_reported_occupation": r["donor_occupation"] or "",
            "donor_reported_employer": r["donor_employer"] or "",
            "in_kind_description": r["in_kind_description"] or "",
            "out_of_state_pac": "true" if r["out_of_state_pac"] == "True" else "",
            "correction": "uncertain-extraction" if r["uncertain"] == "True" else "",
        })
    cols = [c for c in inserts[0] if not c.startswith("_")]
    cur.executemany(
        f"INSERT INTO campaign_finance ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
        [tuple(i[c] for c in cols) for i in inserts])
    print(f"inserted rows: {len(inserts)}")

    # map txid -> rowid + kind
    txkind = {i["transaction_id"]: i["_kind"] for i in inserts}
    new_rows = cur.execute(
        "SELECT rowid, * FROM campaign_finance WHERE transaction_id LIKE 'TRAVIS-%'").fetchall()

    # ---------- Phase C: donor identity resolution (individuals) ----------
    # index existing identities by normalized last name
    existing = cur.execute(
        "SELECT donor_id, canonical_name, canonical_zip, canonical_employer FROM donor_identities").fetchall()
    by_last = defaultdict(list)
    for e in existing:
        last, first = BI.normalize_name(e["canonical_name"] or "")
        if not last:
            continue
        by_last[last].append({
            "donor_id": e["donor_id"], "last": last, "first": first,
            "name": e["canonical_name"],
            "zip5": (e["canonical_zip"] or "")[:5] if re.match(r"^\d{5}", e["canonical_zip"] or "") else "",
            "emp_occ": (e["canonical_employer"] or "").lower(),
        })

    def resolve_person(raw_name, csz, emp, occ):
        """-> (donor_id, confidence, is_new) using builder scoring vs existing."""
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
            return best["donor_id"], f"travis-match-{best_s:.2f}", False
        if best and best_s >= REVIEW_LOW:
            cur.execute("INSERT INTO review_queue (donor_a, donor_b, zip_a, zip_b, emp_occ_a, emp_occ_b, score, resolved) VALUES (?,?,?,?,?,?,?,?)",
                        (raw_name, best["name"], zip5, best["zip5"], emp_occ, best["emp_occ"], best_s, "travis-pending"))
        return None, None, True

    # group new individual rows into persons: (norm last, first, zip5)
    person_rows = defaultdict(list)
    joint_rows = []
    for nr in new_rows:
        kind = txkind[nr["transaction_id"]]
        if kind == "INDIVIDUAL":
            last, first = BI.normalize_name(nr["donor"])
            person_rows[(last, first, BI.normalize_zip(nr["city_state_zip"]))].append(nr)
        elif kind == "JOINT":
            joint_rows.append(nr)

    matched = created = 0
    matched_ids = set()
    def stamp(rowids, donor_id, conf):
        cur.executemany("UPDATE campaign_finance SET donor_id=?, match_confidence=? WHERE rowid=?",
                        [(donor_id, conf, rid) for rid in rowids])

    def mint_identity(sample, rows_for_person):
        did = "tcv-" + str(uuid.uuid4())
        total = sum(float(x["contribution_amount"] or 0) for x in rows_for_person)
        camps = sorted({x["recipient"] for x in rows_for_person})
        dates = sorted(x["contribution_date"] for x in rows_for_person if x["contribution_date"])
        emp_occ = " ".join(sorted(set((BI.normalize_employer(sample["donor_reported_employer"]) + " " +
                                       BI.normalize_occupation(sample["donor_reported_occupation"])).split())))
        cur.execute("""INSERT INTO donor_identities
            (donor_id, canonical_name, canonical_zip, canonical_employer, total_donated,
             campaign_count, campaigns, record_count, first_seen, last_seen, fec_matched)
            VALUES (?,?,?,?,?,?,?,?,?,?,0)""",
            (did, sample["donor"], BI.normalize_zip(sample["city_state_zip"]), emp_occ,
             total, len(camps), "|".join(camps), len(rows_for_person),
             dates[0] if dates else None, dates[-1] if dates else None))
        return did

    def recompute_identity(donor_id):
        """Rebuild aggregates from campaign_finance — idempotent across re-runs."""
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

    for (last, first, zip5), prows in person_rows.items():
        sample = prows[0]
        did, conf, is_new = resolve_person(sample["donor"], sample["city_state_zip"],
                                           sample["donor_reported_employer"], sample["donor_reported_occupation"])
        if is_new:
            did = mint_identity(sample, prows)
            conf = "travis-new"
            created += 1
            # also index it so later travis rows of same person can hit it
            by_last[last].append({"donor_id": did, "last": last, "first": first,
                                  "name": sample["donor"], "zip5": zip5, "emp_occ": ""})
        else:
            matched += 1
            matched_ids.add(did)
        stamp([x["rowid"] for x in prows], did, conf)

    # joint donors: "Last, First & First2"
    joint_matched = 0
    for nr in joint_rows:
        m = re.match(r"^\s*([^,]+),\s*(.+)$", nr["donor"])
        last_raw, firsts = m.group(1), JOINT_SEP.split(m.group(2))
        ids = []
        for f in firsts[:2]:
            nm = f"{last_raw}, {f.strip()}"
            did, conf, is_new = resolve_person(nm, nr["city_state_zip"],
                                               nr["donor_reported_employer"], nr["donor_reported_occupation"])
            if is_new:
                did = mint_identity({**{k: nr[k] for k in nr.keys()}, "donor": nm}, [nr])
            ids.append(did)
        cur.execute("""UPDATE campaign_finance SET donor_id=?, donor_id_2=?, is_joint=1,
                       balanced_amount=?, match_confidence='travis-joint' WHERE rowid=?""",
                    (ids[0], ids[1] if len(ids) > 1 else None,
                     float(nr["contribution_amount"] or 0) / 2, nr["rowid"]))
        matched_ids.update(i for i in ids if i and not i.startswith("tcv-"))
        joint_matched += 1

    for did in matched_ids:
        recompute_identity(did)
    print(f"individuals: {matched} matched to existing identities, {created} new; joint rows: {joint_matched}")

    # ---------- Phase D: employer resolution ----------
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
            return best, f"travis-fuzzy-{best_s:.2f}"
        eid = "tcv-" + str(uuid.uuid4())
        cur.execute("""INSERT INTO employer_identities (employer_id, canonical_name, name_variants,
                       record_count, total_individual_donated, total_entity_donated) VALUES (?,?,?,0,0,0)""",
                    (eid, raw.strip(), raw.strip()))
        variant_map[n] = eid
        by_token[n.split()[0]].append((n, eid))
        return eid, "travis-new"

    e_exact = e_fuzzy = e_new = 0
    for nr in new_rows:
        kind = txkind[nr["transaction_id"]]
        raw = nr["donor"] if kind == "ENTITY" else nr["donor_reported_employer"]
        eid, conf = resolve_employer(raw or "")
        if not eid:
            continue
        cur.execute("UPDATE campaign_finance SET employer_id=?, employer_match_confidence=? WHERE rowid=?",
                    (eid, conf, nr["rowid"]))
        if conf == "exact": e_exact += 1
        elif conf == "travis-new": e_new += 1
        else: e_fuzzy += 1
    print(f"employer stamps: {e_exact} exact, {e_fuzzy} fuzzy, {e_new} new-identity")

    # ---------- summary ----------
    s = cur.execute("""SELECT count(*), sum(cast(contribution_amount as real)),
        count(donor_id), count(employer_id) FROM campaign_finance WHERE transaction_id LIKE 'TRAVIS-%'""").fetchone()
    print(f"TRAVIS rows in db: {s[0]}, ${s[1]:,.2f}; donor_id set on {s[2]}, employer_id on {s[3]}")
    unm = cur.execute("SELECT count(*) FROM donor_identities WHERE fec_matched=0 OR fec_matched IS NULL").fetchone()[0]
    print(f"donor_identities awaiting FEC enrichment: {unm}")

    if DRY:
        print("DRY RUN - rolling back")
        conn.rollback()
    else:
        conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
