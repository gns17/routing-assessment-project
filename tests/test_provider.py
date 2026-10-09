from decimal import Decimal

import httpx
import pytest
from django.core.cache.backends.locmem import LocMemCache

from routing.provider import Geoapify, ProviderError
from routing.serializers import RouteRequestSerializer


def geo(lat=35, lon=-106, label="Albuquerque, NM"):
    return {
        "country_code": "us",
        "state_code": "NM",
        "lat": lat,
        "lon": lon,
        "formatted": label,
        "rank": {"confidence": 1},
    }


def route_data(geometry=None):
    return {
        "features": [
            {
                "geometry": geometry
                or {
                    "type": "MultiLineString",
                    "coordinates": [[[-106, 35], [-105, 36]]],
                },
                "properties": {"distance": 160934.4, "time": 3600},
            }
        ]
    }


def test_three_calls_coordinate_order_geometry_cache():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("search"):
            assert request.url.params["filter"] == "countrycode:us"
            return httpx.Response(
                200,
                json={
                    "results": [
                        geo()
                        if request.url.params["text"] == "Albuquerque"
                        else geo(36, -105, "Santa Fe")
                    ]
                },
            )
        assert request.url.params["waypoints"] == "35,-106|36,-105"
        assert request.url.params["mode"] == "drive"
        return httpx.Response(200, json=route_data())

    cache = LocMemCache("provider-test", {})
    cache.clear()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with Geoapify("test-key", client, cache) as provider:
        route = provider.route("Albuquerque", "Santa Fe")
        assert provider.calls == 3
        assert route.distance_miles == Decimal(100)
        assert route.geometry["coordinates"][0][0] == [-106, 35]
    with Geoapify("test-key", client, cache) as provider:
        assert provider.route("Albuquerque", "Santa Fe").geometry == route.geometry
        assert provider.calls == 0
    assert len(requests) == 3


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "provider_authentication"),
        (403, "provider_authentication"),
        (429, "provider_rate_limited"),
        (503, "provider_unavailable"),
        (400, "provider_response"),
    ],
)
def test_http_errors_no_retries_or_secret_echo(status, code):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, text="test-secret")
        )
    )
    with Geoapify("test-secret", client) as provider:
        with pytest.raises(ProviderError) as error:
            provider.geocode("Albuquerque")
        assert error.value.code == code
        assert "test-secret" not in str(error.value)
        assert provider.calls == 1


def test_timeout_is_sanitized_and_not_retried():
    def handler(request):
        raise httpx.ReadTimeout(str(request.url), request=request)

    with Geoapify(
        "secret", httpx.Client(transport=httpx.MockTransport(handler))
    ) as provider:
        with pytest.raises(ProviderError, match="could not be reached"):
            provider.geocode("Albuquerque")
        assert provider.calls == 1


@pytest.mark.parametrize(
    "results",
    [
        [],
        [{**geo(), "country_code": "ca"}],
        [{**geo(), "state_code": "AK"}],
        [{**geo(), "lat": 100}],
        [{**geo(), "rank": {"confidence": 0.5}}],
    ],
)
def test_unresolved_or_non_contiguous_us(results):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"results": results})
        )
    )
    with Geoapify("key", client) as provider:
        with pytest.raises(ProviderError) as error:
            provider.geocode("location")
        assert error.value.status == 422


def test_ambiguous_candidates_and_duplicate_representations():
    candidates = [geo(), geo(36, -105)]
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"results": candidates})
        )
    )
    with (
        Geoapify("key", client) as provider,
        pytest.raises(ProviderError, match="ambiguous"),
    ):
        provider.geocode("location")
    candidates[:] = [geo(), geo()]
    with Geoapify("key", client) as provider:
        assert provider.geocode("location").latitude == 35


@pytest.mark.parametrize(
    "payload",
    [
        {"features": []},
        {"features": [{}]},
        route_data({"type": "Polygon", "coordinates": []}),
        route_data({"type": "LineString", "coordinates": [[200, 30], [-105, 36]]}),
    ],
)
def test_missing_or_malformed_route(payload):
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        if request.url.path.endswith("search"):
            return httpx.Response(200, json={"results": [geo(count + 30)]})
        return httpx.Response(200, json=payload)

    with Geoapify(
        "key", httpx.Client(transport=httpx.MockTransport(handler))
    ) as provider:
        with pytest.raises(ProviderError):
            provider.route("a", "b")
        assert provider.calls == 3


@pytest.mark.parametrize(
    "data",
    [
        {"start": 123, "finish": "a"},
        {"start": "", "finish": "a"},
        {"start": "a", "finish": "b", "coordinates": [1, 2]},
        {"start": "a"},
        {"start": "a" * 301, "finish": "b"},
        {"start": "a\x00b", "finish": "b"},
    ],
)
def test_request_validation(data):
    assert not RouteRequestSerializer(data=data).is_valid()


def test_request_normalization():
    serializer = RouteRequestSerializer(
        data={"start": "  Santa   Fe, NM ", "finish": "Albuquerque, NM"}
    )
    assert serializer.is_valid()
    assert serializer.validated_data["start"] == "Santa Fe, NM"
