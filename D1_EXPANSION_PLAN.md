# D1 Expansion Plan — 2026 Austin City Council District 1

**Status:** Scoping document. Nothing executed. No code, folders, or commits produced.
**Date:** 2026-07-18
**Scope:** Profiles for the 2026 D1 open-seat field + reorganization of `/austin/`.

---

## 0. Executive summary — three things that change the shape of this project

**1. There are seven declared candidates, not three.** Misael Ramos, Amber Goodwin, and Michael Nahas all check out as D1 — but the field also includes Alexandria Anderson, Steven Brown, Portia Riggins, and (single-sourced, unverified) Kyra Rogers.

**2. The ballot is not close to final. Filing has not opened yet.** The window is **July 20 – August 17, 2026**. Everyone above is a declared candidate with a campaign treasurer, not a candidate on the ballot. Building seven profiles this week means building on a roster that will change — some will not complete filing, and new entrants are likely through Aug 17.

**3. Most of the finance data is already ingested, identity-assigned, and FEC-enriched.** The July 15 refresh absorbed the 2026 filings. Five of the seven already have rows in `austin_finance.db` at 99–100% identity coverage and ~99% FEC match. **Phase C is largely already done.** The real work is rendering and page structure, not data collection.

The single highest-leverage recommendation in this document is in §A: **do not nest the URLs.** The crowding problem is on the landing page, not in the URL space, and nesting encodes a mutable fact (district, candidate-vs-officeholder) into a permanent identifier.

---

## 1. Research findings — the D1 field

### 1.1 Candidates

| Candidate | D1 confirmed | Source quality | Website | Portrait |
|---|---|---|---|---|
| **Misael D. Ramos**, 39 | Yes | Own campaign site | misaelforaustin.com | Yes — site photos, 2022 Ballotpedia page |
| **Amber K. Goodwin**, 44 | Yes | Own campaign site | amberforaustin.com | Yes — professional headshots (Jan 2026) |
| **Michael D. Nahas**, 52 | Yes | Own campaign site | mike4austin.org | Yes — site photo |
| **Alexandria M. Anderson**, 39 | Yes | Own campaign site | alexandriaforaustin.com | Likely — "Meet Alexandria" page, not directly verified |
| **Steven A. Brown**, 41 | Yes | Own campaign site | brownforaustind1.com | Partial — no clean formal headshot |
| **Portia T. Riggins**, 34 | Yes | LinkedIn headline + news | none found | Informal only (Instagram, canvasrebel profile) |
| **Kyra L. Rogers**, 31 | **Reported only** | Austin Bulldog excerpt (403, not fetched) | none found | None found |

Neutral one-line backgrounds: Ramos — housing-development professional, neighborhood association president, ran D1 in 2022 (2nd, 25.3%). Goodwin — Travis County assistant DA, founder of Community Justice Action Fund. Nahas — CS/economics background, housing-supply advocate. Anderson — small-business owner, former Nike-sponsored sprinter, MLK Neighborhood Association president. Brown — Medtronic clinical specialist, former Save Austin Now PAC co-chair. Riggins — accounting/finance background, third-generation East Austinite. Rogers — cleaning-service owner, recent Austin arrival.

**Verification gaps to close before publishing:** Kyra Rogers is single-sourced from a publication that blocks automated fetching, and the same source noted she was not yet a registered voter — genuine doubt she completes filing. Ballotpedia returned empty shells on every attempt and could not be used as a cross-check for anyone.

### 1.2 Election calendar

| Event | Date |
|---|---|
| Filing opens | Mon **Jul 20, 2026** |
| Filing deadline | Mon **Aug 17, 2026, 5:00 p.m.** |
| Residency cutoff (6 mo.) | Feb 17, 2026 |
| Early voting | Oct 19–30, 2026 |
| General (nonpartisan, 50%+1) | Tue **Nov 3, 2026** |
| Runoff | Sat **Dec 12, 2026** |
| Harper-Madison's term ends | Jan 6, 2027 |

Districts on the ballot: **1, 3, 5, 8, 9**.

