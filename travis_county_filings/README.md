# Travis County Commissioners Court — Campaign Finance Filings

Campaign finance filing PDFs for the current incumbent members of the Travis
County Commissioners Court, pulled from the county's EasyVote public filings
portal: https://traviscountytx.easyvotecampaignfinance.com/home/publicfilings

Retrieved: 2026-07-15. PDFs are the public (redacted) versions served by the
portal. Every filing listed on the portal for each official is included.

## Officials

| Folder | Official | Office | Filings |
|---|---|---|---|
| `county-judge_andy-brown/` | Andy Brown | County Judge | 11 |
| `pct1_jeff-travillion/` | Jeff Travillion | County Commissioner, Precinct 1 | 13 |
| `pct2_brigid-shea/` | Brigid Shea | County Commissioner, Precinct 2 | 19 |
| `pct3_ann-howard/` | Ann Howard | County Commissioner, Precinct 3 | 10 |
| `pct4_margaret-gomez/` | Margaret Gómez | County Commissioner, Precinct 4 | 17 |

70 filings total.

## File naming

`<date-submitted>_<document-name>.pdf`, e.g. `2026-01-15_COH.pdf`.
Dates are ISO (YYYY-MM-DD) as reported by the portal's "date submitted" field.
Document names come from the portal and are mostly Texas Ethics Commission
form types:

- **COH / C-OH** — Candidate/Officeholder campaign finance report (Form C/OH)
- **CCOH** — Corrected C/OH report
- **ACTA / CTA** — (Amended) Appointment of campaign treasurer
- Some filers uploaded PDFs with custom titles (e.g. `Shea-Jul-2024-COH`);
  those titles are kept, sanitized for filesystem safety.

## Manifest

`manifest.json` lists every file with its portal document ID, document type,
submission date, and election association — useful for re-downloading or
checking for new filings.

## Re-downloading / updating

The portal is an Angular SPA backed by `https://ecf-api.easyvoteapp.com`.
Anonymous access flow:

1. `GET /authentication/getwebsiteuser/traviscountytx` (with an
   `Origin: https://traviscountytx.easyvotecampaignfinance.com` header)
   returns `UserId` and `CustomerId`.
2. `GET /filer/documentsearch/{CustomerId}` with header
   `Easy-Vote-Authenticated-User: UserId:...|CustomerId:...|ZumoToken:null`
   returns all filers and their document lists.
3. `GET /documents/{documentid}/viewfinalredactedpdf` (same headers)
   returns the PDF. (`/viewfinalpdf` is the unredacted version and returns
   401 for anonymous users.)
