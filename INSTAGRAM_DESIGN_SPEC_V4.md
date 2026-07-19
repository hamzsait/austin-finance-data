# Instagram Post Design Spec — v4 ("Statement")

**Status: current.** Replaces v3 (`INSTAGRAM_DESIGN_SPEC_V3.md`, now deleted). v3's
white editorial cards were clean but recessive — they read well once opened, yet
nothing stopped the scroll. v4 keeps v3's typographic restraint and left-aligned
news-page skeleton, and inverts it into a dark statement card where the dollar
figure IS the post.

## Design direction

**Dark statement editorial.** An ink-navy canvas (rare in a light-mode feed — the
card itself is the scroll-stopper), a thin crimson press-bar across the top edge,
and one enormous dollar figure with a crimson `$` and a full-width crimson
underline. Everything else stays quiet: tracked Oswald eyebrows, hairline rules,
thin bars, generous whitespace. Reference language: NYT dark social cards /
Bloomberg terminal-adjacent graphics.

Principles:

1. **Ink canvas, edge to edge.** `#0c1a2c`, no panels, no gradients. The only
   full-bleed element besides the background is the 8 px crimson bar on the top edge.
2. **The number is the headline.** One giant combined total per member post
   (~190 px cap, sized to fit), white digits, crimson `$`, 8 px crimson underline
   the full width of the figure. Nothing on the card competes with it.
3. **Left-aligned single column.** Same news-page skeleton as v3.
4. **Typography is the design — now in the real brand fonts.** Space Grotesk
   (wordmark, names, figures), Inter (body/meta), Oswald (tracked caps eyebrows) —
   the exact faces decodepolitics.org loads. Variable TTFs live in `assets/fonts/`
   (SIL OFL), so rendering is identical on any OS (v3 depended on Windows-only
   Bahnschrift/Segoe).
5. **Bars are thin lines** (12 px, square ends) on a barely-there track, scaled to
   the pack maximum. They annotate the numbers.
6. **Validated data colors.** Endeavor `#4a96d8`, Armbrust `#e8536b` — this pair
   passes the full palette validation (lightness band, chroma floor, CVD ΔE,
   contrast ≥ 3:1) against the `#0c1a2c` surface. Firm rows are also always
   direct-labeled, so identity never rides on color alone.
7. **Crimson is an accent:** top edge bar, `$`, underlines, wordmark
   (`decode`/`:`), and the Armbrust bar/amount. Nothing else.

## Canvas & tokens

- 1080 × 1350 px portrait, sRGB, PNG, 300 DPI metadata.
- Margin **84 px** all sides; content width **912 px**. Crimson top edge 8 px.
- Colors:
  - BG `#0c1a2c` — canvas
  - White `#f5f8fb` — primary text, hero digits
  - Sky `#c8e0f4` — eyebrows, wordmark parens, footer URL
  - Slate `#8fa3b8` — labels, meta, captions
  - Faint `#687c92` — source notes
  - Crimson `#e8536b` — accent + Armbrust (brightened from site `#cc1f3c` for
    dark-surface contrast)
  - Endeavor blue `#4a96d8`
  - Hairline `#223650` · Track `#1b2f47` · Keyline `#2a4160`
- Fonts (committed variable TTFs in `assets/fonts/`, SIL Open Font License):
  **Space Grotesk** wght 500/700 — wordmark, names, all figures;
  **Inter** 400/600 — body, meta; **Oswald** 600 — tracked caps (0.18 em).
- Wordmark on dark: `decode` crimson, `(` `)` sky, `politics` white, `:` crimson.
  No cursor (static-image artifact).

## Shared chrome (all posts)

- 8 px crimson bar across the very top edge.
- **Header:** wordmark top-left at y = 84, size 34. Top-right: context tag in
  slate 23 px Oswald tracked caps (member posts: `04 / 11` pager; intro/outro:
  series tag). Hairline rule at y = 158.
- **Footer:** hairline at y = 1258; `decodepolitics.org` (Space Grotesk 700, 30,
  sky) left, `July 2026` (Inter 26, slate) right.

## Member post (11 Austin + 5 Travis)

1. Header + pager.
2. **Portrait** 264 × 264 top-right at (732, 208): square crop, 8 px radius,
   keyline. Tall source photos crop **top-weighted** (10% bias) so foreheads are
   never clipped; wide photos crop horizontally centered. Faces at top-right
   balance the left-hung type.