**One discrepancy to resolve:** the Clerk's "November 2026 Election" page rendered a Jan 1 – Oct 23 window, almost certainly write-in candidacy or campaign-finance filing dates rather than ballot applications. The Jul 20 / Aug 17 dates are quoted directly from the Clerk's office in press coverage and are consistent with Texas Election Code (Aug 17 = 78 days before Nov 3). Worth one email to elections@austintexas.gov before publishing a calendar.

### 1.3 Harper-Madison — get the framing right

She is **not seeking a third term**, and the seat is open. But "term-limited" is imprecise and we should not print it. Austin's two-term limit permits a third term if the member gathers signatures from 5% of registered district voters. Harper-Madison **declined to pursue the petition** — she opted out, she is not barred. (Paige Ellis in D8 is reportedly pursuing the petition route, which is a useful contrast.) No evidence she is running for another office, though that is unconfirmed rather than a firm negative.

### 1.4 Coverage landscape

Austin Free Press / Austin Bulldog is the workhorse outlet on this race — the origin of most candidate biography in circulation. Austin Politics Newsletter has the most substantive analysis but is advocacy-inflected (frames the race as anti-growth vs. pro-housing) and should not be treated as neutral. Community Impact carried January fundraising numbers. **KUT, Austin Monitor, and the Statesman have no 2026 D1 coverage** — search results pairing KUT/Monitor with D1 forums are from the **2022** cycle and must not contaminate the file.

---

## 2. Finance data — what we already have

Queried against `austin_finance.db` (2.4 GB, post-identity-migration, refreshed 2026-07-17). City data via the Socrata dataset `3kfv-biw6`.

| Candidate | Recipient string | Rows | Date range | Total | Unique donors |
|---|---|---|---|---|---|
| Ramos | `Ramos, Misael D.` | 417 | 2018-08-25 → 2026-06-30 | $45,743 | 300 |
| Goodwin | `Goodwin, Amber K.` | 583 | 2026-02-06 → 2026-06-30 | $91,346 | 482 |
| Anderson | `Anderson, Alexandria M.` | 198 | 2026-02-09 → 2026-06-30 | $28,367 | 189 |
| Brown | `Brown, Steven A.` | 112 | 2025-11-20 → 2026-06-30 | $22,363 | 96 |
| Riggins | `Riggins, Portia T.` | 2 | 2026-02-21 → 2026-03-02 | $800 | 2 |
| Nahas | — | **0** | — | — | — |
| Rogers | — | **0** | — | — | — |
| *Harper-Madison (incumbent)* | `Harper-Madison, Natasha N.` | 1,418 | 2018 → 2022 | $359,446 | 817 |

Ramos splits across cycles: 2018 (4 rows, $220), 2022 (133 rows, $20,652), 2026 (280 rows, $24,871). Brown splits 2025 (26 rows, $5,953) / 2026 (86 rows, $16,411).

### 2.1 Enrichment coverage — better than expected

| Candidate | donor_id set | employer_id set | FEC matched | Partisan lean present |
|---|---|---|---|---|
| Ramos | 99% | 82% | 298/300 | 193 |
| Goodwin | 99% | 77% | 481/482 | 317 |
| Anderson | 100% | 57% | 188/189 | 119 |
| Brown | 100% | 70% | 96/96 | 54 |
| Riggins | 100% | 100% | 2/2 | 1 |

**Implication: the ingest → identity → FEC chain is already complete for all five.** The global enrichment passes swept them up. The only genuine data gaps are:

- **Employer coverage is soft on Anderson (57%) and Brown (70%)** vs. the ~96% we hold on Harper-Madison. Newer filings, less employer-string cleanup. This directly weakens the "Employer-Affiliated %" hero stat and the Top Industries chart — the two things the card design leans on hardest.
- **Israel-Palestine and fossil-fuel spectrum coverage is effectively nil** (0–6 donors each). These sections auto-hide, so this degrades gracefully, but candidate pages will look thinner than officeholder pages.
- **Civic affiliations cannot be joined by donor_id** — the `civic_affiliations` table keys on `canonical_name`, not `donor_id`. Any affiliation work for candidate donors joins by name.

### 2.2 Publishability thresholds

