#!/usr/bin/env python3
"""
generate_instagram_posts.py — Instagram post package generator (design v3).

Renders two Instagram-ready post packages (1080x1350 PNG, portrait feed size)
summarizing all-time campaign contributions received from Endeavor Real Estate
Group and Armbrust & Brown, PLLC, using the SAME data, rosters, firm-match
rules and portrait assets as generate_pdfs.py.

  Package 1 — Austin City Council        -> instagram_posts/austin/  (13 PNGs)
  Package 2 — Travis Commissioners Court -> instagram_posts/travis/  ( 7 PNGs)

All match logic / SQL / totals are imported verbatim from generate_pdfs.py
(DO NOT re-derive). Reads austin_finance.db read-only. No network access.

Design system: see INSTAGRAM_DESIGN_SPEC_V3.md ("Editorial"). White canvas,
left-aligned single column, small wordmark, hairline rules, one huge number
per member post, 10px line bars, crimson as accent only. No site-chrome
framing, no shadows, no pills, no cursor bar.
"""
import os
import re
import sqlite3

from PIL import Image, ImageDraw, ImageFont

# ---- Reuse everything from the PDF generator (rosters, match rules, totals) ----
from generate_pdfs import (
    AUSTIN, TRAVIS, build, load_firm_people, money, span_text, DB, PHOTOS,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "instagram_posts")

# ---- Canvas ----
W, H = 1080, 1350
M = 84                    # margin, all sides
CW = W - 2 * M            # 912 content width
DPI = (300, 300)

HEADER_RULE_Y = 152
FOOTER_RULE_Y = 1258

# ---- Palette (site CSS: index.html) ----
INK      = (12, 26, 44)      # #0c1a2c
NAVY     = (24, 49, 79)      # #18314f
CRIMSON  = (204, 31, 60)     # #cc1f3c
MUTED    = (91, 107, 122)    # #5b6b7a
HAIRLINE = (221, 228, 236)   # navy @ ~12% on white
TRACK    = (238, 241, 245)   # bar track
KEYLINE  = (200, 209, 220)   # portrait keyline
WHITE    = (255, 255, 255)

# ---- Fonts ----
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
BAHN = os.path.join(FONTS, "bahnschrift.ttf")     # variable; ~ Space Grotesk
SEGOE = os.path.join(FONTS, "segoeui.ttf")        # ~ Inter
SEGOE_SB = os.path.join(FONTS, "seguisb.ttf")
_cache = {}


def bahn(size, instance="SemiBold"):
    key = ("b", size, instance)
    if key not in _cache:
        f = ImageFont.truetype(BAHN, size)
        f.set_variation_by_name(instance)
        _cache[key] = f
    return _cache[key]


def segoe(size, semibold=False):
    key = ("s", size, semibold)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(SEGOE_SB if semibold else SEGOE, size)
    return _cache[key]


def tw(draw, text, fnt):
    return draw.textlength(text, font=fnt)


def fit_bahn(draw, text, max_size, max_w, instance="Bold", min_size=20):
    s = max_size
    while s > min_size and tw(draw, text, bahn(s, instance)) > max_w:
        s -= 2
    return bahn(s, instance), s


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


# ---- Tracked caps labels (small only — 0.12em, never hero-sized) ----
def caps(draw, x, y, text, size=25, fill=MUTED, tr_em=0.12, anchor_right=None):
    fnt = bahn(size, "SemiBold")
    text = text.upper()
    tr = size * tr_em
    total = sum(tw(draw, c, fnt) for c in text) + tr * max(0, len(text) - 1)
    if anchor_right is not None:
        x = anchor_right - total
    for c in text:
        draw.text((x, y), c, font=fnt, fill=fill)
        x += tw(draw, c, fnt) + tr
    return total


# ---- Wordmark: decode(crimson) ( navy politics ink ) navy : crimson — no cursor ----
WM_SEGS = (("decode", CRIMSON), ("(", NAVY), ("politics", INK), (")", NAVY),
           (":", CRIMSON))


