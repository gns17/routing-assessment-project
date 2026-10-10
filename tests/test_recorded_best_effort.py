"""Live Atlanta–Miami capture replayed offline with a fresh ORM dataset, never HTTP."""

import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from routing.importing import import_csv
from routing.models import DatasetState, Station
from routing.provider import Geoapify

pytestmark = pytest.mark.django_db(transaction=True)


def test_recorded_atlanta_miami_with_committed_localities_and_six_sites(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    responses = [
        json.loads(
            (root / f"data/best-effort-live-provider-response-{n}.json").read_text()
        )
        for n in (1, 2, 3)
    ]
    expected = json.loads(
        (root / "data/best-effort-live-api-response.json").read_text()
    )
    import_csv(root / "data/fuel-prices.csv")
    call_command(
        "import_station_coordinates",
        str(root / "data/corridor-reviewed-coordinates.json"),
        reviewed=True,
    )
    before = list(Station.objects.order_by("opis_id").values())
    calls = []

    def handler(request):
        assert len(calls) < 3
        index = len(calls)
        if index < 2:
            assert request.url.path == "/v1/geocode/search"
            assert request.url.params["text"] == ["Atlanta, GA", "Miami, FL"][index]
        else:
            assert request.url.path == "/v1/routing"
        calls.append(request.url.path)
        return httpx.Response(200, json=responses[index])

    cache.clear()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(
            "routing.views.create_provider",
            lambda: Geoapify("recorded-test-only", client, cache),
        )
        api = APIClient()
        body = {"start": "Atlanta, GA", "finish": "Miami, FL"}
        strict = api.post("/api/route/", body, format="json")
        assert strict.status_code == 422
        assert strict.data["error"]["code"] == "insufficient_station_coverage"
        response = api.post(
            "/api/route/", {**body, "allow_estimates": True}, format="json"
        )
        assert response.status_code == 200
        actual = {k: v for k, v in response.data.items() if k != "map_url"}
        assert actual == expected
        assert actual["fuel_stops"] == [] and actual["total_fuel_cost"] is None
        assert actual["fuel_feasibility"] == "unverified"
        assert actual["estimated_fuel_expenditure"] == "48.66"
        scenario = actual["conditional_scenario"]
        assert scenario["ending_gallons"] == "0.000000"
        assert abs(
            Decimal(50)
            + Decimal(scenario["gallons_purchased"])
            - Decimal(actual["gallons_consumed"])
        ) <= Decimal("0.000001")
        area = actual["approximate_fueling_areas"][0]
        assert (
            area["label"] == "Adel, GA"
            and area["modeled_price_candidate_opis_id"] == 70429
        )
        assert not area["navigation_destination"]
        assert area["location_quality"] == "locality_approximation"
        assert Decimal(area["modeled_arrival_gallons"]) >= 0
        assert Decimal(area["modeled_departure_gallons"]) <= 50
        page = api.get(urlsplit(response.data["map_url"]).path)
        assert page.status_code == 200
        text = page.content.decode()
        assert "This is not a station location or verified entrance." in text
        assert (
            "Coordinate method:" in text
            and "JSON.stringify(item.provenance)" not in text
        )
        assert api.post("/api/route/", body, format="json").status_code == 422
        assert (
            len(calls) == 3
        )  # Recorded replies; strict/fallback share the route cache.
    assert list(Station.objects.order_by("opis_id").values()) == before
    assert Station.objects.filter(enrichment_status="accepted").count() == 6
    assert DatasetState.objects.get().revision == 2
