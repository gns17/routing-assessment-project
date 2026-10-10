# Reviewer Postman setup

1. Follow the root README: `uv sync --locked`, migrate, import the original CSV,
   dry-run/import `data/corridor-reviewed-coordinates.json`. The committed locality
   snapshot is already available; do not import town points as station coordinates.
2. Set your own `GEOAPIFY_API_KEY` in local `.env` for live use, then run
   `uv run python manage.py runserver 127.0.0.1:8000 --noreload`.
3. Postman → Import → select `spotter-routing.postman_collection.json` here.
4. Set collection variable `base_url` to the server URL (no trailing slash).
   No API credentials or application authentication belong in Postman.
5. Send the three named requests in order: strict reviewed success, strict
   Atlanta–Miami coverage failure, then opt-in conditional scenario.
6. Open each successful request's freshly returned `map_url` in a browser.

Sending requests can consume Geoapify credits. A cold sequence normally makes six
provider attempts: three for each distinct route; the Atlanta strict/opt-in pair
shares geocoding and driving geometry. No station enrichment or retries occur.
Project-agent recording/live runs need separate explicit approval; none are
performed by importing this collection. Do not use unattended collection runners
or repeat cold requests during recording. Keep one worker alive for warm repeats.

Assertions check status, contracts, identity/price ownership, modeled range and
inventory, coverage and warnings. `assert_recorded_snapshot` defaults to `false`:
provider geometry can change. Set it to `true` only when checking the committed
saved-response examples ($232.44 strict, $48.66 conditional). Tests deliberately
ignore latency and the random/expiring map ID. A changed snapshot deserves review,
not silently replacing an output with an old screenshot.

Credential-free, zero-network regression reproduction:

```sh
uv run pytest tests/test_recorded_corridor.py tests/test_recorded_best_effort.py -q
```

Those tests exercise actual DRF/ORM business logic with saved real provider replies
and isolated station data. They are recorded replay, not a new live request.
Postman/desktop-agent availability must be confirmed before recording; this
repository does not install Postman or extra dependencies.
