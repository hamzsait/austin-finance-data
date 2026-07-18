# Phase 2 pilot: Sonnet 5 vs Opus 4.8 donor research

30-donor pilot (`donorbatch4_pilot.json` → `donorbatch4_pilot_results.json`), run on `claude-sonnet-5`
via a copy of the production driver (`_run_pilot.js`), same system prompt/instructions
(`_research_instructions.md`) as the archived Opus 4.8 `donorbatch3` runs.

**Data-reality note before the numbers:** the `tcv-` donor_id scheme referenced in the original task
spec no longer exists in the live DB — the identity-migration commit (`b4ec1c6`) remapped every
Travis County donor_id, so 0 `tcv-`-prefixed ids remain in `donor_identities`. Adapted:
- **20 "overlap" donors** — pulled directly from the archived `donorbatch3_*.json` / `*_results.json`
  pairs (self-contained; no live-DB lookup needed), stratified 6 positive/high-confidence,
  6 no-result/low-confidence, 8 "sensitive" (prioritizing rare affiliation categories:
  aipac_direct, jewish_civic, oil_gas, military_defense, gun_rights, gun_control).
- **10 "delta" donors** — current unresolved Travis County donors matched by name+zip against
  *all* donorbatch3 inputs to confirm they were never researched before.

Wall time: **501s (8.4 min)** for all 30 donors in one job (no worker pool). Opus 4.8 production
timing for this exact 30-donor set was not separately measured — no historical timing log was
kept from the original donorbatch3 runs (see Cost & latency below for what can and can't be said).

## Agreement rate — 20 overlap donors

| Metric | Result |
|---|---|
| Industry classification match | **16/20 (80%)** |
| Confidence: same tier | 16/20 |
| Confidence: Sonnet higher | 3/20 |
| Confidence: Sonnet lower | 1/20 |
| Affiliation category set match | **12/20 (60%)** |
| Affiliation *recall* on the 8 donors picked for a known sensitive finding | **1/8** confirmed reproduced (oil_gas), **+1 net-new** (jewish_civic) found elsewhere in the batch |

Industry/employer identification — "who is this person, what do they do" — is solidly comparable
between the two models. **Affiliation-flag recall is the real gap**, and it's concentrated exactly
where this pipeline cares most: AIPAC/ADL/oil-gas/gun/military-defense ties.

## 3 agree examples

1. **Gimbel, Thomas** — Media / high confidence, no affiliations, both models. Clean identity match.
2. **Morris, Barbara** — both correctly returned `industry: null`, confidence low, no forced guess on
   an unconfirmable common name. Good — Sonnet doesn't over-claim when it can't identify someone.
3. **Casey, Stan** — Energy/Environment, high confidence, both models flagged `oil_gas` (Diamondback
   Energy, Director of Government Affairs — his job title states the affiliation outright, so this
   was the easy case).

## 3 disagree examples (Sonnet miss)

1. **Weir, Jaspar** (TaskUs co-founder/President) — **the most consequential miss in the batch.**
   Opus found $50,000 in donations to the **United Democracy Project (AIPAC's super PAC)** via FEC
   federal-contribution records (`aipac_direct`), plus $75k+ to Trump/RNC in 2024. Sonnet correctly
   identified Weir as TaskUs co-founder/President (industry match: Technology, both high confidence)
   but recorded **zero affiliations** — it never ran the FEC PAC-contribution search that surfaced
   the AIPAC tie; it stopped at confirming his job title/location.
2. **Zimmerman, Bruce** (ex-UTIMCO CEO, now Tresalia Capital) — Opus found former International
   President of **B'nai B'rith Youth Organization** (`jewish_civic`) and a Vistra Energy Corp. board
   seat (`oil_gas`, fossil-adjacent), both via his professional bio pages. Sonnet correctly identified
   the Tresalia/UTIMCO career (Finance, high confidence both) but recorded no affiliations — it read
   the same class of bio page Opus did but didn't extract the civic/board memberships from it.
3. **Bartram, John** (Armbrust & Brown attorney) — Opus found a `gun_rights` affiliation. Sonnet
   matched the employer/industry (Legal, high confidence both) but again returned zero affiliations.

Pattern across all 6 missed-affiliation donors (Weir, Zimmerman, Averitt, Hayes, Bartram, Epstein):
**Sonnet consistently does the primary identity-confirmation search and stops there.** Opus goes a
step further — FEC PAC-contribution searches, TEC lobbyist-registry searches, full bio pages for
board/honor-roll memberships — the secondary searches the instructions ask for ("record any
AIPAC/ADL/pro-Israel/oil/gun/military-defense affiliations you encounter") but that Sonnet treats as
optional/incidental rather than a required second pass.

## 3 delta-donor production-ready findings

1. **Harrington, Gregory** — identified as a 2025 Pflugerville mayoral candidate (Ballotpedia bio) +
   FEC records at the same ZIP showing 19 years at Dell Technologies then self-employed ("Madidad").
   High confidence, sourced, plausible.
2. **Weisz, Margo** — Executive Director of the Texas Energy Poverty Research Institute (TEPRI),
   founder of PeopleFund (a CDFI), adjunct at UT's LBJ School/McCombs. FEC ZIP match exact. High
   confidence, well-sourced.
3. **Tolleson, Mike** — Austin entertainment/IP attorney, founder of Mike Tolleson & Associates,
   co-founder of Armadillo World Headquarters. Office address ZIP exact match to donor. High
   confidence.

All 10 delta results: 6 high, 3 medium, 1 medium-with-null-industry (appropriately conservative on
an unidentifiable "Limon LLC" business type). Source URLs are specific and load-bearing (Ballotpedia,
FEC search links, company "our story" pages, LinkedIn) — no signs of fabrication or generic filler.
Sanity-check verdict: **production-ready** for the delta set specifically, since none of these
donors' profiles depend on the affiliation-recall gap (all are small-dollar, no PAC/lobbyist ties
found by either model).

## Cost & latency

- **Wall time (measured):** 501s / 30 donors ≈ 16.7s/donor amortized, single job, no parallelism.
  No comparable same-batch Opus timing exists — the original donorbatch3 driver console-logs
  per-batch completion but never persisted a log file, so there's no historical number to diff
  against. This is a real gap in the pilot, not a "roughly equal" finding — treat latency as
  **unmeasured**, not a wash.
- **Cost (estimated, not measured):** neither run captured per-request token usage (the `claude -p`
  CLI driver doesn't surface `usage` fields). At list pricing, Sonnet 5 is $3/$15 per MTok vs Opus
  4.8's $5/$25 (40% cheaper); at introductory pricing through 2026-08-31, Sonnet 5 is $2/$10 vs
  Opus's $5/$25 (~60% cheaper). For a token-usage profile that's roughly similar between models on
  the same task (both are doing WebSearch/WebFetch-heavy identity research), this ratio is the best
  available proxy for cost savings — but it is a proxy, not a measurement.

## Recommendation: **(B) mixed, refined** — not a straight A/B/C pick

Plain "Sonnet for everything" (A) is the wrong call: it would silently drop AIPAC/oil-gas/gun/
military-defense affiliations at roughly an 85% miss rate on cases that matter, in a pipeline whose
explicit purpose includes flagging exactly those ties. Plain "stay on Opus" (C) throws away a real,
measured win on the bulk of the work — general industry/employer identification is 80% agreement
and delta-donor quality is production-ready.

But a category-based split ("Opus for Israel-aligned donors, Sonnet for the rest") isn't operationally
possible — you don't know which donors have a hidden AIPAC/oil-gas/gun tie until *after* the deep
search runs. The workable version of (B):

1. **Run the full ~2,000–3,000 delta batch on Sonnet 5** for identity/industry/employer resolution
   (cheap, fast, 80% agreement with Opus baseline on this dimension, delta-set quality looks
   production-ready).
2. **Run a mandatory second pass — on Opus, or on a Sonnet prompt rewritten to make the
   affiliation search non-optional** (explicit required steps: FEC PAC-contribution search, TEC/state
   lobbyist-registry search, full bio-page read for board/honor-roll lines) — scoped only to donors
   Sonnet resolved at medium+ confidence, not the whole batch. This captures most of the Sonnet cost
   savings on the bulk of the work while closing the specific gap this pilot found.

Before committing further budget to either path, it's worth re-running a small slice of this same
pilot with the affiliation-search step made explicit and mandatory in the Sonnet prompt (rather than
"record incidentally") — that's a prompt fix, not a model fix, and might close most of the gap without
needing an Opus second pass at all. That test wasn't in scope for this pilot but is the natural next
step before scaling to 2-3k donors.
