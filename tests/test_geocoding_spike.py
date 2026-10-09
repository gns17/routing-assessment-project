import copy
import json
from collections import Counter

import httpx
import pytest

from spikes.geocoding import (
    ROOT,
    Runner,
    category,
    classify,
    evaluate,
    fingerprint,
    main,
    prepare,
    save,
    select_sample,
)


@pytest.fixture
def station():
    item = {
        "opis_id": "7",
        "name": "Example Fuel #7",
        "address": "I-10, EXIT 7",
        "city": "Phoenix",
        "state": "AZ",
        "aliases": ["Example Fuel #7"],
    }
    item["location_fingerprint"] = fingerprint(item)
    return item


@pytest.fixture
def match(station):
    return {
        "name": station["name"],
        "city": "Phoenix",
        "state_code": "AZ",
        "country_code": "us",
        "lat": 33.4,
        "lon": -112.1,
        "formatted": "Example Fuel #7, Phoenix, AZ",
        "result_type": "amenity",
        "rank": {"confidence": 0.99, "match_type": "full_match"},
    }


class Clock:
    def __init__(self):
        self.now = 0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def runner(tmp_path, station, handler, count=1):
    path = tmp_path / "results.json"
    document = {
        "stations": [{**station, "opis_id": str(i)} for i in range(count)],
        "attempts": [],
        "results": {},
        "request_count": 0,
        "max_requests": 40,
        "status": "awaiting_live_approval",
    }
    clock = Clock()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Runner(client, "secret-api-key", path, document, clock, clock.sleep), clock


def test_sample_is_deterministic_and_diverse():
    sample, adjustments = select_sample(ROOT / "data/fuel-prices.csv")
    assert (sample, adjustments) == select_sample(ROOT / "data/fuel-prices.csv")
    assert len({s["opis_id"] for s in sample}) == 30
    assert Counter(s["category"] for s in sample) == {
        "exit": 12,
        "intersection": 8,
        "road_only_ambiguous": 6,
        "local_address": 4,
    }
    assert len({s["region"] for s in sample}) == 4
    assert len({s["state"] for s in sample}) >= 20
    assert len({s["chain"] for s in sample}) >= 5
    assert any(len(s["source_rows"]) > 1 for s in sample)
    assert len({s["category"] for s in sample[:5]}) == 4
    assert len({s["region"] for s in sample[:5]}) == 4
    assert "Independent/other" in {s["chain"] for s in sample[:5]}
    assert not adjustments


def test_fingerprint_excludes_prices_and_provenance(station):
    updated = {**station, "price": "9.99", "source_rows": [999], "source_sha256": "new"}
    assert fingerprint(updated) == fingerprint(station)
    updated["address"] = "New location"
    assert fingerprint(updated) != fingerprint(station)


def test_mileage_is_not_a_numbered_street_address():
    assert category("34 MILE WEST OF EXIT 11/146") != "local_address"


def test_provisional_station_acceptance(station, match):
    assert classify(station, match)[0] == "accepted"


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"result_type": "city"}, "ambiguous"),
        ({"result_type": "street"}, "ambiguous"),
        (
            {"rank": {"confidence": 1, "match_type": "match_by_city_or_disrict"}},
            "ambiguous",
        ),
        ({"state_code": "CA"}, "rejected"),
        ({"country_code": "ca"}, "rejected"),
        ({"state_code": ""}, "ambiguous"),
        ({"lat": float("nan")}, "rejected"),
        ({"lon": 181}, "rejected"),
        ({"lat": True}, "rejected"),
        ({"city": "Tucson"}, "ambiguous"),
        ({"name": "Example Fuel #8"}, "ambiguous"),
        ({"rank": {"confidence": 0.1}}, "rejected"),
        ({"rank": {"confidence": 0.9, "match_type": "full_match"}}, "ambiguous"),
        ({"result_type": "building"}, "ambiguous"),
    ],
)
def test_classification_failure_cases(station, match, change, expected):
    assert classify(station, {**match, **change})[0] == expected


def test_multiple_plausible_matches_need_review(station, match):
    assert evaluate(station, [match, {**match, "lat": 34}])[1] == "ambiguous"
    assert evaluate(station, [match, match])[1] == "accepted"
    assert evaluate(station, [])[1] == "rejected"


def test_rate_limit_capture_and_resume(tmp_path, station, match):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.params["filter"] == "countrycode:us"
        assert "text" in request.url.params and "name" not in request.url.params
        return httpx.Response(200, json={"results": [match]})

    run, clock = runner(tmp_path, station, handler, 3)
    run.run()
    assert run.document["request_count"] == 3
    assert sum(clock.sleeps) >= 2
    assert all(a["latency_ms"] == 0 for a in run.document["attempts"])
    assert len(run.document["results"]) == 3
    before = copy.deepcopy(run.document["attempts"])
    run.run()
    assert run.document["attempts"] == before
    assert "secret-api-key" not in run.path.read_text()


def test_transient_retry_then_success(tmp_path, station, match):
    codes = iter([503, 200])
    run, clock = runner(
        tmp_path,
        station,
        lambda _: httpx.Response(next(codes), json={"results": [match]}),
    )
    run.run()
    assert run.document["request_count"] == 2
    assert clock.sleeps[0] == 2
    assert run.document["results"]["0"]["classification"] == "accepted"


