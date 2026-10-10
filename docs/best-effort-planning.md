# Optional best-effort fuel scenarios

The endpoint now accepts an optional **JSON boolean** `allow_estimates`. It defaults
to false. The strict implementation, approved station records, optimizer and existing
response remain unchanged. Strict success wins even when the flag is true. Only
`insufficient_station_coverage` can invoke the separate best-effort layer.

Best effort returns **conditional purchasing scenarios**, not reachable fuel stops or
turn-by-turn instructions. `fuel_stops` is empty and `total_fuel_cost`/top-level
`gallons_purchased` are null. Numeric hypothetical results have distinct estimated/
modeled names; `fuel_feasibility` is always `unverified`. The source-location assumptions
must be checked before using quantities in real travel.

## Architecture and scope

- `routing/serializers.py`: strict boolean validation; no new endpoint location inputs.
- `routing/views.py`: route provider first, strict planner second, eligible fallback last.
  Provider/auth/validation/unrelated planner errors never trigger estimates. No extra
  provider request is made for fallback.
- `routing/fallback_data.py`: static, checksummed offline hints loaded once per worker;
  normalized city/state keys; format/provenance/duplicate/contradiction checks.
- `routing/management/commands/prepare_best_effort_locations.py`: reproducible Census
  preparation against the immutable CSV; no ORM reads/writes, geocoding or downloads.
- `routing/repository.py`: existing strict repository unchanged; best-effort repository
  reads active ORM identities/prices/approved coordinates into plain objects with the
  dataset revision in a short transaction. Two SELECTs, no model creation/N+1 queries.
- `routing/best_effort.py`: pure Python grouping, geometric filtering, conditional
  optimization, optional conservative-bound checks and response assembly. No models,
  HTTP or station writes. `routing/fuel.py` and `routing/planning.py` remain unchanged.
- `routing/templates/routing/map.html`: normal strict map preserved; conditional plans
  use quality-coded indicators, explicit warnings and safe text-only popups.

Station identities/prices and approved coordinates still live in SQLite. The JSON
file is a deployment snapshot of **hints**, not a replacement runtime station CSV or
additional persistence service. No migrations, station CRUD, live discovery, automatic
reload, geospatial infrastructure or new project dependency was introduced.

## Offline data: provenance, coverage and licensing

