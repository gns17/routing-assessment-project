"""Local synthetic API benchmark. Always uses a disposable SQLite database.

No live HTTP, no production coordinate writes; run as a separate Python process.
"""

import argparse
import json
import os
import platform
import resource
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path
from unittest.mock import patch

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    if not 3 <= args.repetitions <= 20:
        parser.error("Use 3–20 repetitions")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.conf import settings

    with tempfile.TemporaryDirectory(
        prefix="synthetic-routing-benchmark-"
    ) as directory:
        # Configure the disposable DB before Django/model initialization.
        settings.DATABASES["default"]["NAME"] = str(Path(directory) / "test.sqlite3")
        settings.CACHES["maps"]["LOCATION"] = str(Path(directory) / "maps")
        import django

        django.setup()
        from django.core.cache import cache, caches
        from django.core.management import call_command
        from django.db import connection
        from django.db.models import F
        from django.test.utils import CaptureQueriesContext
        from rest_framework.test import APIClient

        from routing.importing import import_csv
        from routing.models import Station
        from routing.provider import Geoapify

        assert Path(connection.settings_dict["NAME"]).parent == Path(directory)
        call_command("migrate", verbosity=0)
        import_csv(settings.BASE_DIR / "data/fuel-prices.csv", full_snapshot=True)
        stations = list(Station.objects.all().order_by("opis_id"))
        for index, station in enumerate(stations):
            # Synthetic locations spanning a route bounding box; never real matches.
            station.latitude = 35 + (index % 7) * 0.01
            station.longitude = -110 + (index % 2000) * 0.005
            station.enrichment_status = "accepted"
            station.enrichment_fingerprint = station.location_fingerprint
            station.enrichment_policy = "synthetic-benchmark-only"
        Station.objects.bulk_update(
            stations,
            [
                "latitude",
                "longitude",
                "enrichment_status",
                "enrichment_fingerprint",
                "enrichment_policy",
            ],
            batch_size=200,
        )
        report = {
            "fixture_type": "synthetic_only_disposable_database",
            "real_provider_requests": 0,
            "station_count": len(stations),
            "repetitions": args.repetitions,
            "python": platform.python_version(),
            "platform": platform.system(),
            "workloads": [],
        }
        for name, miles, segments in [
            ("short", 200, 250),
            ("multiple_stops", 1300, 2000),
            ("large_geometry", 2600, 5000),
        ]:
            calls = []
            end = -110 + (5 if name == "short" else 10)
            coordinates = [
                [-110 + (end + 110) * i / segments, 35] for i in range(segments + 1)
            ]

            def handler(
                request, calls=calls, end=end, coordinates=coordinates, miles=miles
            ):
                calls.append(request)
                if request.url.path.endswith("search"):
                    return httpx.Response(
                        200,
                        json={
                            "results": [
                                {
                                    "lat": 35,
                                    "lon": -110
                                    if request.url.params["text"] == "start"
                                    else end,
                                    "country_code": "us",
                                    "state_code": "NM",
                                    "rank": {"confidence": 1},
                                    "formatted": "Synthetic benchmark endpoint",
                                }
                            ]
                        },
                    )
                return httpx.Response(
                    200,
                    json={
                        "features": [
                            {
                                "geometry": {
                                    "type": "LineString",
                                    "coordinates": coordinates,
                                },
                                "properties": {
                                    "distance": miles * 1609.344,
                                    "time": miles * 60,
                                },
                            }
                        ]
                    },
                )

            client = httpx.Client(transport=httpx.MockTransport(handler))
            api = APIClient()
            cold, warm, select_counts = [], [], []
            tracemalloc.start()
            with patch(
                "routing.views.create_provider",
                lambda client=client: Geoapify("mock-only", client, cache),
            ):
                for _ in range(args.repetitions):
                    cache.clear()
                    caches["maps"].clear()
                    start = time.perf_counter()
                    with CaptureQueriesContext(connection) as queries:
                        response = api.post(
                            "/api/route/",
                            {"start": "start", "finish": "finish"},
                            format="json",
                        )
                    cold.append((time.perf_counter() - start) * 1000)
                    select_counts.append(
                        sum(q["sql"].lstrip().startswith("SELECT") for q in queries)
                    )
                    assert response.status_code == 200
                    start = time.perf_counter()
                    assert (
                        api.post(
                            "/api/route/",
                            {"start": "start", "finish": "finish"},
                            format="json",
                        ).status_code
                        == 200
                    )
                    warm.append((time.perf_counter() - start) * 1000)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            report["workloads"].append(
                {
                    "name": name,
                    "route_miles": miles,
                    "segments": segments,
                    "eligible_candidates": response.data["coverage"][
                        "eligible_candidates"
                    ],
                    "matched_stations": response.data["coverage"]["matched_stations"],
                    "fuel_stops": len(response.data["fuel_stops"]),
                    "payload_bytes": len(response.content),
                    "cold_median_ms": round(statistics.median(cold), 3),
                    "cold_max_ms": round(max(cold), 3),
                    "warm_median_ms": round(statistics.median(warm), 3),
                    "warm_max_ms": round(max(warm), 3),
                    "select_counts": select_counts,
                    "mock_http_attempts": len(calls),
                    "python_peak_mib": round(peak / 1024**2, 3),
                }
            )
            client.close()
        query = Station.objects.filter(
            active=True,
            enrichment_status="accepted",
            enrichment_fingerprint=F("location_fingerprint"),
            latitude__range=(34.98, 35.02),
            longitude__range=(-110.1, -99.9),
        ).exclude(enrichment_policy="")
        report["sqlite_query_plan"] = query.explain()
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report["process_peak_rss_mib"] = round(
            rss / (1024**2 if platform.system() == "Darwin" else 1024), 3
        )
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
