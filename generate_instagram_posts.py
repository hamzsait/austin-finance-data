#!/usr/bin/env python3
"""
generate_instagram_posts.py — Instagram post package generator (design v4).

Renders two Instagram-ready post packages (1080x1350 PNG, portrait feed size)
summarizing all-time campaign contributions received from donors employed at
Endeavor Real Estate Group and Armbrust & Brown, PLLC.

  Package 1 — Austin City Council        -> instagram_posts/austin/  (13 PNGs)
  Package 2 — Travis Commissioners Court -> instagram_posts/travis/  ( 7 PNGs)

Data source (v4): the SAME published donation tables that power
decodepolitics.org — the committed <slug>_all_donations.json files
(donor, date, amount, employer-identity, industry, location). No database
required; runs on any machine. Matching is by the cleaned employer identity:
  Endeavor  — employer contains "Endeavor Real Estate"
  Armbrust  — employer is "Armbrust & Brown" (the joint
              "Allen Boone Humphries Robinson / Armbrust Brown" identity is
              EXCLUDED, matching the site's firm rollups)

Design system: see INSTAGRAM_DESIGN_SPEC_V4.md ("Statement"). Ink-navy canvas,
crimson top edge, giant hero dollar figure with crimson $ and underline, brand
fonts (Space Grotesk / Inter / Oswald from assets/fonts/), validated bar
palette (#4a96d8 Endeavor / #e8536b Armbrust) on dark.
"""
import json
import os
import re
import unicodedata
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "instagram_posts")
PHOTOS = os.path.join(HERE, "assets", "photos")
FONTS = os.path.join(HERE, "assets", "fonts")

# ---- Rosters: (name, seat, data-file slug, photo file) ----
AUSTIN = [
    ("Kirk Watson",            "Mayor",       "watson",        "au0.webp"),
    ("Natasha Harper-Madison", "District 1",  "harpermadison", "au1.webp"),
    ("Vanessa Fuentes",        "District 2",  "fuentes",       "au2.webp"),
    ("José Velásquez",         "District 3",  "velasquez",     "au3.webp"),
    ("José “Chito” Vela",      "District 4",  "vela",          "au4.webp"),
    ("Ryan Alter",             "District 5",  "alter",         "au5.webp"),
    ("Krista Laine",           "District 6",  "laine",         "au6.webp"),
    ("Mike Siegel",            "District 7",  "siegel",        "au7.webp"),
    ("Paige Ellis",            "District 8",  "ellis",         "au8.webp"),
    ("Zohaib “Zo” Qadri",      "District 9",  "qadri",         "au9.webp"),
    ("Marc Duchen",            "District 10", "duchen",        "au10.webp"),
]
TRAVIS = [
    ("Andy Brown",        "County Judge", "brown",      "tc-brown.webp"),
    ("Jeff Travillion",   "Precinct 1",   "travillion", "tc-travillion.webp"),
    ("Brigid Shea",       "Precinct 2",   "shea",       "tc-shea.webp"),
    ("Ann Howard",        "Precinct 3",   "howard",     "tc-howard.webp"),
    ("George Morales III", "Precinct 4",  "morales",    "tc-morales.webp"),
]

# ---- Firm match on the published employer identity ----
ARMBRUST_EXCLUDE = "allen boone"


def match_firm(employer):
    e = (employer or "").lower()
    if "endeavor real estate" in e:
        return "endeavor"
    if "armbrust" in e and ARMBRUST_EXCLUDE not in e:
        return "armbrust"
    return None


