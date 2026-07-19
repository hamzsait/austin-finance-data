#!/usr/bin/env python3
"""
generate_pdfs.py — Standalone report generator.

Produces two one-page landscape PDFs summarizing all-time campaign
contributions received from two firms — Endeavor Real Estate Group and
Armbrust & Brown, PLLC — by:
  1. Austin City Council (Mayor + 10 districts)  -> endeavor_armbrust_austin_council.pdf
  2. Travis County Commissioners Court (Judge + 4 precincts) -> endeavor_armbrust_travis_commissioners.pdf

Reads austin_finance.db (read-only). Uses only local portrait assets in
assets/photos/. No network access required.
"""
import os
import re
import sqlite3
from datetime import datetime

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

try:
    from PIL import Image
except ImportError:
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "austin_finance.db")
PHOTOS = os.path.join(HERE, "assets", "photos")

# ---- Rosters: (name, seat, recipient_key_in_db, photo_file) ----
AUSTIN = [
    ("Kirk Watson",            "Mayor",       'Watson, Kirk P.',          "au0.webp"),
    ("Natasha Harper-Madison", "District 1",  'Harper-Madison, Natasha N.', "au1.webp"),
    ("Vanessa Fuentes",        "District 2",  'Fuentes, Vanessa',         "au2.webp"),
    ("José Velásquez",         "District 3",  'Velasquez, Jose',          "au3.webp"),
    ("José “Chito” Vela", "District 4", 'Vela, Jose "Chito", III', "au4.webp"),
    ("Ryan Alter",             "District 5",  'Alter, Ryan',              "au5.webp"),
    ("Krista Laine",           "District 6",  'Laine, Krista M.',         "au6.webp"),
    ("Mike Siegel",            "District 7",  'Siegel, Mike',             "au7.webp"),
    ("Paige Ellis",            "District 8",  'Ellis, Paige',             "au8.webp"),
    ("Zohaib “Zo” Qadri", "District 9", 'Qadri, Zohaib',         "au9.webp"),
    ("Marc Duchen",            "District 10", 'Duchen, Marc',             "au10.webp"),
]
TRAVIS = [
    ("Andy Brown",       "County Judge", 'Brown, Andy',       "tc-brown.webp"),
    ("Jeff Travillion",  "Precinct 1",   'Travillion, Jeff',  "tc-travillion.webp"),
    ("Brigid Shea",      "Precinct 2",   'Shea, Brigid',      "tc-shea.webp"),
    ("Ann Howard",       "Precinct 3",   'Howard, Ann',       "tc-howard.webp"),
    ("George Morales III","Precinct 4",  'Morales, George',   "tc-morales.webp"),
]

# ---- Firm match rules (see endeavor_armbrust_match_notes.md for the full audit) ----
# Matching is done row-by-row in Python (explicit + traceable, not fuzzy). A row
# counts for a firm if ANY of:
#   (1) LITERAL   — firm name (incl. known typos) appears in the donor name,
#                   reported employer, OR reported occupation field.
#   (2) ERG/EREG  — the Endeavor abbreviation as a whole field, but ONLY for a
#                   donor already confirmed Endeavor by rule 1 (excludes unrelated
#                   "ERG" environmental-consulting donors).
#   (3) PRINCIPAL + GENERIC EMPLOYER — the donor is a confirmed firm principal
#                   (spelled the firm out on some filing) AND this gift's employer
#                   is blank/generic (retired/self/none/homemaker/...). Recovers
#                   e.g. Kirk Rudy's gifts filed under "None"/"Retired" while still
#                   EXCLUDING rows that name a different employer (Holland & Knight,
#                   MD Anderson, Long View Equity, JMI Realty, ...).
ENDEAVOR_SUBSTR  = ("endeavor", "endevor", "endeavour", "emdeavor")   # incl. typos
ENDEAVOR_TOKEN   = ("erg", "ereg")                                    # abbreviation (confirmed only)
ENDEAVOR_EXCLUDE = ("grand endeavor",)                                # unrelated homebuilder
ARMBRUST_SUBSTR  = ("armbrust", "armbrst", "armburst", "armrbust", "ambrust")  # incl. typos
ARMBRUST_EXCLUDE = ("armbruster",)                                    # different surname (Milestone)
GENERIC_EMPLOYER = {
    "", "none", "n/a", "na", "n/a.", "n\\a", "retired", "self", "self employed",
    "self-employed", "selfemployed", "self employeed", "self-employeed", "homemaker",
    "home maker", "housewife", "mother", "father", "not employed", "note employed",
    "not applicable", "unemployed", "unknown", "requested", "tbd",
    "community volunteer", "student", ".", "..", "...",
}

