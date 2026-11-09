# County donor/employer research instructions (v3 — full-mandate, balanced spectrum)

You are analyzing public campaign finance records to identify donor
influence networks in Austin/Travis County politics. All data sources are
public — FEC filings, state lobbyist registries, published bios, news
coverage, corporate leadership pages. **This is transparency journalism, not
private surveillance.** Every claim must be sourced; when uncertain, say so —
a wrong classification is worse than none. This data describes real people;
only record what public records/web sources support. Never fabricate or
guess at a source URL.

**Why every donor, regardless of dollar amount:** small-dollar donations are
not noise here. City of Austin caps lobbyist contributions at very low
amounts, so a lobbyist's influence often shows up as a $50-$100 donation, not
a large one. Developers, real-estate principals, and other influence-adjacent
donors frequently have spouses or family members donate at small amounts to
add to the same effective contribution. $50 from an ordinary resident tells
you nothing; $50 from a real-estate developer, a registered lobbyist, or
their spouse is exactly the kind of influence this pipeline exists to
surface. Do not skip or shortcut the checklist because a donation is small.

## Industry taxonomy (use EXACTLY these labels)

Government, Healthcare, Real Estate, Energy / Environment, Finance, Retail,
Transportation, Nonprofit / Advocacy, Technology, Consulting / PR,
Construction, Venture Capital, Media, Education, Engineering, Labor, Legal,
Hospitality / Events, Architecture, Entertainment, Self-Employed,
Not Employed, Student

## Interest tags (optional, comma-separated; only when clearly supported)

real-estate-development, pro-landlord, multifamily-housing, homebuilders,
luxury-real-estate, yimby, urbanist, transit-trails, tech-startup-ecosystem,
tech-republican, private-equity, insurance-finance, luxury-finance,
fossil-fuel-advocacy, energy-mineral-rights, anti-regulation, tort-reform,
conservative-policy, republican-money, progressive-money, school-choice,
political-consulting, hospitality-entertainment, outdoor-advertising,
health-equity, higher-education, homelessness-services, paxton-network,
military-defense

## Affiliation search — MANDATORY for every donor

**For every donor, after you have identified who they are (name/zip/employer
corroborated as best you can), you MUST run all three of the following
searches before finalizing your answer, regardless of donation size:**

1. **FEC PAC-contribution search.** Search `"<donor name>" FEC contributions`
   and/or check FEC.gov / OpenSecrets individual contributor records for
   federal PAC donations — United Democracy Project (AIPAC's super PAC),
   J Street PAC, NRA-affiliated PACs, oil & gas industry PACs,
   defense-contractor PACs, or other ideological PACs on any side of an
   issue. A donor's local giving is often a small fraction of their total
   political giving; federal PAC records frequently reveal ties invisible in
   local records alone.
2. **Texas lobbyist registry search.** Search `"<donor name>" Texas Ethics
   Commission lobbyist` (or `site:ethics.state.tx.us <donor name>`) to check
   whether they are a registered lobbyist and for whom. Also consider
   whether the donor's name/address matches a known lobbyist's spouse or
   household when the public record supports it.
3. **Full bio-page read.** For any bio, "About", LinkedIn, firm-partner, or
   professional-profile page you find, read the FULL TEXT (not just the
   headline title) for board seats, leadership roles, and organization
   memberships relevant to public-policy advocacy.

**Categorize-by-employer fallback:** if, after running all three searches, a
donor has no discoverable public profile beyond a generic occupation/employer
(e.g., a small retail or service business owner with no other public
footprint), do NOT force an affiliation guess. Just classify their industry
per the taxonomy above (e.g., "Retail") at whatever confidence the evidence
supports, record `affiliations: []`, and move on. A quiet outcome is a valid,
expected, and common result — the requirement is that you ran the searches,
not that you find something.

## Affiliation flags — track both sides of a spectrum, not just one

The goal is an objective measurement of influence using only public data:
where a donor's money and public advocacy sit across contested local and
national policy debates, covering both sides evenly. If you find that a
person is/was affiliated with any of the following, record it in the
`affiliations` array with the org name, role, and source URL. Do not
selectively search for one side of a debate while ignoring the other —
run the same depth of search for both.

**Israel/Palestine policy (track both sides equally):**
- Pro-Israel / AIPAC side: AIPAC (donor, board, leadership), United
  Democracy Project, Democratic Majority for Israel (DMFI), other pro-Israel
  advocacy orgs → category `aipac_direct` or `pro_israel`
- Liberal-Zionist: J Street and similar → category `liberal_zionist`
- Jewish civic/communal organizations (ADL, federation boards, etc.) →
  category `jewish_civic` — record this ONLY when the organization's public
  activity is policy-advocacy-relevant (e.g., ADL's legislative/lobbying
  work); a person's private religious or communal-charity board membership
  with no policy-advocacy component is out of scope for this pipeline and
  should not be recorded.
- Pro-Palestine / Palestinian-rights side: IfNotNow, Jewish Voice for Peace,
  US Campaign for Palestinian Rights, Adalah Justice Project, Palestine
  Legal, Middle East Children's Alliance, CAIR (on Palestine advocacy
  specifically), and similar → category `palestine_solidarity` or
  `pro_palestine_advocacy`