def parse_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def build(roster):
    rows = []
    for name, seat, slug_, photo in roster:
        path = os.path.join(HERE, slug_ + "_all_donations.json")
        stats = {k: {"total": 0.0, "n": 0, "donors": set(), "dates": []}
                 for k in ("endeavor", "armbrust")}
        for donor, date, amount, employer, _industry, _loc in json.load(open(path)):
            firm = match_firm(employer)
            if not firm:
                continue
            s = stats[firm]
            s["total"] += amount
            s["n"] += 1
            s["donors"].add(donor)
            d = parse_date(date)
            if d:
                s["dates"].append(d)
        for s in stats.values():
            s["total"] = round(s["total"], 2)
            s["donors"] = len(s["donors"])
        dates = stats["endeavor"]["dates"] + stats["armbrust"]["dates"]
        rows.append({
            "name": name, "seat": seat, "photo": photo,
            "endeavor": stats["endeavor"], "armbrust": stats["armbrust"],
            "combined": round(stats["endeavor"]["total"] + stats["armbrust"]["total"], 2),
            "span_min": min(dates) if dates else None,
            "span_max": max(dates) if dates else None,
        })
    rows.sort(key=lambda r: r["combined"], reverse=True)
    return rows


def money(v):
    return "$0" if not v else "${:,.0f}".format(v)


def span_text(dmin, dmax):
    if not dmin or not dmax:
        return "no contributions on record"
    fmt = lambda d: d.strftime("%b %Y")
    return fmt(dmin) if fmt(dmin) == fmt(dmax) else "{} – {}".format(fmt(dmin), fmt(dmax))


# ---- Canvas ----
W, H = 1080, 1350
M = 84                    # margin, all sides
CW = W - 2 * M            # 912 content width
DPI = (300, 300)

TOP_BAR_H = 8             # crimson top edge
HEADER_RULE_Y = 158
FOOTER_RULE_Y = 1258

# ---- Palette (dark; bar pair validated for CVD + contrast on BG) ----
BG       = (12, 26, 44)      # #0c1a2c ink navy
WHITE    = (245, 248, 251)   # #f5f8fb primary text
SKY      = (200, 224, 244)   # #c8e0f4 brand sky
SLATE    = (143, 163, 184)   # #8fa3b8 muted
FAINT    = (104, 124, 146)   # #687c92 source notes
CRIMSON  = (232, 83, 107)    # #e8536b accent (bright-for-dark)
ENDEAVOR = (74, 150, 216)    # #4a96d8 Endeavor bar
ARMBRUST = CRIMSON           # Armbrust bar
HAIRLINE = (34, 54, 80)      # #223650 rules
TRACK    = (27, 47, 71)      # #1b2f47 bar track
KEYLINE  = (42, 65, 96)      # #2a4160 portrait keyline

_cache = {}


def _var_font(fname, size, weight):
    key = (fname, size, weight)
    if key not in _cache:
        f = ImageFont.truetype(os.path.join(FONTS, fname), size)
        f.set_variation_by_axes([weight])
        _cache[key] = f
    return _cache[key]


def grotesk(size, weight=700):
    return _var_font("SpaceGrotesk.ttf", size, weight)


def inter(size, weight=400):
    return _var_font("Inter.ttf", size, weight)


def oswald(size, weight=600):
    return _var_font("Oswald.ttf", size, weight)


def tw(draw, text, fnt):
    return draw.textlength(text, font=fnt)


def fit_grotesk(draw, text, max_size, max_w, weight=700, min_size=20):
    s = max_size
    while s > min_size and tw(draw, text, grotesk(s, weight)) > max_w:
        s -= 2
    return grotesk(s, weight), s


def wrap(draw, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tw(draw, t, fnt) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---- Tracked caps labels (Oswald, like the site's eyebrows) ----
def caps(draw, x, y, text, size=25, fill=SLATE, tr_em=0.18, anchor_right=None):
    fnt = oswald(size, 600)
    text = text.upper()
    tr = size * tr_em
    total = sum(tw(draw, c, fnt) for c in text) + tr * max(0, len(text) - 1)
    if anchor_right is not None:
        x = anchor_right - total
    for c in text:
        draw.text((x, y), c, font=fnt, fill=fill)
        x += tw(draw, c, fnt) + tr
    return total


# ---- Wordmark: decode(politics): — crimson / sky parens / white ----
WM_SEGS = (("decode", CRIMSON), ("(", SKY), ("politics", WHITE), (")", SKY),
           (":", CRIMSON))


def wordmark(draw, x, y, size):
    fb = grotesk(size, 700)
    for seg, col in WM_SEGS:
        draw.text((x, y), seg, font=fb, fill=col)
        x += tw(draw, seg, fb)
    return x


# ---- Shared chrome ----
def base_canvas():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, TOP_BAR_H - 1], fill=CRIMSON)
    return img, draw


