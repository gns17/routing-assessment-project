# Spotter Routing Assessment

Django/DRF backend for a fixed-route fuel-purchasing model. `POST /api/route/`
accepts only `start` and `finish` strings; the response includes route GeoJSON,
recommended purchases, fuel totals, dataset revision, warnings and a minimal
Leaflet `map_url`. The tested implementation uses Django ORM + SQLite.

**Coverage limitation:** a fresh CSV import has 6,626 US stations with no coordinates.
The six-record [reviewed artifact](data/corridor-reviewed-coordinates.json) is approved
for **local development** and was imported into local SQLite (revision 2), leaving
6,620 stations unresolved. The recorded Albuquerque–Nashville route now passes the
actual DRF/ORM pipeline offline; other routes may still return explicit
`insufficient_station_coverage` errors. This is optimization among reviewed candidates,
not nationwide coverage. Synthetic fixtures remain isolated tests.

Geoapify station experiments are complete with a negative conclusion for
unattended nationwide enrichment. Further individual station searches are stopped.
Geoapify remains the endpoint geocoder/router. No new live provider requests or
OSM downloads have been made during core implementation.
The subsequent [approved corridor investigation](docs/corridor-investigation.md)
acquired a real 1,221.63-mile route and reviewed six station-site locations.
The approved [local import/offline milestone](docs/corridor-local-integration.md)
now validates the ORM-backed multi-stop API using saved responses. A fresh live
DRF request and browser rendering remain unverified.

## Setup and checks

Use Python 3.13 and `uv`. Dependencies are pinned by `uv.lock`.

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py import_fuel_prices --full-snapshot
# Reviewed six-station fixture for local development only:
uv run python manage.py import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed --dry-run
uv run python manage.py import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python manage.py runserver
```

Store `GEOAPIFY_API_KEY` in the untracked local `.env` or process environment.
Missing credentials produce a safe 503 response. Tests mock HTTP and require no
key. Do not commit `.env` or log request URLs containing credentials. Live API
execution in this project still requires explicit approval; setup, imports and
tests make no external requests. Optional settings: `DJANGO_SECRET_KEY` (stable
key for deployments), `STATION_CORRIDOR_MILES` (positive miles, provisional default
1). Current settings are for local development, with DEBUG enabled and local hosts.

## API and map

Request body: `{"start": "Albuquerque, NM", "finish": "Santa Fe, NM"}`.

Responses expose `route` (GeoJSON Feature), `distance_miles`, `duration_seconds`,
`fuel_stops`, `total_fuel_cost`, `gallons_consumed`, `gallons_purchased`,
`ending_gallons`, `initial_tank_cost` (null), `dataset_revision`, `corridor_miles`,
`coverage`, `mileage_method`, `warnings`, and `map_url`. Money/gallon quantities are decimal strings, with money
rounded only for display. Stop rows include OPIS identity, address, coordinates,
price, position/offset and purchases. Input errors return 400; unresolved or
ambiguous endpoints, missing routes and inadequate fuel coverage return 422;
provider/configuration failures return safe 502/503 errors without credentials.

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
artifact. Repeating unchanged records is idempotent. Add `--dry-run` to perform the same validation and report exact changes without
writes. This command neither searches for stations nor validates an identity claim
automatically. Do not import
fixtures as real station matches. No unattended nationwide enrichment is implemented.

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
- Only active, accepted coordinates matching current location fingerprints may
  enter planning. Proximity or chain agreement never proves station identity.
- Chainage uses local segment projection, validated provider step distances and
  interpolation within each step. Missing steps use a disclosed route-wide scaled
  geometry fallback. It is approximate; station-access detours and road access
  are unverified. The one-mile development corridor is configurable and uncalibrated.
- Endpoint resolution accepts confident, unambiguous contiguous-US results.
  Routes themselves may cross borders; no border-avoidance guarantee is claimed.
- No live prices, schedulers, CRUD/admin interface, PostgreSQL, PostGIS, Redis,
  Celery or nationwide geocoding is included.

See [architecture](docs/architecture.md), [plan](docs/plan.md),
[implementation evidence](docs/implementation-progress.md),
[validation review](docs/route-validation-review.md),
[proposed real demonstration](docs/real-data-demonstration-plan.md),
[station feasibility findings](docs/geocoding-feasibility.md), and
[original assignment](docs/assignment.md).
