# Endeavor / Armbrust & Brown — contribution match rules (audit notes)

These notes document how `generate_pdfs.py` decides whether a contribution row
counts as **Endeavor Real Estate Group** or **Armbrust & Brown, PLLC** money, and
the audit behind the rules. Goal: explicit, traceable, no fuzzy matching — just a
union of clearly-scoped patterns.

## The bug that prompted this

Krista Laine (District 6) showed **$0** from Endeavor, but Kirk Rudy — an Endeavor
Real Estate Group principal — gave her $237. The row:

| donor | employer | occupation | amount | date | recipient |
|---|---|---|---|---|---|
| `Rudy, Kirk` | `None` | `Self employed` | `237.00` | `2024-09-28` | `Laine, Krista M.` |

The old rule only matched `donor`/`employer` on the literal string "endeavor", so a
principal who filed under employer **"None"** was missed — even though the same
donor string `Rudy, Kirk` reports **"Endeavor Real Estate Group"** on 9+ other rows.

## Match rules (row counts for a firm if ANY apply)

1. **LITERAL** — the firm name appears (case-insensitive) in the **donor name,
   reported employer, OR reported occupation** field. This adds the occupation
   field, which the old rule ignored; a large share of legitimate rows put the
   firm in occupation (e.g. `employer='Principal', occupation='Endeavor'`;
   `employer='Attorney', occupation='Armbrust & Brown'`).
   - Endeavor spellings incl. typos: `endeavor`, `endevor`, `endeavour`, `emdeavor`.
   - Armbrust spellings incl. typos: `armbrust`, `armbrst`, `armburst`, `armrbust`, `ambrust`.
   - Exclusions: `grand endeavor` (an unrelated homebuilder), `armbruster`
     (Shani Armbruster works at Milestone — a different surname caught only as a
     substring).

2. **ERG / EREG abbreviation (Endeavor only, confirmed donors only)** — `ERG`/`EREG`
   as a whole field counts, **but only** for a donor already confirmed Endeavor by
   rule 1 on some other filing. This deliberately excludes two unrelated donors who
   list "ERG" as an *environmental-consulting* employer (`Kurth, Lynn`,
   `Williams, Christy`) — verified they contribute $0 to any roster member anyway.

3. **KNOWN PRINCIPAL + GENERIC EMPLOYER** — the donor is a confirmed firm
   principal/employee (their exact donor string spelled the firm out in
   donor/employer/occupation on at least one filing) **AND** on this particular
   gift the employer field is blank or generic (`""`, `none`, `n/a`, `retired`,
   `self`, `self employed`, `homemaker`, `mother`, `not employed`, `unknown`,
   `requested`, `student`, `.`, …). This recovers Kirk Rudy's `None`/`Retired`
   gifts and the coordinated bundled givers who left employer blank (e.g. the
   Endeavor group giving to Travillion in 2022–2023, Richard Suttle giving to
   Shea/Howard).

### What rule 3 deliberately EXCLUDES (the reason it isn't a blanket sweep)

A naive "count everyone who ever listed the firm" would wrongly pull in spouses and
job-changers whose *other* money is at a different, named employer. Rule 3 excludes
a principal's row whenever the employer names a specific different organization.
Confirmed exclusions from the audit:

