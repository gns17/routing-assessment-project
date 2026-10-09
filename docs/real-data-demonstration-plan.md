# Real-data demonstration — original proposal

The bounded route/coordinate investigation was subsequently approved and executed.
See [corridor-investigation.md](corridor-investigation.md) for findings. Coordinate
import remains unapproved; the original pre-execution proposal below is preserved.

This is a proposed investigation, not an executed reconciliation. No new station
identities or coordinates are verified. No dataset downloads, live Geoapify calls
or coordinate imports are authorized by this document. Preserve ORM + SQLite and
the start/finish-only API with its at-most-three-attempt runtime baseline.

## Recommended corridor

Albuquerque, NM → Nashville, TN, expected primarily along I-40. Planning estimate:
roughly **1,200–1,300 driving miles**, to be established by the approved live router
rather than treated as measured. Exceeding 1,000 miles makes at least two positive
refueling purchases necessary with a full 50-gallon starting tank. The actual
provider route, eligible station gaps and listed prices determine whether the
optimizer chooses two, three or more stops; do not force a desired stop count.

Start with **six reviewed stations**, two alternatives per region: Amarillo,
Oklahoma City, and North Little Rock. Target eight only if one pair is unresolved
or poorly situated; Russellville/West Memphis provide possible gap-filling backups.
Approximate anchor positions are 280–300, 540–570 and 850–900 route miles; these are
planning estimates, not geocoded positions. Seek 250–350-mile consecutive gaps and
avoid relying on exactly 500 miles, leaving practical room for access detours
that the baseline model still excludes.

The source CSV has 92 unique IDs in 16 chosen I-40 localities (including off-corridor
sites). This locality shortlist is not true corridor coverage: coordinates are
unknown and locality labels can be misleading. City/exit names cannot establish
that a record lies on the actual driving geometry.

## Candidate source records, all unverified

| OPIS ID | Source name/branch | Source highway description | City/state |
| --- | --- | --- | --- |
| 4446 | LOVES TRAVEL STOP #200 | I-40 EXIT 74 | Amarillo, TX |
| 7733 | FLYING J TRAVEL PLAZA #723 | I-40, EXIT 76 | Amarillo, TX |
| 4227 | LOVES TRAVEL STOP #203 | I-40, EXIT 140 | Oklahoma City, OK |
| 52468 | FLYING J TRAVEL PLAZA #703 | I-40, EXIT 140 | Oklahoma City, OK |
| 6755 | PETRO STOPPING CENTER #326 | I-40, EXIT 161 & SR-391 | North Little Rock, AR |
| 52458 | PILOT TRAVEL CENTER #332 | I-40, EXIT 161 & SR-391 | North Little Rock, AR |

These are exact identities from the supplied CSV, not claims about current business
listings or availability. Several different businesses share exit descriptions;
never choose one merely because it is nearby. Match the numbered branch, chain,
city/state and address/exit evidence; reject renamed/moved/closed or conflicting
sites unless documented historical aliases establish the source identity.

## Verification and bounded execution, after approval

Hard cap **90 minutes** (target 60) for the corridor attempt, independent of other
implementation. Suggested allocation: 10 minutes route confirmation; 45 minutes
up to eight station reviews; 10 minutes reviewed import; 15 minutes integration/
map validation; 10 minutes evidence and demo notes. Stop if the evidence cannot be
established within the cap. Do not restart broad Geoapify station searching.

1. Approve one cold API route: two endpoint geocoding attempts and one driving
   routing attempt, no retries or additional provider details. Save sanitized route
   geometry, step distances, mileage, timing and call count as live evidence.
   If endpoint ambiguity fails or the route differs, stop for review rather than
   spending an open-ended request budget. A cached repeat should add zero calls.
2. Use official Love's, Pilot/Flying J, and TA/Petro numbered location pages to
   corroborate source identity. Preserve URLs, retrieval time, branch number,
   street address and highway/exit relationship. Extract coordinates from listing
   structured data/map links where available; do not use a city or road centroid.
