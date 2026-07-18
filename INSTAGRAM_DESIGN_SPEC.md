# Instagram Post Pack — Design Spec (v2)

Design system for `generate_instagram_posts.py`. Replaces the v1 design after user
feedback: *"weird errors with the logo and the red line cursor … I want bar graphs
per profile, an intro with all electeds per body, and more pleasing graphics that
incorporate our website branding."*

## What was wrong with v1 (audit findings)

1. **Wordmark colors were wrong.** v1 rendered `(politics):` all-navy. The site
   (index.html, assets/og/card.html) renders the **colon in crimson**: `decode`
   crimson · `(politics)` navy · `:` crimson.
2. **The cursor read as a rendering error.** v1 drew a thin sharp crimson
   rectangle butted against the colon — at hero size it looked like a stray
   capital-I glyph. On the site the cursor is a *rounded* 2–4px bar with a clear
   gap, and it blinks; frozen in a static image the v1 version looked broken.
3. **Broken-looking underline.** Intro/outro drew a 300px crimson rule centered
   on the canvas, but the wordmark (with cursor) isn't optically centered, so the
   rule landed under "code(poli" and read as a misaligned underline.
4. **Generic typography.** Everything was Arial. The site is Space Grotesk /
   Oswald / Inter — none of the brand feel survived.
5. **No graphics.** Member posts were two giant numbers; intro/outro were text in
   white space. No bars, no portraits on intro, sky-blue almost unused.

## Brand sources

- Live site: https://decodepolitics.org/ (repo: `index.html`, `assets/og/card.html`)
- Palette: navy `#18314f` · crimson `#cc1f3c` · sky `#c8e0f4` (site `--sky`) ·
  ink `#0c1a2c` · muted grey `#5b6b7a` · bar track `#eaeef3`
- Signature device: **sky band + white browser tab** header (traffic dots
  `#18314f`, `#ec3a22`, `#f5a623`; white tab with rounded top corners holding the
  wordmark) — used by the site header and every OG card.
- PDF v3 (`generate_pdfs.py`): stacked navy/crimson rounded bars on a light
  track, values right of the bars, rounded-square portraits, crimson accent rule.

## Typography

Brand webfonts aren't installed locally; nearest system equivalents:

| Role | Site font | Post font (Windows) |
|---|---|---|
| Wordmark, titles, big numbers | Space Grotesk Bold | **Bahnschrift SemiBold** (variable instance) |
| Eyebrow labels (uppercase, tracked) | Oswald | **Bahnschrift SemiBold Condensed**, +0.18em manual tracking |
| Body, subtitles, footnotes | Inter | **Segoe UI** (regular / semibold) |

Scale (1080×1350 canvas): hero wordmark 104 · post title 76–84 (auto-fit) ·
member name 68–76 (auto-fit) · combined number 108–120 (auto-fit) · bar values 42 ·
eyebrow 30 · subtitle 36 · grid labels 26/22 · footnote 22 · footer 28.

## Grid & safe areas

- Canvas 1080×1350 (4:5 portrait), white sheet.
- Side margins **72px**; content width 936px.
- Header band: sky `#c8e0f4`, y 0–150. Traffic dots (18px, gap 14) bottom-left;
  white tab (radius 22 top corners, flush to band bottom) holds the wordmark at 44px
  with the rounded cursor.
- Footer band: sky `#c8e0f4`, y 1274–1350. `decodepolitics.org` (crimson,
  semibold) left, date right (muted), vertically centered.
- Everything else lives on the white sheet between the two sky bands — sky is a
  structural bookend, not leftover white space.

## Wordmark treatment (static-safe)

Segments: `decode` crimson → `(politics)` navy → `:` crimson.

- **Header tab (44px):** include the cursor, drawn like the site's CSS: gap
  `0.17em`, width `0.11em`, height `0.94em`, **fully rounded ends**, crimson at
  90% opacity. Small + rounded + spaced = reads as intentional.
- **Hero size (outro, ≥100px): NO cursor** — exactly what the OG cards do for
  their big wordmark. No underline rule anywhere near the wordmark.

## Bar graph style (from PDF v3)

