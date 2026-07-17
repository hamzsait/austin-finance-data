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

# ---- Firm match patterns (case-insensitive; matches donor name OR employer) ----
ENDEAVOR_WHERE = (
    "((lower(donor) LIKE '%endeavor%' OR lower(donor_reported_employer) LIKE '%endeavor%') "
    "AND lower(donor) NOT LIKE '%grand endeavor%' "
    "AND lower(donor_reported_employer) NOT LIKE '%grand endeavor%')"
)
ARMBRUST_WHERE = (
    "((lower(donor) LIKE '%armbrust%' OR lower(donor_reported_employer) LIKE '%armbrust%') "
    "AND lower(donor) NOT LIKE '%armbruster%' "
    "AND lower(donor_reported_employer) NOT LIKE '%armbruster%')"
)

# ---- Colors ----
C_ENDEAVOR = (0.11, 0.53, 0.60)   # teal
C_ARMBRUST = (0.85, 0.42, 0.28)   # terracotta
C_INK      = (0.13, 0.14, 0.16)
C_GREY     = (0.45, 0.47, 0.50)
C_LIGHT    = (0.90, 0.91, 0.93)
C_TRACK    = (0.945, 0.95, 0.955)


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


def firm_stats(cur, recipient, where):
    cur.execute(
        f"SELECT contribution_amount, contribution_date FROM campaign_finance "
        f"WHERE recipient = ? AND {where}", (recipient,))
    total, n, dates = 0.0, 0, []
    for amt, dt in cur.fetchall():
        total += parse_amt(amt)
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
        e = firm_stats(cur, recip, ENDEAVOR_WHERE)
        a = firm_stats(cur, recip, ARMBRUST_WHERE)
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


def draw_page(c, title, subtitle, rows):
    W, H = landscape(letter)          # 792 x 612
    c.setFillColorRGB(*C_INK)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, H - 44, title)
    c.setFillColorRGB(*C_GREY)
    c.setFont("Helvetica", 8.5)
    c.drawString(40, H - 58, subtitle)

    # Legend (own horizontal line below the subtitle, left-aligned)
    lx, ly = 40, H - 76
    for label, col in (("Endeavor Real Estate Group", C_ENDEAVOR),
                       ("Armbrust & Brown, PLLC", C_ARMBRUST)):
        c.setFillColorRGB(*col)
        c.rect(lx, ly, 9, 9, stroke=0, fill=1)
        c.setFillColorRGB(*C_INK)
        c.setFont("Helvetica", 8)
        c.drawString(lx + 13, ly + 1, label)
        lx += 20 + c.stringWidth(label, "Helvetica", 8) + 28

    # Layout geometry
    top = H - 94
    bottom = 34
    n = len(rows)
    row_h = (top - bottom) / n

    photo_s = min(44, row_h - 8)
    px = 40
    name_x = px + photo_s + 12
    bar_x0 = 250
    bar_max_w = 300           # leaves room for value label + span
    val_x = bar_x0 + bar_max_w + 8
    span_x = W - 150

    scale = max([max(r["endeavor"]["total"], r["armbrust"]["total"]) for r in rows] + [1.0])

    for i, r in enumerate(rows):
        y0 = top - (i + 1) * row_h
        cy = y0 + row_h / 2

        # zebra background
        if i % 2 == 0:
            c.setFillColorRGB(0.975, 0.978, 0.982)
            c.rect(36, y0 + 1, W - 72, row_h - 2, stroke=0, fill=1)

        # rank chip
        c.setFillColorRGB(*C_GREY)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(px - 4, cy - 3, str(i + 1))

        # photo
        img = load_photo(r["photo"])
        pcx, pcy = px, cy - photo_s / 2
        if img is not None:
            c.saveState()
            p = c.beginPath()
            p.roundRect(pcx, pcy, photo_s, photo_s, 5)
            c.clipPath(p, stroke=0, fill=0)
            c.drawImage(img, pcx, pcy, photo_s, photo_s,
                        preserveAspectRatio=True, anchor='c', mask='auto')
            c.restoreState()
        else:
            c.setFillColorRGB(*C_LIGHT)
            c.roundRect(pcx, pcy, photo_s, photo_s, 5, stroke=0, fill=1)
        c.setStrokeColorRGB(*C_LIGHT)
        c.setLineWidth(0.75)
        c.roundRect(pcx, pcy, photo_s, photo_s, 5, stroke=1, fill=0)

        # name + seat + combined
        c.setFillColorRGB(*C_INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(name_x, cy + 4, r["name"])
        c.setFillColorRGB(*C_GREY)
        c.setFont("Helvetica", 7.8)
        c.drawString(name_x, cy - 7, "{}  ·  combined {}".format(r["seat"], money(r["combined"])))

        # two bars
        bar_h = min(8.5, (row_h - 12) / 2)
        gap = 3
        firms = (("endeavor", C_ENDEAVOR), ("armbrust", C_ARMBRUST))
        total_stack = bar_h * 2 + gap
        by = cy + total_stack / 2 - bar_h
        for key, col in firms:
            val = r[key]["total"]
            w = (val / scale) * bar_max_w
            # track
            c.setFillColorRGB(*C_TRACK)
            c.roundRect(bar_x0, by, bar_max_w, bar_h, bar_h / 2, stroke=0, fill=1)
            # value bar
            if w > 0.5:
                c.setFillColorRGB(*col)
                c.roundRect(bar_x0, by, max(w, bar_h), bar_h, bar_h / 2, stroke=0, fill=1)
            # value label
            c.setFont("Helvetica-Bold", 8)
            if val > 0:
                c.setFillColorRGB(*col)
            else:
                c.setFillColorRGB(*C_GREY)
            c.drawString(val_x, by + bar_h / 2 - 3, money(val))
            by -= (bar_h + gap)

        # span sidebar
        c.setFillColorRGB(*C_GREY)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(span_x, cy + 2, "Contributions span")
        c.setFillColorRGB(*C_INK)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(span_x, cy - 8, span_text(r["span_min"], r["span_max"]))

    # footer
    c.setFillColorRGB(*C_GREY)
    c.setFont("Helvetica", 6.5)
    c.drawString(40, 20,
                 "Source: austin_finance.db campaign_finance table. All-time monetary + in-kind "
                 "contributions where donor name or reported employer matches the firm. Bars scaled to page maximum.")


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    austin = build(cur, AUSTIN)
    travis = build(cur, TRAVIS)
    conn.close()

    out1 = os.path.join(HERE, "endeavor_armbrust_austin_council.pdf")
    c = canvas.Canvas(out1, pagesize=landscape(letter))
    draw_page(c, "Contributions from Endeavor & Armbrust & Brown — Austin City Council",
              "Mayor + 10 council districts · sorted by combined dollars received (all-time)", austin)
    c.showPage()
    c.save()

    out2 = os.path.join(HERE, "endeavor_armbrust_travis_commissioners.pdf")
    c = canvas.Canvas(out2, pagesize=landscape(letter))
    draw_page(c, "Contributions from Endeavor & Armbrust & Brown — Travis County Commissioners",
              "County Judge + 4 precinct commissioners · sorted by combined dollars received (all-time)", travis)
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
