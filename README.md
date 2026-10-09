# Spotter Routing Assessment

A Django backend assessment for US route planning and cost-effective fuel stops.
The architecture is approved; the complete application has not been implemented.
Only Issue A, Geoapify Geocoding Feasibility, is the first implementation task.
Its execution plan and external-request budget require approval before geocoding.

## Approved design

- Use Geoapify for endpoint geocoding, routing, and offline station enrichment.
- Accept start and finish location strings. Target at most two endpoint geocoding
  calls and one routing call on a successful uncached baseline request.
- Treat `data/fuel-prices.csv` as immutable source/seed data. Use Django ORM and
  the default SQLite database for normalized stations, prices, coordinates,
  enrichment metadata, and status.
- Keep location enrichment and minimum-price selection as separate offline steps
  updating station records. Location fingerprints exclude prices, source-row
  numbers, and the overall source checksum, so price-only changes reuse coordinates.
- Use indexed coordinates for coarse ORM geographic filtering; avoid N+1 queries
  and unnecessary model instantiation. Keep precise geometry matching and optimization in
  pure Python, independent of Django and storage. Keep the repository interface
  independent of the storage mechanism.
- Return route GeoJSON, fuel-stop data, and a `map_url` served by a minimal Leaflet
  view. Browser map-tile traffic is separate from backend planning calls.
- Use management commands for reproducible, transactional imports and resumable
  offline enrichment. Keep all provider calls outside database transactions.
- SQLite is a deliberate persistence/extensibility choice, not a performance claim.
  Benchmark ORM filtering, query counts, and Python matching on actual routes.
- This assignment uses a fixed snapshot. Price-only reimports must reuse accepted
  coordinates. Live pricing, schedulers, station CRUD/admin interfaces, PostgreSQL,
  PostGIS, Redis, and Celery are outside scope.

## Assumptions and limitations

- The vehicle starts with a full 50-US-gallon tank, achieves 10 MPG, and has no
  required ending reserve. Partial purchases are permitted.
- `total_fuel_cost` means fuel purchased during the trip. Return
  `gallons_consumed` and `gallons_purchased` separately. The initial tank's cost is
  unknown and excluded; a short trip can consume fuel while costing $0 in purchases.
- Treat US retail prices as USD per US gallon for compatible fuel. The supplied
  file does not identify currency, fuel grade, or observation date.
- Deduplicate by OPIS station ID and use the lowest listed retail price. Preserve
  original minimum/maximum values and source-row provenance. The minimum is an
  optimistic dataset assumption, not proof of a current available price.
- Exclude Canadian records and uncertain station coordinates. Missing enrichment
  or station coverage must be reported rather than filled with invented locations.
- Optimize purchases on one provider-selected route, not across the road network.
- Make the station corridor configurable; choose its default after accuracy tests.
  Geometric proximity does not establish road access. Baseline mileage and fuel
  estimates exclude unverified station-access detours.
- Initial scope is contiguous-US road journeys. Cross-border routes and unsupported
  endpoint/route cases need explicit rejection or disclosure.

See [architecture](docs/architecture.md) and the [implementation plan](docs/plan.md)
for component boundaries, transaction boundaries, acceptance criteria, and gates.
The original assignment remains in [docs/assignment.md](docs/assignment.md).

## Development

Use Python 3.13 and `uv`, retaining the project's pinned Django version.
Do not commit `.env` or log provider credentials.

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

These are development checks, not instructions to run live Geoapify requests.
