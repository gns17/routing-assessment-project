"""New Mexico-only offline research; never imports coordinates or assigns prices.

Extraction requires pyosmium in an isolated environment, not an app dependency.
Outputs must be outside the repository. OSM tags are evidence, not verification.
"""

import argparse
import csv
import hashlib
import json
import re
import resource
import sys
import time
import unicodedata
from collections import Counter
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = "nm-osm-research-v1"
# Spelling/brand aliases only. No cross-brand or historic-ownership substitution.
CHAINS = {
    "loves": ["loves", "love s"],
    "flying_j": ["flying j"],
    "pilot": ["pilot"],
    "ta": ["ta", "travelcenters of america", "travel centers of america"],
    "petro": ["petro", "petro stopping center"],
    "allsups": ["allsups", "allsup s"],
    "maverik": ["maverik"],
    "circle_k": ["circle k"],
    "one9": ["one9", "one 9"],
    "stripes": ["stripes"],
    "quarles": ["quarles"],
    "speedway": ["speedway"],
    "kent_kwik": ["kent kwik"],
    "toot_n_totum": ["toot n totum"],
    "chevron": ["chevron"],
}
GENERIC = {
    "travel",
    "truck",
    "truckstop",
    "stop",
    "stopping",
    "center",
    "centre",
    "plaza",
    "fuel",
    "fuels",
    "gas",
    "station",
    "convenience",
    "country",
    "store",
    "market",
    "marketplace",
    "the",
    "of",
}


