# Affiliation Template Expansion — Scoping Plan

**Status:** Scoping document. Read-only investigation. No code changed, nothing committed.
**Date:** 2026-07-18
**Question:** The `civic_affiliations` table holds 1,791 rows. The profile page renders four narrow buckets. What should be surfaced, and what does it cost?

---

## 0. The finding that changes the shape of this task

**This is not a template-only change.** The task brief assumed the work lives in `profile_template.html` with maybe a payload tweak. It doesn't.

`generate_profile_data.py` (lines ~1080–1170) builds the `civic_affiliations` payload by **filtering to four hard-coded buckets**, and it does so partly by **string-matching organization names**, not by reading the `category` column:

```python
def is_adl_row(r):
    org_lc = (r.get("org") or "").lower()
    return r["category"] == "jewish_civic" and (
        "anti-defamation" in org_lc or "adl" in org_lc)
...
"by_category": {
    "aipac_direct":    sort_donors(aipac_donors),
    "adl":             sort_donors(adl_donors),
    "liberal_zionist": sort_donors(liberal_zionist_donors),
    "oil_gas":         sort_donors(oil_gas_donors),
},
```

Everything outside those four buckets is **dropped before the JSON is written**. The rows aren't hidden by CSS — they were never serialized. `civic`, `political`, `business`, `gun_control`, `military_defense`, `gun_rights`, `healthcare`, and `industry` do not exist in any published `*_data.json`.

So the real footprint is **`generate_profile_data.py` first, `profile_template.html` second**, plus a regeneration pass across all 22 profiles. Details in §C.

### How much is invisible

| Profile | Donors with an affiliation | Rendered today | Hidden | % invisible |
|---|---|---|---|---|
| Goodwin | 193 | 9 | 184 | **95%** |
| Ramos | 43 | 0 | 43 | **100%** |
| Anderson | 32 | 1 | 31 | **97%** |
| Steven Brown | 24 | 0 | 24 | **100%** |
| Riggins | 2 | 0 | 2 | **100%** |
| *Watson* (sitting) | 286 | 87 | 199 | **70%** |
| *Ellis* (sitting) | 61 | 27 | 34 | **56%** |

Three of the five D1 candidates currently render an **empty affiliation section** despite having documented findings. The D1 scrub cost $257.86; roughly 95% of what it produced is not visible on the site.

Note the asymmetry: the four rendered buckets are Israel/Palestine-adjacent plus oil & gas. On a candidate whose donor base has no such ties, the section renders blank — while their 43 civic and business affiliations sit unused. That is a real editorial distortion, not just a coverage gap: **the only donor affiliations the site currently shows are Israel/Palestine and fossil-fuel ties.**

---

## Section A: Category inventory + ranking

### A.1 Voter-transparency rubric

Scores answer one question: **does knowing this about a donor help a voter understand who is funding this candidate and what those funders may want from City Council?**

| Score | Meaning |
|---|---|
| **5** | Direct, documented interest in matters the City Council votes on. A voter's read of the candidate changes. |
| **4** | Organized political or advocacy activity with a clear policy agenda, but not necessarily city-specific. |
| **3** | Economic or professional interest that plausibly intersects council business (land use, permitting, contracts). |
| **2** | Community standing and civic participation. Contextual — tells you who the donor is, not what they want. |
| **1** | Identity-adjacent, ambiguous, or already covered better elsewhere on the page. Publishing risks implying a claim the data doesn't support. |

Two deliberate consequences of this rubric. First, **`civic` — the single largest category — scores 2**, not 5. Volume is not relevance; being on a soccer nonprofit board tells a voter little about a council vote. Second, **`political` scores 4 but is heavily duplicative** (see A.3), so its practical value is lower than its score suggests.

### A.2 Inventory (sorted by row count DESC)

