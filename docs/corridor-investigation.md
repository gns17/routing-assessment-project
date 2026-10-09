# Albuquerque–Nashville corridor investigation

Executed 2026-10-09 UTC, starting 02:47:03; completed within the 90-minute cap.
This investigation reviews six source stations. No additional fallback station
reviews, nationwide enrichment or OSM extract downloads were needed. Public OSM
rendered map tiles were viewed for independent site-placement evidence, not vector
extracts or automated POI matching. No station coordinates were imported into SQLite.

## GitHub push

Confirmed `origin` points to the intended **private** repository
[gns17/routing-assessment-project](https://github.com/gns17/routing-assessment-project).
Pushed the existing feature branch normally (no main push/force/history rewrite):
[feat/assessment-implementation](https://github.com/gns17/routing-assessment-project/tree/feat/assessment-implementation).
Remote commit listing confirmed all five approved commits:
`2a92e25`, `c2cd076`, `41b9f7b`, `ce09a6f`, `4ebdf40`.
The investigation artifacts and narrow normalization fix below remain local and
uncommitted; they were not part of the approved existing-commit push.

## Actual route and usage

Albuquerque, NM → Nashville, TN: **1,221.630055 miles** (provider driving route).
The live result contains **12,071 geometry segments** with validated road-step
mileage, using within-step geometric interpolation for station positions.

| HTTP attempt | Operation | Status | Latency |
| --- | --- | --- | --- |
| 1 | Albuquerque endpoint geocoding | 200 | 1.0741 s |
| 2 | Nashville endpoint geocoding | 200 | 0.4137 s |
| 3 | Driving routing | 200 | 2.3647 s |

Total **three attempts, 3.8525 s HTTP latency, zero retries/errors**. The credential
was loaded from local .env and checked for presence/matching without exposing it.
The runner enforced both its own three-attempt checkpoint/deadline guard and the
adapter limit, with transport retries=0 and redirects disabled. Existing checkpoints
prevent rerunning live requests. No further Geoapify calls are authorized under this
budget; saved-response replay made only mocked requests.

Estimated usage is **six credits**, below the eight-credit reserved allowance,
based on two geocodes and the published 500-km routing-distance pricing. The exact
account debit is **not verified**: responses supplied no usage/credit headers, and
no separate account/usage API was called. See
[Geoapify pricing](https://www.geoapify.com/pricing-details/).

Sanitized raw replies, attempt timings and normalized geometry are preserved in
[data/corridor-route.json](../data/corridor-route.json). No credential values or
credential-bearing request URLs are retained.

## Reviewed source stations

All six are accepted **for identity and station-site location**, not exact entrances
or detour-inclusive navigability. Coordinates come from official business listings;
independent OSM rendered building/forecourt/brand mapping corroborates placement.
This is document/visual review, not a GPS survey or an OSM object/tag audit.

| OPIS | Official identity/address | Latitude, longitude | Route miles | Offset miles | CSV selected price |
| --- | --- | --- | ---: | ---: | ---: |
| 4446 | [Love's #200](https://www.loves.com/locations/tx/amarillo/loves-travel-stop-amarillo-200), 6930 I-40 E., Amarillo TX | 35.191927, -101.760945 | 290.859611 | 0.0452 | 3.20900000 |
| 7733 | [Flying J #723](https://locations.pilotflyingj.com/us/tx/amarillo/9601-e-i-40), 9601 E I-40, Amarillo TX | 35.1937863, -101.7234389 | 292.979032 | 0.0721 | 3.26566666 |
| 52468 | [Flying J #703](https://locations.pilotflyingj.com/us/ok/oklahoma-city/701-s-morgan-rd), 701 S Morgan Rd, Oklahoma City OK | 35.4587888, -97.6904462 | 533.416479 | 0.0906 | 3.30900000 |
| 4227 | [Love's #203](https://www.loves.com/locations/ok/oklahoma-city/loves-travel-stop-oklahoma-city-203), 800 S Morgan Rd, Oklahoma City OK | 35.457659, -97.688649 | 533.516811 | 0.1694 | 3.35566666 |
| 6755 | [Petro #0326](https://www.ta-petro.com/location/ar/petro-n-little-rock/), 3205 Valentine Rd, North Little Rock AR | 34.781000, -92.129800 | 884.396169 | 0.2481 | 3.20733333 |
| 52458 | [Pilot #332](https://locations.pilotflyingj.com/us/ar/north-little-rock/3300-ar-391), 3300 AR-391, North Little Rock AR | 34.7811979, -92.1278341 | 884.510260 | 0.2492 | 3.23700000 |

Love's pages explicitly publish **OPIS 04446 and 04227**, matching the source IDs
exactly. Other matches use the exact named chain/branch, city/state and I-40 exit
relationship, not mere proximity. Coordinates for Love's/Petro are published in
JSON-LD `geo`; Pilot/Flying J pages visibly list coordinates. Leading zeroes in
Petro #0326 normalize to CSV branch #326.

Independent placement evidence and inspection pixel positions are recorded per
station in [data/corridor-investigation.json](../data/corridor-investigation.json).
The OSM views distinguish Love's from Flying J on opposite sides of Morgan Road,
Love's #200 from the nearby TA/Exxon property, and Pilot from Petro/truck-wash sites.
Map attribution: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).
Petro also has independent [Arkansas DEQ inspection evidence](https://adeq.state.ar.us/downloads/webdatabases/inspectionsonline/079361-insp.pdf),
page 2: same branch/address, general-area GPS 34.7818,-92.1294, approximately 96 m
from the official point. That historical GPS supports the site, not an entrance.

Selected-record classifications: **6 accepted site locations, 0 ambiguous,
0 rejected**. Incidental search results for Love's #250 and Speedco #901 were
rejected as matches for OPIS 4446: different branch/address/exit. No additional
OPIS station was substituted or assigned another business's price. Independent
map evidence corroborates actual fuel-site placement rather than city/road centroids.

The CSV is unchanged. Pilot #332 retains original min/max 3.237/3.239 and selected
minimum 3.237; live prices displayed by official sites were not imported or used.

## Range feasibility and offline purchase plan

All six reviewed stations fall within the configured one-mile corridor. Consecutive
gaps including endpoints are **290.86, 2.12, 240.44, 0.10, 350.88, 0.11, 337.12
miles**. Largest gap **350.879358 miles**; no interval exceeds 500. Route matching
of these six points took 0.021741 s locally, excluding HTTP and API/database setup.

The pure optimizer, using the actual saved route and reviewed coordinates in plain
Python objects, returns:

| Purchase stop | Route miles | Gallons purchased | Cost, USD |
| --- | ---: | ---: | ---: |
| Love's #200 / OPIS 4446 | 290.859611 | 29.085961 | 93.34 |
| Flying J #723 / OPIS 7733 | 292.979032 | 0.211942 | 0.69 |
| Flying J #703 / OPIS 52468 | 533.416479 | 9.141714 | 30.25 |
| Petro #326 / OPIS 6755 | 884.396169 | 33.723389 | 108.16 |

Totals: **122.163006 gallons consumed**, **72.163006 purchased**, **$232.44 purchase
cost**, zero ending fuel in the model. The initial full 50-gallon tank's unknown
cost is excluded. Exact Decimal values are in the machine-readable report.
The small Flying J #723 top-up is permitted by cost-only optimization with no stop
penalty/minimum fill. It reduces later purchases at a higher price; it is not a
claim that stopping for a fraction of a gallon is practically worthwhile.

Corridor sensitivity: **0.1 mile is infeasible** because it excludes the Arkansas
stations; 0.25, 0.5 and 1 mile include all six and yield the same model result.
The 0.25 threshold has almost no positional margin at Pilot #332; it should not be
adopted as an operational default from this six-station sample. The configurable
one-mile default stays unchanged. Road access, entrances and access detours remain
unverified and excluded from mileage/consumption estimates.

This is optimization among **six reviewed stations** on one provider route, not
among all CSV stations or all road choices. The missing-station denominator cannot
be established geographically without unresolved station coordinates. Production
still has 6,626 records, revision 1, zero accepted coordinates: the long-route DRF
API cannot yet return this plan from its ORM repository.

## Narrow integration defect and validation

The live response has a rounded zero-distance terminal step. Decimal normalization
applied a -2.2E-23-mile summation correction to that step, causing the matcher to
reject negative mileage. Only the relevant normalization was fixed: apply the
correction to the largest positive segment instead. A new mocked regression test
covers this shape. Replaying the same saved live replies confirms all 12,071
weights are nonnegative and their sum equals provider route distance. No extra
live call was made and no unrelated application behavior changed.

**144 tests pass**, Ruff lint and Django system checks pass, and migration-drift
checks report no changes. Full production DRF/ORM integration and browser visualization
with these real coordinates are **not verified**. GNS-8/GNS-10 remain In Progress;
no Linear status changes were made.

## Artifact awaiting approval and remaining decisions

[data/corridor-reviewed-coordinates.json](../data/corridor-reviewed-coordinates.json)
contains only the six accepted site-coordinate entries: OPIS ID, current location
fingerprint, coordinates, policy and identity/source/evidence. Schema, field limits,
current fingerprints and credential redaction were checked without invoking the
import command. A read-only database check confirmed null coordinates, revision 1
and unchanged SQLite file hash. Nothing was imported.

Approval is required before running
`import_station_coordinates data/corridor-reviewed-coordinates.json --reviewed`.
Then verify the actual ORM-backed API and map. The three live attempts are exhausted:
use an explicitly labeled saved-route replay/cache for local integration checks,
or seek separate approval for another live request budget. Do not silently make
new requests. Coordinate import approval does not authorize further Geoapify usage.

No need to expand to eight stations, download OSM extracts or begin nationwide
enrichment. The main remaining blocker is coordinate-import approval, followed by
an honest production API/map demonstration and final acceptance review.