- **Ramos, Goodwin, Anderson, Brown — publishable now.** Enough donors for meaningful industry breakdowns.
- **Riggins — not publishable.** Two contributions totaling $800. A profile page would be an empty shell, and publishing a near-blank page next to Goodwin's $91K page creates a misleading visual comparison of candidate viability. Recommend a card with a "no reportable contributions yet" state rather than a profile.
- **Nahas, Rogers — no data at all.** Nahas is a confirmed, website-having candidate with zero rows: either he has not filed a report, is self-funding under the disclosure threshold, or files under a name variant. Worth one direct check against the Clerk's treasurer-appointment list before concluding.

**Expected data once they file:** the next city filing deadlines will add 30-day and 8-day pre-election reports (early October and late October). Candidate totals typically multiply 2–4× between July and the general. Any numbers we publish now are a mid-race snapshot and must be labeled as such.

---

## 3. Photo sourcing

No downloads performed. Availability:

- **Clean campaign-site portraits available:** Ramos, Goodwin, Nahas, Anderson.
- **No clean formal headshot:** Brown (family/event photos only), Riggins (informal social media only), Rogers (nothing).

The existing site uses `assets/photos/<key>.webp` with a hardcoded `PHOTOS` set in `austin/index.html`; missing photos fall back to a generated initials tile. That fallback is a legitimate ship-blocker workaround for Brown/Riggins/Rogers, but a grid where four candidates have portraits and three have initials tiles reads as editorial favoritism even when it isn't. **Recommend: either all portraits or all initials tiles for the candidate grid.** Request headshots directly from campaigns that lack one — that is the journalistically clean path and takes one email each.

Note also: campaign-supplied portraits are copyrighted. Publishing them needs either permission (usually freely given for this purpose) or a defensible fair-use posture. Worth deciding once, up front.

---

## 4. Current site architecture

### 4.1 URL and file layout

- Live at `https://decodepolitics.org` (GitHub Pages from `hamzsait/austin-finance-data`, no Actions workflow — served directly from the branch).
- Profiles at `/austin/<slug>/index.html`. 17 currently live: `alter, brown, duchen, ellis, fuentes, gomez, harpermadison, howard, laine, morales, qadri, shea, siegel, travillion, vela, velasquez, watson`.
- Landing at `/austin/index.html`. Root `index.html` is the decode(politics) brand page; `austin.html` is a meta-refresh redirect to `/austin/`.
- Legacy `profile_<slug>.html` stubs at root are meta-refresh redirects to the clean URLs — **the established redirect pattern**, and the only one available (GitHub Pages has no server-side rewrites).

### 4.2 How a profile is generated

`build_candidate.py` is the driver:

1. `generate_profile_data.generate(recipient, ROOT, slug_override=slug)` → writes `<slug>_data.json` + `<slug>_all_donations.json` to repo root.
2. `make_profile_html(slug)` → copies `profile_template.html`, substitutes `PROFILE_SLUG`, injects OG meta from `austin_landing.json`, applies `COUNTY_TEMPLATE_SUBS` for county slugs, writes to `austin/<slug>/index.html`.
3. Prints an index-card snippet with the headline stats.

Per-slug election cycles live in a `CYCLES` dict in `generate_profile_data.py`; `CANDIDATE_MIN_YEAR` overrides the 2018 default for county officials.

### 4.3 How the landing page renders — three findings that matter

**Finding 1 — the landing page is already candidate-aware.** `austin/index.html` is fully data-driven from `austin_landing.json`. Each entry carries `{section, seat, status, status_note}`, and `frontHtml()` already has a `status === 'candidate'` branch rendering a `CANDIDATE` badge. `STATUS_ORDER` already sorts `current(0) → incoming(1) → candidate(2) → retired(3)`. The in-file comment states the intent explicitly: adding a candidate is meant to be a pure data change. **Adding candidates to the existing grid requires zero HTML edits.**

**Finding 2 — the one line that blocks nesting.** The render loop builds `href: '/austin/' + c.slug + '/'`, **ignoring the `href` field that already exists in `austin_landing.json`**. Any nested URL scheme requires changing this line to use `c.href`. It is a one-line fix, and arguably a latent bug worth fixing regardless — the JSON carries an `href` that is silently discarded.

**Finding 3 — the profile template is already location-independent.** It fetches `/${PROFILE_SLUG}_data.json` root-absolute and uses root-absolute asset paths. **A profile page renders correctly from any directory depth.** Nesting costs nothing technically — which means the case against nesting has to be made on other grounds, and it can be (§A).