| Category | Sitewide rows | D1 delta | Distinct names | Rendered today | Score | What it means | Example finding |
|---|---|---|---|---|---|---|---|
| `civic` | **704** | 351 | 389 | ❌ Hidden | **2** | Nonprofit boards, neighborhood associations, mentorship and community orgs | Malek Benyousef — 100 Black Men of Austin, VP of Mentorship |
| `political` | **372** | 203 | 264 | ❌ Hidden | **4** | Party committees, campaign roles, lobby registrations, partisan donor patterns | Joe DiQuinzio — TEC lobby registration, client of registered lobbyist John W. Bartram (2010) |
| `business` | **372** | 101 | 280 | ❌ Hidden | **3** | Company ownership, executive and founder roles | Malek Benyousef — Austin Sol FC, co-founder/co-owner |
| `jewish_civic` | **157** | 2 | 85 | ⚠️ Partial | **1** | Jewish communal organizations. **Only ADL-name-matching rows render**; the rest are dropped | Sanford Dochen — ADL board member; registered witness for SB 326 |
| `gun_control` | **54** | 52 | 32 | ❌ Hidden | **4** | Gun-violence-prevention advocacy roles | Nicole Golden — Executive Director, Texas Gun Sense; co-founder, Moms Demand Action Austin |
| `oil_gas` | **53** | 3 | 43 | ✅ Rendered | **5** | Oil & gas ownership, executive, mineral interests | Gerald Lindenmuth — owner/president, Lindenmuth & Associates; 8 mineral interests |
| `military_defense` | **21** | 1 | 19 | ❌ Hidden | **3** | Defense contracting executives and board members | Warren Hayes — Hayes Modular Group, military barracks contracts |
| `oil_gas_major` | 9 | 0 | 9 | ✅ Rendered | **5** | Major integrated oil companies | — |
| `oil_gas_industry_association` | 7 | 0 | 5 | ✅ Rendered | **5** | Industry trade associations | — |
| `oil_gas_independent` | 6 | 0 | 6 | ✅ Rendered | **5** | Independent producers | — |
| `healthcare` | 5 | 0 | 3 | ❌ Hidden | **3** | Hospital and medical-institution boards | Laura Gottesman — Dell Medical School Founders Circle |
| `liberal_zionist` | 5 | 0 | 3 | ✅ Rendered | **1** | J Street, OneVoice, dovish Zionist orgs | — |
| `aipac_direct` | 5 | 1 | 4 | ✅ Rendered | **4** | AIPAC leadership, board, staff | Yael Ouzillou — former AIPAC development staff |
| `pro_israel` | 4 | 0 | 4 | ❌ Hidden | **4** | Other pro-Israel advocacy orgs | — |
| `oil_gas_services` | 4 | 0 | 4 | ✅ Rendered | **5** | Oilfield services | — |
| `oil_gas_legal` | 4 | 0 | 4 | ✅ Rendered | **4** | Energy law practice | — |
| `gun_rights` | 4 | 0 | 4 | ❌ Hidden | **4** | Firearms industry and gun-rights orgs | David Gochman — former CEO, Academy Sports + Outdoors |
| `industry` | 3 | 0 | 2 | ❌ Hidden | **2** | Legacy catch-all, pre-v3 | Kirk Rudy — Endeavor Real Estate, co-founder & CEO |
| `jewish_political` | 1 | 0 | 1 | ❌ Hidden | **1** | Legacy single row | — |
| `oil_gas_academic` | 1 | 0 | 1 | ✅ Rendered | **3** | Energy academia | — |
| **TOTAL** | **1,791** | 714 | 780 | — | | | |

### A.3 Four data-quality problems that must be resolved before shipping

These surfaced while reading actual rows. Each one is a reason not to ship `political` and `civic` as-is.

**1. `political` substantially duplicates the Partisan Lean section.** Example row: *"Consistent Republican donor — $5,000 to the NRSC in each of 2022 and 2024, $5,000 via WinRed…"* That is FEC donation history, which the page already renders as a dedicated dollar-weighted partisan-lean chart built from structured data. Re-publishing it as prose "affiliation" is redundant and less rigorous than the chart. **Recommendation: split `political` into genuine organizational roles (campaign staff, party officer, lobby registration) versus donation-pattern restatements, and publish only the former.** This split does not exist in the data today and needs either a query heuristic or a re-tagging pass.

