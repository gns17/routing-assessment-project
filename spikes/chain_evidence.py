"""Offline official-directory evidence prototype. Never imported by the application.

Official source rows are not imported station records; no production DB or HTTP.
The source ID/name/branch establishes identity before independent fuel geometry is
considered. A nearby POI never establishes identity by itself.
"""

import argparse
import html
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from spikes.osm_feasibility import branches, chain, normalize, poi_branches

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_HOSTS = {
    "www.loves.com": {"loves"},
    "locations.pilotflyingj.com": {"pilot", "flying_j", "one9"},
    "locations.maverik.com": {"maverik"},
}
# Product labels can appear at network dealers. They are not retail identity proof.
FUEL_PRODUCT_LABELS = {
    normalize(s)
    for s in (
        "Shell",
        "Valero",
        "Conoco",
        "Phillips 66",
        "Texaco",
        "Mobil",
        "Alon",
        "Chevron",
        "Exxon",
        "BP",
        "DK",
    )
}


class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def plain(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def microprop(body, key):
    match = re.search(
        rf'<([\w-]+)\b[^>]*\bitemprop=["\']{key}["\'][^>]*>', body, re.IGNORECASE
    )
    if not match:
        return ""
    content = re.search(r'\bcontent=["\']([^"\']*)', match[0], re.IGNORECASE)
    if content:
        return html.unescape(content[1])
    end = body.find(f"</{match[1]}", match.end())
    return plain(body[match.end() : end]) if end != -1 else ""


def parse_official(body, url):
    """Parse explicit main-store fields; ambiguous coordinate fields fail closed."""
    location = urlsplit(url)
    if location.scheme != "https" or location.hostname not in OFFICIAL_HOSTS:
        return None
    heading = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.DOTALL | re.IGNORECASE)
    if not heading:
        return None
    name = plain(heading[1])
    family = chain(name)
    if family not in OFFICIAL_HOSTS[location.hostname]:
        return None
    visible = Visible()
    visible.feed(body)
    text = " ".join(visible.parts)
    row = {
        "source_url": url,
        "name": name,
        "chain": family,
        "branch_ids": sorted(branches(name)),
        "official_opis_id": None,
        "street": microprop(body, "streetAddress"),
        "city": microprop(body, "addressLocality"),
        "state": microprop(body, "addressRegion"),
        "postal": microprop(body, "postalCode"),
        "latitude": None,
        "longitude": None,
        "coordinate_provenance": "missing",
        "exit_numbers": sorted(
            set(re.findall(r"\bExit\s+(\d+)[A-Z]?\b", text, re.IGNORECASE))
        ),
    }
    if family == "loves":
        for block in re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            body,
            re.DOTALL | re.IGNORECASE,
        ):
            try:
                data = json.loads(block)
            except ValueError:
                continue
            if isinstance(data, dict) and isinstance(data.get("geo"), dict):
                address = data.get("address", {})
                row.update(
                    street=address.get("streetAddress", ""),
                    city=address.get("addressLocality", ""),
                    state=address.get("addressRegion", ""),
                    postal=address.get("postalCode", ""),
                    latitude=float(data["geo"]["latitude"]),
                    longitude=float(data["geo"]["longitude"]),
                    coordinate_provenance="official_jsonld_site",
                )
        opis = re.search(r"\bOPIS\s*:\s*(\d+)\b", text)
        if opis:
            row["official_opis_id"] = int(opis[1])
    elif family in {"pilot", "flying_j", "one9"}:
        coords = re.findall(r"Coordinates:\s*(-?\d+\.\d+),\s*(-?\d+\.\d+)", text)
        if len(set(coords)) == 1:
            row.update(
                latitude=float(coords[0][0]),
                longitude=float(coords[0][1]),
                coordinate_provenance="official_visible_site_coordinate",
            )
    elif family == "maverik":
        coords = re.findall(
            r'"latitude"\s*:\s*"?(-?\d+\.\d+)"?\s*,\s*"longitude"\s*:\s*"?(-?\d+\.\d+)',
            html.unescape(body),
        )
        if len(set(coords)) == 1:
            row.update(
                latitude=float(coords[0][0]),
                longitude=float(coords[0][1]),
                coordinate_provenance="official_single_site_data_coordinate",
            )
    return row