### 4.4 Template reusability for candidates — better than assumed

Checked directly against `profile_template.html`:

- **There is no "in office since" line.** `heroSubtitle` is explicitly set to empty (`// no subtitle in generic template`). Nothing to remove.
- **The partisan section already auto-hides** when there is no FEC data: `if (!pl || !pl.matched_donors) { section.style.display = 'none'; return; }`. Same for `ipSection` and `civicSection` (both `display:none` by default). **The "no partisan chart if no FEC donors" requirement is already satisfied.**
- **The hero badge is data-driven** via `meta.office`.
- Genuinely hardcoded and city-specific: `Raised 2022+` (line ~985), `<span class="hint">2022+</span>`, and the "Austin City Clerk" sourcing footers — all already handled for county profiles by the `COUNTY_TEMPLATE_SUBS` string-substitution list, which is the pattern to extend.

**Conclusion: the template needs additive work (race context, campaign link), not surgery.** The user's anticipated removals are already handled.

---

## 5. Plan

## A. Reorganization proposal

### A.1 Recommendation: **do not nest the profile URLs.** Add a race *view*, not a race *container*.

Keep every profile at `/austin/<slug>/`. Add a new page at `/austin/district1/` that is an index over candidates, not a parent directory of them.

The reasoning, stated plainly because it cuts against the framing in the request:

**The overcrowding is on the landing page, not in the URL space.** Nobody browses the directory tree. What feels crowded is a single flat grid of 17 cards about to become 22+. That is a *presentation* problem, and it is fixable with sectioning and filtering in `austin/index.html` — which is already data-driven and already sorts by seat and status. Restructuring URLs does not make the grid less crowded.

**Nesting encodes a mutable fact into a permanent identifier.** A URL should be stable for the life of the resource. `district1` is not stable: one of these seven wins in November, and on January 6, 2027 they stop being a District 1 candidate and become the District 1 council member. Under Option 1 or 2, that transition forces a *second* URL migration and a *second* set of redirects, for a page whose content barely changed. Under a flat scheme, the winner's page needs a status field flipped and nothing else. Losing candidates are the same story in reverse — their pages remain valid historical records at a URL that never claimed they'd win.

**Redistricting is a live risk.** Austin redistricts on the decennial cycle; the next map lands before 2032. District numbers attached to person-URLs will rot.

**Cost asymmetry.** Flat costs zero redirects and zero broken inbound links. Nesting costs 17 meta-refresh stubs (Harper-Madison at minimum under Option 1), regenerated OG `canonical` tags, and a permanent second-hop for every existing shared link — and we already carry one legacy redirect layer from the July 14 move to clean URLs. Adding a second is how link rot compounds.

This is closest to **Option 3** in spirit — a clear separation between the officeholder view and the race view — but implemented as a *view over flat URLs* rather than a URL prefix. It gets Option 3's clarity without Option 3's migration.

### A.2 Concrete structure

```
/austin/                       landing — all officeholders + candidates, sectioned
/austin/<slug>/                every profile, officeholder and candidate alike (unchanged)
/austin/district1/             NEW — the D1 open-seat race page
/austin/races/                 FUTURE — index of all 2026 races (D1/3/5/8/9)
```

Candidate slugs: `ramos`, `goodwin`, `nahas`, `anderson`, `stevenbrown`, `riggins`, `rogers`.

**Note the collision:** `brown` is already taken by Travis County Judge Andy Brown. Steven Brown must be `stevenbrown` (or `brownsteven`). This also matters for `generate_profile_data`, which matches `recipient LIKE '%fragment%'` — `Brown` matches both. Pass the exact recipient string `Brown, Steven A.` as the fragment with `--slug stevenbrown`, exactly as `build_candidate.py`'s docstring already warns.

### A.3 Landing page changes

Purely additive to `austin_landing.json` plus a small edit to `austin/index.html`:

