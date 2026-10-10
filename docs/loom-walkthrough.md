# Loom walkthrough draft — 4 minutes 45 seconds

Prepared only; no recording or submission performed. Use Postman and the actual
running Django API. Demonstrate both previously verified routes. For recording,
obtain approval first and either reuse a verified warm worker with a checked
provider ledger or approve a bounded off-camera preflight. Current live authorizations
are exhausted; never silently make another cold call. Recorded-response reproduction
is valid when explicitly labeled replay, never presented as a new live run.
Keep `.env`, credential-bearing provider URLs and account pages off screen.
See [the recording checklist](recording-checklist.md).

| Time | Screen and narration |
| --- | --- |
| 0:00–0:20 | README. “Django/DRF with ORM + SQLite and a fixed CSV snapshot. Six independently reviewed station sites support strict planning. An opt-in fallback models fueling areas; those are not verified stations.” |
| 0:20–1:10 | Postman request 1, Albuquerque → Nashville strict. Show 200, 1,221.63 driving miles, four purchases, $232.44; 122.163006 consumed and 72.163006 purchased gallons. “This is optimization within six reviewed route candidates, not the nationwide network. Endpoint and route data are cached from the disclosed preflight.” |
| 1:10–1:35 | Open this response's fresh strict `map_url`; show route, station popups, prices and attribution. Zoom Amarillo if needed to distinguish the two close purchases. |
| 1:35–2:00 | Postman requests 2 and 3: Atlanta → Miami strict 422, then `allow_estimates:true` 200. Show 663.90 miles, $48.66 conditional expenditure, `fuel_feasibility:unverified`, `fuel_stops:[]`, `total_fuel_cost:null`. “Strict is always attempted first; only inadequate coverage invokes fallback.” |
| 2:00–2:20 | Fresh best-effort map URL. Show hollow Adel area indicator and readable Census source/locality/method. “This is not a station location or verified entrance. The scenario associates original OPIS identities and prices with an assumed area; no road-access guarantee.” |
| 2:20–2:50 | `routing/models.py` and `routing/importing.py`: unique OPIS IDs, source-price min/max, accepted coordinates/provenance, location fingerprints excluding prices. “Validate first, atomic writes, idempotent revisions. Price changes need not repeat geocoding.” |
| 2:50–3:15 | `routing/provider.py` and `routing/repository.py`: two US geocodes + one driving route; no retries or per-station runtime geocoding. HTTP outside transactions, projected indexed strict filtering, consistent revision snapshots and cached geometry. |
| 3:15–3:50 | `routing/geometry.py` and `routing/fuel.py`: projected provider-step chainage, independent pure Decimal optimizer. “Start full: 50 gallons, 10 MPG, 500-mile range, partial fills, zero reserve/stop penalty. Buy toward a cheaper reachable station, otherwise fill within capacity. Tests use a small-case optimality oracle.” |
| 3:50–4:15 | `routing/best_effort.py`: unchanged optimizer invoked in a separate conditional layer, distinct cache keys and provenance/version. “6,138 locality-associated records are not precisely geocoded sites. Town points may be miles off route; no uncertainty margin is invented. Zero modeled ending fuel is fragile.” |
| 4:15–4:45 | Tests/README. “Over 200 tests, provider failures, recorded real-route regressions, clean-database and actual browser checks. Initial tank cost unknown/excluded; historic prices, detours and entrances unverified. The 0.212-gallon strict fill can be impractical. Strict coverage remains limited; optional guidance does not establish nationwide fuel feasibility.” End with setup/Postman collection and feature-branch link. |

Do not film installation or scroll full GeoJSON. Expected figures are the verified
snapshots, not guarantees about a future provider response. Stop on discrepancies,
provider errors, expired maps or an exhausted ledger. Keep the recording under five
minutes and review audio, readability, secret exposure and truthful cached/live/replay
labels before submission approval. No permission change or submission is implicit.
