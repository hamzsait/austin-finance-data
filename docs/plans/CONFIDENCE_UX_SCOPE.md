# Confidence UX — Scope

**Status:** Scope-out only. No code written, no schema changed. Review before greenlighting.
**Date:** 2026-07-18
**Context:** Phases 1–5 of `AFFILIATION_TEMPLATE_EXPANSION_PLAN.md` shipped four affiliation cards rendering ~2,400 donor findings. Confidence data was deliberately left unrendered. This documents what it would take to surface it.

---

## 1. Schema state

### 1.1 Correction to the brief

The task described confidence as living on `donor_identities.match_confidence`. That column does not exist. The actual layout:

| Table | Column | Grain | Notes |
|---|---|---|---|
| `donor_identities` | `resolved_confidence` | **per donor** | TEXT, mixed vocabulary (see below) |
| `campaign_finance` | `match_confidence` | per contribution row | identity-resolution score, unrelated to research |
| `civic_affiliations` | **none** | — | no confidence column exists |

`campaign_finance.match_confidence` measures how confidently a *contribution* was matched to a donor identity. It says nothing about whether a research finding is correct. Using it here would be a category error.

### 1.2 The core problem

**`civic_affiliations` has no confidence column, and the confidence that does exist is per-donor, not per-affiliation.**

`resolved_confidence` also carries a mixed vocabulary — only two of its eight values come from research:

| Value | Rows | Source |
|---|---|---|
| `employer` | 14,878 | employer-string classification |
| `occupation-incr` | 7,189 | occupation classification |
| `occupation` | 5,735 | occupation classification |
| `fec-employer` | 3,123 | FEC employer field |
| `employer-incr` | 3,000 | incremental employer pass |
| `cross-identity (employer)` | 1,043 | cross-identity resolution |
| **`llm-research-high`** | **861** | **Opus research** |
| **`llm-research-medium`** | **421** | **Opus research** |

Only the last two are meaningful for affiliation display. A donor whose `resolved_confidence` is `employer` has *no* research-confidence signal at all, yet may still carry affiliation rows from a pre-batch manual script.

### 1.3 What the batch files actually carry

Both research corpora record confidence **per donor record**, not per affiliation:

| Corpus | Records | high | medium | low |
|---|---|---|---|---|
| D1 (`d1batch_*_results.json`) | 606 | 329 | 142 | 135 |
| Travis (`donorbatch*_results.json`) | 1,755 | 823 | 392 | 540 |

Of the 606 D1 records, 276 carry affiliations totalling **720 rows** — so a single donor-level confidence value would have to be stamped onto multiple affiliation rows that were established by entirely different evidence.

**Recoverability:** 1,514 distinct `(name, organization)` pairs are reconstructable from batch result files, against **1,791 rows** in the table. **~277 rows (15%) predate the batch pipeline** — they came from the April-era manual scripts (`add_adl_affiliations.py`, `add_harpermadison_aipac.py`, and similar) and have **no recoverable confidence at any grain**.

---

## 2. Backfill options

### Option A — Stamp donor-level confidence onto affiliation rows *(cheapest, least honest)*

Add `confidence TEXT` to `civic_affiliations`; replay batch JSONs; write each donor's record-level confidence to all of that donor's rows.

- **Effort:** ~2 h. Additive migration, idempotent replay, no re-research.
- **Coverage:** ~85% of rows; ~277 legacy rows land NULL.
- **Problem:** it asserts something untrue. A donor rated `medium` overall — because their *employer* was hard to pin down — may have a rock-solid affiliation sourced from a Texas Ethics Commission filing. Stamping `medium` on that row misrepresents it, and the inverse (a `high` donor with one weak affiliation) is worse because it launders a shaky claim.

### Option B — Re-research for per-affiliation confidence *(most accurate, most expensive)*

Re-run the research pass with an output schema requiring a confidence value per affiliation object.

- **Effort:** ~1 h instruction/schema change, ~4–6 h wall time, **~$250–400** at the measured $8.37/batch across ~2,360 donor records.
- **Coverage:** 100% at the correct grain.
- **Problem:** cost, and it re-derives ~1,500 findings that are already correct just to attach a metadata field.

### Option C — Derive a per-row **source-quality** signal from data already present *(recommended)*

Don't render confidence at all. Render **source quality**, computed from `source_url` and `role` text, which exist on every row today:

| Tier | Rule | Meaning |
|---|---|---|
| **Institutional** | `.gov`, `capitol.texas.gov`, `ethics.state.tx.us`, FEC, IRS, court records | Primary public record |
| **Organizational** | org's own site, annual report, press release, board roster | First-party but self-published |
| **Self-reported** | LinkedIn, personal bio pages, interview profiles | Subject's own account |
| **Unconfirmed** | `role` text contains hedging ("not independently verified", "reported in his biography") | Explicitly flagged by the researcher |