def test_pilot_never_requests_remaining_stations_even_with_retries(tmp_path, station):
    run, _ = runner(tmp_path, station, lambda _: httpx.Response(503), 30)
    run.run(limit=5, fallbacks=False)
    assert run.document["request_count"] == 10
    assert {a["opis_id"] for a in run.document["attempts"]} == {
        str(i) for i in range(5)
    }
    assert all(not a["fallback"] for a in run.document["attempts"])
    assert len(run.document["results"]) == 5


@pytest.mark.parametrize("status", [401, 403, 429])
def test_auth_or_quota_stops_whole_run(tmp_path, station, status):
    run, _ = runner(
        tmp_path, station, lambda _: httpx.Response(status, text="secret-api-key"), 5
    )
    run.run()
    assert run.document["request_count"] == 1
    assert run.document["status"] == "stopped_auth_or_quota"
    assert "secret-api-key" not in run.path.read_text()
    run.run()
    assert run.document["request_count"] == 1


def test_transport_retry_is_bounded_and_redacted(tmp_path, station):
    def handler(request):
        raise httpx.ReadTimeout(f"error {request.url}", request=request)

    run, _ = runner(tmp_path, station, handler)
    run.run()
    assert run.document["request_count"] == 2
    assert run.document["results"]["0"]["reason"] == "transport_error"
    assert "secret-api-key" not in run.path.read_text()


@pytest.mark.parametrize("payload", [{"features": []}, {"results": [None]}, [1]])
def test_malformed_payload_is_not_retried(tmp_path, station, payload):
    run, _ = runner(tmp_path, station, lambda _: httpx.Response(200, json=payload))
    run.run()
    assert run.document["request_count"] == 1
    assert run.document["results"]["0"]["reason"] == "malformed_response"


def test_raw_provider_echo_is_redacted(tmp_path, station, match):
    match["formatted"] = "Echo secret-api-key"
    run, _ = runner(
        tmp_path, station, lambda _: httpx.Response(200, json={"results": [match]})
    )
    run.run()
    assert "secret-api-key" not in run.path.read_text()
    assert "[REDACTED]" in run.path.read_text()


def test_budget_survives_resume(tmp_path, station):
    run, _ = runner(tmp_path, station, lambda _: httpx.Response(503))
    run.document["request_count"] = 39
    run.document["attempts"] = [{"opis_id": "old", "fallback": False}] * 39
    run.run()
    assert run.document["request_count"] == 40
    saved = json.loads(run.path.read_text())
    assert len(saved["attempts"]) == 40
    run.run()
    assert run.document["request_count"] == 40


def test_fallback_uses_structured_query_and_ten_attempt_cap(tmp_path, station):
    seen = []

    def handler(request):
        seen.append(request.url.params)
        return httpx.Response(200, json={"results": []})

    run, _ = runner(tmp_path, station, handler, 30)
    run.run(30, fallbacks=True)
    assert run.document["request_count"] == 40
    assert sum(a["fallback"] for a in run.document["attempts"]) == 10
    assert "name" in seen[-1] and "text" not in seen[-1]
    run.run(30, fallbacks=True)
    assert run.document["request_count"] == 40


def test_completed_response_checkpoint_recovers_without_http(tmp_path, station, match):
    run, _ = runner(
        tmp_path, station, lambda _: httpx.Response(200, json={"results": [match]})
    )
    sample = run.document["stations"][0]
    result = run.query(sample)
    assert run.document["request_count"] == 1
    assert not run.document["results"]
    run.run()
    assert run.document["request_count"] == 1
    assert run.document["results"]["0"]["classification"] == result["classification"]


def test_prepare_never_calls_network(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr(httpx.Client, "get", fail)
    path = tmp_path / "prepared.json"
    document = prepare(ROOT / "data/fuel-prices.csv", path)
    assert document["request_count"] == 0
    assert document["results"] == {}
    with pytest.raises(SystemExit):
        main(["--output", str(path)])


def test_missing_key_fails_before_network(tmp_path, monkeypatch):
    monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        main(["--live", "--output", str(tmp_path / "missing.json")])


def test_atomic_save_failure_preserves_previous_file(tmp_path):
    path = tmp_path / "checkpoint.json"
    save(path, {"old": True})
    with pytest.raises(ValueError):
        save(path, {"bad": float("nan")})
    assert json.loads(path.read_text()) == {"old": True}


def test_bad_source_headers_are_rejected(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("name,price\nUnknown,3.00\n")
    with pytest.raises(ValueError, match="headers"):
        select_sample(source)


def test_full_sample_requires_pilot_review_before_network(tmp_path, monkeypatch):
    path = tmp_path / "sample.json"
    prepare(ROOT / "data/fuel-prices.csv", path)
    monkeypatch.setenv("GEOAPIFY_API_KEY", "test-key")
    with pytest.raises(SystemExit):
        main(["--live", "--limit", "30", "--output", str(path), "--pilot-reviewed"])
