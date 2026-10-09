# Loom walkthrough draft — 4 minutes 45 seconds

Prepared only: no recording or submission has been performed. Use Postman and a
real running Django API. A new live run requires separate Geoapify approval; do not
pass replayed responses off as live. Keep .env, HTTP credential URLs and account
pages off screen. Use the reviewed six-record SQLite import, never synthetic matches.

| Time | Screen and narration |
| --- | --- |
| 0:00–0:25 | README coverage notice. “This is a Django/DRF fuel planner using a fixed CSV snapshot. The real demonstration is Albuquerque to Nashville. Six stations are identity-reviewed; 6,620 remain unresolved. This is not nationwide fuel coverage.” |
| 0:25–1:20 | Postman POST `http://127.0.0.1:8000/api/route/`, raw JSON `{"start":"Albuquerque, NM","finish":"Nashville, TN"}`. Send only with live approval, otherwise show the saved live response clearly labeled recorded evidence. Inspect 200, 1,221.63 miles, revision 2, incomplete-coverage flag, four purchase OPIS IDs 4446/7733/52468/6755 and $232.44. Point to consumed 122.163006 / purchased 72.163006 gallons. |
| 1:20–1:55 | Open the newly returned `map_url` from an approved running request. Show route, endpoints, purchase popups, CSV prices and attribution. Zoom Amarillo to separate the two close markers. If replay is used, explicitly label provider replies as recorded real data. An expired saved map URL cannot be reused; show labeled verification screenshots if no running demo is approved. |
| 1:55–2:30 | `routing/models.py` and management commands: unique OPIS ID, min/max source prices, coordinates/status/provenance, location fingerprint excluding price. “Validate first, then atomic writes; unchanged imports do not increment revision. Price changes reuse coordinates.” |
| 2:30–3:05 | `routing/provider.py` / `routing/repository.py`: bounded adapter, two US geocodes plus one route, no retries or runtime station enrichment. HTTP outside DB transactions; indexed bounding box, projected rows and two SELECTs in a consistent revision snapshot. Cached plans include shared revision. |
| 3:05–3:45 | `routing/geometry.py` / `routing/fuel.py`: project onto route segments using provider step mileage; configurable corridor, pure Python/Decimal optimization. “Start full at 50 gallons; 500 miles at 10 MPG; partial purchases, no reserve or stop penalty. Buy enough to reach a cheaper station, otherwise fill within capacity. Tests check conservation and an independent small-case oracle.” |
| 3:45–4:15 | Tests/final verification: 148 passing, mocked failures and recorded real-route regression, cold live three calls in 4.52 s, actual Chrome/Leaflet checks, isolated fresh database. Distinguish measured live latency from replay/synthetic benchmarks. |
| 4:15–4:45 | Coverage/assumptions. “$232.44 excludes the unknown initial tank cost. The 0.212-gallon fill is valid in the zero-stop-penalty model but operationally impractical. Prices are historic; entrances and detours are unverified. Optimal means this fixed route and reviewed subset. Unsupported long routes return an explicit 422, never invented stations.” End with documented setup and feature-branch link. |

Prerequisites: reviewer has repo access; fresh setup commands tested; API key present
off screen; browser assets/tiles available with approval; Postman body ready; console
font readable; code files bookmarked. Avoid setup/install footage and full GeoJSON
scrolling. If live data changes materially, stop and explain instead of swapping in a
cached response without disclosure. The approved snapshot cost is evidence, not a
guarantee that future provider geometry will produce exactly the same amount.
