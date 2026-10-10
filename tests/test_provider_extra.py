import httpx
import pytest

from routing.provider import Geoapify, ProviderError


def test_hard_request_cap():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={}))
    )
    with Geoapify("key", client) as provider:
        for _ in range(3):
            provider.request("geocode/search", {})
        with pytest.raises(ProviderError, match="limit"):
            provider.request("geocode/search", {})
        assert provider.calls == 3


def test_invalid_json_and_missing_key():
    with pytest.raises(ProviderError, match="not configured"):
        Geoapify("")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="not JSON"))
    )
    with (
        Geoapify("key", client) as provider,
        pytest.raises(ProviderError, match="invalid data"),
    ):
        provider.geocode("Albuquerque")
