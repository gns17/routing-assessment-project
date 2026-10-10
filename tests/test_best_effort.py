"""Synthetic fixtures unless explicitly labeled recorded; never live HTTP or real DB writes."""

import io
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from rest_framework.test import APIClient

from routing.best_effort import (
    SeedStation,
    conservative_check,
    locations,
    plan_best_effort,
    reference_inventory,
)
from routing.fallback_data import FallbackDataError, LocationCatalog, content_version
from routing.fuel import FuelStation, optimize
from routing.geometry import Candidate, Match
from routing.models import DatasetState, Station
from routing.provider import Location, ProviderError, Route
from routing.repository import BestEffortRepository
from tests.test_api import accepted_station
from tests.test_importing import import_csv, row, source

pytestmark = pytest.mark.django_db(transaction=True)
pytest_plugins = ("tests.test_api",)
ROOT = Path(__file__).resolve().parents[1]


def document(points=None, estimates=None):
    doc = {
        "schema_version": 1,
        "localities": points or [],
        "station_estimates": estimates or [],
        "provenance": {
            "synthetic_fixture": True,
            "provider": "synthetic unit fixtures",
        },
    }
    doc["version"] = content_version(doc)
    return doc


def point(city="Carlsbad", state="NM", latitude=35, longitude=-101):
    return {
        "city": city,
        "state": state,
        "latitude": latitude,
        "longitude": longitude,
        "source": {
            "url": "https://example.invalid/synthetic-localities",
            "coordinate_method": "SYNTHETIC TEST ONLY",
        },
    }


def catalog(tmp_path, points=None, estimates=None):
    path = tmp_path / "hints.json"
    path.write_text(json.dumps(document(points, estimates)))
    return LocationCatalog.read(path)


def inject_catalog(monkeypatch, tmp_path, points=None, estimates=None):
    value = catalog(tmp_path, points or [point()], estimates)
    monkeypatch.setattr("routing.views.get_location_catalog", lambda: value)
    return value


def request(allow="absent"):
    body = {"start": "start", "finish": "finish"}
    if allow != "absent":
        body["allow_estimates"] = allow
    return APIClient().post("/api/route/", body, format="json")


def seed(opis=1, city="Synthetic City", state="TX", price="3", fingerprint="a" * 64):
    return SeedStation(
        opis,
        f"SYNTHETIC FUEL {opis}",
        "Test only",
        city,
        state,
        Decimal(price),
        fingerprint,
        None,
        None,
        "pending",
        "",
        "",
        {},
    )


def synthetic_route(geometry=None, miles="900"):
    return Route(
        Location(35, -105, "Synthetic start"),
        Location(35, -96, "Synthetic finish"),
        geometry or {"type": "LineString", "coordinates": [[-105, 35], [-96, 35]]},
        Decimal(miles),
        50000,
    )


def repository(stations, revision=1):
    return Mock(snapshot=Mock(return_value=(revision, stations)))


def test_strict_absent_and_false_remain_identical(tmp_path, transport):
    accepted_station(tmp_path)
    absent = request()
    explicit = request(False)
    assert absent.status_code == explicit.status_code == 200
    assert {k: v for k, v in absent.data.items() if k != "map_url"} == {
        k: v for k, v in explicit.data.items() if k != "map_url"
    }
    assert "planning_mode" not in explicit.data


def test_strict_success_with_opt_in_never_loads_hints(tmp_path, transport, monkeypatch):
    accepted_station(tmp_path)
    monkeypatch.setattr(
        "routing.views.get_location_catalog",
        Mock(side_effect=AssertionError("Do not replace strict success")),
    )
    response = request(True)
    assert response.status_code == 200 and "planning_mode" not in response.data


