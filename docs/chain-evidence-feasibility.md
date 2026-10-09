# Official-chain evidence follow-up — New Mexico only

**Yes: usable research coverage improves substantially when official station
identity/coordinates lead reconciliation, with independent evidence and review.**
The result supports a bounded, manually reviewed chain-specific extension (choice C),
not nationwide unattended acceptance (choice B). No coordinates were imported and
the functioning six-station/$232.44 production demonstration remains unchanged.

Authorized 90-minute window: **2026-10-09 22:22:26–23:52:26 UTC**. Progress checked
at about 48 minutes: measurable improvement justified finishing the audit/report.
No further collection is needed. Exact completion and resource summary are in the
scratch summary. Deadline remains October 11, 2026, 16:55 GMT−3 / 19:55 UTC.
GNS-12's original findings/history stay intact; this separately authorized follow-up
does not reverse production rules, import its five sites or authorize national work.

## Why this differs from GNS-12

GNS-12 required strong identity primarily from OSM tags. Its fuel geometry was often
real, but locality/ref tags were missing or inconsistent. The new generator first
joins OPIS records to **official identities** using exact published OPIS IDs or
chain + branch + city/state, plus highway-exit consistency where provided. Only then
does it compare explicit official site coordinates to independently mapped fuel POIs.
Missing OSM branch/locality fields do not defeat stronger external identity evidence.