1. Add candidate entries with `section: 'council'`, `seat: 'District 1'`, `status: 'candidate'`, `status_note: '2026 Race'`. They sort under Harper-Madison automatically via existing `STATUS_ORDER`.
2. Change `href: '/austin/' + c.slug + '/'` → `href: c.href || '/austin/' + c.slug + '/'`. Fixes the latent bug; future-proofs any later restructuring.
3. Add candidate slugs to the `PHOTOS` set once portraits exist.
4. **Anti-crowding (the actual ask):** add a third collapsible section — `SECTION_DEFS` already supports this — titled "2026 Races," holding candidates for open seats, with a link to `/austin/district1/`. Officeholders stay in "Council" and "County." This shrinks the default grid rather than growing it, and the section-collapse state already persists per visitor via `localStorage`.

**Recommended default: candidates live in the "2026 Races" section, not inline under Harper-Madison.** Mixing declared candidates into the officeholder grid implies a parity between "person who holds this office" and "person who filed a treasurer appointment" that isn't real, especially pre-filing-deadline.

### A.4 If the user overrules and wants nested URLs

The path exists and is cheap-ish, because the template is location-independent (§4.3, Finding 3). Required: create `austin/district1/<slug>/`; write meta-refresh stubs at old paths (only Harper-Madison under Option 1, since candidates have no legacy URLs); update `og:url`/`canonical` in `build_candidate.py`'s OG injection; make `make_profile_html` take an output-path prefix; apply the `c.href` fix from A.3.2. Roughly **+40 lines across 3 files, plus 1 redirect stub.** The objection is durability, not difficulty.

---

## B. Candidate profile generation — template changes

**Reusable as-is:** `generate_profile_data.py` end to end, the entire donor/industry/firm/top-donor pipeline, the flip-card design, the OG-injection path, the auto-hiding conditional sections.

**New work required:**

| # | Change | Where | Est. |
|---|---|---|---|
| B1 | `CANDIDATE_TEMPLATE_SUBS` list mirroring `COUNTY_TEMPLATE_SUBS` — swap `Raised 2022+` → `Raised This Cycle`, `2022+` hint → `2026 cycle`, badge → `District 1 Candidate · 2026` | `build_candidate.py` | ~15 lines |
| B2 | `CYCLES` entries for each candidate slug. Ramos needs three (2018, 2022, 2026); Goodwin/Anderson one; Brown one spanning 2025–26 | `generate_profile_data.py` | ~10 lines |
| B3 | `CANDIDATE_MIN_YEAR` entries (2025 for Brown, 2026 for Goodwin/Anderson) so the hero window reflects the actual campaign, not an empty 2018 baseline | `generate_profile_data.py` | ~4 lines |
| B4 | Race-context banner: "Open seat — Natasha Harper-Madison is not seeking a third term. N candidates have declared. General Nov 3, 2026." + inline links to the other candidates | `profile_template.html` | ~35 lines HTML + ~20 JS |
| B5 | Campaign website link + "candidate-supplied information" disclosure in hero | `profile_template.html` | ~12 lines |
| B6 | Thin-data guard — if `unique_donors < 25`, show an explicit "limited filings to date" notice instead of rendering charts off a handful of donors | `profile_template.html` | ~15 lines |
| B7 | `ROSTER` entries + `CANDIDATE_SLUGS` set | `build_candidate.py` | ~10 lines |
| B8 | Race metadata as data, not hardcoded HTML — `austin_races.json` holding the D1 field, dates, and context, consumed by both B4 and the `/district1/` page | new file | ~60 lines |

**Estimated diff: ~200 lines across 4 files, one new data file.** Roughly 70% additive.

**Endorsements — recommend deferring.** Endorsement tracking is a real editorial commitment: it needs a sourcing standard, a refresh cadence, and a correction policy, and it is the section most likely to draw complaints from campaigns. It is not campaign-finance data and it is not what this site's credibility rests on. Ship without it; revisit after the filing deadline if there's appetite.

**B6 is the integrity-critical item.** Rendering a full industry-breakdown treatment on Riggins's two contributions would be technically correct and journalistically misleading.

---

## C. Data collection order

Most of this is already done. Revised, per candidate:

| Step | Ramos | Goodwin | Anderson | Brown | Riggins | Nahas | Rogers |
|---|---|---|---|---|---|---|---|
| Ingest | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ none | ❌ none |
| Identity assign | ✅ 99% | ✅ 99% | ✅ 100% | ✅ 100% | ✅ | — | — |
| FEC enrich | ✅ 298/300 | ✅ 481/482 | ✅ 188/189 | ✅ 96/96 | ✅ | — | — |
| Employer coverage | 82% | 77% | ⚠️ 57% | ⚠️ 70% | — | — | — |
| Web affiliation research | not run | not run | not run | not run | — | — | — |
| Profile generation | ready | ready | ready | ready | ⛔ too thin | blocked | blocked |