The approved source is the [2025 Census National Places Gazetteer](https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.2025.html).
The downloaded ZIP contains 32,350 places: **1,214,053 bytes compressed** and
**3,288,984 bytes uncompressed**. Names and representative internal points are used;
these are neither station points nor guaranteed downtown centroids. Census-produced
works are generally public domain in the US; retain [source-policy attribution](https://www2.census.gov/foia/ds_policies/ds027.pdf).
Census licensing applies to locality records only; future optional station estimates
must retain their own source terms.

Raw ZIP is outside Git. `data/best-effort-locations.json` contains only uniquely matched
CSV localities, source GEOIDs/names/methods, edition/license/source and seed checksums,
and a content-derived version. Exact source names are matched after ASCII case/
punctuation/whitespace normalization and documented Census suffix removal. No guessed
postal aliases, nearest town or inferred neighboring municipality is used. Duplicate
normalized locality keys are excluded instead of picking one by proximity.

Measured against the current fixed seed:

| Measurement | Count |
| --- | ---: |
| US OPIS records | 6,626 |
| Unique CSV city/state keys | 3,808 |
| Uniquely matched locality keys | **3,493** |
| OPIS records with locality association | **6,144 (92.73%)** |
| Ambiguous normalized locality keys excluded | 23 |
| States represented by matched hints | **47** |
| Records without usable hints/approved coordinates | **482** |
| Approved physical sites in development DB | **6** |
| Unreviewed physical-site estimates shipped | **0** |
| Locality-associated unresolved OPIS records | **6,138** |

**92.73% is locality-association coverage, not station-coordinate accuracy, reachable
fuel-network coverage or nationwide route feasibility.** Six verified sites plus the
3,493 locality hints produce 3,499 distinct hints; many OPIS rows share one area.
The currently approved contiguous-US provider scope is retained. Political-place
names differ from mailing localities (for example Athens/its consolidated government);
unsupported names and ambiguous municipalities remain missing rather than silently
aliased. Internal points can be many miles from a business or highway.

Reproduce the prepared snapshot from a previously approved/downloaded input:

```sh
uv run python manage.py prepare_best_effort_locations \
  /path/to/2025_Gaz_place_national.zip
```

The command fully validates the prepared temporary JSON before atomic replacement.
It never imports coordinates into SQLite. A malformed input leaves the old output
intact. Raw input is bounded to 10 MiB, uncompressed text 12 MiB. Every worker loads the
prepared snapshot once: **restart all workers after replacement**. No automatic reload
or runtime station updates are implemented. ORM price updates invalidate plans through
the dataset revision and do not require repeating locality preparation/geocoding.

An optional `--station-estimates reviewed-provisional-hints.json` input supports
`estimated_physical_station` records. It requires original OPIS ID/current location
fingerprint, valid coordinates, `identity_supported:true`, empty contradictions,
source URL/coordinate method/license, evidence and uncertainty metadata. Road-chainage/
access bounds need explicit bound evidence; null means unknown. This is trusted offline
provisional preparation, **not automatic identity verification**. A stale fingerprint
excludes the estimated point at runtime. No such physical records are shipped or
promoted into `Station.enrichment_status=accepted`; capability is tested with labeled
synthetic fixtures. The existing 26-site reviewed artifact remains pending import
approval and is not consumed as production coordinates by this feature.

## API contract

Use `Content-Type: application/json`. Strings/numbers/null are rejected for the flag.

Strict/default request:

```json
{"start":"Albuquerque, NM","finish":"Nashville, TN"}
```

The existing reviewed corridor still returns its original result:

```json
{
  "distance_miles":"1221.630055",
  "total_fuel_cost":"232.44",
  "gallons_consumed":"122.163006",
  "gallons_purchased":"72.163006",
  "dataset_revision":2,
  "coverage":{"scope":"reviewed_candidates_only","complete_csv_coverage":false}
}
```

Example snippets omit geometry/stops/map URL for space. **No new strict-mode marker
fields are added**; absent `planning_mode` means the unchanged strict response. The
same request with `allow_estimates:true` still returns that normal result.

When strict coverage fails, an opt-in success uses this distinct shape:

```json
{
  "planning_mode":"best_effort",
  "status":"estimated",
  "fuel_feasibility":"unverified",
  "fuel_stops":[],
  "total_fuel_cost":null,
  "gallons_purchased":null,
  "estimated_fuel_expenditure":"88.06",
  "conditional_scenario":{
    "mathematically_feasible_under_assumed_positions":true,
    "gallons_purchased":"30.000000",
    "ending_gallons":"0.000000",
    "uncertainty_check":{"status":"unknown"}
  }
}
```

**This $88.06 snippet comes from the synthetic road-geometry validation below; it is
not a live Ocala–Charlotte route, quote or guarantee.** Full examples are in
`data/best-effort-validation.json`.

A purchase scenario contains:

- `location_quality`: `verified_station_site`, `estimated_physical_station`, or
  `locality_approximation`.
- `assumed_point` with explicit representation text, separate from candidate station
  identities. Candidate stations contain their OPIS/name/original address/city/state/
  snapshot price, **never town-derived station latitude/longitude**.
- `candidate_stations`, `modeled_price_candidate_opis_id` and its original stored price.
- `assumed_route_miles`, reference-point offset, modeled gallons/arrival/departure,
  conditional purchase cost, provenance and uncertainty.
- `navigation_destination:false`. No scenario point is a turn-by-turn destination.

`approximate_fueling_areas` exposes the purchased area scenarios separately. An area
is one hypothetical opportunity with its associated stations, not a collection of
independent stops. Lowest associated CSV price is a clearly labeled hypothetical
choice; every alternative retains its own price/OPIS identity. A known approved site
always keeps its real coordinates and is never replaced by a town anchor.

Coverage reports global OPIS association counts by quality, route association counts
and unique hint counts separately. The default 10-mile area search corridor is the
radius for finding **reference-point hints**, not a town boundary, station-position
uncertainty bound or reachable access distance. Estimated/verified physical hints use
the existing station corridor. Coarse bounding boxes precede precise projection.
Locality reference points may be several miles from the route: a point up to the
configured 10-mile corridor can participate without establishing the station's
position or road access. Its `reference_point_offset_miles` is a geometric distance,
not driving detour mileage; the actual station may be farther away.
Repeated route intersections with the same locality yield one assumed area opportunity.

HTTP semantics:

| Situation | HTTP / result |
| --- | --- |
| Strict success, opt-in omitted/false/true |200, unchanged strict payload |
| Strict coverage insufficient, default/false |422, existing `insufficient_station_coverage` |
| Opt-in conditional scenario available |200, `best_effort`/`estimated`/`unverified` |
| Even assumed positions cannot bridge modeled range |422, `insufficient_best_effort_coverage` |
| Offline snapshot missing/invalid |500, `best_effort_data_unavailable` |
| Supplied meaningful uncertainty bounds fail |422, `uncertain_fuel_plan_rejected` |
| Invalid flag/input |400, no provider/fallback work |
| Provider/auth/unrelated failure |Original error; fallback not attempted |

Failures retain the existing structured `error` envelope; best-effort details expose
mode, coverage/uncertainty and unverified feasibility where applicable.200 means a
conditional mathematical scenario was constructed, **not additional verified routes**.

Missing/corrupt location data is a deployment failure, not a problem with the client's
valid request. Therefore it returns 500, preserving the structured error code and
unverified-feasibility details without exposing filesystem paths. 503 is reserved for
known temporary unavailability; there is no automatic recovery or justified retry
interval for this deployment snapshot. No `Retry-After` is supplied. This distinction
follows [HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.6).

## Fuel uncertainty, falsification and guarantees

The optimizer remains unchanged:50-gallon tank starting full,10 MPG,500-mile model
range,zero ending reserve,partial divisible fuel,no stop penalty. Initial tank cost
is unknown/excluded. No route-choice/global optimization, access detours, current
prices, road entrances, supply/grade/hours or exact unreviewed positioning is assumed
verified. Machine warnings explicitly cover conditional quantities, unknown positions,
unverified access/driving feasibility, historical prices and approximate chainage.

**Zero ending fuel is fragile under geographic uncertainty.** With no required reserve,
the cost model can deliberately arrive at the destination or an intermediate purchase
with zero modeled fuel. Any additional mileage, incorrect station position or access
detour can then create an actual deficit. The synthetic $88.06 example ends with zero
modeled gallons; it is not an operational fuel schedule. No reserve or stop penalty is
added: those would change the approved optimizer objective.

A locality's position/access error cannot be bounded by its distance from the route.
No safety margin or confidence percentage is fabricated. Such scenarios remain
`fuel_feasibility:unverified`, even if the nominal mathematical model passes 500 miles.
When explicit road-chainage and total-access bounds are provided, the separate layer
checks pessimistic arrival inventory, range, possible fixed-quantity tank overflow
and final inventory. Violations reject the scenario; even passing supplied bounds
never becomes a real-world driving guarantee. Unknown unused hints cannot suppress
a known violation at a purchased bounded point.

Tests reuse the observed town-only false-feasibility case: an apparently feasible
plan's purchases yield **−0.7568687 gallons at the reviewed Petro position**. The pure
reference-replay validator rejects it. Synthetic boundary tests likewise expose
negative intermediate inventory and range failures. The API cannot classify any
approximation as verified feasible: quantities reside in a conditional scenario,
actionable stops are empty, guaranteed totals are unset and navigation is disabled.
This separation is a structural safeguard; a warning alone does not repair bad data.

## Map

Normal strict markers/cost display are preserved. Best-effort views show green reviewed
site indicators, orange estimated physical indicators, and **hollow/dashed purple
locality reference indicators**, labeled NOT a station. A screen-sized circle is not
an invented geographic uncertainty radius. Conditional costs, quality, original
candidate identities/prices, provenance and warnings appear in summaries/popups.
No directions link or physical fuel-station pin is created for a locality.

All dynamic content uses Django `json_script` and DOM `textContent`; attribution
remains OpenStreetMap. Strict-only extra legend/warning elements are hidden.

## Validation, examples and performance

An isolated fresh SQLite database migrated and imported all 6,626 seed records. A
saved real Geoapify response exercised the actual DRF pipeline with no station
coordinates: strict returned 422, opt-in returned a conditional scenario. Importing
only the existing six approved records **into that temporary database** restored the
$232.44 strict result with opt-in true. No development database writes occurred.

Outside-corridor example: **explicitly synthetic 800-mile geometry** passing through
real Census localities Ocala, FL; Tifton, GA; Forsyth, GA; Gainesville, GA; Greenville, SC; Charlotte, NC.
It uses actual ORM CSV identities/prices; no synthetic station coordinates or verified
site claims. Strict returned 422; best effort 200 returned **$88.06**, 30 modeled purchased
and 80 consumed gallons, with two provisional areas:

| Area | Price-bearing candidate | Modeled gallons | Conditional cost |
| --- | ---: | ---: | ---: |
| Adel, GA |OPIS 70429 |15.519168 |$46.08 |
| Pelzer, SC |OPIS 70458 |14.480832 |$41.98 |

The route and 800-mile distance are test fixtures, not an actual driving corridor
measurement. They establish a working vertical slice beyond the reviewed corridor,
**not real-world feasibility or a live integration success**. Actual new routes need
separately approved live provider verification before demonstrating them as real.

Five recorded-route benchmark repetitions (12,071 segments, real seed/Census data,
mocked saved HTTP replies) measure roughly **0.30 s cold /0.08 s warm median API time**,
excluding live provider latency. Synthetic regional API example roughly 0.04 s. Cold
means cleared provider/plan caches; the static catalogue loads once per process.
Exact final measurements and response examples are recorded in the validation JSON.

Final verification: **223 tests passed**, Ruff lint and changed-file formatting passed,
Django system checks passed, and no migration drift was detected. The benchmark
process peaked at **118 MiB RSS**, including preparation/import/validation work.

Actual Chrome rendering with real Leaflet 1.9.4 passed for the synthetic regional
API response: route geometry, both endpoint indicators, both hollow locality
indicators, conditional $88.06 cost, uncertainty popups, warnings and attribution
were displayed. There were no precise station pins, console errors or network
errors. **20 approved OpenStreetMap tiles** loaded; encoded browser traffic totaled
526,317 bytes, including locally cached Leaflet assets. No Geoapify calls occurred.
This is browser rendering verification of a synthetic scenario, not a new live
driving-route verification. See `data/best-effort-browser-verification.json`.

The development database remains byte-for-byte unchanged: six accepted records,
6,620 pending records, dataset revision 2. The immutable seed, pure optimizer,
approved coordinate artifacts and submission/recording drafts remain unchanged.

Provider geocoding/routing caches are deliberately shared between modes: routing
geometry does not depend on station quality and sharing avoids duplicate external
calls. **Fuel-plan caches have distinct namespaces/mode keys**, plus ORM revision,
location-file content version, geometry/step mileage, search corridors and policy.
Map snapshots retain their own immutable payloads/versions. Tests prove an estimated
response cannot satisfy a later strict request and a price/hint-version change cannot
reuse an old scenario.

## Delivery recommendation and remaining gates

Include this feature only as an **opt-in provisional scenario**, with the strict
$232.44 corridor remaining the main demonstration. The feature meaningfully adds
area/price-comparison guidance; it does not close the assignment's arbitrary-US
verified-station coverage gap. Never advertise 6,144 verified/geocoded fuel sites.

Before presenting a new real-route demonstration, obtain approval for live provider
requests and verify that response; no such call was made here. Review the new API/map
contract and update README/Postman/Loom mentions explicitly after review. Existing
submission and recording drafts have been preserved. No commit or push is performed.

## Proposed final live verification (awaiting approval)

Use `POST /api/route/` with:

```json
{"start":"Atlanta, GA","finish":"Miami, FL","allow_estimates":true}
```

This is a real US driving corridor longer than 500 miles, outside the reviewed
Albuquerque–Nashville demonstration. A [distance reference](https://www.travelmath.com/drive-distance/from/Atlanta%2C%2BGA/to/Miami%2C%2BFL)
lists about 662 driving miles; the exact chosen route and distance must come from
the actual Geoapify response. No physical sites are approved in GA or FL in the
current database, so a route requiring fuel should fail strict coverage and exercise
fallback if locality hints can bridge the assumed range. Success is not promised.

Proposed authorization: **three Geoapify HTTP attempts total, no retries**—two
US-filtered endpoint geocodes and one two-waypoint driving route. No enrichment,
Places, route details, elevation or alternative-route calls. Estimate **six credits**,
with an **eight-credit conservative allowance**, based on approximately 1,065 km and
[Geoapify credit guidance](https://apidocs.geoapify.com/docs/routing/). Actual account
debit may not be exposed by responses. Replaying strict and opt-in requests in the
same worker may use existing caches; any unexpected cache miss must not exceed the
three-attempt global budget. Stop on unexpected errors; do not try another route.

Measure provider attempts/statuses/latency, total API latency, actual mileage source,
area offsets and ordering, OPIS price ownership, conditional inventory, warnings,
unknown uncertainty, revision and hint version. Compare a cached explicit strict
request against the estimated response: strict must fail honestly and best effort
must keep empty actionable stops, null guaranteed totals and unverified feasibility.
This would verify live fallback integration, not independently verify station sites
or real fuel-range feasibility. No live requests were made during the final review.

The next cohesive Git checkpoint should be **`feat: add opt-in conditional fuel
planning with offline locality hints`**, containing the feature source files, map,
31 fallback tests, prepared locality data, validation/browser artifacts and this
document. Keep earlier research/import-review artifacts and submission/Loom drafts
separate. Review and stage explicit paths; exclude `.env`, SQLite databases, raw ZIP,
browser profiles, caches and temporary outputs. Commit/push await approval.