3. Independently cross-check placement against a map/OSM business footprint and
   street/address/entrance evidence. Record map source and position convention
   (forecourt/site versus entrance), coordinate precision, ramp direction and
   uncertainties. Official listings alone may contain imprecise coordinates.
   A second chain listing repeating the same upstream data is not independent
   positional corroboration. OSM identity/address tags are supporting evidence,
   never a proximity-only price join. Browsing a few existing listings/maps does
   not require state extracts or paid station searches, but execute after approval.
4. Accept only an unambiguous branch/address/state match with actual site placement.
   Keep ambiguous/unmatched evidence in a review ledger; do not import it as accepted.
   If multiple OPIS records plausibly describe one site, resolve the identity conflict
   or omit it. Do not invent addresses, aliases or branch correspondence.
5. Build a small reviewed JSON list with OPIS ID, current SQLite location fingerprint,
   latitude/longitude, policy, identity_verified=true, source and evidence (including
   both identity and positional sources). Present the actual artifact for review
   before importing, unless that reviewed import was explicitly included in approval.
6. Use `import_station_coordinates artifact.json --reviewed` for only these records.
   The existing command validates all entries, checks active identity/fingerprint,
   writes accepted coordinates/provenance and revision atomically, and is idempotent.
   It does not alter unrelated stations or seed prices and makes no HTTP requests.
   No full-snapshot import, production synthetic fixtures or broad updates needed.
7. Repeat the same API route from permitted cache, inspect stop ordering, purchased
   quantities/cost, inventory, geometry and browser map; verify actual call counts.
   Check station approach/detour manually and clearly retain model approximations.

Proposed live Geoapify budget: **three HTTP attempts total, no retries**. Additional
requests need new approval. Reserve **eight credits conservatively** for two
one-credit geocodes plus one approximately 1,930–2,090 km driving route, based on
[current published pricing](https://www.geoapify.com/pricing-details/) with a
500-km long-distance component. The routing documentation/examples differ in
rounding presentation, so this is a budget allowance, not a claimed exact debit;
confirm account usage before/after. No additional details or avoid options are
requested. The runtime three-call target concerns calls, not credits. Provider
latency and actual route quality will be measured only during that approved run.

## Coverage measurement and legitimate claims

Maintain a small ledger for all selected OPIS IDs: identity evidence/status,
coordinate evidence/status, import eligibility, corridor offset/position and
exclusion reason. Report selected/reviewed/imported counts separately from unique
stations actually matched to the returned geometry. Inventory constraints use
matched route visits, not every imported station.

For the confirmed route, measure start → first station, every successive station
and last station → finish. Report largest gap and every interval over 500 miles;
use both the API coverage diagnostics and manual map review. Report unresolved
records in the chosen city/state/highway shortlist and why they were omitted.
Do not claim that all geographically nearby missing CSV stations are known:
without coordinates, an exhaustive corridor denominator is impossible.

Legitimate claim: optimized fuel purchases among the **reviewed subset** on the
provider's fixed route using the CSV snapshot and approved tank assumptions.
It is not a global/nationwide optimum, an optimum over all 6,626 IDs, a live price
quote, or a detour-inclusive/access-verified navigation plan. Preserve min/max
price ambiguity, unknown initial tank cost and interpolation/access limitations.
If verified candidates cannot bridge the route, return/report the explicit gap;
never assign a CSV price to an unrelated POI to make the demonstration pass.

## Relation to GNS-12

New Mexico OSM extraction can assess future reconciliation methodology but cannot
supply Amarillo/Oklahoma City/Arkansas stations needed for this multi-stop corridor.
Its dependency/setup/download costs are less direct than six official branch
reviews. Recommend leaving GNS-12 Backlog/nonblocking and prioritizing this corridor
investigation after approval. No issue H scope/dependency change is made here;
a separate proposal is needed before re-scoping Linear. Michigan/national extracts
and further paid station searches remain excluded.

Fallback at the time cap: demonstrate a genuine short route requiring no purchased
fuel and a longer route's truthful coverage error, alongside labeled mocked
multi-stop tests. This demonstrates behavior but does **not** satisfy a real-world
multi-stop success; acknowledge that submission gap rather than implying completion.