def test_strict_failure_opt_in_returns_conditional_areas_and_safe_map(
    tmp_path, transport, monkeypatch
):
    import_csv(source(tmp_path, [row(name="<script>unsafe</script>")]))
    before = list(Station.objects.values())
    inject_catalog(monkeypatch, tmp_path)
    assert request().status_code == 422
    response = request(True)
    assert response.status_code == 200, response.data
    data = response.data
    assert data["planning_mode"] == "best_effort" and data["status"] == "estimated"
    assert data["fuel_feasibility"] == "unverified"
    assert data["fuel_stops"] == [] and data["total_fuel_cost"] is None
    assert data["gallons_purchased"] is None
    area = data["approximate_fueling_areas"][0]
    assert area["location_quality"] == "locality_approximation"
    assert not area["uncertainty"]["station_position_known"]
    assert area["uncertainty"]["route_mile_bound"] is None
    assert "latitude" not in area["candidate_stations"][0]
    assert area["modeled_price_candidate_opis_id"] == Station.objects.get().opis_id
    assert data["coverage"]["complete_csv_coverage"] is False
    assert list(Station.objects.values()) == before
    page = APIClient().get(urlsplit(data["map_url"]).path).content.decode()
    assert "APPROXIMATE FUELING AREA" in page and "UNVERIFIED" in page
    assert "textContent" in page and "unverified_driving_feasibility" in page
    assert "<script>unsafe</script>" not in page and "OpenStreetMap" in page


@pytest.mark.parametrize("value", ["true", 1, None, [], {}])
def test_non_boolean_opt_in_rejected_without_provider(transport, value):
    calls, _ = transport
    assert request(value).status_code == 400
    assert not calls


@pytest.mark.parametrize(
    "code,status",
    [("provider_timeout", 504), ("provider_auth", 502), ("location_not_resolved", 422)],
)
def test_provider_failure_never_invokes_best_effort(monkeypatch, code, status):
    provider = Mock()
    provider.__enter__ = Mock(return_value=provider)
    provider.__exit__ = Mock(return_value=None)
    provider.route.side_effect = ProviderError(code, "Synthetic error", status)
    monkeypatch.setattr("routing.views.create_provider", lambda: provider)
    fallback = Mock(side_effect=AssertionError("No fallback on provider errors"))
    monkeypatch.setattr("routing.views.get_location_catalog", fallback)
    response = request(True)
    assert response.status_code == status and response.data["error"]["code"] == code
    fallback.assert_not_called()


def test_unrelated_planner_failure_never_invokes_fallback(transport, monkeypatch):
    monkeypatch.setattr(
        "routing.views.plan",
        Mock(side_effect=ProviderError("other_failure", "Test", 502)),
    )
    fallback = Mock(side_effect=AssertionError())
    monkeypatch.setattr("routing.views.get_location_catalog", fallback)
    assert request(True).data["error"]["code"] == "other_failure"
    fallback.assert_not_called()


def test_missing_data_and_no_guidance_are_structured_failures(
    tmp_path, transport, monkeypatch
):
    monkeypatch.setattr(
        "routing.views.get_location_catalog",
        Mock(side_effect=FallbackDataError("missing")),
    )
    response = request(True)
    assert response.status_code == 500
    assert response.data["error"]["code"] == "best_effort_data_unavailable"
    inject_catalog(monkeypatch, tmp_path, points=[point()])
    response = request(True)  # No CSV rows in this isolated database.
    assert response.status_code == 422
    assert response.data["error"]["code"] == "insufficient_best_effort_coverage"
    assert response.data["error"]["details"]["fuel_feasibility"] == "unverified"


@pytest.mark.parametrize("contents", [None, '{"schema_version":1}'])
def test_missing_or_invalid_deployment_data_is_server_error(
    contents, tmp_path, transport, monkeypatch
):
    path = tmp_path / "private-server-hints.json"
    if contents is not None:
        path.write_text(contents)
    monkeypatch.setattr(
        "routing.views.get_location_catalog", lambda: LocationCatalog.read(path)
    )
    response = request(True)
    assert response.status_code == 500
    assert response.data["error"]["code"] == "best_effort_data_unavailable"
    assert response.data["error"]["details"] == {
        "planning_mode": "best_effort",
        "status": "unavailable",
        "fuel_feasibility": "unverified",
        "strict_failure": "insufficient_station_coverage",
    }
    assert str(path) not in json.dumps(response.data)
    assert "map_url" not in response.data
    assert "Retry-After" not in response