Three public directory templates were exercised: [Love's](https://www.loves.com/locations/nm/milan/loves-travel-stop-milan-257),
[Pilot/Flying J/ONE9](https://locations.pilotflyingj.com/us/nm/jamestown/1-giant-crossing),
and [Maverik](https://locations.maverik.com/nm/albuquerque/9701-bluewater-rd-nw).
Love's pages expose OPIS IDs, branch, complete address and JSON-LD coordinates.
Pilot-family pages expose branch/address/exit and visible station coordinates.
Maverik pages expose branch/address and explicit main-location data coordinates.
These are business-directory points, not geocoding-confidence scores; their correctness
still needs corroboration. No existing threshold was simply lowered to increase yield.

Public robots policies allowed the selected paths. Collection used an identifying
research agent, one request per second per host minimum, no retries and no JS/map API
execution. A 401/403/429 stops the host; no access controls were bypassed. Responses
other than 200 were excluded, including two 500s, three 404s and one unconsumed redirect.
Love's Milan reused its prior successful GNS-12 HTML after the new 500, with cache
provenance; missing pages are inconclusive, not proof of closure. Broader harvesting
or redistribution requires checking applicable source terms; robots permission is
not a blanket data license.

## Isolated pipeline and explicit gates

`spikes/chain_evidence.py` is pure Python, not imported by production. It consumes
sanitized official records and the existing 1,021 fuel objects for 107 NM OPIS IDs.
It makes no HTTP/ORM calls, assigns no OSM prices, and writes only research output
outside the repository. An external temporary collector preserved source HTML,
checksums, request ledger and parser inputs; no new runtime dependency was added.

1. **Identity:** allowlisted HTTPS official domain/family; exact direct OPIS and
   branch where present, otherwise exact chain/branch/locality. Wrong explicit
   OPIS, branch or state is rejected. City/chain or a coordinate alone cannot pass.
2. **Location:** complete official street and an explicit site-coordinate source.
   Viewport/centroid/geocoder-provenance points are refused. State/bounds and exit
   contradictions require review. A single parsed main coordinate is required for
   Pilot/Maverik; sources/templates with ambiguous fields must not be trusted.
3. **Physical corroboration:** only `amenity=fuel` nodes/ways, never roads/towns.
   Named matching-chain fuel geometry must agree within 60 m; unnamed geometry
   within 30 m. This is a *new research site-agreement policy*, not the production
   road corridor. Product-only labels at dealers do not prove identity. Unrelated
   named businesses, branch/state/locality conflicts and competing source claims
   block automatic confidence. All objects/evidence/reasons are retained.
4. **Canonical point:** official business-site point, not an arbitrarily selected
   closest OSM object. Multiple canopies may corroborate one official station;
   a competing official business claim is not silently collapsed.
5. **Review:** the generator never emits Verified. Manual triangulation uses held-out
   government facility identity/address/coordinates, not the same directory/OSM
   evidence alone. Cases lacking fuel geometry can be manually corroborated through
   separate station-specific government coordinates; they are not made automatic
   highs by widening the 60 m bound.

Spelling/leading-zero normalization is explicit. No global branch-prefix stripping
or inferred nearby-town alias exists. Historically documented differences were
examined: government Pilot #305/current Flying J #305; ONE9's dealer/legal-business
name and product-brand distinctions; older/current street numbers. An exact facility
ID plus independent site coordinates can support a **documented manual** reconciliation.
This does not establish reusable national alias rules. Allsup's #2392/#102392 and
Speedway #9117/#47106 remain examples requiring a sourced, record-specific crosswalk;
unsupported directories/number changes were not guessed into matches.

## Measured coverage

Collection parsed **39 official site records**, yielding source-backed proposals
for **31 of 107 OPIS records**. Eight parsed directory entries lacked a corresponding
CSV identity or served other branches: no original CSV price was assigned to them.
The generator produced **23 high-confidence proposals**: two were already in the
five verified GNS-12 sites; **21 were new beyond GNS-12's verified/high union**.
GNS-12's automatic-only yield was six, so new evidence materially improves discovery.

After independent review, preserving prior findings:

| Station category | GNS-12 baseline | Follow-up |
| --- | ---: | ---: |
| Verified research site | 5 / 4.67% | **26 / 24.30%** |
| High-confidence, not independently verified | 2 / 1.87% | **2 / 1.87%** |
| Approximate/ambiguous/unresolved | 99 / 92.52% | **79 / 73.83%** |
| Rejected station-coordinate proposal | 1 / 0.93% | 0 at final station level |

Verified increases by **21 records / 19.63 percentage points**. Verified/high union
increases from 7 to **28 / 26.17%**. These are research outcomes, not accepted database
records; production still has **six resolved / 6,620 unresolved**. The five GNS-12
sites remain unapproved for import. The rejected old Maverik #740 OSM point remains
rejected; a different, authoritative coordinate is independently recovered, explaining
the change in station-level rejection count. Rejected evidence is not discarded.

## Independent quality audit

Initial purposive 20-case sample was extended to **26** to include every new high
proposal and five borderline cases, covering all three source families, network
dealers, urban/rural locations, I-10/I-25/I-40 and eastern NM, missing OSM tags,
street-number differences, failed geometry checks and the prior bad-coordinate case.
This is not a random sample or a national accuracy study.

Held-out evidence came from [NMED's public tank-facility register](https://www.env.nm.gov/petroleum_storage_tank/wp-content/uploads/sites/20/2025/10/Active-Storage-Tanks-10-14-2025.pdf)
and [NMED's independent GIS facility layer](https://mercator.env.nm.gov/server/rest/services/pstb/petroleum_storage_tank_facilities/FeatureServer/1).
Facility IDs, current/historical business labels, complete addresses and coordinates
were compared manually. Government observations were **not** used to generate or tune
the automatic results. Their reported points may represent tanks rather than storefronts;
they do not certify entrances, fuel grade, hours, current prices or surveyed accuracy.
Different publishers do not prove statistically independent measurement errors:
the government may use self-reported/geocoded locations. This is cross-source site
corroboration, not an on-site survey or a quantified national error guarantee.

Outcome: **21 research sites corroborated; five unresolved**. Among the 21 new
automatic highs, **17 were corroborated and four downgraded**. Four initially borderline
proposals became manually corroborated using new independent evidence. No generated
high was *proved* to be the wrong business; four remain inconclusive, so this is not
100% precision or a bounded nationwide false-positive rate.

| OPIS / site | Held-out facility | Point difference | Audit conclusion |
| --- | ---: | ---: | --- |
| 1632 Pilot #266, Las Cruces | 29969 | 37.8 m | Verified |
| 2922 Love's #210, Albuquerque | 29166 | 82.6 m | Verified site; 2200/2201 street numbers documented, not silently equated |
| 6218 Love's #215, Gallup | 29172 | 59.6 m | Verified |
| 7080 ONE9 #1422, Moriarty | 47369 | 14.7 m | Verified; official dealer/branch + independently named legal business/address/site, not Phillips 66 brand alone |
| 7228 Maverik #638, Albuquerque | 28027 | 46.1 m | Verified |
| 52659 Love's #276, Lordsburg | 29165 | 39.7 m | Verified |
| 63597 Pilot #163, Lordsburg | 29970 | about 50 m | Verified site; documented historic 1050/current 1124 street numbering |
| 64122 Flying J #691, Tucumcari | 54615 | 69.2 m | Verified |
| 68928 Pilot #475, Moriarty | 54795 | 9.9 m | Verified; street 305 was not confused with Flying J branch 305 |
| 69133 Pilot #557, Hobbs | 54830 | 35.7 m | Verified |
| 69745 Pilot #1070, Santa Rosa | 54873 | 3.3 m | Verified |
| 70079 Pilot #1118, Clovis | 54903 | 10.8 m | Verified |
| 70190 Love's #726, Belen | 54909 | 51.0 m | Verified |
| 70236 Love's #733, Las Vegas | 54932 | 12.4 m | Verified |
| 70309 Pilot #1165, Jal | 54929 | 33.4 m | Verified site; property/entrance numbering 410/422 documented |
| 71264 Maverik #649, Albuquerque | 54974 | 4.9 m | Verified site; corner-property street names differ and are documented |
| 71514 Love's #817, Santa Teresa | 55001 | 94.0 m | Verified site, not highway entrance |
| 1596 Flying J #305, Jamestown | 1358 | 187.4 m | Downgraded; exact site/campus-anchor distinction unresolved |
| 20027 Love's #262, Tucumcari | 54606 | 167.0 m | Downgraded; 262A/262 and campus-anchor difference unresolved |
| 70405 Love's #760, Eunice | 54946 | **35.49 km** | Downgraded; government point duplicates unrelated Jal Pilot #1165 despite Eunice address |
| 71536 Pilot #1106, Albuquerque | 54990 | 120.1 m | Downgraded pending site-boundary interpretation |
| 7225 Love's #329, Clovis | 27518 | 52.6 m | Verified manually despite missing qualifying OSM geometry |
| 20024 Love's #259, Las Cruces | 29169 | 22.1 m | Verified manually; street numbers 8993/9005 documented |
| 52553 Flying J #689, Albuquerque | 28068 | 72.6 m | Verified manually; no widening of automatic geometry bound |
| 63613 Flying J #690, Lordsburg | 54588 | 394.4 m | Remains ambiguous; location/campus/source error unresolved |
| 73043 Maverik #740, Las Vegas | 55059 | 66.2 m | New official point verified; old OSM node remains rejected 1.076 km away |

Concrete error patterns: misplaced OSM nodes; government copy/paste coordinates;
branch/address-number confusion; historic naming versus network/product brands;
different anchors in large truck-stop sites; redirects/missing directories; multiple
canopies; street-corner/postal numbering. Numeric coordinate precision does not establish
accuracy. The government point with a correct identity/address but wrong location
shows why neither official nor government coordinates should be adopted blindly.

## Geographic and fuel-route benefit

The combined 26 manually corroborated NM sites span **15 cities**, including I-10
(Lordsburg/Las Cruces), I-25 (Belen/Las Vegas), I-40 (Gallup/Moriarty/Santa Rosa/
Tucumcari) and southeastern sites (Hobbs/Jal). This improves distribution over GNS-12's
north/central concentration, not just coordinate counts. Source streets/IDs remain
bound to the original OPIS prices; current directory prices were not substituted.

Using saved real route/step mileage and unchanged pure services, a counterfactual
with **only the 21 newly reviewed sites** plus the existing production six gives:

- **11 matched stations**, including five new NM positions at miles 2.804020,
  39.375580, 40.279479, 119.170205 and 176.456782. Offsets 0.078–0.241 mile.
- Five purchases, adding ONE9 #1422 (OPIS 7080), 4.027948 gallons near mile 40.28.
- **$232.07** modeled purchased cost versus $232.44 baseline; same total fuel
  purchased. Approximate saving **$0.38** before display rounding.
- Existing 500-mile feasibility is retained; it was already feasible. Later sparse
  gaps outside NM remain. No newly feasible long-distance route is proven because
  no new driving-route request was made.

This is **offline hypothetical evidence**, not a real API response or an approved
import. The five older NM research sites are excluded from that counterfactual;
they remain unapproved. If approved later, importing just the new 21 would make
27 accepted production records, not nationwide coverage. Entrances/detours, small
fills, zero-stop-penalty objective and fixed-price assumptions are unchanged. A new
stop to save pennies may not be operationally worthwhile; no optimizer changes made.

## Workload, network and scaling

Direct operations: **58 recorded official-page attempts**, 52 HTTP 200; four robots
reads; one 397,564-byte government PDF; one government schema read and three bounded
facility queries. Total **67 direct network operations**, plus separately performed
web source/documentation searches and the isolated PDF-reader installation; this is
not an exhaustive all-network HTTP ledger. No Geoapify, driving-route, matrix,
Google-map API or paid-service requests. No new OSM extract was downloaded.
Collector took **69.5 s**, enforcing at least one second per host between requests.
Matching 107 records / 39 sources / 1,021 reused POIs took **0.032 s** in a measured
fresh process. Observed process RSS **51,691,520 bytes (~49.30 MiB)** includes diagnostic
setup; not a peak measurement of every separate collector/PDF process. Raw HTML,
government data, intermediates and machine-readable audit remain outside Git.

Only **three parsers**, ordinary Python/JSON, simple identity gates and plain objects
were needed. `pypdf` was installed solely in the preexisting temporary research
environment; project dependencies/lockfile unchanged. No persistence framework or
background worker was introduced. The simpler evidence strategy, rather than a lower
OSM threshold or more infrastructure, explains the gain.

In the actual 6,626-row US seed, named records in the exercised families total
**1,375 (20.75%)**: Love's 549; Pilot 438; Flying J 194; ONE9 74; Maverik 120.
This is a **targetable ceiling by CSV name**, not verified coverage or predicted
match yield. Old/renumbered/closed stores, affiliates, records without public detail
pages and missing geometry may fail. Do not extrapolate national precision from NM.

Public state/city/detail hierarchies and structured site fields appear reusable.
For those named records, roughly 1,500–3,000 detail/directory requests might be needed,
depending on batching/cache and city overhead. At one request/second per host this
means tens of minutes to hours, source failures/terms permitting; zero Geoapify
credits, but real bandwidth and maintenance cost. Generalizing/validating three
collectors, aliases, cached source provenance and a review queue is **roughly 1–3
engineering days**, not a guaranteed before-deadline national solution. State-specific
held-out registries vary and can contain errors. Independent manual review at an
illustrative 2–5 minutes for 1,375 sites would take **46–115 hours**; measured NM
audit throughput is not a human/national productivity guarantee. Use simple spatial
grids/name/branch dictionaries for larger POI sets; no PostGIS or new service needed.

Nationwide OSM/download/enrichment was not executed. Official identity data alone
does not prove a complete 500-mile priced network. Additional long-route feasibility
requires real driving geometry and reviewed sites along its gaps; straight-line
links, town positions and large counts are insufficient.

## Integration choices — proposals only

| Choice | Exact proposed scope | Trade-off / effort |
| --- | --- | --- |
| **A: retain six approved sites** | No production changes. Preserve current snapshot/demo and disclose incomplete US coverage. | Lowest delivery risk; foregoes proven research breadth. Appropriate if no further review/import time is approved. |
| **B: accept strong automated sites** | Add explicit model evidence level (`manual_verified`, `strong_automated`) and check constraints/current fingerprints; migrate existing six as manual. Extend importer to validate structured official ID/branch/address/coordinate provenance, independent geometry, conflicts, review method and stale-source policy without falsely setting manual verification. Explicit repository policy decides which levels are eligible; all matching/optimization still use plain objects. Add per-stop evidence labels, eligible counts by level and qualified coverage warnings to API/map/docs. Increment shared revision on eligibility/evidence changes; test rollback, conflicting claims, corrupted sources, defaults excluding automatic records and cross-worker cache invalidation. | **Not recommended for submission.** Changes acceptance policy/schema/API and requires policy approval plus meaningful independent validation; roughly 1–2 engineering days, potentially more auditing. No national error bound established. |
| **C: chain-specific, manually reviewed subset** | After user review, prepare artifacts for some/all of the **new 21** with current source fingerprints and full evidence under existing `--reviewed` gate. Keep original CSV/identity/prices; do not overwrite current six or include older five without separate approval. Dry-run, atomic/idempotent import, revision/cache checks and isolated regression/fresh setup. | **Recommended only as a bounded follow-up after approval**, approximately **2–4 hours** including final individual review and integration checks. No models/migrations, importer acceptance relaxation, repository rule or optimizer change required. |

For C, existing metadata's `source`, `evidence` and policy string can retain directory
and registry IDs/URLs, coordinate source, object links and discrepancies. No new API
contract field is required while every eligible point is still manually verified;
update reviewed counts, warnings/docs/fixtures and fresh-import instructions, and
add tests for the new accepted artifact and hypothetical five-stop plan. Existing
six-only fixture remains a $232.44 regression; extended fixture gets its own expected
plan. A new approved live/browser verification would be needed before representing
extended results as live. Automated directory collection remains offline preparation.

Do **not** turn C into nationwide data collection before the deadline. If its review,
coordinate gate and regression work cannot fit while reserving recording/submission
time, choose A. The benefit shown is truthful geographic breadth and a modest modeled
price improvement; it still does not satisfy arbitrary-US station coverage. Stop at
this decision gate. No production change, import, commit/push, new issue, submission
package edit or Loom action has been performed in this follow-up.

## Evidence / replay

Temporary research directory: `/tmp/spotter-chain-nm-20261009`. Key evidence files:
`network.json`, `robots.json`, `sources.json`, `final-raw-results.json`, `audit.json`,
`new21-route-diagnostic.json`, `metrics.json` and final `summary.json`. The government
observations are held out from generation. Code/test additions are uncommitted for
review; raw source/intermediate data remains outside Git.

```sh
uv run python -m spikes.chain_evidence \
  --sources /tmp/spotter-chain-nm-20261009/sources.json \
  --osm-results /tmp/spotter-nm-osm-20261009/results.json \
  --output /tmp/spotter-chain-nm-20261009/replay.json
uv run pytest tests/test_chain_evidence.py -q
```

Source files explicitly preserve per-proposal identity evidence, canonical official
point, all nearby fuel objects, contradictions, uncertainty and manual-review state.
They are not reviewed importer artifacts and cannot authorize station writes.

Final checks: **180 tests pass (162 baseline + 18 research tests)**; Ruff, relevant
formatting, Django system checks, migration-drift and whitespace checks pass.
Database, original CSV, existing six-coordinate artifact, dependency files and all
submission/Loom-document hashes match the pre-experiment checkpoint. Only the new
prototype, tests and this report are repository additions, uncommitted for review.
OSM data reused from GNS-12 is © OpenStreetMap contributors, ODbL; IDs/provenance remain
in the external research artifacts. Scratch footprint is approximately 9.7 MB for
this follow-up, excluding the unchanged reused extract/temporary environment.
