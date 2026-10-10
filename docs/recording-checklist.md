# Recording checklist — prepared, not executed

Target 4:45; hard limit 5:00. Follow [the timed script](loom-walkthrough.md).
Deadline: **October 11, 2026, 16:55 GMT−3 (19:55 UTC)**. Original recruitment receipt
timestamp is unavailable; the deadline is user-confirmed.

## Local readiness before recording approval

- Confirm intended reviewer GitHub identity/access. Repository remains private;
  current API listing shows only the owner. Do not invite/change visibility silently.
- Confirm Postman desktop or localhost-capable desktop agent is installed/openable.
  The collection is prepared, but availability is a separate recording prerequisite.
- Import `docs/postman/spotter-routing.postman_collection.json`; set `base_url` to
  `http://127.0.0.1:8000`. No keys in Postman. Disable runners, auto-refresh and retries.
- Confirm SQLite has 6,626 stations / six accepted / revision 2. Do not import the
  unapproved New Mexico artifact or research candidates. Census locality hints are
  static file inputs, not verified station records. Preserve existing coordinates.
- Fresh setup: README install, migrate, CSV `--full-snapshot`, six-site dry run/import.
  The committed `data/best-effort-locations.json` requires no download/geocoding.
- Run the two recorded regression tests first. They need no credential or live calls:
  `uv run pytest tests/test_recorded_corridor.py tests/test_recorded_best_effort.py -q`.
- Hide `.env`, provider URLs/logs, account pages and unrelated tabs. Increase fonts;
  bookmark models/import, provider/repository, matcher, optimizer and fallback code.

## Start one stable Django worker

```sh
uv run python manage.py check
uv run python manage.py runserver 127.0.0.1:8000 --noreload
```

Startup makes no provider requests. `--noreload` avoids silent restart/cache loss.
Stop only a known assessment server if the port is occupied. Keep one process alive
through preflight/recording; do not clear caches, alter data or edit code mid-demo.
Endpoint caches last 24 hours; route/plan caches and map snapshots last one hour
(or eviction). Map file-cache snapshots can outlive a worker, but route caches do not.

## External-request approval gate

**Current budgets are exhausted; no new calls are authorized by this checklist.**
A future cold two-route preflight would need separate approval for at most **six
Geoapify attempts, no retries**, approximately **12 credits**, conservative **16-credit
allowance** (three attempts/eight-credit allowance per route). Use a global bounded
ledger; the normal adapter's three-attempt limit is per request, not session-wide.
No station enrichment, Places, matrices or per-stop routing. Browser Leaflet assets
and OSM tiles are separate network requests and need the approved browser context.

Prefer approved off-camera preflight: strict Albuquerque–Nashville, then opt-in
Atlanta–Miami. Verify both, their ledgers and map pages; keep the worker warm. During
recording all three Postman examples should reuse the same endpoint/route results.
Say explicitly that these are warm API responses using preflight provider data.
Any unexpected cache miss must be blocked by the global budget, not paid silently.
Recorded replay may instead support an explicitly labeled rehearsal; never claim it
is a fresh live provider request. Do not send anything until recording/live approval.

## Postman examples and expected snapshots

1. Strict: `{"start":"Albuquerque, NM","finish":"Nashville, TN"}` → 200,
   1,221.630055 miles, six matched sites, four purchases (4446/7733/52468/6755),
   $232.44, 122.163006 consumed / 72.163006 purchased gallons.
2. Strict failure: `{"start":"Atlanta, GA","finish":"Miami, FL"}` → 422,
   `insufficient_station_coverage`; never fabricate stations to pass.
3. Best effort: `{"start":"Atlanta, GA","finish":"Miami, FL","allow_estimates":true}`
   → 200, `best_effort`/`estimated`/`unverified`, 663.900943 miles, conditional $48.66,
   Adel area, 16.390094 modeled gallons, `fuel_stops:[]`, `total_fuel_cost:null`.

`assert_recorded_snapshot=true` checks exact saved examples; use false for new live
geometry, then manually investigate meaningful deviations. Do not assert latency or
UUID map IDs. Do not replace unexpected current output with old screenshots.

## Maps and stop conditions

Open each response's **newly returned** `map_url` (normally `/maps/<uuid>/`), not an
expired committed URL. Preflight less than an hour before recording. Check strict
route/endpoints/four stop popups, $232.44 and attribution; zoom Amarillo for the two
nearby fills. Best effort must show hollow/dashed Adel reference-area indicator,
readable Census labels, original identities/prices, $48.66 conditional cost and all
warnings. It must not depict a verified entrance or navigation destination.

Check browser console/network errors. The existing live/browser evidence is historical
verification, not permission to load new requests without the recording gate. Zero
modeled ending fuel is fragile; unknown station positioning and detours can break
real driving feasibility. Never imply the 500-mile model guarantees these area stops.

Stop on provider/validation errors, changed geometry/cost requiring review, negative
modeled inventory, unexpected calls, map expiration or unavailable Postman. Resolve
before recording; do not improvise another live request or mislabel replay.

## Finish and submission gates

Keep narration to 4:45. Disclose six-site strict coverage, 6,138 locality associations
(not station geocodes), historic prices, initial tank exclusion, zero reserve/penalty
and unverified access. Review video for secrets, clarity and duration after recording
approval. Fill Loom placeholder only then; obtain submission approval separately.
GNS-11 stays In Progress until its remaining delivery criteria are satisfied.