def test_shared_town_is_one_scenario_area_and_prices_keep_opis_ids(
    tmp_path, transport, monkeypatch
):
    import_csv(source(tmp_path, [row(opis=7, price="4"), row(opis=8, price="3")]))
    inject_catalog(monkeypatch, tmp_path)
    data = request(True).data
    assert data["coverage"]["unique_location_hints"] == 1
    assert len(data["conditional_scenario"]["purchases"]) == 1
    area = data["approximate_fueling_areas"][0]
    assert area["modeled_price_candidate_opis_id"] == 8
    assert {
        s["opis_id"]: s["price_per_gallon"] for s in area["candidate_stations"]
    } == {7: "4.00000000", 8: "3.00000000"}
    assert data["coverage"]["candidate_counts"]["locality_approximation"] == 2


def estimate(station, longitude=-101, bound=None, access=None):
    return {
        "opis_id": station.opis_id,
        "location_fingerprint": station.fingerprint,
        "location_quality": "estimated_physical_station",
        "identity_supported": True,
        "latitude": 35,
        "longitude": longitude,
        "contradictions": [],
        "source": {
            "url": "https://example.invalid/synthetic-poi",
            "coordinate_method": "synthetic fuel POI",
            "license": "synthetic unit fixture only",
        },
        "evidence": "SYNTHETIC unique branch/address fixture, not a real CSV match",
        "uncertainty": {"independently_verified": False, "access_verified": False},
        "route_mile_uncertainty": bound,
        "access_detour_bound_miles": access,
        "bound_evidence": "SYNTHETIC bound only"
        if bound is not None or access is not None
        else None,
    }


def test_estimated_sites_are_not_promoted_and_stale_fingerprints_excluded(tmp_path):
    station = seed(city="Carlsbad", state="NM")
    cat = catalog(tmp_path, [point()], [estimate(station)])
    hints, stale = locations([station], cat)
    assert hints[0].quality == "estimated_physical_station" and not station.verified
    assert not hints[0].payload()["uncertainty"]["station_position_known"]
    assert hints[0].payload()["provenance"]["identity_evidence"].startswith("SYNTHETIC")
    hints, stale = locations([replace(station, fingerprint="b" * 64)], cat)
    assert stale == 1 and hints[0].quality == "locality_approximation"


@pytest.mark.parametrize(
    "city,state,coords",
    [
        ("Synthetic NY town", "NY", [[-77, 41], [-70, 41]]),
        ("Synthetic TX town", "TX", [[-106, 31], [-98, 31]]),
        ("Synthetic GA town", "GA", [[-87, 32], [-80, 32]]),
    ],
)
def test_multiregion_synthetic_scenarios_never_guarantee_range(
    tmp_path, city, state, coords
):
    loc = point(city, state, coords[0][1], (coords[0][0] + coords[1][0]) / 2)
    route = synthetic_route({"type": "LineString", "coordinates": coords}, "800")
    cat = catalog(tmp_path, [loc])
    result = plan_best_effort(
        route, repository([seed(city=city, state=state)]), LocMemCache(city, {}), cat
    )
    assert result["fuel_feasibility"] == "unverified"
    assert result["conditional_scenario"]["uncertainty_check"]["status"] == "unknown"
    assert result["estimated_fuel_expenditure"] == "90.00"


def test_approximate_intermediate_deficit_cannot_be_verified(tmp_path):
    route = Decimal(1100)
    mathematical = optimize(
        route,
        [
            FuelStation("high", Decimal(400), Decimal(4)),
            FuelStation("low", Decimal(800), Decimal(3)),
        ],
    )
    replay = reference_inventory(
        route, mathematical.purchases, {"high": Decimal(400), "low": Decimal("800.1")}
    )
    assert (
        replay["valid"] is False and replay["reason"] == "reference_inventory_violation"
    )
    a, b = seed(1, "A", "NM", "4"), seed(2, "B", "NM", "3")
    cat = catalog(
        tmp_path,
        [point("A", longitude=-101.727272727), point("B", longitude=-98.454545454)],
    )
    result = plan_best_effort(
        synthetic_route(miles="1100"),
        repository([a, b]),
        LocMemCache("deficit", {}),
        cat,
    )
    assert result["fuel_feasibility"] == "unverified"


