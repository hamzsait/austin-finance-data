# D9 Expansion Plan — 2026 Austin City Council District 9

**Status:** Scoping document, written immediately before execution in the same session.
**Date:** 2026-07-19
**Scope:** `/austin/district9/` (fifth and final race-view instance for the 2026 field) + three new profiles (Heyman, Kam, Thadani). Worktree `austin-finance-data-d9`, branch `d9-race-page`, DB copied in, plan committed first, issue tracks execution.

## 0. What's different — read this first

1. **First race with an `omitted` entry for a suspended campaign.** Ard Ardalan (raised $7,600 Jul–Oct 2025) suspended on **Dec 15, 2025** (own X/Instagram posts; corroborated by Community Impact, Free Press, APN). He goes in `omitted` with that reason — not a candidate card — even though he has finance data. His CTA was still uncancelled as of Feb 2026; if he re-enters before Aug 17 the roster changes.
2. **Three new profiles at once** (Heyman 188 donors / $35,881; Kam 51 / $8,355; Thadani 20 / $1,944). All This-Cycle-only. Thadani is thin but well above the Riggins floor (2 donors) — full profile per precedent.
3. **The incumbent is the biggest fundraiser on the site's 2026 field:** Qadri, 2,014 donors / $650,249 lifetime, $128,164 cycle, ~$182K CoH per press — profile exists (`qadri`, photo `au9`), zero changes.
4. **Kam/Thadani backfill already executed in this worktree** (`d9_research/_backfill_kam_thadani_employers.py`, 13 donors): Kam 78%→92%, Thadani 65%→95%. Heyman is at 90%, fine as-is.
5. **No loans reported for anyone** — no loan-disclosure sentence needed (unlike D5/D8).

## A. Race context

- **Qadri, 35** — Austin's first South Asian council member; won the open 2022 seat (Tovo term-limited): led the general ~30%, then **def. Linda Guerrero 51–49 in the Dec 13, 2022 runoff**, buoyed by UT student support (Chronicle). Launched re-election Dec 4, 2025 (Daily Texan); zoforaustin.com is explicitly "Re-elect Zo Qadri". Endorsements incl. Watson, Talarico, Hinojosa, Doggett. `kind: "incumbent"`.
- **Heyman, 58** — urban geographer; taught urban studies at UT ~20 years; richforaustin.org; CTA/filings from Aug 2025; APN characterizes his lane as "leftist anti-growth"; D9 homeowner since 2006. His UT dismissal after a 2024 campus-protest arrest (charge dropped Jan 2025) is press-prominent but non-finance → **bio stays neutral**, flagged §G.2.
- **Kam, 49** — civil/transportation engineer (PhD), ex-city urban planner and AISD science teacher, Austin resident since 1983; katiekamforaustin.com; CTA 3/9/2026, treasurer Doug Addison (verified in the D3 roster sweep). Transportation/mobility platform.
- **Thadani** — UT computer science **freshman** (verified: Daily Texan + Chron syndication), lives in Jester dorm; daveforaustintx.com; renter-protections platform, $10K goal. The Feb Free Press "does not appear to be a registered voter" note → omit (eligibility, non-finance; same class as prior districts' residency items, §G.3).
- Additional filers: none — Bulldog counts Kam as the *fourth* D9 entrant; Clerk/press cross-checks clean. Calendar identical to the other districts.

## B. Finance (queried this session, through 2026-06-30)

| Candidate | Recipient | Donors | Total | Cycle-25+ | Industry | Profile |
|---|---|---|---|---|---|---|
| Qadri | `Qadri, Zohaib` | 2,014 | $650,249 | 529 / $128,164 | 97% | exists — zero changes |
| Heyman | `Heyman, Richard` | 188 | $35,881 | all cycle | 90% | **new** |
| Kam | `Kam, Katherine` | 51 | $8,355 | all cycle | 92% after backfill | **new** |
| Thadani | `Thadani, Dave` | 20 | $1,944 | all cycle | 95% after backfill | **new** |
| Ardalan | `Ardalan, Ard` | 45 | $7,600 | 2025 only, ended Oct | — | omitted (suspended) |

## C. Scrub scope (deferred — separate greenlight)

Qadri's 2,014-donor base is the largest uncovered pool on the site. Compute precisely when greenlit; ballpark ≥$100 lifetime: likely 60+ batches (~$270+ at the observed D3 rate). Note his existing profile already displays lifetime donors, so the D3 lifetime-basis argument applies unchanged.

## D. Site changes

1. `austin_races.json` — `district9`, `kind: "incumbent"`, no loans sentence, `omitted: [Ardalan + reason]`.
2. Dicts: `CANDIDATE_SLUGS` += heyman, kam, thadani; `CANDIDATE_CYCLES` This-Cycle-only ×3; `OFFICE_OVERRIDE` "District 9 Candidate" ×3; `CANDIDATE_MIN_YEAR`: heyman 2025, kam 2026, thadani 2026.
3. Build three profiles (after race entry), render district9, `--html-only` stability check on the other four races, QA, PR, merge, post-merge backfill + rebuild on canonical DB.
4. After this district: the "2026 Races" hub shows **all five races** — the architecture milestone the D1 plan aimed at ("revisit /austin/races/ index when a third district lands" is now overdue → flagged as follow-up, not in scope).

## G. Judgment calls

1. **Ardalan placement** — `omitted` with the suspension reason (recommended) rather than a card; his $7,600 stays out of the comparison strip. Re-check if he re-files.
2. **Heyman bio neutrality** — omit the UT dismissal/arrest from the bio (non-finance; the site's lane is money). His occupation is described as it stood ("taught urban studies at UT for two decades").
3. **Thadani voter-registration note** — omit (eligibility class, resolves at filing).
4. **Thadani thin data** — ship full profile (Riggins precedent; 20 donors is 10× the floor).

## Verification notes

Finance: direct DB queries, recipient strings exact (`Kam, Katherine`, not "Katie"; `Thadani, Dave`). Roster: agent research, 2+ sources each (Daily Texan, Community Impact, Free Press, APN, Chron syndication, candidates' own sites, Ardalan's own suspension posts). One outlet misspells Thadani as "Thandini" — ignore. Bulldog/KXAN 403 as usual.