- **Effort:** ~3 h — a classifier function in `generate_profile_data.py` plus chip rendering. **No schema change, no re-research, no backfill, 100% row coverage including the 277 legacy rows.**
- **Why it's better:** source quality is what a reader can actually evaluate. "This came from a Texas Ethics Commission filing" is a verifiable statement; "the model was 80% sure" is not. It also degrades honestly — a row with a weak source looks weak regardless of what any model thought.
- **Known inputs:** `source_url` is populated on **100%** of 1,791 rows; 75 rows (4.2%) cite LinkedIn; `role` averages 53 chars, `notes` 589.

### Option D — Do nothing

Current state. Every row shows its source link; the methodology note already says some roles are self-reported rather than independently confirmed. **This is defensible** and is what ships today.

---

## 3. Rendering options

Assuming Option C's tiers:

1. **Chip after the org name** — `[TEC filing]`, `[self-reported]`. Sky `#cfe3f5` bg / navy text for institutional; muted grey outline for self-reported. Most explicit, adds visual noise to dense cards.
2. **Source-link styling** — recolor the existing `source ↗` link per tier. Zero new elements, near-zero noise, but discoverable only on inspection.
3. **Opacity / de-emphasis** — dim weaker rows. **Not recommended:** reads as editorial dismissal rather than a sourcing statement, and hurts accessibility contrast.
4. **Grouping within a bucket** — verified rows first, self-reported below a divider. Clearest hierarchy, but fragments already-small buckets (many have 1–3 rows).

**Recommendation: (2) as the default, escalating to (1) only for the `Unconfirmed` tier** — badge the rows that need a warning, leave the rest to a colored source link. Adds a chip exactly where it carries information.

---

## 4. Misinterpretation risks

**4.1 Donor-level confidence read as row-level truth.** The central risk in Option A, described in §2. If Option A ships, the label must say "donor identification confidence," never "affiliation confidence" — and that distinction will be lost on most readers, which is the argument against shipping it at all.

**4.2 A confidence chip implies a verification process that didn't happen.** These are model-generated ratings from a web-research pass, not a fact-checking desk. A green "high confidence" badge on a claim about a private individual reads as an editorial guarantee. Source-quality tiers make a narrower, defensible claim.

**4.3 Absence read as doubt.** ~277 legacy rows can't get a value under Option A. A missing chip beside populated ones reads as "we couldn't verify this," when it actually means "this predates the pipeline that records confidence." Same failure mode as the Palestine-column zeros fixed in Phase 2 — any partial rollout needs an explicit label for the null state.

**4.4 Low-confidence rows are already excluded.** `_apply_d1_results.py` and `_apply_results.py` both gate writes on `confidence in ('high','medium')`. **Every affiliation row in the database already passed a confidence filter** — 135 of 606 D1 donors and 540 of 1,755 Travis donors were dropped at apply time. Rendering a high/medium chip therefore communicates far less than it appears to: the low tier was never published. This meaningfully weakens the case for Options A and B.

---

## 5. Effort summary

| Option | Effort | Cost | Coverage | Recommend |
|---|---|---|---|---|
| A — stamp donor confidence | ~2 h | $0 | ~85% | ✗ misrepresents grain |
| B — re-research per-affiliation | ~6 h + wall | ~$250–400 | 100% | ✗ cost vs. benefit |
| **C — source-quality tiers** | **~3 h** | **$0** | **100%** | **✓** |
| D — do nothing | 0 | $0 | n/a | ✓ acceptable fallback |

**Recommendation: Option C with rendering (2)+(1).** ~3 hours, no schema migration, no re-research, works on all 1,791 rows including legacy, and makes a claim the data can support. If the answer is "not now," **Option D is genuinely fine** — the per-row source link plus the existing methodology note already meet the honesty bar, which is why Phases 1–5 shipped without this.

**Deliberately not recommended: adding a `confidence` column now.** It's cheap and reversible, but §4.4 means the column would record "which of two published tiers this was" rather than "how much to trust this" — a distinction that would get lost the moment it reached the page. If you later run Option B, add the column then, at the correct grain.

---

## Appendix — verification

All figures from direct read-only queries against `austin_finance.db` and direct reads of `d1_research/d1batch_*_results.json` (31 files), `travis_research/donorbatch*_results.json`, `_apply_d1_results.py`, and `_apply_results.py` on 2026-07-18. Nothing was written except this file.

- `civic_affiliations`: 1,791 rows, columns `id, canonical_name, organization, role, category, source_url, notes, added_at` — no confidence column.
- `donor_identities.resolved_confidence`: 8 distinct values, only `llm-research-high` (861) and `llm-research-medium` (421) research-derived.
- Batch confidence is per donor record: D1 606 records (329/142/135), Travis 1,755 records (823/392/540).
- 1,514 of 1,791 rows (85%) have a recoverable `(name, org)` match in batch files; ~277 predate the pipeline.
- Both apply scripts gate on `confidence in ('high','medium')`, so no low-confidence affiliation was ever written.