**Actual remaining work:**

1. **Verify Nahas and Rogers against the Clerk's treasurer-appointment list.** Nahas has a campaign site and zero rows — resolve whether that's a name variant, a not-yet-filed report, or under-threshold self-funding. One lookup.
2. **Employer backfill for Anderson and Brown.** Existing `fix_unclassified_employers.py` / `auto_classify_employers.py` path. Biggest single quality win — moves the hero stat and Top Industries chart from shaky to solid.
3. **Web affiliation batch on candidate donors** — ~1,070 unique donors across the four publishable candidates. **Explicitly deferred until Travis Phase 2 completes** (running in `travis_research/`, untouched per constraints). This is a follow-up batch on a warm pipeline, not a blocker for launch.
4. **Render + publish.** `build_candidate.py --recipient "<exact>" --slug <slug>`.
5. **Re-run everything after Aug 17** when the field is final.

**Order:** verify Nahas/Rogers → employer backfill → render four profiles → build `/district1/` → landing update → push → affiliation batch as a later enrichment pass.

---

## D. `/austin/district1/` page design

**Structure**, reusing the decode(politics) brand from `INSTAGRAM_DESIGN_SPEC.md` and the existing landing chrome (browser-tab header, navy `#18314f` / red `#ba1200`, Space Grotesk / Inter / Oswald):

1. **Header** — "District 1 · Open Seat" with the tab-strip chrome, breadcrumb back to `/austin/`.
2. **Race context block** — Harper-Madison not seeking a third term (with the petition nuance from §1.3 stated correctly, not "term-limited"), her term ending Jan 6 2027, general Nov 3, runoff Dec 12.
3. **Filing-status banner — prominent, above the cards.** "Candidate filing runs July 20 – August 17, 2026. This field is not final." Non-negotiable while it's true; it's the difference between a useful page and a misleading one.
4. **Candidate card grid** — reuse `flipcard` markup exactly. Front: portrait/initials, name, "District 1 Candidate," raised pill, donor count. Back: Top Industries bars + See More. Cards for candidates without profiles link out to the campaign site rather than a stub page.
5. **Comparison strip** — a single horizontal bar chart of total raised across candidates. High-value, cheap, and the clearest thing on the page.
6. **Methodology + as-of date** — data through 2026-06-30, sourced from Austin City Clerk filings, next reports due October.

**Sort order — recommend alphabetical by surname, with raised-DESC as a user toggle.** Defaulting to raised-DESC editorializes: it presents fundraising as the ranking metric on a page many readers will treat as a candidate directory, and it structurally advantages the best-funded candidate before a single vote. Alphabetical is the neutral default; the money story is still fully present in the comparison strip and on every card. Random order is worse than both — it looks arbitrary and makes the page unciteable across visits.

**Candidates with no finance data get a card**, with an explicit "no contributions reported to date" state. Omitting them entirely would be a worse distortion than showing a zero — absence from a candidate directory reads as "not running."

**Harper-Madison should appear**, in a visually distinct "Outgoing" block set apart from the candidate grid, linking to her existing profile. She's the reason the seat is open and her donor history is the natural baseline. Distinct styling is what prevents her from reading as a candidate.

---

## E. Effort estimate

| Work | Files touched | Est. |
|---|---|---|
| Landing page: `c.href` fix + "2026 Races" section | `austin/index.html`, `austin_landing.json` | 45 min |
| Template changes B1–B7 | `build_candidate.py`, `generate_profile_data.py`, `profile_template.html` | 2.5–3 hr |
| `austin_races.json` (B8) | new | 30 min |
| `/austin/district1/index.html` | new | 2–2.5 hr |
| Verify Nahas/Rogers with Clerk | — | 30 min |
| Employer backfill (Anderson, Brown) | existing scripts | 45 min + runtime |
| Photo sourcing (request, convert to webp) | `assets/photos/` | 1 hr + campaign response latency |
| Per-candidate render (export → render → card) | — | **~6–8 min each**, ~30 min for four |
| OG card images (4) | `assets/og/` | 30 min |
| QA, mobile check, push | — | 45 min |