3. Left of portrait: sky eyebrow caps `DISTRICT 4 · AUSTIN CITY COUNCIL`, then
   **name** in Space Grotesk 700, ≤ 76 px, up to 2 lines, white. Suffixes (III,
   Jr.) never orphan onto their own line.
4. Slate caps label `TOOK FROM DONORS AT THESE TWO FIRMS`, then the **hero
   figure** at y = 596: combined total ≤ 190 px, crimson `$` + white digits +
   8 px crimson underline at figure width, placed below the figure's actual ink
   bbox so comma descenders never touch it.
5. **Two firm rows** (y = 906, pitch 144): firm name (Inter 600, 33, white) left,
   amount (Space Grotesk 500, 46) right — Endeavor blue / Armbrust crimson, slate
   when $0; beneath each a 12 px bar on a full-width track, fill scaled to the
   **pack maximum** single-firm total.
6. Caption (Inter 29, slate): `Nov 2021 – Jul 2024 · 113 contributions · 69 donors`.
7. Source note (Inter 22, faint, ≤ 2 lines): match rule + `decodepolitics.org`
   citation + bar-scaling note.
8. Footer.

## Intro post (1 per package)

1. Header; right tag = `AUSTIN CITY COUNCIL` / `TRAVIS COUNTY`.
2. Sky eyebrow `FOLLOW THE MONEY · ALL-TIME`.
3. Headline Space Grotesk 700 ≤ 76 px, white: *Who's funding Austin City Council?*
4. **Hero figure**: package combined total, ≤ 150 px, same crimson-$ treatment.
5. Subhead Inter 31 slate: "in contributions from donors at Endeavor Real Estate
   Group and Armbrust & Brown, PLLC."
6. **Roster grid** — Austin 6 × 2 (11 tiles), Travis 5 × 1: square portraits,
   keyline, last name (Space Grotesk 500, white, shrink-to-fit) + seat (Inter 20,
   slate) below. Trailing cells stay empty.
7. Footer.

## Outro post (1 per package)

1. Header; right tag = series tag.
2. Sky eyebrow `FOLLOW THE MONEY`; wordmark at 68 px; tagline Inter 34 slate.
3. **Stat ledger:** three hairline-separated rows — value left (Space Grotesk
   700, 62, white), label right (slate tracked caps): seats · combined ·
   contributions traced.
4. **CTA:** `See every donor at` (Inter 34, white) over `decodepolitics.org`
   (Space Grotesk 700, 58, sky) with a 6 px crimson underline; closing line
   *Every filing pulled, every dollar matched to its donor.* (Inter 29, slate).
5. Footer.

## Data rules (v4 — website-derived)

- **Source of truth: the committed `<slug>_all_donations.json` files** — the same
  published donation tables that power decodepolitics.org. No `austin_finance.db`
  required; `python generate_instagram_posts.py` runs on any machine.
- Row shape: `[donor, date, amount, employer-identity, industry, location]`.
- **Firm match on the cleaned employer identity:**
  - Endeavor — employer contains `"Endeavor Real Estate"` (covers "…Group" and
    principal-annotated variants).
  - Armbrust — employer contains `"Armbrust"` **excluding** the joint
    `"Allen Boone Humphries Robinson / Armbrust Brown"` identity, matching the
    site's firm rollups.
- **Totals and donor counts prefer the site's own displayed rollups**: when the
  firm appears in `<slug>_data.json` → `notable_firms` (the "Notable firms" card
  the live profile page renders), its `total` and `donors` are used verbatim, so
  a posted figure always equals the live page. The donation-table computation is
  the fallback only where a firm sits below the page's notable-firms cutoff (and
  always supplies contribution counts and date spans, which the rollups lack).
- Note this is intentionally **narrower** than the v3/PDF fuzzy DB rules (donor
  name + raw employer + occupation-field matching): totals equal what a reader
  can verify on the site's own donor tables, e.g. Watson $75,950 (v4) vs
  $119,851 (v3 DB-fuzzy).
- Post order: combined total descending. Filenames `NN_lastname_seat.png`
  (ASCII-folded), `01_intro`, `NN_outro`.
- Captions report span, contribution count, and unique-donor count from the same
  rows. Bars scaled to the package maximum single-firm total.
- Portraits from `assets/photos/` (same files as the PDFs).

## Build

`python generate_instagram_posts.py` → 13 PNGs in `instagram_posts/austin/`,
7 in `instagram_posts/travis/`. Reads only committed JSON + assets; no network,
no database.
