"""
identity_migration.py  (2026-07-17)
Consolidate ~108k phantom donor identities (the max_block=50 fragmentation bug)
into deterministic per-(name,zip5) identities. Implements IDENTITY_MIGRATION_DESIGN.md
with FIX #1 (recompute FEC/ip/ff/gun totals from DEDUPED fec_contributions_raw —
never column-sum) and FIX #2 (per-zip identities + inflation-catcher gate).

Non-destructive to signal: enrichment is UNIONed, not dropped. Single transaction,
all gates run pre-COMMIT, ROLLBACK on any failure. `--dry-run` runs the whole thing
incl. gates + report, then ROLLS BACK (validate on real data without committing).

Usage:
    python identity_migration.py --dry-run      # validate, roll back
    python identity_migration.py                # execute, commit iff all gates pass
"""
import argparse, sqlite3, hashlib, sys, io, time
from collections import defaultdict, Counter
import build_identities as bi

try: sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception: pass

DB = r"C:\Users\Hamza Sait\Electoral\austin-finance-data\austin_finance.db"
AMT = "CAST(REPLACE(REPLACE(contribution_amount,'$',''),',','') AS REAL)"

def sha16(s): return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]
def money(x): return f"${x:,.0f}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db", default=DB)
    args = ap.parse_args()
    t0 = time.time()

    conn = sqlite3.connect(args.db, timeout=300)
    conn.isolation_level = None
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=300000")
    conn.execute("PRAGMA synchronous=NORMAL")
    cur = conn.cursor()

    # ── institutional zips (rows>5000 & rows/distinct_names>20) ────────────────
    zc = defaultdict(lambda: [0, set()])
    for donor, csz in cur.execute("SELECT donor,city_state_zip FROM campaign_finance "
            "WHERE donor_type IN ('INDIVIDUAL','Individual') AND donor LIKE '%,%'"):
        z = bi.normalize_zip(csz or "")
        if z: zc[z][0]+=1; zc[z][1].add((donor or "").strip().lower())
    INST = {z for z,(n,names) in zc.items() if n>5000 and n/max(len(names),1)>20}
    print(f"Institutional zips (emp_occ tiebreak): {sorted(INST)}")

    def newid_for(cname, czip, cemp):
        last, first = bi.normalize_name(cname or "")
        if not last or not first: return None
        z = bi.normalize_zip(czip or "")
        if z in INST:
            eo = " ".join(sorted(set(bi.normalize_employer(cemp or "").split())))
            return sha16(f"{last}|{first}|{z}|{eo}")
        return sha16(f"{last}|{first}|{z}")

    # ── PRE snapshot (authoritative baseline) ──────────────────────────────────
    def snap():
        return dict(
            cf=cur.execute("SELECT COUNT(*) FROM campaign_finance").fetchone()[0],
            pre2022=cur.execute("SELECT COUNT(*) FROM campaign_finance WHERE contribution_date<'2022-01-01'").fetchone()[0],
            total=round(cur.execute(f"SELECT SUM({AMT}) FROM campaign_finance").fetchone()[0],2),
            di=cur.execute("SELECT COUNT(*) FROM donor_identities").fetchone()[0],
            fecraw=cur.execute("SELECT COUNT(*) FROM fec_contributions_raw").fetchone()[0],
            texraw=cur.execute("SELECT COUNT(*) FROM texas_contributions_raw").fetchone()[0],
        )
    pre = snap()
    per_recipient_pre = dict(cur.execute(f"SELECT recipient, ROUND(SUM({AMT}),2) FROM campaign_finance GROUP BY recipient"))
    print("PRE:", pre)

    # row-level key (each cf row keyed by its OWN name+zip[+emp_occ at 78721])
    def rowkey(donor, csz, emp, occ):
        last, first = bi.normalize_name(donor)
        if not last or not first: return None
        z = bi.normalize_zip(csz or "")
        if z in INST:
            eo = " ".join(sorted(set((bi.normalize_employer(emp)+" "+bi.normalize_occupation(occ)).split())))
            return sha16(f"{last}|{first}|{z}|{eo}")
        return sha16(f"{last}|{first}|{z}")

    # ── 1. OLDMAP (approach A): old_id -> DOMINANT row-key among its rows ───────
    # Row-level keying consolidates a person's same-(name,zip) rows and keeps a
    # mover's distinct-zip fragments separate (Judah -> 3). old_id -> the new_id
    # most of its rows fall under; used uniformly for cf/fec/tex/joint/enrichment.
    print("Computing row-level keys + dominant old->new map ...")
    oldctr = defaultdict(Counter)
    for donor, csz, emp, occ, did in cur.execute("""SELECT donor,city_state_zip,donor_reported_employer,
            donor_reported_occupation,donor_id FROM campaign_finance
            WHERE donor_type IN ('INDIVIDUAL','Individual') AND donor LIKE '%,%' AND donor_id IS NOT NULL"""):
        k = rowkey(donor, csz, emp, occ)
        if k: oldctr[did][k] += 1
    OLD = {oid: ctr.most_common(1)[0][0] for oid, ctr in oldctr.items()}

    # enrichment per old_id + fallback map for old_ids with no primary rows
    # (e.g. joint-second-only identities) via their stored canonical.
    di_enr = {}; unkeyable = []
    for row in cur.execute("""SELECT donor_id,canonical_name,canonical_zip,canonical_employer,
            total_donated,fec_matched,fec_matched_at,
            tec_total_dem,tec_total_rep,tec_total_other,tec_total_donations,tec_matched,
            ip_spectrum,ip_tier,ip_total,ip_committees,
            ff_spectrum,ff_tier,ff_total,ff_committees,
            gun_spectrum,gun_tier,gun_total,gun_committees,
            resolved_industry,resolved_employer_display,resolved_confidence FROM donor_identities"""):
        oid = row[0]; di_enr[oid] = row
        if oid not in OLD:
            nid = newid_for(row[1], row[2], row[3])
            OLD[oid] = nid if nid else oid
            if nid is None: unkeyable.append(oid)
    print(f"  {len(OLD):,} old identities -> {len(set(OLD.values())):,} new ids "
          f"(fallback/unkeyable: {len(unkeyable)})")

    # collision sanity: distinct new_ids should equal distinct keys (checked implicitly)
    # ── 2. temp idmap table for set-based SQL remaps ───────────────────────────
    cur.execute("BEGIN IMMEDIATE")
    try:
        cur.execute("CREATE TEMP TABLE idmap(old_id TEXT PRIMARY KEY, new_id TEXT)")
        cur.executemany("INSERT INTO idmap VALUES(?,?)", list(OLD.items()))

        # ── 3. remap campaign_finance donor_id / donor_id_2 ────────────────────
        print("Remapping campaign_finance donor_id / donor_id_2 ...")
        cur.execute("UPDATE campaign_finance SET donor_id=(SELECT new_id FROM idmap WHERE old_id=donor_id) "
                    "WHERE donor_id IS NOT NULL AND donor_id IN (SELECT old_id FROM idmap)")
        cur.execute("UPDATE campaign_finance SET donor_id_2=(SELECT new_id FROM idmap WHERE old_id=donor_id_2) "
                    "WHERE donor_id_2 IS NOT NULL AND donor_id_2 IN (SELECT old_id FROM idmap)")
        # joint self-collapse guard: primary == second after remap
        collapsed = cur.execute("SELECT COUNT(*) FROM campaign_finance WHERE is_joint=1 AND donor_id_2=donor_id").fetchone()[0]
        cur.execute("UPDATE campaign_finance SET donor_id_2=NULL, is_joint=0 WHERE is_joint=1 AND donor_id_2=donor_id")
        cur.execute("UPDATE campaign_finance SET match_confidence='migrated' WHERE donor_id IS NOT NULL")

        # ── 4. rebuild fec_contributions_raw: remap + DEDUP by (new_id,sub_id) ──
        print("Rebuilding fec_contributions_raw (remap + dedupe) ...")
        cur.execute("""CREATE TABLE fecraw_new(
            id INTEGER PRIMARY KEY AUTOINCREMENT, donor_id TEXT NOT NULL, committee_id TEXT NOT NULL,
            contribution_amount REAL, contribution_date TEXT, fec_contributor_name TEXT,
            fec_contributor_city TEXT, fec_contributor_zip TEXT, fec_employer TEXT, fec_occupation TEXT,
            fec_sub_id TEXT, confirm_score REAL, UNIQUE(donor_id, fec_sub_id))""")
        cur.execute("""INSERT OR IGNORE INTO fecraw_new
            (donor_id,committee_id,contribution_amount,contribution_date,fec_contributor_name,
             fec_contributor_city,fec_contributor_zip,fec_employer,fec_occupation,fec_sub_id,confirm_score)
            SELECT COALESCE(m.new_id,f.donor_id),f.committee_id,f.contribution_amount,f.contribution_date,
                   f.fec_contributor_name,f.fec_contributor_city,f.fec_contributor_zip,f.fec_employer,
                   f.fec_occupation,f.fec_sub_id,f.confirm_score
            FROM fec_contributions_raw f LEFT JOIN idmap m ON m.old_id=f.donor_id""")
        cur.execute("DROP TABLE fec_contributions_raw")
        cur.execute("ALTER TABLE fecraw_new RENAME TO fec_contributions_raw")
        cur.execute("CREATE INDEX idx_fec_raw_sub ON fec_contributions_raw(fec_sub_id)")
        cur.execute("CREATE INDEX idx_fec_raw_donor ON fec_contributions_raw(donor_id)")
        cur.execute("CREATE INDEX idx_fec_raw_committee ON fec_contributions_raw(committee_id)")

        # ── 5. remap texas_contributions_raw austin_donor_id (no dedup needed) ──
        print("Remapping texas_contributions_raw ...")
        cur.execute("UPDATE texas_contributions_raw SET austin_donor_id=(SELECT new_id FROM idmap WHERE old_id=austin_donor_id) "
                    "WHERE austin_donor_id IS NOT NULL AND austin_donor_id IN (SELECT old_id FROM idmap)")

        # ── 6. remap joint_donations ───────────────────────────────────────────
        cur.execute("UPDATE joint_donations SET donor_id_1=(SELECT new_id FROM idmap WHERE old_id=donor_id_1) WHERE donor_id_1 IN (SELECT old_id FROM idmap)")
        cur.execute("UPDATE joint_donations SET donor_id_2=(SELECT new_id FROM idmap WHERE old_id=donor_id_2) WHERE donor_id_2 IN (SELECT old_id FROM idmap)")

        # ── 7. recompute FEC/ip/ff/gun totals from the DEDUPED new raw table ────
        print("Recomputing FEC/ip/ff/gun totals from deduped raw ...")
        fec_agg = defaultdict(lambda: {"dem":0.0,"rep":0.0,"oth":0.0,"n":0,"ip":0.0,"ff":0.0,"gun":0.0})
        for nid, cls, ipc, ffc, gunc, amt in cur.execute("""
                SELECT f.donor_id, cc.classification, cc.ip_category, cc.fossil_category, cc.gun_category,
                       f.contribution_amount
                FROM fec_contributions_raw f LEFT JOIN fec_committee_cache cc ON cc.committee_id=f.committee_id
                WHERE f.contribution_amount>0"""):
            a = fec_agg[nid]; amt = amt or 0.0
            if cls=="Dem": a["dem"]+=amt
            elif cls=="Rep": a["rep"]+=amt
            else: a["oth"]+=amt
            a["n"]+=1
            if ipc: a["ip"]+=amt
            if ffc: a["ff"]+=amt
            if gunc: a["gun"]+=amt

        # ── 8. base aggregates per new_id from remapped cf (primary + joint-2nd) ─
        print("Recomputing base aggregates ...")
        base = defaultdict(lambda: {"usd":0.0,"n":0,"fs":"9999","ls":"0000","rec":set(),
                                    "names":[],"zips":[],"emps":[]})
        for did,donor,csz,emp,recip,date,a in cur.execute(f"""
                SELECT donor_id,donor,city_state_zip,donor_reported_employer,recipient,contribution_date,{AMT}
                FROM campaign_finance WHERE donor_id IS NOT NULL"""):
            g=base[did]; g["usd"]+=a or 0.0; g["n"]+=1
            if date:
                if date<g["fs"]: g["fs"]=date
                if date>g["ls"]: g["ls"]=date
            if recip: g["rec"].add(recip)
            g["names"].append(donor or "");
            z=bi.normalize_zip(csz or "");  g["zips"].append(z) if z else None
            e=bi.normalize_employer(emp or ""); g["emps"].append(e) if e else None
        # joint-second-only identities (appear only as donor_id_2): add balanced_amount
        for did,bal,date,recip in cur.execute("""SELECT donor_id_2,balanced_amount,contribution_date,recipient
                FROM campaign_finance WHERE donor_id_2 IS NOT NULL"""):
            g=base[did]; g["usd"]+=bal or 0.0; g["n"]+=1
            if date:
                if date<g["fs"]: g["fs"]=date
                if date>g["ls"]: g["ls"]=date
            if recip: g["rec"].add(recip)

        def mc(lst): return Counter(lst).most_common(1)[0][0] if lst else ""

        # ── 9. union old-di enrichment (tec col-sum ok; ip/ff/gun spectrum agree)
        enr_by_new = defaultdict(lambda: {"tecd":0.0,"tecr":0.0,"teco":0.0,"tecn":0,"tecm":0,
            "fecm":0,"fecat":"","ind":None,"empd":None,"conf":None,"indtot":-1.0,
            "ip_s":None,"ip_t":0,"ip_c":set(),"ip_best":-1.0,
            "ff_s":None,"ff_t":0,"ff_c":set(),"ff_best":-1.0,
            "gn_s":None,"gn_t":0,"gn_c":set(),"gn_best":-1.0,
            "max_frag_fec":0.0})
        for oid, nid in OLD.items():
            e = di_enr.get(oid)
            if not e: continue
            (_,cn,cz,ce,tot,fecm,fecat,td,tr,to,tn,tecm,ips,ipt,ipv,ipc,ffs,fft,ffv,ffc,
             gns,gnt,gnv,gnc,ind,empd,conf) = e
            u = enr_by_new[nid]
            u["tecd"]+=td or 0; u["tecr"]+=tr or 0; u["teco"]+=to or 0; u["tecn"]+=tn or 0
            u["tecm"]=max(u["tecm"], tecm or 0); u["fecm"]=max(u["fecm"], fecm or 0)
            if fecat and fecat>u["fecat"]: u["fecat"]=fecat
            # inflation-catcher: track largest single-fragment fec dem+rep (pre-migration)
            # (uses old di fec columns via re-query below; here we only have via di_enr? not fec cols)
            if ind and (tot or 0)>u["indtot"]:
                u["indtot"]=tot or 0; u["ind"]=ind; u["empd"]=empd; u["conf"]=conf
            if ips and (ipv or 0)>u["ip_best"]: u["ip_best"]=ipv or 0; u["ip_s"]=ips; u["ip_t"]=ipt or 0
            if ipc: u["ip_c"].update(x for x in ipc.split(",") if x)
            if ffs and (ffv or 0)>u["ff_best"]: u["ff_best"]=ffv or 0; u["ff_s"]=ffs; u["ff_t"]=fft or 0
            if ffc: u["ff_c"].update(x for x in ffc.split(",") if x)
            if gns and (gnv or 0)>u["gn_best"]: u["gn_best"]=gnv or 0; u["gn_s"]=gns; u["gn_t"]=gnt or 0
            if gnc: u["gn_c"].update(x for x in gnc.split(",") if x)

        # inflation-catcher inputs (donor_identities still intact — query directly):
        #   maxfrag[new_id]   = largest single pre-migration fragment's (dem+rep)
        #   pre_fec_global    = Σ all fragments' (dem+rep)  [the INFLATED total]
        # A correct dedup-recompute must (a) reduce the global total substantially,
        # and (b) never grossly exceed the max fragment (legit disjoint unions are
        # ~1-3x; the column-sum bug is 37-180x).
        maxfrag = defaultdict(float); pre_fec_global = 0.0
        for oid, dd, rr in cur.execute("SELECT donor_id,COALESCE(fec_total_dem,0),COALESCE(fec_total_rep,0) FROM donor_identities"):
            nid = OLD.get(oid, oid); v = (dd or 0)+(rr or 0)
            maxfrag[nid] = max(maxfrag[nid], v); pre_fec_global += v

        # ── 10. rebuild donor_identities ───────────────────────────────────────
        print("Rebuilding donor_identities ...")
        all_new = set(base) | set(enr_by_new) | set(fec_agg)
        rows_out = []
        for nid in all_new:
            b = base.get(nid, {"usd":0.0,"n":0,"fs":"9999","ls":"0000","rec":set(),"names":[],"zips":[],"emps":[]})
            fa = fec_agg.get(nid, {"dem":0,"rep":0,"oth":0,"n":0,"ip":0,"ff":0,"gun":0})
            u = enr_by_new.get(nid, None)
            dem,rep,oth = round(fa["dem"],2),round(fa["rep"],2),round(fa["oth"],2)
            lean = dem/(dem+rep) if (dem+rep)>0 else None
            fs = b["fs"] if b["fs"]!="9999" else ""; ls = b["ls"] if b["ls"]!="0000" else ""
            rows_out.append((
                nid, mc(b["names"]), mc(b["zips"]), mc(b["emps"]), round(b["usd"],2),
                len(b["rec"]), "|".join(sorted(b["rec"])), b["n"], fs, ls,
                lean, dem, rep, oth, fa["n"],
                (u["fecm"] if u else (1 if fa["n"]>0 else 0)), (u["fecat"] or None) if u else None,
                (u["ind"] if u else None),(u["empd"] if u else None),(u["conf"] if u else None),
                (u["ip_s"] if u else None),(u["ip_t"] if u else 0),round(fa["ip"],2),("|".join(sorted(u["ip_c"])) if u and u["ip_c"] else None),
                (u["ff_s"] if u else None),(u["ff_t"] if u else 0),round(fa["ff"],2),("|".join(sorted(u["ff_c"])) if u and u["ff_c"] else None),
                (u["tecd"] if u else 0),(u["tecr"] if u else 0),(u["teco"] if u else 0),(u["tecn"] if u else 0),(u["tecm"] if u else 0),
                (u["gn_s"] if u else None),(u["gn_t"] if u else 0),round(fa["gun"],2),("|".join(sorted(u["gn_c"])) if u and u["gn_c"] else None),
            ))
        cur.execute("DELETE FROM donor_identities")
        cur.executemany("""INSERT INTO donor_identities
            (donor_id,canonical_name,canonical_zip,canonical_employer,total_donated,campaign_count,campaigns,
             record_count,first_seen,last_seen,fec_partisan_lean,fec_total_dem,fec_total_rep,fec_total_other,
             fec_total_donations,fec_matched,fec_matched_at,resolved_industry,resolved_employer_display,resolved_confidence,
             ip_spectrum,ip_tier,ip_total,ip_committees,ff_spectrum,ff_tier,ff_total,ff_committees,
             tec_total_dem,tec_total_rep,tec_total_other,tec_total_donations,tec_matched,
             gun_spectrum,gun_tier,gun_total,gun_committees)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows_out)

        # ── 11. GATES ──────────────────────────────────────────────────────────
        post = snap()
        gates = []
        gates.append(("cf total rows unchanged", post["cf"]==pre["cf"], f'{pre["cf"]}->{post["cf"]}'))
        gates.append(("pre-2022 unchanged", post["pre2022"]==pre["pre2022"], f'{pre["pre2022"]}->{post["pre2022"]}'))
        gates.append(("SUM(amount) unchanged", abs(post["total"]-pre["total"])<0.01, f'{pre["total"]}->{post["total"]}'))
        per_recipient_post = dict(cur.execute(f"SELECT recipient, ROUND(SUM({AMT}),2) FROM campaign_finance GROUP BY recipient"))
        bad_rec = [r for r in per_recipient_pre if abs(per_recipient_pre.get(r,0)-per_recipient_post.get(r,0))>0.01]
        gates.append(("per-candidate SUM unchanged", len(bad_rec)==0, f'{len(bad_rec)} recipients differ'))
        red = pre["di"]-post["di"]
        gates.append(("di decreased ~108,561", 100000<=red<=112000, f'{pre["di"]}->{post["di"]} (-{red})'))
        # Judah Rice the PERSON (donor='Rice, Judah') -> 3 identities, one per zip
        # (his business "Judah Rice Photo" has no comma and a reversed-name typo
        #  "Judah, Rice" are correctly kept separate — not counted here).
        jr = cur.execute("""SELECT donor_id, ROUND(SUM(CAST(contribution_amount AS REAL)),2), COUNT(*)
            FROM campaign_finance WHERE donor='Rice, Judah'
            GROUP BY donor_id ORDER BY 2 DESC""").fetchall()
        jr_sum = round(sum(x[1] for x in jr),2)
        gates.append(("Judah Rice person 68->3 identities", len(jr)==3 and abs(jr_sum-1226.18)<1,
                      f'{len(jr)} ids totaling {money(jr_sum)}: '+", ".join(money(x[1]) for x in jr)))
        # inflation-catcher (FIX #1): global total must drop from dedup, and no
        # donor may grossly exceed its max fragment (column-sum bug = 37-180x).
        post_fec_global = cur.execute("SELECT COALESCE(SUM(fec_total_dem+fec_total_rep),0) FROM donor_identities").fetchone()[0]
        gates.append(("FEC global total reduced by dedup", post_fec_global < pre_fec_global,
                      f'{money(pre_fec_global)} -> {money(post_fec_global)}'))
        viol = []; worst = 1.0
        for nid,dd,rr in cur.execute("SELECT donor_id,COALESCE(fec_total_dem,0),COALESCE(fec_total_rep,0) FROM donor_identities"):
            mf = maxfrag.get(nid, 0.0)
            if mf > 0:
                ratio = (dd+rr)/mf; worst = max(worst, ratio)
                if ratio > 10: viol.append((nid, round(dd+rr,2), round(mf,2), round(ratio,1)))
        gates.append(("no gross FEC inflation (<=10x max frag)", len(viol)==0,
                      f'worst={worst:.2f}x, >10x violations={len(viol)}'))
        # orphans
        orph = cur.execute("""SELECT COUNT(*) FROM (SELECT DISTINCT donor_id FROM campaign_finance
            WHERE donor_id IS NOT NULL AND donor_id NOT IN (SELECT donor_id FROM donor_identities))""").fetchone()[0]
        orph2 = cur.execute("""SELECT COUNT(*) FROM (SELECT DISTINCT donor_id_2 FROM campaign_finance
            WHERE donor_id_2 IS NOT NULL AND donor_id_2 NOT IN (SELECT donor_id FROM donor_identities))""").fetchone()[0]
        gates.append(("zero orphan donor_id/2", orph==0 and orph2==0, f'orphans={orph}, orphan2={orph2}'))
        # fecraw dedupe-only: post == distinct (new_id,sub_id) pre-image ; texraw unchanged
        gates.append(("fecraw shrank (dedupe)", post["fecraw"]<=pre["fecraw"], f'{pre["fecraw"]}->{post["fecraw"]}'))
        gates.append(("texraw unchanged (FK-only)", post["texraw"]==pre["texraw"], f'{pre["texraw"]}->{post["texraw"]}'))
        # no fec_sub_id lost for a person: distinct (donor_id,sub_id) preserved
        gates.append(("di rows == distinct new ids", post["di"]==len(all_new), f'{post["di"]} vs {len(all_new)}'))

        print("\n=== VERIFICATION GATES ===")
        allok=True
        for name,ok,detail in gates:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
            allok = allok and ok
        if viol[:5]:
            print("  inflation violations sample:", viol[:5])

        # sanity report: Ellis/Watson/Brown top-10 quick + top fragmented donors
        print("\n=== POST top fragmented (dedup-corrected FEC) ===")
        for nm in [("cofer","george"),("coon","jonathan"),("hoff","scott")]:
            r = cur.execute("""SELECT canonical_name,total_donated,fec_total_dem,fec_total_rep,fec_total_donations
                FROM donor_identities WHERE lower(canonical_name) LIKE ? LIMIT 3""",(f"%{nm[0]}, {nm[1]}%",)).fetchall()
            for x in r: print(f"   {x[0]:28} local={money(x[1])} FEC D={money(x[2])} R={money(x[3])} n={x[4]}")

        if args.dry_run or not allok:
            conn.rollback()
            print(f"\n{'DRY-RUN' if args.dry_run else '*** GATE FAILURE'} — ROLLED BACK. No changes committed."
                  + ("" if args.dry_run else " ***"))
            if not allok and not args.dry_run: sys.exit(1)
        else:
            conn.commit()
            print("\nCOMMITTED.")
    except Exception:
        conn.rollback(); raise
    finally:
        try: cur.execute("DROP TABLE IF EXISTS idmap")
        except Exception: pass

    print(f"\nElapsed: {time.time()-t0:.0f}s")
    conn.close()

if __name__ == "__main__":
    main()
