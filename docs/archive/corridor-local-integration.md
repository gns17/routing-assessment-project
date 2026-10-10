# Local reviewed-coordinate import and offline DRF milestone

The investigation/rounding-fix checkpoint is **d714375**, created before import.
It is local only, not pushed. Its eight files were reviewed for credentials and
unintended sensitive content; they contain business-site evidence and sanitized
provider responses. The SQLite database is ignored and was not committed.

## Dry run and import

Added a small `--dry-run` option to the existing reviewed-coordinate command. It
runs the same schema/identity/fingerprint validation and computes changes in a read
transaction, then returns before any writes or dataset-state creation. Tests cover
no station/revision writes, stale identity rejection and an unchanged artifact.

Executed locally:

```sh
uv run python manage.py import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed --dry-run
uv run python manage.py import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed
```

The dry run selected exactly **4227, 4446, 6755, 7733, 52458, 52468**. Each existed
in the original CSV and local imported source; current location fingerprints,
branch numbers, city/state, official source and address evidence matched the review
ledger. Coordinate ordering is latitude then longitude: all latitudes 34–36 N and
longitudes 91–103 W. They represent corroborated station sites, not verified highway
entrances. The dry-run SQLite hash matched its pre-run value.

The actual import used the command's atomic six-record update/revision transaction.
Whole-dataset before/after snapshots confirmed:

- Exactly the approved six station rows changed, only coordinate/enrichment fields.
- All **6,626** station identities, source data and price fields stayed unchanged.
- **Six accepted/current locations**, **6,620 unresolved** paired-null locations.
- Dataset revision **1 → 2**; checksum/import policy and original seed CSV retained.
- Repeat import accepted **zero** new changes and left revision **2**.

Only the local development `db.sqlite3` was modified. The validator checked its
resolved path/SQLite engine, and compared every other row/field after import.
Machine-readable observations: [corridor-local-integration.json](../../data/corridor-local-integration.json).

## Actual API pipeline with recorded provider transport

Used Django's APIClient against the real views/serializers, Geoapify adapter,
ORM-backed repository, geometric matcher, optimizer, cache and map view. Only the
HTTP transport was replaced with replies saved during the approved live investigation.
Python socket connection entry points were blocked; no external request was made.

Before import the same long route returned **422 insufficient_station_coverage**.
After import it returned **200**, using unchanged geometry and provider step mileage:

- Driving distance **1,221.630055 miles**.
- Six matched stations, ordered at **290.859611, 292.979032, 533.416479,
  533.516811, 884.396169, 884.510260 miles**.
- Largest eligible-network gap **350.879358 miles**, none above 500.
- Four positive purchases, nonnegative inventory, capacity no greater than 50 gallons.
- **122.163006 gallons consumed**, **72.163006 purchased**, **$232.44 purchase cost**,
  zero ending reserve/fuel; unknown starting-tank cost excluded.
- API snapshot revision **2**, `mileage_method=provider_steps`,
  `coverage.scope=reviewed_candidates_only`, `complete_csv_coverage=false`.

Response retained the exact saved route geometry and actual ORM station identities,
coordinates and snapshot prices. Internal comparisons allowed <=0.0000005 gallon
or mile display rounding, and <=$0.005 per displayed purchase; no optimizer objective
was changed. Full response: [corridor-offline-api-response.json](../../data/corridor-offline-api-response.json).

| Purchased at | Route mile | Gallons | Displayed cost |
| --- | ---: | ---: | ---: |
| Love's #200 — OPIS 4446 | 290.859611 | 29.085961 | $93.34 |
| Flying J #723 — OPIS 7733 | 292.979032 | 0.211942 | $0.69 |
| Flying J #703 — OPIS 52468 | 533.416479 | 9.141714 | $30.25 |
| Petro #326 — OPIS 6755 | 884.396169 | 33.723389 | $108.16 |

The **0.212-gallon** purchase is valid under the divisible-fuel, zero-stop-penalty
mathematical model. It can be operationally unrealistic because travel time,
minimum fills and stop inconvenience are excluded. No stop penalty, minimum fill or
stop-count objective was added. Optimization is only among the reviewed subset on
one provider route, not among all CSV stations or routes; prices are not live and
station-access detours remain unverified/excluded.

Single local post-import API request took **0.052535 s**, excluding live HTTP latency.
Three recorded transport replies were used initially; subsequent route repeats used
permitted caches and no additional replies. Actual external HTTP attempts: **zero**.
This measurement is a local verification observation, not a production SLA.

## Cache consistency and coverage failures

A successful same-location zero-mile plan was cached at revision 1 before import.
After import the same request returned revision 2, proving the stale revision-1 plan
was not selected. The full route then returned stable revision-2 purchases on repeat.
Other rows/prices were rechecked after API/cache operations and stayed unchanged.

With a 0.1-mile corridor, the **same actual saved route** returned 422, because
Arkansas stations were excluded and the remaining final gap exceeded 500 miles.
Changing corridor therefore did not select the cached one-mile success result.
A separate explicitly **synthetic failure-test** geometry outside the reviewed
region also returned 422 and zero eligible stations. It is not a live route, is not
used for demonstration and contributed no fake station records, prices or stops.
The complete regression suite retains other coverage/provider-failure cases.

## Map and browser status

The map view returned **200**, embedding the exact route/purchases, correct attribution,
endpoint markers, cost summary and dataset revision. The actual client JavaScript
also passed an isolated local contract execution using a **test SDK stub**: correct
geometry handoff, four purchase markers, two endpoint markers and summary text.
This is not actual Leaflet/browser rendering and is not presented as such.

**Browser/Leaflet visual verification remains pending.** Leaflet JS/CSS and OSM tiles
are external resources, no local Leaflet/Playwright package is installed, and this
phase makes no external requests or downloads. No screenshot/rendering success is
claimed. The recorded response's `map_url` is generated by Django testserver context;
a development server/browser must be exercised separately, with authorized asset
and tile loading, before a public demonstration is claimed.

## Checks, remaining gate and scope

The full suite now passes **148 tests**, including dry-run tests and a reproducible
recorded-real-corridor regression in an isolated SQLite test database. Ruff lint,
Django checks and migration-drift checks pass. No new planning/optimization defect
was found; the missing dry-run mode was implemented for this authorized import.
GNS-8/GNS-10 remain In Progress, with final corridor-default/accuracy review and
actual browser/provider demonstration still outstanding. No Linear status changed.

Recommended final live budget: **three HTTP attempts**, no retries, approximately
six credits with an **eight-credit conservative allowance**, for a cold start:
two endpoint geocodes and one driving route through the actual DRF API. One routing
attempt can suffice only with previously validated endpoints already in that worker's
cache; this phase does not assume such a cache survives process exit. Browser static
assets/tile loading is separate from Geoapify backend calls. It can be verified from
recorded geometry without another Geoapify call if that browser access is approved.

No new commits were pushed, external API requests made, or datasets downloaded.
The dry-run implementation and this milestone's tests/evidence/documentation are
local changes made after checkpoint d714375, awaiting the next commit/push decision.
