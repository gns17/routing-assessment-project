"""Regression and integration evidence; all coordinates/providers are synthetic."""

import json
from decimal import Decimal

import httpx
import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from routing.geometry import Candidate, match_stations
from routing.models import DatasetState, Station
from routing.planning import plan
from routing.provider import Geoapify, Location, ProviderError, Route, road_weights
from routing.repository import StationRepository
from tests.test_api import request_plan
from tests.test_coordinate_import import record
from tests.test_geometry import line, station
from tests.test_importing import import_csv, row, source
from tests.test_provider import geo

pytestmark = pytest.mark.django_db(transaction=True)
pytest_plugins = ("tests.test_api",)


def test_out_and_back_preserves_visits_even_when_adjacent_segments_match():
    geometry = line([[-101, 35], [-99, 35], [-101, 35]])
    matches = match_stations(geometry, Decimal(800), [station()], 1)
    assert [m.miles for m in matches] == [Decimal(200), Decimal(600)]


def test_step_weights_change_chainage_without_changing_geometry():
    geometry = line([[-101, 35], [-100, 35], [-99, 35]])
    weights = (Decimal(300), Decimal(700))
    matches = match_stations(geometry, Decimal(1000), [station()], 1, weights)
    assert len(matches) == 1 and matches[0].miles == 300
    assert match_stations(geometry, Decimal(1000), [station()], 1)[0].miles == 500


def test_road_weights_multiple_legs_and_altitude():
    geometry = {
        "type": "MultiLineString",
        "coordinates": [
            [[-101, 35, 100], [-100, 35, 110]],
            [[-100, 35, 110], [-99, 35, 120]],
        ],
    }
    properties = {
        "legs": [
            {"steps": [{"from_index": 0, "to_index": 1, "distance": 482803.2}]},
            {"steps": [{"from_index": 0, "to_index": 1, "distance": 1126540.8}]},
        ]
    }
    weights = road_weights(geometry, properties, Decimal(1000))
    assert weights == (Decimal(300), Decimal(700))
    assert (
        match_stations(geometry, Decimal(1000), [station()], 1, weights)[0].miles == 300
    )


@pytest.mark.parametrize(
    "steps",
    [
        [{"from_index": 0, "to_index": 3, "distance": 160934.4}],
        [{"from_index": 1, "to_index": 2, "distance": 160934.4}],
        [{"from_index": 0, "to_index": 1, "distance": 160934.4}],
        [{"from_index": 0, "to_index": 2, "distance": 999}],
        [{"from_index": 0, "to_index": 2, "distance": float("nan")}],
    ],
)
def test_inconsistent_provider_steps_are_rejected(steps):
    with pytest.raises(ValueError):
        road_weights(
            line([[-101, 35], [-100, 35], [-99, 35]]),
            {"legs": [{"steps": steps}]},
            Decimal(100),
        )


def test_provider_normalizes_step_mileage_and_cache():
    from django.core.cache.backends.locmem import LocMemCache

    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("search"):
            return httpx.Response(
                200,
                json={
                    "results": [
                        geo(lon=-101 if request.url.params["text"] == "a" else -99)
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": line([[-101, 35], [-100, 35], [-99, 35]]),
                        "properties": {
                            "distance": 1609344,
                            "time": 1000,
                            "legs": [
                                {
                                    "steps": [
                                        {
                                            "from_index": 0,
                                            "to_index": 1,
                                            "distance": 482803.2,
                                        },
                                        {
                                            "from_index": 1,
                                            "to_index": 2,
                                            "distance": 1126540.8,
                                        },
                                    ]
                                }
                            ],
                        },
                    }
                ]
            },
        )

    local = LocMemCache("step-normalization", {})
    local.clear()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with Geoapify("mock-key", client, local) as provider:
        route = provider.route("a", "b")
        assert provider.calls == 3 and route.segment_miles == (
            Decimal(300),
            Decimal(700),
        )
    with Geoapify("mock-key", client, local) as provider:
        assert provider.route("a", "b").segment_miles == route.segment_miles
        assert provider.calls == 0


