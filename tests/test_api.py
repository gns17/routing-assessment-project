from urllib.parse import urlsplit

import httpx
import pytest
from django.core.cache import cache, caches
from django.core.cache.backends.filebased import FileBasedCache
from django.core.cache.backends.locmem import LocMemCache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from routing.geometry import bounds
from routing.models import DatasetState, Station
from routing.planning import plan
from routing.provider import Geoapify, Location, Route
from routing.repository import StationRepository
from tests.test_coordinate_import import artifact, record
from tests.test_importing import import_csv, row, source

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def transport(monkeypatch):
    cache.clear()
    caches["maps"].clear()
    calls = []
    state = {"miles": 900}

    def handler(request):
        calls.append(request)
        assert not connection.in_atomic_block
        if request.url.path.endswith("search"):
            start = request.url.params["text"] == "start"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "country_code": "us",
                            "state_code": "NM",
                            "lat": 35,
                            "lon": -105 if start else -96,
                            "formatted": "Synthetic endpoint",
                            "rank": {"confidence": 1},
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
                            "coordinates": [[-105, 35], [-96, 35]],
                        },
                        "properties": {
                            "distance": state["miles"] * 1609.344,
                            "time": 36000,
                        },
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "routing.views.create_provider", lambda: Geoapify("mock-only", client, cache)
    )
    return calls, state


def accepted_station(tmp_path):
    # Isolated fixture: never added to the real source database or demonstration.
    from django.core.management import call_command

    import_csv(source(tmp_path, [row()]))
    item = Station.objects.get()
    entry = {**record(item), "latitude": 35, "longitude": -101}
    call_command(
        "import_station_coordinates", str(artifact(tmp_path, entry)), reviewed=True
    )
    return item


def request_plan():
    return APIClient().post(
        "/api/route/", {"start": "start", "finish": "finish"}, format="json"
    )


def test_end_to_end_mocked_geometry_fuel_map_and_revision(tmp_path, transport):
    calls, _ = transport
    item = accepted_station(tmp_path)
    response = request_plan()
    assert response.status_code == 200, response.data
    assert len(calls) == 3
    assert response.data["route"]["geometry"]["coordinates"] == [[-105, 35], [-96, 35]]
    assert response.data["gallons_purchased"] == "40.000000"
    assert response.data["gallons_consumed"] == "90.000000"
    assert response.data["initial_tank_cost"] is None
    assert response.data["fuel_stops"][0]["opis_id"] == item.opis_id
    map_response = APIClient().get(urlsplit(response.data["map_url"]).path)
    assert map_response.status_code == 200
    assert (
        b"OpenStreetMap" in map_response.content
        and b"route-data" in map_response.content
    )
    assert b"mock-only" not in map_response.content
    assert request_plan().data["total_fuel_cost"] == response.data["total_fuel_cost"]
    assert len(calls) == 3
    old_revision = response.data["dataset_revision"]
    import_csv(source(tmp_path, [row(price="1.00000000")]))
    changed = request_plan()
    assert changed.data["dataset_revision"] > old_revision
    assert changed.data["total_fuel_cost"] == "40.00"
    assert len(calls) == 3  # Price changes do not invalidate provider caches.


def test_unresolved_records_do_not_enable_infeasible_route(tmp_path, transport):
    import_csv(source(tmp_path, [row()]))
    response = request_plan()
    assert response.status_code == 422
    assert response.data["error"]["code"] == "insufficient_station_coverage"
    assert "total_fuel_cost" not in response.data


def test_short_trip_needs_no_station(transport):
    _, state = transport
    state["miles"] = 100
    response = request_plan()
    assert response.status_code == 200
    assert response.data["total_fuel_cost"] == "0.00"
    assert response.data["gallons_consumed"] == "10.000000"
    assert response.data["ending_gallons"] == "40.000000"


def test_invalid_input_makes_no_http_attempt(transport):
    calls, _ = transport
    response = APIClient().post(
        "/api/route/", {"start": 12, "finish": "finish"}, format="json"
    )
    assert response.status_code == 400 and not calls


def test_expired_map_and_no_admin(transport):
    assert (
        APIClient().get("/maps/00000000-0000-0000-0000-000000000001/").status_code
        == 404
    )
    assert APIClient().get("/admin/").status_code == 404


def test_repository_projects_plain_records_with_two_selects(tmp_path):
    item = accepted_station(tmp_path)
    geometry = {"type": "LineString", "coordinates": [[-105, 35], [-96, 35]]}
    with CaptureQueriesContext(connection) as queries:
        revision, candidates = StationRepository().snapshot(bounds(geometry, 1))
    assert len([q for q in queries if q["sql"].lstrip().startswith("SELECT")]) == 2
    assert revision == DatasetState.objects.get().revision
    assert len(candidates) == 1 and candidates[0].opis_id == item.opis_id
    Station.objects.filter(pk=item.pk).update(enrichment_status="ambiguous")
    assert not StationRepository().snapshot(bounds(geometry, 1))[1]
    Station.objects.filter(pk=item.pk).update(
        enrichment_status="accepted", active=False
    )
    assert not StationRepository().snapshot(bounds(geometry, 1))[1]


def test_two_worker_caches_select_new_dataset_revision(tmp_path):
    from decimal import Decimal

    accepted_station(tmp_path)
    location = Location(35, -105, "Synthetic fixture")
    route = Route(
        location,
        location,
        {"type": "LineString", "coordinates": [[-105, 35], [-96, 35]]},
        Decimal(900),
        36000,
    )
    workers = [LocMemCache(f"worker-{i}", {}) for i in range(2)]
    for worker in workers:
        worker.clear()
    original = [plan(route, StationRepository(), worker, 1) for worker in workers]
    import_csv(source(tmp_path, [row(price="1")]))
    for index, worker in enumerate(workers):
        updated = plan(route, StationRepository(), worker, 1)
        assert updated["dataset_revision"] > original[index]["dataset_revision"]
        assert updated["total_fuel_cost"] == "40.00"


def test_map_snapshot_is_shared_across_local_cache_instances(transport):
    _, state = transport
    state["miles"] = 100
    response = request_plan()
    token = urlsplit(response.data["map_url"]).path.strip("/").split("/")[-1]
    other_worker = FileBasedCache(caches["maps"]._dir, {})
    assert other_worker.get(f"map:{token}")["route"] == response.data["route"]
