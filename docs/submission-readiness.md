# Submission readiness review

Reviewed on 2026-10-09. No Loom recorded, assessment submitted, new live Geoapify
request made, or additional station enrichment performed during this review.

## Original assignment compliance

| Original requirement | Classification | Evidence and limits |
| --- | --- | --- |
| API accepts start/finish within the USA | Partially satisfied | DRF accepts only two strings and validates confident US endpoint results. Contiguous states only; Alaska/Hawaii are excluded. Arbitrary refueling routes are not generally feasible with current station coverage. |
| Return a route map and cost-effective fueling locations | Partially satisfied | Actual cold Albuquerque–Nashville request and rendered Leaflet map show four real purchases. Six reconciled candidates support this corridor, not arbitrary US routes or nationwide cost optimization. |
| Maximum range 500 miles, potentially multiple fuel-ups | Fully satisfied within the approved model | 50-gallon capacity, starting full, 10 MPG, partial fills and zero reserve. Four live purchases; largest purchase leg 350.979690 miles. Infeasible coverage returns 422. Station-access detours are excluded. |
| Total fuel expenditure at 10 MPG | Fully satisfied within the approved interpretation | Decimal conservation and independent small-case optimality tests; live $232.44, 122.163006 consumed / 72.163006 purchased. Unknown initial-tank cost excluded, as approved. |
| Use supplied fuel-price list | Fully satisfied | Immutable original CSV; 6,626 unique US OPIS stations imported. All six real-demo prices retain source values. Lowest conflicting price selected; min/max and provenance preserved. Prices are historic, not live. |
| Find a free map/routing API | Fully satisfied for assessment usage | Geoapify adapter and approved live verification; Leaflet/attributed OSM tiles. An individual Geoapify key and quota are required; unlimited free usage is not claimed. |
| Latest stable Django | Partially verified | Locked and tested Django 6.1.2 / Python 3.13.16. No package-index release-status audit performed in this delivery review, so current latest-stable status is not independently established. |
| Deliver within three days | Unsatisfied at this checkpoint | Submission not authorized or performed. Receipt timestamp/deadline is not recorded here; elapsed compliance cannot be verified. |
| Return quickly | Fully satisfied as a measured assessment result | Cold real request 4.522191 s, including 4.3668 s provider HTTP. Saved-reply fresh-server run 0.101339 s. Larger synthetic workloads documented separately; no general latency SLA claimed. |
| Ideally one, acceptably two or three provider calls | Fully satisfied | Cold live request: two endpoint geocodes + one driving route, all 200, no retries. Mocked warm-repeat tests make zero provider calls. No runtime station enrichment or per-stop routing. Browser assets/tiles are separate. |
| Postman-style Loom, at most five minutes | Unsatisfied pending approval | Postman instructions and 4:45 script prepared. Recording deliberately not performed. |
| Share GitHub code | Partially satisfied | Feature branch published to private repository. Reviewer identity/access and actual submission remain pending; a URL alone does not grant access. |

"Fully satisfied" in the model rows does not override the partial overall route/
coverage requirement. Only **6 / 6,626 (approximately 0.09%)** station records have
reviewed coordinates; **6,620** remain unresolved. A short route can require no
purchase, but that does not establish arbitrary-route station coverage.

## External interviewer review

- Reproducibility: committed lockfile, both migrations, original CSV and reviewed
  six-record coordinate artifact suffice for an empty database. README gives install,
  migrate, source import, reviewed dry run/import, server, Postman and curl commands.
  The isolated fresh-checkout running-server verification replayed recorded real
  provider replies; it did not use the owner's database, .env or another live budget.
  The isolated regression provides the same reproducible plan without credentials.
- Separation: serializers/views, Geoapify adapter, projected ORM repository,
  pure geometry and Decimal optimizer have distinct boundaries. External HTTP is
  outside transactions. Seed preparation is separate from request-time planning.
- Consistency: atomic imports, unique OPIS IDs, checks/indexes, price-independent
  fingerprints, dataset revisions, idempotent coordinate import and worker-cache
  tests demonstrate deliberate ORM use. No unnecessary infrastructure is added.
- Evidence: 148 tests, lint, relevant formatting, Django and migration-drift checks
  pass. Actual live response, sanitized request ledger, browser checks and screenshots
  are published as evidence, not offered as an always-live hosted API.
- Artifacts: recorded responses contain public business/route data; screenshots
  show only the map/application, attribution and public station information.
  Local loopback URLs are intentionally retained as historical evidence and expire.
  No credentials, personal filesystem paths, local DB, caches, browser profiles or
  downloaded raw datasets belong in the milestone. Historical reports/initial 404
  evidence remain labeled rather than discarded or presented as current failures.
- Limits: README states fixed snapshot/minimum-price ambiguity, unknown initial
  tank cost, unverified access/detours, interpolated chainage, process-local caches,
  expiring single-machine map snapshots, development settings and tiny fills.
- Performance: indexed SQLite query plan and two-SELECT bound are evidenced;
  synthetic workload memory/timings are labeled. Production concurrency and SQLite
  lock-contention behavior have not been stress-tested. No deployment-readiness claim.

## Scoped issue completion

GNS-8's accepted criteria concern indexed projected filtering, eligibility, snapshots,
pure matching, query counts and measured geometry/performance. GNS-10 concerns the
contract, integration, revision-aware caching and real attributed map. Those are met
for the reviewed corridor and tested failure cases. Their existing criteria explicitly
require disclosing inadequate coverage; neither requires resolving all source stations.
Completion therefore does **not** waive or satisfy nationwide assignment functionality.
The configurable one-mile default is supported only by the six-site sensitivity check;
no nationwide accuracy/access calibration is claimed. Supersede old pending live/map
notes with links to final evidence, without deleting their historical findings.

GNS-11 remains In Progress: review/script prepared, but reviewer access, recording,
final submission authorization and the deadline need resolution. Its SQLite locking
benchmark criterion is not yet evidenced; any waiver or bounded measurement should
be explicit before declaring it complete. GNS-12 remains optional/nonblocking and
unexecuted. Existing implementation dependencies need no additions/removals.

## Recommended submission plan

Submit the demonstrated implementation with an explicit prominent coverage limitation
once access and Loom are approved. It is a credible backend/algorithm demonstration,
but an incomplete answer to arbitrary-US fuel routing. Do not label it nationwide
ready; if that requirement is a strict assessment gate, seek the reviewer's acceptance
of the limitation before claiming completion.

Do not spend the remaining deadline on enrichment by default: five-station experiments
failed unattended identity resolution, and a few additional sites cannot establish
nationwide coverage. If the reviewer explicitly requires another demonstration corridor,
propose at most 60 minutes of identity review targeting that named route, with a stop
condition when evidence is inadequate. This is a future option, not authorization for
searches, downloads, imports or provider calls. GNS-12 does not block delivery.

Before recording: confirm intended reviewer GitHub identity and grant only approved
access; settle the exact deadline; authorize recording and choose live versus clearly
labeled recorded-response presentation. A new cold live demonstration needs separate
approval for at most three Geoapify attempts; the previous budget is exhausted. Do
not show .env or credential-bearing HTTP URLs. Rehearse the draft below five minutes.
Before submission: get explicit authorization, share the feature-branch URL and Loom,
and disclose the partial assignment compliance above. Do not merge to main silently.
