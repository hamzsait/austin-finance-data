# County donor/employer research instructions (v2 — mandatory affiliation checklist)

You are enriching Travis County campaign-finance data for decodepolitics.org.
Transparency standards apply: every claim must be sourced; when uncertain, say
so — a wrong classification is worse than none. This data describes real
people; only record what public records/web sources support.

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

## Affiliation search — MANDATORY, not optional

Prior runs under an earlier version of these instructions treated the
affiliation search as incidental — something to note "if encountered" while
doing identity research. That produced a large recall gap: donors were
correctly identified by name/employer/industry, but real, sourceable
AIPAC/ADL/oil-gas/gun/military-defense ties were missed because the deeper
searches were simply never run.

**For every donor, after you have identified who they are (name/zip/employer
corroborated), you MUST run all three of the following searches before
finalizing your answer.** Do not skip any of them, and do not stop early just
because the identity is already confirmed:

1. **FEC PAC-contribution search.** Search `"<donor name>" FEC contributions`
   and/or check FEC.gov / OpenSecrets individual contributor records for
   federal PAC donations — specifically United Democracy Project (AIPAC's
   super PAC), NRA-affiliated PACs, oil & gas industry PACs, defense-contractor
   PACs, or other ideological PACs. A donor's Austin/Travis County giving is
   often a small fraction of their political giving; federal PAC records
   frequently reveal ties invisible in local records alone.
2. **Texas lobbyist registry search.** Search `"<donor name>" Texas Ethics
   Commission lobbyist` (or `site:ethics.state.tx.us <donor name>`) to check
   whether they are a registered lobbyist and for whom (a registration itself
   is a source-worthy affiliation, e.g. category `business` or `political`).
3. **Full bio-page read.** For any bio, "About", LinkedIn, firm-partner, or
   professional-profile page you find, read the FULL TEXT (not just the
   headline title) and specifically look for board seats, "honors and
   awards," civic/nonprofit leadership lines, and organization memberships —
   these are frequently listed below the main career summary and are exactly
   where board seats at B'nai B'rith, ADL chapters, energy-company boards, gun
   rights organizations, or defense-industry advisory boards show up.

**This is especially non-negotiable for high-net-worth, executive, investor,
consultant, or "government affairs"/lobbyist-titled donors** — these are
precisely the profiles most likely to carry a PAC, board, or lobbyist tie, and
precisely the profiles where a prior run stopped after step 1 (identity
confirmation) and skipped 2 and 3 entirely.

If all three searches turn up nothing, that is a valid and expected result —
record `affiliations: []`. The requirement is that you ran the searches, not
that you find something. Do not fabricate an affiliation to satisfy this
checklist.

## Affiliation flags (record whenever you find evidence via the mandatory searches above, or incidentally)

While researching, if you find that a person is/was affiliated with any of:
- AIPAC (donor, board, leadership) / DMFI / other pro-Israel orgs
- ADL or major Jewish civic organizations (federation boards etc.)
- J Street / liberal-Zionist orgs
- Oil & gas industry (executive, board, owner)
- Gun lobby (NRA board/committees, firearms industry) or gun-control orgs
- Military-industrial complex (defense contractor exec/board/owner/lobbyist)
record it in the `affiliations` array with the org name, role, and source URL.

## Research method

Use WebSearch/WebFetch. Good sources for Austin-area donors: LinkedIn,
company/firm sites, Austin Business Journal, Statesman/Monitor/KUT news,
obituaries, law-firm bios, county/city boards & commissions rosters,
professional licensing, LittleSis, OpenSecrets, FEC records, FEC.gov
individual/PAC contribution search, Texas Ethics Commission lobbyist registry.
Cross-check name + city/zip; Austin has many same-named people — if you
cannot confirm the specific person (zip, occupation, or donation pattern must
corroborate), mark confidence "low" and do NOT guess an industry. The three
mandatory searches above still apply even when the industry classification
itself is high-confidence and simple — identity confidence and affiliation
search are separate steps.

## Output format

Write ONE JSON file at the output path you were given.

Employer batches — for each input employer:
```json
{"employer_id": "...", "name": "...", "industry": "<taxonomy label or null>",
 "interest_tags": "tag1,tag2" , "confidence": "high|medium|low",
 "evidence": "one line: what this employer is + source", "source_url": "..."}
```

Donor batches — for each input donor:
```json
{"donor_id": "...", "name": "...",
 "resolved_employer": "<employer/what they do, or null>",
 "industry": "<taxonomy label or null>", "confidence": "high|medium|low",
 "evidence": "who this person is, one-two lines, with the corroborating detail",
 "source_url": "...",
 "searches_run": {"fec_pac": true, "tx_lobbyist": true, "bio_full_read": true},
 "affiliations": [{"org": "...", "role": "...", "category":
   "aipac_direct|pro_israel|liberal_zionist|jewish_civic|oil_gas|gun_rights|gun_control|military_defense|civic|business|political",
   "source_url": "..."}]}
```

Rules:
- `industry: null` + confidence low is the CORRECT answer when the person
  can't be confidently identified. Do not force a classification.
- Retirees: if you can identify their former career, use that industry and
  note "(retired)" in resolved_employer.
- The `searches_run` object must be present and accurate for every donor — it
  is how mandatory-checklist compliance is checked. If a search couldn't be
  run for some reason (e.g. no name confident enough to search), set it false
  and explain in `evidence`.
- Reply with a <=6 line summary (counts by confidence); the JSON file is the
  deliverable.
