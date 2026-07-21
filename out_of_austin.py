"""
out_of_austin.py
"Out of Austin Limits" evaluation — Austin City Charter Art. III, § 8(A)(3).

The charter caps the AGGREGATE a candidate for Mayor or City Council may
accept "from sources other than natural persons eligible to vote in a postal
zip code completely or partially within the Austin city limits." The cap is
CPI-adjusted each budget year, with a separate (smaller) cap for a runoff.
It does NOT apply to Travis County offices.

Classification model (mirrors how Ethics Review Commission complaints have
tallied it — voter-registration status is not observable in filings, so an
Austin-area zip is the accepted proxy for "eligible to vote"):

  EXEMPT   individual donor whose zip is on the clerk's Austin-zip list
  COUNTED  every entity/PAC/business donor regardless of zip, plus every
           individual donor with a zip not on the list
  UNKNOWN  individual donor with no parseable zip — disclosed, not counted

Zip source: campaign_finance.city_state_zip (99.7% parseable), falling back
to donor_identities.canonical_zip.
"""

import re

# Postal zip codes completely or partially within the Austin city limits.
# Source: City Clerk memo "Annual Adjustment of Campaign Finance Limits"
# (May 1, 2026), 2026 City Council Candidate Packet p. 37 attachment.
# The list includes suburbs the city limits merely poke into (Buda 78610,
# Cedar Park 78613, Leander 78641, Pflugerville 78660, Round Rock
# 78664/78681) — donors there are exempt even though "Round Rock, TX" looks
# out-of-town in the filings.
AUSTIN_ZIPS = {
    "78610", "78612", "78613", "78617", "78641", "78652", "78653", "78660",
    "78664", "78681", "78701", "78702", "78703", "78704", "78705", "78712",
    "78717", "78719", "78721", "78722", "78723", "78724", "78725", "78726",
    "78727", "78728", "78729", "78730", "78731", "78732", "78733", "78734",
    "78735", "78736", "78737", "78738", "78739", "78741", "78742", "78744",
    "78745", "78746", "78747", "78748", "78749", "78750", "78751", "78752",
    "78753", "78754", "78756", "78757", "78758", "78759",
}
ZIP_LIST_VINTAGE = 2026  # which clerk memo the list came from

# Austin PO-box and unique (agency/university) zips. The clerk's list is
# geographic zips only, but a donor whose filing address is an Austin PO box
# is sitting inside the city limits — counting them as out-of-town money
# would be a false positive (seen in real data: "Austin, TX, 78714").
AUSTIN_PO_BOX_ZIPS = {
    "78708", "78709", "78710", "78711", "78713", "78714", "78715", "78716",
    "78718", "78720", "78755", "78760", "78761", "78762", "78763", "78764",
    "78765", "78766", "78767", "78768", "78769", "78772", "78773", "78774",
    "78778", "78779", "78783", "78799",
}

# Aggregate limit by election year: (general, runoff, runoff_verified).
# The charter base (2006) was $30,000 / $20,000, CPI-W-adjusted each August
# with the budget, so the value in force for a November election is the one
# set that summer. Sourced per year, all from City Clerk "Annual Adjustment
# of Campaign Finance Limits" memos unless noted:
#   2018  $37,000 / $25,000  (memo 8/7/2018, edims id 296172)
#   2020  $38,000 / $25,000  (memo 5/1/2020, edims id 338797)
#   2022  $44,000 / $30,000  (Austin Monitor 7/2022)
#   2024  $47,000 / $31,000  (clerk, Nov 2024 election; May 2024 was 46/30)
#   2026  $48,000 / $32,000  (memo 5/1/2026, 2026 candidate packet)
LIMITS = {
    2018: {"general": 37000, "runoff": 25000, "runoff_verified": True},
    2020: {"general": 38000, "runoff": 25000, "runoff_verified": True},
    2022: {"general": 44000, "runoff": 30000, "runoff_verified": True},
    2024: {"general": 47000, "runoff": 31000, "runoff_verified": True},
    2026: {"general": 48000, "runoff": 32000, "runoff_verified": True},
}
# Future cycles fall back to the newest published values, flagged provisional
# (they will be re-adjusted with each budget before that election).
_LATEST_YEAR = max(LIMITS)