def wordmark_w(draw, size):
    fb = bahn(size, "Bold")
    return tw(draw, "decode(politics):", fb)


def wordmark(draw, x, y, size):
    """Top-left anchored. Returns end x."""
    fb = bahn(size, "Bold")
    for seg, col in WM_SEGS:
        draw.text((x, y), seg, font=fb, fill=col)
        x += tw(draw, seg, fb)
    return x


# ---- Shared chrome ----
def header(draw, right_tag):
    wordmark(draw, M, M, 34)
    if right_tag:
        caps(draw, 0, M + 8, right_tag, size=24, fill=MUTED, anchor_right=W - M)
    draw.rectangle([M, HEADER_RULE_Y, W - M, HEADER_RULE_Y + 2], fill=HAIRLINE)


def footer(draw, date_str):
    draw.rectangle([M, FOOTER_RULE_Y, W - M, FOOTER_RULE_Y + 2], fill=HAIRLINE)
    y = FOOTER_RULE_Y + 24
    draw.text((M, y), "decodepolitics.org", font=bahn(30, "SemiBold"), fill=NAVY)
    draw.text((W - M, y + 3), date_str, font=segoe(26), fill=MUTED, anchor="ra")


def base_canvas():
    img = Image.new("RGB", (W, H), WHITE)
    return img, ImageDraw.Draw(img)


# ---- Portraits: square, 6px radius, thin keyline, no shadow ----
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


def portrait_tile(fname, side, radius=6):
    ss = side * 4
    photo = _square_photo(fname, ss)
    tile = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ss - 1, ss - 1], radius * 4, fill=255)
    tile.paste(photo, (0, 0), mask)
    ImageDraw.Draw(tile).rounded_rectangle(
        [1, 1, ss - 2, ss - 2], radius * 4, outline=KEYLINE + (255,), width=4)
    return tile.resize((side, side), Image.LANCZOS)


# ---- Thin line bar ----
def line_bar(draw, x, y, w, frac, color, h=10):
    draw.rectangle([x, y, x + w, y + h], fill=TRACK)
    if frac > 0:
        draw.rectangle([x, y, x + max(4, int(frac * w)), y + h], fill=color)


# ---- Posts ----
def member_post(row, rank, n, scale, body_label, source, out_path, date_str):
    img, draw = base_canvas()
    header(draw, "{:02d} / {:02d}".format(rank, n))

    # portrait, left
    side = 300
    tile = portrait_tile(row["photo"], side)
    img.paste(tile, (M, 216), tile)

    # right column: eyebrow + name
    nx = M + side + 44
    nw = W - M - nx
    caps(draw, nx, 236, "{}  ·  {}".format(row["seat"], body_label),
         size=25, fill=CRIMSON)
    name_lines = wrap(draw, row["name"], bahn(72, "Bold"), nw)
    if len(name_lines) > 2:
        name_lines = wrap(draw, row["name"], bahn(56, "Bold"), nw)
    # never leave a suffix (III, Jr., ...) alone on its own line
    if len(name_lines) > 1 and name_lines[-1].lower().strip(".") in _SUFFIXES:
        name_lines[-2:] = [name_lines[-2] + " " + name_lines[-1]]
    longest = max(name_lines, key=lambda ln: tw(draw, ln, bahn(72, "Bold")))
    nf, ns = fit_bahn(draw, longest, 72, nw, "Bold", min_size=40)
    y = 290
    for ln in name_lines:
        draw.text((nx, y), ln, font=nf, fill=INK)
        y += int(ns * 1.12)

    # combined hero number, full width
    caps(draw, M, 596, "Combined from both firms", size=24, fill=MUTED)
    combo = money(row["combined"])
    cf, cs = fit_bahn(draw, combo, 165, CW, "Bold")
    draw.text((M, 636), combo, font=cf, fill=NAVY)

    draw.rectangle([M, 866, W - M, 868], fill=HAIRLINE)

    # firm rows: label left, amount right, thin bar beneath
    y = 906
    for key, label, col in (("endeavor", "Endeavor Real Estate Group", NAVY),
                            ("armbrust", "Armbrust & Brown, PLLC", CRIMSON)):
        val = row[key]["total"]
        draw.text((M, y), label, font=segoe(33, True), fill=INK)
        draw.text((W - M, y - 8), money(val), font=bahn(46, "SemiBold"),
                  fill=col, anchor="ra")
        line_bar(draw, M, y + 62, CW, val / scale, col)
        y += 146

    # caption: span + contribution count
    n_contrib = row["endeavor"]["n"] + row["armbrust"]["n"]
    span = span_text(row["span_min"], row["span_max"])
    cap = span + ("  ·  {} contribution{}".format(
        n_contrib, "" if n_contrib == 1 else "s") if n_contrib else "")
    draw.text((M, 1152), cap, font=segoe(29), fill=MUTED)

    # source note, <= 2 lines
    note = ("Monetary + in-kind where the donor, employer, or occupation matches "
            "the firm · {} · bars scaled to the pack maximum".format(source))
    nf22 = segoe(22)
    ny = 1198
    for ln in wrap(draw, note, nf22, CW)[:2]:
        draw.text((M, ny), ln, font=nf22, fill=MUTED)
        ny += 28

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


