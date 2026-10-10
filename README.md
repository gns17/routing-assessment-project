# Spotter Routing Assessment

Django/DRF backend for a fixed-route fuel-purchasing model. `POST /api/route/`
accepts `start` and `finish` strings plus an optional JSON boolean `allow_estimates`.
The response includes route GeoJSON,
recommended purchases, fuel totals, dataset revision, warnings and a minimal
Leaflet `map_url`. The tested implementation uses Django ORM + SQLite.

**Coverage limitation:** a fresh CSV import has 6,626 US stations with no coordinates.
The six-record [reviewed artifact](data/corridor-reviewed-coordinates.json) is approved
for **local development** and was imported into local SQLite (revision 2), leaving
6,620 stations unresolved. The recorded Albuquerque–Nashville route now passes the
actual DRF/ORM pipeline offline; other routes may still return explicit
`insufficient_station_coverage` errors. This is optimization among reviewed candidates,
not nationwide coverage. Synthetic fixtures remain isolated tests.

**Optional best effort:** when strict coverage is insufficient, `allow_estimates:true`
can return a **conditional mathematical purchasing scenario**, never verified fuel
stops or driving instructions. The approved Atlanta–Miami live example covers
663.90 driving miles and models $48.66 in the Adel, GA area. Strict mode returns 422;
best effort returns 200 with `fuel_feasibility:"unverified"`, `fuel_stops:[]` and
`total_fuel_cost:null`. The committed Census snapshot associates 6,138 unresolved
OPIS records with locality anchors across 47 states; these are **not precisely
geocoded stations or nationwide reachable fuel coverage**. No estimated physical
station records are supplied. Default strict behavior remains unchanged.

Geoapify station experiments are complete with a negative conclusion for
unattended nationwide enrichment. Further individual station searches are stopped.
Geoapify remains the endpoint geocoder/router. The two approved driving-route
demonstrations used bounded live requests; ordinary
tests/reproduction use recorded replies and require no network discovery.
The subsequent [approved corridor investigation](docs/corridor-investigation.md)
acquired a real 1,221.63-mile route and reviewed six station-site locations.
The approved [local import/offline milestone](docs/corridor-local-integration.md)
now validates the ORM-backed multi-stop API using saved responses. The [final verification](docs/final-verification.md) also passed a cold live DRF
request and actual Chrome/Leaflet rendering. The three-request live budget is
exhausted; tests and recorded-response replay need no additional provider calls.

## Setup and checks

Use Python 3.13 and `uv`. Dependencies are pinned by `uv.lock`.

```sh
uv sync --locked
uv run python manage.py migrate
uv run python manage.py import_fuel_prices --full-snapshot
# Reviewed six-station fixture for local development only:
uv run python manage.py import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed --dry-run
uv run python manage.py import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed
uv run pytest
uv run ruff check .
uv run ruff format --check routing tests spikes config/settings.py config/urls.py
uv run python manage.py runserver
```

Store `GEOAPIFY_API_KEY` in the untracked local `.env` or process environment.
Missing credentials produce a safe 503 response. Tests mock HTTP and require no
key. Do not commit `.env` or log request URLs containing credentials. Live API
execution in this project still requires explicit approval; setup, imports and
tests make no external requests. Optional settings: `DJANGO_SECRET_KEY` (stable
key for deployments), `STATION_CORRIDOR_MILES` (positive miles, provisional default
1). Current settings are for local development, with DEBUG enabled and local hosts.

## Reproduce the reviewed corridor from a fresh checkout

No local database, .env or virtual environment is supplied. Run the setup commands
above: install locked dependencies, apply migrations, import the original CSV, dry-run
and import the reviewed six-record artifact. This creates 6,626 stations, six accepted
coordinates and dataset revision 2 entirely from committed source data.

Copy `.env.example` to `.env` and set `GEOAPIFY_API_KEY` to **your own Geoapify key**
for live use. Start Django and, from another terminal, request:

