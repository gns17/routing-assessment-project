# Geoapify station-geocoding feasibility — GNS-5

## Execution status

The approved initial five-station pilot completed on 2026-10-09 UTC (2026-10-08
local time). Exactly five live Geoapify attempts were made; all returned HTTP 200,
with no retries, fallbacks, authentication/quota errors, or transport failures.
The other 25 sample stations remain unqueried. The local .env credential was
verified and loaded without printing or persisting its value.

Automated screening found zero accepted and five ambiguous station queries.
Preliminary identity/precision review leaves four ambiguous and rejects the
Casey's building match pending a source/current-listing address reconciliation.
The subsequent approved name-first/Places comparison also completed: ten additional
attempts, no retries/errors, and all candidates preserved. It verifies TA's site
identity using an official matching address; the other four station identities
remain unresolved. Exact entrances and coordinate access are not independently
verified. GNS-5 is Done: a completed investigation with a negative conclusion
for unattended nationwide Geoapify enrichment. The unexecuted 30-station live
sample and ten-station manual audit criteria are explicitly superseded by the
reviewed evidence, not claimed as satisfied. Further searches are not authorized.
Core application work is approved and independent of enrichment research. The
initial pilot findings below remain preserved as a baseline.

This experiment creates no Django models/migrations and performs no database
writes. Its diagnostic JSON checkpoint is separate from the approved production
ORM + SQLite persistence, which belongs to GNS-6.

## API inspection

Use `GET /v1/geocode/search` with `format=json`, `filter=countrycode:us`, English
output, and up to three candidates. The first query uses station name, normalized
address, city, and state. The bounded fallback uses structured name/city/state/
country inputs without the noisy highway description; text and structured inputs
are not combined. This fallback may improve POI identity but loses address detail.

Useful fields retained in the artifact:

| Fields | Review purpose |
| --- | --- |
| `lat`, `lon`, `formatted`, address components | Inspect actual location and geographic consistency |
| `name`, `state_code`, `city`, `country_code` | Compare station identity and locality |
| `result_type` | Distinguish station/building results from road or area results |
| `rank.confidence`, city/street/building confidence | Inspect confidence at relevant levels |
| `rank.match_type` | Inspect address granularity, not a guarantee of correctness |
| `category`, `place_id`, `datasource` | Preserve identity hints and source attribution |