**2. Some roles are self-flagged as unverified.** A `civic` row reads: *"Nonprofit board service (reported in his professional biography; not independently verified against either organization's published roster)."* The research agent was appropriately honest. But the section is titled **"Verified Organizational Affiliations"** — publishing an explicitly unverified claim under that heading is a straightforward accuracy problem.

**3. 75 rows (4.2%) cite LinkedIn as the source.** A self-authored profile is weak sourcing for a public factual claim about a private individual, and LinkedIn's terms don't contemplate this reuse. Two of the `civic`/`jewish_civic` examples above rest on LinkedIn alone.

**4. At least one row publishes a family relationship.** An `industry` row reads: *"Spouse of former Austin Mayor Steve Adler… NO documented [affiliation]."* That's a relational fact about a private individual with no documented affiliation of her own. Publishing it under an affiliations heading implies an interest the row itself says isn't documented.

**Bottom line for Section A:** the two highest-volume hidden categories (`civic` 704, `political` 372) are also the two with the weakest transparency value and the most quality problems. **Volume should not drive ship order.** See §E.

---

## Section B: What to add, per category

Proposal: **three new cards** plus a fix to the existing one, rather than eight new sections. Eight sections on a page that already has seven would bury the signal.

### B.1 Card: "Policy & Advocacy Ties" — *ship first*

**Categories:** `gun_control` (54), `gun_rights` (4), `military_defense` (21), `pro_israel` (4), `healthcare` (5). Plus the existing `aipac_direct` / `liberal_zionist` / `oil_gas` buckets migrate here so all policy spectrums sit together and read as balanced.

**Heading:** Policy & Advocacy Ties
**Description:** *"Donors with documented leadership, board, or staff roles at organizations that take positions on public policy. Both sides of each policy spectrum are searched and reported. These are organizational roles from public records — not inferred from names, employers, or donation patterns."*

**Chip style (brand palette):**
- Container: white card, `1px solid rgba(24,49,79,.12)`, radius 12px — matches `.card`
- Category header: Oswald 600, 12px, `.1em` tracking, uppercase, navy `#18314f`
- Category chip: sky `#cfe3f5` background, navy text, radius 5px, 10px
- Spectrum-paired categories rendered **adjacent with matched styling** (gun control next to gun rights, pro-Israel next to pro-Palestine) so a zero on one side is visibly a zero, not an omission
- Count badge: crimson `#cc1f3c` only when count > 0

**Finding row:** donor name (Space Grotesk 700, 13px, navy) · local dollar total, right-aligned, muted · org name (13px) · role (12px, muted, **clamped to 2 lines with expand**) · source link (crimson, 11px, `rel="noopener nofollow"`).

**Sort:** dollar DESC. This is the one card where money is the point — a $2,000 donor with a defense-contracting role matters more to a voter than a $50 one.

### B.2 Card: "Industry & Business Ties" — *ship second*

**Categories:** `business` (372), `industry` (3), plus `oil_gas_legal` if not kept in B.1.

**Heading:** Industry & Business Ties
**Description:** *"Donors who own, founded, or hold executive roles at identifiable businesses. Ownership and leadership are reported; employment alone is captured in the industry breakdown above and is not repeated here."*

Same chip style, navy accent instead of crimson. **Sort: dollar DESC.** Cap at top 25 with "show all" expander — 372 rows would dwarf the page.

**Dedup note:** this card overlaps the existing "Top Industries" chart, which already classifies every donor by employer. The distinction to enforce is **ownership/leadership vs. employment** — otherwise it restates the chart in prose.

### B.3 Card: "Community & Civic Roles" — *ship last, if at all*

**Categories:** `civic` (704).

**Heading:** Community & Civic Roles
**Description:** *"Donors with documented board or leadership roles at neighborhood associations, nonprofits, and community organizations. Included as civic context; these roles do not indicate a policy position."*

That last clause is load-bearing. Without it, listing a donor's church or youth-sports board under a "follow the money" heading implies an interest the data doesn't support.

**Sort: alphabetical.** Dollar-sorting community volunteering creates an implication — "biggest donor is most connected" — that isn't supported. **Cap at top 20 with expander.** Collapsed by default.

