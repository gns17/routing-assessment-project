# GNS-8 / GNS-10 validation review

Reviewed against the existing Linear criteria on 2026-10-09 UTC. This is local
verification only. No live Geoapify requests, OSM downloads or real-coordinate
imports occurred. All synthetic fixtures remain in isolated tests or the disposable
benchmark database. Existing source/production records were not changed.

## Defects fixed

1. Adjacent long segments could merge separate visits to one station on an
   out-and-back route. Visits now merge only when the shared vertex remains in the
   corridor; tests establish separate positions at 200 and 600 miles.
2. Route-wide scaling discarded available provider road-step distances. The
   adapter now validates leg/step geometry indexes and distances, distributes each
   step's mileage over its own geometry and preserves cumulative totals. Within-step
   position still interpolates geometric proportions. Steps must cover geometry
   contiguously; materially inconsistent totals/indexes fail safely. Small rounding
   differences (up to max 10 meters or 1% of route distance) are normalized to total
   mileage. Absent steps explicitly use the prior scaled-geometry fallback.
3. Geometry altitude values previously broke two-coordinate distance unpacking;
   horizontal distance now ignores altitude. Disconnected legs are rejected rather
   than hiding a gap of up to 16 meters.
4. Matching recalculated projection parameters and distances for every candidate
   against every segment. Parameters/buffer boxes are prepared once, and cheap
   per-segment coordinate bounds skip distant candidates without changing mileage.
5. Invalid provider state/properties types could escape safe error handling. New
   regression tests verify safe unresolved/provider-response errors.
6. Infeasibility returned no useful gap diagnostics. Success now includes coverage
   counts/largest gap; 422 coverage errors include unbridgeable intervals and the
   revision used. None implies complete CSV coverage or verified road access.
7. Plan caches now include segment mileage and a matcher policy version; endpoint/
   route cache namespace also changed to prevent using the old normalized shape.

Step fields (`distance`, `from_index`, `to_index`) and their per-leg geometry mapping
are documented in [Geoapify Routing API](https://apidocs.geoapify.com/docs/routing/).
No additional details or provider call is requested. This adapter interpretation
is mocked/tested, not confirmed against a new live routing response.

## Acceptance evidence

| Criterion | Evidence / remaining limit |
| --- | --- |
| Segment projection/order/chainage | Segment-interior and junction projection; corridor boundary; loops/out-and-back; degenerate/disconnected geometry; altitude; step-weighted cumulative mileage. Detailed road geometry is still required, and within-step mileage is interpolated. |
| ORM eligibility/filtering | Active, accepted/current fingerprint/policy, positive prices, coordinate ranges; plain projected records; two SELECTs; indexed range query in measured SQLite plan. DB constraints reject stale accepted coordinates. |
| Consistent revision | Same short read transaction for revision/candidates; HTTP before reads; matching afterward. Independent worker-cache tests and an import after snapshot prove old results stay under old revision. |
| Fuel integration | 1,300-mile tests with two and three positive purchases, competing prices, inventory in [0,50], consumption/purchases, order, and coverage gaps. Independent optimizer oracle remains in the full suite. |
| DRF contract/errors | GeoJSON, stop identity/coordinates/price/purchases, totals, inventory, revision, corridor, mileage method, qualified coverage, warnings, map URL; invalid input makes no HTTP calls; provider failures sanitize credentials. |
| Leaflet | Template tests confirm reused geometry/stops, attribution, map expiry/shared local cache, safe JSON/XSS handling. Added start/finish markers, ordered purchase labels and fuel summary. No actual browser rendering or tile smoke test has run. |
| Performance | Disposable benchmark populates all 6,626 source IDs with labeled synthetic locations; short/multi-stop/large geometry workloads, cold/warm timings, memory, payload, query counts and mock request counts. No live provider or real-coordinate distribution claim. |
| Real corridor/default calibration | Still pending: no real coordinates to assess identity, station access or operational corridor default. One mile remains provisional/configurable. |

Full suite: **143 passed**. Ruff lint passes; relevant implementation files are
formatted; Django system checks and migration-drift checks pass. Existing unrelated
Django scaffold formatting is not changed by this review.

GNS-8 cannot yet satisfy its real-accuracy justification for the operational corridor
value. GNS-10's local contract/integration checks pass, but its D dependency and the
real map/coverage demonstration remain unresolved. Both stay In Progress; no Linear
records were changed during this review because the full completion gates are not
satisfied. This does not claim live integration was verified.

## Local performance evidence

Reproduce with `uv run python -m spikes.benchmark_planning --output /tmp/planning-benchmark.json --repetitions 3`.
The utility always configures a disposable database before Django initialization,
asserts that database location, mocks all HTTP, and deletes the database afterward.
It never writes benchmark coordinates to production SQLite. Machine-readable
results: [local-planning-benchmark.json](../data/local-planning-benchmark.json).

| Synthetic workload | Segments | Eligible candidates | Cold median | Warm median | Payload | Python traced peak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 200 miles | 250 | 1,040 | 188.576 ms | 25.234 ms | 4,329 B | 2.432 MiB |
| 1,300 miles | 2,000 | 1,894 | 865.313 ms | 58.104 ms | 30,108 B | 3.820 MiB |
| 2,600 miles | 5,000 | 1,894 | 2,029.786 ms | 97.305 ms | 75,052 B | 6.703 MiB |

Three repetitions/workload, including tracemalloc overhead, local Mac/Python
3.13.16. Two SELECTs per cold request. Nine mocked HTTP attempts per workload
(three cold requests × three attempts); warm requests add zero. Actual external
requests: zero. Whole-process peak RSS: 132.484 MiB including setup/import, distinct
from traced per-workload allocations. SQLite used its longitude index. No latency
SLA, provider timing, heavy-concurrency/locking or national-data distribution is
established. These results do not justify adding infrastructure.

## Remaining delivery priorities

Required: approve/execute a bounded genuine corridor demonstration; reconcile enough
source identities; verify route mileage/provider response and basic browser/map;
record remaining coverage/access limits; final checks and <=5-minute Loom/GitHub
submission preparation. Do not publish/record automatically.

Valuable optional: a few competing verified stations in each refueling region,
corridor sensitivity on those real coordinates, simple concurrency/lock observation,
and independent manual mileage checks. Keep these bounded.

Safe to defer: GNS-12 broad state extraction if it does not directly unblock the demo,
nationwide enrichment, all unresolved stations, live pricing, multi-host deployment,
new persistence/index services, automated road-access routing, and station CRUD.

The principal deadline risks are identity/coordinate availability, historic branch
or address changes, stations on the wrong carriageway, one-mile corridor excluding
legitimate exits, unverified access detours, and an unexpected live provider shape.
No amount of passing synthetic tests resolves these data/integration risks.
