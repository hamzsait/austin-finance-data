#!/usr/bin/env python3
"""
generate_instagram_posts.py — Instagram post package generator (design v5).

Renders two Instagram-ready post packages (1080x1350 PNG, portrait feed size)
summarizing all-time campaign contributions received from donors employed in
the REAL ESTATE industry — the single largest donor industry for most of the
officials covered.

  Package 1 — Austin City Council        -> instagram_posts/austin/  (13 PNGs)
  Package 2 — Travis Commissioners Court -> instagram_posts/travis/  ( 7 PNGs)

Data source (v5): the SAME published tables that power decodepolitics.org.
  - The hero figure and donor count are the site's own "Real Estate"
    interest-group rollup from <slug>_data.json, shown VERBATIM — a posted
    number always equals what the live profile page renders.
  - Contribution counts, date spans, and the audit trail come from the
    committed <slug>_all_donations.json rows (donor, date, amount,
    employer-identity, industry, location) filtered to industry ==
    "Real Estate". The script asserts the row sum reconciles with the site
    rollup to within $1 (rollups round to whole dollars).
  - The industry-rank eyebrow cross-checks <slug>_data.json -> hero ->
    top_industry, another figure the site publishes.

Alongside the PNGs the script writes instagram_posts/AUDIT_REAL_ESTATE.md —
every single donation behind every posted number, per official, reconciled
row-by-row to the posted totals.

Design system: see INSTAGRAM_DESIGN_SPEC_V5.md ("Statement"). Ink-navy canvas,
crimson top edge, giant all-white hero dollar figure with crimson underline,
brand fonts (Space Grotesk / Inter / Oswald from assets/fonts/). One data
color (#4a96d8 blue) for the official's own bar; the pack-reference bar is
muted slate. Bars are scaled to the pack's highest real-estate total
(Kirk Watson on the council, Andy Brown on the commissioners court).
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

INDUSTRY = "Real Estate"

# Employment-status buckets the site's top_industry stat skips; excluded when
# deriving the rank shown in the eyebrow so rank #1 always agrees with the
# site's published top_industry field (asserted in build()).
NON_INDUSTRY = {"Not Employed", "Self-Employed", "Unknown", "Retired",
                "Family", "Student"}


def parse_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def build(roster):
    rows = []
    for name, seat, slug_, photo in roster:
        site = json.load(open(os.path.join(HERE, slug_ + "_data.json")))
        group = next((g for g in site["interest_groups"]
                      if g["label"] == INDUSTRY), None)
        if group is None:
            raise SystemExit("{}: no '{}' interest group on the site data"
                             .format(slug_, INDUSTRY))

        donations = [r for r in
                     json.load(open(os.path.join(HERE, slug_ + "_all_donations.json")))
                     if r[4] == INDUSTRY]
        row_sum = round(sum(r[2] for r in donations), 2)
        if abs(row_sum - group["total"]) > 1.0:
            raise SystemExit(
                "{}: site rollup ${:,} does not reconcile with row sum ${:,.2f}"
                .format(slug_, group["total"], row_sum))

        ranked = sorted((g for g in site["interest_groups"]
                         if g["label"] not in NON_INDUSTRY),
                        key=lambda g: -g["total"])
        rank = next(i for i, g in enumerate(ranked, 1)
                    if g["label"] == INDUSTRY)
        top = site["hero"].get("top_industry")
        if (rank == 1) != (top == INDUSTRY):
            raise SystemExit("{}: derived rank #{} disagrees with site "
                             "top_industry '{}'".format(slug_, rank, top))

        dates = [d for d in (parse_date(r[1]) for r in donations) if d]
        rows.append({
            "name": name, "seat": seat, "photo": photo, "slug": slug_,
            "total": float(group["total"]),   # site-verbatim
            "donors": group["donors"],        # site-verbatim
            "n": len(donations),
            "rank": rank,
            "row_sum": row_sum,
            "donations": donations,
            "span_min": min(dates) if dates else None,
            "span_max": max(dates) if dates else None,
        })
    # keep roster order: Mayor/County Judge first, then districts/precincts
    return rows


def money(v):
    return "$0" if not v else "${:,.0f}".format(v)


def ordinal_rank(rank):
    return "#{}".format(rank)


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

# ---- Palette (dark; data blue validated for CVD + contrast on BG) ----
BG       = (12, 26, 44)      # #0c1a2c ink navy
WHITE    = (245, 248, 251)   # #f5f8fb primary text
SKY      = (200, 224, 244)   # #c8e0f4 brand sky
SLATE    = (143, 163, 184)   # #8fa3b8 muted
FAINT    = (104, 124, 146)   # #687c92 source notes
CRIMSON  = (232, 83, 107)    # #e8536b accent (bright-for-dark)
RE_BLUE  = (74, 150, 216)    # #4a96d8 the official's own bar
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
def caps_width(draw, text, size, tr_em=0.18):
    fnt = oswald(size, 600)
    text = text.upper()
    tr = size * tr_em
    return sum(tw(draw, c, fnt) for c in text) + tr * max(0, len(text) - 1)


def caps(draw, x, y, text, size=25, fill=SLATE, tr_em=0.18, anchor_right=None):
    fnt = oswald(size, 600)
    text = text.upper()
    tr = size * tr_em
    total = caps_width(draw, text, size, tr_em)
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
    """Square-crop a headshot. Tall photos crop top-weighted (faces live in the
    upper part of a portrait — a center crop chops foreheads); wide photos crop
    horizontally centered. Per-photo overrides tune the window when needed."""
    path = os.path.join(PHOTOS, fname)
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        s = min(w, h)
        if h > w:
            top = int((h - s) * CROP_TOP_BIAS.get(fname, 0.10))
            img = img.crop((0, top, s, top + s))
        else:
            left = (w - s) // 2
            img = img.crop((left, 0, left + s, s))
        return img.resize((side, side), Image.LANCZOS)
    except Exception:
        return Image.new("RGB", (side, side), TRACK)


# vertical crop-window bias for tall photos: 0.0 = flush top, 0.5 = centered
CROP_TOP_BIAS = {}


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


# ---- Hero dollar figure: white $ and digits, crimson underline ----
def hero_amount(draw, x, y, amount, max_size, max_w):
    text = money(amount)
    fnt, size = fit_grotesk(draw, text, max_size, max_w, 700)
    draw.text((x, y), text, font=fnt, fill=WHITE)
    total_w = tw(draw, text, fnt)
    # underline clears the actual ink bbox (commas descend below the baseline)
    ink_bottom = draw.textbbox((x, y), text, font=fnt)[3]
    uy = ink_bottom + int(size * 0.10)
    draw.rectangle([x, uy, x + total_w, uy + 8], fill=CRIMSON)
    return total_w, size, uy + 8


# ---- Posts ----
_SUFFIXES = {"iii", "ii", "iv", "jr", "jr.", "sr", "sr."}


def member_post(row, rank, n, body_label, source, out_path, date_str):
    img, draw = base_canvas()
    header(draw, "{:02d} / {:02d}".format(rank, n))

    # portrait, top right
    side = 340
    tile = portrait_tile(row["photo"], side)
    px = W - M - side
    img.paste(tile, (px, 208), tile)

    # eyebrow + name, left of portrait
    nw = px - M - 48
    eyebrow = "{}  ·  {}".format(row["seat"], body_label)
    esz = 26
    while esz > 18 and caps_width(draw, eyebrow, esz) > nw:
        esz -= 1
    caps(draw, M, 224, eyebrow, size=esz, fill=SKY)
    name_lines = wrap(draw, row["name"], grotesk(84, 700), nw)
    if len(name_lines) > 2:
        name_lines = wrap(draw, row["name"], grotesk(64, 700), nw)
    if len(name_lines) > 1 and name_lines[-1].lower().strip(".") in _SUFFIXES:
        name_lines[-2:] = [name_lines[-2] + " " + name_lines[-1]]
    longest = max(name_lines, key=lambda ln: tw(draw, ln, grotesk(84, 700)))
    nf, ns = fit_grotesk(draw, longest, 84, nw, 700, min_size=40)
    y = 288
    for ln in name_lines:
        draw.text((M, y), ln, font=nf, fill=WHITE)
        y += int(ns * 1.12)

    # hero label: what the figure is + where real estate ranks for them
    lead = "took from real estate donors"
    rank_tag = "· their {} donor industry".format(ordinal_rank(row["rank"]))
    sz = 27
    while sz > 18 and (caps_width(draw, lead, sz) + 24
                       + caps_width(draw, rank_tag, sz)) > CW:
        sz -= 1
    lw = caps(draw, M, 660, lead, size=sz, fill=SLATE)
    caps(draw, M + lw + 24, 660, rank_tag, size=sz,
         fill=(SKY if row["rank"] == 1 else SLATE))
    hero_amount(draw, M, 712, row["total"], 225, CW)

    # caption: span + contributions + donors (donor count is site-verbatim)
    parts = [span_text(row["span_min"], row["span_max"])]
    if row["n"]:
        parts.append("{} contribution{}".format(row["n"], "" if row["n"] == 1 else "s"))
        parts.append("{} donor{}".format(row["donors"], "" if row["donors"] == 1 else "s"))
    draw.text((M, 1128), "  ·  ".join(parts), font=inter(33), fill=SLATE)

    # source note, <= 2 lines
    note = ("Itemized contributions whose donor's employer is classified "
            "Real Estate · {}".format(source))
    nf24 = inter(24)
    ny = 1188
    for ln in wrap(draw, note, nf24, CW)[:2]:
        draw.text((M, ny), ln, font=nf24, fill=FAINT)
        ny += 31

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def last_name(name):
    toks = [t for t in name.split() if t.lower().strip(",") not in _SUFFIXES]
    return toks[-1] if toks else name


def intro_post(rows, title, combined_total, sub, cols, right_tag, out_path,
               date_str):
    """title is a list of (text, color) segments, wrapped word by word —
    e.g. Real Estate in crimson, the body name in blue, the rest white."""
    img, draw = base_canvas()
    header(draw, right_tag)

    caps(draw, M, 208, "Follow the money", size=24, fill=SKY)

    tf = grotesk(76, 700)
    words = [(w, col) for seg, col in title for w in seg.split()]
    space_w = tw(draw, " ", tf)
    x, y = M, 250
    for word, col in words:
        ww = tw(draw, word, tf)
        if x > M and x + ww > M + CW:
            x, y = M, y + 88
        draw.text((x, y), word, font=tf, fill=col)
        x += ww + space_w
    y += 88

    # hero total
    y += 18
    _, hs, hb = hero_amount(draw, M, y, combined_total, 150, CW)
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
    total = sum(r["total"] for r in rows)
    n_contrib = sum(r["n"] for r in rows)
    stats = (("{}".format(len(rows)), "Seats"),
             (money(total), "From real estate donors"),
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

    # methodology disclaimer — these totals are a deliberate undercount
    disc = ("These totals are deliberately conservative — an undercount. Real "
            "estate money also arrives through spouses, family members, and "
            "donors who list no employer; we count only contributions whose "
            "reported employer verifiably places the donor in the industry.")
    df = inter(24)
    dy = uy + 186
    for ln in wrap(draw, disc, df, CW):
        draw.text((M, dy), ln, font=df, fill=FAINT)
        dy += 32

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def slug(name, seat):
    ascii_last = unicodedata.normalize("NFKD", last_name(name)) \
        .encode("ascii", "ignore").decode()
    last = re.sub(r"[^a-z]", "", ascii_last.lower())
    s = re.sub(r"[^a-z0-9]", "", seat.lower())
    return "{}_{}".format(last, s)


def render_package(rows, subdir, intro_title, outro_sub, cols, body_label,
                   right_tag, source, date_str):
    dpath = os.path.join(OUT, subdir)
    os.makedirs(dpath, exist_ok=True)
    files = []
    combined_total = sum(r["total"] for r in rows)
    n_top = sum(1 for r in rows if r["rank"] == 1)

    sub = ("in contributions from donors working in real estate — the #1 "
           "donor industry for {} of these {} officials."
           .format(n_top, len(rows)))
    p = os.path.join(dpath, "01_intro.png")
    intro_post(rows, intro_title, combined_total, sub, cols, right_tag, p,
               date_str)
    files.append(p)

    for i, row in enumerate(rows, start=2):
        fn = "{:02d}_{}.png".format(i, slug(row["name"], row["seat"]))
        p = os.path.join(dpath, fn)
        member_post(row, i - 1, len(rows), body_label, source, p, date_str)
        files.append(p)

    p = os.path.join(dpath, "{:02d}_outro.png".format(len(rows) + 2))
    outro_post(rows, outro_sub, right_tag, p, date_str)
    files.append(p)
    return files


# ---- Audit document ----
def write_audit(packages, date_str):
    """packages: list of (title, rows). Every posted figure, reconciled to the
    exact published donation rows that produce it."""
    path = os.path.join(OUT, "AUDIT_REAL_ESTATE.md")
    L = []
    L.append("# Real estate contributions — audit trail")
    L.append("")
    L.append("Generated by `generate_instagram_posts.py` (design v5), {}. "
             "This document accounts for every dollar shown in the Instagram "
             "post packages.".format(date_str))
    L.append("")
    L.append("## Method")
    L.append("")
    L.append("- A contribution counts as **real estate money** if and only if "
             "its `industry` field in the committed, published "
             "`<slug>_all_donations.json` table — the same donor table the "
             "live profile page at decodepolitics.org serves — equals "
             "`\"Real Estate\"`. No fuzzy matching, no manual additions.")
    L.append("- The **posted total and donor count** for each official are the "
             "site's own \"Real Estate\" interest-group rollup from "
             "`<slug>_data.json`, used verbatim, so every number on a post "
             "equals what the live profile page renders. The tables below "
             "reconcile each rollup to its underlying rows; site rollups are "
             "rounded to whole dollars, so a reconciliation difference of up "
             "to $1 can occur and is stated where it does.")
    L.append("- **Donor counts** are the site's count of distinct resolved "
             "donor identities. Distinct donor *name strings* in the rows "
             "below can be slightly fewer, because different people can share "
             "a printed name; both counts are given per official.")
    L.append("- The **industry rank** shown on each post orders the site's "
             "published interest groups by total, skipping the employment-"
             "status buckets ({}) that the site's own `top_industry` stat "
             "also skips; rank #1 is asserted to agree with the site's "
             "published `top_industry`.".format(", ".join(sorted(NON_INDUSTRY))))
    L.append("")

    for title, rows in packages:
        pkg_total = sum(r["total"] for r in rows)
        pkg_n = sum(r["n"] for r in rows)
        L.append("---")
        L.append("")
        L.append("# {}".format(title))
        L.append("")
        L.append("**Package total: {}** across {} seats · {:,} itemized "
                 "contributions.".format(money(pkg_total), len(rows), pkg_n))
        L.append("")
        L.append("| Official | Seat | Posted total | Sum of rows | Δ | Contributions | Donors (site) | Donor names in rows |")
        L.append("|---|---|---:|---:|---:|---:|---:|---:|")
        for r in rows:
            names = len(set(d[0] for d in r["donations"]))
            delta = r["total"] - r["row_sum"]
            L.append("| {} | {} | {} | ${:,.2f} | ${:+.2f} | {:,} | {:,} | {:,} |"
                     .format(r["name"], r["seat"], money(r["total"]),
                             r["row_sum"], delta, r["n"], r["donors"], names))
        L.append("")

        for r in rows:
            L.append("## {} — {}, {}".format(r["name"], r["seat"], title))
            L.append("")
            names = len(set(d[0] for d in r["donations"]))
            delta = r["total"] - r["row_sum"]
            L.append("- **Posted total: {}** — the \"Real Estate\" rollup "
                     "published in `{}_data.json` (the figure the live page "
                     "renders).".format(money(r["total"]), r["slug"]))
            L.append("- Sum of the {:,} rows below: **${:,.2f}**{}."
                     .format(r["n"], r["row_sum"],
                             "" if abs(delta) < 0.005 else
                             " — difference ${:+.2f} (site rollup rounds to "
                             "whole dollars)".format(delta)))
            L.append("- **Donors: {:,}** (site-resolved identities) · {:,} "
                     "distinct donor names in the rows.".format(r["donors"], names))
            L.append("- Span: {}.".format(span_text(r["span_min"], r["span_max"])))
            L.append("")
            L.append("| # | Date | Donor | Employer | Amount |")
            L.append("|---:|---|---|---|---:|")
            rows_sorted = sorted(
                r["donations"],
                key=lambda d: (parse_date(d[1]) or datetime.min, str(d[0] or "")))
            for i, d in enumerate(rows_sorted, 1):
                donor, date, amount, employer = d[0], d[1], d[2], d[3]
                esc = lambda s: str(s).replace("|", "\\|")
                L.append("| {} | {} | {} | {} | ${:,.2f} |".format(
                    i, str(date)[:10], esc(donor or "—"), esc(employer or "—"),
                    amount))
            L.append("| | | | **Total** | **${:,.2f}** |".format(r["row_sum"]))
            L.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return path


def main():
    austin = build(AUSTIN)
    travis = build(TRAVIS)

    date_str = "July 2026"
    os.makedirs(OUT, exist_ok=True)

    af = render_package(
        austin, "austin",
        [("How much is", WHITE), ("Real Estate", CRIMSON),
         ("funding the", WHITE), ("Austin City Council?", RE_BLUE)],
        "Austin campaign finance, decoded.",
        6, "Austin City Council", "Austin City Council",
        "Source: published filings at decodepolitics.org/austin",
        date_str)

    tf = render_package(
        travis, "travis",
        [("How much is", WHITE), ("Real Estate", CRIMSON),
         ("funding the", WHITE), ("Travis County Commissioners?", RE_BLUE)],
        "Travis County campaign finance, decoded.",
        5, "Travis County", "Travis County",
        "Source: published filings at decodepolitics.org",
        date_str)

    audit = write_audit(
        [("Austin City Council", austin),
         ("Travis County Commissioners Court", travis)], date_str)

    print("Output folder:", OUT)
    for label, files in (("AUSTIN (13)", af), ("TRAVIS (7)", tf)):
        print("\n" + label)
        for p in files:
            sz = os.path.getsize(p)
            print("  {:<28s} {:>8.1f} KB".format(os.path.basename(p), sz / 1024))
    print("\nAudit doc:", audit,
          "({:.1f} KB)".format(os.path.getsize(audit) / 1024))


if __name__ == "__main__":
    main()
