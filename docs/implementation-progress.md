# Implementation evidence

Local core implementation and mocked integration completed on 2026-10-09 UTC.
The later [validation review](route-validation-review.md) records 143 passing tests,
additional fixes and a reproducible full-dataset synthetic benchmark. The original
measurements/test counts below are preserved as historical implementation evidence.
No new external API calls or dataset downloads were made.

## Components

- GNS-7: Geoapify adapter with bounded timeouts, three-attempt cap, no retries,
  US/ambiguity checks, geometry validation and price-independent caches. HTTP occurs
  before repository transactions. Endpoint serializer supports only start/finish strings.
- GNS-9: storage-independent Decimal optimizer, starting full, partial purchases,
  conservation and explicit infeasibility. Tested against a separate exhaustive
  integer-gallon oracle over 35 deterministic small random cases.
- GNS-6: Station/DatasetState models, migrations, validated bulk CSV import and
  reviewed-coordinate artifact import. Tests cover constraints, rollback, idempotence,
  price reuse, location invalidation, explicit deactivation and stale evidence.
- GNS-8/10: projected ORM repository, pure segment matcher, DRF POST endpoint,
  revision-aware plan cache and minimal Leaflet map. Integration tests use mocked
  HTTP and synthetic records only in isolated test databases.

## Actual database/source verification

Local migrations were applied and `import_fuel_prices --full-snapshot` was run twice.
First import: 8,151 source rows, 620 Canadian exclusions, 6,626 unique US stations,
6,626 created, revision 1. Second import: zero creates/updates/deactivations, revision
still 1. All real records remain pending with null coordinates. The original CSV
was not modified. No synthetic or reviewed real coordinates were imported locally.

## Initial performance measurements

Single local run on the development Mac, 8 GiB RAM; indicative, not a production SLA:

| Measurement | Observed |
| --- | --- |
| Pure matching, 300 explicitly synthetic candidates, 1,000 segments | 0.2561 s |
| Synthetic matches in that fixture | 60 |
| Repository snapshot, actual 6,626 rows, zero accepted coordinates, 20 repetitions | median 0.416 ms |
| SQLite EXPLAIN, accepted/active station bounding box | SEARCH using longitude index |

The query plan used `routing_station_longitude_0a15f66a`; SQLite did not need both
range indexes simultaneously. Repository tests enforce two SELECTs per snapshot,
with no per-station queries or model instantiation. Reads are short transactions
and matching/optimization run afterward. Matching is O(candidates × segments),
optimizer worst-case quadratic. Empty eligible coordinates are not a representative
national workload; larger/dense geometry, memory, payload, locking and provider
latency measurements remain GNS-11 work. No new storage/index infrastructure is
justified by these preliminary results.

## Validation

The full mocked suite passed (124 tests), as did Ruff lint, Django system checks,
and migration-drift checks. No test makes live provider calls. Existing generated
manage.py/asgi.py/wsgi.py formatting prevents a whole-repository Ruff format check;
those unrelated scaffold files were left unchanged. Changed implementation files
are formatted. GNS-8/GNS-10 remain In Progress for final matching/integration review;
GNS-11 submission and broader performance work remain pending.

## Known limitations and next checks

The one-mile corridor is a provisional configurable development value, not an
accuracy-calibrated default. Chainage scales geometric proportions to road mileage;
station-access detours are excluded. Only endpoints are validated as contiguous-US;
route border avoidance is not guaranteed. Final money is rounded to cents; internal
cost calculations use Decimal. Lowest duplicate prices may be optimistic.

Default route/plan caches are process-local; every worker consults the shared
SQLite revision when selecting a plan. Local map snapshots use Django's file cache
with a one-hour TTL and eviction, shared by workers on the same filesystem.
Multi-host sharing and permanent map links are not implemented. Leaflet/OSM browser
traffic is separate from backend API usage; no browser/live-map smoke test has run.

No actual-coordinate accuracy, real long-route coverage or live routing success is
claimed. GNS-12 requires separate download approval and has a 60–90 minute cap;
it must not block delivery. Do not restart Geoapify station searching.
