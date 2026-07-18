#!/usr/bin/env python3
"""
generate_instagram_posts.py — Instagram post package generator (design v2).

Renders two Instagram-ready post packages (1080x1350 PNG, portrait feed size)
summarizing all-time campaign contributions received from Endeavor Real Estate
Group and Armbrust & Brown, PLLC, using the SAME data, rosters, firm-match
rules and portrait assets as generate_pdfs.py.

  Package 1 — Austin City Council       -> instagram_posts/austin/  (13 PNGs)
  Package 2 — Travis Commissioners Court-> instagram_posts/travis/  ( 7 PNGs)

All match logic / SQL / totals are imported verbatim from generate_pdfs.py
(DO NOT re-derive). Reads austin_finance.db read-only. No network access.

Design system: see INSTAGRAM_DESIGN_SPEC.md. Highlights vs. v1:
  - Site-accurate wordmark (crimson colon; rounded cursor only at header size,
    none on hero wordmarks — matches assets/og/card.html).
  - Sky band + white browser-tab header and sky footer band (site chrome).
  - PDF-v3-style rounded navy/crimson bars on a light track, scaled to the
    pack maximum, on a light-sky panel.
  - Intro post = full roster portrait grid; outro = stats + mini roster + CTA.
  - Bahnschrift (variable) + Segoe UI in place of Space Grotesk/Oswald/Inter.
"""
import os
import re
import sqlite3

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---- Reuse everything from the PDF generator (rosters, match rules, totals) ----
from generate_pdfs import (
    AUSTIN, TRAVIS, build, load_firm_people, money, span_text, DB, PHOTOS,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "instagram_posts")
ASSETS = os.path.join(HERE, "assets")

# ---- Canvas ----
W, H = 1080, 1350
MARGIN = 72
CW = W - 2 * MARGIN
DPI = (300, 300)

BAND_H = 150          # sky header band
FOOT_H = 76           # sky footer band

# ---- Brand palette (decodepolitics.org: index.html / assets/og/card.html) ----
NAVY    = (24, 49, 79)      # #18314f
CRIMSON = (204, 31, 60)     # #cc1f3c
SKY     = (200, 224, 244)   # #c8e0f4  (site --sky)
SKY_PANEL = (231, 241, 249) # sky mixed toward white — bar panel
INK     = (12, 26, 44)      # #0c1a2c
MUTED   = (91, 107, 122)    # #5b6b7a
TRACK   = (234, 238, 243)   # bar track (PDF C_TRACK)
LINE    = (206, 216, 228)   # hairlines
WHITE   = (255, 255, 255)
DOT_NAVY, DOT_RED, DOT_AMBER = (24, 49, 79), (236, 58, 34), (245, 166, 35)

# ---- Fonts ----
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
BAHN = os.path.join(FONTS, "bahnschrift.ttf")       # ~ Space Grotesk / Oswald
SEGOE = os.path.join(FONTS, "segoeui.ttf")          # ~ Inter
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


def fit_bahn(draw, text, max_size, max_w, instance="SemiBold", min_size=20):
    s = max_size
    while s > min_size and tw(draw, text, bahn(s, instance)) > max_w:
        s -= 2
    return bahn(s, instance), s


def _wrap(draw, text, fnt, maxw):
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


# ---- Eyebrow labels (Oswald-style: condensed uppercase, tracked) ----
EYEBROW_INST = "SemiBold Condensed"


def tracked_w(draw, text, fnt, tr):
    if not text:
        return 0
    return sum(tw(draw, c, fnt) for c in text) + tr * (len(text) - 1)


def draw_tracked(draw, x, y, text, fnt, fill, tr, anchor_mid_x=None):
    if anchor_mid_x is not None:
        x = anchor_mid_x - tracked_w(draw, text, fnt, tr) / 2
    for c in text:
        draw.text((x, y), c, font=fnt, fill=fill)
        x += tw(draw, c, fnt) + tr