```sh
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H 'Content-Type: application/json' \
  -d '{"start":"Albuquerque, NM","finish":"Nashville, TN"}'
```

The verified snapshot returns approximately 1,221.63 miles, six matched stations,
four purchases, 72.163006 gallons purchased and $232.44 purchase expenditure.
Provider data may change; exact reproducibility without a key or live calls is
available through `uv run pytest tests/test_recorded_corridor.py tests/test_recorded_best_effort.py -q`. These regressions
build isolated SQLite databases from the committed CSV/coordinate artifact and
use the saved real provider responses. They never use the existing development DB.
The fresh running-server check used this same recorded-response approach; only the
separately documented final live request consumed new Geoapify calls.

Open the returned `map_url` to view actual Leaflet geometry/stops. Leaflet static
assets and OSM tiles need browser internet access, independent of backend provider
calls. Two nearby Amarillo markers overlap at the continent overview; zoom in or
open their popups to inspect each purchase. Do not present recorded replies as a new
live provider run. Agent workflows retain the explicit external-request approvals
in AGENTS.md; no additional live calls were made for fresh-database testing.

## API and map

Demonstration request: `{"start": "Albuquerque, NM", "finish": "Nashville, TN"}`.

Responses expose `route` (GeoJSON Feature), `distance_miles`, `duration_seconds`,
`fuel_stops`, `total_fuel_cost`, `gallons_consumed`, `gallons_purchased`,
`ending_gallons`, `initial_tank_cost` (null), `dataset_revision`, `corridor_miles`,
`coverage`, `mileage_method`, `warnings`, and `map_url`. Money/gallon quantities are decimal strings, with money
rounded only for display. Stop rows include OPIS identity, address, coordinates,
price, position/offset and purchases. The strict response does not add a planning-mode
field, preserving existing consumers. Input errors return 400; unresolved or
ambiguous endpoints, missing routes and inadequate fuel coverage return 422;
provider/configuration failures return safe 502/503 errors without credentials. A
missing/corrupt server-side locality snapshot returns structured HTTP 500
`best_effort_data_unavailable`; insufficient hypothetical coverage or rejected
uncertainty returns 422, never a fabricated success.

Import [the portable Postman collection](docs/postman/spotter-routing.postman_collection.json),
set collection variable `base_url` to `http://127.0.0.1:8000`, and start Django locally.
The collection contains strict reviewed-corridor success, strict Atlanta–Miami failure,
and opt-in Atlanta–Miami success. No API key belongs in Postman: only the backend
reads your local environment. Request assertions check status, identities/prices,
inventory, conditional semantics and uncertainty. Precise saved-snapshot assertions
are opt-in through `assert_recorded_snapshot=true`; fresh provider geometry may vary.
See [Postman instructions](docs/postman/README.md).

After a 200 response open its newly returned `map_url`. Strict maps show reviewed
station sites; best-effort maps show hollow locality indicators, clear source/method
labels and uncertainty. Town reference points are not fuel-station entrances or
navigation destinations. Maps expire after one hour or eviction; historical local
URLs are not hosted maps. See the [4:45 walkthrough](docs/loom-walkthrough.md).

Selected fields from the verified response (not the complete response schema):

```json
{
  "distance_miles": "1221.630055",
  "total_fuel_cost": "232.44",
  "gallons_consumed": "122.163006",
  "gallons_purchased": "72.163006",
  "ending_gallons": "0.000000",
  "initial_tank_cost": null,
  "dataset_revision": 2,
  "coverage": {
    "scope": "reviewed_candidates_only",
    "complete_csv_coverage": false,
    "eligible_candidates": 6,
    "matched_stations": 6,
    "route_visits": 6,
    "largest_gap_miles": "350.879358",
    "unbridgeable_gaps": []
  }
}
```