def header(draw, right_tag):
    wordmark(draw, M, M, 34)
    if right_tag:
        caps(draw, 0, M + 10, right_tag, size=23, fill=SLATE, anchor_right=W - M)
    draw.rectangle([M, HEADER_RULE_Y, W - M, HEADER_RULE_Y + 2], fill=HAIRLINE)


def footer(draw, date_str):
    draw.rectangle([M, FOOTER_RULE_Y, W - M, FOOTER_RULE_Y + 2], fill=HAIRLINE)
    y = FOOTER_RULE_Y + 24
    draw.text((M, y), "decodepolitics.org", font=grotesk(30, 700), fill=SKY)
    draw.text((W - M, y + 4), date_str, font=inter(26), fill=SLATE, anchor="ra")


# ---- Portraits: square, thin keyline ----
def _square_photo(fname, side):
    path = os.path.join(PHOTOS, fname)
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        s = min(w, h)
        img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        return img.resize((side, side), Image.LANCZOS)
    except Exception:
        return Image.new("RGB", (side, side), TRACK)


def portrait_tile(fname, side, radius=8):
    ss = side * 4
    photo = _square_photo(fname, ss)
    tile = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ss - 1, ss - 1], radius * 4, fill=255)
    tile.paste(photo, (0, 0), mask)
    ImageDraw.Draw(tile).rounded_rectangle(
        [1, 1, ss - 2, ss - 2], radius * 4, outline=KEYLINE + (255,), width=6)
    return tile.resize((side, side), Image.LANCZOS)


# ---- Thin line bar ----
def line_bar(draw, x, y, w, frac, color, h=12):
    draw.rectangle([x, y, x + w, y + h], fill=TRACK)
    if frac > 0:
        draw.rectangle([x, y, x + max(6, int(frac * w)), y + h], fill=color)


# ---- Hero dollar figure: crimson $, white digits, crimson underline ----
def hero_amount(draw, x, y, amount, max_size, max_w):
    text = money(amount)
    fnt, size = fit_grotesk(draw, text, max_size, max_w, 700)
    draw.text((x, y), "$", font=fnt, fill=CRIMSON)
    dx = x + tw(draw, "$", fnt)
    draw.text((dx, y), text[1:], font=fnt, fill=WHITE)
    total_w = tw(draw, text, fnt)
    asc, desc = fnt.getmetrics()
    uy = y + asc + int(size * 0.10)
    draw.rectangle([x, uy, x + total_w, uy + 8], fill=CRIMSON)
    return total_w, size, uy + 8


# ---- Posts ----
_SUFFIXES = {"iii", "ii", "iv", "jr", "jr.", "sr", "sr."}


