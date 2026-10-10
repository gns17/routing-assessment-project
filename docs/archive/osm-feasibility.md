# GNS-12 — bounded New Mexico OSM feasibility

**Recommendation: refine as a review-assistance tool; do not expand nationally or
enable unattended coordinate acceptance before submission.** Discovery is cheap;
identity tags and coordinate quality are the limiting factors. This experiment did
not change the application, matching thresholds, prices, six accepted records,
coordinate importer, submission package or Loom. No Geoapify calls or coordinate
imports occurred. Findings require user review before any next experiment/import.

Authorized cap: two hours from **2026-10-09 20:04:52 UTC**, stop by 22:04:52 UTC.
Extraction, matching, 20-case audit and report checkpoint completed at
**20:27:58 UTC (about 23 minutes)**, comfortably within the cap. Final reporting and
issue reconciliation also finish within that cap. Deadline supplied by the
user: **October 11, 2026, 16:55 GMT−3 / 19:55 UTC**. Reserve delivery/recording time;
research is nonblocking. The user reviewed and accepted these findings; GNS-12 is
closed as a **completed feasibility investigation**, not successful enrichment.
Decision: **no nationwide OSM expansion before submission, no production acceptance
rule changes, and no import of the five verified research sites**. Production remains
six approved sites / 6,620 unresolved stations. Verified research evidence is not
authorization to import coordinates.

## Input, extraction and reproducibility

Examined **107 distinct OPIS IDs / 107 source rows**, all New Mexico. Original seven
columns: OPIS ID, name, address, city, state, rack ID, retail price. All source prices
and source bytes are preserved; reconciliation attaches no prices to OSM objects.
Most location descriptions identify highways/exits/intersections rather than civic
street addresses. Whitespace is normalized; identity is OPIS-based, not OSM-based.

Inspected existing Station constraints, price-independent fingerprint, projected
repository, pure matcher and reviewed-coordinate importer. Import requires explicit
review, `identity_verified: true`, current fingerprint, provenance and valid coordinates;
experimental output deliberately is **not** a reviewed import artifact. High-confidence
research status is not the production `accepted` status. ORM/SQLite stays unchanged.