High confidence in a city result does not establish station coordinates. Fields
may be absent; missing evidence requires review. See the official
[Geoapify response and confidence documentation](https://apidocs.geoapify.com/docs/geocoding/forward-geocoding/).

## Representative sample

The immutable source is `data/fuel-prices.csv`; the prepared sample/results artifact
is [data/geocoding-feasibility.json](../../data/geocoding-feasibility.json).
OPIS IDs are unique, Canadian entries are excluded, and source-row references,
aliases, location fingerprints, and a source checksum are retained. Prices never
participate in fingerprints or queries.

Selection balances region, state, and chain labels, prefers repeated-ID examples
where those counts tie, and breaks remaining ties by numeric OPIS ID. The pilot
interleaves address categories and regions. The source sample covers 26 states:

| Primary address category | Count |
| --- | ---: |
| Exit description | 12 |
| Highway intersection | 8 |
| Road-only/ambiguous description | 6 |
| Local/numbered address | 4 |

Chain labels include Pilot/Flying J, Love's, TA/Petro, Kwik, Circle K, other
recognizable chains, and six independent/other stations. The four geographic
regions are represented. Address-based rural/ambiguous labels are proxies, not
verified population classifications; independent/other is also a heuristic.
This purposive diagnostic sample does not support a nationwide statistical
accuracy estimate. The JSON records every selected station and selection rationale.

## Explicit provisional classification

Automated classifications below are preserved in JSON. Preliminary reviewer
decisions are separate under `manual_review`; they do not rewrite provider evidence
or automatically change the classifier.

**Accepted:** valid finite coordinates; US country and matching state; matching
city; amenity/building-level result; name similarity of at least 0.85 against a
source alias; matching branch number when the source uses `#`; overall confidence
at least 0.95; full/building-level match type. Building results additionally need
building confidence at least 0.95. Multiple distinct accepted locations make the
query ambiguous. These thresholds are spike hypotheses, not calibrated accuracy
guarantees. Accepted results still require manual verification before production use.

**Ambiguous:** street/city/area precision, missing identity/locality/confidence
evidence, uncertain name/branch, confidence below the acceptance threshold, or
multiple plausible locations. Operational failures also remain ambiguous/unresolved
and are identified by error reason; do not count them as incorrect station matches.

**Rejected:** invalid coordinates, explicit country/state mismatch, confidence
below 0.2, or no usable candidates. Candidate-level reasons are preserved even
when the query-level result summarizes several candidates. Primary and fallback
classifications remain separate to allow comparison rather than silently replacing
evidence. Confidence is a provider score, not a measured probability of correctness.

Manual review must inspect at least ten stations, including accepted and problematic
cases when available. Record reviewer decision/evidence alongside the JSON results
and summarize discrepancies here. Check the station/branch against independent
maps or station listings and inspect highway access. Coordinate proximity alone
does not establish road accessibility. Do not choose a route corridor default
from confidence scores alone.

## Usage, credentials, and operation

Required credential: `GEOAPIFY_API_KEY` in the local process environment. The
utility does not automatically load `.env`; arrange environment loading locally
without putting the key in command arguments, committed files, or logs.
No routing/map API credential is needed for the spike itself.

The pilot was executed through a Python wrapper using
`load_dotenv(ROOT / '.env', override=True)` before invoking the utility. This
verified that the process key matched the local file while exposing only a boolean
confirmation. The normal utility still reads the process environment.

The five-station selection covers exit, intersection, road-only, and street-address
descriptions, chains and independent stops, and four US regions. Road-only Carlsbad
is a rural/highway-style address proxy, not a verified rural site; the utility
should not claim it is geographically rural.

The pilot is complete. **Do not rerun or execute the remaining commands without
new approval.** These describe the utility's operation, not an authorization:

```sh
# Five-station pilot; the prepared artifact already exists.
uv run python -m spikes.geocoding --live --limit 5

# After inspecting the pilot, resume the remaining sample.
uv run python -m spikes.geocoding --live --limit 30 --pilot-reviewed

# Optional bounded structured-query fallbacks, within the same cumulative budget.
uv run python -m spikes.geocoding --live --limit 30 --pilot-reviewed --fallbacks
```

Without `--live`, the utility only prepares a sample and refuses to overwrite an
existing artifact. Use `--output` for a new diagnostic artifact. Never reset a
live checkpoint to evade the approved cumulative budget.

Budget: 30 primary queries plus up to ten fallback attempts, **at most 40 total
HTTP attempts including retries**, shared across resumes. One retry at most per
query on transport/5xx failures, two-second backoff, and at least one second
between request starts. Fallback retries also consume the ten-attempt allowance.
Stop the entire run on 401/403/429; do not automatically resume an auth/quota halt.
Resolve the cause before explicitly reviewing any recovery with the same budget.
The five-station pilot needs five attempts normally, up to ten if all retry.
Retries reduce the remaining fallback allowance; the hard cap takes precedence
over completing every query.

Requests are synchronous with bounded connection/read timeouts and redirects
disabled. Latency excludes pacing/backoff. Error codes are recorded without raw
provider error bodies, credential-bearing URLs, or exception messages. Selected
response fields are redacted if the provider echoes the key.

The artifact reserves/counts attempts before HTTP and checkpoints atomically after
responses. Completed responses can be recovered without new requests. An interrupted
attempt stays counted conservatively; a crash after receiving but before saving
can still repeat a query within its retry/budget limits. This is one-writer
diagnostic checkpointing, not a custom persistence system or exactly-once delivery.

Ordinary geocoding costs one credit/request, so allow approximately 40 credits;
the documented free plan has 3,000 credits/day shared with other usage.
[Geoapify pricing](https://www.geoapify.com/geocoding-api/).

## Preliminary five-station findings

Latency is per HTTP attempt, including response parsing/classification but excluding
rate-limit waiting and checkpoint writes: total 30.515 seconds, mean 6.103 seconds,
median 6.617 seconds, range 2.247–11.224 seconds. Observed latency is for station
queries, not a benchmark of endpoint geocoding or the full route-planning API.
The artifact retains full-precision values and every returned candidate.

### Original station identities and top returned matches

Coordinates below use **latitude, longitude**. Overall/city/street/building values
are the corresponding `rank.confidence*` fields; a dash means absent.

| OPIS | Original identity and address | Returned identity/address | Coordinates | Type / match type | Overall / city / street / building | Latency | Preliminary decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 105 | TA SAGINAW I 75 TRAVEL CENTER; I-75, EXIT 144-B; Bridgeport, MI | Bridgeport, Bridgeport Charter Township, MI | 43.3594696, -83.8816364 | suburb / match_by_city_or_disrict | 0.25 / 1 / — / — | 11.224 s | Ambiguous: locality, not station |
| 1028 | FOUR STATES TRUCK STOP; I-495, EXIT 4 & SR-9; New Castle, DE | New Castle, DE | 39.6620572, -75.5663132 | city / match_by_city_or_disrict | 0.25 / 1 / — / — | 6.617 s | Ambiguous: city point, not truck stop |
| 64211 | PILOT #490/WESTERN PETROLEUM; US-180; Carlsbad, NM | US 180, Carlsbad, NM 88220 | 32.3897900, -104.2198350 | street / match_by_street | 0.50 / 1 / 1 / — | 6.647 s | Ambiguous: road point, no station identity |
| 67682 | CASEYS #2739; 1323 E MAIN ST; Beloit, KS | 1323 East Main Street, Beloit, KS 67420; no station name | 39.4588009994, -98.0926878747 | building / full_match | 1 / 1 / 1 / 1 | 2.247 s | Rejected after review: current official branch address conflicts |
| 368 | WILTON TRAVEL PLAZA; I-87, EXIT 16; Gansevoort, NY | Gansevoort, NY | 43.1962051, -73.6513967 | city / match_by_city_or_disrict | 0.25 / 1 / — / — | 3.780 s | Ambiguous: locality, no plaza identity |

### False-positive risks and review evidence

- TA returned two Bridgeport locality candidates plus an unrelated Ohio city
  candidate. The official [TA listing](https://www.ta-petro.com/location/mi/ta-saginaw/)
  supplies a street address at 6364 Dixie Hwy and I-75 Exit 144. No returned
  candidate proves that station position.
- Four States returned New Castle's city point. Alternate candidates were a
  New York bicycle-rental station and an Illinois bus stop, both confidence zero
  and wrong-state. `full_match` on those amenities does not establish identity.
- Pilot returned US 180 plus two other Carlsbad streets with zero overall
  confidence. Its best candidate's city/street confidence of 1 does not identify
  Pilot #490. No independent coordinate verification was performed.
- Casey's returned a building matching the supplied street address with every
  confidence level equal to 1, but no station name. The
  [official branch #2739 listing](https://www.caseys.com/general-store/ks-beloit/3132-us-24-hwy/2739)
  currently gives **3132 US 24 Hwy**, rather than the CSV's **1323 E Main St**.
  This may reflect stale data, relocation, or a source identity error; the pilot
  does not determine which. Reject the match pending reconciliation, rather than
  treating a correctly geocoded address as a confirmed fuel station.
- Wilton returned a Gansevoort locality point plus two Pennsylvania ramp-address
  buildings. Its [own site](https://www.wiltontravelcenter.com/) identifies
  215 Ballard Rd and Exit 16. The first candidate is not a verified plaza location.

Review examined all five responses and all 13 candidates for precision/identity,
plus available official listings. It did not verify station entrances, distances
from returned points to actual stops, or road access on an independent map.
The ten-station manual-review goal for the full sample remains incomplete.

## Recommendation after the pilot

**The current name + highway-description free-form query is inadequate as an
unattended station-location strategy.** Four pilot queries returned coarse
locality/road points; the numbered-address result illustrates a different problem:
high address confidence can coexist with unconfirmed or conflicting station identity.
Five purposively selected cases are diagnostic evidence, not a national accuracy rate.

Before expanding the sample, propose a small separately approved comparison on
these same five stations: cleaned station-name aliases and structured name/city/state
queries, with station-specific/fuel-POI lookup or verified chain street addresses
as subsequent fallbacks. Confirm city/state/branch and fuel-station identity;
preserve coarse results for diagnosis but exclude them from runtime planning.
Handle address conflicts as explicit review items. Do not relax thresholds or
accept city/road points merely to improve the acceptance count. No fallback
queries or strategy changes were executed in this pilot.

The named rural/ambiguous sample category is only an address proxy, and the pilot
does not establish actual rural coverage. The next sampling review should address
that limitation before interpreting performance by rural/urban location.

The source's highway descriptions create a material risk of geocoding roads or
localities rather than the named fuel station. The four local-address examples
provide a comparison group. Identity/branch checks and station-level precision
must take precedence over blindly accepting the first high-confidence result.

Recommended fallback order: cleaned/structured station-name search, manual review
of ambiguous cases, then a separately approved fuel-POI/chain-directory matching
experiment if geocoding is inadequate. Never use city centroids as station locations.
Do not widen the route corridor to compensate for unverified coordinates.

Nationwide preparation would deduplicate to 6,626 US station IDs and persist
status/provenance in SQLite through GNS-6. A primary pass costs approximately
6,626 ordinary geocoding credits before retries/fallbacks, exceeding two daily
free allowances. At one request/second, pacing alone is approximately 110 minutes;
actual elapsed time includes latency and quota scheduling. Applying the pilot's
6.103-second mean illustratively gives roughly 11.2 hours for a sequential primary
pass, before fallbacks/retries, but five cases are too few for a reliable projection
and a revised query strategy may behave differently. Allow at least three
daily quota windows, reserve capacity for runtime/demo traffic, and revise the
estimate after testing the revised strategy on a larger approved sample. Batch geocoding
may reduce credits but requires a separate scope/budget review; do not implement it
in this spike.

Use location fingerprints excluding prices, make HTTP calls outside transactions,
and save reviewed results with short fingerprint-checked writes. Nationwide
enrichment is not approved by implementing this utility. Review the actual sample
findings before deciding that Geoapify alone is sufficient or beginning GNS-6.

## Verification

Mocked tests cover sample diversity, price-independent fingerprints, classifications,
conflicting candidates, budgets, fallback parameters, retries, pacing, error halts,
redaction, malformed responses, safe resumption, and atomic checkpoint replacement.
Run `uv run pytest`; routine tests make no external calls and require no key.

## Approved name-first versus Places comparison

Executed only the same five stations. `spikes/station_comparison.py` has a separate
cumulative **15-additional-attempt** budget, at most five retry attempts total,
and at most one retry per logical query. It makes exactly five structured amenity
geocoding queries and five fuel-POI queries, with no new locality queries, paging,
Place Details, or radius expansion. The original pilot remains at five attempts;
the combined observed total is 15, not 15 new attempts.

Name-first inputs are TA Saginaw, Four States Truck Stop, Pilot #490, Casey's
#2739, and Wilton Travel Plaza, with source city/state and a US filter. Highway
descriptions are omitted. Retain up to five candidates per geocoding request.
Places inputs use `service.vehicle.fuel`, a 10-km circle around the original top
candidate as an approximate locality anchor, `bias=proximity:lon,lat`, and limit 20.
Distance orders retrieval; it never establishes source identity. The anchor is
not promoted to a station coordinate.

The JSON comparison section preserves complete credential-redacted response bodies,
all GeoJSON features and raw source tags, credential-free request parameters,
individual attempt latency/status, candidate counts, truncation flags, and indexed
review annotations. No automatic acceptance occurs. Empty searches remain
inconclusive; full pages are flagged rather than silently treated as exhaustive.

### Observed usage and latency

| Approach | Attempts / estimated credits | Sum of request latency | Mean | Median | Range | Candidates |
| --- | --- | --- | --- | --- | --- | --- |
| Original address-first baseline | 5 / 5 | 30.515 s | 6.103 s | 6.617 s | 2.247–11.224 s | 13 |
| Name-first | 5 / 5 | 13.990 s | 2.798 s | 2.871 s | 2.138–3.770 s | 20 |
| Places | 5 / 5 | 3.742 s | 0.748 s | 0.737 s | 0.614–0.930 s | 74 |

Comparison total: ten additional requests, approximately ten credits, 17.731 s
summed request latency, zero retries, zero HTTP/transport errors; every response
was HTTP 200. Pacing/checkpoint overhead is excluded from the latency totals.
These five cases are not a throughput benchmark or national success estimate.

Places pages for TA, Four States, and Pilot reached 20 candidates and are
potentially truncated. Casey's returned three and Wilton eleven. Four name-first
pages reached their five-result limit; Four States returned none. Those limits
make absence claims unsafe even when a radius contains the actual station.

### Per-station comparison and evidence

"Verified" below means manually corroborated station-site identity/address, not
automatic acceptance or verification of a navigable entrance. The original
classifications and raw comparison responses are unchanged by review annotations.

| OPIS station | Original address-first | Name-first | Places | Combined identity decision |
| --- | --- | --- | --- | --- |
| 105 TA Saginaw | Bridgeport locality; ambiguous | Two TA facility representations at 6364 Dixie Hwy, confidence 0.5 | Unnamed HGV fuel point and named Travel Centers of America at 6364 Dixie Hwy; page truncated | Verified site via official address; exact fuel/entrance point still needs selection |
| 1028 Four States | New Castle city; ambiguous | Empty; inconclusive | Twenty nearby fuel POIs, no reconciled Four States candidate; page truncated | Ambiguous; do not substitute Shell/BP/Wawa |
| 64211 Pilot #490 | US 180 road; ambiguous | Pilot convenience/facility points in Carlsbad, without branch/house number; also wrong-city/state results | Unnamed HGV fuel point on South Canal St among twenty POIs | Ambiguous; strong lead but missing current branch/address evidence in returned points |
| 67682 Casey's #2739 | Building at CSV address; rejected pending conflict resolution | Same-chain East Main St fuel POI, confidence 0; unrelated/wrong-state candidates | Same-chain fuel POI 95 m from disputed anchor, no branch/ref | Ambiguous identity; reject uncorroborated assignment of #2739/CSV price |
| 368 Wilton Travel Plaza | Gansevoort locality; ambiguous | All five candidates unrelated; reject returned matches | Ballard Rd Sunoco and unnamed HGV fuel points, no plaza name/house number | Ambiguous; supplier/locality agreement alone is insufficient |

Name-first query decisions: **one verified, three ambiguous, one rejected**.
Places query decisions: **one verified, four ambiguous, zero rejected queries**;
numerous unrelated individual fuel candidates are rejected. Combined distinct
source stations: **one verified site, four unresolved**, no automatically accepted
coordinates. Rejecting a query's returned matches does not declare the station
nonexistent.

Detailed promising coordinates (latitude, longitude):

- **TA name-first:** 43.351628, -83.869437; second representation
  43.3517117, -83.8690735. Both give 6364 Dixie Highway. The
  [official TA listing](https://www.ta-petro.com/location/mi/ta-saginaw/) gives the
  same address and I-75 Exit 144. The source name's Saginaw/Bridgeport variation
  is supported by that listing. An OSM ref 0198 differs from current business
  #0528: preserve both, never confuse either with OPIS ID 105. Do not count these
  facility representations as separate source stations.
- **TA Places:** unnamed HGV point 43.3520343, -83.8695216 at 6364 Dixie Hwy;
  named Travel Centers of America point 43.3519803, -83.8688854 at the same address
  has `hgv=no`. The latter is not an appropriate diesel/truck-access assumption.
  Identity/address corroboration supports the site, but point/access selection
  remains explicit. The closest result was **Kroger**, not TA.
- **Pilot name-first:** convenience-store point 32.387937, -104.215111
  (confidence 1), plus Pilot Travel Center point 32.3881564, -104.2152807
  (confidence 0). Both lack branch/house number; proximity cannot fill that gap.
  A [New Mexico regulator listing dated 2024-10-04](https://www.rld.nm.gov/wp-content/uploads/2024/10/MSB-Auth-Delegate-List-as-of-Oct-4-2024.pdf)
  independently links Pilot #490 with 3202 S Canal St. The current official
  business page could not be retrieved. The historical branch/address evidence
  is a lead, not current-coordinate verification.
- **Pilot Places:** unnamed `hgv=yes` fuel point 32.3883563, -104.2155318,
  435 m from the anchor. It has no returned operator/branch/house number. Nearby
  Southwest LP Gas, Shell, and Shamrock are not replacements for Pilot #490.
- **Casey's:** name-first and Places share 39.4590896, -98.0916504 on East Main
  St. Raw tags identify Casey's brand/operator but no branch/ref. The
  [official #2739 page](https://www.caseys.com/general-store/ks-beloit/3132-us-24-hwy/2739)
  gives 3132 US 24 Hwy, conflicting with the CSV and returned locality address.
  There is no basis to transfer #2739's price to a nearby same-chain POI.
- **Wilton:** Sunoco 43.1701972, -73.7143524 and unnamed HGV point
  43.169985, -73.7156439 are Ballard Rd leads. The
  [business's site](https://www.wiltontravelcenter.com/) identifies a Sunoco plaza
  at 215 Ballard Rd and Mobil across the road at 216. Returned points lack the
  house number/operator needed to establish which fuel area belongs to the CSV
  station. The closest result was **Stewart's**, 84 m from the locality anchor.
- **Four States:** no reconciled target. A
  [third-party exit directory](https://www.iexitapp.com/Delaware/I-495/Exit%202/492)
  lists 520 Terminal Ave and Exit 2, whereas the CSV says Exit 4. No official
  business listing was found. The limited page ends about 4.56 km from the anchor;
  neither page truncation nor source-address ambiguity can be resolved by accepting
  a nearby unrelated station.

Geocoding's `type=amenity` did not prevent observed building/unrelated results,
and supplied city/state did not exclude every wrong-locality/state candidate.
Validate actual response fields. Branch numbers were sometimes interpreted as
street numbers (e.g. 490 Pilot Street), proving why `full_match` and numbers in
an address cannot be treated as branch verification.

### Revised resolution recommendation and scalability

Use fuel-POI retrieval for candidate discovery and name/alias searches as supporting
evidence. Reconciliation must combine distinctive identity, branch or verified
address, state/locality compatibility, and fuel capability. A chain-name match,
nearest distance, or overlapping endpoint results is insufficient. Both APIs
frequently share OSM source data, so agreement is not independent verification.

Do not deploy the paired per-station strategy nationwide unchanged. For 6,626 US
stations, two requests per station cost about **13,252 credits**, needing at least
five 3,000-credit daily windows before retries, anchor resolution, or pagination.
Without cached locality anchors, one extra request per station raises the worst
case to **19,878 credits**, at least seven daily windows. Even the two-pass credit
floor exceeds a three-day 9,000-credit allowance. Illustratively, applying the
observed means gives about 6.5 hours of sequential HTTP time for the paired pass,
plus pacing and review; five stations cannot establish a reliable national estimate.

A reviewed future enrichment plan should reuse searches by locality/region,
deduplicate physical fuel sites, and use verified chain directories/addresses for
identity reconciliation. Grouped Places search must account for truncated pages
and area coverage; do not simply download the nearest twenty per city and declare
coverage complete. Offline OSM fuel extracts can avoid per-station discovery calls
and retain richer tags, but share coverage/identity gaps with Geoapify's OSM data
and add preparation effort. No OSM extract was downloaded in this comparison.

For unresolved stations, keep status/provenance and review reasons, exclude them
from runtime recommendations, and return explicit coverage/infeasibility errors
when verified stations cannot bridge a trip. Bound manual review to a diagnostic
set; do not promise manual verification of thousands within three days. Any
limited-coverage demonstration or revised enrichment budget needs explicit review.
The ORM/SQLite runtime architecture is unchanged; this work is entirely GNS-5.
No remaining sample stations, nationwide work, or GNS-6 were started.