@pytest.mark.parametrize(
    "prices,total,stop_count", [([4, 2, 3], "220.00", 2), ([4, 2, 1], "210.00", 3)]
)
def test_multiple_purchases_inventory_order_and_contract(
    tmp_path, transport, prices, total, stop_count
):
    _, state = transport
    state["miles"] = 1300
    import_csv(
        source(
            tmp_path,
            [row(opis=i + 1, price=str(price)) for i, price in enumerate(prices)],
        )
    )
    entries = [
        {**record(s), "latitude": 35, "longitude": -105 + 9 * (400 * (i + 1) / 1300)}
        for i, s in enumerate(Station.objects.order_by("opis_id"))
    ]
    # Mock geometry spans 9 degrees and 1300 miles: stations at 400/800/1200.
    artifact = tmp_path / "isolated-test-only.json"
    artifact.write_text(json.dumps(entries))
    call_command("import_station_coordinates", str(artifact), reviewed=True)
    response = request_plan()
    assert response.status_code == 200, response.data
    data = response.data
    assert data["total_fuel_cost"] == total
    assert (
        data["gallons_consumed"] == "130.000000"
        and data["gallons_purchased"] == "80.000000"
    )
    assert len(data["fuel_stops"]) == stop_count
    assert [Decimal(s["route_miles"]) for s in data["fuel_stops"]] == sorted(
        Decimal(s["route_miles"]) for s in data["fuel_stops"]
    )
    assert all(
        0 <= Decimal(s["arrival_gallons"]) <= Decimal(s["departure_gallons"]) <= 50
        for s in data["fuel_stops"]
    )
    assert data["coverage"]["matched_stations"] == 3
    assert (
        not data["coverage"]["unbridgeable_gaps"]
        and not data["coverage"]["complete_csv_coverage"]
    )
    assert data["dataset_revision"] == DatasetState.objects.get().revision


def test_incomplete_coverage_reports_exact_gap(transport):
    response = request_plan()
    details = response.data["error"]["details"]
    assert response.status_code == 422
    assert details["coverage"]["unbridgeable_gaps"] == [
        {"from_miles": "0.000000", "to_miles": "900.000000", "gap_miles": "900.000000"}
    ]
    assert details["coverage"]["matched_stations"] == 0


def test_cached_plan_changes_when_step_distribution_changes():
    class Repository:
        def snapshot(self, _):
            return 7, [
                Candidate(1, "Synthetic", "test", "test", "NM", Decimal(3), 35, -100)
            ]

    cache.clear()
    point = Location(35, -101, "Synthetic endpoint")
    route = Route(
        point,
        point,
        line([[-101, 35], [-100, 35], [-99, 35]]),
        Decimal(900),
        1000,
        (Decimal(400), Decimal(500)),
    )
    assert plan(route, Repository(), cache, 1)["total_fuel_cost"] == "120.00"
    changed = Route(
        point,
        point,
        route.geometry,
        route.distance_miles,
        route.duration_seconds,
        (Decimal(300), Decimal(600)),
    )
    with pytest.raises(ProviderError, match="coverage"):
        plan(changed, Repository(), cache, 1)


def test_map_safely_embeds_untrusted_station_name(tmp_path, transport):
    import_csv(source(tmp_path, [row(name='</script><script>alert("test")</script>')]))
    item = Station.objects.get()
    artifact = tmp_path / "test.json"
    artifact.write_text(
        json.dumps([{**record(item), "latitude": 35, "longitude": -101}])
    )
    call_command("import_station_coordinates", str(artifact), reviewed=True)
    response = request_plan()
    from urllib.parse import urlsplit

    html = APIClient().get(urlsplit(response.data["map_url"]).path).content
    assert b"</script><script>alert" not in html
    assert b"\\u003C/script\\u003E" in html and b"label.textContent" in html


def test_malformed_geocoding_state_is_unresolved_not_unhandled():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"results": [{**geo(), "state_code": []}]}
            )
        )
    )
    with (
        Geoapify("mock-only", client) as provider,
        pytest.raises(ProviderError) as error,
    ):
        provider.geocode("test")
    assert error.value.status == 422


@pytest.mark.parametrize("properties", [None, [], "bad"])
def test_malformed_route_properties_are_safely_rejected(properties):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("search"):
            return httpx.Response(
                200, json={"results": [geo(lon=-101 if len(calls) == 1 else -99)]}
            )
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": line([[-101, 35], [-99, 35]]),
                        "properties": properties,
                    }
                ]
            },
        )

    with (
        Geoapify(
            "mock-only", httpx.Client(transport=httpx.MockTransport(handler))
        ) as provider,
        pytest.raises(ProviderError) as error,
    ):
        provider.route("a", "b")
    assert error.value.code == "provider_response" and len(calls) == 3


def test_inflight_snapshot_is_never_cached_under_new_revision(tmp_path):
    from tests.test_api import accepted_station

    accepted_station(tmp_path)
    cache.clear()
    point = Location(35, -105, "Test")
    route = Route(point, point, line([[-105, 35], [-96, 35]]), Decimal(900), 1000)
    before = DatasetState.objects.get().revision

    class UpdatingRepository:
        def snapshot(self, box):
            snapshot = StationRepository().snapshot(box)
            import_csv(source(tmp_path, [row(price="1")]))
            return snapshot

    old = plan(route, UpdatingRepository(), cache, 1)
    new = plan(route, StationRepository(), cache, 1)
    assert old["dataset_revision"] == before and new["dataset_revision"] > before
    assert (
        new["total_fuel_cost"] == "40.00"
        and old["total_fuel_cost"] != new["total_fuel_cost"]
    )