| donor | different employer (excluded) | relationship |
|---|---|---|
| `Phillips, Ashley` | Holland & Knight, Thompson & Knight | attorney at another firm (spouse of A&B's Travis Phillips) |
| `Baumgartner, Lydia` | MD Anderson | works elsewhere (spouse of A&B's Matthew Baumgartner) |
| `Campbell, Daniel` | Long View Equity | different real-estate firm |
| `Clay, Greg` | JMI Realty | different developer |
| `Levy, Andrew` | Amazon Web Services | left real estate |
| `Abbott, Sean` | Allen Boone Humphries Robison | different law firm |
| `Whellan, Michael` | Graves Dougherty Hearon & Moody | different law firm |

Their genuine firm-labeled rows still count (rule 1); only their different-employer
rows are excluded.

### Judgment call left OUT (documented for review)

- `Rudy, Amy` (Kirk Rudy's spouse) gave a paired **$237** to Laine the same day, but
  she **never** self-identifies with Endeavor on any filing (only "Retired"). Under
  the "no fuzzy matching / no spouse inference" rule she is **not** counted. Joint
  filings under `Rudy, Kirk & Amy` (employer "Endeavor / none") *do* count via rule 1.
  If household aggregation is desired, that is a separate policy decision.

## Impact: roster totals, before → after

| member | Endeavor before | Endeavor after | Armbrust before | Armbrust after |
|---|---|---|---|---|
| Watson (Mayor) | $51,414 | $70,845 | $38,650 | $49,006 |
| Harper-Madison D1 | $16,050 | $22,550 | $10,646 | $15,496 |
| Fuentes D2 | $19,600 | $21,900 | $14,450 | $18,400 |
| Velásquez D3 | $21,401 | $34,589 | $15,716 | $27,678 |
| Vela D4 | $15,898 | $21,908 | $12,796 | $16,271 |
| Alter D5 | $18,212 | $25,736 | $13,225 | $19,525 |
| Laine D6 | $0 | $237 | $0 | $0 |
| Siegel D7 | $0 | $0 | $18,025 | $22,075 |
| Ellis D8 | $33,298 | $39,679 | $24,059 | $29,959 |
| Qadri D9 | $17,420 | $20,594 | $17,750 | $21,350 |
| Duchen D10 | $10,066 | $10,291 | $6,300 | $7,200 |
| Brown (Judge) | $20,654 | $22,614 | $10,000 | $10,100 |
| Travillion P1 | $0 | $19,828 | $12,500 | $12,629 |
| Shea P2 | $0 | $4,966 | $15,890 | $23,816 |
| Howard P3 | $0 | $2,060 | $5,050 | $15,200 |
| Morales P4 | $19,684 | $20,954 | $14,106 | $14,106 |
| **Roster total** | **$243,695** | **$338,751** | **$229,164** | **$302,811** |

Added dollars by reason (across roster): Endeavor — occupation-field literal
≈ $23.0k, known-principal/generic-employer ≈ $72.0k. Armbrust — occupation-field
literal ≈ $15.7k, known-principal/generic-employer ≈ $58.0k.

> **Note (2026-07-19):** every dollar figure above was computed from raw
> `contribution_amount` sums and therefore **double-counts amended filings** —
> see the addendum below. The match *rules* and row counts are unaffected.

## Addendum (2026-07-19): amended-filing dedup

The raw city feed repeats a contribution whenever a campaign amends a report:
the superseded original stays in the dataset flagged `correction='X'`, and the
enrichment pass sets its `balanced_amount` to 0. `generate_pdfs.py` was summing
raw `contribution_amount`, counting every amended gift twice (for Watson alone:
70 Endeavor rows worth $28,122 and 51 Armbrust rows worth $19,128 were
duplicates). It now sums `COALESCE(balanced_amount, contribution_amount)` and
skips non-positive rows — the same convention the website
(`generate_profile_data.py`) uses. Travis County rows came from the PDF
extractions, carry no amendment duplicates, and are unchanged.

### Deduped totals (rules unchanged, duplicates removed)

| member | Endeavor (was → now) | Armbrust (was → now) |
|---|---|---|
| Watson (Mayor) | $70,845 → $42,722 | $49,006 → $29,778 |
| Harper-Madison D1 | $22,550 → $12,550 | $15,496 → $7,823 |
| Fuentes D2 | $21,900 → $10,950 | $18,400 → $9,300 |
| Velásquez D3 | $34,589 → $29,089 | $27,678 → $27,653 |
| Vela D4 | $21,908 → $21,908 | $16,271 → $16,246 |
| Alter D5 | $25,736 → $20,786 | $19,525 → $13,650 |
| Laine D6 | $237 → $237 | $0 → $0 |
| Siegel D7 | $0 → $0 | $22,075 → $22,000 |
| Ellis D8 | $39,679 → $28,405 | $29,959 → $22,480 |
| Qadri D9 | $20,594 → $10,297 | $21,350 → $10,875 |
| Duchen D10 | $10,291 → $10,291 | $7,200 → $7,200 |
| Brown (Judge) | $22,614 → $22,614 | $10,100 → $10,100 |
| Travillion P1 | $19,828 → $19,828 | $12,629 → $12,629 |
| Shea P2 | $4,966 → $4,966 | $23,816 → $23,816 |
| Howard P3 | $2,060 → $2,060 | $15,200 → $15,200 |
| Morales P4 | $20,954 → $20,954 | $14,106 → $14,106 |
| **Roster total** | **$338,751 → $257,657** | **$302,811 → $242,856** |

Remaining differences vs the website's Notable Firms card are methodology, not
duplication: the site groups by resolved employer identity (so it makes its own
calls on spouses/job-changers, e.g. it counts Greg Clay/JMI to Endeavor and the
Bartram/Hollingsworth/Whitt households to Armbrust, while missing
occupation-literal rows like Jennifer Marsh), and it splits Armbrust across
several canonical identities. Known caveat in these PDFs: the donor-name literal
rule counts anyone surnamed Armbrust — John Armbrust (educator, Austin Achieve,
$2,000 to Watson) is likely unrelated to the firm.