### B.4 Fix: the existing "Verified Organizational Affiliations" card

Three changes independent of any new card:

1. **Drop `jewish_civic` from default display, or rename the card honestly.** Today the ADL bucket catches only rows whose org name string-matches "ADL"/"anti-defamation" — 85 distinct names are tagged `jewish_civic` and most never render. Either surface the category under a neutral heading with the same treatment as every other communal-organization category, or don't surface it. The current halfway state singles out one community's organizations for display while dropping equivalent civic ties from every other community — that's the least defensible option of the three and it is what ships today.
2. **Retitle "Verified Organizational Affiliations" → "Documented Organizational Affiliations."** Some rows are explicitly not independently verified (§A.3.2).
3. **Suppress rows whose only source is LinkedIn** (75 rows), or badge them `self-reported`.

### B.5 Small-donor suppression — documented, not recommended

Option: hide findings from donors giving under $100. Would remove ~50% of D1 donor rows.

**Recommendation: do not suppress.** You explicitly chose to keep small donors, and the rationale holds — a $50 donor who runs a lobbying shop is more newsworthy than a $500 donor who doesn't. Money-based suppression would hide exactly the asymmetric cases the research exists to find. The noise problem is better solved by the per-card caps in B.2/B.3 and by category selection, both of which cut volume without correlating to donor wealth.

---

## Section C: Code footprint

| File | Change | Lines | Type |
|---|---|---|---|
| `generate_profile_data.py` | Replace the 4 hard-coded buckets with a category→card mapping table; emit all categories; add per-category totals; keep name-match join unchanged | **~120** | **Refactor** (~60 replaced) |
| `profile_template.html` — CSS | New card/chip/spectrum-pair styles; reuse `.civic-*` classes where possible | ~70 | Additive |
| `profile_template.html` — markup | 3 new `<div class="card">` blocks, `display:none` by default | ~25 | Additive |
| `profile_template.html` — JS | Generalize `renderCivicAffiliations()` into a config-driven renderer; add caps/expanders/spectrum pairing | **~180** | **Refactor** (~90 replaced) |
| `build_candidate.py` | None — payload shape flows through unchanged | 0 | — |
| Database | **None.** All data already present | 0 | — |

**Total ≈ 395 lines, roughly 40% refactor of existing rendering code.**

**Not additive-only**, contrary to the brief's assumption. `renderCivicAffiliations()` and the payload builder both have to be generalized, and both are currently coupled to the four-bucket shape.

**Regeneration:** all 22 profiles need `build_candidate.py` re-runs (~30–40s each, ~15 min total), because the payload shape changes. Sitting-member profiles gain content too — Watson picks up 199 findings, Ellis 34.

**Time estimate**

| Phase | Est. |
|---|---|
| Payload refactor + category mapping | 2.5 h |
| Renderer generalization | 3 h |
| CSS + markup | 1.5 h |
| Data-quality filters (§A.3: LinkedIn, unverified, political dedup) | 2 h |
| Regenerate 22 profiles + spot-check | 1 h |
| Mobile/responsive QA | 1 h |
| **Total** | **~11 h, 2 working days** |

Add ~3 h if the `political` split (§A.3.1) needs a re-tagging pass rather than a query heuristic.

---

## Section D: Open decisions

**D1. Icons — recommend none.** Emoji (🔫, 🛢️) would editorialize; a gun glyph next to a donor's name reads as an accusation. Custom SVGs cost design time for little gain. **Recommend: colored category chips in the brand palette, text only.**

**D2. Grouping — recommend the 3-card structure in §B** over eight flat sections or one mega-card. Open question is whether `business` (372 rows) earns its own card or folds into the existing Top Industries chart as a "leadership roles" annotation. Recommendation: own card, because ownership ≠ employment.

**D3. Confidence treatment — this one needs a schema decision.** `civic_affiliations` has **no confidence column**; confidence lives on `donor_identities.resolved_confidence` (861 high / 421 medium sitewide) and is **per-donor, not per-affiliation**. So "badge medium-confidence findings" is not currently expressible — a donor can be medium-confidence overall while one specific affiliation is rock-solid. Options: (a) render all findings identically and rely on the source link, (b) add a `confidence` column to `civic_affiliations` and backfill from the batch result JSONs, which do carry per-record confidence, (c) badge by source quality instead of confidence — LinkedIn/self-reported vs. institutional. **Recommend (c) now, (b) as a follow-up** — source quality is what a reader can actually evaluate.

