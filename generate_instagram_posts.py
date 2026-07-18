#!/usr/bin/env python3
"""
generate_instagram_posts.py — Instagram post package generator.

Renders two Instagram-ready post packages (1080x1350 PNG, portrait feed size)
summarizing all-time campaign contributions received from Endeavor Real Estate
Group and Armbrust & Brown, PLLC, using the SAME data, rosters, firm-match
rules, brand palette, and portrait assets as generate_pdfs.py.

  Package 1 — Austin City Council      -> instagram_posts/austin/  (13 PNGs)
  Package 2 — Travis Commissioners Court-> instagram_posts/travis/  ( 7 PNGs)

All match logic / SQL / totals are imported verbatim from generate_pdfs.py
(DO NOT re-derive). Reads austin_finance.db read-only. No network access.

Design defaults chosen (documented in the module docstring):
  - Portrait crop: center-cropped square, circular mask with a light-sky ring
    (matches the PDF's center-square crop; circle reads best on IG feed).
  - Two big stacked numeric callouts (Endeavor navy / Armbrust crimson),
    auto-fit so the widest figure never exceeds the content width.
  - Intro/outro: full-brand hero — big wordmark, series title, "Follow the
    money" tagline, decodepolitics.org CTA.
"""
import os
import re
import sqlite3

from PIL import Image, ImageDraw, ImageFont

# ---- Reuse everything from the PDF generator (rosters, match rules, totals) ----
import generate_pdfs as g
from generate_pdfs import (
    AUSTIN, TRAVIS, build, load_firm_people, money, span_text, DB, PHOTOS,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "instagram_posts")

# ---- Canvas ----
W, H = 1080, 1350
MARGIN = 84
CW = W - 2 * MARGIN
DPI = (300, 300)

# ---- Brand palette (from generate_pdfs, converted 0-1 floats -> 0-255 ints) ----
def _rgb(t):
    return tuple(int(round(c * 255)) for c in t)

NAVY    = _rgb(g.C_NAVY)      # #18314f
CRIMSON = _rgb(g.C_CRIMSON)   # #cc1f3c
SKY     = _rgb(g.C_SKY)       # #cfe3f5
GREY    = _rgb(g.C_GREY)
LIGHT   = _rgb(g.C_LIGHT)
WHITE   = (255, 255, 255)
TRACK   = _rgb(g.C_TRACK)

# ---- Fonts (Arial ~= the PDF's Helvetica) ----
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FONT_REG = os.path.join(FONTS, "arial.ttf")
FONT_BLD = os.path.join(FONTS, "arialbd.ttf")
FONT_ITA = os.path.join(FONTS, "arialbi.ttf")   # bold-italic for the tagline
_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def tw(draw, text, fnt):
    b = draw.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0]


def fit_font(draw, text, path, max_size, max_w, min_size=20):
    """Largest size (<= max_size) at which `text` fits within max_w."""
    s = max_size
    while s > min_size and tw(draw, text, font(path, s)) > max_w:
        s -= 2
    return font(path, s)


def wordmark(draw, cx_left, top, size, tagline=True):
    """decode(politics): wordmark. Returns (right_x, baseline_height)."""
    fb = font(FONT_BLD, size)
    x = cx_left
    draw.text((x, top), "decode", font=fb, fill=CRIMSON)
    x += tw(draw, "decode", fb)
    draw.text((x, top), "(politics):", font=fb, fill=NAVY)
    x += tw(draw, "(politics):", fb)
    # blinking-cursor cue
    cur_w = max(3, int(size * 0.11))
    draw.rectangle([x + int(size * 0.10), top + int(size * 0.06),
                    x + int(size * 0.10) + cur_w, top + int(size * 0.86)],
                   fill=CRIMSON)
    return x


def circle_portrait(fname, dia, ring=SKY, ring_w=10):
    """Center-cropped square -> circular mask with a light-sky ring."""
    path = os.path.join(PHOTOS, fname)
    ss = dia * 4  # supersample for crisp edges
    canvas = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        s = min(w, h)
        img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        img = img.resize((ss, ss), Image.LANCZOS)
    except Exception:
        img = Image.new("RGB", (ss, ss), SKY)
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, ss - 1, ss - 1], fill=255)
    canvas.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(canvas)
    d.ellipse([ring_w * 2, ring_w * 2, ss - 1 - ring_w * 2, ss - 1 - ring_w * 2],
              outline=ring, width=ring_w * 4)
    return canvas.resize((dia, dia), Image.LANCZOS)


