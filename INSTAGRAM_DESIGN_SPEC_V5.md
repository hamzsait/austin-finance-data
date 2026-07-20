# Instagram Post Design Spec — v5 ("Statement · Real Estate")

**Status: current.** Replaces v4 (`INSTAGRAM_DESIGN_SPEC_V4.md`, now deleted).
v4's visual system ("Statement": dark editorial card, one enormous dollar
figure) carries over unchanged. What changes is the **story**: v4 tracked two
named firms (Endeavor Real Estate Group, Armbrust & Brown); v5 widens to the
**entire real-estate industry** — a larger, more systemic number that makes the
money-in-politics point without singling firms out. Real estate is the **#1
donor industry for 12 of the 16 officials** covered (top-2 for all but one),
$1.71M across both packages vs the ~$561k the two-firm cut captured.

## Design direction

**Dark statement editorial.** An ink-navy canvas (rare in a light-mode feed —
the card itself is the scroll-stopper), a thin crimson press-bar across the top
edge, and one enormous dollar figure with a full-width crimson underline.
Everything else stays quiet: tracked Oswald eyebrows, hairline rules, thin
bars, generous whitespace. Reference language: NYT dark social cards /
Bloomberg terminal-adjacent graphics.

Principles:

1. **Ink canvas, edge to edge.** `#0c1a2c`, no panels, no gradients. The only
   full-bleed element besides the background is the 8 px crimson bar on the top edge.
2. **The number is the headline.** One giant real-estate total per member post
   (~190 px cap, sized to fit), white digits, 8 px crimson underline.
3. **Left-aligned single column.** News-page skeleton, unchanged from v4.
4. **Typography is the design — in the real brand fonts.** Space Grotesk
   (wordmark, names, figures), Inter (body/meta), Oswald (tracked caps
   eyebrows) — the exact faces decodepolitics.org loads, committed as variable
   TTFs in `assets/fonts/` (SIL OFL).
5. **No charts on member cards.** The hero figure stands alone — no bars, no
   comparisons to colleagues. The rank tag in the eyebrow carries the context.
6. **Two headline colors.** Crimson `#e8536b` marks *Real Estate*, blue
   `#4a96d8` marks the body name (intro headline); both validated on the dark
   surface.
7. **Crimson is otherwise an accent:** top edge bar, underlines, wordmark.

## Canvas & tokens

- 1080 × 1350 px portrait, sRGB, PNG, 300 DPI metadata.
- Margin **84 px** all sides; content width **912 px**. Crimson top edge 8 px.
- Colors:
  - BG `#0c1a2c` — canvas
  - White `#f5f8fb` — primary text, hero digits
  - Sky `#c8e0f4` — eyebrows, wordmark parens, footer URL, #1-rank tag
  - Slate `#8fa3b8` — labels, meta, captions, reference bar/amount
  - Faint `#687c92` — source notes
  - Crimson `#e8536b` — accent + *Real Estate* headline color (brightened from
    site `#cc1f3c` for dark-surface contrast)
  - Blue `#4a96d8` — body-name headline color
  - Hairline `#223650` · Track `#1b2f47` · Keyline `#2a4160`
- Fonts: **Space Grotesk** wght 500/700 — wordmark, names, all figures;
  **Inter** 400/600 — body, meta; **Oswald** 600 — tracked caps (0.18 em).
- Wordmark on dark: `decode` crimson, `(` `)` sky, `politics` white, `:` crimson.

## Shared chrome (all posts)

- 8 px crimson bar across the very top edge.
- **Header:** wordmark top-left at y = 84, size 34. Top-right: context tag in
  slate 23 px Oswald tracked caps (member posts: `04 / 11` pager; intro/outro:
  series tag). Hairline rule at y = 158.
- **Footer:** hairline at y = 1258; `decodepolitics.org` (Space Grotesk 700, 30,
  sky) left, `July 2026` (Inter 26, slate) right.

## Member post (11 Austin + 5 Travis)

1. Header + pager.
2. **Portrait** 340 × 340 top-right at (656, 208): square crop, 8 px radius,
   keyline. Tall source photos crop top-weighted (10% bias); wide photos crop
   horizontally centered.
3. Left of portrait: sky eyebrow caps `DISTRICT 4 · AUSTIN CITY COUNCIL`
   (26 px, shrink-to-fit beside the larger portrait), then **name** in Space
   Grotesk 700, ≤ 84 px, up to 2 lines, white.