def test_conservative_bounds_reject_known_negative_inventory_even_unused_unknown_hint(
    tmp_path,
):
    station = seed()
    cat = catalog(tmp_path, estimates=[estimate(station, bound=0.1, access=0)])
    loc = locations([station], cat)[0][0]
    match = Match(
        Candidate(0, "Synthetic", "", "", "", Decimal(3), 35, -101), Decimal(500), 0
    )
    purchase = optimize(
        Decimal(900), [FuelStation("0", Decimal(500), Decimal(3))]
    ).purchases
    result = conservative_check(Decimal(900), purchase, {"0": (match, loc)})
    assert result["status"] == "violated"


def test_cache_keys_cover_revision_location_version_and_do_not_pollute_strict(
    tmp_path, transport, monkeypatch
):
    calls, _ = transport
    import_csv(source(tmp_path, [row(price="3")]))
    inject_catalog(monkeypatch, tmp_path)
    first = request(True).data
    assert request().status_code == 422
    assert (
        request(True).data["estimated_fuel_expenditure"]
        == first["estimated_fuel_expenditure"]
    )
    import_csv(source(tmp_path, [row(price="2")]))
    second = request(True).data
    assert second["dataset_revision"] > first["dataset_revision"]
    assert second["estimated_fuel_expenditure"] != first["estimated_fuel_expenditure"]
    newer = inject_catalog(monkeypatch, tmp_path, points=[point(longitude=-100.9)])
    third = request(True).data
    assert (
        third["location_data_version"]
        == newer.version
        != first["location_data_version"]
    )
    assert third["approximate_fueling_areas"][0]["assumed_point"]["longitude"] == -100.9
    assert len(calls) == 3  # Provider geometry is mode-independent and shared.


def test_offline_preparation_ambiguous_keys_and_no_orm_writes(tmp_path):
    seed_csv = source(tmp_path, [row(city="Example", state="TX")])
    text = "USPS|GEOID|NAME|INTPTLAT|INTPTLONG\nTX|48001|Example city|31|-101\n"
    gaz = tmp_path / "synthetic-2025.txt"
    gaz.write_text(text)
    output = tmp_path / "prepared.json"
    queries = []

    def observe(execute, sql, params, many, context):
        queries.append(sql)
        return execute(sql, params, many, context)

    with connection.execute_wrapper(observe):
        call_command(
            "prepare_best_effort_locations",
            str(gaz),
            csv=seed_csv,
            output=output,
            stdout=io.StringIO(),
        )
    assert not queries
    one = LocationCatalog.read(output)
    assert len(one.localities) == 1
    gaz.write_text(text + "TX|48002|Example town|32|-102\n")
    call_command(
        "prepare_best_effort_locations",
        str(gaz),
        csv=seed_csv,
        output=output,
        stdout=io.StringIO(),
    )
    assert not LocationCatalog.read(output).localities
    preserved = output.read_bytes()
    gaz.write_text("bad input")
    with pytest.raises(CommandError):
        call_command(
            "prepare_best_effort_locations", str(gaz), csv=seed_csv, output=output
        )
    assert output.read_bytes() == preserved


def test_corrupt_version_duplicate_town_or_estimate_conflicts_fail_closed(tmp_path):
    path = tmp_path / "bad.json"
    for doc in [
        document([point(), point()]),
        document(
            estimates=[{**estimate(seed()), "contradictions": ["branch conflict"]}]
        ),
    ]:
        path.write_text(json.dumps(doc))
        with pytest.raises(FallbackDataError):
            LocationCatalog.read(path)
    doc = document([point()])
    doc["version"] = "invalid"
    path.write_text(json.dumps(doc))
    with pytest.raises(FallbackDataError):
        LocationCatalog.read(path)


def test_orm_best_effort_snapshot_does_not_change_station_data(tmp_path):
    import_csv(source(tmp_path, [row()]))
    before = list(Station.objects.values())
    revision, stations = BestEffortRepository().snapshot()
    assert revision == DatasetState.objects.get().revision and len(stations) == 1
    assert list(Station.objects.values()) == before and not stations[0].verified


