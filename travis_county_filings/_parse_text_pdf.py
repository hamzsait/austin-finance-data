"""Deterministic extraction for TEC Form C/OH reports that carry a text layer.

Electronically-filed reports (TEC form generator, ~2,300 chars/page) can be read
straight out of the PDF text layer — exact, instant, no vision model. Scanned
filings have no text layer and still go through _render_pages -> _run_extraction.

Emits the SAME per-page JSON shape the vision pipeline writes to extracted/raw/,
so _validate.py and _assemble_csv.py consume the output unchanged:

    {"chunk": "<official>__<report-stem>__text", "pages": [ {...}, ... ]}

Usage:
    python _parse_text_pdf.py --scan                    # report which PDFs qualify
    python _parse_text_pdf.py <pdf> [<pdf> ...]         # extract to extracted/raw/
    python _parse_text_pdf.py --all                     # every text-layer PDF found
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

import pymupdf

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "extracted", "raw")
TEXT_LAYER_MIN_CPP = 400          # chars/page below this = scanned, needs vision

# Column boundary between the "Principal occupation / Job title" box (left) and
# the "Employer" box (right) on Schedule A1/A2 entry rows.
OCC_EMP_SPLIT = 300.0
AMOUNT_X_MIN = 420.0              # amount column lives at the far right

# The per-entry header row, repeated above every entry on the page.
HEADER_ROW = re.compile(r"Full name of contributor|Amount of Contribution", re.I)

REPORT_TYPES = [
    "January 15", "July 15", "30th day before election", "8th day before election",
    "Runoff", "Exceeded modified reporting limit", "Final Report",
    "15th day after campaign treasurer appointment",
]


def lines(page, tol=4):
    """[(y, [words sorted by x])] in reading order."""
    rows = collections.defaultdict(list)
    for w in page.get_text("words"):
        rows[round(w[1] / tol)].append(w)
    return [(k * tol, sorted(rows[k], key=lambda w: w[0])) for k in sorted(rows)]


def text_of(ws):
    return " ".join(w[4] for w in ws)


def money(s):
    try:
        return float(str(s).replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def classify(page):
    up = page.get_text().upper()
    if "COVER SHEET PG 1" in up and "CAMPAIGN FINANCE REPORT" in up:
        return "COVER1"
    if "COVER SHEET PG 2" in up or "SUPPORT & TOTALS" in up:
        return "COVER2"
    if "SUBTOTALS" in up and "C/OH" in up:
        return "COVER3"
    if "NON-MONETARY" in up and "SCHEDULE" in up:
        return "A2"
    if "MONETARY POLITICAL CONTRIBUTIONS" in up and "SCHEDULE" in up:
        return "A1"
    if "POLITICAL CONTRIBUTIONS" in up and "SCHEDULE A" in up and "PLEDGE" not in up:
        return "A1"
    return "OTHER"


def parse_cover1(page, pno):
    ls = lines(page)
    flat = [(y, text_of(ws), ws) for y, ws in ls]
    out = {"page": pno, "type": "COVER1", "filer_name": None, "report_type": None,
           "period_from": None, "period_through": None, "office_held": None,
           "correction": False}

    # Name: FIRST sits under the "MS / MRS / MR FIRST MI" header, LAST under
    # "NICKNAME LAST SUFFIX", a line or two below. Form labels on this page are
    # ALL CAPS ("OFFICE USE ONLY", "OFFICEHOLDER"); the filled-in name is not,
    # so only accept Title-case tokens.
    def name_below(start, limit=4):
        for j in range(start + 1, min(start + limit, len(flat))):
            for w in flat[j][2]:
                if w[0] > 150 and re.fullmatch(r"[A-Z][a-z'\-]+", w[4]):
                    return w[4]
        return None

    first = last = None
    for i, (y, t, ws) in enumerate(flat):
        if first is None and re.search(r"MS\s*/\s*MRS\s*/\s*MR\s+FIRST", t):
            first = name_below(i)
        if last is None and "NICKNAME" in t and "LAST" in t:
            last = name_below(i)
    if first and last:
        out["filer_name"] = f"{last}, {first}"

    # Report type: an "X" glyph immediately left of the checked label.
    checks = []
    for y, t, ws in flat:
        xs = [w for w in ws if w[4] == "X"]
        for x in xs:
            after = " ".join(w[4] for w in ws if w[0] > x[0])
            for rt in REPORT_TYPES:
                if after.startswith(rt):
                    checks.append(rt)
                    break
    if checks:
        # prefer a schedule type over election-type boxes captured elsewhere
        out["report_type"] = checks[0]

    for y, t, ws in flat:
        m = re.search(r"(\d{2}/\d{2}/\d{4})\s+THROUGH\s+(\d{2}/\d{2}/\d{4})", t)
        if m:
            out["period_from"], out["period_through"] = m.group(1), m.group(2)
        if re.match(r"^11\s+OFFICE", t) or "OFFICE HELD" in t:
            idx = flat.index((y, t, ws))
            for j in range(idx, min(idx + 3, len(flat))):
                cand = text_of([w for w in flat[j][2] if w[0] < OCC_EMP_SPLIT])
                if cand and "OFFICE" not in cand.upper():
                    out["office_held"] = cand.strip()
                    break
    up = page.get_text().upper()
    if "CORRECTION" in up and "AFFIDAVIT" in up:
        out["correction"] = True
    return out


COVER2_FIELDS = [
    ("total_unitemized_contributions", "TOTAL UNITEMIZED POLITICAL CONTRIBUTIONS"),
    ("total_contributions", "TOTAL POLITICAL CONTRIBUTIONS"),
    ("total_unitemized_expenditures", "TOTAL UNITEMIZED POLITICAL EXPENDITURES"),
    ("total_expenditures", "TOTAL POLITICAL EXPENDITURES"),
    ("contribution_balance", "TOTAL POLITICAL CONTRIBUTIONS MAINTAINED"),
    ("outstanding_loans", "TOTAL PRINCIPAL AMOUNT OF ALL OUTSTANDING LOANS"),
]


def parse_cover2(page, pno):
    """Amounts sit on their own line near the label; take the nearest $ value
    within a few lines below the numbered label."""
    ls = lines(page)
    flat = [(y, text_of(ws).upper(), text_of(ws)) for y, ws in ls]
    out = {"page": pno, "type": "COVER2"}
    for key, label in COVER2_FIELDS:
        val = None
        for i, (y, up, raw) in enumerate(flat):
            if label not in up:
                continue
            for j in range(i, min(i + 4, len(flat))):
                m = re.search(r"\$\s*([\d,]+\.\d{2})", flat[j][2])
                if m:
                    val = money(m.group(1))
                    break
            if val is not None:
                break
        out[key] = val
    return out


def parse_schedule(page, pno, sched):
    """Schedule A1/A2 entries.

    Layout per entry: an anchor line 'MM/DD/YYYY  Name, First   $amount',
    then the address block, then an occupation/employer value line split at
    OCC_EMP_SPLIT. The header row repeats above each entry, so the address /
    occupation lines are located relative to the anchor.
    """
    ls = lines(page)
    ys = [y for y, _ in ls]
    txt = [text_of(ws) for _, ws in ls]
    wsl = [ws for _, ws in ls]

    sch_pos = None
    for t in txt:
        m = re.search(r"Sch:\s*(\d+)\s*/\s*(\d+)", t)
        if m:
            sch_pos = f"{m.group(1)}/{m.group(2)}"
            break

    anchors = []
    for i, ws in enumerate(wsl):
        date_w = [w for w in ws if re.fullmatch(r"\d{2}/\d{2}/\d{4}", w[4]) and w[0] < 110]
        amt_w = [w for w in ws if w[0] >= AMOUNT_X_MIN and re.fullmatch(r"\$?[\d,]+\.\d{2}", w[4])]
        if not date_w:
            continue
        name = " ".join(w[4] for w in ws if 110 <= w[0] < AMOUNT_X_MIN)
        name = re.sub(r"\s*out-of-state PAC.*$", "", name).strip()
        anchors.append({
            "i": i, "date": date_w[0][4], "name": name,
            "amount": money(amt_w[0][4]) if amt_w else None,
        })

    entries = []
    for a_idx, a in enumerate(anchors):
        stop = anchors[a_idx + 1]["i"] if a_idx + 1 < len(anchors) else len(wsl)
        addr, occ, emp, in_kind = [], None, None, None
        j = a["i"] + 1
        while j < stop:
            t = txt[j]
            if t.startswith("Contributor address") or re.match(r"^\d+\s+Contributor address", t):
                j += 1
                continue
            if "Principal occupation" in t:
                # An entry with both boxes left blank is followed directly by the
                # next entry's header row — don't read that as occupation data.
                if j + 1 < stop and not HEADER_ROW.search(txt[j + 1]):
                    row = wsl[j + 1]
                    occ = " ".join(w[4] for w in row if w[0] < OCC_EMP_SPLIT).strip() or None
                    emp = " ".join(w[4] for w in row if w[0] >= OCC_EMP_SPLIT).strip() or None
                j += 2
                continue
            if "In-kind contribution description" in t or "IN-KIND CONTRIBUTION DESCRIPTION" in t.upper():
                if j + 1 < stop:
                    in_kind = txt[j + 1].strip() or None
                j += 2
                continue
            if re.match(r"^\d*\s*(Date|Full name|Amount of Contribution)", t):
                j += 1
                continue
            if t.strip() and not t.startswith("Forms provided"):
                addr.append(t.strip())
            j += 1

        csz = next((x for x in reversed(addr) if re.search(r",\s*[A-Z]{2}\.?\s+\d{5}", x)), None)
        oos = False
        row_txt = txt[a["i"]]
        if re.search(r"out-of-state PAC\s*\(ID#:\s*\w", row_txt):
            oos = True

        e = {"date": a["date"], "name": a["name"], "city_state_zip": csz,
             "amount": a["amount"], "occupation": occ, "employer": emp,
             "oos_pac": oos}
        if sched == "A2":
            e["in_kind_description"] = in_kind
        if a["amount"] is None or not a["name"]:
            e["uncertain"] = True
            e["note"] = "amount or name not readable from text layer"
        entries.append(e)

    return {"page": pno, "type": sched, "sch_pos": sch_pos, "entries": entries}


def parse_pdf(path):
    doc = pymupdf.open(path)
    pages = []
    for i, page in enumerate(doc, 1):
        t = classify(page)
        if t == "COVER1":
            pages.append(parse_cover1(page, i))
        elif t == "COVER2":
            pages.append(parse_cover2(page, i))
        elif t in ("A1", "A2"):
            pages.append(parse_schedule(page, i, t))
        else:
            label = None
            m = re.search(r"SCHEDULE\s+([A-Z]\d?)", page.get_text().upper())
            if m:
                label = "SCHEDULE " + m.group(1)
            pages.append({"page": i, "type": t if t == "COVER3" else "OTHER",
                          "label": label})
    doc.close()
    return pages


def chars_per_page(path):
    d = pymupdf.open(path)
    n = max(d.page_count, 1)
    c = sum(len(p.get_text().strip()) for p in d)
    d.close()
    return c // n, n


def chunk_id(path):
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace("\\", "/")
    official, fname = rel.split("/", 1)
    return f"{official}__{os.path.splitext(fname)[0]}__text"


CHUNKS = os.path.join(ROOT, "_chunks.json")


def register_chunk(path, npages, out_path):
    """Add/replace this report's entry in _chunks.json.

    _validate.py and _assemble_csv.py both derive their report list from
    _chunks.json and rewrite validation.json / travis_contributions.csv
    wholesale, so a text-extracted report has to appear there or it is silently
    dropped from the final CSV. 'pages' is only ever used for its length by
    those two scripts (the renderer is what consumes real page paths), so we
    record the page count as placeholder names.
    """
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace("\\", "/")
    official, fname = rel.split("/", 1)
    stem = os.path.splitext(fname)[0]
    cid = chunk_id(path)
    entry = {
        "id": cid, "official": official, "report": stem, "first_page": 1,
        "pages": [f"{stem}/p{i:04d}.text" for i in range(1, npages + 1)],
        "out": out_path, "source": "text-layer",
    }
    chunks = json.load(open(CHUNKS, encoding="utf-8")) if os.path.exists(CHUNKS) else []
    # drop any prior plan for this same report (vision chunks or an older run)
    chunks = [c for c in chunks
              if not (c.get("official") == official and c.get("report") == stem)]
    chunks.append(entry)
    json.dump(chunks, open(CHUNKS, "w", encoding="utf-8"), indent=1)
    return cid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("--scan", action="store_true", help="report qualifying PDFs, extract nothing")
    ap.add_argument("--all", action="store_true", help="every text-layer PDF under the filing folders")
    ap.add_argument("--register", action="store_true",
                    help="add each extracted report to _chunks.json so _validate.py "
                         "and _assemble_csv.py pick it up")
    ap.add_argument("--out", default=RAW)
    args = ap.parse_args()

    paths = args.pdfs
    if args.all or args.scan:
        paths = sorted(glob.glob(os.path.join(ROOT, "*", "*.pdf")))
    if not paths:
        ap.error("give PDF paths, or --all / --scan")

    os.makedirs(args.out, exist_ok=True)
    qualifying = []
    for p in paths:
        try:
            cpp, n = chars_per_page(p)
        except Exception as e:
            print(f"  ERR  {p}: {e}")
            continue
        kind = "TEXT" if cpp >= TEXT_LAYER_MIN_CPP else "SCAN"
        if args.scan:
            print(f"  {kind}  pages={n:4d}  chars/pg={cpp:5d}  {os.path.relpath(p, ROOT)}")
            continue
        if kind == "SCAN":
            print(f"  SKIP (scanned, needs vision) {os.path.relpath(p, ROOT)}")
            continue
        qualifying.append(p)

    if args.scan:
        return

    for p in qualifying:
        pages = parse_pdf(p)
        cid = chunk_id(p)
        dest = os.path.join(args.out, cid + ".json")
        json.dump({"chunk": cid, "pages": pages}, open(dest, "w", encoding="utf-8"), indent=1)
        if args.register:
            register_chunk(p, len(pages), dest)
        ents = sum(len(pg.get("entries", [])) for pg in pages)
        total = sum(e["amount"] or 0 for pg in pages for e in pg.get("entries", []))
        cover = next((pg for pg in pages if pg["type"] == "COVER2"), None)
        sworn = cover.get("total_contributions") if cover else None
        flag = ""
        if sworn is not None:
            flag = "RECONCILES" if abs(sworn - total) < 1.0 else f"DELTA {total - sworn:+,.2f}"
        print(f"  {os.path.basename(dest)}: {len(pages)}pp {ents} entries "
              f"${total:,.2f} sworn={sworn} {flag}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
