"""Experimental identity gates, independent of osmium and production persistence."""

import time

import pytest

from spikes.osm_feasibility import assess, check_resources, polygon_center, reconcile


def record(name="LOVES TRAVEL STOP #257", city="Milan"):
    return {
        "opis_id": 1356,
        "Truckstop Name": name,
        "City": city,
        "Address": "I-40 EXIT 79",
        "State": "NM",
        "aliases": [name],
    }


def poi(**tags):
    return {
        "osm_type": "node",
        "osm_id": 1,
        "latitude": 35.2,
        "longitude": -107.9,
        "tags": {"amenity": "fuel", "name": "Love's", **tags},
    }


def test_branch_and_locality_unique_is_candidate_not_verified():
    results = reconcile([record()], [poi(ref="257", **{"addr:city": "Milan"})])
    assert results[0]["classification"] == "high_confidence_automated_candidate"
    assert results[0]["candidates"][0]["evidence"]["branch_match"] is True


def test_chain_only_is_never_high_confidence():
    candidate = assess(record(), poi(**{"addr:city": "Milan"}))
    assert candidate["classification"] == "ambiguous_or_approximate"


def test_same_branch_without_locality_is_ambiguous():
    assert (
        assess(record(), poi(ref="257"))["classification"] == "ambiguous_or_approximate"
    )


def test_embedded_branch_reference_and_unknown_locality_competitor():
    first = poi(ref="Milan #257", **{"addr:city": "Milan"})
    assert (
        assess(record(), first)["classification"]
        == "high_confidence_automated_candidate"
    )
    second = {**poi(ref="257"), "osm_id": 2}
    assert (
        reconcile([record()], [first, second])[0]["classification"]
        == "ambiguous_or_approximate"
    )


def test_street_number_never_used_as_branch_number():
    candidate = poi(**{"addr:city": "Milan", "addr:housenumber": "257"})
    assert assess(record(), candidate)["classification"] == "ambiguous_or_approximate"


def test_conflicting_branch_or_locality_is_rejected():
    assert (
        assess(record(), poi(ref="999", **{"addr:city": "Milan"}))["classification"]
        == "rejected"
    )
    assert (
        assess(record(), poi(ref="257", **{"addr:city": "Gallup"}))["classification"]
        == "rejected"
    )


def test_competing_node_way_not_silently_accepted():
    first = poi(ref="257", **{"addr:city": "Milan"})
    second = {**first, "osm_type": "way", "osm_id": 2}
    result = reconcile([record()], [first, second])[0]
    assert result["classification"] == "ambiguous_or_approximate"
    assert len(result["candidates"]) == 2
    assert all(
        c["evidence"]["competing_strong_candidates"] for c in result["candidates"]
    )


def test_distinctive_independent_identity_and_locality():
    candidate = assess(
        record("DANCING EAGLE", "Casa Blanca"),
        poi(name="Dancing Eagle Travel Center", **{"addr:city": "Casa Blanca"}),
    )
    assert candidate["classification"] == "high_confidence_automated_candidate"
    assert (
        assess(
            record("NATIONAL TRUCK STOP", "Vado"),
            poi(name="National", **{"addr:city": "Vado"}),
        )["classification"]
        == "ambiguous_or_approximate"
    )


def test_unresolved_geometry_and_wrong_state_rejected():
    candidate = poi(ref="257", **{"addr:city": "Milan"})
    assert (
        assess(record(), {**candidate, "latitude": None})["classification"]
        == "rejected"
    )
    candidate["tags"]["addr:state"] = "TX"
    assert assess(record(), candidate)["classification"] == "rejected"


def test_closed_area_centroid_and_open_way_rejection():
    assert polygon_center(
        [(-108, 34), (-106, 34), (-106, 36), (-108, 36), (-108, 34)]
    ) == (35, -107)
    assert polygon_center([(-108, 34), (-106, 34), (-106, 36)]) is None


def test_brand_alias_does_not_equate_pilot_with_flying_j():
    assert (
        assess(
            record("PILOT #266", "Las Cruces"),
            poi(name="Flying J", ref="266", **{"addr:city": "Las Cruces"}),
        )
        is None
    )


def test_unmatched_preserved_without_invented_coordinates():
    result = reconcile([record()], [])[0]
    assert result["classification"] == "unmatched"
    assert result["candidates"] == []


def test_resource_guard_stops_before_memory_ceiling(monkeypatch, tmp_path):
    monkeypatch.setattr("spikes.osm_feasibility.rss_bytes", lambda: 2.9 * 1024**3)
    with pytest.raises(RuntimeError, match="memory approaching"):
        check_resources(tmp_path, time.monotonic() + 10)


def test_expired_execution_budget_stops(tmp_path):
    with pytest.raises(RuntimeError, match="time limit"):
        check_resources(tmp_path, time.monotonic() - 1)