def base_canvas():
    img = Image.new("RGB", (W, H), WHITE)
    return img, ImageDraw.Draw(img)


def header(draw, tagline_right=True):
    wordmark(draw, MARGIN, 70, 54)
    if tagline_right:
        fi = font(FONT_ITA, 30)
        t = "Follow the money"
        draw.text((W - MARGIN - tw(draw, t, fi), 82), t, font=fi, fill=GREY)
    draw.rectangle([MARGIN, 158, W - MARGIN, 165], fill=CRIMSON)


def footer(draw, date_str="July 2026"):
    draw.line([MARGIN, H - 96, W - MARGIN, H - 96], fill=LIGHT, width=2)
    draw.text((MARGIN, H - 72), "decodepolitics.org", font=font(FONT_BLD, 32), fill=CRIMSON)
    fr = font(FONT_REG, 30)
    draw.text((W - MARGIN - tw(draw, date_str, fr), H - 71), date_str, font=fr, fill=GREY)


def member_post(row, out_path, date_str="July 2026"):
    img, draw = base_canvas()
    header(draw)

    cx = W // 2

    # ---- Portrait (circular) ----
    dia = 356
    top = 196
    port = circle_portrait(row["photo"], dia)
    img.paste(port, (cx - dia // 2, top), port)

    # ---- Name + seat ----
    name_y = top + dia + 26
    nf = fit_font(draw, row["name"], FONT_BLD, 90, CW)
    draw.text((cx, name_y), row["name"], font=nf, fill=NAVY, anchor="ma")
    nb = draw.textbbox((cx, name_y), row["name"], font=nf, anchor="ma")
    seat_y = nb[3] + 12
    sf = font(FONT_BLD, 46)
    draw.text((cx, seat_y), row["seat"], font=sf, fill=CRIMSON, anchor="ma")
    sb = draw.textbbox((cx, seat_y), row["seat"], font=sf, anchor="ma")

    # ---- Two big numeric callouts (sequential cursor; no overlap) ----
    e_val = money(row["endeavor"]["total"])
    a_val = money(row["armbrust"]["total"])
    # shared number size: fits the widest figure in the content width, big by default
    num_size = 150
    while num_size > 90 and max(tw(draw, e_val, font(FONT_BLD, num_size)),
                                tw(draw, a_val, font(FONT_BLD, num_size))) > CW:
        num_size -= 4
    num_f = font(FONT_BLD, num_size)
    lab_f = font(FONT_BLD, 33)
    dot = 22

    combo_top = H - 168                        # combined strip sits here
    callout_top = sb[3] + 34
    pair_h = 34 + 12 + num_size                 # label + gap + number
    gap_between = max(18, (combo_top - callout_top - pair_h * 2) / 3)

    y = callout_top
    for label, val, col in (
        ("ENDEAVOR REAL ESTATE GROUP", e_val, NAVY),
        ("ARMBRUST & BROWN, PLLC", a_val, CRIMSON),
    ):
        lw = tw(draw, label, lab_f)
        lx = cx - (dot + 16 + lw) // 2
        draw.ellipse([lx, y + 4, lx + dot, y + 4 + dot], fill=col)
        draw.text((lx + dot + 16, y), label, font=lab_f, fill=GREY)
        draw.text((cx, y + 34 + 12), val, font=num_f, fill=col, anchor="ma")
        y += pair_h + gap_between

    # ---- Combined + span strip ----
    combo = "Combined {}    ·    {}".format(
        money(row["combined"]), span_text(row["span_min"], row["span_max"]))
    cf = fit_font(draw, combo, FONT_REG, 36, CW)
    draw.text((cx, combo_top + 26), combo, font=cf, fill=GREY, anchor="mm")

    footer(draw, date_str)
    img.save(out_path, "PNG", dpi=DPI)


def hero_post(kind, out_path, title, subtitle, date_str="July 2026"):
    """kind: 'intro' or 'outro'. Full-brand hero."""
    img, draw = base_canvas()

    # big centered wordmark
    wm_size = 96
    fb = font(FONT_BLD, wm_size)
    decode_w = tw(draw, "decode", fb)
    pol_w = tw(draw, "(politics):", fb)
    total_w = decode_w + pol_w + int(wm_size * 0.22)
    wx = (W - total_w) // 2
    wy = 232
    draw.text((wx, wy), "decode", font=fb, fill=CRIMSON)
    draw.text((wx + decode_w, wy), "(politics):", font=fb, fill=NAVY)
    curx = wx + decode_w + pol_w
    cur_w = max(5, int(wm_size * 0.11))
    draw.rectangle([curx + int(wm_size * 0.10), wy + int(wm_size * 0.06),
                    curx + int(wm_size * 0.10) + cur_w, wy + int(wm_size * 0.86)], fill=CRIMSON)

    # crimson accent rule under wordmark
    ry = wy + wm_size + 34
    draw.rectangle([W // 2 - 150, ry, W // 2 + 150, ry + 8], fill=CRIMSON)

    # series title (wrapped, centered, navy)
    tf_size = 84
    tf = font(FONT_BLD, tf_size)
    lines = _wrap(draw, title, tf, CW)
    while len(lines) > 3 and tf_size > 48:
        tf_size -= 6
        tf = font(FONT_BLD, tf_size)
        lines = _wrap(draw, title, tf, CW)
    ty = 560
    for ln in lines:
        draw.text((W // 2, ty), ln, font=tf, fill=NAVY, anchor="ma")
        ty += int(tf_size * 1.14)

    # subtitle (grey, wrapped)
    ty += 24
    stf = font(FONT_REG, 40)
    for ln in _wrap(draw, subtitle, stf, CW):
        draw.text((W // 2, ty), ln, font=stf, fill=GREY, anchor="ma")
        ty += 54

    # tagline
    tag_f = font(FONT_ITA, 46)
    draw.text((W // 2, H - 320), "Follow the money", font=tag_f, fill=CRIMSON, anchor="ma")

    # CTA pill
    cta = "decodepolitics.org"
    cf = font(FONT_BLD, 44)
    cbw = tw(draw, cta, cf)
    pad_x, pad_y = 48, 26
    pill_w = cbw + pad_x * 2
    pill_h = 44 + pad_y * 2
    px0 = (W - pill_w) // 2
    py0 = H - 210
    draw.rounded_rectangle([px0, py0, px0 + pill_w, py0 + pill_h],
                           radius=pill_h // 2, fill=NAVY)
    draw.text((W // 2, py0 + pill_h // 2), cta, font=cf, fill=WHITE, anchor="mm")

    # date footnote
    fr = font(FONT_REG, 28)
    draw.text((W // 2, H - 84), date_str, font=fr, fill=GREY, anchor="ma")

    img.save(out_path, "PNG", dpi=DPI)


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


def slug(recip, seat):
    last = recip.split(",")[0].strip().lower()
    last = re.sub(r"[^a-z]", "", last)
    s = re.sub(r"[^a-z0-9]", "", seat.lower())
    return "{}_{}".format(last, s)


def render_package(rows, roster, subdir, intro_title, intro_sub, outro_title, outro_sub, date_str):
    dpath = os.path.join(OUT, subdir)
    os.makedirs(dpath, exist_ok=True)
    # roster lookup recip->photo already inside rows (build carries name/seat/photo)
    files = []
    # 01 intro
    p = os.path.join(dpath, "01_intro.png")
    hero_post("intro", p, intro_title, intro_sub, date_str)
    files.append(p)
    # members (rows already sorted by combined DESC)
    recip_of = {r[0]: r[2] for r in roster}
    for i, row in enumerate(rows, start=2):
        recip = recip_of[row["name"]]
        fn = "{:02d}_{}.png".format(i, slug(recip, row["seat"]))
        p = os.path.join(dpath, fn)
        member_post(row, p, date_str)
        files.append(p)
    # outro
    n = len(rows) + 2
    p = os.path.join(dpath, "{:02d}_outro.png".format(n))
    hero_post("outro", p, outro_title, outro_sub, date_str)
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
        "Contributions from Endeavor & Armbrust & Brown, all-time",
        "See the full data at decodepolitics.org",
        "Follow the money — Austin campaign finance, decoded",
        date_str)

    tf = render_package(
        travis, TRAVIS, "travis",
        "Who's funding Travis County?",
        "Contributions from Endeavor & Armbrust & Brown, all-time",
        "See the full data at decodepolitics.org",
        "Follow the money — Travis County campaign finance, decoded",
        date_str)

    print("Output folder:", OUT)
    for label, files in (("AUSTIN (13)", af), ("TRAVIS (7)", tf)):
        print("\n" + label)
        for p in files:
            sz = os.path.getsize(p)
            print("  {:<28s} {:>8.1f} KB".format(os.path.basename(p), sz / 1024))


if __name__ == "__main__":
    main()