**D4. Suppression rules.** Per-card caps (25 business / 20 civic) with expanders — agreed? And do LinkedIn-only rows get suppressed, badged, or shipped as-is?

**D5. Cross-candidate visibility.** Expanding the template changes **every** profile, not just D1. Watson gains 199 findings and Ellis 34 — including `political` rows describing sitting officials' donors' partisan giving. Ship sitewide at once, or gate the new cards to candidate profiles first and roll to sitting members after review? **Recommend sitewide** — showing more scrutiny of challengers than incumbents is its own bias.

---

## Section E: Recommended ship order

Ordered by transparency value per unit of risk, not by row count.

**Phase 1 — "Policy & Advocacy Ties" (~5 h).** 88 rows across gun control/rights, defense, pro-Israel, healthcare, plus migrating the existing oil & gas and AIPAC buckets in. Highest-scoring categories, smallest volume, cleanest sourcing. Makes the spectrum coverage visibly balanced. Delivers the single biggest honesty improvement: Ramos, Brown, and Riggins stop rendering a blank section.

**Phase 2 — card fixes from §B.4 (~2 h).** Retitle to "Documented," resolve the `jewish_civic` half-display, handle LinkedIn-only sourcing. Do this *before* adding volume — these are corrections to what already ships.

**Phase 3 — "Industry & Business Ties" (~3 h).** 375 rows. Needs the ownership-vs-employment rule enforced so it doesn't restate the Top Industries chart.

**Phase 4 — `political`, after the dedup split (~3 h + re-tagging).** Genuinely valuable (lobby registrations, campaign roles) but ~half is FEC-restatement the partisan chart already does better. Do not ship raw.

**Phase 5 — "Community & Civic Roles," collapsed by default (~2 h).** 704 rows, lowest score, highest noise. Reasonable to defer indefinitely; the value is context, not accountability.

**Ship Phases 1+2 together** — Phase 2 fixes what Phase 1 touches, and shipping Phase 1 on top of an uncorrected card compounds an existing problem.

---

## Appendix — verification

Every figure here comes from direct read-only queries against `austin_finance.db` and direct reads of `generate_profile_data.py`, `profile_template.html`, `travis_research/_apply_results.py`, `d1_research/_apply_d1_results.py`, and `travis_research/_research_instructions_v3.md` on 2026-07-18. Nothing was written except this file. `travis_research/` and `d1_research/` were read but not modified.

**v3 taxonomy vs. reality.** The instructions specify: `aipac_direct | pro_israel | liberal_zionist | jewish_civic | palestine_solidarity | pro_palestine_advocacy | oil_gas | gun_rights | gun_control | military_defense | civic | business | political`.

- **Opus stayed in-taxonomy.** No unanticipated categories appeared in the D1 delta.
- **Legacy categories predate v3** and are not in its vocabulary: `oil_gas_major`, `oil_gas_independent`, `oil_gas_services`, `oil_gas_legal`, `oil_gas_industry_association`, `oil_gas_academic`, `healthcare`, `industry`, `jewish_political`. Any category mapping must handle these or they silently vanish — the same failure mode this whole document is about.
- **Two taxonomy categories have zero rows sitewide:** `palestine_solidarity` and `pro_palestine_advocacy`. They were searched under the mandatory checklist (FEC PAC search ran on 606/606 D1 donors) and returned nothing. **These are absences in the data, not unsearched categories** — worth stating explicitly on the page, because a blank pro-Palestine column next to a populated pro-Israel one will otherwise read as selective reporting.

**Evidence-text length:** `role` averages 53 chars (max 631); `notes` averages 589 chars (max 2,485). The notes field is long-form prose, not chip-sized — any design that renders it inline needs clamping and an expander, which is why B.1–B.3 all specify a 2-line clamp.