def normalize(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def chain(value):
    padded = f" {normalize(value)} "
    return next(
        (
            name
            for name, aliases in CHAINS.items()
            if any(f" {a} " in padded for a in aliases)
        ),
        None,
    )


def branches(value):
    return {str(int(n)) for n in re.findall(r"#\s*(\d+)\b", value)}


def poi_branches(tags):
    values = branches(tags.get("name", "")) | branches(tags.get("official_name", ""))
    for key in (
        "ref",
        "branch",
        "brand:ref",
        "operator:ref",
        "ref:store",
        "store_number",
    ):
        text = tags.get(key, "").strip()
        values |= branches(text)
        if re.fullmatch(r"#?\d+", text):
            values.add(str(int(text.lstrip("#"))))
    return values


def distinctive(value):
    return {
        t for t in normalize(re.sub(r"#\s*\d+", "", value)).split() if t not in GENERIC
    }


def polygon_center(points):
    """Closed way's planar area centroid; a site proxy, never an entrance."""
    if len(points) < 4 or points[0] != points[-1]:
        return None
    origin_x, origin_y = points[0]
    shifted = [(x - origin_x, y - origin_y) for x, y in points]
    area = cx = cy = 0.0
    for (x, y), (xx, yy) in pairwise(shifted):
        cross = x * yy - xx * y
        area += cross
        cx += (x + xx) * cross
        cy += (y + yy) * cross
    if not area:
        return None
    return origin_y + cy / (3 * area), origin_x + cx / (3 * area)


def rss_bytes():
    amount = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return amount if sys.platform == "darwin" else amount * 1024


def check_resources(scratch, deadline):
    if time.monotonic() >= deadline:
        raise RuntimeError("Experiment time limit reached")
    if rss_bytes() >= 2.8 * 1024**3:
        raise RuntimeError("Peak process memory approaching 3 GiB")
    if sum(p.stat().st_size for p in scratch.rglob("*") if p.is_file()) > 5 * 1024**3:
        raise RuntimeError("Scratch storage exceeds 5 GiB")


def nm_records(path):
    records = {}
    with path.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            if row["State"].strip() != "NM":
                continue
            opis = int(row["OPIS Truckstop ID"])
            identity = {
                k: " ".join(row[k].split())
                for k in ("Truckstop Name", "Address", "City", "State")
            }
            prior = records.setdefault(
                opis, {"opis_id": opis, **identity, "aliases": []}
            )
            if any(prior[k] != identity[k] for k in ("Address", "City", "State")):
                raise ValueError("Conflicting OPIS location")
            prior["aliases"] = sorted(
                set(prior["aliases"] + [identity["Truckstop Name"]])
            )
    return list(records.values())


def extract(path, scratch, deadline):
    import osmium  # Optional spike dependency; never imported by the application.

    class Handler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.pois, self.counts = [], Counter()

        def tick(self, kind):
            self.counts[kind] += 1
            if self.counts[kind] % 100_000 == 0:
                check_resources(scratch, deadline)

        def node(self, node):
            self.tick("nodes")
            if node.tags.get("amenity") == "fuel":
                tags = dict(node.tags)
                position = (
                    (node.location.lat, node.location.lon)
                    if node.location.valid()
                    else None
                )
                self.keep("node", node.id, tags, position, "osm_fuel_node")

        def way(self, way):
            self.tick("ways")
            if way.tags.get("amenity") == "fuel":
                points = [(n.lon, n.lat) for n in way.nodes if n.location.valid()]
                position = (
                    polygon_center(points) if len(points) == len(way.nodes) else None
                )
                self.keep(
                    "way",
                    way.id,
                    dict(way.tags),
                    position,
                    "osm_closed_fuel_way_area_centroid",
                )

        def relation(self, relation):
            self.tick("relations")
            if relation.tags.get("amenity") == "fuel":
                self.counts["fuel_relations_not_assembled"] += 1

        def keep(self, kind, object_id, tags, position, provenance):
            self.pois.append(
                {
                    "osm_type": kind,
                    "osm_id": object_id,
                    "osm_url": f"https://www.openstreetmap.org/{kind}/{object_id}",
                    "tags": tags,
                    "latitude": position[0] if position else None,
                    "longitude": position[1] if position else None,
                    "coordinate_provenance": provenance
                    if position
                    else "unresolved_geometry",
                }
            )

    handler = Handler()
    start = time.monotonic()
    # Compact sparse memory location cache; nodes streamed, full ways not retained.
    handler.apply_file(str(path), locations=True, idx="sparse_mem_array")
    check_resources(scratch, deadline)
    return handler.pois, {
        **handler.counts,
        "seconds": time.monotonic() - start,
        "peak_rss_bytes": rss_bytes(),
    }


def assess(record, poi):
    tags = poi["tags"]
    names = [
        tags.get(k, "")
        for k in ("name", "official_name", "alt_name", "old_name", "brand", "operator")
    ]
    target_chain = chain(record["Truckstop Name"])
    # Name/brand take precedence over corporate operator, which can span brands.
    actual_chain = chain(tags.get("name", "")) or chain(tags.get("brand", ""))
    target_branches = branches(record["Truckstop Name"])
    actual_branches = poi_branches(tags)
    branch_match = bool(target_branches & actual_branches)
    locality = normalize(record["City"])
    city_tag = (
        tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village") or ""
    )
    locality_match = locality == normalize(city_tag) or any(
        f" {locality} " in f" {normalize(n)} " for n in names[:3]
    )
    explicit_city_conflict = bool(city_tag) and normalize(city_tag) != locality
    distinctive_match = not target_chain and any(
        len(distinctive(record["Truckstop Name"])) >= 2
        and distinctive(record["Truckstop Name"]) == distinctive(n)
        for n in names[:3]
        if n
    )
    related = (
        branch_match
        and target_chain == actual_chain
        or distinctive_match
        or locality_match
        and target_chain == actual_chain
    )
    if not related:
        return None
    contradictions = []
    if target_chain and actual_chain and target_chain != actual_chain:
        contradictions.append("chain_conflict")
    if target_branches and actual_branches and not branch_match:
        contradictions.append("branch_conflict")
    if explicit_city_conflict:
        contradictions.append("explicit_locality_conflict")
    if tags.get("addr:state") and normalize(tags["addr:state"]) not in {
        "nm",
        "new mexico",
    }:
        contradictions.append("state_conflict")
    lat, lon = poi["latitude"], poi["longitude"]
    if lat is None or lon is None or not 31.2 < lat < 37.1 or not -109.1 < lon < -102.9:
        contradictions.append("invalid_or_outside_nm_plausibility_bounds")
    # CSV exit descriptions are not equivalent to an OSM postal street address.
    # Highway/locality agreement is explanatory, never independent identity proof.
    strong_identity = (
        target_chain == actual_chain
        and target_chain is not None
        and branch_match
        or distinctive_match
    )
    high = strong_identity and locality_match and not contradictions
    return {
        "osm_type": poi["osm_type"],
        "osm_id": poi["osm_id"],
        "classification": "rejected"
        if contradictions
        else "high_confidence_automated_candidate"
        if high
        else "ambiguous_or_approximate",
        "evidence": {
            "chain_match": target_chain is not None and target_chain == actual_chain,
            "branch_match": branch_match,
            "distinctive_name_match": distinctive_match,
            "strong_identity": strong_identity,
            "locality_match": locality_match,
            "osm_branch_ids": sorted(actual_branches),
            "contradictions": contradictions,
            "csv_address": record["Address"],
            "osm_address": {k: v for k, v in tags.items() if k.startswith("addr:")},
        },
    }


def reconcile(records, pois):
    results = []
    for record in records:
        candidates = [candidate for poi in pois if (candidate := assess(record, poi))]
        strong = [
            c
            for c in candidates
            if c["classification"] == "high_confidence_automated_candidate"
        ]
        # Do not silently collapse duplicate node/way representations or branches.
        possible_identity_matches = [
            c
            for c in candidates
            if c["classification"] != "rejected" and c["evidence"]["strong_identity"]
        ]
        if len(possible_identity_matches) > 1:
            for candidate in strong:
                candidate["classification"] = "ambiguous_or_approximate"
                candidate["evidence"]["competing_strong_candidates"] = True
        strong = [
            c
            for c in candidates
            if c["classification"] == "high_confidence_automated_candidate"
        ]
        category = (
            "high_confidence_automated_candidate"
            if len(strong) == 1
            else "ambiguous_or_approximate"
            if any(
                c["classification"] == "ambiguous_or_approximate" for c in candidates
            )
            else "rejected"
            if candidates
            else "unmatched"
        )
        results.append(
            {"record": record, "classification": category, "candidates": candidates}
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=300)
    args = parser.parse_args()
    if ROOT in args.output.resolve().parents or ROOT in args.pbf.resolve().parents:
        parser.error("PBF and experimental outputs must stay outside the repository")
    if not args.pbf.name.startswith("new-mexico-") or args.max_seconds > 7200:
        parser.error("New Mexico only, bounded execution")
    start = time.monotonic()
    records = nm_records(ROOT / "data/fuel-prices.csv")
    pois, metrics = extract(args.pbf, args.output.parent, start + args.max_seconds)
    results = reconcile(records, pois)
    document = {
        "policy": POLICY,
        "production_import_approved": False,
        "aliases": CHAINS,
        "pbf_sha256": hashlib.file_digest(args.pbf.open("rb"), "sha256").hexdigest(),
        "pbf_bytes": args.pbf.stat().st_size,
        "extraction": metrics,
        "total_processing_seconds": time.monotonic() - start,
        "opis_count": len(records),
        "poi_count": len(pois),
        "classifications": dict(Counter(r["classification"] for r in results)),
        "pois": pois,
        "results": results,
    }
    args.output.write_text(json.dumps(document, indent=2))
    print(
        json.dumps(
            {
                k: v
                for k, v in document.items()
                if k not in {"pois", "results", "aliases"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
