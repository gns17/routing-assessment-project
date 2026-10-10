# Approved architecture

## Decision and scope

Use Django ORM and the default SQLite database for normalized stations, prices,
coordinates, enrichment metadata, and status. This approved decision supersedes
the enriched-CSV/in-memory repository design. The source CSV remains immutable
seed data. Conventional Django persistence and durable enrichment progress are
deliberate benefits; Django does not require a database and ORM speed is not assumed.
Measure query and processing performance on the expected workload.

The implementation is complete for the disclosed reviewed subset. Geoapify is the
endpoint geocoder/router; unattended nationwide station enrichment was rejected
by feasibility investigations. Six independently reviewed sites support strict
planning. An approved opt-in conditional layer uses the committed Census locality
snapshot when strict coverage is insufficient; it never promotes hints to verified
station records. Research sites remain outside the approved database.

## Evidence and dataset handling

The supplied CSV contains 8,151 rows, 6,738 distinct OPIS IDs, and no coordinates.
There are 620 Canadian rows (112 IDs), leaving 7,531 US rows and 6,626 US IDs.
There are no blank fields or invalid numeric prices in the inspected snapshot.
There are 678 repeated-ID groups, 597 IDs with conflicting prices (487 US),
and 26 extra exact duplicate rows. Highway descriptions dominate: 4,617 rows
mention an exit. Geocoding quality is the principal feasibility risk.

Keep the supplied CSV immutable. Offline preparation validates headers, required
values, positive finite Decimal prices, IDs, and country/state classification.
Normalize whitespace, group by OPIS ID, select the lowest listed price, and
preserve original min/max and source-row references. Do not merge different IDs
solely because their highway descriptions match. Reject identity/location
conflicts rather than silently picking coordinates. Exclude non-US records.

## Persistence and offline preparation

Keep one station record per unique OPIS ID, with normalized name/address/city/state,
current selected Decimal price, original min/max, source-row provenance, active
status, nullable latitude/longitude, and enrichment status/source/query/confidence,
attempt timestamp, location fingerprint, and policy version. Use a small persisted
dataset-state record for source checksum, import-policy version, and revision.
An import-run audit table or price-history table is not required for this snapshot.

