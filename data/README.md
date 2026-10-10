# Data, regression fixtures and attribution

Large/generated files remain when they materially support runtime behavior, source
provenance or reproducibility. No stored API response is a hosted endpoint; historical
localhost map URLs expire. Tests and offline replays never request those URLs.

## Required inputs and fixtures

| File | Role / dependency |
| --- | --- |
| `fuel-prices.csv` | Immutable assignment-provided OPIS seed; validated importer and tests. No blanket redistribution license is assigned to this third-party input. |
| `corridor-reviewed-coordinates.json` | Six approved station identities, fingerprints, site coordinates and independent evidence; importer and both recorded regressions. |
| `best-effort-locations.json` | Runtime Census locality snapshot; fallback loads once per worker. Contains no station-site coordinates or prices. |
| `corridor-route.json` | Full original endpoint/route responses and normalized geometry for Albuquerque–Nashville; required by `test_recorded_corridor.py` and pending local research tests. |
| `best-effort-live-provider-response-{1,2,3}.json` | Full original Atlanta/Miami geocodes and driving response; required by `test_recorded_best_effort.py`. |
| `best-effort-live-api-response.json` | Full expected best-effort contract/geometry used by that regression; transient map URL omitted explicitly in the live report. |
| `geocoding-feasibility.json` | Earlier geocoding/Places experiment; required by the preserved station-comparison tests. It is not approved station enrichment. |

Do not replace these with shortened independent-review copies. The runtime Census
snapshot has source/seed checksums, edition and content version; preparation is
reproducible using `prepare_best_effort_locations` with an already obtained Gazetteer.
Raw ZIP/PBF downloads, SQLite databases, browser profiles and temporary outputs
are not tracked. Coordinate ingestion uses only the approved six-record artifact.

## Supporting evidence and historical outputs

- `final-live-*`, `final-browser-*`, `final-fresh-setup-verification.json`: strict
  live/API/browser/fresh-setup evidence; source results are historical, not current prices.
- `best-effort-live-*`, `best-effort-readable-popup-browser-verification.json`:
  approved live conditional scenario, exact inventory/candidate audit, usage ledger
  and browser proof. API geometry is real; station/locality assumptions remain unverified.
- `delivery-*.json`: final isolated setup and quality checks, explicitly recorded replay.
- `corridor-investigation.json`, `corridor-local-integration.json`,
  `corridor-offline-api-response.json`: pre-live coordinate/integration provenance,
  retained with historical context in `docs/archive/` rather than treated as latest output.
- `best-effort-validation.json`, `best-effort-browser-verification.json`,
  `local-planning-benchmark.json`: prior offline/synthetic validation and performance;
  the $88.06 example uses synthetic geometry, unlike the live $48.66 scenario.

Redundant historical snapshots are not runtime inputs. They are retained at stable
paths to preserve the audit trail and existing references; the reviewer entry point
links the current reports. Research scripts/tests are supporting investigation, not
application services or a requirement to repeat nationwide enrichment.

## Recorded Geoapify results: reuse and attribution

Checked against official published pages on October 10, 2026:

- [Geoapify products/services](https://www.geoapify.com/products-and-services/)
  explicitly permits caching, storing and redistributing service results.
- [Platform licensing statement](https://www.geoapify.com/#why-choose-geoapify-location-platform)
  includes geocoding reuse; [routing documentation](https://www.geoapify.com/routing-api/)
  describes routing-result reuse. This supports retaining full responses as fixtures;
  it is not permission to redistribute API credentials or sublicense service access.
- [Terms, version 5 dated February 2, 2024](https://www.geoapify.com/terms-and-conditions/)
  require OpenStreetMap attribution and Geoapify attribution for the Free plan,
  plus any API/source-specific attribution.
- Saved geocodes identify OpenStreetMap as their source and the Open Database License.
  Retain datasource/license fields and [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
  including its ODbL notice and conditions. No blanket license for all repository
  data or automatic exemption from upstream obligations is claimed.

Provider-result redistribution has published support; account-specific agreements,
if any, still govern the subscriber. Census-produced locality data is public domain
in the US, separately from Geoapify/OSM and assignment-provided prices; retain its
source/edition and [Census policy](https://www2.census.gov/foia/ds_policies/ds027.pdf).

The shared Leaflet attribution control preserves OpenStreetMap credit and includes
an always-visible **Powered by Geoapify** link in both strict and best-effort modes.
The static link uses `target="_blank"` and `rel="noopener noreferrer"`; it has no
`nofollow` restriction. This corrects the earlier free-plan attribution gap without
changing any API fields, routing, matching or fuel assumptions. Original screenshots
remain historical evidence; refreshed images use the same saved responses and are
explicitly labeled replay, not additional live API verification.

Routing/geocoding powered by [Geoapify](https://www.geoapify.com/).