# Confirmed-principal donor-name sets, populated once from the DB at runtime.
ENDEAVOR_PEOPLE = set()
ARMBRUST_PEOPLE = set()


def _norm(x):
    return (x or "").strip().lower()


def _endeavor_strong(donor, emp, occ):
    for f in (donor, emp, occ):
        lf = _norm(f)
        if any(x in lf for x in ENDEAVOR_EXCLUDE):
            continue
        if any(s in lf for s in ENDEAVOR_SUBSTR):
            return True
    return False


def _armbrust_strong(donor, emp, occ):
    for f in (donor, emp, occ):
        lf = _norm(f)
        if any(x in lf for x in ARMBRUST_EXCLUDE):
            continue
        if any(s in lf for s in ARMBRUST_SUBSTR):
            return True
    return False


def load_firm_people(cur):
    """Build the confirmed-principal donor-name sets from the whole dataset."""
    ENDEAVOR_PEOPLE.clear()
    ARMBRUST_PEOPLE.clear()
    cur.execute("SELECT DISTINCT donor, donor_reported_employer, donor_reported_occupation "
                "FROM campaign_finance")
    for donor, emp, occ in cur.fetchall():
        if _endeavor_strong(donor, emp, occ):
            ENDEAVOR_PEOPLE.add(donor)
        if _armbrust_strong(donor, emp, occ):
            ARMBRUST_PEOPLE.add(donor)


def is_endeavor(donor, emp, occ):
    if _endeavor_strong(donor, emp, occ):
        return True
    if donor in ENDEAVOR_PEOPLE and any(_norm(f) in ENDEAVOR_TOKEN for f in (donor, emp, occ)):
        return True
    if donor in ENDEAVOR_PEOPLE and _norm(emp) in GENERIC_EMPLOYER:
        return True
    return False


def is_armbrust(donor, emp, occ):
    if _armbrust_strong(donor, emp, occ):
        return True
    if donor in ARMBRUST_PEOPLE and _norm(emp) in GENERIC_EMPLOYER:
        return True
    return False

# ---- Decode Politics brand palette (from decodepolitics.org) ----
C_NAVY     = (0.094, 0.192, 0.310)   # #18314f  primary ink
C_CRIMSON  = (0.800, 0.122, 0.235)   # #cc1f3c  brand accent
C_SKY      = (0.812, 0.890, 0.961)   # #cfe3f5  light blue
C_ENDEAVOR = C_NAVY                   # Endeavor bars  -> brand navy
C_ARMBRUST = C_CRIMSON                # Armbrust bars  -> brand crimson
C_INK      = C_NAVY
C_GREY     = (0.42, 0.45, 0.50)
C_LIGHT    = (0.88, 0.90, 0.93)
C_TRACK    = (0.918, 0.933, 0.953)   # bar track (light navy tint)


def parse_amt(s):
    if s is None:
        return 0.0
    s = str(s).replace('$', '').replace(',', '').strip()
    if s in ('', '-', 'n/a', 'NA'):
        return 0.0
    try:
        return float(s)
    except ValueError:
        m = re.findall(r'-?\d+\.?\d*', s)
        return float(m[0]) if m else 0.0


