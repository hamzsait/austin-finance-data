# D3 Expansion Plan — 2026 Austin City Council District 3

**Status:** Scoping document. Nothing executed. No code, folders, or commits produced.
**Date:** 2026-07-18
**Scope:** Add `/austin/district3/` as the second instance of the race-view architecture shipped for D1 in commit `ef17abe`, plus one new candidate profile (Shah).
**Note:** supersedes an earlier same-day draft of this file; that draft's findings were verified and merged (a backup sits in the session scratchpad). Material corrections from it: Shah is **not** single-sourced (she's on the City Clerk's treasurer list), and there are **two** "open seat" hardcodes, not one.

---

## 0. What's different from D1 — read this first

The D1 architecture (`austin_races.json` + `race_template.html` + `build_race.py`) was built generic and it holds up: adding D3 really is close to "one JSON entry + one command." The differences are in the shape of the race, not the architecture:

1. **This is an incumbent-defense race, not an open seat.** José Velásquez (elected Dec 2022) is seeking re-election; Neha Shah is his first and only confirmed challenger. There is no `outgoing` block (the template skips it when absent — verified conditional at `race_template.html:400`), and `kind` must be something other than `"open"`. Three small presentation gaps follow from D1 never exercising this path — two "an open seat" hardcodes and a missing INCUMBENT badge (§E.3).

2. **The field is two candidates, not seven — and both have finance data.** No Nahas-style zero-data placeholder, no Rogers-style omission call. The grid and comparison strip render fine with two entries.

3. **The incumbent already has a live profile.** `/austin/velasquez/` has been published since the officeholder builds, is cycle-aware (`CANDIDATE_CYCLES['velasquez']` has a "This Cycle" selector), and needs **zero changes**. Only Shah needs a new profile. D1 built five from scratch.

4. **Landing page work is zero.** The "2026 Races" section of `/austin/` is driven entirely by `austin_races.json` (`austin/index.html:439–478`) — the D3 card, the "2 races · N candidates" summary line, and the section itself update automatically when the JSON entry lands.

5. **Scrub-pool math has a new wrinkle: basis.** D1 candidates had essentially no pre-2023 history, so pool = lifetime was uncontroversial. Velásquez's 2022 donor base means lifetime vs cycle-2025+ roughly doubles or halves the cost (§D). This is the one real money decision.

6. **Coverage dedup must now include the D1 batches.** The D1 prep script deduped against `travis_research/donorbatch*.json` + the pilot. A copied D3 prep script must also glob `d1_research/d1batch*.json` (31 batches) or it will re-scrub donors D1 already covered. All §D numbers already account for that.

