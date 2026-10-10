"""Real reviewed fixture + recorded HTTP replies, isolated SQLite; never live HTTP."""

import json
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


def test_recorded_real_corridor_with_reviewed_orm_stations(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    live = json.loads((root / "data/corridor-route.json").read_text())
    import_csv(root / "data/fuel-prices.csv")
    prices = dict(Station.objects.values_list("opis_id", "price"))
    calls = []

    def handler(request):
        calls.append(request.url.path)
        reply = (
            next(
                a
                for a in live["attempts"][:2]
                if a["params"]["text"] == request.url.params["text"]
            )
            if request.url.path.endswith("search")
            else live["attempts"][2]
        )
        return httpx.Response(reply["status_code"], json=reply["response"])

    cache.clear()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(
            "routing.views.create_provider",
            lambda: Geoapify("recorded-test-only", client, cache),
        )
        api = APIClient()
        body = {"start": live["start"], "finish": live["finish"]}
        assert api.post("/api/route/", body, format="json").status_code == 422
        call_command(
            "import_station_coordinates",
            str(root / "data/corridor-reviewed-coordinates.json"),
            reviewed=True,
        )
        response = api.post("/api/route/", body, format="json")
        assert response.status_code == 200
        data = response.data
        assert data["distance_miles"] == "1221.630055"
        assert data["route"]["geometry"] == live["normalized_route"]["geometry"]
        assert data["mileage_method"] == "provider_steps"
        assert data["coverage"]["matched_stations"] == 6
        assert data["coverage"]["largest_gap_miles"] == "350.879358"
        assert data["coverage"]["unbridgeable_gaps"] == []
        assert data["coverage"]["scope"] == "reviewed_candidates_only"
        assert data["coverage"]["complete_csv_coverage"] is False
        assert [s["opis_id"] for s in data["fuel_stops"]] == [4446, 7733, 52468, 6755]
        assert data["total_fuel_cost"] == "232.44"
        assert data["gallons_purchased"] == "72.163006"
        assert data["gallons_consumed"] == "122.163006"
        assert data["fuel_stops"][1]["gallons_purchased"] == "0.211942"
        assert data["dataset_revision"] == DatasetState.objects.get().revision == 2
        assert dict(Station.objects.values_list("opis_id", "price")) == prices
        assert Station.objects.filter(enrichment_status="accepted").count() == 6
        assert Station.objects.filter(latitude__isnull=True).count() == 6620
        assert api.get(urlsplit(data["map_url"]).path).status_code == 200
        assert (
            api.post("/api/route/", body, format="json").data["total_fuel_cost"]
            == "232.44"
        )
        assert len(calls) == 3  # Recorded replies only; no repeats after import/cache.