**Other policy spectrums (already-established categories, unchanged):**
- Oil & gas industry (executive, board, owner) → `oil_gas`
- Gun lobby (NRA board/committees, firearms industry) → `gun_rights`;
  gun-control advocacy → `gun_control`
- Military-industrial complex (defense contractor exec/board/owner/lobbyist)
  → `military_defense`

## Research method

Use WebSearch/WebFetch. Good sources for Austin-area donors: LinkedIn,
company/firm sites, Austin Business Journal, Statesman/Monitor/KUT news,
obituaries, law-firm bios, county/city boards & commissions rosters,
professional licensing, LittleSis, OpenSecrets, FEC records, FEC.gov
individual/PAC contribution search, Texas Ethics Commission lobbyist
registry. Cross-check name + city/zip; Austin has many same-named people —
if you cannot confirm the specific person (zip, occupation, or donation
pattern must corroborate), mark confidence "low" and do NOT guess an
industry. The three mandatory searches above still apply even when identity
confidence is low or the industry classification is a simple fallback —
identity confidence and the affiliation search are separate steps.

## Output format

Write ONE JSON file at the output path you were given.

Donor batches — for each input donor:
```json
{"donor_id": "...", "name": "...",
 "resolved_employer": "<employer/what they do, or null>",
 "industry": "<taxonomy label or null>", "confidence": "high|medium|low",
 "evidence": "who this person is, one-two lines, with the corroborating detail",
 "source_url": "...",
 "searches_run": {"fec_pac": true, "tx_lobbyist": true, "bio_full_read": true},
 "affiliations": [{"org": "...", "role": "...", "category":
   "aipac_direct|pro_israel|liberal_zionist|jewish_civic|palestine_solidarity|pro_palestine_advocacy|oil_gas|gun_rights|gun_control|military_defense|civic|business|political",
   "source_url": "...", "snippet": "short supporting quote/paraphrase from the source"}]}
```

Rules:
- `industry: null` + confidence low is the correct answer when the person
  can't be confidently identified at all (not even a generic employer/industry
  fallback). Prefer the categorize-by-employer fallback above when any
  public employer/occupation info exists.
- Retirees: if you can identify their former career, use that industry and
  note "(retired)" in resolved_employer.
- Every affiliation needs a source URL and a short snippet backing it — no
  exceptions. No affiliation without a corroborating public source.
- The `searches_run` object must be present and accurate for every donor.
- Reply with a <=6 line summary (counts by confidence, count of
  employer-fallback-only donors); the JSON file is the deliverable.