4. Two-part slate caps label at y = 660 (27 px, shrink-to-fit as one line):
   `TOOK FROM REAL ESTATE DONORS` + `· THEIR #1 DONOR INDUSTRY` — the rank tag
   renders **sky when #1**, slate otherwise. Then the **hero figure** at
   y = 712: the official's real-estate total ≤ 225 px, white digits, 8 px
   crimson underline placed below the figure's actual ink bbox. The figure
   stands alone — no bars or member-to-member comparisons.
5. Caption (Inter 33, slate) at y = 1128: `Jan 2022 – Jun 2026 ·
   273 contributions · 176 donors` — donor count is the **site's** rollup
   figure, verbatim.
6. Source note (Inter 24, faint, ≤ 2 lines): match rule + citation.
7. Footer.

## Intro post (1 per package)

1. Header; right tag = `AUSTIN CITY COUNCIL` / `TRAVIS COUNTY`.
2. Sky eyebrow `FOLLOW THE MONEY`.
3. Headline Space Grotesk 700 ≤ 76 px, wrapped word-by-word in three colors:
   *How much is* (white) *Real Estate* (crimson) *funding the* (white)
   *Austin City Council?* / *Travis County Commissioners?* (blue).
4. **Hero figure**: package real-estate total, ≤ 150 px.
5. Subhead Inter 31 slate: "in contributions from donors working in real
   estate — the #1 donor industry for 9 of these 11 officials." (counts
   computed from the data).
6. **Roster grid** — Austin 6 × 2 (11 tiles), Travis 5 × 1: square portraits,
   keyline, last name + seat below.
7. Footer.

## Outro post (1 per package)

1. Header; right tag = series tag.
2. Sky eyebrow `FOLLOW THE MONEY`; wordmark at 68 px; tagline Inter 34 slate.
3. **Stat ledger:** three hairline-separated rows — seats · total
   `FROM REAL ESTATE DONORS` · contributions traced.
4. **CTA:** `See every donor at` over `decodepolitics.org` with a 6 px crimson
   underline; closing line *Every filing pulled, every dollar matched to its
   donor.*
5. **Methodology disclaimer** (Inter 24, faint): the totals are a deliberate
   undercount — spouses, family members, and donors listing no employer are
   excluded; only contributions whose reported employer verifiably places the
   donor in the industry are counted.
6. Footer.

## Data rules (v5 — website-derived, fully audited)

- **Source of truth: the committed published data files** — the same tables
  that power decodepolitics.org. No `austin_finance.db` required;
  `python generate_instagram_posts.py` runs on any machine.
- **Hero total and donor count** per official are the site's own
  `"Real Estate"` interest-group rollup from `<slug>_data.json`, used
  **verbatim** — a posted figure always equals what the live profile page
  renders.
- **Membership rule:** a contribution is real-estate money iff its `industry`
  field in `<slug>_all_donations.json` (row shape `[donor, date, amount,
  employer-identity, industry, location]`) equals `"Real Estate"`. No fuzzy
  matching. The script asserts the row sum reconciles with the site rollup to
  within $1 (rollups round to whole dollars) and aborts otherwise.
- **Industry rank** (eyebrow tag) orders the site's interest groups by total,
  skipping the employment-status buckets (Not Employed, Self-Employed,
  Unknown, Retired, Family, Student) exactly as the site's `top_industry`
  stat does; rank #1 is asserted to agree with the site's published
  `top_industry` field.
- Contribution counts and date spans come from the same rows; donor counts on
  cards are the site's resolved-identity counts (the audit doc also reports
  distinct donor-name counts, which can run slightly lower).
- **Audit trail:** every run writes `instagram_posts/AUDIT_REAL_ESTATE.md` —
  per official, every single qualifying donation (date, donor, employer,
  amount) with per-official and per-package reconciliation tables tying each
  posted figure back to its exact rows.
- Post order: roster order (Mayor / County Judge first, then districts /
  precincts). Filenames `NN_lastname_seat.png` (ASCII-folded), `01_intro`,
  `NN_outro`.
- Portraits from `assets/photos/` (same files as the PDFs).

## Build

`python generate_instagram_posts.py` → 13 PNGs in `instagram_posts/austin/`,
7 in `instagram_posts/travis/`, plus `instagram_posts/AUDIT_REAL_ESTATE.md`.
Reads only committed JSON + assets; no network, no database.
