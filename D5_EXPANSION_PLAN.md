# D5 Expansion Plan — 2026 Austin City Council District 5

**Status:** Scoping document, written immediately before execution in the same session.
**Date:** 2026-07-19
**Scope:** Add `/austin/district5/` as the third instance of the race-view architecture (D1 `ef17abe`, D3 PR #6), plus one new candidate profile (Weinberg). Mirrors the D3 flow: worktree `austin-finance-data-d5`, branch `d5-race-page`, DB copied in, plan committed first, GitHub issue tracks execution.

---

## 0. What's different from D3 — read this first

1. **Three candidates, one with zero finance data.** Incumbent Ryan Alter and challenger David Weinberg both file with the city; Farrah Abraham has **no city finance filings at all** — she gets a Nahas-style placeholder card (`slug: null`, `has_data: false`, `placeholder_note`), the first since D1.
2. **No template or build-script work.** D3 shipped the incumbent generalization (OG `race.kind` branch, INCUMBENT badge, incumbent subtitle, landing label) and the repo-relative path fixes. D5 exercises those paths as-is: one JSON entry, one profile, renders.
3. **The incumbent's profile exists and needs zero changes** (`/austin/alter/`, photo key `au5`, cycle-aware). Same as Velásquez on D3.
4. **Weinberg's headline money is a self-loan, not contributions.** Press (Community Impact 1/20, Free Press 2/2): ~$11K raised + **$275K self-loan**, $270K+ cash on hand — the cash leader in the race. Our contributions-only DB shows $16,035. Without a note, the race page would materially understate his position → one sentence in the race `intro` (§E.1, G.2).
5. **Abraham has an unresolved residency question in press** (Free Press 2/2 and Austin Politics Newsletter 1/30 both report her listed address is not in D5). Same §G call as Velásquez's residency item on D3: **omit from the site** — not campaign-finance data, and eligibility resolves at filing. Flagged §G.3 so it's a decision, not an oversight.

## A. Race context

- **Incumbent-defense** (`kind: "incumbent"`). Ryan Alter, 35, attorney and former Texas Senate policy staffer, elected Dec 2022, seeking a second term. Confirmed: Free Press (2/2), Austin Politics Newsletter (1/30), Community Impact (1/20), Bulldog (snippet), active officeholder CTA (treasurer Anna M. Riojas, 3/17/2022).
- **2022 context:** six-way general, no majority; **Alter def. Stephanie Bazan 59.6%–40.4% in the Dec 13, 2022 runoff** (KUT; Free Press ~60%). Alter spent ~$206K on that race (Free Press). District covers South-Central Austin (Zilker, Barton Hills, South Lamar…).
- **Calendar:** identical to D1/D3 — filing Jul 20–Aug 17; early voting Oct 19–30; general Nov 3; runoff Dec 12. Nobody on the ballot yet; the standard filing banner does the disclosure work.
- **Coverage:** Free Press/Bulldog again the workhorse; Community Impact and KXAN/Fox7 (Abraham entry/re-file) add second sources. APN advocacy-inflected as usual. No 2026-race coverage from KUT/Monitor/Statesman found.
- **Fundraising posture per press:** Alter $115K+ CoH on the Jan 15 filing (raised only ~$6.9K in H2 2025; an earlier Bulldog piece said $83K CoH end-2023 — discrepancy unresolved in coverage, our DB is the tiebreaker for raised amounts); Weinberg ~$11K raised + the self-loan; Abraham zero reported.

## B. Candidate roster (all 2+ sources; no additional filers found)

| Candidate | Status | Website | Photo | Notes |
|---|---|---|---|---|
| **Ryan Alter** | incumbent | https://www.ryanforatx.com (live, maintained, officeholder-tense; not explicitly "2026"-branded — good enough to link) | `au5` (exists everywhere) | CTA active since 2022 |
| **David Weinberg** | declared (CTA 9/9/2025, treasurer Jim Marston) | https://davidforatx.com | none — initials tile (campaign-approval convention) | 48, public-affairs consultant; ex-ED Texas League of Conservation Voters; Brennan Center consultant; led Save Zilker Park PAC; Barton Hills/Zilker resident |
| **Farrah Abraham** | declared (CTA 1/14–15/2026, self-treasurer; initially filed for mayor, re-filed D5) | https://farrahabraham.com/farrah-for-austin (live, D5-specific) | none — initials tile | 34, television personality, Austin business owner; **no finance filings — placeholder card**; residency caveat §G.3 |

Additional-filers check: none for D5 (the "seven more candidates" wave is D1/D3/D8/D9; Hudsky is D8 per Bulldog correction). Field can grow through Aug 17 — banner covers it.

## C. Finance coverage (queried this session, data through 2026-06-30, positive contributions, unique donor_ids)

| Candidate | Recipient string | Donors | Total | Cycle-2025+ donors | Cycle raised | Industry res. | FEC match |
|---|---|---|---|---|---|---|---|
| Alter | `Alter, Ryan` | 839 | $369,745 | 356 | $118,264 | 785/839 (94%) | 836/839 |
| Weinberg | `Weinberg, David M.` | 116 | $16,035 | 116 (first gift 2025-10-17) | $16,035 | 103/116 (89%) | 109/116 |
| Abraham | — | 0 | — | — | — | — | — |

**Do not confuse `Alter, Alison B.`** (former D10 member, 2016–2022 filings) with `Alter, Ryan`.

**Weinberg employer backfill (§E.4):** 13 unresolved donors, mostly small out-of-state gifts with crisp employers (NY State Assembly, NeighborWorks America, City & County of Denver, Thermo Fisher Scientific, Prevent Cancer Foundation, Griffiss Institute, STCHealth, Function Health…). Classify the clear ones the D3 way (committed idempotent script, `manual` confidence); leave the 2–3 with nothing usable.

## D. Affiliation-scrub scope (deferred — separate greenlight, per precedent)

≥$100 lifetime pool across both filing campaigns, minus travis/pilot/D1/D3 batch coverage and existing `civic_affiliations` names (118 of Alter's donors already covered):

| Threshold | Uncovered pool | Batches | Est. cost (observed D3 rate ~$4.43/batch) |
|---|---|---|---|
| **≥$100** | **598** | **30** | **~$133** |
| ≥$250 | 406 | 21 | ~$93 |
| ≥$500 | 189 | 10 | ~$44 |

Prep/driver/apply: copy the `d3_research` trio → `d5_research`, `CANDIDATES = ["Alter, Ryan", "Weinberg, David M."]`, add `d3_research/d3batch_*.json` to the covered-ids glob.

## E. Site changes

1. **`austin_races.json`:** one `district5` entry, `kind: "incumbent"`, no `outgoing`. Intro covers the 2022 runoff + one self-loan disclosure sentence (§0.4). Abraham entry mirrors the Nahas placeholder shape exactly.
2. **Weinberg profile** (`/austin/weinberg/`, no slug collision): add to `CANDIDATE_SLUGS` (build_candidate.py), `CANDIDATE_CYCLES` / `OFFICE_OVERRIDE` ("Austin City Council · District 5 Candidate") / `CANDIDATE_MIN_YEAR` (2025 — his filings begin Oct 2025) in generate_profile_data.py, then build (after E.4 backfill; race entry must exist first so his OG description resolves race-aware on the first HTML pass).
3. **Renders:** `build_race.py --race district5`, then `--race district1 --html-only` and `--race district3 --html-only` (shared template is untouched this time, but stats refresh for all races — verify D1/D3 page HTML is byte-stable; if so, skip committing them).
4. **Weinberg backfill script:** `d5_research/_backfill_weinberg_employers.py` (§C).
5. **Landing/photos:** zero work (races section is data-driven; `au5` already in all PHOTOS sets; challengers render initials tiles).

## F. Effort: ~1–2 focused hours (was ~3 for D3 — no template work, no roster mystery).

## G. Judgment calls

1. **Scrub threshold** — recommend ≥$100 lifetime (~$133) when greenlit, matching D1/D3.
2. **Self-loan disclosure** — recommend one neutral sentence in the race intro: contributions-only framing would otherwise misstate the race's cash reality. (Loans aren't in the contributions feed.)
3. **Abraham residency question** — recommend omit (matches D3's §G.7 call on Velásquez's residency item): single-topic eligibility reporting, not finance data; resolves at filing close.
4. **Abraham placeholder** — include as placeholder card (declared + CTA + 2+ sources + live campaign site clears the D1 bar Rogers failed).

## Verification notes

Primary-source: City Clerk CTA facts (master list), all finance numbers (direct DB queries this session, recipient strings verified exact). News-verified: rosters/bios/2022 results (sources per §B), Weinberg self-loan (two outlets), Abraham residency question (two outlets). Not verified: none load-bearing. Bulldog 403s automated fetch as always — Free Press mirror + snippets used.
