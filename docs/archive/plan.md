# Approved delivery plan and Linear reconciliation

Project: [Spotter Routing API — Three-Day Assessment](https://linear.app/gns17/project/spotter-routing-api-three-day-assessment-23c93ff7abb6).

The latest approved priority is working, tested backend delivery. Station research
is not the critical path. The approved Django ORM + SQLite architecture remains.
Existing issue progress and relevant dependencies were preserved; no duplicate
application issues were created.

| Issue | Scope | Current status |
| --- | --- | --- |
| [GNS-5](https://linear.app/gns17/issue/GNS-5) A | Geoapify station feasibility | Done — negative conclusion |
| [GNS-7](https://linear.app/gns17/issue/GNS-7) C | Endpoint geocoding/routing/cache | Done — mocked and approved live evidence |
| [GNS-9](https://linear.app/gns17/issue/GNS-9) E | Pure fuel optimizer | Done — optimality tests |
| [GNS-6](https://linear.app/gns17/issue/GNS-6) B | SQLite schema/import/reviewed coordinate artifact | Done |
| [GNS-8](https://linear.app/gns17/issue/GNS-8) D | Repository and pure route matching | Done — explicit reviewed-subset scope |
| [GNS-10](https://linear.app/gns17/issue/GNS-10) F | DRF and minimal Leaflet vertical slice | Done — live/browser/fresh evidence; limited coverage |
| [GNS-11](https://linear.app/gns17/issue/GNS-11) G | Performance/submission | In Progress — technical checks complete, delivery gates pending |
| [GNS-12](https://linear.app/gns17/issue/GNS-12) H | Bounded offline New Mexico OSM feasibility | Done — limited yield, no expansion or production imports |

## Reconciled scope and dependencies

A was completed first. Five address-first requests and ten name-first/Places
requests produced only one corroborated identity among five stations. All actual
findings and candidates remain preserved. The unexecuted remaining sample and
manual-audit targets are explicitly superseded; they are not claimed fulfilled.
No further individual station searches or unattended nationwide Geoapify enrichment.

C and E no longer depend on A's enrichment success and were implemented first
using mocked HTTP and known test coordinates. B followed, preserving unresolved
station identities, prices, provenance and status with null coordinates. B remains
independent of H; its offline coordinate command accepts reviewed evidence rather
than implementing a failed automatic enrichment loop.

D retains B/C dependencies and F retains C/D/E. Their vertical slice can be tested
without real-coordinate coverage. G retains B/C/D/E/F. H has no outgoing blocking
dependency to application implementation. Synthetic coordinates are isolated tests,
never real source matches or demonstration substitutes.

## Acceptance and remaining evidence

- C: bounded start/finish strings; confident contiguous-US geocoding with ambiguity
  handling; normalized driving geometry; safe timeouts/errors; at most three HTTP
  attempts, no runtime station geocoding; price-independent endpoint/route caching.
- E: pure Python/Decimal, full 50 gallons, 10 MPG, partial purchases, no ending
  reserve; conservation, gap/tie/range cases and independent small-case oracle.
- B: unique OPIS IDs, price/coordinate/status constraints, indexes; whole-file
  validation and atomic bulk import/revision; idempotence, rollback, explicit
  full-snapshot deactivation, price-only coordinate reuse and location invalidation.
  Offline reviewed artifacts validate current identity/fingerprint/evidence and
  commit atomically without any HTTP; unchanged evidence can resume idempotently.
- D: accepted/current/active eligibility; two projected SELECTs, consistent revision
  and candidates; matching outside transactions; configurable corridor, loops,
  disconnected geometry and boundaries. Query plan/timings, representative labeled
  synthetic benchmarks and six-site corridor sensitivity are recorded. Default is
  justified only for the reviewed subset; no national calibration/access claim.
- F: route GeoJSON, genuine eligible stop identity, decimal fuel totals, revision,
  warnings and attributed map URL; mocked ORM-backed API/map integration; plan keys
  include shared revision, route, corridor and fuel policy. Approved live request,
  actual browser rendering and isolated fresh setup pass; unsupported coverage returns
  an explicit 422 rather than fake stops. Completion is not nationwide functionality.
- G: broaden measured workloads only where useful, record memory/payload/locking
  limitations, final tests/Ruff/docs, prepare GitHub and at-most-five-minute Loom.
  Publication/recording is not performed automatically.

## H — initially New Mexico only

Historical experiment proposal below. Completed under the later approved two-hour
cap: 107 OPIS records, 20-case audit, five verified research sites, no production
imports. The user accepted the [feasibility findings](osm-feasibility.md) and closed
GNS-12; no national expansion or production acceptance changes before submission.

Priority Medium. Start only after core implementation is underway; max 60–90 minutes
including setup/download/extraction/matching, target 60. Require approval before
any dataset download. Do not download Michigan, full-US extracts, or make paid calls.

Start with 10–15 geographically/address-diverse OPIS stations. Extract actual
`amenity=fuel` POIs from a Geofabrik New Mexico state extract, preserving OSM type/ID,
name, brand/operator, address tags and coordinates. Reconcile using identity,
branch, address/locality/state and documented aliases. Nearby stations and matching
chains alone are insufficient. Keep high-confidence/verified, ambiguous and rejected
candidates distinct, retaining evidence. Assign prices only to reconciled identities.

Measure matched CSV coverage and its denominator, unresolved/ambiguous counts,
time, peak memory and download size. Assess priced-network gaps versus 500-mile
range; coverage of one state's sample cannot establish national route feasibility.
Abort early if native dependencies, processing or identity evidence are costly.
Negative findings are valid. Michigan requires promising measurable results AND
new approval. Fallback: deliver the tested backend, disclose inadequate real coverage,
retain unresolved records and reject unsupported long trips. Do not substitute POIs.

## Implementation order

Completed: A investigation → C/E independent components → B schema/import.
Current: D/F complete with explicit scoped acceptance and live/browser/fresh evidence.
See [final verification](../final-verification.md), [submission readiness](submission-readiness.md)
and [reviewer setup](../../README.md). G's required local technical checks
are complete; the user verified latest-stable Django and explicitly made SQLite
write-contention benchmarking optional/nonblocking absent an actual problem.
Confirmed deadline: October 11, 2026, 16:55 GMT−3 (19:55 UTC).
Next: finalize submission documentation, Postman availability and reviewer access; obtain recording,
any new live-request budget and final submission approvals. No Loom or submission yet.
H is complete and nonblocking; do not run further research without new approval.
Additional live Geoapify requests, OSM downloads and nationwide enrichment are not
authorized. No architecture changes or additional infrastructure are planned.

## Final approved delivery scope

The approved opt-in best-effort fallback and live Atlanta–Miami evidence join the
strict reviewed-corridor demonstration. They do not change strict eligibility,
station coordinates, ORM architecture or the pure optimizer. Locality positions
support only explicitly conditional scenarios, never a nationwide fuel guarantee.
Remaining work is publication, reviewer access, Postman/under-five-minute Loom and
submission. No new enrichment, live requests, infrastructure or scope expansion.
See [best-effort live verification](../best-effort-live-verification.md) and
[Postman collection instructions](../postman/README.md). GNS-11 remains In Progress.
