"""GNS-5: deterministic sample and bounded, resumable Geoapify experiment."""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.geoapify.com/v1/geocode/search"
POLICY = "station-spike-v1"
REGIONS = {
    "Northeast": "CT ME MA NH RI VT NJ NY PA",
    "Midwest": "IN IL MI OH WI IA KS MN MO NE ND SD",
    "South": "DE DC FL GA MD NC SC VA WV AL KY MS TN AR LA OK TX",
    "West": "AZ CO ID MT NV NM UT WY AK CA HI OR WA",
}
STATE_REGION = {s: region for region, states in REGIONS.items() for s in states.split()}
FIELDS = ("OPIS Truckstop ID", "Truckstop Name", "Address", "City", "State")
TARGETS = {"exit": 12, "intersection": 8, "road_only_ambiguous": 6, "local_address": 4}
RESULT_FIELDS = (
    "name",
    "formatted",
    "address_line1",
    "address_line2",
    "lat",
    "lon",
    "country_code",
    "state",
    "state_code",
    "city",
    "county",
    "street",
    "housenumber",
    "postcode",
    "result_type",
    "rank",
    "category",
    "place_id",
    "datasource",
)


def normalized(value):
    return " ".join(value.split())


def fingerprint(station):
    # Neither prices nor source-row/checksum provenance participates in location identity.
    values = [
        station[k].casefold() for k in ("opis_id", "name", "address", "city", "state")
    ]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def chain(name):
    for label, pattern in (
        ("Pilot/Flying J", r"\bPILOT\b|FLYING J"),
        ("Love's", r"\bLOVE'?S\b"),
        ("TA/Petro", r"\bTA\b|\bPETRO\b"),
        ("Kwik", r"KWIK"),
        ("Circle K", r"CIRCLE K"),
        ("Other chain", r"7-ELEVEN|CHEVRON|SHELL|SPEEDWAY|CASEY"),
    ):
        if re.search(pattern, name, re.IGNORECASE):
            return label
    return "Independent/other"


def category(address):
    if re.match(r"^\d+\s", address) and not re.search(
        r"\bMILE\b", address, re.IGNORECASE
    ):
        return "local_address"
    if "&" in address or re.search(
        r"\b(?:I|US|SR|HWY)[ -]?\d+[/]", address, re.IGNORECASE
    ):
        return "intersection"
    if "EXIT" in address.upper():
        return "exit"
    return "road_only_ambiguous"