_SUFFIXES = {"iii", "ii", "iv", "jr", "jr.", "sr", "sr."}


def last_name(name):
    toks = [t for t in name.split() if t.lower().strip(",") not in _SUFFIXES]
    return toks[-1] if toks else name


def intro_post(rows, title, combined_total, cols, right_tag, out_path, date_str):
    img, draw = base_canvas()
    header(draw, right_tag)

    caps(draw, M, 210, "Follow the money  ·  All-time", size=25, fill=CRIMSON)

    tf = bahn(84, "Bold")
    tlines = wrap(draw, title, tf, CW)
    y = 254
    for ln in tlines:
        draw.text((M, y), ln, font=tf, fill=INK)
        y += 96

    sub = ("{} in contributions from Endeavor Real Estate Group and "
           "Armbrust & Brown, PLLC.".format(money(combined_total)))
    sf = segoe(32)
    y += 14
    for ln in wrap(draw, sub, sf, CW):
        draw.text((M, y), ln, font=sf, fill=MUTED)
        y += 44

    # roster grid — square tiles, name + seat below, trailing cells stay empty
    gap = 20 if cols == 4 else 28
    label_h = 62
    n = len(rows)
    rows_n = -(-n // cols)
    gy0 = y + 30
    avail = (FOOTER_RULE_Y - 20) - gy0
    tile_w = min((CW - (cols - 1) * gap) // cols,
                 (avail + 24) // rows_n - (label_h + 24))
    pitch_y = tile_w + label_h + 24
    grid_h = rows_n * pitch_y - 24
    gy0 += max(0, (avail - grid_h) // 2)

    name_f = bahn(26, "SemiBold")
    seat_f = segoe(22)
    for i, r in enumerate(rows):
        gx = M + (i % cols) * (tile_w + gap)
        gy = gy0 + (i // cols) * pitch_y
        tile = portrait_tile(r["photo"], tile_w)
        img.paste(tile, (gx, gy), tile)
        ln = last_name(r["name"])
        lf = name_f if tw(draw, ln, name_f) <= tile_w else \
            fit_bahn(draw, ln, 26, tile_w, "SemiBold Condensed")[0]
        draw.text((gx, gy + tile_w + 10), ln, font=lf, fill=INK)
        draw.text((gx, gy + tile_w + 40), r["seat"], font=seat_f, fill=MUTED)

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def outro_post(rows, subtitle, right_tag, out_path, date_str):
    img, draw = base_canvas()
    header(draw, right_tag)

    caps(draw, M, 232, "Follow the money", size=25, fill=CRIMSON)
    wordmark(draw, M, 278, 72)
    draw.text((M, 392), subtitle, font=segoe(34), fill=MUTED)

    # stat ledger: hairline-separated rows, value left, label right
    total = sum(r["combined"] for r in rows)
    n_contrib = sum(r["endeavor"]["n"] + r["armbrust"]["n"] for r in rows)
    stats = (("{}".format(len(rows)), "Seats"),
             (money(total), "Combined from both firms"),
             ("{:,}".format(n_contrib), "Contributions traced"))
    y = 486
    row_h = 118
    for val, lab in stats:
        draw.rectangle([M, y, W - M, y + 2], fill=HAIRLINE)
        draw.text((M, y + 26), val, font=bahn(64, "Bold"), fill=NAVY)
        caps(draw, 0, y + 50, lab, size=24, fill=MUTED, anchor_right=W - M)
        y += row_h
    draw.rectangle([M, y, W - M, y + 2], fill=HAIRLINE)

    # CTA — typographic, no pill
    y += 78
    draw.text((M, y), "See every donor at", font=segoe(34), fill=INK)
    uy = y + 58
    url_f = bahn(60, "Bold")
    draw.text((M, uy), "decodepolitics.org", font=url_f, fill=NAVY)
    uw = tw(draw, "decodepolitics.org", url_f)
    draw.rectangle([M, uy + 82, M + uw, uy + 88], fill=CRIMSON)
    draw.text((M, uy + 122), "Every filing pulled, every dollar matched to its donor.",
              font=segoe(29), fill=MUTED)

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def slug(recip, seat):
    last = recip.split(",")[0].strip().lower()
    last = re.sub(r"[^a-z]", "", last)
    s = re.sub(r"[^a-z0-9]", "", seat.lower())
    return "{}_{}".format(last, s)


def render_package(rows, roster, subdir, intro_title, outro_sub, cols,
                   body_label, right_tag, source, date_str):
    dpath = os.path.join(OUT, subdir)
    os.makedirs(dpath, exist_ok=True)
    files = []
    combined_total = sum(r["combined"] for r in rows)
    scale = max([max(r["endeavor"]["total"], r["armbrust"]["total"]) for r in rows] + [1.0])

    p = os.path.join(dpath, "01_intro.png")
    intro_post(rows, intro_title, combined_total, cols, right_tag, p, date_str)
    files.append(p)

    recip_of = {r[0]: r[2] for r in roster}
    for i, row in enumerate(rows, start=2):
        recip = recip_of[row["name"]]
        fn = "{:02d}_{}.png".format(i, slug(recip, row["seat"]))
        p = os.path.join(dpath, fn)
        member_post(row, i - 1, len(rows), scale, body_label, source, p, date_str)
        files.append(p)

    p = os.path.join(dpath, "{:02d}_outro.png".format(len(rows) + 2))
    outro_post(rows, outro_sub, right_tag, p, date_str)
    files.append(p)
    return files


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    load_firm_people(cur)
    austin = build(cur, AUSTIN)
    travis = build(cur, TRAVIS)
    conn.close()

    date_str = "July 2026"
    os.makedirs(OUT, exist_ok=True)

    af = render_package(
        austin, AUSTIN, "austin",
        "Who's funding Austin City Council?",
        "Austin campaign finance, decoded.",
        4, "Austin City Council", "Austin City Council",
        "Source: City of Austin campaign finance dataset (data.austintexas.gov)",
        date_str)

    tf = render_package(
        travis, TRAVIS, "travis",
        "Who's funding Travis County?",
        "Travis County campaign finance, decoded.",
        3, "Travis County", "Travis County",
        "Source: Travis County campaign finance filings",
        date_str)

    print("Output folder:", OUT)
    for label, files in (("AUSTIN (13)", af), ("TRAVIS (7)", tf)):
        print("\n" + label)
        for p in files:
            sz = os.path.getsize(p)
            print("  {:<28s} {:>8.1f} KB".format(os.path.basename(p), sz / 1024))


if __name__ == "__main__":
    main()