- Track: full content width, `#eaeef3`, fully rounded (radius = h/2).
- Fill: rounded, navy = Endeavor, crimson = Armbrust; minimum visible fill =
  bar height when total > 0.
- **Scale: pack-wide maximum** (same rule as the PDF page max), so bars compare
  honestly across the pack's posts. Footnote states this.
- Bar height 44px; label row above each bar: 16px color dot + firm name in
  eyebrow style (muted navy); dollar value right-aligned above bar end in the
  firm color, Bahnschrift SemiBold 42.
- The two bar rows sit on a **light-sky panel** (sky mixed ~40% toward white,
  radius 28, padding 40) so the sky accent does design work.

## Portrait treatment

- Source: `assets/photos/*.webp`, center-cropped square (same as PDF).
- Shape: **rounded square** (radius ≈ 12% of side) — matches the PDF and OG
  cards, not the v1 circle. 4x supersampled mask for clean edges.
- Border: 8px white inner ring + 1px `rgba(24,49,79,.12)` outline; soft navy
  drop shadow (blurred, 18% alpha, offset y+10).
- Member post: 300×300 centered. Intro grid: tile-sized (see below). Outro:
  56px mini-round row of the whole roster.

## Post compositions

### 01 — Intro ("who's in this pack")
1. Header band (above).
2. Eyebrow, crimson, tracked uppercase: `FOLLOW THE MONEY · ALL-TIME`.
3. Title, navy, 2 lines max: *Who's funding Austin City Council?* /
   *Who's funding Travis County?*
4. Subtitle, muted: contributions from the two firms + combined pack total.
5. **Roster grid**: every elected in the pack, sorted by combined total
   (= post order). Austin 4×3 (11 portraits + logomark tile closing the grid),
   Travis 3×2 (5 + logomark tile). Tile = rounded-square portrait, last name
   (navy, semibold-condensed) + seat (muted) beneath. Logomark tile =
   `assets/logomark.png` on a navy rounded square.
6. Footer band.

### 02..N — Member posts
1. Header band.
2. Rounded-square portrait 300px, centered, y≈190.
3. Eyebrow: `MAYOR · №1 OF 11` (seat + rank by combined, crimson, tracked).
4. Name, navy, auto-fit ≤ 76px.
5. Combined callout: eyebrow `COMBINED FROM BOTH FIRMS` (muted) + the combined
   dollar figure — the single hero number, navy, ~112px.
6. Sky panel with the two firm bars (style above), Endeavor then Armbrust.
7. Span line, muted: `Feb 2022 – Oct 2024 · N contributions`.
8. Footnote (tiny, centered): match rule + source + "bars scaled to pack max".
9. Footer band.

### Last — Outro (CTA)
1. Header band.
2. Eyebrow: `FOLLOW THE MONEY`.
3. Hero wordmark (no cursor), ~104px, centered.
4. Subtitle: *Austin campaign finance, decoded.* / *Travis County …*
5. Stats row (OG-card style, top rule): SEATS · COMBINED · CONTRIBUTIONS —
   values navy Bahnschrift 64, labels tracked muted eyebrows.
6. Mini portrait strip: whole roster as 56px rounded circles in one row.
7. CTA pill: navy, fully rounded, white `decodepolitics.org`, 44px text.
8. Footer band.

## Color usage rules

- **Navy**: titles, names, hero numbers, Endeavor, CTA pill, logomark tile.
- **Crimson**: `decode` + `:` + cursor, eyebrows, Armbrust, footer URL. Never
  for body text; never as a free-floating rule near the wordmark.
- **Sky**: header band, footer band, bar panel tint, portrait ring accents.
- **White**: sheet + tab. **Muted `#5b6b7a`**: subtitles, labels, footnotes.

## Data

Unchanged: rosters, firm-match rules, and totals imported from
`generate_pdfs.py` (`build`, `load_firm_people`); no re-derivation. The only
new displayed figures are sums of already-computed values (pack combined total,
contribution counts) and the rank index from the existing sort order.

Output: `instagram_posts/austin/` (13) + `instagram_posts/travis/` (7),
1080×1350 PNG, 300dpi metadata, same filenames as v1.