def member_post(row, rank, n, scale, body_label, source, out_path, date_str):
    img, draw = base_canvas()
    header(draw, "{:02d} / {:02d}".format(rank, n))

    # portrait, top right
    side = 264
    tile = portrait_tile(row["photo"], side)
    px = W - M - side
    img.paste(tile, (px, 208), tile)

    # eyebrow + name, left of portrait
    nw = px - M - 48
    caps(draw, M, 224, "{}  ·  {}".format(row["seat"], body_label),
         size=24, fill=SKY)
    name_lines = wrap(draw, row["name"], grotesk(76, 700), nw)
    if len(name_lines) > 2:
        name_lines = wrap(draw, row["name"], grotesk(58, 700), nw)
    if len(name_lines) > 1 and name_lines[-1].lower().strip(".") in _SUFFIXES:
        name_lines[-2:] = [name_lines[-2] + " " + name_lines[-1]]
    longest = max(name_lines, key=lambda ln: tw(draw, ln, grotesk(76, 700)))
    nf, ns = fit_grotesk(draw, longest, 76, nw, 700, min_size=40)
    y = 282
    for ln in name_lines:
        draw.text((M, y), ln, font=nf, fill=WHITE)
        y += int(ns * 1.12)

    # hero figure
    caps(draw, M, 552, "took from donors at these two firms", size=24, fill=SLATE)
    hero_amount(draw, M, 596, row["combined"], 190, CW)

    # firm rows: label left, amount right, thin bar beneath
    y = 906
    for key, label, col in (("endeavor", "Endeavor Real Estate Group", ENDEAVOR),
                            ("armbrust", "Armbrust & Brown, PLLC", ARMBRUST)):
        val = row[key]["total"]
        draw.text((M, y), label, font=inter(33, 600), fill=WHITE)
        draw.text((W - M, y - 8), money(val), font=grotesk(46, 500),
                  fill=(col if val else SLATE), anchor="ra")
        line_bar(draw, M, y + 60, CW, val / scale, col)
        y += 144

    # caption: span + contributions + donors
    n_contrib = row["endeavor"]["n"] + row["armbrust"]["n"]
    n_donors = row["endeavor"]["donors"] + row["armbrust"]["donors"]
    parts = [span_text(row["span_min"], row["span_max"])]
    if n_contrib:
        parts.append("{} contribution{}".format(n_contrib, "" if n_contrib == 1 else "s"))
        parts.append("{} donor{}".format(n_donors, "" if n_donors == 1 else "s"))
    draw.text((M, 1150), "  ·  ".join(parts), font=inter(29), fill=SLATE)

    # source note, <= 2 lines
    note = ("Itemized contributions whose reported employer is the firm · {} · "
            "bars scaled to the pack maximum".format(source))
    nf22 = inter(22)
    ny = 1198
    for ln in wrap(draw, note, nf22, CW)[:2]:
        draw.text((M, ny), ln, font=nf22, fill=FAINT)
        ny += 28

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def last_name(name):
    toks = [t for t in name.split() if t.lower().strip(",") not in _SUFFIXES]
    return toks[-1] if toks else name


