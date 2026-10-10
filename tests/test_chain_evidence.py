"""Research-only evidence gates; synthetic fixtures never become station records."""

import copy

from spikes.chain_evidence import identity, parse_official, reconcile


def source(**changes):
    return {
        "source_url": "https://www.loves.com/locations/nm/milan/loves-travel-stop-milan-257",
        "name": "Love's Travel Stop #257",
        "chain": "loves",
        "branch_ids": ["257"],
        "official_opis_id": 1356,
        "street": "257 Horizon Boulevard",
        "city": "Milan",
        "state": "NM",
        "postal": "87021",
        "latitude": 35.183319,
        "longitude": -107.899758,
        "coordinate_provenance": "official_jsonld_site",
        "exit_numbers": ["79"],
        **changes,
    }


def record(**changes):
    return {
        "opis_id": 1356,
        "Truckstop Name": "LOVES TRAVEL STOP #257",
        "City": "Milan",
        "State": "NM",
        "Address": "I-40 EXIT 79",
        **changes,
    }


def poi(**tags):
    return {
        "osm_type": "node",
        "osm_id": 1,
        "latitude": 35.183319,
        "longitude": -107.899758,
        "tags": {"amenity": "fuel", **tags},
    }


def test_official_opis_and_branch_recover_unnamed_geometry():
    result = reconcile(record(), [source()], [poi()])
    assert result["classification"] == "high_confidence_automated"
    assert result["production_import_approved"] is False
    assert (
        result["proposals"][0]["identity_evidence"]["reason"]
        == "official_opis_and_branch"
    )


def test_precise_official_point_without_identity_never_passes():
    result = reconcile(
        record(), [source(branch_ids=[], official_opis_id=None)], [poi()]
    )
    assert result["classification"] == "approximate_ambiguous"
    assert result["unresolved_reason"] == "no_unique_official_identity_source"


def test_wrong_opis_id_rejected_despite_exact_coordinates():
    result = reconcile(record(), [source(official_opis_id=999)], [poi()])
    assert result["classification"] == "rejected"
    assert result["proposals"][0]["reasons"] == ["official_opis_conflict"]


def test_official_branch_locality_proof_without_opis_listing():
    assert identity(record(), source(official_opis_id=None))["accepted"] is True


def test_foreign_state_and_locality_not_overridden_by_proximity():
    assert identity(record(), source(state="TX"))["reason"] == "official_state_conflict"
    assert (
        identity(record(), source(city="Grants"))["reason"]
        == "official_locality_conflict_requires_documented_crosswalk"
    )


def test_exit_contradiction_requires_review():
    assert (
        identity(record(), source(exit_numbers=["16"]))["reason"]
        == "official_highway_exit_conflict"
    )


def test_missing_coordinate_and_city_centroid_without_fuel_stays_ambiguous():
    assert identity(record(), source(latitude=None))["accepted"] is False
    assert (
        reconcile(record(), [source()], [])["classification"] == "approximate_ambiguous"
    )


def test_competing_official_claims_fail_closed():
    result = reconcile(
        record(),
        [source(), source(source_url="https://www.loves.com/another")],
        [poi()],
    )
    assert result["classification"] == "approximate_ambiguous"
    assert all(
        p["reasons"] == ["competing_official_station_claims"]
        for p in result["proposals"]
    )


def test_unrelated_named_station_is_not_a_physical_corroboration():
    result = reconcile(record(), [source()], [poi(name="Joe's Discount Gas")])
    assert result["classification"] == "approximate_ambiguous"
    assert (
        "unrelated_named_business_requires_review"
        in result["proposals"][0]["fuel_geometry"][0]["contradictions"]
    )


def test_explicit_competing_chain_or_branch_stays_ambiguous():
    assert (
        reconcile(record(), [source()], [poi(name="Pilot")])["classification"]
        == "approximate_ambiguous"
    )
    assert (
        reconcile(record(), [source()], [poi(name="Love's", ref="999")])[
            "classification"
        ]
        == "approximate_ambiguous"
    )


def test_sparse_osm_tags_do_not_remove_strong_external_identity():
    assert (
        reconcile(record(), [source()], [poi(brand="Love's")])["classification"]
        == "high_confidence_automated"
    )


def test_distant_actual_fuel_does_not_rescue_bad_official_point():
    distant = {**poi(), "latitude": 35.19}
    assert (
        reconcile(record(), [source()], [distant])["classification"]
        == "approximate_ambiguous"
    )


def test_canonical_point_is_official_and_inputs_unchanged():
    s, p = source(), poi()
    before = copy.deepcopy((s, p))
    result = reconcile(record(), [s], [p])
    assert (s, p) == before
    assert result["proposals"][0]["source"]["latitude"] == s["latitude"]


def test_official_parser_requires_whitelisted_domain_and_family():
    body = "<h1>Love's Travel Stop #257</h1>"
    assert parse_official(body, "https://unrelated.example/store") is None
    assert parse_official(body, "https://locations.maverik.com/store") is None


def test_parser_reads_explicit_id_and_site_jsonld_without_map_api():
    body = '<h1>Love\'s Travel Stop #257</h1><p>OPIS: 01356 Exit 79</p><script type="application/ld+json">{"geo":{"latitude":35.183319,"longitude":-107.899758},"address":{"streetAddress":"257 Horizon Blvd","addressLocality":"Milan","addressRegion":"NM"}}</script>'
    result = parse_official(body, source()["source_url"])
    assert result["official_opis_id"] == 1356
    assert result["latitude"] == 35.183319
    assert result["exit_numbers"] == ["79"]


def test_maverik_ambiguous_coordinate_fields_fail_closed():
    body = '<h1>Albuquerque NM Maverik #639</h1><script>{"latitude":35.0791,"longitude":-106.7435};{"latitude":35.1,"longitude":-106.7}</script>'
    result = parse_official(body, "https://locations.maverik.com/nm/albuquerque/store")
    assert result["latitude"] is None


def test_city_and_road_objects_do_not_corroborate_a_fuel_site():
    town = {**poi(), "tags": {"place": "city"}}
    road = {**poi(), "tags": {"highway": "primary"}}
    assert (
        reconcile(record(), [source()], [town, road])["classification"]
        == "approximate_ambiguous"
    )


def test_untrusted_and_viewport_sources_do_not_pass_identity():
    assert (
        identity(record(), source(source_url="https://unrelated.example/store"))[
            "accepted"
        ]
        is False
    )
    assert (
        identity(record(), source(coordinate_provenance="map_viewport_center"))[
            "accepted"
        ]
        is False
    )
