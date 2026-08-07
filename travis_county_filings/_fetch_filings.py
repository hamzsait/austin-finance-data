"""Download Travis County campaign finance PDFs from the EasyVote portal.

The portal (https://traviscountytx.easyvotecampaignfinance.com/home/publicfilings)
is an Angular SPA over https://ecf-api.easyvoteapp.com. Anonymous flow:

  1. GET /authentication/getwebsiteuser/traviscountytx  -> UserId, CustomerId
  2. GET /filer/documentsearch/{CustomerId}             -> every filer + documents
  3. GET /documents/{documentid}/viewfinalredactedpdf   -> the PDF
     (/viewfinalpdf is the unredacted version; 401 for anonymous users)

Writes <folder>/<date-submitted>_<document-name>.pdf and merges new entries into
manifest.json. Idempotent: a document already in the manifest with its file on
disk is skipped, so this doubles as the "check for new filings" refresh.

Usage:
    python _fetch_filings.py --list                  # show new docs, download nothing
    python _fetch_filings.py --office commissioner   # judge|commissioner|all
    python _fetch_filings.py --filer "Woody, Susanna"
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest.json")
API = "https://ecf-api.easyvoteapp.com"
SITE = "https://traviscountytx.easyvotecampaignfinance.com"
CUSTOMER_SLUG = "traviscountytx"


def get(url, headers=None, binary=False):
    req = urllib.request.Request(url, headers={
        "Origin": SITE, "Referer": SITE + "/",
        "User-Agent": "Mozilla/5.0 (decode-politics research fetch)",
        **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    return data if binary else json.loads(data)


def auth():
    u = get(f"{API}/authentication/getwebsiteuser/{CUSTOMER_SLUG}")
    hdr = {"Easy-Vote-Authenticated-User":
           f"UserId:{u['UserId']}|CustomerId:{u['CustomerId']}|ZumoToken:null"}
    return u["CustomerId"], hdr


def iso(d):
    """'07/14/26' -> '2026-07-14'"""
    try:
        m, dd, y = d.split("/")
        y = int(y)
        y += 2000 if y < 70 else 1900
        return f"{y:04d}-{int(m):02d}-{int(dd):02d}"
    except Exception:
        return d or "unknown"


def slug_folder(displayname, officename):
    """Match the existing folder convention: pct1_jeff-travillion, county-judge_andy-brown."""
    last, _, first = displayname.partition(",")
    person = re.sub(r"[^a-z0-9]+", "-", f"{first.strip()} {last.strip()}".strip().lower()).strip("-")
    off = officename or ""
    m = re.search(r"Precinct\s*(\d)", off)
    if "Commissioner" in off and m:
        prefix = f"pct{m.group(1)}"
    elif "Judge" in off and "County Judge" in off:
        prefix = "county-judge"
    elif "Constable" in off and m:
        prefix = f"pct{m.group(1)}"
        person += "-constable"
    else:
        prefix = re.sub(r"[^a-z0-9]+", "-", off.lower()).strip("-") or "other"
    return f"{prefix}_{person}"


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", (s or "doc").strip()).strip("-")[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--office", default="commissioner",
                    help="judge | commissioner | all  (substring match on officename)")
    ap.add_argument("--filer", action="append", default=[],
                    help="exact displayname, repeatable; overrides --office")
    ap.add_argument("--list", action="store_true", help="report only, download nothing")
    ap.add_argument("--out", default=ROOT, help="destination root (default: this dir)")
    args = ap.parse_args()

    manifest = json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else []
    have = {r["documentid"].upper() for r in manifest}

    customer, hdr = auth()
    filers = get(f"{API}/filer/documentsearch/{customer}", hdr)
    print(f"portal filers: {len(filers)}")

    def wanted(f):
        off = f.get("officename") or ""
        if args.filer:
            return f["displayname"] in args.filer
        if args.office == "all":
            return True
        if args.office == "judge":
            return off == "County Judge"
        return "Commissioner" in off or off == "County Judge"

    todo = []
    for f in filers:
        if not wanted(f):
            continue
        folder = slug_folder(f["displayname"], f.get("officename"))
        for d in f.get("documents", []):
            if d["documentid"].upper() in have:
                continue
            todo.append({
                "official": f["displayname"], "office": f.get("officename"),
                "folder": folder,
                "file": f"{iso(d['datesubmitted'])}_{safe_name(d['documentname'])}.pdf",
                "documentid": d["documentid"], "documenttype": d.get("documenttype"),
                "documentname": d.get("documentname"),
                "datesubmitted": iso(d["datesubmitted"]),
                "electionname": d.get("electionname"), "status": "pending",
            })

    todo.sort(key=lambda r: (r["folder"], r["datesubmitted"]))
    print(f"new documents: {len(todo)}")
    for r in todo:
        print(f"  {r['folder']:34s} {r['datesubmitted']}  {r['documenttype']:8s} {r['documentname'][:44]}")
    if args.list or not todo:
        return

    added = 0
    for r in todo:
        outdir = os.path.join(args.out, r["folder"])
        os.makedirs(outdir, exist_ok=True)
        dest = os.path.join(outdir, r["file"])
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            r["status"] = "ok"
            manifest.append(r)
            continue
        try:
            pdf = get(f"{API}/documents/{r['documentid']}/viewfinalredactedpdf", hdr, binary=True)
            if not pdf.startswith(b"%PDF"):
                raise ValueError(f"not a pdf ({len(pdf)} bytes)")
            open(dest, "wb").write(pdf)
            r["status"] = "ok"
            added += 1
            print(f"  OK {len(pdf):>9,}b  {r['folder']}/{r['file']}", flush=True)
        except Exception as e:
            r["status"] = f"error: {e}"
            print(f"  FAIL {r['folder']}/{r['file']}: {e}", flush=True)
        manifest.append(r)
        time.sleep(0.4)

    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), indent=1)
    print(f"downloaded {added}; manifest now {len(manifest)} entries")


if __name__ == "__main__":
    main()