def intro_post(rows, title, combined_total, cols, right_tag, out_path, date_str):
    img, draw = base_canvas()
    header(draw, right_tag)

    caps(draw, M, 208, "Follow the money  ·  All-time", size=24, fill=SKY)

    tf = grotesk(76, 700)
    tlines = wrap(draw, title, tf, CW)
    y = 250
    for ln in tlines:
        draw.text((M, y), ln, font=tf, fill=WHITE)
        y += 88

    # hero total
    y += 18
    _, hs, hb = hero_amount(draw, M, y, combined_total, 150, CW)
    sub = ("in contributions from donors at Endeavor Real Estate Group "
           "and Armbrust & Brown, PLLC.")
    sf = inter(31)
    sy = hb + 26
    for ln in wrap(draw, sub, sf, CW):
        draw.text((M, sy), ln, font=sf, fill=SLATE)
        sy += 42

    # roster grid — square tiles, name + seat below
    gap = 18 if cols >= 6 else 28
    label_h = 58
    n = len(rows)
    rows_n = -(-n // cols)
    gy0 = sy + 34
    avail = (FOOTER_RULE_Y - 20) - gy0
    tile_w = min((CW - (cols - 1) * gap) // cols,
                 (avail + 24) // rows_n - (label_h + 24))
    pitch_y = tile_w + label_h + 24
    grid_h = rows_n * pitch_y - 24
    gy0 += max(0, (avail - grid_h) // 2)

    name_f = grotesk(24, 500)
    seat_f = inter(20)
    for i, r in enumerate(rows):
        gx = M + (i % cols) * (tile_w + gap)
        gy = gy0 + (i // cols) * pitch_y
        tile = portrait_tile(r["photo"], tile_w)
        img.paste(tile, (gx, gy), tile)
        ln = last_name(r["name"])
        lf = name_f if tw(draw, ln, name_f) <= tile_w else \
            fit_grotesk(draw, ln, 24, tile_w, 500, min_size=13)[0]
        draw.text((gx, gy + tile_w + 10), ln, font=lf, fill=WHITE)
        draw.text((gx, gy + tile_w + 38), r["seat"], font=seat_f, fill=SLATE)

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def outro_post(rows, subtitle, right_tag, out_path, date_str):
    img, draw = base_canvas()
    header(draw, right_tag)

    caps(draw, M, 226, "Follow the money", size=24, fill=SKY)
    wordmark(draw, M, 272, 68)
    draw.text((M, 384), subtitle, font=inter(34), fill=SLATE)

    # stat ledger: hairline-separated rows, value left, label right
    total = sum(r["combined"] for r in rows)
    n_contrib = sum(r["endeavor"]["n"] + r["armbrust"]["n"] for r in rows)
    stats = (("{}".format(len(rows)), "Seats"),
             (money(total), "From both firms' donors"),
             ("{:,}".format(n_contrib), "Contributions traced"))
    y = 478
    row_h = 118
    for val, lab in stats:
        draw.rectangle([M, y, W - M, y + 2], fill=HAIRLINE)
        draw.text((M, y + 24), val, font=grotesk(62, 700), fill=WHITE)
        caps(draw, 0, y + 50, lab, size=23, fill=SLATE, anchor_right=W - M)
        y += row_h
    draw.rectangle([M, y, W - M, y + 2], fill=HAIRLINE)

    # CTA — typographic, crimson underline
    y += 76
    draw.text((M, y), "See every donor at", font=inter(34), fill=WHITE)
    uy = y + 58
    url_f = grotesk(58, 700)
    draw.text((M, uy), "decodepolitics.org", font=url_f, fill=SKY)
    uw = tw(draw, "decodepolitics.org", url_f)
    draw.rectangle([M, uy + 80, M + uw, uy + 86], fill=CRIMSON)
    draw.text((M, uy + 120), "Every filing pulled, every dollar matched to its donor.",
              font=inter(29), fill=SLATE)

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def slug(name, seat):
    ascii_last = unicodedata.normalize("NFKD", last_name(name)) \
        .encode("ascii", "ignore").decode()
    last = re.sub(r"[^a-z]", "", ascii_last.lower())
    s = re.sub(r"[^a-z0-9]", "", seat.lower())
    return "{}_{}".format(last, s)


def render_package(rows, subdir, intro_title, outro_sub, cols,
                   body_label, right_tag, source, date_str):
    dpath = os.path.join(OUT, subdir)
    os.makedirs(dpath, exist_ok=True)
    files = []
    combined_total = sum(r["combined"] for r in rows)
    scale = max([max(r["endeavor"]["total"], r["armbrust"]["total"]) for r in rows] + [1.0])

    p = os.path.join(dpath, "01_intro.png")
    intro_post(rows, intro_title, combined_total, cols, right_tag, p, date_str)
    files.append(p)

    for i, row in enumerate(rows, start=2):
        fn = "{:02d}_{}.png".format(i, slug(row["name"], row["seat"]))
        p = os.path.join(dpath, fn)
        member_post(row, i - 1, len(rows), scale, body_label, source, p, date_str)
        files.append(p)

    p = os.path.join(dpath, "{:02d}_outro.png".format(len(rows) + 2))
    outro_post(rows, outro_sub, right_tag, p, date_str)
    files.append(p)
    return files


def main():
    austin = build(AUSTIN)
    travis = build(TRAVIS)

    date_str = "July 2026"
    os.makedirs(OUT, exist_ok=True)

    af = render_package(
        austin, "austin",
        "Who's funding Austin City Council?",
        "Austin campaign finance, decoded.",
        6, "Austin City Council", "Austin City Council",
        "Source: published filings at decodepolitics.org/austin",
        date_str)

    tf = render_package(
        travis, "travis",
        "Who's funding Travis County?",
        "Travis County campaign finance, decoded.",
        5, "Travis County", "Travis County",
        "Source: published filings at decodepolitics.org",
        date_str)

    print("Output folder:", OUT)
    for label, files in (("AUSTIN (13)", af), ("TRAVIS (7)", tf)):
        print("\n" + label)
        for p in files:
            sz = os.path.getsize(p)
            print("  {:<28s} {:>8.1f} KB".format(os.path.basename(p), sz / 1024))


if __name__ == "__main__":
    main()