def distance_meters(a, b):
    lat, lon, other_lat, other_lon = map(math.radians, (*a, *b))
    value = (
        math.sin((lat - other_lat) / 2) ** 2
        + math.cos(lat) * math.cos(other_lat) * math.sin((lon - other_lon) / 2) ** 2
    )
    return 12_742_000 * math.asin(min(1, math.sqrt(value)))


def identity(record, source):
    """Identity first. City/chain or coordinates alone can never pass this gate."""
    target_chain = chain(record["Truckstop Name"])
    origin = urlsplit(source["source_url"])
    if origin.scheme != "https" or source["chain"] not in OFFICIAL_HOSTS.get(
        origin.hostname, set()
    ):
        return {"accepted": False, "reason": "untrusted_official_source_domain"}
    if source["coordinate_provenance"] not in {
        "official_jsonld_site",
        "official_visible_site_coordinate",
        "official_single_site_data_coordinate",
    }:
        return {
            "accepted": False,
            "reason": "coordinate_is_not_an_explicit_official_site_point",
        }
    target_branches = branches(record["Truckstop Name"])
    if target_chain != source["chain"]:
        return None
    explicit_id = source.get("official_opis_id")
    branch_agrees = bool(target_branches & set(source["branch_ids"]))
    if explicit_id is not None and explicit_id != record["opis_id"]:
        return (
            {"accepted": False, "reason": "official_opis_conflict"}
            if branch_agrees
            else None
        )
    if explicit_id != record["opis_id"] and not branch_agrees:
        return None
    if target_branches and not branch_agrees:
        return {"accepted": False, "reason": "branch_conflict"}
    if normalize(record["City"]) != normalize(source["city"]):
        return {
            "accepted": False,
            "reason": "official_locality_conflict_requires_documented_crosswalk",
        }
    if normalize(source["state"]) not in {"nm", "new mexico"}:
        return {"accepted": False, "reason": "official_state_conflict"}
    target_exits = set(
        re.findall(r"\bEXIT\s+(\d+)[A-Z]?\b", record["Address"], re.IGNORECASE)
    )
    source_exits = set(source["exit_numbers"])
    if target_exits and source_exits and not target_exits & source_exits:
        return {"accepted": False, "reason": "official_highway_exit_conflict"}
    if (
        not source["street"]
        or source["latitude"] is None
        or source["longitude"] is None
    ):
        return {
            "accepted": False,
            "reason": "official_site_coordinate_or_street_missing",
        }
    lat, lon = source["latitude"], source["longitude"]
    if not 31.2 < lat < 37.1 or not -109.1 < lon < -102.9:
        return {"accepted": False, "reason": "official_site_outside_nm_bounds"}
    return {
        "accepted": True,
        "reason": "official_opis_and_branch"
        if explicit_id == record["opis_id"]
        else "official_chain_branch_locality",
        "street": source["street"],
        "exit_agreement": bool(target_exits & source_exits),
    }


