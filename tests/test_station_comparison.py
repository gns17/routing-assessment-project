import json

import httpx
import pytest

from spikes.geocoding import ROOT
from spikes.station_comparison import Comparison, assess, tasks
from tests.test_geocoding_spike import Clock


@pytest.fixture
def document():
    source = json.loads((ROOT / "data/geocoding-feasibility.json").read_text())
    source.pop("comparison", None)
    return source


def make_runner(tmp_path, document, handler):
    clock = Clock()
    return Comparison(
        httpx.Client(transport=httpx.MockTransport(handler)),
        "test-secret",
        tmp_path / "results.json",
        document,
        clock,
        clock.sleep,
    )


def test_only_five_stations_and_bias(document):
    queries = tasks(document)
    assert len(queries) == 10
    assert len({t["opis_id"] for t in queries}) == 5
    for task in queries:
        if task["approach"] == "places":
            assert task["params"]["bias"].startswith("proximity:")
            assert task["params"]["categories"] == "service.vehicle.fuel"
            assert task["params"]["limit"] == 20
        else:
            assert "text" not in task["params"]
            assert "street" not in task["params"]
            assert task["params"]["type"] == "amenity"


def test_preserves_all_candidates_truncation_and_empty(document):
    task = tasks(document)[-1]
    payload = {
        "features": [
            {"properties": {"name": "Fuel", "datasource": {"raw": {"ref": str(i)}}}}
            for i in range(20)
        ]
    }
    result = assess(task, payload)
    assert result["raw_response"] == payload
    assert result["candidate_count"] == 20
    assert result["potentially_truncated"]
    assert result["classification"] == "ambiguous"
    assert assess(task, {"features": []})["reason"] == "empty_search_inconclusive"


def test_fifteen_attempt_cap_including_retries(tmp_path, document):
    run = make_runner(tmp_path, document, lambda _: httpx.Response(503))
    run.run()
    assert run.state["attempt_count"] == 15
    assert sum(a["retry"] for a in run.state["attempts"]) == 5
    assert len(run.state["results"]) == 10
    run.run()
    assert run.state["attempt_count"] == 15


def test_success_pacing_resume_redaction(tmp_path, document):
    def handler(request):
        field = "features" if request.url.path.endswith("places") else "results"
        return httpx.Response(
            200,
            json={field: [{"name": "test-secret", "datasource": {"source": "OSM"}}]},
        )

    run = make_runner(tmp_path, document, handler)
    run.run()
    assert run.state["attempt_count"] == 10
    assert sum(run.sleep.__self__.sleeps) >= 9
    assert "test-secret" not in run.path.read_text()
    run.run()
    assert run.state["attempt_count"] == 10


@pytest.mark.parametrize("code", [401, 403, 429])
def test_auth_quota_halt(tmp_path, document, code):
    run = make_runner(tmp_path, document, lambda _: httpx.Response(code))
    run.run()
    assert run.state["attempt_count"] == 1
    run.run()
    assert run.state["attempt_count"] == 1


def test_rejects_corrupt_budget(tmp_path, document):
    document["comparison"] = {
        "policy": "five-station-name-places-v1",
        "max_attempts": 16,
        "attempt_count": 0,
        "attempts": [],
        "results": {},
    }
    with pytest.raises(ValueError, match="budget"):
        make_runner(tmp_path, document, lambda _: httpx.Response(200))