# (slug, election_year) pairs whose race went to a December runoff, verified
# race-by-race against KUT/Austin Monitor/Wikipedia results coverage
# (audit 2026-07-21). A runoff carries its own separate aggregate allowance
# on top of the general-election cap, so these cycles get an extended
# ceiling instead of reading as violations.
#   Dec 2018: D1 Harper-Madison, D8 Ellis
#   Dec 2020: D6 Kelly (beat Flannigan)
#   Dec 2022: Mayor Watson & Israel, D3 Velásquez, D5 Alter,
#             D9 Qadri & Guerrero
#   Dec 2024: D7 Siegel
# Verified NO-runoff races: Fuentes 2020/2024, Vela 2022 (Jan special)/2024,
# Harper-Madison 2022, Ellis 2022, Watson 2024 (50.004%, cleared by 13
# votes), Laine/Kelly 2024, Duchen/Ganguly 2024, Llanes 2024, Bowen 2024,
# Ramos 2022.
HAD_RUNOFF = {
    ("harpermadison", 2018), ("ellis", 2018),
    ("kelly", 2020),
    ("watson", 2022), ("israel", 2022), ("velasquez", 2022),
    ("alter", 2022), ("qadri", 2022), ("guerrero", 2022),
    ("siegel", 2024),
}

# Travis County offices — the charter limit does not apply.
COUNTY_SLUGS = {"brown", "travillion", "shea", "howard", "gomez", "morales"}

_ZIP_RE = re.compile(r"(\d{5})(?:-\d{4})?\s*$")
_CITY_ST_RE = re.compile(r"^(.*?,\s*[A-Za-z]{2})\b")


def _extract_zip(city_state_zip: str, canonical_zip: str) -> str:
    """5-digit zip from 'City, ST, 78704[-1234]', else canonical_zip, else ''."""
    m = _ZIP_RE.search(city_state_zip or "")
    if m:
        return m.group(1)
    m = re.match(r"(\d{5})", (canonical_zip or "").strip())
    return m.group(1) if m else ""


def _city_state(city_state_zip: str) -> str:
    m = _CITY_ST_RE.match((city_state_zip or "").strip())
    return m.group(1) if m else ""


def limits_for(election_year: int) -> dict:
    if election_year in LIMITS:
        return {**LIMITS[election_year], "provisional": False}
    return {**LIMITS[_LATEST_YEAR], "provisional": True}


def classify(donor_type: str, zip5: str, city_state: str = "") -> str:
    """'exempt' | 'counted' | 'unknown' per § 8(A)(3).

    An individual with a zip that is neither on the clerk list nor an Austin
    PO box, but whose reported city is Austin, is exempted anyway: every real
    Austin-area geographic zip IS on the list, so a mismatch there is a
    data-entry typo (e.g. "Austin, TX, 79717"), not an out-of-town donor.
    """
    is_individual = (donor_type or "").strip().lower() == "individual"
    if not is_individual:
        return "counted"  # entities/PACs count wherever they sit
    if zip5 in AUSTIN_ZIPS or zip5 in AUSTIN_PO_BOX_ZIPS:
        return "exempt"
    is_austin_city = bool(re.match(r"austin\s*,\s*tx\b", (city_state or "").strip(), re.I))
    if is_austin_city:
        return "exempt"
    return "counted" if zip5 else "unknown"