def eyebrow(draw, cx, y, text, size=30, fill=CRIMSON):
    fnt = bahn(size, EYEBROW_INST)
    draw_tracked(draw, 0, y, text.upper(), fnt, fill, tr=size * 0.18, anchor_mid_x=cx)


# ---- Wordmark: decode (crimson) + (politics) (navy) + : (crimson) ----
def wordmark_w(draw, size, cursor=False):
    fb = bahn(size, "SemiBold")
    w = tw(draw, "decode(politics):", fb)
    if cursor:
        w += size * 0.17 + size * 0.11
    return w


def wordmark(draw, x, cy, size, cursor=False):
    """Draw the wordmark left-aligned at x, vertically centered on cy."""
    fb = bahn(size, "SemiBold")
    for seg, col in (("decode", CRIMSON), ("(politics)", NAVY), (":", CRIMSON)):
        draw.text((x, cy), seg, font=fb, fill=col, anchor="lm")
        x += tw(draw, seg, fb)
    if cursor:
        # site CSS: 0.17em gap, 0.11em wide, ~0.94em tall, fully rounded
        cx0 = x + size * 0.17
        cw = max(4, size * 0.11)
        ch = size * 0.90
        draw.rounded_rectangle([cx0, cy - ch / 2, cx0 + cw, cy + ch / 2],
                               radius=cw / 2, fill=CRIMSON)
        x = cx0 + cw
    return x


# ---- Site chrome: sky band + white browser tab / sky footer band ----
def header(draw):
    draw.rectangle([0, 0, W, BAND_H], fill=SKY)
    # traffic dots (colors from index.html)
    dcy = BAND_H - 46
    for i, col in enumerate((DOT_NAVY, DOT_RED, DOT_AMBER)):
        cx = MARGIN + 9 + i * 32
        draw.ellipse([cx - 9, dcy - 9, cx + 9, dcy + 9], fill=col)
    # white tab, rounded top corners, flush with band bottom
    wm_size = 44
    pad = 34
    tx0 = MARGIN + 9 + 2 * 32 + 9 + 26
    tab_w = wordmark_w(draw, wm_size, cursor=True) + pad * 2
    draw.rounded_rectangle([tx0, BAND_H - 94, tx0 + tab_w, BAND_H + 24],
                           radius=22, fill=WHITE)
    wordmark(draw, tx0 + pad, BAND_H - 94 + 47, wm_size, cursor=True)


def footer(draw, date_str):
    draw.rectangle([0, H - FOOT_H, W, H], fill=SKY)
    cy = H - FOOT_H / 2
    draw.text((MARGIN, cy), "decodepolitics.org", font=segoe(30, True),
              fill=CRIMSON, anchor="lm")
    draw.text((W - MARGIN, cy), date_str, font=segoe(28), fill=MUTED, anchor="rm")


def base_canvas():
    img = Image.new("RGB", (W, H), WHITE)
    return img, ImageDraw.Draw(img)


# ---- Portraits ----
def _square_photo(fname, side):
    path = os.path.join(PHOTOS, fname)
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        s = min(w, h)
        img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        return img.resize((side, side), Image.LANCZOS)
    except Exception:
        return Image.new("RGB", (side, side), SKY)


def rounded_square(fname, side, radius=None):
    """Rounded-square portrait (supersampled) with a subtle navy outline."""
    radius = radius if radius is not None else int(side * 0.12)
    ss = side * 4
    photo = _square_photo(fname, ss)
    tile = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ss - 1, ss - 1], radius * 4, fill=255)
    tile.paste(photo, (0, 0), mask)
    ImageDraw.Draw(tile).rounded_rectangle([2, 2, ss - 3, ss - 3], radius * 4,
                                           outline=(24, 49, 79, 46), width=6)
    return tile.resize((side, side), Image.LANCZOS)


def circle_photo(fname, dia, ring=WHITE, ring_w=6):
    ss = dia * 4
    photo = _square_photo(fname, ss)
    tile = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, ss - 1, ss - 1], fill=255)
    tile.paste(photo, (0, 0), mask)
    ImageDraw.Draw(tile).ellipse([3, 3, ss - 4, ss - 4],
                                 outline=(24, 49, 79, 60), width=ring_w)
    return tile.resize((dia, dia), Image.LANCZOS)


