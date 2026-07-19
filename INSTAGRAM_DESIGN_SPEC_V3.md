# Instagram Post Design Spec — v3 ("Editorial")

**Status: current.** Replaces v1/v2 (`INSTAGRAM_DESIGN_SPEC.md`, now deleted). v2's
site-chrome framing (sky bands, browser tab, traffic-light dots, pill bars, drop-shadow
squircles) tested badly — it read as a screenshot mockup / 2012 infographic template.
v3 starts from a blank canvas.

## Design direction

**Data-first editorial minimalist.** The decodepolitics.org site itself is a white page
with restrained code-styled type — the posts now borrow that *restraint*, not the
browser-chrome gimmick. Reference language: Bloomberg CityLab / NYT graphics / Axios
social cards — big confident numbers, typographic hierarchy, thin data marks, generous
whitespace, one accent color.

Principles:

1. **White canvas.** No background bands, panels, frames, or tints. `#ffffff` edge to edge.
2. **Left-aligned single column.** Everything hangs off the left margin like a news page.
   No centered business-card compositions.
3. **Typography is the design.** Hierarchy comes from size and weight only. No pills,
   no rounded panels, no shadows, no decorative dots, no cursor bar.
4. **One huge number per member post.** The combined total is the hero (Apple-marketing
   scale, ~150–170 px). Everything else supports it.
5. **Bars are thin lines.** 10 px tall, square ends, on a barely-there track. They
   annotate the numbers; they are not the composition.
6. **Crimson is an accent, not a frame.** It appears only in: the wordmark (`decode`, `:`),
   the small eyebrow line, and the Armbrust & Brown bar/amount. Everything else is
   navy / ink / gray on white.
7. **Brand is small.** Wordmark ~34 px top-left; URL in the footer. No hero wordmarks
   on member posts. No blinking-cursor bar anywhere (static-image artifact).

## Canvas & tokens

- 1080 × 1350 px portrait, sRGB, PNG, 300 DPI metadata.
- Margin **84 px** all sides; content width **912 px**.
- Colors (from site CSS):
  - Ink `#0c1a2c` — primary text
  - Navy `#18314f` — names, numbers, Endeavor bar
  - Crimson `#cc1f3c` — accent only (wordmark, eyebrow, Armbrust bar)
  - Muted `#5b6b7a` — labels, meta, captions
  - Hairline `#dde4ec` (≈ navy @ 12%) — rules
  - Track `#eef1f5` — bar track
- Fonts (system, no downloads): **Bahnschrift** (variable; SemiBold/Bold, stands in for
  Space Grotesk) for wordmark, names, numbers; **Segoe UI** (+ Semibold) for body/meta.
- Caps labels: tracked at ~0.12–0.14 em, 24–26 px, never larger. (v2's 0.18 em
  hero-width tracking read amateur.)

## Shared chrome (all posts)

- **Header:** wordmark top-left at y≈84, size 34 — `decode` crimson, `(` `)` navy,
  `politics` ink, `:` crimson, **no cursor**. Top-right, same baseline: context tag in
  muted 24 px tracked caps (member posts: `01 / 11` pager; intro/outro: series tag).
- Hairline rule full content width at y = 152.
- **Footer:** hairline at y = 1258; below it `decodepolitics.org` (Bahnschrift SemiBold
  30, navy) left, `July 2026` (Segoe 26, muted) right.

## Member post (11 Austin + 5 Travis)

Top to bottom, all left-aligned:

1. Header + pager (`03 / 11`).
2. **Portrait** 300 × 300 at (84, 216): square center-crop, 6 px corner radius, 2 px
   navy-at-12% keyline. No shadow.
3. Right of portrait (x = 428): crimson eyebrow caps `MAYOR · AUSTIN CITY COUNCIL`,
   then **name** in Bahnschrift Bold, up to 2 lines, sized to fit (≤ 72 px), ink.
4. **Combined block** (full width, below portrait): muted caps label
   `COMBINED FROM BOTH FIRMS`, then the total in Bahnschrift Bold ≤ 165 px, navy.
5. Hairline.
6. **Two firm rows:** firm name (Segoe Semibold 33, ink) left, amount (Bahnschrift
   SemiBold 46) right — navy for Endeavor, crimson for Armbrust & Brown; beneath each a
   10 px bar on a full-width track, fill scaled to the **pack maximum** (same rule as
   PDF v3).
7. Caption line (Segoe 29, muted): `Feb 2022 – Oct 2024 · 341 contributions`.
8. Source note (Segoe 22, muted, ≤ 2 lines): match rule + dataset citation
   (`City of Austin campaign finance dataset (data.austintexas.gov)` /
   `Travis County campaign finance filings`) + bar-scaling note.
9. Footer.

## Intro post (1 per package)

1. Header; right tag = `AUSTIN CITY COUNCIL` / `TRAVIS COUNTY`.
2. Crimson eyebrow `FOLLOW THE MONEY · ALL-TIME`.
3. Headline Bahnschrift Bold ≤ 84 px, ink, wrapped: *Who's funding Austin City Council?*
4. Subhead Segoe 32 muted: combined $ from both firms, one sentence.
5. **Roster grid** — Austin 4 × 3 (11 tiles), Travis 3 × 2 (5 tiles): square portraits,
   6 px radius, keyline, last-name (Bahnschrift SemiBold) + seat (Segoe, muted) below.
   Empty trailing cells stay **empty** (whitespace, no logo filler tile).
6. Footer.

## Outro post (1 per package)

1. Header; right tag = series tag.
2. Crimson eyebrow `FOLLOW THE MONEY`.
3. Wordmark at 72 px, left-aligned (the one place it may be sized up), tagline below in
   Segoe 34 muted (*Austin campaign finance, decoded.*).
4. **Stat ledger:** three rows separated by hairlines — value left (Bahnschrift Bold 64,
   navy), label right (muted tracked caps): seats · combined · contributions.
5. **CTA, typographic:** `See every donor at` (Segoe 34, ink) over `decodepolitics.org`
   (Bahnschrift Bold 60, navy) with a 6 px crimson underline bar; closing line
   *Every filing pulled, every dollar matched to its donor.* (Segoe 29, muted).
   No button pill.
6. Footer.

## Data rules (unchanged from v2 / PDF v3)

- Rosters, firm-match rules, totals, `money()`, `span_text()` imported **verbatim** from
  `generate_pdfs.py`. Never re-derived.
- Post order: combined total descending. Filenames unchanged from v2
  (`NN_lastname_seat.png`, `01_intro`, `NN_outro`).
- Bars scaled to the package maximum single-firm total.
- Portraits from `assets/photos/` (same files as PDFs).

## Build

`python generate_instagram_posts.py` → 13 PNGs in `instagram_posts/austin/`,
7 in `instagram_posts/travis/`. Reads `austin_finance.db` read-only; no network.