def reconcile(record, sources, pois):
    proposals = []
    for source in sources:
        evidence = identity(record, source)
        if evidence is None:
            continue
        proposal = {
            "source": source,
            "identity_evidence": evidence,
            "fuel_geometry": [],
            "classification": "approximate_ambiguous",
            "reasons": [],
        }
        if not evidence["accepted"]:
            proposal["reasons"] = [evidence["reason"]]
            if evidence["reason"] in {
                "official_opis_conflict",
                "branch_conflict",
                "official_state_conflict",
            }:
                proposal["classification"] = "rejected"
            proposals.append(proposal)
            continue
        anchor = source["latitude"], source["longitude"]
        for poi in pois:
            if poi["tags"].get("amenity") != "fuel":
                continue
            if poi["latitude"] is None or poi["longitude"] is None:
                continue
            separation = distance_meters(anchor, (poi["latitude"], poi["longitude"]))
            if separation > 60:
                continue
            tags = poi["tags"]
            poi_chain = chain(tags.get("name", "")) or chain(tags.get("brand", ""))
            contradictions = []
            if poi_chain and poi_chain != source["chain"]:
                contradictions.append("independent_poi_chain_conflict")
            if (
                tags.get("name")
                and not poi_chain
                and normalize(tags["name"]) not in FUEL_PRODUCT_LABELS
            ):
                contradictions.append("unrelated_named_business_requires_review")
            refs = poi_branches(tags)
            if refs and not refs & set(source["branch_ids"]):
                contradictions.append("independent_poi_branch_conflict")
            if tags.get("addr:state") and normalize(tags["addr:state"]) not in {
                "nm",
                "new mexico",
            }:
                contradictions.append("independent_poi_state_conflict")
            if tags.get("addr:city") and normalize(tags["addr:city"]) != normalize(
                source["city"]
            ):
                contradictions.append("independent_poi_locality_requires_review")
            # Unnamed/brandless geometry needs tighter agreement and an authoritative
            # identity above; it is never a candidate-generator from geographic proximity.
            compatible = not contradictions and (
                poi_chain == source["chain"] or separation <= 30
            )
            proposal["fuel_geometry"].append(
                {
                    "osm_type": poi["osm_type"],
                    "osm_id": poi["osm_id"],
                    "meters_from_official_site": round(separation, 3),
                    "same_named_chain": poi_chain == source["chain"],
                    "compatible": compatible,
                    "contradictions": contradictions,
                }
            )
        good = [p for p in proposal["fuel_geometry"] if p["compatible"]]
        conflicting = [p for p in proposal["fuel_geometry"] if p["contradictions"]]
        if good and not conflicting:
            proposal["classification"] = "high_confidence_automated"
            proposal["reasons"] = [
                "official_identity_precedes_independent_actual_fuel_geometry",
                "canonical_point_is_official_site_not_closest_osm_object",
                "manual_audit_pending",
            ]
        else:
            proposal["reasons"] = [
                "nearby_independent_identity_contradiction"
                if conflicting
                else "independent_fuel_geometry_missing_or_too_far"
            ]
        proposals.append(proposal)
    strong = [
        p for p in proposals if p["classification"] == "high_confidence_automated"
    ]
    if len(strong) > 1:
        for proposal in strong:
            proposal.update(
                classification="approximate_ambiguous",
                reasons=["competing_official_station_claims"],
            )
    final = (
        "high_confidence_automated"
        if len(strong) == 1
        else "approximate_ambiguous"
        if any(p["classification"] != "rejected" for p in proposals)
        else "rejected"
        if proposals
        else "approximate_ambiguous"
    )
    return {
        "opis_id": record["opis_id"],
        "record": record,
        "classification": final,
        "proposals": proposals,
        "unresolved_reason": None
        if proposals
        else "no_unique_official_identity_source",
        "production_import_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--osm-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if ROOT in args.output.resolve().parents:
        parser.error("Experimental output must remain outside Git/workspace")
    sources = json.loads(args.sources.read_text())
    osm = json.loads(args.osm_results.read_text())
    results = [reconcile(r["record"], sources, osm["pois"]) for r in osm["results"]]
    args.output.write_text(json.dumps(results, indent=2))
    print(
        json.dumps(
            {
                "records": len(results),
                "high": sum(
                    r["classification"] == "high_confidence_automated" for r in results
                ),
                "production_import_approved": False,
            }
        )
    )


if __name__ == "__main__":
    main()
