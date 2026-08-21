# D8 Expansion Plan — 2026 Austin City Council District 8

**Status:** Scoping document, written immediately before execution in the same session.
**Date:** 2026-07-19
**Scope:** `/austin/district8/` (fourth race-view instance) + two new profiles (Xie, Bowen). Worktree `austin-finance-data-d8`, branch `d8-race-page`, DB copied in, plan committed first, issue tracks execution.

## 0. What's different — read this first

1. **The incumbent is not yet on the ballot path.** Paige Ellis is term-limited and seeking a **rare third term via the charter's petition route** (~5% of D8 registered voters, ~3,000–3,400 signatures, due with her ballot application by Aug 17). As of the latest coverage (Austin Politics, July 1) she's actively gathering with paid canvassers — **not yet submitted**. `kind: "incumbent"` still fits (she's the officeholder defending), the intro explains the petition wrinkle in the same language the D1 intro used for Harper-Madison, and the standard filing banner covers the uncertainty.
2. **Two new profiles, not one:** Xie (660 donors / $105,727, all since June 2025 — nearly matching the incumbent's cycle total) and Bowen (119 / $33,741, of which ~$16K is his **2024 mayoral run** — he gets a Ramos-style prior-cycle selector). Hudsky has zero filings → placeholder card.
3. **Xie backfill already executed in this worktree** (`d8_research/_backfill_xie_employers.py`): her donors put job titles in the employer field; a scoped rules pass took her 75% → **85%** (70 classified, 98 generic/blank left). Bowen (97%) and Ellis (93%) need nothing.
4. **Ellis's website is live but stale-2022** ("November 8th ballot", © 2022) with an active donate page. Linked anyway (it's her real campaign domain) — flagged §G.2.

## A. Race context

- Ellis, 40, environmental/PR professional; won D8 in **Dec 2018 runoff 56–44 over Republican Frank Ward** (flipping the seat), **re-elected outright 2022: 57.8% vs Richard Smith 28.4%** (no runoff). Term ends Jan 2027. Endorsed by 16 electeds incl. Fuentes, Vela, R. Alter, Qadri.
- **Xie, 38** — ATCEMS commander, ICU nurse, ~6 years president of the Austin EMS Association; D8 homeowner since Sept 2024; campaign manager Joe Cascino (Watson's mayoral CM); 150+ endorsements; running left of Ellis — press frames it as a **Dem-v-Dem** contest. CTA 6/16/2025.
- **Bowen, 70** — retired USAF veteran, 45-year construction manager, Austin Neighborhoods Council president, Board of Adjustment chair; ran for mayor 2024 (~$17K spent); transparency/anti-developer lane. CTA 8/21/2024 (amended 4/2/2026 for D8).
- **Hudsky, 61** — Czech-born Army veteran, running as the self-described conservative in the field. CTA 2/5/2026. No website, no finance reports. (An Oct 2023 peace bond, issued and dismissed, appears in press — **omit**, same §G reasoning as prior districts' non-finance items.)
- Additional filers: none (Clerk CTA list + finance-filer list + press cross-checked). Calendar identical to D1/D3/D5.
- Press money notes (Feb 2026): Ellis ~$74K raised / $100K+ CoH (incl. $30K self/spouse loans); Xie $61K+ raised + $25K self-loan / ~$72K CoH. Both sides' loans are invisible to contributions data — worth one intro sentence like D5's (§G.3).

## B. Finance (queried this session, through 2026-06-30)

| Candidate | Recipient | Donors | Total | Cycle-25+ | Industry res. | Profile |
|---|---|---|---|---|---|---|
| Ellis | `Ellis, Paige` | 963 | $396,694 | 420 / $113,219 | 93% | exists (`ellis`, photo `au8`) — zero changes |
| Xie | `Xie, Selena` | 660 | $105,727 | 660 / $105,727 | 85% after backfill | **new** (`xie`) |
| Bowen | `Bowen, Jeffery L.` | 119 | $33,741 | 39 / $17,716 | 97% | **new** (`bowen`), prior-cycle selector for the 2024 mayoral run |
| Hudsky | — | 0 | — | — | — | placeholder card |

## C. Scrub scope (deferred — separate greenlight)

Not yet computed precisely; ballpark from donor counts: Ellis+Xie+Bowen ≥$100 lifetime pool will be the largest yet (Ellis 963 + Xie 660 donors, low prior coverage). Compute with the standard prep script when greenlit; expect ~40–50 batches (~$180–225 at the observed D3 rate).

## D. Site changes

1. `austin_races.json` — `district8`, `kind: "incumbent"`, intro = petition explanation + 2018/2022 context + loan disclosure sentence. Hudsky mirrors the Nahas placeholder shape.
2. Dicts: `CANDIDATE_SLUGS` += xie, bowen; `CANDIDATE_CYCLES`: xie = This Cycle only; bowen = `[{'label': '2024 Mayoral Run', 'election_year': 2024, 'end_year': 2024}, {'label': 'This Cycle', 'election_year': 2026, 'start_year': 2025}]`; `OFFICE_OVERRIDE` "District 8 Candidate" ×2; `CANDIDATE_MIN_YEAR`: xie 2025, bowen 2024.
3. Build xie + bowen profiles (after race entry lands, for race-aware OG), render district8, `--html-only` D1/D3/D5 (expect byte-identical), QA, PR, merge, post-merge backfill + rebuild on canonical DB.

## G. Judgment calls

1. **Ellis petition framing** — intro states the petition route factually, no handicapping; banner covers field non-finality. If she fails to qualify by Aug 17 the page needs an update (flagged as a known follow-up, same class as "new entrants through Aug 17").
2. **Ellis stale-2022 website** — link it (real domain, active donate); revisit if she relaunches.
3. **Loan disclosure** — one intro sentence covering both Ellis's $30K and Xie's $25K self-loans (contributions-only data understates both).
4. **Hudsky peace bond** — omit (non-finance, dismissed).
5. **Bowen's hero total** includes 2024 mayoral money by design (matches Ramos precedent; cycle selector separates the runs).

## Verification notes

Finance: direct DB queries, recipient strings exact. Roster/petition/2022: agent web research, 2+ sources each (KVUE, CBS Austin, Community Impact, Austin Politics Newsletter, Free Press, Bulldog-via-snippets, Austin Monitor). Bulldog and KXAN 403 automated fetch; facts corroborated elsewhere.
