# FEC Integration Plan

## Goal
Match Austin local donors against FEC federal donation history to derive a partisan lean score per individual donor.

## Data Model (to add to donor_identities)
```sql
ALTER TABLE donor_identities ADD COLUMN fec_partisan_lean REAL;
-- 1.0 = 100% Democrat, 0.0 = 100% Republican, 0.5 = even split, NULL = no FEC history
ALTER TABLE donor_identities ADD COLUMN fec_total_dem REAL;
ALTER TABLE donor_identities ADD COLUMN fec_total_rep REAL;
ALTER TABLE donor_identities ADD COLUMN fec_total_donations INTEGER;
ALTER TABLE donor_identities ADD COLUMN fec_matched INTEGER DEFAULT 0; -- 0=unmatched, 1=matched
```

## FEC API Endpoints
- Contributor search: GET /schedules/schedule_a/
- Key params: contributor_name, contributor_city, contributor_state=TX, contributor_zip
- Returns: committee_id, contribution_amount, contribution_receipt_date, contributor_employer

## Matching Strategy
1. For each donor_identity with 2+ local donations, query FEC by name + TX state
2. Fuzzy match on name + city/zip to confirm identity
3. Pull all federal contributions, classify committee as Dem/Rep using FEC committee data
4. Compute: lean = dem_total / (dem_total + rep_total)

## Committee Party Classification
- Use /committees/ endpoint: committee_type + party field
- Presidential/Senate/House committees have clear party affiliations
- PACs need to be looked up separately

## Priority Order
- Focus on top 500 donors by Austin local giving first
- These cover the vast majority of total donation volume