Downloaded only `new-mexico-261008.osm.pbf` from [Geofabrik New Mexico](https://download.geofabrik.de/north-america/us/new-mexico.html).
HEAD confirmed 136,470,545 bytes before download; transfer HTTP 200, no retry,
18.326511 seconds. Actual PBF header snapshot: **2026-10-08T20:21:06Z**, generator
osmium/1.16.0. SHA256:
`6c2493b8e323e18cbe5b29ea701a800a5f4e45e0f6ec17444577c9c0b7f4fcab`.
Pinning the downloaded file/header avoids relying on cached web-page dates or an
unversioned latest URL. OSM data is © OpenStreetMap contributors, ODbL; derived
candidate data retains object IDs/source links and needs appropriate attribution.

Pyosmium **4.3.1** installed from a wheel in an isolated temporary Python 3.13
environment; no `pyproject.toml`/lockfile changes. Its [streaming handler API](https://docs.osmcode.org/pyosmium/latest/reference/Handler-Processing/)
supports node-location lookup for ways. Prototype uses `sparse_mem_array`, retaining
node coordinates and only fuel POI records, not the full OSM document/way collection.

| Measurement | Observed |
| --- | ---: |
| Nodes / ways / relations streamed | 21,141,471 / 1,597,601 / 14,354 |
| Fuel node / closed-way objects | 455 / 566 = **1,021** |
| Fuel relations omitted | 7; counted, not assembled |
| Missing node/way geometry | 0 in this extract |
| Extraction elapsed | **30.651969 s** |
| Peak extraction process RSS | **576,110,592 B ≈ 549.42 MiB** |
| Initial extraction/reconciliation/hash pass | 34.296552 s |
| Corrected reconciliation only | **1.818592 s**, 107 × 1,021 comparisons |

Resource guards stop at 2.8 GiB peak RSS, >5 GiB scratch or extraction timeout.
They are checked every 100,000 objects and after processing; there is no claim of
a per-allocation OS hard limit. Target <2 GiB was met. Scratch total including PBF,
wheel environment, public-page evidence and results totals **198,230,353 logical
bytes (~189.05 MiB)** and **157,084 KiB allocated (~153.40 MiB)** at the final
checkpoint; the small final summary adds a few KiB. Hardware: 8 GiB RAM, initially
161 GiB free disk. No resource limit was approached.

Each fuel object preserves complete raw tags (names/official/old/alt aliases, brand,
operator, refs, addresses and source tags), object type/ID/link, coordinates and
coordinate provenance. Nodes use their OSM position. Closed ways use a translated
planar area centroid: a site proxy, not a driveway or surveyed pump; concave polygons
can have exterior centroids. Relations are not silently assigned a point. **1,021
objects does not mean 1,021 distinct businesses**: multiple canopies and node/way
representations are retained. State clipping can include adjoining complete ways;
rough geographic bounds are a plausibility test, not independent state verification.

Reproduce offline, with raw extract/output outside the repository:

```sh
uv venv /tmp/spotter-nm-osm/venv --python 3.13
uv pip install --python /tmp/spotter-nm-osm/venv/bin/python osmium==4.3.1
# Place the approved, pinned New Mexico PBF under /tmp/spotter-nm-osm/.
/tmp/spotter-nm-osm/venv/bin/python spikes/osm_feasibility.py \
  --pbf /tmp/spotter-nm-osm/new-mexico-261008.osm.pbf \
  --output /tmp/spotter-nm-osm/results.json --max-seconds 300
uv run pytest tests/test_osm_feasibility.py -q
```

Prototype/tests are source-controlled candidates; downloaded data, experimental
JSONs, public HTML and temporary helpers stay outside Git. Current scratch directory
is `/tmp/spotter-nm-osm-20261009`; evidence files: `results.json`, `audit.json`,
`route-diagnostic.json`, `official-marker-coordinates.json`, final `summary.json`.
No Google map API, static-map image or paid service was called: numeric markers
were read from already retrieved first-party HTML. Credential-bearing embedded
third-party map URLs are omitted from exported audit metadata.

## Explicit identity rules

The automatic prototype never outputs Verified. High-confidence requires:

- Exact documented brand spelling plus exact branch reference and locality agreement,
  **or** exact distinctive independent business-name tokens (at least two) plus locality.
- Valid fuel-POI geometry in rough New Mexico bounds, no explicit state/locality/branch
  contradiction and no competing strong identity candidate, including one lacking locality.
- Branches come from explicit `#` names or designated ref tags, including a named ref
  such as `Albuquerque #639`. A house number is never treated as a branch number.

Canonical spelling aliases are visible in the prototype/result metadata: e.g. Love's/
Loves, Allsup's/Allsups and TA/TravelCenters of America. No automatic historic brand,
branch-prefix or locality substitution. Corporate operator and fuel-supplier brand
are retained for review; they are not interchangeable with storefront identity.
Street-address fields are preserved, but a CSV highway-exit description does not
prove an exact match to an OSM postal address. Website/phone hints are diagnostic;
they do not override conflicting geometry or supply an independently verified location.

Chain-only, missing locality/ref, generic/unnamed fuel POIs and competing objects
remain ambiguous or unmatched. Unmatched is an unresolved subtype, not a rejection
or proof that the business is absent. Exact locality conflicts initially reject a
candidate; manually documented mailing-place aliases can reverse that judgment,
without changing production rules. Only manual corroboration of identity **and**
site location using first-party coordinates and independently mapped fuel geometry
produced Verified research cases. These remain unapproved for database import.
Verified means a corroborated business site, not a verified truck entrance, truck
fuel lane, compatible fuel grade or current price. Some named car-fuel POIs carry
`hgv=no`, while nearby truck-fuel POIs are unnamed; neither is silently substituted.

## Coverage before and after audit

All percentages use **107 OPIS records**, not OSM objects or only returned candidates.

| Category | Automatic-only | After explicit manual audit |
| --- | ---: | ---: |
| Verified | 0 (0%) | **5 (4.67%)** |
| High-confidence automated candidate, not verified | **6 (5.61%)** | **2 (1.87%)** |
| Ambiguous/approximate/unresolved | 100 (93.46%) | **99 (92.52%)** |
| Rejected | 1 (0.93%) | **1 (0.93%)** |

Automatic unresolved group: 29 ambiguous + **71 unmatched**. Manual final group
still includes **70 unmatched by the prototype**; Love's Milan was recovered manually.
Verified plus remaining high-confidence = 7 (6.54%), **not** 7 accepted import records.
Only the five reviewed research sites have the strict manual evidence described here.

| Missing OSM tag | Objects / percentage of 1,021 |
| --- | ---: |
| name | 256 / 25.07% |
| brand | 382 / 37.41% |
| operator | 940 / 92.07% |
| ref | 906 / 88.74% |
| addr:city | 594 / 58.18% |
| addr:street | 567 / 55.53% |
| addr:housenumber | 577 / 56.51% |

## Twenty-case purposive audit

Selected all six corrected automatic-high cases, seven ambiguous cases, the single
automatic rejection and six unmatched records. Covers urban Albuquerque, rural
interstate exits, independent truck stops, several chains, highway-only addresses,
locality aliases, street/branch mismatches and NM's northern/southern/eastern/western
regions. This is a quality/debugging sample, **not random or statistically representative**.

Outcome: **5 corroborated site matches, 1 incorrect coordinate, 9 identity-supported
but location-incomplete cases, 5 unreconciled OSM identities**. Of six automatic-high
cases, three were site-verified, two remain high-confidence and one was downgraded
to ambiguous. None was proved incorrect, but half lack full site verification;
**do not report 100% precision or a nationwide false-positive rate**. The incorrect
coordinate was already ambiguous automatically, not an accepted recommendation.

| OPIS / station | Audited outcome | Evidence / reason |
| --- | --- | --- |
| 7045 Bubble City, Farmington | Verified | [Official Valero](https://locations.valero.com/en-us/LocationDetails/Index/3125-BLOOMFIELD-HWY/0000032078) names the business at 3125 Bloomfield Hwy; explicit marker is 20.68 m from [OSM fuel way](https://www.openstreetmap.org/way/535023386), matching name/address. |
| 64187 Speedway #9117, Las Vegas | High-confidence, not verified | [Current operator](https://careers.7-eleven.com/job/las-vegas/restaurant-crew/45445/78024874624) uses #47106 at 1 Romeroville; [NMED](https://www.env.nm.gov/petroleum_storage_tank/wp-content/uploads/sites/20/2024/12/2024-12-02-NMED-facility_active_tanks_county.pdf) supports historic #9117. [OSM node](https://www.openstreetmap.org/node/2879191692) agrees, but independent numeric site location unavailable. |
| 65361 Black Mesa, Algodones | Ambiguous; downgraded from high | [Official](https://blackmesa-travelcenter.com/location/) says 26 Hagen Rd/San Felipe; [OSM](https://www.openstreetmap.org/node/11251543300) says 25/Algodones. Identity plausible, exact site/address discrepancy unresolved. |
| 66237 Route 66 Travel Center | Verified | [Casino](https://www.rt66casino.com/rt-66-travel-center/) confirms exit 140; [Valero](https://locations.valero.com/en-us/LocationDetails/Index/14314-CENTRAL-AVE-SW/0000033221) confirms named center at 14314 Central and marker 52.26 m from [OSM canopy](https://www.openstreetmap.org/way/479169964). Campus address 14500 distinguished from site address. |
| 70879 Maverik #611 | High-confidence, not verified | [NMED 2025](https://www.env.nm.gov/petroleum_storage_tank/wp-content/uploads/sites/20/2025/10/Active-Storage-Tanks-10-14-2025.pdf) confirms 7700 Los Volcanes; [OSM](https://www.openstreetmap.org/way/888809684) has branch/address. Current official URL 404; current availability/location remains uncorroborated. |
| 71063 Maverik #639 | Verified | [Official](https://locations.maverik.com/nm/albuquerque/9701-bluewater-rd-nw) branch/address and explicit coordinates agree with [OSM](https://www.openstreetmap.org/way/888809632) within 41.54 m. An independent directory mislabeled this address #611; it was not trusted. |
| 4417 TA Moriarty | Verified site, multiple objects | [Official #229](https://www.ta-petro.com/location/nm/ta-moriarty/) address/exit/JSON-LD corroborate [one diesel canopy](https://www.openstreetmap.org/way/226934271) within 65.12 m and a second same-address canopy. Manual grouping, no automatic merge. |
| 61357 Kent Kwik #501 | Ambiguous | [Government site assessment](https://cloud.env.nm.gov/resources/_translator.php/MTQ3Y2FlODgyNzcwM2Q1MjBlM2ZkYmRhMF81NTI4NQ~~.pdf) confirms 3500 North White Sands, matching [OSM](https://www.openstreetmap.org/way/995652167); missing branch tag and first-party numeric corroboration. |
| 64215 Stripes #42588, Tatum | Ambiguous, promising address match | [Official](https://stripesstores.com/locations/store-42588) says 10 E Broadway; [OSM](https://www.openstreetmap.org/way/511358601) same name/address, missing branch; no independent numeric coordinate obtained. |
| 73043 Maverik #740, Las Vegas | **Rejected coordinate** | [Official](https://locations.maverik.com/nm/las-vegas/2472-n.-grand-ave) says 2472 N Grand with explicit coordinate. [OSM node](https://www.openstreetmap.org/node/13769097683) says 22742 and is **1,076.31 m away**, despite same phone/website. No nearby substitute accepted. |
| 72837 Quarles #54284, Loving | Ambiguous, promising address match | [Official guide](https://www.quarlesinc.com/wp-content/uploads/2026/04/QFF-pocket-site-guide-v4-2026.pdf) specifies 22 W London; [OSM](https://www.openstreetmap.org/way/1373574213) agrees but lacks branch/independent site coordinate. |
| 65989 Dancing Eagle | Ambiguous; automatic rejection reversed | [Official](https://www.dancingeaglecasino.com/dancing-eagle-travel-center/) exit 108/Casa Blanca and [government](https://www.rld.nm.gov/wp-content/uploads/2026/01/FID-Authorized-Delegate-Directory-as-of-12-31-2025.pdf) 167 Casa Blanca support [OSM](https://www.openstreetmap.org/way/904596024), whose city is Paraje. Mailing-locality difference requires documented review. Embedded map viewport is not a POI coordinate. |
| 1356 Love's #257, Milan | Verified; automated miss | [Official](https://www.loves.com/locations/nm/milan/loves-travel-stop-milan-257) explicitly OPIS 01356, complete street, phone and JSON-LD; [OSM named node](https://www.openstreetmap.org/node/11471626969) agrees within 34.04 m. Missing locality/ref prevented automatic acceptance. Housenumber 257 was not mistaken for branch evidence. |
| 1596 Flying J #305, Jamestown | Unreconciled | [Official](https://locations.pilotflyingj.com/us/nm/jamestown/1-giant-crossing) provides exact identity/coordinate; nearby [unnamed truck fuel node](https://www.openstreetmap.org/node/957789428) and brand-only car fuel node lack branch/address identity. Neither accepted by proximity. |
| 64211 Pilot #490/Western Petroleum | Unreconciled | [Historical listing](https://opendatany.com/place.php?id=ChIJfe6e22x544YR7YCrbcPjZlA) supports 3202 S Canal; [unnamed canopy](https://www.openstreetmap.org/way/361182465) only 3 m away still has no identity/address. No substituted Shell/Shamrock POI or new verification claim. |
| 7227 National Truck Stop, Vado | Unreconciled | [Official Valero](https://locations.valero.com/en-us/LocationDetails/Index/16320-STERN-DR-7298/0000028422) names National and its coordinate; adjacent [generic Valero fuel canopy](https://www.openstreetmap.org/way/1385358683) lacks site identity/address. Brand/proximity alone not accepted. |
| 64523 Sky City | Unreconciled | [Official](https://skycitytravelcenter.com/contact-us/) and [NM Gaming Board](https://www.gcb.nm.gov/new-mexico-gaming-control-board-office-of-the-state-gaming-representative/) confirm Acoma/exit 102. No named fuel identity; locality/exit-level embedded query is not a station point. |
| 6001 Allsup's #2392, Roswell | Unreconciled | [Independent listing](https://www.affordablehousing411.com/food-assistances/snap-retailer-details-allsups-102392-5500-n-main-st-roswell-nm-88201/) suggests #102392 at 5500 N Main. OSM uses supplier Valero. No confirmed prefix alias or first-party site identity obtained. |
| 69119 Circle K #2741217 | Ambiguous | [NM lottery](https://www.nmlottery.com/wp-content/uploads/2024/01/February-2024-Best-Practices_sm.pdf) supports branch; [OSM](https://www.openstreetmap.org/way/830411135) embeds official ID URL/385 US550. Official fetch redirects to generic locator. CSV I-24 is inconsistent with locality, possibly a typo; not silently corrected. |
| 71995 Chevron, Clines Corners | Ambiguous | [OSM](https://www.openstreetmap.org/way/340494077) names 1 Yacht Club and links official locator; JS-driven official page provides no corroborating coordinate. Unique local brand is insufficient alone. |

## Route benefit and national scalability

Used only saved real Geoapify route geometry/step mileage with the unchanged pure
matcher/optimizer. **Zero** of six original automatic-high candidates matches the
one-mile Albuquerque–Nashville corridor. Four of the five manually corroborated
sites are west of the starting point or on other highways. TA Moriarty matches at
**mile 38.211571, offset 0.207536 mile**. An explicitly offline counterfactual with
the baseline six plus these five retains the same four purchase IDs and **$232.44**
cost. It is not an API result or approved coordinate import. Existing 500-mile
feasibility does not improve: it was already feasible. These findings do not prove
an additional arbitrary route can be completed; no new driving routes were requested.

Reviewed/strong sites cluster in north/central NM: Farmington, Milan, Albuquerque,
Moriarty and Las Vegas/Algodones. No strict reviewed site on I-10 or the southeastern
oilfield corridors emerged from this audit. Straight-line distances and town centroids
cannot prove 500-mile driving legs or access. Evaluate priced stations' **on-route
positions and remaining gaps** on specific saved/approved driving routes before
claiming network improvement.

Processing 6,626 CSV rows is small; scanning OSM and missing identity fields dominate.
[Geofabrik's metadata](https://download.geofabrik.de/north-america/us.html) lists the
full-US snapshot at 12,194,147,082 bytes (about 11.4 GiB), already above the experiment's
5 GiB scratch cap. Only that HTML metadata was read; no US/additional-state extract
was downloaded. **Do not use NM byte ratios as sizing guarantees**: tags, node density
and states vary. Direct byte scaling of measured extraction elapsed gives roughly
46 minutes of decode time and 51 GB RSS for a whole-US single-pass in-memory cache,
which is plainly unsuitable; these are scenarios, not measured national performance.
Use sequential state/chunk processing with file-backed node locations or prefiltering
if a future expansion is approved, retaining compact POIs and releasing each extract.
Larger states can exceed the memory target even with this NM cache choice.

Naive all-pairs reconciliation scales poorly: at the measured 1.82 s / 109,247 pairs,
6,626 rows × a hypothetical 100,000–200,000 POIs implies roughly **3–6 hours** of
matching alone. Those POI counts are scenarios, not measured US counts. Simple
branch/chain/name/locality dictionaries can sharply reduce comparisons without new
infrastructure. Better indexing does not invent absent branch/address tags or cure
bad geometry. Relation assembly, canonical physical-site grouping, locality aliases,
fuel-supplier/operator separation and authoritative branch/address crosswalks need
additional tests/review. Existing per-state extraction evidence is technically promising;
**unattended national identity reconciliation is not demonstrated**.

Human review remains necessary for every proposed production import under current
rules. Even favorable automated candidates need a review queue, not auto-promotion.
At an illustrative 2–5 minutes per record, reviewing 6,626 records would require
220–552 hours; this is a planning estimate, not a measured human throughput rate.
The 20-case purposive audit cannot justify national precision/coverage extrapolation.
Renumbered stores, missing labels, supplier branding, duplicate canopies and misplaced
nodes create a concrete risk of attaching OPIS prices to the wrong fuel location.

If the user approves individual reviewed sites, preparing five current-fingerprint,
evidence-bearing artifacts and using the existing dry-run/transactional/idempotent
importer needs **roughly 1–2 hours** including explicit review and regression checks,
not a model/migration/rule change. Remaining ambiguous cases require more source
review; that effort is not included. No import artifact was produced or imported
here. None of these five adds a new purchase to the current demonstration, so this
is optional breadth, not a prerequisite for delivery.

Locality-level estimates can be useful only in a non-actionable research heatmap or
unresolved-record summary (e.g. town-level missing coverage). Keep approximation type,
uncertainty and source separate; never attach fuel prices, route-mile positions,
range feasibility or recommended stops to a city/road centroid. No such feature was
added to production. Stop this experiment here; retain strict identity gates and the
existing reviewed demo. Any refinement, import or expansion requires a new decision.

## Final checks and preservation

**162 tests pass (148 baseline + 14 isolated research tests)**. Ruff, Django system
checks, migration-drift and whitespace checks pass. Resource-limit and identity/
competition/branch-reference cases are covered without making osmium a runtime
dependency. Database SHA256 remains byte-identical to the pre-experiment file;
the original CSV and six-reviewed-coordinate artifact match Git HEAD byte-for-byte.
Production code/dependencies and the preexisting local submission/Loom documentation
changes were not altered by this experiment. Only the new spike, research tests and
this report form the separate research checkpoint. Raw/scratch artifacts remain
outside Git. GNS-12 closes only after the completed 20-case quality audit and the
user's acceptance of its limited yield/negative unattended-enrichment conclusion;
prototype implementation alone was not the completion criterion. GNS-11 delivery
resumes as the critical path; any future research/import needs new approval.
