# Submission readiness review

Delivery review updated on 2026-10-10. No Loom recorded, assessment submitted, new live Geoapify
request made, or additional station enrichment performed during this review.

## Original assignment compliance

| Original requirement | Classification | Evidence and limits |
| --- | --- | --- |
| API accepts start/finish within the USA | Partially satisfied | DRF validates start/finish strings and an optional JSON boolean; confident contiguous-US endpoints are required. Contiguous states only; Alaska/Hawaii are excluded. Arbitrary refueling routes are not generally feasible with current station coverage. |
| Return a route map and cost-effective fueling locations | Partially satisfied | Actual cold Albuquerque–Nashville request and rendered Leaflet map show four real purchases. Six reconciled candidates support this corridor. The approved Atlanta–Miami opt-in scenario and hollow-area map are conditional guidance, not verified arbitrary-US refueling. |
| Maximum range 500 miles, potentially multiple fuel-ups | Fully satisfied within the approved model | 50-gallon capacity, starting full, 10 MPG, partial fills and zero reserve. Four live purchases; largest purchase leg 350.979690 miles. Infeasible coverage returns 422. Station-access detours are excluded. |
| Total fuel expenditure at 10 MPG | Fully satisfied within the approved interpretation | Decimal conservation and independent small-case optimality tests; live $232.44, 122.163006 consumed / 72.163006 purchased. Unknown initial-tank cost excluded, as approved. |
| Use supplied fuel-price list | Fully satisfied | Immutable original CSV; 6,626 unique US OPIS stations imported. All six real-demo prices retain source values. Lowest conflicting price selected; min/max and provenance preserved. Prices are historic, not live. |
| Find a free map/routing API | Fully satisfied for assessment usage | Geoapify adapter and approved live verification; Leaflet/attributed OSM tiles. An individual Geoapify key and quota are required; unlimited free usage is not claimed. |
| Latest stable Django | Fully satisfied | Locked and tested Django 6.1.2 / Python 3.13.16. User supplied external verification that 6.1.2 is the latest stable release as of October 9, 2026; no new release lookup required. |
| Deliver within three days | Unsatisfied at this checkpoint | Submission not performed. User confirmed the deadline: October 11, 2026, 16:55 GMT−3 (19:55 UTC). Original receipt timestamp remains unavailable; do not claim submission occurred. |
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
- Evidence: 212 committed tests (224 with pending unrelated research), lint, relevant formatting, Django and migration-drift checks
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

GNS-11 remains In Progress for delivery gates: reviewer access, recording/link and
final submission authorization are pending. The deadline is confirmed as October 11,
2026, 16:55 GMT−3 (19:55 UTC).
All required local technical checks are complete. On October 9 the user explicitly
made SQLite write-contention benchmarking optional/nonblocking unless an actual
problem is identified. No such problem has been identified in the completed checks;
no stress-test result is claimed. The user also supplied external latest-stable
Django verification. These decisions supersede the earlier outstanding-check notes.
GNS-12 is Done: the bounded New Mexico audit demonstrated limited yield and no
benefit to the existing fuel plan. The user accepted no national expansion or
production-rule change before submission. Its five verified research sites are
not approved production imports; the database retains six accepted sites.
Existing implementation dependencies need no additions/removals.

## Recommended submission plan

Submit the demonstrated implementation with an explicit prominent coverage limitation
once access and Loom are approved. It is a credible backend/algorithm demonstration,
but an incomplete answer to arbitrary-US fuel routing. Do not label it nationwide
ready; if that requirement is a strict assessment gate, seek the reviewer's acceptance
of the limitation before claiming completion.

Further enrichment is deferred. The earlier possibility of another identity-reviewed
corridor is superseded by the approved opt-in fallback and delivery scope; no research
expansion is authorized. GNS-12 does not block delivery, and approximate guidance does
not upgrade arbitrary-US verified fueling to fully satisfied.

Before recording: confirm intended reviewer GitHub identity and grant only approved
access; use the confirmed deadline; authorize recording and choose live versus clearly
labeled recorded-response presentation. A new cold live demonstration needs separate
approval for at most three Geoapify attempts per route (six for both demonstrations);
all previous budgets are exhausted. Do
not show .env or credential-bearing HTTP URLs. Rehearse the draft below five minutes.
Before submission: get explicit authorization, share the feature-branch URL and Loom,
and disclose the partial assignment compliance above. Do not merge to main silently.

## Exact deadline and access check

The original assignment says “within 3 days of receiving the exercise.” Original
recruitment delivery headers/received timestamp are unavailable, but the user has
explicitly confirmed the deadline: **October 11, 2026, 16:55 GMT−3 (19:55 UTC)**.
Use that deadline; do not infer another one from Git commits or local timezone.

Read-only GitHub check: repository is private, active and not archived; its default
branch is main, but delivered implementation is on `feat/assessment-implementation`
at the final published delivery checkpoint (see Git history). Collaborator listing shows only owner `gns17` and
zero pending invitations. No intended reviewer identity is supplied. Reviewer access
is therefore not established; do not send a private URL assuming access. No visibility,
invitations or permissions were changed. Postman was not found at the standard
`/Applications/Postman.app` location; availability elsewhere is unconfirmed.

Use the [recording checklist](recording-checklist.md) and
[submission package](submission-package.md). No new application functionality is
needed. Deadline/access/tooling/approval gates are separate from optional benchmarking
and future coverage work.

Current final preparation checks: 212 committed tests (224 including pending unrelated
research), Ruff, relevant formatting, Django and migration-drift checks pass. The local
development DB remains 6,626 stations / six accepted / revision 2. The isolated fresh
HTTP reproduction checks both modes and both map pages with recorded-only provider
transport and no credential/dev-DB/research access. The earlier GET-405 startup check
was historical; current delivery evidence is in [delivery verification](delivery-verification.md).
No actual Postman desktop run or new live Geoapify request is claimed.

## Approved optional fallback and final publication

The fallback and live Atlanta–Miami verification are approved for inclusion. Strict
planning remains default and wins on success. Only verified-coverage insufficiency
can invoke opt-in conditional scenarios; provider/input failures never do. The live
663.900943-mile route has a $48.66 Adel-area scenario, but strict returns 422.
`fuel_feasibility:unverified`, `fuel_stops:[]`, null guaranteed totals and full source/
uncertainty warnings prevent treating this as verified station navigation.
6,138 locality associations are not station geocodes. Prices remain OPIS-specific;
no coordinate was imported and no optimizer objective changed.

The readable-popup presentation keeps API provenance intact. Final saved-response
regressions reconstruct both examples in isolated databases with the committed
locality snapshot, no development DB, no research-file dependency and no live HTTP.
The portable Postman collection covers strict success, strict failure and opt-in
success with contract/inventory checks. Its JavaScript assertions were evaluated
against saved responses without network calls; actual Postman desktop operation is
still a recording prerequisite, not claimed tested.

Reviewer access remains unconfirmed: read-only GitHub checks show private visibility
and owner-only collaborator listing. Postman desktop was not found in the standard
system/user application locations. No visibility/invitations were changed, no new
Geoapify calls made, and Loom/submission remain pending. SQLite write-contention work
remains optional/nonblocking. GNS-11 must stay In Progress through the delivery gates.
