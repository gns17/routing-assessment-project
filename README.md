# Spotter fuel-routing assessment

A Django REST Framework API that retrieves a US driving route and optimizes fuel
purchases using the supplied OPIS price snapshot. It uses **Python 3.13, Django 6.1.2,
Django ORM + SQLite**, a pure Python matcher/optimizer and a minimal Leaflet map.

**Coverage:** strict planning has six independently reviewed station sites, supporting
Albuquerque–Nashville. Optional best effort models approximate fueling areas; it does
**not** establish reachable stations or driving feasibility. Neither mode claims
nationwide station coverage or road-network-global optimality.

[Setup](#setup) · [API examples](#api-examples) · [Tests and Postman](#tests-and-postman) ·
[Architecture and assumptions](#architecture-and-assumptions) · [Evidence](#evidence)

## Setup

Use `uv` and run these commands from the repository root:

```sh
uv sync --locked
cp .env.example .env
# Edit .env locally: set GEOAPIFY_API_KEY to your own key. Never commit it.
uv run python manage.py migrate
uv run python manage.py import_fuel_prices --full-snapshot
uv run python manage.py import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed --dry-run
uv run python manage.py import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed
uv run python manage.py runserver 127.0.0.1:8000 --noreload
```

The CSV import creates **6,626 US stations**. The reviewed import resolves exactly
six, leaving **6,620 unresolved**, at dataset revision 2. No database, credentials
or virtual environment is supplied. Imports are validated, transactional and
idempotent; price-only updates preserve current coordinates. Duplicate OPIS IDs
use the lowest listed price while retaining source min/max and provenance.

The committed [Census locality snapshot](data/best-effort-locations.json) is loaded
once per worker for fallback. Setup needs no extra download, station geocoding or
locality import into SQLite. Restart workers after deliberately replacing that
snapshot. Research coordinates are not part of the approved import.

Geoapify reads `GEOAPIFY_API_KEY` from local `.env` or the environment; keep it out
of Postman and screenshots. Missing credentials return a safe 503. Tests need no key.
Settings are for local development, with DEBUG and localhost enabled. Optional
settings include `DJANGO_SECRET_KEY` and `STATION_CORRIDOR_MILES` (default 1 mile).

## API examples

### Strict: reviewed station purchases

```sh
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H 'Content-Type: application/json' \
  -d '{"start":"Albuquerque, NM","finish":"Nashville, TN"}'
```

Observed live result: **200**, **1,221.63 driving miles**, **four purchases**, **$232.44**
purchased fuel; 122.163006 gallons consumed and 72.163006 purchased. Optimization is
limited to the six reviewed candidates. `allow_estimates` omitted/false uses this mode;
strict success remains unchanged even when it is true. Insufficient coverage returns
`422 insufficient_station_coverage`, not invented fuel stops.

### Best effort: conditional fueling-area scenario

```sh
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H 'Content-Type: application/json' \
  -d '{"start":"Atlanta, GA","finish":"Miami, FL","allow_estimates":true}'
```

Observed live result: **663.90 driving miles**. Strict mode returns **422**; opt-in
returns **200** with a conditional **$48.66** scenario in **Adel, GA**, modeling
16.390094 purchased gallons using OPIS 70429's original $2.969/gallon price.

```json
{
  "planning_mode":"best_effort",
  "status":"estimated",
  "fuel_feasibility":"unverified",
  "fuel_stops":[],
  "total_fuel_cost":null,
  "gallons_purchased":null,
  "estimated_fuel_expenditure":"48.66"
}
```

This is a selected-field excerpt. The [full contract](docs/best-effort-planning.md)
includes conditional purchases, original candidate identities/prices, location quality,
provenance, uncertainty, coverage and warnings. A locality point is **not a station
site or entrance**. Its price is hypothetical availability, not a verified purchase
opportunity. Zero ending fuel is fragile under positioning/access uncertainty.
The **6,138 locality-associated records across 47 states are not precisely geocoded
stations**; no estimated physical-site records are supplied.

Fallback runs only after strict coverage failure, never validation/authentication,
provider or unrelated errors. Invalid inputs return 400; insufficient hypothetical
coverage/rejected uncertainty returns 422; missing/corrupt server locality data
returns 500; provider failures return safe 502/503 responses. Future provider geometry
may change the observed figures; they are not hardcoded.

### Maps and response conventions

Successful responses include route GeoJSON, distance, mileage method, dataset revision,
warnings and `map_url`. Money/gallon values are decimal strings. Strict responses
return station purchases/totals; best effort keeps guaranteed totals null and exposes
quantities in a conditional scenario. [Live evidence](docs/best-effort-live-verification.md)
documents the differences.

Open the **newly returned** `map_url`. Strict maps show reviewed sites; best-effort
maps show hollow locality indicators with readable source/method and uncertainty.
No locality indicator is a navigation destination. Maps expire after one hour or
eviction. Saved localhost URLs are historical evidence, not hosted endpoints.
Leaflet assets and attributed OSM tiles need browser access, separate from routing calls.

## Tests and Postman

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check routing tests spikes config/settings.py config/urls.py
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

The published suite contains **214 tests**. Reproduce both examples with no key,
external requests or existing database using the recorded real-provider regressions:

```sh
uv run pytest tests/test_recorded_corridor.py tests/test_recorded_best_effort.py -q
```

They create isolated ORM datasets from committed inputs and replay original provider
payloads. This is recorded reproduction, not a new live verification.

Import [the Postman collection](docs/postman/spotter-routing.postman_collection.json),
set `base_url` to `http://127.0.0.1:8000`, and follow [its instructions](docs/postman/README.md).
It covers strict success, strict Atlanta–Miami failure and opt-in success with
contract, identity, inventory and uncertainty checks. Exact snapshot assertions are
optional; random map IDs and provider latency are not asserted.

Cold live requests use up to two endpoint geocodes plus one driving route, with no
retries or station discovery. Both distinct examples may consume six calls;
strict/opt-in share route geometry. Agent workflows require explicit approval for
live calls. Tests, imports and setup do not consume API credits.

## Architecture and assumptions

### Why Geoapify?

Google Maps was a viable alternative. The assessment requested a free routing/maps
API, and [Geoapify's free tier](https://www.geoapify.com/pricing/) suited the anticipated
assessment usage. Geoapify provides driving-route geometry and step-level distances
needed for route matching and the optimizer. The integration is isolated behind an
adapter, keeping core planning and pure fuel optimization provider-independent.

DRF validation → isolated Geoapify adapter → ORM station repository → pure route
projection → pure Decimal optimization → API/Leaflet response. Strict queries use
indexed coordinates and projected values in a revision-consistent snapshot. External
HTTP and mathematical processing run outside database transactions. Best effort is
a separate layer using immutable offline hints and the unchanged optimizer. Plan
caches distinguish modes and data versions; geometry caches are shared.

- Full **50-US-gallon** starting tank, **10 MPG**, **500-mile** modeled range; partial
  fills, zero ending reserve and zero stop penalty.
- Trip cost excludes the unknown initial tank cost. Strict includes a valid but
  potentially impractical 0.212-gallon fill under this model.
- Prices are historical USD-per-gallon listings; grade, supply and current prices
  are unknown. Lowest-price selection is optimistic when source records disagree.
- Fixed-route optimality concerns the supplied candidates/assumed positions, not
  all stations or alternate roads. Entrances and access detours are unverified.
- Projection interpolates provider-step mileage; missing steps use disclosed scaled
  geometry. Corridor proximity does not prove access; locality points may be miles away.
- Contiguous-US endpoints only; no guarantee all route segments stay within the US.
- Process-local route/plan caches and single-machine map snapshots; no deployment
  SLA, live price feeds, PostgreSQL/PostGIS, Redis, Celery or station CRUD interface.

See [architecture](docs/architecture.md) and [original assignment](docs/assignment.md).

## Evidence

- [Data/fixture index and licensing](data/README.md): immutable seed, approved sites,
  runtime hints, full provider fixtures and attribution.
- [Strict live/browser verification](docs/final-verification.md).
- [Best-effort live/browser verification](docs/best-effort-live-verification.md).
- [Current attribution screenshots](docs/map-attribution-verification.md), explicitly saved-response replay.
- [Fresh-database and quality checks](docs/delivery-verification.md).
- [Reviewed-site identity evidence](docs/corridor-investigation.md).
- [Historical research archive](docs/archive/README.md), separate from setup/API guidance.

Routing/geocoding powered by [Geoapify](https://www.geoapify.com/), with
[© OpenStreetMap contributors](https://www.openstreetmap.org/copyright).
Provider/data attribution and redistribution terms are documented in the data index.
