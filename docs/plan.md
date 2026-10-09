# Implementation plan and Linear backlog

Project: [Spotter Routing API — Three-Day Assessment](https://linear.app/gns17/project/spotter-routing-api-three-day-assessment-23c93ff7abb6).

The architecture in [architecture.md](architecture.md) is approved. Project and
issues A–G have been created. Only Issue A is the first implementation
task; complete application implementation must not begin yet. External geocoding
requires approval of the execution plan and request budget below.

| Plan issue | Linear issue | Initial status |
| --- | --- | --- |
| A | [GNS-5](https://linear.app/gns17/issue/GNS-5/a-geoapify-geocoding-feasibility) | Todo |
| B | [GNS-6](https://linear.app/gns17/issue/GNS-6/b-persist-stations-and-implement-csv-importoffline-enrichment) | Backlog |
| C | [GNS-7](https://linear.app/gns17/issue/GNS-7/c-implement-string-based-route-acquisition-and-caching) | Backlog |
| D | [GNS-8](https://linear.app/gns17/issue/GNS-8/d-filter-orm-station-candidates-and-match-route-geometry) | Backlog |
| E | [GNS-9](https://linear.app/gns17/issue/GNS-9/e-implement-cost-effective-fuel-purchasing) | Backlog |
| F | [GNS-10](https://linear.app/gns17/issue/GNS-10/f-deliver-api-response-and-minimal-leaflet-map) | Backlog |
| G | [GNS-11](https://linear.app/gns17/issue/GNS-11/g-validate-performance-and-prepare-submission) | Backlog |

Dependencies have been recorded in Linear. High maps to priority 2; Normal maps
to Linear's Medium priority (3). Issue A is waiting for execution approval.

## A — Geoapify Geocoding Feasibility

Priority: High. Dependencies: none. First technical task.

Select 30 distinct US station IDs representing highway exits, intersections,
rural/ambiguous addresses, chain branch numbers, independent stops, and regions.
Target 12 single-exit descriptions, eight highway intersections, six rural or
otherwise ambiguous descriptions, and four numbered/local-address descriptions.
Assign each station to one primary category; verify availability and document any
quota adjustment before calls. Include Northeast, South, Midwest, and West, both
chains and independents, and repeated-ID/name-variant examples. Select by stable
OPIS-ID ordering within categories, choosing geographic spread explicitly. This
is a diagnostic sample, not a statistically representative accuracy estimate.
Preserve selection rationale and source-row references. Begin with a
five-station pilot; inspect it before processing the remaining sample.

Use one primary query per station (name + normalized address + city/state, US
filter). Permit at most one fallback for up to ten ambiguous/failed matches.
Inspect returned identity, coordinates, type/precision, confidence fields, and
manual map placement. City/road-level results cannot be accepted solely because
the provider labels them confident.

Required credential: GEOAPIFY_API_KEY in an untracked .env or process environment.
Never print/log the key or persist credential-bearing request URLs. An account
with sufficient geocoding quota is needed. No routing or separate map credential
is required for this spike; manual coordinate inspection can use a browser map.

Proposed external budget: 30 primary calls plus at most 10 fallbacks, with a hard
cap of 40 total HTTP attempts including retries. Geoapify documentation currently
prices ordinary geocoding at one credit/request; allow approximately 40 credits
against the account's shared quota. Run sequentially at no more than one request
per second, use bounded timeouts, and stop on authentication/quota failures.
No routing, batch-geocoding, or nationwide enrichment calls are authorized.

Acceptance: a sample/results report distinguishing accepted, ambiguous, rejected,
and unresolved matches; manual review of at least ten including problematic
cases; calls/credits/timing; recommended acceptance rules, coverage risks, and
corridor sensitivity. Propose a corridor default only if evidence supports it.
Review findings before nationwide enrichment. No API application is built here.
Spike implementation is limited to sample selection, a small bounded HTTP runner,
simple result checkpoints, mocked tests for budgets/errors/resume/key redaction,
and a findings report. Do not build the full preparation pipeline or runtime API.
Implement only after presenting this plan; live calls still require explicit
approval. Issue A remains Todo while waiting for execution approval.
The spike may use a small diagnostic file checkpoint; this is not runtime station
storage. Do not add production models or run migrations as a prerequisite to A.
Issue B owns the ORM schema, import, and production enrichment persistence.

## B — Persist stations and implement CSV import/offline enrichment

Priority: High. Dependencies: A and review of its findings.

Use Django ORM + default SQLite for normalized stations, selected/min/max prices,
coordinates, enrichment metadata/status, and persisted dataset revision/provenance.
Preserve immutable CSV source and unique OPIS identity. Add appropriate database
checks and coordinate indexes. Keep price selection separate from location enrichment;
location fingerprints exclude pricing, timestamps, row positions, and source checksum.

Implement management commands for reproducible bulk import and resumable offline
geocoding. Validate the complete import before short transactional writes; commit
all import changes and revision together or roll back. Unchanged reimports are
idempotent; validated full-snapshot imports can mark absent stations inactive.
Price-only changes retain accepted coordinates and cause zero geocoding calls.

Make provider calls outside transactions; persist each result/status in a short
transaction only if input fingerprint/policy still match. Resume from persisted
status, reject stale responses, and update revision for planner-visible changes.
Test rollback, constraints, idempotence, resumption, and coordinate reuse. Review
nationwide geocoding budget separately. No live feeds, scheduler, CRUD/admin UI,
PostgreSQL, PostGIS, Redis, or Celery. Models/migrations belong to this future issue,
not the present planning-reconciliation task.

## C — Implement string-based route acquisition and caching

Priority: High. Dependencies: A.

Validate start/finish strings; resolve unambiguous US locations through Geoapify;
obtain normalized driving geometry/distances. Isolate HTTP behavior and cache
permitted results. Test provider failures and the successful uncached baseline
limit of two geocoding calls plus one routing call. No runtime station geocoding.
Keep route cache keys independent of prices. Specify the fuel-plan cache contract
using persisted dataset revision, route identity, corridor, and fuel policy;
B/D/F wire the revision read to candidate selection and full-plan caching.
Do not hold a database transaction across endpoint geocoding or routing.

## D — Filter ORM station candidates and match route geometry

Priority: High. Dependencies: B, C.

Implement an ORM-backed station repository with indexed coordinate bounding-box
filtering for active, valid-price stations with accepted, current enrichment.
Project only needed columns through values()/values_list() into plain objects;
avoid N+1 queries and unnecessary model instantiation. Keep the repository's
candidate interface independent of storage.
Read revision and candidates in a short consistent transaction after provider
calls, then perform precise segment projection and optimization outside it.

Implement pure Python route positions/proximity and a configurable corridor;
justify its default with accuracy tests. Test loops, boundaries, distance/coverage,
station eligibility, revision consistency, and bounded query counts. Inspect
SQLite query plans and benchmark actual filtering/matching rather than assuming
ORM is faster. Disclose unverified station-access detours.

## E — Implement cost-effective fuel purchasing

Priority: High. Dependencies: A; integration depends on D.

Implement pure Python greedy purchases for a full 50-gallon starting tank, 10 MPG,
and no ending reserve. Return purchase expenditure, consumed/purchased gallons,
and inventory accounting. Test partial fills, ties, exact range boundaries,
infeasibility, conservation, and optimality on small cases. Exclude the unknown
initial tank cost and keep business logic independent of Django and providers.

## F — Deliver API response and minimal Leaflet map

Priority: High. Dependencies: C, D, E.

Connect planning components and return route GeoJSON, fuel-stop data, totals,
dataset version derived from the persisted revision, approximations, and map_url.
Read shared revision before fuel-plan cache lookup and key plans by revision and
planning parameters. Return the revision actually used for candidate selection;
in-flight requests may finish against an older consistent snapshot. Do not mix
prices/coordinates from different revisions or cache old data under a new revision.
Serve a minimal attributed Leaflet view reusing geometry/stops. Test ORM-backed
integration, response/map behavior, cross-worker revision-aware cache selection,
and backend call counts. No frontend application or station CRUD/admin UI;
browser tile traffic is separate.

## G — Validate performance and prepare submission

Priority: Normal. Dependencies: B, C, D, E, F.

Benchmark cold/warm latency, ORM filtering/query counts and query plans, SQLite
locking, matching/optimization, memory, payloads, and external calls. Run uv tests
and Ruff. Document SQLite setup and migrations for future implementation, validated
CSV import, resumable enrichment, credentials, and reproducibility. Explain
price-only reimports/coordinate reuse, transaction boundaries, shared revisions,
worker cache consistency, minimum-price ambiguity, initial-tank cost, coverage,
and detours. Prepare GitHub submission and a maximum-five-minute Loom.
Do not implement live updates, station CRUD/admin UI, or additional infrastructure.

## Completion criteria

Each issue is complete only when its scoped behavior and relevant tests satisfy
the criteria below. Creating backlog issues does not authorize their implementation.

| Issue | Acceptance criteria |
| --- | --- |
| A | Sample contains 30 distinct US IDs with category rationale/provenance; five-station pilot is reviewed before continuing and at least ten matches are manually inspected. Results classify precision/identity, record usage, and recommend acceptance rules. Diagnostic runner has safe resume/key redaction and a 40-attempt cap; no live calls before approval. No production schema/migrations or full API in the spike. |
| B | Unique OPIS records, coordinate/price checks and coordinate indexes are defined. Whole-file validation precedes transactional bulk upsert/revision writes; rollback and idempotence are tested. Status-based enrichment resumes, HTTP stays outside transactions, and stale-input results are rejected. Price-only imports preserve coordinates without geocoding; location changes invalidate them. Full-snapshot deactivation is explicit. No CRUD/admin UI or extra infrastructure. |
| C | Only endpoint strings are accepted; ambiguity, US validation and provider failures are tested. Successful uncached baseline uses at most two geocoding calls and one routing call. No transaction spans HTTP. Route caches are price-independent; fuel-plan cache contract includes persisted revision and planning parameters. |
| D | ORM bounding-box filtering uses coordinate indexes and projects only needed columns. Query-count tests rule out N+1 behavior; inactive/unaccepted/stale-enrichment records are excluded. Revision/candidates are read consistently, then pure Python matching runs outside the transaction. Corridor/loops/distances/coverage are tested; query plans and actual performance are measured. |
| E | Pure Python optimizer is independent of Django, HTTP and storage. Full 50-gallon tank, 10 MPG and no ending reserve are enforced. Purchase cost excludes initial-tank cost; consumed/purchased gallons and fuel conservation are verified. Tests cover partial fills, ties, exact range limits and coverage gaps; small cases are checked against an optimality oracle. |
| F | Response includes GeoJSON, stop data, fuel totals, dataset revision, approximations and working attributed Leaflet map_url. ORM integration and revision-aware plan caching are tested; response revision matches candidate snapshot and all workers consult the shared revision. Geometry is reused; baseline call target is preserved. No frontend app or station CRUD/admin UI. |
| G | Representative benchmarks measure ORM query counts/plans, SQLite locking, local processing, memory and provider calls. Tests/Ruff pass or unrelated existing failures are documented. Import/enrichment, transaction and revision semantics, setup and assumptions are documented. GitHub and maximum-five-minute Loom are prepared; no speculative infrastructure/features. |

## Indicative schedule

Day one: spike and findings review, then approved dataset/provider work. Day two:
matching and optimization. Day three: integration, validation, documentation, and
demo. This is not a promise of full-country enrichment within the deadline: quota
and station match quality must be assessed first.

## ORM + SQLite reconciliation

The prior enriched-CSV runtime architecture is superseded. Source CSV remains
immutable seed data; production import/enrichment state lives in SQLite.
A's small diagnostic file checkpoint does not contradict production persistence.
No new issues or dependency changes are required: A first and findings review;
then B and C, with E's pure algorithm after A; D after B/C; F after C/D/E; G last.
Existing issue statuses, priorities, assignees, and relations are preserved.
This reconciliation authorizes documentation/ticket changes only: no application
functionality, migration execution, or live Geoapify requests in the current task.