def select_sample(source):
    stations = {}
    with source.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("CSV is missing required location headers")
        for row_number, row in enumerate(reader, 2):
            if None in row or any(not (row.get(k) or "").strip() for k in FIELDS):
                raise ValueError(f"Invalid location record at row {row_number}")
            values = [normalized(row[k]) for k in FIELDS]
            opis_id, name, address, city, state = values
            if not opis_id.isdigit():
                raise ValueError(f"Invalid OPIS ID at row {row_number}")
            if state not in STATE_REGION:
                continue
            item = stations.setdefault(
                opis_id,
                {
                    "opis_id": opis_id,
                    "name": name,
                    "address": address,
                    "city": city,
                    "state": state,
                    "region": STATE_REGION[state],
                    "chain": chain(name),
                    "category": category(address),
                    "source_rows": [],
                    "aliases": [],
                },
            )
            if any(
                item[k].casefold() != value.casefold()
                for k, value in zip(
                    ("address", "city", "state"), (address, city, state), strict=True
                )
            ):
                raise ValueError(f"Conflicting location for OPIS ID {opis_id}")
            item["source_rows"].append(row_number)
            if name not in item["aliases"]:
                item["aliases"].append(name)
    selected = []
    regions, states, chains = Counter(), Counter(), Counter()
    adjustments = []
    for kind, requested in TARGETS.items():
        pool = [s for s in stations.values() if s["category"] == kind]
        count = min(requested, len(pool))
        if count != requested:
            adjustments.append(f"{kind}: requested {requested}, available {len(pool)}")
        for _ in range(count):
            item = min(
                pool,
                key=lambda s: (
                    regions[s["region"]],
                    states[s["state"]],
                    chains[s["chain"]],
                    -int(len(s["source_rows"]) > 1),
                    int(s["opis_id"]),
                ),
            )
            pool.remove(item)
            selected.append(item)
            regions[item["region"]] += 1
            states[item["state"]] += 1
            chains[item["chain"]] += 1
    # A scarce address category may be replaced by a diverse remaining description.
    remaining = [s for s in stations.values() if s not in selected]
    while len(selected) < 30 and remaining:
        item = min(
            remaining,
            key=lambda s: (regions[s["region"]], states[s["state"]], int(s["opis_id"])),
        )
        remaining.remove(item)
        selected.append(item)
        regions[item["region"]] += 1
        states[item["state"]] += 1
    if len(selected) != 30:
        raise ValueError("Source has fewer than 30 eligible unique US stations")
    for station in selected:
        station["location_fingerprint"] = fingerprint(station)
        station["selection_reason"] = (
            f"{station['category']}; {station['region']}; {station['chain']}"
        )
    # Interleave categories so the five-record pilot is diverse as well.
    selected.sort(key=lambda s: int(s["opis_id"]))
    pilot = []
    pilot_regions = Counter()
    for kind in TARGETS:
        candidates = [s for s in selected if s["category"] == kind]
        if candidates:
            item = min(
                candidates,
                key=lambda s: (pilot_regions[s["region"]], int(s["opis_id"])),
            )
            pilot.append(item)
            pilot_regions[item["region"]] += 1
    candidates = [
        s for s in selected if s not in pilot and s["chain"] == "Independent/other"
    ]
    if not candidates:
        candidates = [s for s in selected if s not in pilot]
    while len(pilot) < 5:
        item = min(
            candidates, key=lambda s: (pilot_regions[s["region"]], int(s["opis_id"]))
        )
        pilot.append(item)
        candidates.remove(item)
        pilot_regions[item["region"]] += 1
    return pilot + [s for s in selected if s not in pilot], adjustments


def finite_number(value, low, high):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and low <= value <= high
    )


def name_key(value):
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def classify(station, result):
    """Conservative provisional classification; accepted still needs manual review."""
    if not finite_number(result.get("lat"), -90, 90) or not finite_number(
        result.get("lon"), -180, 180
    ):
        return "rejected", "invalid_coordinates"
    if result.get("country_code", "").lower() not in ("", "us"):
        return "rejected", "wrong_country"
    state = result.get("state_code", "").upper().removeprefix("US-")
    if state and state != station["state"]:
        return "rejected", "wrong_state"
    rank = result.get("rank") if isinstance(result.get("rank"), dict) else {}
    confidence = rank.get("confidence")
    if finite_number(confidence, 0, 1) and confidence < 0.2:
        return "rejected", "very_low_confidence"
    if result.get("result_type") not in ("amenity", "building"):
        return "ambiguous", "not_station_level"
    if result.get("country_code", "").lower() != "us" or not state:
        return "ambiguous", "missing_country_or_state"
    if name_key(result.get("city", "")) != name_key(station["city"]):
        return "ambiguous", "city_mismatch_or_missing"
    matched_name = result.get("name", "")
    similarity = max(
        SequenceMatcher(None, name_key(alias), name_key(matched_name)).ratio()
        for alias in station["aliases"]
    )
    branch = re.search(r"#\s*(\d+)", station["name"])
    if similarity < 0.85 or (
        branch and not re.search(r"\b" + branch[1] + r"\b", matched_name)
    ):
        return "ambiguous", "station_identity_unconfirmed"
    if not finite_number(confidence, 0.95, 1):
        return "ambiguous", "confidence_below_0.95_or_missing"
    if rank.get("match_type") not in ("full_match", "match_by_building"):
        return "ambiguous", "coarse_or_missing_match_type"
    if result["result_type"] == "building" and not finite_number(
        rank.get("confidence_building_level"), 0.95, 1
    ):
        return "ambiguous", "building_precision_unconfirmed"
    return "accepted", "provisional_station_identity_and_precision"


