"""Static provider credit in both saved-response map modes; no external requests."""

import json
import re
import uuid
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.core.cache import caches
from django.urls import reverse
from rest_framework.test import APIClient


class AttributionLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


@pytest.mark.parametrize(
    "fixture", ["final-live-api-response.json", "best-effort-live-api-response.json"]
)
def test_both_map_modes_credit_geoapify_and_osm_without_altering_payload(fixture):
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "data" / fixture).read_text())
    payload.pop("map_url", None)
    token = uuid.uuid4()
    caches["maps"].set(f"map:{token}", payload, 60)
    response = APIClient().get(reverse("route-map", args=[token]))
    assert response.status_code == 200
    page = response.content.decode()
    # Credits are on the shared map attribution control, not a conditional popup.
    attribution = re.search(r"attribution: '([^']+)'", page).group(1)
    assert "Powered by Geoapify" in attribution and "OpenStreetMap" in attribution
    parser = AttributionLinks()
    parser.feed(attribution)
    links = {link["href"]: link for link in parser.links}
    assert "https://www.openstreetmap.org/copyright" in links
    provider = links["https://www.geoapify.com/"]
    assert provider["target"] == "_blank"
    assert set(provider["rel"].split()) == {"noopener", "noreferrer"}
    embedded = json.loads(
        re.search(
            r'<script id="route-data" type="application/json">(.*?)</script>',
            page,
            re.DOTALL,
        ).group(1)
    )
    assert embedded == payload