7. **The D1 plan's profile-page enrichments (its B4–B6) never shipped.** Checked directly against `profile_template.html`: no race-context banner, no campaign-website link, no thin-data guard exists on any live D1 candidate profile — and Riggins shipped a full profile on 2 donors / $800 despite the D1 doc recommending against it. Two implications: that line item doesn't recur here (it was never built), and there is no code-level publishability gate to worry about for Shah — precedent is that thin data ships as a full profile. (Shah, at 57 donors, isn't thin by any standard D1 applied anyway.)

8. **Effort is roughly a quarter to a third of D1's.** ~2.5–4 focused hours vs 10–12, because the race template, build driver, landing section, and candidate-profile plumbing all shipped with D1 — and Velásquez's portrait already exists (`au3`), so there's no photo-latency dependency on the incumbent side.

---

## A. Race context

### A.1 The race

**José Velásquez is seeking re-election.** First-term incumbent, elected December 2022; marketing strategist, East Austin native. Not term-limited. Confirmed across 3+ independent sources: Austin Free Press (Feb 2, 2026 — "the sole incumbent who has not yet drawn a challenger"), Austin Politics Newsletter (Jan 30, 2026), the Austin Bulldog (July 2026), plus his still-active treasurer appointment on the Clerk's master list.

**Neha Shah, 40, is his first and — as of the July Bulldog piece — only declared challenger.** Software technology developer, startup entrepreneur, bilingual children's-book author; moved to Austin January 2016; D3 resident; first run for office. Her treasurer appointment appears on the City Clerk's master list (page dated 7/16/2026), and the city's own filings show her as an active recipient (57 donors, $10,985 — §C), so her candidacy is primary-source confirmed, not merely reported.

District 3 covers Central-East and East Austin. It was last on the ballot in 2022, so Velásquez is defending in the first cycle after his election.

**Fundraising posture:** Velásquez raised ~$27K in 2025 with ~$32K cash on hand as of the January press accounts — described by the Free Press as notably less than the other defending incumbents (Alter $83K, Ellis $100K, Qadri $182K on hand). Our DB puts his 2025+ raise at $89,251 through 6/30 — meaning H1 2026 ($61K) roughly tripled his 2025 pace. That acceleration is a story the site's data can uniquely show.

### A.2 Election calendar

Identical to D1 — same citywide calendar. Filing opens Mon **Jul 20, 2026**; filing deadline Mon **Aug 17, 2026, 5 p.m.**; early voting Oct 19–30; general (nonpartisan, 50%+1) Tue **Nov 3, 2026**; runoff Sat **Dec 12, 2026**. Nobody is on the ballot yet — both are declared candidates with treasurer appointments. The filing-status banner (already forced by the template) does the disclosure work.

### A.3 2022 D3 context

- Open seat to succeed Sabino "Pio" Renteria; multi-candidate field (Velásquez, Daniela Silva, Gavino Fernandez Jr., José Noé Elías, and others). No majority in the general — Velásquez led with roughly 36%, Silva ~34% (news-reported, not primary-verified this session).
- **Runoff (Dec 13, 2022): Velásquez def. Silva 53%–47%** (KUT, KVUE, KXAN — consistent). Competitive, not a blowout.
- **Money:** Velásquez raised **$167,669** in 2022 per `austin_finance.db` — cross-checks the Bulldog's reported "$168,000 raised, $158,000 spent" almost exactly. Silva raised **$78,390** (also in our DB, `Silva, Daniela M.`).
- No sign Silva is running again: no treasurer appointment, no coverage.

### A.4 Coverage landscape

Same as D1: **the Austin Bulldog / Austin Free Press is the workhorse** (the Bulldog's own site 403s automated fetch; the Free Press mirror carries the same pieces and fetches fine). Austin Politics Newsletter has the most analysis but is advocacy-inflected. **No KUT / Austin Monitor / Statesman coverage of the 2026 D3 race found** — 2022 D3 pieces from those outlets must not be cited as 2026 coverage (same contamination risk the D1 plan flagged).

One editorial landmine, recommended **omitted** from the site: the Feb 2 Free Press piece raised questions about Velásquez's listed residence (property owned by a third party; he didn't respond to their inquiry). Single-outlet, unresolved, not campaign-finance data. Flagged as §G.7 so it's a decision, not an oversight.

---

## B. Candidate roster

### B.1 Confirmed (2+ sources) — both go on the page

| Candidate | Sources | Website | Portrait |
|---|---|---|---|
| **José Velásquez** (incumbent) | Free Press, Austin Politics Newsletter, Bulldog, Clerk master list | none found for 2026 — verify at execution (2022 cycle used velasquezforaustin.com); his card renders from live stats either way | Already have: photo key `au3`, present in every `PHOTOS` set. **Zero photo work.** |
| **Neha Shah** | Bulldog ("Velasquez finally draws a challenger," July 2026) + own campaign site (nehaforatx.com) + Clerk master list (7/16/2026) + her own city finance filings | nehaforatx.com | Multiple photos on her campaign site. Not downloaded — user handles portraits manually with campaign approval, same as D1. Initials-tile fallback until then. |

### B.2 Single-sourced / dropped out / placeholders

None. Nobody has dropped out, nobody is single-sourced (Shah clears the bar Rogers failed on D1 — the Clerk list and her filings are primary sources), and both candidates have data, so there are no placeholder cards.

### B.3 Unresolved — check before publishing

The Clerk's master list (7/16/2026) shows six recent treasurer filers whose district could not be determined from any indexed source: **Marcus W. "Mark" May, Adam Finkenbinder, Chelsea M. Ozorkiewicz, Carol A. Guthrie, Doug R. Addison, Brenda Malik**. (A seventh recent filer, Katherine Kam, is confirmed District 9.) Any of them could be an uncovered D3 entrant. **Executor: before publishing, check the Bulldog's candidate coverage manually (its site blocks automated fetch; a browser works) or the Clerk's individual CTA PDFs, and confirm none of the six filed for District 3.** The same check helps close out rosters for the eventual D5/8/9 pages.

Side-finding for D1, flagged as a separate task: **Kyra Rogers now appears on the Clerk's master list**, which expires the D1 page's stated reason for omitting her.

---

## C. Finance coverage table

Queried directly against `austin_finance.db` this session (data through 2026-06-30; positive contributions only; donor counts are unique `donor_id`s). Cycle basis = contributions from 2025-01-01 forward, matching `cycle_start_year: 2025`.

| Candidate | Recipient string | Total donors | Total raised | Cycle donors | Cycle raised (2025+) | Already scrubbed for affiliations |
|---|---|---|---|---|---|---|
| Velásquez | `Velasquez, Jose` | 871 | $263,104 | 313 | $89,251 | 75/871 lifetime (**9%**); 34/313 cycle (11%) |
| Shah | `Shah, Neha` | 57 | $10,985 | 57 | $10,985 | 0/57 (**0%**) |

Detail worth having in front of you at execution:

- **Velásquez by year:** 2022 — 917 positive rows / $167,669 / 661 donors; 2024 — 17 rows / $6,184 (officeholder fundraising; D3 wasn't on the 2024 ballot); 2025 — 118 rows / $28,131 (first gift 2025-02-06); 2026 — 210 rows / $61,120 through 6/30. Plus 31 null-`donor_id` rows excluded from donor counts.
- **Shah:** 59 positive rows, first gift **2026-05-25**, last 2026-06-30 — five weeks of filings. One null-`donor_id` row. 57 unique donors clears the D1 plan's 25-donor thin-data threshold comfortably; she gets a real profile, not a Riggins-style shell.
- **Enrichment is already done, as with D1:** FEC match is **100% for both** (871/871 and 57/57 donors — the global enrichment passes swept them up). Partisan lean present: 608 of Velásquez's donors, 19 of Shah's. Industry resolution: Velásquez **89%** of lifetime donors / 93% of cycle donors — strong; Shah **53%** (30/57) — soft, the same newer-filings problem Anderson (57%) and Brown (70%) had on D1. **Employer backfill on Shah's ~27 unresolved donors is the biggest single data-quality item, and it's small** (existing `fix_unclassified_employers.py` / `auto_classify_employers.py` path).
- **Cycle Top Industries the race page will render** (previewed with `build_race.py`'s exact query): Velásquez — Real Estate $30,966, Finance $8,725, Nonprofit/Advocacy $5,760, Government $5,316. Shah — Technology $1,871, Not Employed $1,763, Healthcare $946, Legal $422. Both render meaningful bars.
- Growth expected: 30-day and 8-day pre-election reports land in October; the same mid-race-snapshot labeling caveat as D1 applies.

---

## D. Affiliation-scrub scope

Methodology mirrors `d1_research/_prep_d1_batches.py` exactly: pool = donors at/above threshold across the race's campaigns, minus donors already **submitted to any prior research batch** (travis donorbatch 1–20 + pilot + d1batch 1–31 — 2,185 covered donor_ids), minus donors already **present in `civic_affiliations`** by canonical name (777 names; that table keys on name, not donor_id). Batches of 20; observed cost **~$9.14/batch** on the D1 run.

Prior coverage barely touches this pool: 75 of Velásquez's 871 donors (9%), 0 of Shah's 57. Note that the earlier `velasquez_batch_1–4.txt` research was targeted ADL/AIPAC/oil spectrum work on his pre-2025 base, not the civic-affiliation scrub — whatever it contributed is captured through the `civic_affiliations` name check, and his 2025+ donors are a mostly new set.

Combined pool, both candidates, deduplicated:

| Threshold | Lifetime pool | Lifetime uncovered | Batches | Cost | Cycle-2025+ pool | Cycle uncovered | Batches | Cost |
|---|---|---|---|---|---|---|---|---|
| Full pool | 928 | 853 | 43 | ~$393 | 370 | 336 | 17 | ~$155 |
| **≥$100** | 624 | **558** | **28** | **~$256** | 286 | **256** | **13** | **~$119** |
| ≥$250 | 405 | 350 | 18 | ~$165 | 194 | 170 | 9 | ~$82 |
| ≥$500 | 148 | 124 | 7 | ~$64 | 65 | 55 | 3 | ~$27 |

**Recommendation: ≥$100 (the threshold the user picked on D1) on the lifetime pool — 28 batches, ~$256.** Lifetime is the faithful mirror of D1's pool definition (all-time giving across the race's campaigns; D1's just happened to have almost no pre-2023 history), and the affiliation cards on `/austin/velasquez/` display lifetime donors — a cycle-only scrub would leave the base behind 89% of his money unscrubbed while the profile implies coverage. **The budget alternative is ≥$100 cycle-only (13 batches, ~$119)** if the goal is only the race page. Decision flagged as §G.1. Timing follows the D1 precedent: deferred until the Travis Phase 2 pipeline is free — a follow-up batch on a warm pipeline, not a launch blocker.

Prep-script notes (copy `_prep_d1_batches.py` → `d3_research/_prep_d3_batches.py`):
- `CANDIDATES = ["Velasquez, Jose", "Shah, Neha"]`
- Add `d1_research/d1batch*.json` to the covered-ids glob (see §0.6 — the D1 script only globs travis batches).
- Lifetime basis: no year filter, as in D1. Cycle basis: add `AND cf.contribution_year >= 2025`.
- Output format unchanged, so the v3 instructions and the `_apply_d1_results.py` apply-path pattern work as-is.

---

## E. Site changes required

### E.1 `austin_races.json` — add one race entry

Append to the `races` array. Execution-ready except the two marked TODOs:

```json
{
 "race_id": "district3",
 "seat": "District 3",
 "title": "Austin City Council District 3",
 "kind": "incumbent",
 "cycle_start_year": 2025,
 "data_through": "2026-06-30",
 "election_date": "2026-11-03",
 "runoff_date": "2026-12-12",
 "early_voting": "2026-10-19 to 2026-10-30",
 "filing_opens": "2026-07-20",
 "filing_closes": "2026-08-17",
 "ballot_final": false,
 "intro": "José Velásquez, who has represented District 3 since 2023, is seeking a second term. He won the seat in December 2022, defeating Daniela Silva in a runoff with 53% of the vote. The district covers Central-East and East Austin.",
 "context_note": "Candidate filing runs July 20 - August 17, 2026. Everyone listed here has declared and appointed a campaign treasurer, but filing has not closed. Expect additions, and expect some listed candidates not to complete filing.",
 "candidates": [
  {
   "slug": "velasquez",
   "name": "José Velásquez",
   "recipient": "Velasquez, Jose",
   "photo": "au3",
   "website": null,
   "bio": "East Austin native and marketing strategist; elected to this seat in 2022, defeating Daniela Silva in a December runoff. Seeking a second term.",
   "status": "incumbent",
   "has_data": true
  },
  {
   "slug": "shah",
   "name": "Neha Shah",
   "recipient": "Shah, Neha",
   "photo": null,
   "website": "https://www.nehaforatx.com",
   "bio": "Software technology developer, startup entrepreneur and bilingual children's book author; District 3 resident since 2016. First run for office.",
   "status": "declared",
   "has_data": true
  }
 ],
 "omitted": []
}
```

TODOs at execution: **(1)** verify whether Velásquez has a live 2026 campaign site and fill `website` (2022 used velasquezforaustin.com; don't link it without confirming it's current); **(2)** re-run the §B.3 check on the six unresolved Clerk filers and extend `candidates`/`omitted` if any are D3. There is deliberately **no `outgoing` key**. `status: "incumbent"` is a new value (D1 used only `"declared"`); it drives E.3 and degrades gracefully if E.3 is skipped — unknown statuses fall through to the current CANDIDATE badge.

### E.2 Render

```
python build_race.py --race district3
```

(python = `C:/Users/Hamza Sait/AppData/Local/Microsoft/WindowsApps/python3.13.exe`.) Note `build_stats()` recomputes `austin_race_stats.json` for **every** race — D1's numbers refresh against the current DB in the same run. Desirable, but it means D1's published stats can change in this commit if new filings were ingested since the D1 render.

### E.3 Generalization gaps found (flagged, not papered over)

Verified by direct read of the shipped code. `build_race.py` itself has no district1 hardcodes in executable logic, and `race_template.html` contains zero occurrences of "district1" — the architecture generalizes. Four real items:

1. **`build_race.py` → `og_meta_for()` hardcodes "an open seat"** in the race page's OG description. False for D3; ships a wrong social-share description. Fix: branch on `race["kind"]`, or cleaner, add an optional `og_context` string field to the race entry with a generic fallback ("a seat on the November 2026 ballot"). ~6 lines.
2. **`build_candidate.py:84` (the `og_meta_for` fallback for 2026 candidates) also hardcodes "an open seat"** — every `CANDIDATE_SLUGS` profile's OG description says the candidate "is running for Austin City Council {seat}, an open seat." True for all five D1 profiles, false for Shah's. Same fix: branch on the race's `kind` (the function already has the `race` object in hand). Must land **before** Shah's profile is built. Backward-compatible — D1's `kind` is `"open"`, so existing output is unchanged; no D1 re-render needed.
3. **`race_template.html` → `cardHtml()` has no incumbent badge** — every candidate with data gets `CANDIDATE`, without data `PENDING` (lines 292–297). Velásquez should read `INCUMBENT`. Branch on `c.status === 'incumbent'`; reuse the badge styling with one new CSS rule. ~8 lines.
4. **Card subtitle** (`race_template.html:317`) reads `"District 3 Candidate"` for everyone, incumbent included. Technically true, but "District 3 · Incumbent" is more informative. Same `c.status` branch as #3. ~2 lines.

Cosmetic, fine to leave: the non-open eyebrow renders "Council race · General Nov 3, 2026" (`race_template.html:384`) — accurate, works (see §G.2 on whether `kind` deserves richer labels before D5/8/9 arrive). The `PHOTOS` set at `race_template.html:269` already contains `au3`. Because the template is materialized per race, applying #3/#4 means also re-running `--race district1 --html-only` so both pages ship from the same template.

### E.4 Landing page (`/austin/`)

**Zero work.** Confirmed by direct read — the section is commented "driven entirely by austin_races.json" and fetches `austin_races.json` + `austin_race_stats.json` at runtime. The D3 card appears automatically.

### E.5 Shah profile at `/austin/shah/` (flat URL, per the D1 architecture decision)

No slug collision (`shah` is unused — checked `austin/` and `austin_landing.json`). Four dict entries + one command:

| Change | File / location |
|---|---|
| Add `"shah"` to `CANDIDATE_SLUGS` | `build_candidate.py:118` |
| `'shah': [{'label': 'This Cycle', 'election_year': 2026, 'start_year': None, 'end_year': None}]` in `CANDIDATE_CYCLES` | `generate_profile_data.py` (~line 118, with the D1 candidate entries) |
| `'shah': 'Austin City Council · District 3 Candidate'` in `OFFICE_OVERRIDE` | `generate_profile_data.py` (~line 221) |
| `'shah': 2026` in `CANDIDATE_MIN_YEAR` | `generate_profile_data.py` (~line 224) |

Then, after E.3 item #2 and the employer backfill (§C):

```
python build_candidate.py --recipient "Shah, Neha" --slug shah
```

`CANDIDATE_TEMPLATE_SUBS` ("Total Raised" / "all filings" hero framing) and the OG lookup through `austin_races.json` both key off `CANDIDATE_SLUGS` and generalize with no further changes (verified at `build_candidate.py:62–92, 182–184`).

### E.6 Velásquez profile

**No changes.** Live at `/austin/velasquez/`, cycle-aware ("This Cycle" = 2023+ → election 2026), keeps its officeholder framing and its `austin_landing.json` entry. The D1 plan's deferred profile↔race cross-link banner stays deferred; if ever built, his profile and Shah's get it together.

### E.7 Not needed

No new OG image (race pages share `og-austin.png`; per-candidate OG cards for Shah can follow the existing `assets/og/card.html` screenshot process when her headline stats settle). No redirect stubs. No `austin_landing.json` changes (candidates stay out of the officeholder roster, per the D1 decision). No `PHOTOS` additions until Shah's portrait arrives — then add her key to the three `PHOTOS` sets (`race_template.html`, `austin/index.html`, plus the landing set if used).

### E.8 Execution order

Roster check (§B.3 + website TODO) → both OG hardcode fixes (E.3 #1–#2) → badge/subtitle fixes (E.3 #3–#4) → employer backfill on Shah → Shah dict entries + profile render (E.5) → `austin_races.json` entry (E.1) → `build_race.py --race district3` + `--race district1 --html-only` re-render → QA both race pages + Shah profile on mobile → commit + push (standing rule: pre-push secret scan). Scrub runs separately whenever greenlit (§D).

---

## F. Effort estimate

| Work | Files touched | Est. |
|---|---|---|
| Roster close-out: six unresolved Clerk filers + Velásquez website check | — | 30–45 min |
| OG "open seat" fixes (both files) | `build_race.py`, `build_candidate.py` | 30 min |
| INCUMBENT badge + card subtitle | `race_template.html` | 30 min |
| Employer backfill on Shah's ~27 unresolved donors | existing scripts | 30 min + runtime |
| Shah: 4 dict entries + profile render + QA | `build_candidate.py`, `generate_profile_data.py` | 45 min |
| `austin_races.json` district3 entry | existing file | 20 min |
| Render D3 + re-render D1 from updated template | — | 10 min |
| Landing section | — | 0 (automatic) |
| Mobile QA, commit, push | — | 30 min |

**Total: ~2.5–4 focused hours.** No photo-latency dependency for launch (Velásquez's portrait exists; Shah falls back to an initials tile until her campaign supplies one).

**Affiliation scrub, costed separately (§D):** recommended ≥$100 lifetime = **~$256** (28 batches); budget alternative ≥$100 cycle-only = ~$119. Plus the prep-script copy (~20 min) and the usual batch runtime/apply pass.

**Deferred, matching D1:** endorsements, profile↔race cross-link banner, `/austin/races/` index (revisit when a third district lands).

---

## G. Judgment calls to flag for user

1. **Scrub basis — the one real money decision.** Lifetime ≥$100 (~$256) covers the donor base Velásquez's live profile actually displays; cycle-only ≥$100 (~$119) covers just the 2026-race donors. Recommendation: lifetime (§D). D1 never faced this because its candidates had no history.
2. **Incumbent presentation.** Recommend the INCUMBENT badge + "District 3 · Incumbent" subtitle (E.3 #3–#4). The zero-code alternative — Velásquez badged CANDIDATE like everyone else — is defensible as neutral but reads as an error on an incumbent-defense page. Related: is `kind: "incumbent"` + the generic "Council race" eyebrow enough, or should `kind` grow richer labels now, before D5/8/9 (which may also be incumbent-defended) multiply the retrofit cost? Cheap to settle either way.
3. **Cycle window footnote.** The race page's 2025+ basis excludes Velásquez's $6,184 of 2024 officeholder fundraising, and his own profile's "This Cycle" selector starts at 2023 — the two pages will show different "this cycle" numbers. Recommend keeping 2025+ on the race page (D1 convention; apples-to-apples with Shah) and adding a one-line methodology note.
4. **Sort default.** D1 chose alphabetical with a raised-DESC toggle; no new argument for changing it. Alphabetical puts Shah above Velásquez — that's what neutral means, and the toggle exists.
5. **Publish timing.** D1 shipped 2026-07-18, before filing even opened, with the banner doing the disclosure work — that's now precedent, and D3's roster (an incumbent plus an already-fundraising challenger) is more stable than D1's seven-way field. Recommend: publish on the same basis. New entrants remain possible through Aug 17; the roster check in §B.3 is the mitigation.
6. **The six unresolved Clerk filers.** If one is D3, the roster changes at or right after launch. Recommend resolving before publishing — a 30-minute manual check.
7. **The residency question.** The Free Press's unresolved item about Velásquez's listed address: recommend **omit** — single-outlet, non-finance, and the site's credibility rests on staying in its data lane.
8. **Shah's industry coverage (53%).** Recommend running the employer backfill before her profile ships (it's in the estimate). Shipping without it weakens her Top Industries chart the way Anderson's 57% did on D1.
9. **D1 follow-ups surfaced by this scope, outside D3:** (a) Kyra Rogers is now on the Clerk's master list — the D1 page's stated reason for omitting her has expired (spun off as a separate task); (b) the thin-data guard the D1 doc recommended (its B6) never shipped and Riggins has a full profile on 2 donors / $800 — decide whether that's now accepted policy or debt.

---

## Appendix — verification notes

**Verified against primary sources this session:** Shah's treasurer appointment (Clerk master list, page dated 7/16/2026); Shah's candidacy, bio, and platform (own campaign site); all finance figures, enrichment coverage, and scrub-pool counts (direct read-only `austin_finance.db` queries — recipient strings `Velasquez, Jose` and `Shah, Neha` confirmed exact); all architecture claims (direct reads of `austin_races.json`, `build_race.py`, `race_template.html`, `build_candidate.py`, `generate_profile_data.py`, `austin/index.html`, `d1_research/_prep_d1_batches.py`).

**Cross-checked:** DB 2022 Velásquez total ($167,669) vs Bulldog-reported "$168,000 raised" — match.

**News-reported, not primary-verified:** Velásquez seeking re-election (three independent outlets; consistent with his still-active CTA, but he has made no primary-source declaration we could fetch); Shah's age and biographical details; 2022 general percentages and field composition; the 2022 runoff margin (KUT/KVUE/KXAN, consistent).

**Could not verify:** Ballotpedia returned an empty shell on every fetch (same failure mode as D1); theaustinbulldog.org 403s automated fetch (content recovered via search snippets and the Austin Free Press mirror); district assignments for the six recent Clerk filers in §B.3; the in-app browser's text extraction was unavailable this session (persistent policy-check errors), which is why the Bulldog pieces could not be read in full — the executor should read them in a normal browser during the §B.3 check.

**Contamination risk:** 2022 D3 coverage (KUT candidate-issues piece, KVUE/KXAN results stories) must not be cited as 2026 coverage. Aggregator sites (austinmayor.com-style): do not cite.