def evaluate(station, results):
    candidates = []
    for result in results:
        status, reason = classify(station, result)
        candidates.append(
            {
                "match": {k: result[k] for k in RESULT_FIELDS if k in result},
                "classification": status,
                "reason": reason,
            }
        )
    accepted = [c for c in candidates if c["classification"] == "accepted"]
    distinct = {
        (round(c["match"]["lat"], 5), round(c["match"]["lon"], 5)) for c in accepted
    }
    if len(distinct) > 1:
        return candidates, "ambiguous", "multiple_plausible_stations"
    if accepted:
        return candidates, "accepted", accepted[0]["reason"]
    if any(c["classification"] == "ambiguous" for c in candidates):
        return candidates, "ambiguous", "requires_manual_review"
    return candidates, "rejected", "no_usable_station_match"


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def redact(value, key):
    if isinstance(value, dict):
        return {k: redact(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def prepare(source, output):
    sample, adjustments = select_sample(source)
    document = {
        "schema_version": 1,
        "policy": POLICY,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "sample_adjustments": adjustments,
        "sample_counts": {
            field: dict(Counter(s[field] for s in sample))
            for field in ("category", "region", "chain")
        },
        "status": "awaiting_live_approval",
        "request_count": 0,
        "max_requests": 40,
        "stations": sample,
        "attempts": [],
        "results": {},
    }
    save(output, document)
    return document


class Runner:
    def __init__(
        self, client, key, path, document, clock=time.monotonic, sleep=time.sleep
    ):
        self.client, self.key, self.path, self.document = client, key, path, document
        self.clock, self.sleep = clock, sleep
        self.last_started = None

    def query(self, station, fallback=False):
        prior = [
            a
            for a in self.document["attempts"]
            if a["opis_id"] == station["opis_id"] and a["fallback"] == fallback
        ]
        for attempt in reversed(prior):
            if "result" in attempt:
                if attempt.get("http_status") in (401, 403, 429):
                    self.document["status"] = "stopped_auth_or_quota"
                return attempt["result"]
        params = {
            "filter": "countrycode:us",
            "format": "json",
            "limit": 3,
            "lang": "en",
        }
        if fallback:
            params.update(
                name=station["name"],
                city=station["city"],
                state=station["state"],
                country="United States",
            )
        else:
            params["text"] = (
                f"{station['name']}, {station['address']}, {station['city']}, {station['state']}, USA"
            )
        for retry in range(len(prior), 2):
            fallback_count = sum(a["fallback"] for a in self.document["attempts"])
            if self.document["request_count"] >= self.document["max_requests"] or (
                fallback and fallback_count >= 10
            ):
                return {
                    "classification": "ambiguous",
                    "reason": "request_budget_exhausted",
                    "candidates": [],
                }
            if self.last_started is not None:
                self.sleep(max(0, 1 - (self.clock() - self.last_started)))
            attempt = {
                "opis_id": station["opis_id"],
                "fallback": fallback,
                "retry": retry,
                "started_at": datetime.now(UTC).isoformat(),
                "status": "interrupted_or_pending",
            }
            self.document["attempts"].append(attempt)
            self.document["request_count"] += 1
            save(self.path, self.document)  # Reserve budget durably before HTTP.
            started = self.clock()
            self.last_started = started
            retryable, fatal = False, False
            try:
                response = self.client.get(
                    ENDPOINT, params={**params, "apiKey": self.key}
                )
                attempt["http_status"] = response.status_code
                if response.status_code != 200:
                    attempt["status"] = f"http_{response.status_code}"
                    retryable = response.status_code >= 500
                    fatal = response.status_code in (401, 403, 429)
                    result = {
                        "classification": "ambiguous",
                        "reason": attempt["status"],
                        "candidates": [],
                    }
                else:
                    payload = response.json()
                    results = (
                        payload.get("results") if isinstance(payload, dict) else None
                    )
                    if not isinstance(results, list) or not all(
                        isinstance(r, dict) for r in results
                    ):
                        raise ValueError("Invalid response schema")
                    candidates, status, reason = evaluate(station, results)
                    result = {
                        "classification": status,
                        "reason": reason,
                        "candidates": candidates,
                    }
                    attempt["status"] = "ok"
            except httpx.RequestError:
                # Exception messages/URLs and provider error bodies can contain the key.
                attempt["status"] = "transport_error"
                retryable = True
                result = {
                    "classification": "ambiguous",
                    "reason": "transport_error",
                    "candidates": [],
                }
            except (ValueError, TypeError, AttributeError):
                attempt["status"] = "malformed_response"
                result = {
                    "classification": "ambiguous",
                    "reason": "malformed_response",
                    "candidates": [],
                }
            attempt["latency_ms"] = round((self.clock() - started) * 1000, 2)
            # Redact even selected provider fields if the provider echoes the credential.
            result = redact(result, self.key)
            if fatal or not retryable or retry == 1:
                attempt["result"] = result
            save(self.path, self.document)
            if fatal:
                self.document["status"] = "stopped_auth_or_quota"
                save(self.path, self.document)
                return result
            if retryable and retry == 0:
                self.sleep(2)
                continue
            return result
        return {
            "classification": "ambiguous",
            "reason": "interrupted_attempts_exhausted",
            "candidates": [],
        }

    def run(self, limit=5, fallbacks=False):
        if limit not in (5, 30):
            raise ValueError(
                "Only the five-record pilot or 30-record sample is allowed"
            )
        if self.document["status"] == "stopped_auth_or_quota":
            return
        self.document["status"] = "running"
        for station in self.document["stations"][:limit]:
            opis_id = station["opis_id"]
            if opis_id in self.document["results"]:
                continue
            result = self.query(station)
            result.update(
                manual_review="pending",
                location_fingerprint=station["location_fingerprint"],
            )
            self.document["results"][opis_id] = result
            save(self.path, self.document)
            if self.document["status"] == "stopped_auth_or_quota":
                return
        if fallbacks and self.document["status"] != "stopped_auth_or_quota":
            used = {a["opis_id"] for a in self.document["attempts"] if a["fallback"]}
            for station in self.document["stations"][:limit]:
                current = self.document["results"].get(station["opis_id"])
                if (
                    not current
                    or current["classification"] == "accepted"
                    or "fallback" in current
                ):
                    continue
                if len(used) >= 10:
                    break
                if (
                    self.document["request_count"] >= 40
                    or sum(a["fallback"] for a in self.document["attempts"]) >= 10
                ):
                    break
                used.add(station["opis_id"])
                current["fallback"] = self.query(station, fallback=True)
                save(self.path, self.document)
                if self.document["status"] == "stopped_auth_or_quota":
                    return
        self.document["status"] = (
            "awaiting_manual_review"
            if self.document["request_count"] < 40
            else "request_budget_exhausted"
        )
        save(self.path, self.document)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/fuel-prices.csv")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/geocoding-feasibility.json"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Make live requests only after explicit approval",
    )
    parser.add_argument("--limit", type=int, choices=(5, 30), default=5)
    parser.add_argument("--fallbacks", action="store_true")
    parser.add_argument(
        "--pilot-reviewed",
        action="store_true",
        help="Confirm pilot inspection before the remaining sample",
    )
    args = parser.parse_args(argv)
    if not args.live:
        if args.output.exists():
            parser.error(
                "Output exists; choose a different path to avoid losing checkpoints"
            )
        document = prepare(args.source, args.output)
    else:
        key = os.environ.get("GEOAPIFY_API_KEY", "").strip()
        if not key:
            parser.error("GEOAPIFY_API_KEY is required in the local environment")
        if not args.output.exists():
            parser.error("Prepare the sample without --live first")
        document = json.loads(args.output.read_text())
        sample, _ = select_sample(args.source)
        if document["policy"] != POLICY or document["stations"] != sample:
            parser.error("Checkpoint sample/policy mismatch; prepare a new artifact")
        if (
            document["max_requests"] != 40
            or document["request_count"] != len(document["attempts"])
            or not 0 <= document["request_count"] <= 40
        ):
            parser.error("Invalid checkpoint budget")
        if args.limit == 30 and (
            not args.pilot_reviewed
            or not all(s["opis_id"] in document["results"] for s in sample[:5])
        ):
            parser.error(
                "Run and inspect the five-station pilot first; then use --pilot-reviewed"
            )
        with httpx.Client(
            timeout=httpx.Timeout(15, connect=5), follow_redirects=False
        ) as client:
            Runner(client, key, args.output, document).run(args.limit, args.fallbacks)
    print(
        json.dumps(
            {
                "status": document["status"],
                "sample_size": len(document["stations"]),
                "request_count": document["request_count"],
                "results": len(document["results"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
