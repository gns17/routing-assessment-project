# Delivery publication verification

No new features, architecture changes, live Geoapify requests, coordinate imports,
recording, submission or GitHub permission changes were made in this phase.
The only presentation change replaces raw popup provenance JSON with readable
source/locality/method/uncertainty labels. The API and strict-mode display logic
remain unchanged; existing strict regressions and the updated popup check pass.

## Reproducible application checks

- Working tree: **224 tests passed**. The additional 12 tests are pending unrelated
  research and are not included in the published delivery commits.
- Isolated archive of the committed application/evidence: **212 tests passed**.
- Ruff, relevant Python formatting, Django system checks, migration-drift and
  Git diff checks passed. Credential/URL/artifact scans found no publishable secrets.
- Locked dependencies installed offline from the local cache; no new dependencies.
- Fresh SQLite migrations and original CSV import created 6,626 US stations.
  Six-site reviewed dry run/import produced exactly six accepted sites, revision 2.
  The committed locality snapshot was available without downloads or imports.
- Actual local Django WSGI/DRF requests against that fresh database, with recorded
  real provider transport, reproduced strict **200/$232.44**, strict Atlanta–Miami
  **422**, and best-effort **200/$48.66**. Both generated map pages returned 200
  and contained the exact response payload. Six recorded replies, zero external
  Geoapify attempts; no existing development database, `.env` or research-file access.

The temporary-path guard needed macOS `/tmp` canonicalization before the local
HTTP reproduction could start. No request was made by the failed guard; it was a
verification-script correction, not an application defect.

[Fresh setup measurements](../data/delivery-fresh-setup-verification.json) explicitly
label these as recorded replay, not another live-provider run. The source/evidence
checkout was `b6e88f4`; the final documentation commit does not change application code.

## Map and Postman

Actual Chrome/Leaflet replay of the saved live Atlanta–Miami response shows readable
Census labels, exact route geometry, conditional cost, original candidate identities,
all warnings, a hollow Adel indicator and attribution. Final passive screenshot
check: 15 tiles, zero console/network errors, no Geoapify requests. Original live
evidence and the later readable-popup screenshot are both retained and labeled.

The portable Postman collection has three requests and configurable `base_url`.
Its 14 assertion groups across normal/snapshot settings were evaluated with the
saved API responses in an offline JavaScript harness; this is not claimed to be an
actual Postman desktop run. Assertions ignore random map IDs and latency, preserve
conditional semantics and check identity-specific prices/inventory. Exact expected
snapshot values are optional because future driving geometry may change.

## Publication and delivery gates

Publish only to `origin/feat/assessment-implementation` in the intended private
repository. No force push, rebase, squash or main merge is authorized. Full provider
payloads and complete API contracts are retained; the shortened independent-review
copy and pending New Mexico/falsification research remain uncommitted.

Read-only GitHub checks show private visibility and owner-only collaborator listing.
Reviewer access must be confirmed/authorized; it has not been established merely
by publishing the branch. Postman desktop was not found in standard system/user
application locations; confirm desktop/agent availability before recording.

Loom/checklist/package now include both modes, historical prices, reviewed-subset
limits, locality associations (not station geocodes), unknown access and fragile
zero-fuel arrivals. Both modes are reproducible offline, but a recording using new
live preflight requires separate request-budget approval. Current budgets are exhausted.
GNS-11 remains In Progress. Recording and submission require separate approvals.
Deadline: **October 11, 2026, 16:55 GMT−3 (19:55 UTC)**.

[Machine-readable verification](../data/delivery-verification.json).