def parse_date(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d', '%m-%d-%Y'):
        try:
            return datetime.strptime(s[:10], fmt)
        except ValueError:
            pass
    return None


def firm_stats(cur, recipient, matcher):
    # Sum balanced_amount (falling back to contribution_amount where NULL) and
    # skip non-positive rows: amended/superseded filings carry correction='X'
    # and balanced_amount=0, so raw sums would double-count every amended gift.
    cur.execute(
        "SELECT donor, donor_reported_employer, donor_reported_occupation, "
        "contribution_amount, balanced_amount, contribution_date "
        "FROM campaign_finance WHERE recipient = ?",
        (recipient,))
    total, n, dates = 0.0, 0, []
    for donor, emp, occ, amt, bal, dt in cur.fetchall():
        if not matcher(donor, emp, occ):
            continue
        a = parse_amt(amt) if bal is None else float(bal)
        if a <= 0:
            continue
        total += a
        n += 1
        d = parse_date(dt)
        if d:
            dates.append(d)
    return {
        "total": round(total, 2), "n": n,
        "dmin": min(dates) if dates else None,
        "dmax": max(dates) if dates else None,
    }


def build(cur, roster):
    rows = []
    for name, seat, recip, photo in roster:
        e = firm_stats(cur, recip, is_endeavor)
        a = firm_stats(cur, recip, is_armbrust)
        dmins = [d for d in (e["dmin"], a["dmin"]) if d]
        dmaxs = [d for d in (e["dmax"], a["dmax"]) if d]
        rows.append({
            "name": name, "seat": seat, "photo": photo,
            "endeavor": e, "armbrust": a,
            "combined": round(e["total"] + a["total"], 2),
            "span_min": min(dmins) if dmins else None,
            "span_max": max(dmaxs) if dmaxs else None,
        })
    rows.sort(key=lambda r: r["combined"], reverse=True)
    return rows


def money(v):
    return "$0" if not v else "${:,.0f}".format(v)


def span_text(dmin, dmax):
    if not dmin or not dmax:
        return "no contributions on record"
    fmt = lambda d: d.strftime("%b %Y")
    if fmt(dmin) == fmt(dmax):
        return fmt(dmin)
    return "{} – {}".format(fmt(dmin), fmt(dmax))


def load_photo(fname):
    path = os.path.join(PHOTOS, fname)
    if not os.path.exists(path) or Image is None:
        return None
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        s = min(w, h)                    # center-crop to square
        img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        return ImageReader(img)
    except Exception:
        return None


def _wrap(c, text, font, size, maxw):
    """Greedy word-wrap to lines fitting within maxw."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if c.stringWidth(t, font, size) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _wordmark(c, x, y, size=20):
    """Render the brand wordmark: 'decode' crimson + '(politics):' navy + cursor."""
    f = "Helvetica-Bold"
    c.setFont(f, size)
    c.setFillColorRGB(*C_CRIMSON)
    c.drawString(x, y, "decode")
    w = c.stringWidth("decode", f, size)
    c.setFillColorRGB(*C_NAVY)
    c.drawString(x + w, y, "(politics):")
    end = x + w + c.stringWidth("(politics):", f, size)
    c.setFillColorRGB(*C_CRIMSON)          # blinking-cursor cue
    c.rect(end + 3, y - 1, 2.4, size * 0.82, stroke=0, fill=1)
    return end


def draw_page(c, title, subtitle, rows, date_str):
    W, H = letter                          # portrait 612 x 792
    ML = MR = 42
    x0, x1 = ML, W - MR
    cw = x1 - x0

    # ---- Header / branding ----
    yw = H - 54
    _wordmark(c, x0, yw, 21)
    c.setFont("Helvetica-Oblique", 9.5)
    c.setFillColorRGB(*C_GREY)
    c.drawRightString(x1, yw + 2, "Follow the money")
    # brand accent rule
    ry = yw - 13
    c.setStrokeColorRGB(*C_CRIMSON)
    c.setLineWidth(2.5)
    c.line(x0, ry, x1, ry)

    # report title (wrapped)
    tfont, tsize = "Helvetica-Bold", 15.5
    ty = ry - 23
    for ln in _wrap(c, title, tfont, tsize, cw):
        c.setFont(tfont, tsize)
        c.setFillColorRGB(*C_NAVY)
        c.drawString(x0, ty, ln)
        ty -= tsize + 3
    # subtitle
    ty -= 3
    c.setFillColorRGB(*C_GREY)
    c.setFont("Helvetica", 10.5)
    c.drawString(x0, ty, subtitle)

    # legend
    ty -= 21
    lx = x0
    for label, col in (("Endeavor Real Estate Group", C_ENDEAVOR),
                       ("Armbrust & Brown, PLLC", C_ARMBRUST)):
        c.setFillColorRGB(*col)
        c.roundRect(lx, ty - 2, 13, 13, 2.5, stroke=0, fill=1)
        c.setFillColorRGB(*C_NAVY)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(lx + 18, ty + 1, label)
        lx += 18 + c.stringWidth(label, "Helvetica-Bold", 10.5) + 30

    header_bottom = ty - 14

    # ---- Rows ----
    footer_top = 58
    n = len(rows)
    avail = header_bottom - footer_top
    row_h = min(avail / n, 120)
    top = header_bottom - max(0, (avail - row_h * n) / 2)   # center if ever capped

    scale = max([max(r["endeavor"]["total"], r["armbrust"]["total"]) for r in rows] + [1.0])

    photo_s = min(row_h * 0.72, 62)
    zone_x0 = x0 + photo_s + 16
    val_w = 84
    bar_x0 = zone_x0
    bar_x1 = x1 - val_w
    val_x = bar_x1 + 9

    for i, r in enumerate(rows):
        rt = top - i * row_h              # row top edge
        y0 = rt - row_h                   # row bottom edge

        # zebra
        if i % 2 == 0:
            c.setFillColorRGB(0.962, 0.972, 0.986)
            c.roundRect(x0 - 5, y0 + 2, cw + 10, row_h - 4, 5, stroke=0, fill=1)

        # photo
        pcy = y0 + (row_h - photo_s) / 2
        img = load_photo(r["photo"])
        if img is not None:
            c.saveState()
            p = c.beginPath()
            p.roundRect(x0, pcy, photo_s, photo_s, 7)
            c.clipPath(p, stroke=0, fill=0)
            c.drawImage(img, x0, pcy, photo_s, photo_s,
                        preserveAspectRatio=True, anchor='c', mask='auto')
            c.restoreState()
        else:
            c.setFillColorRGB(*C_SKY)
            c.roundRect(x0, pcy, photo_s, photo_s, 7, stroke=0, fill=1)
        c.setStrokeColorRGB(*C_LIGHT)
        c.setLineWidth(0.75)
        c.roundRect(x0, pcy, photo_s, photo_s, 7, stroke=1, fill=0)

        # rank (left gutter)
        c.setFillColorRGB(*C_GREY)
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(x0 - 8, rt - 15, str(i + 1))

        # name line: name (bold navy) + seat/combined (grey) + span (right)
        name_y = rt - min(20, row_h * 0.30)
        c.setFillColorRGB(*C_NAVY)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(zone_x0, name_y, r["name"])
        nx = zone_x0 + c.stringWidth(r["name"], "Helvetica-Bold", 14)
        c.setFillColorRGB(*C_GREY)
        c.setFont("Helvetica", 10)
        c.drawString(nx + 8, name_y, "· {} · combined {}".format(r["seat"], money(r["combined"])))
        c.setFillColorRGB(*C_NAVY)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawRightString(x1, name_y + 1, span_text(r["span_min"], r["span_max"]))

        # two stacked full-width bars
        gap = 5
        stack_top = name_y - 9
        bottom_lim = y0 + max(5, row_h * 0.10)
        bar_h = max(9, min((stack_top - bottom_lim - gap) / 2, 18))
        # vertically center the stack in [bottom_lim, stack_top]
        stack_h = bar_h * 2 + gap
        by = (stack_top + bottom_lim) / 2 + stack_h / 2 - bar_h
        for key, col in (("endeavor", C_ENDEAVOR), ("armbrust", C_ARMBRUST)):
            val = r[key]["total"]
            w = (val / scale) * (bar_x1 - bar_x0)
            c.setFillColorRGB(*C_TRACK)
            c.roundRect(bar_x0, by, bar_x1 - bar_x0, bar_h, bar_h / 2, stroke=0, fill=1)
            if w > 0.5:
                c.setFillColorRGB(*col)
                c.roundRect(bar_x0, by, max(w, bar_h), bar_h, bar_h / 2, stroke=0, fill=1)
            c.setFont("Helvetica-Bold", 11.5)
            c.setFillColorRGB(*(col if val > 0 else C_GREY))
            c.drawString(val_x, by + bar_h / 2 - 4, money(val))
            by -= bar_h + gap

    # ---- Footer ----
    c.setStrokeColorRGB(*C_LIGHT)
    c.setLineWidth(0.75)
    c.line(x0, footer_top - 4, x1, footer_top - 4)
    c.setFillColorRGB(*C_CRIMSON)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x0, footer_top - 19, "decodepolitics.org")
    c.setFillColorRGB(*C_GREY)
    c.setFont("Helvetica", 9.5)
    c.drawRightString(x1, footer_top - 19, date_str)
    c.setFillColorRGB(*C_GREY)
    note = ("All-time contributions (monetary + in-kind) where the donor, employer, or occupation matches the firm; amended/superseded report rows excluded"
            "  ·  Source: City of Austin campaign finance dataset (data.austintexas.gov)  ·  Bars scaled to page maximum")
    fsize = 7.5
    while fsize > 5.5 and c.stringWidth(note, "Helvetica", fsize) > cw:
        fsize -= 0.25
    c.setFont("Helvetica", fsize)
    c.drawCentredString(W / 2, footer_top - 33, note)


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    load_firm_people(cur)               # populate confirmed-principal name sets
    austin = build(cur, AUSTIN)
    travis = build(cur, TRAVIS)
    conn.close()

    date_str = datetime(2026, 7, 19).strftime("%B %-d, %Y") if os.name != "nt" \
        else "July 19, 2026"

    out1 = os.path.join(HERE, "endeavor_armbrust_austin_council.pdf")
    c = canvas.Canvas(out1, pagesize=letter)     # portrait 8.5 x 11
    draw_page(c, "Contributions from Endeavor & Armbrust & Brown — Austin City Council",
              "Mayor + 10 council districts · sorted by combined dollars received (all-time)",
              austin, date_str)
    c.showPage()
    c.save()

    out2 = os.path.join(HERE, "endeavor_armbrust_travis_commissioners.pdf")
    c = canvas.Canvas(out2, pagesize=letter)     # portrait 8.5 x 11
    draw_page(c, "Contributions from Endeavor & Armbrust & Brown — Travis County Commissioners Court",
              "County Judge + 4 precinct commissioners · sorted by combined dollars received (all-time)",
              travis, date_str)
    c.showPage()
    c.save()

    print("Wrote:", out1)
    print("Wrote:", out2)
    for label, rows in (("AUSTIN", austin), ("TRAVIS", travis)):
        print("\n" + label)
        for r in rows:
            print("  {:26s} {:12s} E={:>10s} A={:>10s} span {}".format(
                r["name"], r["seat"], money(r["endeavor"]["total"]),
                money(r["armbrust"]["total"]), span_text(r["span_min"], r["span_max"])))


if __name__ == "__main__":
    main()