The [complete recorded live response](data/final-live-api-response.json) also
contains full GeoJSON, four purchases, inventory, warnings and an expired map URL.
Arbitrary US trips requiring refueling are **not generally supported** by six
reviewed stations; 422 is an honest failure, not fulfillment of nationwide routing.
Alaska/Hawaii endpoints are excluded by the contiguous-US provider policy.

### Best-effort request and observed live result

```json
{"start":"Atlanta, GA","finish":"Miami, FL","allow_estimates":true}
```

Selected fields from the **real live** response (full geometry/contracts are retained
in [the complete saved response](data/best-effort-live-api-response.json)):

```json
{
  "planning_mode":"best_effort",
  "status":"estimated",
  "fuel_feasibility":"unverified",
  "distance_miles":"663.900943",
  "fuel_stops":[],
  "total_fuel_cost":null,
  "gallons_purchased":null,
  "estimated_fuel_expenditure":"48.66",
  "gallons_consumed":"66.390094",
  "conditional_scenario":{
    "gallons_purchased":"16.390094",
    "ending_gallons":"0.000000"
  }
}
```

This abbreviated snippet is not a replacement for the full response. The scenario
models 16.390094 gallons in the **Adel, GA area**, using OPIS 70429's original
$2.969/gallon price. It matches 43 locality hints associated with 102 CSV records;
no reviewed station site is established on this route. Each area exposes candidate
identities/prices, location quality, Census provenance, null uncertainty bounds,
assumed position, conditional quantities and `navigation_destination:false`.
The same route in strict mode returns `422 insufficient_station_coverage`.

Strict planning is always attempted first, even with opt-in true. Fallback runs only
for insufficient verified coverage, never input/auth/provider/unrelated errors.
Zero modeled ending fuel is fragile: incorrect positions, unknown access detours or
extra miles can cause a real deficit. The 10-mile reference-point search corridor is
not an access or uncertainty bound. No guaranteed totals or driving feasibility are
claimed, and town-derived coordinates are never assigned to station records.
[Contract and preparation](docs/best-effort-planning.md) and
[live/browser evidence](docs/best-effort-live-verification.md) explain all limitations.
The older **$88.06 example is synthetic geometry**, not this live route/result.

The offline locality snapshot is committed: fresh setup needs **no Gazetteer download,
locality import into SQLite or request-time discovery**. Workers load it once;
restart all workers after deliberately replacing it. It derives from the public-domain
US Census 2025 Places Gazetteer and preserves source/edition/checksum metadata.
For credential-free reproduction run the two recorded regression tests above;
they create isolated ORM data and replay committed original provider payloads.

An uncached successful baseline makes at most two endpoint geocoding calls and
one routing call, without retries. Endpoint caches last 24 hours, route and plan
caches one hour. Prices invalidate fuel plans through the shared SQLite revision,
not route geometry. No station geocoding, per-stop route request or matrix call
occurs at runtime. Infeasible responses include coverage counts/unbridgeable mile intervals and
the snapshot revision, without fabricated costs or a partial success map.

The minimal map reuses returned geometry and stops. Map snapshots expire after
one hour (or cache eviction), using Django's file cache in ignored `.cache/maps`
so local workers share map URLs. Route/plan caches remain process-local. Leaflet
assets and attributed OpenStreetMap tiles load in the browser; their requests are
separate from backend provider calls. Multi-host map sharing and a frontend
application are outside scope.

## Dataset preparation

The supplied `data/fuel-prices.csv` is immutable seed data. Ingestion validates the
entire file before one transaction, deduplicates by OPIS ID, chooses the lowest
listed price, and preserves aliases, min/max, distinct source prices, source rows
and checksum. There are 8,151 rows, including 620 Canadian rows excluded from the
US repository. Unchanged imports are idempotent. Only explicit `--full-snapshot`
imports deactivate missing IDs; partial imports do not. Use one preparation writer.

Price-only imports preserve accepted coordinates. Location fingerprints exclude
prices, source-row positions, timestamps and source checksum. Changed location
inputs invalidate coordinates. Database checks enforce price validity, paired
coordinates and accepted/current enrichment; coordinate indexes support filtering.