def build_cycle_block(cur, base_where: str, base_params: tuple, slug: str, cycle: dict) -> dict:
    """Out-of-Austin tally for one election cycle. base_where/base_params must
    already carry the recipient + min-year + positive-amount filters; the
    cycle's year clauses are appended here (same rule as build_year_clause)."""
    clauses, params = [base_where], list(base_params)
    if cycle["start_year"] is not None:
        clauses.append("cf.contribution_year >= ?")
        params.append(cycle["start_year"])
    if cycle["end_year"] is not None:
        clauses.append("cf.contribution_year <= ?")
        params.append(cycle["end_year"])

    rows = cur.execute(f"""
        SELECT cf.donor_type,
               TRIM(COALESCE(cf.city_state_zip, '')),
               COALESCE(di.canonical_zip, ''),
               COALESCE(NULLIF(di.canonical_name, ''), cf.donor, ''),
               ROUND(COALESCE(cf.balanced_amount, cf.contribution_amount), 2)
        FROM campaign_finance cf
        LEFT JOIN donor_identities di ON cf.donor_id = di.donor_id
        WHERE {" AND ".join(clauses)}
    """, tuple(params)).fetchall()

    totals = {"exempt": 0.0, "counted": 0.0, "unknown": 0.0}
    entity_total = individual_out_total = 0.0
    entity_count = individual_out_count = unknown_count = 0
    by_source = {}  # name -> {name, location, entity, total}

    for donor_type, csz, czip, name, amount in rows:
        amount = float(amount or 0)
        zip5 = _extract_zip(csz, czip)
        bucket = classify(donor_type, zip5, csz)
        totals[bucket] += amount
        if bucket == "unknown":
            unknown_count += 1
            continue
        if bucket != "counted":
            continue
        is_entity = (donor_type or "").strip().lower() != "individual"
        if is_entity:
            entity_total += amount
            entity_count += 1
        else:
            individual_out_total += amount
            individual_out_count += 1
        key = (name or "(unnamed)").strip().lower()
        src = by_source.setdefault(key, {
            "name": (name or "(unnamed)").strip(),
            "location": _city_state(csz),
            "entity": is_entity,
            "total": 0.0,
        })
        src["total"] += amount
        if not src["location"]:
            src["location"] = _city_state(csz)

    top_sources = sorted(by_source.values(), key=lambda s: -s["total"])[:8]
    for s in top_sources:
        s["total"] = round(s["total"])

    lim = limits_for(cycle["election_year"])
    had_runoff = (slug, cycle["election_year"]) in HAD_RUNOFF
    counted = round(totals["counted"])
    ceiling = lim["general"]
    if had_runoff and lim["runoff"]:
        ceiling += lim["runoff"]

    return {
        "label": cycle["label"],
        "election_year": cycle["election_year"],
        "limit": lim["general"],
        "runoff_limit": lim["runoff"],
        "runoff_verified": lim["runoff_verified"],
        "limit_provisional": lim["provisional"],
        "had_runoff": had_runoff,
        "ceiling": ceiling,
        "counted_total": counted,
        "exempt_total": round(totals["exempt"]),
        "unknown_total": round(totals["unknown"]),
        "entity_total": round(entity_total),
        "individual_out_total": round(individual_out_total),
        "entity_count": entity_count,
        "individual_out_count": individual_out_count,
        "unknown_count": unknown_count,
        "pct_of_ceiling": round(counted / ceiling * 100, 1) if ceiling else 0.0,
        "top_sources": top_sources,
    }


def build_payload(cur, base_where: str, base_params: tuple, slug: str, cycles: list) -> dict:
    """The `out_of_austin` block for a profile's data JSON."""
    if slug in COUNTY_SLUGS:
        return {"applies": False, "reason": "county_office"}
    return {
        "applies": True,
        "zip_list_vintage": ZIP_LIST_VINTAGE,
        "zip_list": sorted(AUSTIN_ZIPS),
        "po_box_zips": sorted(AUSTIN_PO_BOX_ZIPS),
        "cycles": [build_cycle_block(cur, base_where, base_params, slug, c) for c in cycles],
    }