Use database uniqueness for OPIS identity, positive-price/min-max checks, and checks
for coordinate ranges and paired nullability. Accepted enrichment requires valid
coordinates and matching fingerprint/policy. Validate strings, finite numbers,
status transitions, and provenance at the command boundary as well. Index latitude
and longitude for coarse geographic filtering; inspect SQLite query plans rather
than assuming both range indexes will be used simultaneously. SQLite Decimal
storage has limitations; calculate money in Python Decimal, not SQL arithmetic,
and test source-price round trips at the chosen field precision. See the official
[Django SQLite notes](https://docs.djangoproject.com/en/6.0/ref/databases/#sqlite-notes)
and [SQLite query-planning guidance](https://www.sqlite.org/queryplanner.html).

CSV ingestion and location enrichment are separate management-command concerns.
Parse, normalize, validate, and deduplicate the entire seed before a write
transaction. Reject malformed input before changing the database; report expected
Canadian exclusions and price ambiguity. Bulk-read existing IDs/fingerprints,
then use bounded bulk writes within one transaction.atomic() for this small import,
including the dataset revision/provenance change. Roll back the whole import on
failure. Reimporting unchanged content under the same policy is idempotent.
New IDs are inserted; absent IDs are marked inactive only after a validated,
explicit full-snapshot import, not a partial sample. No hard-delete or CRUD API.

The location fingerprint covers OPIS ID and normalized name/address/city/state
used in the query. Exclude all pricing, timestamps, source-row positions, and the
overall source checksum. Keep the checksum for provenance, and compare enrichment
policy separately. Price-only reimports preserve accepted coordinates and require
zero geocoding calls. Changed location inputs invalidate enrichment and make it
ineligible for runtime planning until reviewed/re-enriched.

Current enrichment boundary: import an explicitly reviewed JSON coordinate artifact
using `import_station_coordinates --reviewed`. Each record must carry OPIS ID,
current location fingerprint, bounded coordinates, policy, source, identity
attestation, and evidence. Unknown, inactive, stale, unverified or explicitly
synthetic entries reject the whole artifact. Updates and dataset revision commit
together; repeating unchanged evidence is idempotent. This command makes no HTTP
requests. Human review of identity and station placement remains essential: an
attestation flag does not establish correctness by itself. Six reviewed station sites have been imported for the demonstration; no research
coordinates are approved production imports. The stored pending/ambiguous/rejected statuses preserve
unresolved records without making them eligible for planning.

Any future approved resolver reads inputs before HTTP and writes results in a
short transaction only if inputs still match. No HTTP, sleeps or retries may run
inside database transactions. Run one offline mutating command at a time;
concurrent ingestion writers and exactly-once external execution are out of scope.
No automatic Geoapify enrichment loop is implemented after the negative spike.

The assignment still uses a fixed price snapshot. Reimport supports price changes
without re-geocoding, but live pricing feeds, scheduled updates, CRUD endpoints,
administrative interfaces, file watching, and additional infrastructure are out
of scope. Database persistence makes later extensions possible without implementing
those extensions now.

## Runtime boundaries

| Component | Responsibility |
| --- | --- |
| DRF validation | Bounded start/finish strings and optional strict JSON boolean `allow_estimates` |
| Endpoint resolver | Geoapify geocoding, ambiguity/US checks, permitted caching |
| Routing adapter | HTTP timeouts/errors and normalized geometry/distances |
| Station repository | Indexed ORM bounding-box filtering; project needed columns into plain objects |
| Route matcher | Pure Python segment projection, proximity, and along-route position |
| Fuel optimizer | Pure Python purchases, inventory, feasibility, and expenditure |
| Planning service | Orchestration, response assembly, versioned caching |
| Leaflet view | Display existing GeoJSON and stops with required attribution |

The repository interface describes station candidates, not ORM operations, so a
future storage change does not alter its callers. It returns plain station objects,
not storage rows or Django models.
The matcher and optimizer contain no HTTP calls, ORM access, or Django imports.

Start with buffered route bounding-box filtering, then precise segment matching.
Filter active stations with accepted, current enrichment and valid prices. Use
values()/values_list() to fetch only required columns in a bounded number of
queries; never query per candidate or instantiate unnecessary model objects.
Read dataset revision and candidates in a short consistent read transaction,
after all provider requests have completed; finish the transaction before precise
matching and optimization. No long-lived database read snapshot crosses HTTP work.
Use detailed geometry, cumulative haversine segment lengths and local segment
projection. Normalize validated provider leg/step distances into segment weights
and interpolate only within each step. Missing step data explicitly falls back to
geometry proportions scaled to total road mileage. Neither method proves road
access or exact within-step chainage; reject inconsistent supplied step metadata.
Round chainage to a micro-mile to suppress floating noise, not to imply accuracy.
Reject disconnected geometry; preserve separate visits on route loops. Handle route loops deterministically. The corridor is configurable;
STATION_CORRIDOR_MILES defaults provisionally to 1 for local development,
not as a calibrated claim. Real-data accuracy review is still required before
settling the operational default.

## Fuel model and response

Capacity is 50 US gallons, starting full; consumption is 10 MPG; usable range is
500 miles; no destination reserve is required. Allow partial fills.

On the fixed route, buy just enough to reach the first cheaper station within
range. If none exists, fill up, capped by fuel needed to finish. Track inventory
through successive candidates, return only positive purchases, and reject
unbridgeable coverage gaps. Use Decimal money and round only displayed amounts.
Test optimality against an exhaustive oracle on small synthetic cases.

Return route GeoJSON/distance, stop identity and coordinates, listed price,
gallons/cost per purchase, total_fuel_cost, gallons_consumed, gallons_purchased,
map_url, dataset version, and relevant coverage/approximation information.
total_fuel_cost excludes the unknown cost of the starting tank. Cheapest-price
selection is an explicit optimistic assumption. These prices are not live.

Greedy optimality applies only to the fixed-route model with accepted candidates,
unlimited supply, partial purchases, and no stop penalty. A corridor cannot prove
road accessibility. Baseline consumption and reachability exclude unverified
access detours; verified waypoint routing would require a reviewed extension.

## Provider calls and performance

Successful uncached string requests target two endpoint geocoding calls and one
routing call. Cached endpoints reduce calls; complete result caching can eliminate
them. Reuse geometry for the map. Browser tile requests are counted separately.
Bound timeout/retry behavior and count attempts explicitly. Do not perform
per-station routing, geocoding, reverse geocoding, or matrix queries at runtime.

Use simple Django process-local caching initially. Route keys include ordered
endpoints, provider, and profile/options. Fuel-plan keys also include route identity,
persisted dataset revision, corridor, and fuel policy. Read the shared revision
before plan-cache lookup so all workers stop selecting stale keys after imports
or accepted-enrichment changes commit. Return the revision actually used to read
candidates; an in-flight request may finish against its older consistent snapshot.
Changes invalidate plans without invalidating routes. Process-local route/plan caches reset
on restart; no startup-loaded station collection or automatic reload is required.
Map snapshots use Django's built-in file cache under the ignored .cache/maps
directory, shared by workers on the same machine, with a one-hour TTL. This fixes
cross-worker map URLs without another service. Multi-host sharing, cleanup beyond
Django cache eviction, and persistent/public map links are outside scope.

Benchmark cold/warm short and cross-country routes, dense/sparse station coverage,
ORM filtering/query counts and query plans, matching/optimization time, memory,
payload size, external calls, and SQLite lock behavior. Initial local measurements are recorded in docs/implementation-progress.md;
synthetic geometry timings and a database with zero accepted coordinates do not
establish nationwide production performance. Do not assume ORM or in-memory filtering is inherently faster.

## Validation and scope

Test dataset parsing/deduplication, database constraints, import rollback/idempotence,
resumable enrichment and stale-response rejection,
input-fingerprint invalidation, endpoint validation, provider failures, geometry
matching, fuel conservation/range/optimality, response/map behavior, and call
counts. Routine tests use fixtures and mocked providers; they make no live calls.
Verify bounded query counts, inactive/unaccepted station exclusions, revision/cache
consistency, and that price-only changes preserve the location fingerprint and accepted
coordinates without invoking geocoding, while location changes invalidate them.
Run uv-based tests and Ruff after meaningful implementation changes.

Out of scope: global road-network cost optimization, live prices, traffic/tolls,
fleet features, a frontend application, and production infrastructure. Do not add
PostgreSQL, PostGIS, Redis, Celery, or self-hosted routing. No station CRUD/admin UI.
Full-country geocoding quality and budget remain subject to the feasibility review.

## Optional conditional planning

Strict planning always runs first and its successful contract is preserved. Only
`insufficient_station_coverage` can invoke opt-in best effort. A separate pure Python
layer groups original OPIS identities/prices by versioned locality hints or explicit
physical-estimate evidence, projects assumed positions and invokes the unchanged
optimizer. Locality anchors are areas, not station coordinates or navigation points.
All quantities are conditional; `fuel_feasibility` stays unverified, actionable
`fuel_stops` stays empty and guaranteed totals remain null.

ORM stations remain the identity/price source. The static hint file is a deployment
snapshot loaded once per worker, not replacement station persistence or runtime
geocoding. Grouped locality anchors prevent fictitious independent repeated stops.
Mode-specific plan caches include dataset revision and hint content version;
provider geometry caches are shared. Supplied uncertainty bounds can reject a
scenario; unknown access/position bounds never become a fabricated safety margin.
See the [response contract](best-effort-planning.md) and [fixture index](../data/README.md).