`import_station_coordinates path.json --reviewed` imports only a manually reviewed
JSON list. Each entry requires `opis_id`, `location_fingerprint`, `latitude`,
`longitude`, `policy`, `identity_verified: true`, `source`, and `evidence`.
Explicitly synthetic, unknown, inactive, invalid or stale records reject the whole
artifact. Repeating unchanged records is idempotent. Add `--dry-run` to perform
the same validation and report exact changes without writes. This command neither searches for stations nor validates an identity claim
automatically. Do not import synthetic fixtures as real station matches. No unattended nationwide enrichment is implemented.

## Assumptions and limits

- A full 50-US-gallon starting tank, 10 MPG, 500-mile range, partial purchases and
  no ending reserve. `total_fuel_cost` is purchases during the trip; the unknown
  initial tank cost is excluded. A short trip can consume fuel with zero purchases.
- Prices are assumed USD per US gallon for compatible fuel. The CSV does not
  establish fuel grade, observation date or current availability. Minimum price
  selection is optimistic when duplicate records disagree.
- The current corridor includes a 0.212-gallon purchase under the zero-stop-penalty
  model. Minimum fills and operational stop costs are not modeled; the small
  purchase can be impractical despite reducing modeled fuel expenditure.
- Optimization is mathematically optimal within the supplied fixed-route model,
  with divisible fuel, unlimited supply and no stop penalties. It does not choose
  the cheapest route across the road network.
- Only active, accepted coordinates matching current fingerprints enter **strict**
  planning. Optional hints enter a separate conditional scenario layer and never
  promote records to verified. Proximity or chain agreement never proves identity.
- Chainage uses local segment projection, validated provider step distances and
  interpolation within each step. Missing steps use a disclosed route-wide scaled
  geometry fallback. It is approximate; station-access detours and road access
  are unverified. The configurable one-mile assessment corridor is conservative
  for the reviewed subset: all six offsets are below 0.25 mile, while a 0.1-mile
  corridor makes the route infeasible. This is not nationwide accuracy calibration.
- Endpoint resolution accepts confident, unambiguous contiguous-US results.
  Routes themselves may cross borders; no border-avoidance guarantee is claimed.
- No live prices, schedulers, CRUD/admin interface, PostgreSQL, PostGIS, Redis,
  Celery or nationwide geocoding is included.

## Implementation overview

DRF serializers validate the two strings and opt-in boolean; the Geoapify adapter
resolves endpoints
and normalizes a driving route before any station read transaction. SQLite models
preserve OPIS identity, source-price ambiguity, location fingerprints and enrichment
provenance. Management commands validate input before short atomic writes and
increment the shared dataset revision only for actual changes.

The station repository reads revision and projected, indexed bounding-box candidates
in one short consistent transaction (two SELECTs). Pure Python segment matching
computes corridor offsets and cumulative route miles outside that transaction.
The Decimal fuel optimizer buys partial quantities based on the next cheaper reachable
station, independently of Django models or provider HTTP. Revision-keyed plan caches
avoid mixing station snapshots; route caches are independent of price changes.
Best-effort plan caches use a separate namespace and include revision, hint content
version and matching policy. The optimizer is unchanged; offline location hints
remain separate from ORM station identity/pricing and strict eligibility.

See [delivery readiness and assignment compliance](docs/submission-readiness.md),
[final delivery verification](docs/delivery-verification.md),
[recording checklist](docs/recording-checklist.md),
[draft submission package](docs/submission-package.md),
[architecture](docs/architecture.md), [plan](docs/plan.md),
[implementation evidence](docs/implementation-progress.md),
[validation review](docs/route-validation-review.md),
[proposed real demonstration](docs/real-data-demonstration-plan.md),
[station feasibility findings](docs/geocoding-feasibility.md), and
[original assignment](docs/assignment.md).
