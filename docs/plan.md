# Approved delivery plan and Linear reconciliation

Project: [Spotter Routing API — Three-Day Assessment](https://linear.app/gns17/project/spotter-routing-api-three-day-assessment-23c93ff7abb6).

The latest approved priority is working, tested backend delivery. Station research
is not the critical path. The approved Django ORM + SQLite architecture remains.
Existing issue progress and relevant dependencies were preserved; no duplicate
application issues were created.

| Issue | Scope | Current status |
| --- | --- | --- |
| [GNS-5](https://linear.app/gns17/issue/GNS-5) A | Geoapify station feasibility | Done — negative conclusion |
| [GNS-7](https://linear.app/gns17/issue/GNS-7) C | Endpoint geocoding/routing/cache | Done — mocked tests |
| [GNS-9](https://linear.app/gns17/issue/GNS-9) E | Pure fuel optimizer | Done — optimality tests |
| [GNS-6](https://linear.app/gns17/issue/GNS-6) B | SQLite schema/import/reviewed coordinate artifact | Done |
| [GNS-8](https://linear.app/gns17/issue/GNS-8) D | Repository and pure route matching | In Progress — calibration/performance review remains |
| [GNS-10](https://linear.app/gns17/issue/GNS-10) F | DRF and minimal Leaflet vertical slice | In Progress — implemented, final review pending |
| [GNS-11](https://linear.app/gns17/issue/GNS-11) G | Performance/submission | Backlog |
| [GNS-12](https://linear.app/gns17/issue/GNS-12) H | Bounded offline New Mexico OSM feasibility | Backlog — nonblocking, download unapproved |

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
  disconnected geometry and boundaries. Initial query plan/timings are recorded,
  but real accuracy, representative performance and operational corridor calibration
  remain pending. No coverage claim follows from synthetic tests.
- F: route GeoJSON, genuine eligible stop identity, decimal fuel totals, revision,
  warnings and attributed map URL; mocked ORM-backed API/map integration; plan keys
  include shared revision, route, corridor and fuel policy. Final integration review
  remains pending; unsupported coverage returns an explicit 422 rather than fake stops.
- G: broaden measured workloads only where useful, record memory/payload/locking
  limitations, final tests/Ruff/docs, prepare GitHub and at-most-five-minute Loom.
  Publication/recording is not performed automatically.

## H — initially New Mexico only

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
Current: D/F local validation fixes/tests/benchmarks complete; real-data accuracy
calibration and map/provider demonstration remain unverified. See
[validation review](route-validation-review.md) and the proposed
[bounded corridor demonstration](real-data-demonstration-plan.md). No Linear scope
or completion status is changed by this proposal. Next: approve the demonstration
strategy, then close remaining D/F gates and finish G delivery validation.
H can run only within its time cap after download approval and never blocks delivery.
Additional live Geoapify requests, OSM downloads and nationwide enrichment are not
authorized. No architecture changes or additional infrastructure are planned.