**Total: roughly 10–12 focused hours,** realistically **2–3 working days** with photo-request latency.

**Nesting URLs instead (Option 1) would add ~2 hours** — plus recurring cost at every status transition.

**Deferred, not counted:** web affiliation batch on ~1,070 candidate donors (gated on Travis Phase 2), endorsements section, `/austin/races/` index for D3/5/8/9.

**Sequencing recommendation:** the strongest argument is to **build the infrastructure now and publish after August 17.** Everything in the table above except the per-candidate render is roster-independent. Building now and publishing on Aug 18 with a final, verified field costs nothing extra and avoids publishing a candidate list that changes twice before the ballot is set. If there's a reason to publish sooner — and there may be, since nobody else is covering this race's money — the filing-status banner (D3) is what makes an early publish defensible.

---

## F. Open questions

Defaults are baked in above; these are the decisions worth confirming before code.

1. **URL scheme.** Plan assumes flat `/austin/<slug>/` + a `/district1/` view (§A.1), against the nesting options in the request. Confirm or overrule — this is the one decision that's expensive to reverse later.
2. **Publish now or after Aug 17?** Default: build now, publish Aug 18 with a verified field. Publishing before the deadline is defensible with the D3 banner but means a roster that will change.
3. **Scope: four or seven?** Default: render profiles for the four with real data (Ramos, Goodwin, Anderson, Brown); cards-only for Riggins, Nahas, Rogers. Alternative is scaffolding all seven, which produces three near-empty pages.
4. **Riggins.** $800 across two contributions. Default: card with "no meaningful filings yet," no profile page. Confirm the threshold — proposed cutoff is 25 unique donors (B6).
5. **Kyra Rogers.** Single-sourced from a publication that blocks fetching, reportedly not a registered voter. Default: omit until independently confirmed. Include as unconfirmed instead?
6. **Nahas.** Confirmed candidate, zero finance rows. Default: card linking to his campaign site, flagged "no contributions reported." Want the Clerk lookup first?
7. **Harper-Madison on `/district1/`?** Default: yes, in a distinct "Outgoing" block.
8. **Sort order.** Default: alphabetical, with a raised-DESC toggle. Raised-DESC by default is the alternative and is a real editorial choice, not a neutral one.
9. **Photos.** Default: request headshots from Brown/Riggins/Rogers rather than shipping a mixed portrait/initials grid. Also needs a one-time call on using campaign-supplied images (permission vs. fair use).
10. **Endorsements.** Default: defer entirely (§B).
11. **Affiliation research batch.** Confirmed deferred until Travis Phase 2 finishes. Should candidate donors be Phase 3, or fold into the next general pass?
12. **Do the other four open districts (3, 5, 8, 9) get the same treatment?** Affects whether `/district1/` is built as a one-off page or as the first instance of a reusable race-page generator. Building it generic costs maybe 45 extra minutes now and saves that four times over.

---

## Appendix — verification notes

**Verified against primary sources:** filing window and election dates (austintexas.gov/clerk/programs/elections); D1 candidacy for Ramos, Goodwin, Nahas, Anderson, Brown (own campaign sites); all finance figures (direct `austin_finance.db` queries, this session); all architecture claims (direct file reads of `austin/index.html`, `profile_template.html`, `build_candidate.py`, `generate_profile_data.py`).

**Reported but not primary-verified:** Riggins's candidacy (LinkedIn + Austin Free Press); Rogers entirely; candidate ages and middle names; Harper-Madison's petition decision (news-reported, consistent across sources).

**Could not verify:** Ballotpedia returned empty shells on every fetch; theaustinbulldog.org returns HTTP 403; the Clerk's official election-calendar PDF could not be parsed in this environment.

**Known contamination risk:** KUT and Austin Monitor results for "District 1 candidate forum" are from the **2022** cycle. The Austin Monitor's D1 tag archive stops at December 2024. Do not cite either as 2026 coverage.

**Unreliable source, do not cite:** austinmayor.com/council01/ — an auto-generated aggregator still showing Harper-Madison as incumbent with "no challengers filed yet."