def paste_portrait(img, fname, x, y, side, shadow=True):
    """Rounded-square portrait with a soft navy drop shadow, pasted at (x, y)."""
    pad = 48
    if shadow:
        sh = Image.new("RGBA", (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [pad, pad + 12, pad + side, pad + side + 12],
            int(side * 0.12), fill=(24, 49, 79, 64))
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        img.paste(sh, (x - pad, y - pad), sh)
    tile = rounded_square(fname, side)
    img.paste(tile, (x, y), tile)


def logomark_tile(side):
    """Navy rounded square with the '(:)' brand mark set in type (sky + crimson)."""
    tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.rounded_rectangle([0, 0, side - 1, side - 1], int(side * 0.12), fill=NAVY)
    f = bahn(int(side * 0.52), "SemiBold")
    segs = (("(", SKY), (":", CRIMSON), (")", SKY))
    total = sum(d.textlength(s, font=f) for s, _ in segs)
    x = (side - total) / 2
    for seg, col in segs:
        d.text((x, side * 0.47), seg, font=f, fill=col, anchor="lm")
        x += d.textlength(seg, font=f)
    return tile


# ---- Bars (PDF v3 language) ----
def bar_row(draw, x, y, w, label, value, frac, color):
    """Label row (dot + tracked label, value right) + rounded bar. Returns bottom y."""
    lab_f = bahn(28, EYEBROW_INST)
    dot = 15
    draw.ellipse([x, y + 6, x + dot, y + 6 + dot], fill=color)
    draw_tracked(draw, x + dot + 14, y, label.upper(), lab_f, MUTED, tr=28 * 0.14)
    val_f = bahn(42, "SemiBold")
    draw.text((x + w, y + 14), value, font=val_f, fill=color, anchor="rs")
    bar_h = 44
    by = y + 40
    draw.rounded_rectangle([x, by, x + w, by + bar_h], bar_h // 2, fill=TRACK)
    if frac > 0:
        fw = max(bar_h, int(frac * w))
        draw.rounded_rectangle([x, by, x + fw, by + bar_h], bar_h // 2, fill=color)
    return by + bar_h


# ---- Posts ----
def member_post(row, rank, n, scale, source, out_path, date_str):
    img, draw = base_canvas()
    header(draw)
    cx = W // 2

    # portrait
    side = 300
    paste_portrait(img, row["photo"], cx - side // 2, 196, side)

    # seat + rank eyebrow
    eyebrow(draw, cx, 540, "{}  ·  #{} of {}".format(row["seat"], rank, n))

    # name
    nf, ns = fit_bahn(draw, row["name"], 74, CW)
    draw.text((cx, 584), row["name"], font=nf, fill=NAVY, anchor="ma")
    name_bottom = draw.textbbox((cx, 584), row["name"], font=nf, anchor="ma")[3]

    # combined hero number
    ey = max(668, name_bottom + 26)
    eyebrow(draw, cx, ey, "Combined from both firms", size=26, fill=MUTED)
    combo = money(row["combined"])
    cf, _ = fit_bahn(draw, combo, 112, CW)
    draw.text((cx, ey + 40), combo, font=cf, fill=NAVY, anchor="ma")

    # sky panel with the two firm bars
    px0, px1 = MARGIN, W - MARGIN
    py0, py1 = 856, 1128
    draw.rounded_rectangle([px0, py0, px1, py1], 28, fill=SKY_PANEL)
    bx, bw = px0 + 40, (px1 - px0) - 80
    y = py0 + 34
    for key, label, col in (("endeavor", "Endeavor Real Estate Group", NAVY),
                            ("armbrust", "Armbrust & Brown, PLLC", CRIMSON)):
        val = row[key]["total"]
        y = bar_row(draw, bx, y, bw, label, money(val), val / scale, col) + 30

    # span + contribution count
    n_contrib = row["endeavor"]["n"] + row["armbrust"]["n"]
    span = span_text(row["span_min"], row["span_max"])
    extra = "  ·  {} contribution{}".format(n_contrib, "" if n_contrib == 1 else "s") \
        if n_contrib else ""
    draw.text((cx, 1162), span + extra, font=segoe(33), fill=MUTED, anchor="ma")

    # footnote (must fit in two lines above the footer band)
    note = ("Monetary + in-kind where the donor, employer, or occupation matches "
            "the firm  ·  {}  ·  bars scaled to the pack maximum".format(source))
    nf22 = segoe(21)
    ny = 1206
    for ln in _wrap(draw, note, nf22, CW)[:2]:
        draw.text((cx, ny), ln, font=nf22, fill=MUTED, anchor="ma")
        ny += 27

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


_SUFFIXES = {"iii", "ii", "iv", "jr", "jr.", "sr", "sr."}


def last_name(name):
    toks = [t for t in name.split() if t.lower().strip(",") not in _SUFFIXES]
    return toks[-1] if toks else name


def intro_post(rows, title, combined_total, cols, out_path, date_str):
    img, draw = base_canvas()
    header(draw)
    cx = W // 2

    eyebrow(draw, cx, 192, "Follow the money  ·  All-time")
    tf, ts = fit_bahn(draw, title, 62, CW, min_size=40)
    draw.text((cx, 236), title, font=tf, fill=NAVY, anchor="ma")

    sub = ("Contributions from Endeavor Real Estate Group & "
           "Armbrust & Brown, PLLC — {} combined".format(money(combined_total)))
    sf = segoe(33)
    sy = 236 + ts + 26
    for ln in _wrap(draw, sub, sf, CW):
        draw.text((cx, sy), ln, font=sf, fill=MUTED, anchor="ma")
        sy += 44

    # roster grid (post order = combined desc), logomark tile closes the grid
    gap = 20 if cols == 4 else 24
    label_h = 56
    n_tiles = len(rows) + 1
    rows_n = -(-n_tiles // cols)
    # shrink tiles if needed so the last row's labels clear the footer band
    gy_top = sy + 28
    avail = (H - FOOT_H - 24) - gy_top
    tile_w = min((CW - (cols - 1) * gap) // cols,
                 (avail + 26) // rows_n - (label_h + 26))
    pitch_y = tile_w + label_h + 26
    grid_h = rows_n * pitch_y - 26
    grid_w = cols * tile_w + (cols - 1) * gap
    gx0 = (W - grid_w) // 2
    gy0 = gy_top + max(0, (avail - grid_h) // 2)

    name_f = bahn(27, "SemiBold SemiCondensed")
    seat_f = segoe(22)
    for i in range(n_tiles):
        gx = gx0 + (i % cols) * (tile_w + gap)
        gy = gy0 + (i // cols) * pitch_y
        if i < len(rows):
            r = rows[i]
            tile = rounded_square(r["photo"], tile_w)
            img.paste(tile, (gx, gy), tile)
            tcx = gx + tile_w // 2
            ln = last_name(r["name"])
            lf = name_f if tw(draw, ln, name_f) <= tile_w else \
                fit_bahn(draw, ln, 27, tile_w, "SemiBold Condensed")[0]
            draw.text((tcx, gy + tile_w + 10), ln, font=lf, fill=NAVY, anchor="ma")
            draw.text((tcx, gy + tile_w + 40), r["seat"], font=seat_f,
                      fill=MUTED, anchor="ma")
        else:
            tile = logomark_tile(tile_w)
            img.paste(tile, (gx, gy), tile)

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def outro_post(rows, subtitle, out_path, date_str):
    img, draw = base_canvas()
    header(draw)
    cx = W // 2

    eyebrow(draw, cx, 268, "Follow the money")

    # hero wordmark — NO cursor at hero size (matches the OG cards)
    wm_size = 96
    while wordmark_w(draw, wm_size) > CW and wm_size > 60:
        wm_size -= 2
    wx = cx - wordmark_w(draw, wm_size) / 2
    wordmark(draw, wx, 330 + wm_size * 0.5, wm_size, cursor=False)

    draw.text((cx, 330 + wm_size + 40), subtitle, font=segoe(36), fill=MUTED, anchor="ma")

    # stats row
    total = sum(r["combined"] for r in rows)
    n_contrib = sum(r["endeavor"]["n"] + r["armbrust"]["n"] for r in rows)
    stats = (("{}".format(len(rows)), "Seats"),
             (money(total), "Combined"),
             ("{:,}".format(n_contrib), "Contributions"))
    ry = 572
    draw.line([MARGIN, ry, W - MARGIN, ry], fill=LINE, width=2)
    col_w = CW // 3
    for i, (val, lab) in enumerate(stats):
        scx = MARGIN + col_w * i + col_w // 2
        vf, _ = fit_bahn(draw, val, 64, col_w - 30)
        draw.text((scx, ry + 34), val, font=vf, fill=NAVY, anchor="ma")
        eyebrow(draw, scx, ry + 112, lab, size=24, fill=MUTED)

    # mini roster strip
    dia, sgap = 64, 20
    strip_w = len(rows) * dia + (len(rows) - 1) * sgap
    sx = cx - strip_w // 2
    for r in rows:
        c = circle_photo(r["photo"], dia)
        img.paste(c, (int(sx), 792), c)
        sx += dia + sgap

    # CTA pill
    cta = "See every donor at decodepolitics.org"
    cf = bahn(40, "SemiBold")
    pw = tw(draw, cta, cf) + 112
    ph = 100
    px0, py0 = cx - pw / 2, 952
    draw.rounded_rectangle([px0, py0, px0 + pw, py0 + ph], ph // 2, fill=NAVY)
    draw.text((cx, py0 + ph / 2), cta, font=cf, fill=WHITE, anchor="mm")

    draw.text((cx, py0 + ph + 56),
              "Every filing pulled, every dollar matched to its donor.",
              font=segoe(30), fill=MUTED, anchor="ma")

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def slug(recip, seat):
    last = recip.split(",")[0].strip().lower()
    last = re.sub(r"[^a-z]", "", last)
    s = re.sub(r"[^a-z0-9]", "", seat.lower())
    return "{}_{}".format(last, s)


def render_package(rows, roster, subdir, intro_title, outro_sub, cols, source, date_str):
    dpath = os.path.join(OUT, subdir)
    os.makedirs(dpath, exist_ok=True)
    files = []
    combined_total = sum(r["combined"] for r in rows)
    scale = max([max(r["endeavor"]["total"], r["armbrust"]["total"]) for r in rows] + [1.0])

    p = os.path.join(dpath, "01_intro.png")
    intro_post(rows, intro_title, combined_total, cols, p, date_str)
    files.append(p)

    recip_of = {r[0]: r[2] for r in roster}
    for i, row in enumerate(rows, start=2):
        recip = recip_of[row["name"]]
        fn = "{:02d}_{}.png".format(i, slug(recip, row["seat"]))
        p = os.path.join(dpath, fn)
        member_post(row, i - 1, len(rows), scale, source, p, date_str)
        files.append(p)

    p = os.path.join(dpath, "{:02d}_outro.png".format(len(rows) + 2))
    outro_post(rows, outro_sub, p, date_str)
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
        4, "Source: City of Austin campaign finance data (data.austintexas.gov)",
        date_str)

    tf = render_package(
        travis, TRAVIS, "travis",
        "Who's funding Travis County?",
        "Travis County campaign finance, decoded.",
        3, "Source: Travis County campaign finance filings",
        date_str)

    print("Output folder:", OUT)
    for label, files in (("AUSTIN (13)", af), ("TRAVIS (7)", tf)):
        print("\n" + label)
        for p in files:
            sz = os.path.getsize(p)
            print("  {:<28s} {:>8.1f} KB".format(os.path.basename(p), sz / 1024))


if __name__ == "__main__":
    main()