def test_api_estimated_physical_site_retains_evidence_without_orm_promotion(
    tmp_path, transport, monkeypatch
):
    import_csv(source(tmp_path, [row()]))
    _, stations = BestEffortRepository().snapshot()
    entry = estimate(stations[0])
    inject_catalog(monkeypatch, tmp_path, estimates=[entry])
    response = request(True)
    assert response.status_code == 200
    purchase = response.data["conditional_scenario"]["purchases"][0]
    assert purchase["location_quality"] == "estimated_physical_station"
    assert purchase["provenance"]["source"] == entry["source"]
    assert purchase["provenance"]["uncertainty_evidence"] == entry["uncertainty"]
    assert purchase["navigation_destination"] is False
    assert response.data["approximate_fueling_areas"] == []
    station = Station.objects.get()
    assert station.enrichment_status == "pending" and station.latitude is None


def test_real_census_artifact_matches_source_and_is_not_station_geometry():
    # Public locality facts and immutable seed identities; no reference-site labels.
    from routing.importing import parse_csv

    prepared = LocationCatalog.read(ROOT / "data/best-effort-locations.json")
    records, _, _ = parse_csv(ROOT / "data/fuel-prices.csv")
    from routing.fallback_data import locality_key

    usable = [
        r
        for r in records.values()
        if locality_key(r["city"], r["state"]) in prepared.localities
    ]
    assert len(prepared.localities) == 3493 and len(usable) == 6144
    assert not prepared.station_estimates
    assert len({p["state"] for p in prepared.localities.values()}) == 47
    assert all(
        "NOT station site" in p["source"]["coordinate_method"]
        for p in prepared.localities.values()
    )


def test_recorded_falsification_quantities_fail_at_reviewed_site_positions():
    # Saved real-route mileage + observed town-point policy ablation. No city
    # point is being imported or claimed as an actual station coordinate.
    from routing.importing import parse_csv

    seed_rows, _, _ = parse_csv(ROOT / "data/fuel-prices.csv")
    distance = Decimal("1221.630055476020042949176807")
    assumed = {
        7080: "39.174840",
        4446: "287.144666",
        52468: "543.262607",
        6755: "876.827482",
    }
    reference = {
        7080: "40.279479",
        4446: "290.859611",
        52468: "533.416479",
        6755: "884.396169",
    }
    conditional = optimize(
        distance,
        [
            FuelStation(str(i), Decimal(m), seed_rows[i]["price"])
            for i, m in assumed.items()
        ],
    )
    assert conditional.ending_gallons == 0
    outcome = reference_inventory(
        distance,
        conditional.purchases,
        {str(i): Decimal(m) for i, m in reference.items()},
    )
    assert outcome["valid"] is False
    assert Decimal(outcome["arrival_gallons"]) == Decimal("-0.7568687")


def test_api_rejects_scenario_when_supplied_bounds_cross_initial_range(
    tmp_path, transport, monkeypatch
):
    import_csv(source(tmp_path, [row()]))
    _, stations = BestEffortRepository().snapshot()
    entry = estimate(stations[0], longitude=-100, bound=0.1, access=0)
    inject_catalog(monkeypatch, tmp_path, estimates=[entry])
    response = request(True)
    assert response.status_code == 422
    assert response.data["error"]["code"] == "uncertain_fuel_plan_rejected"
    assert response.data["error"]["details"]["fuel_feasibility"] == "unverified"
    assert Station.objects.get().enrichment_status == "pending"


def test_two_csv_town_records_on_revisited_route_do_not_create_independent_area_stops(
    tmp_path,
):
    # SYNTHETIC out-and-back geometry; do not invent multiple independent cities.
    route = synthetic_route(
        {"type": "LineString", "coordinates": [[-105, 35], [-96, 35], [-105, 35]]},
        "800",
    )
    cat = catalog(tmp_path, [point("Synthetic City", "TX", longitude=-100.5)])
    rows = [seed(1), seed(2, price="4")]
    with pytest.raises(ProviderError) as failure:
        plan_best_effort(route, repository(rows), LocMemCache("repeat-area", {}), cat)
    assert failure.value.code == "insufficient_best_effort_coverage"
    assert failure.value.details["coverage"]["matched_location_hints"] == 1
    assert (
        failure.value.details["coverage"]["route_candidate_counts"][
            "locality_approximation"
        ]
        == 2
    )
    assert failure.value.details["fuel_feasibility"] == "unverified"
