"""Approved five-station comparison only; no nationwide or runtime integration."""

import argparse
import json
import os
import time
from datetime import UTC, datetime

import httpx
from dotenv import load_dotenv

from spikes.geocoding import ENDPOINT, ROOT, finite_number, redact, save

NAMES = {
    "105": "TA Saginaw",
    "1028": "Four States Truck Stop",
    "64211": "Pilot #490",
    "67682": "Casey's #2739",
    "368": "Wilton Travel Plaza",
}
PLACES_ENDPOINT = "https://api.geoapify.com/v2/places"
POLICY = "five-station-name-places-v1"


def tasks(document):
    stations = document["stations"][:5]
    if {s["opis_id"] for s in stations} != set(NAMES):
        raise ValueError("Only the original five pilot stations are authorized")
    items = []
    for station in stations:
        opis_id = station["opis_id"]
        params = {
            "name": NAMES[opis_id],
            "city": station["city"],
            "state": station["state"],
            "country": "United States",
            "filter": "countrycode:us",
            "type": "amenity",
            "format": "json",
            "limit": 5,
            "lang": "en",
        }
        items.append(
            {
                "opis_id": opis_id,
                "approach": "name_first",
                "endpoint": ENDPOINT,
                "params": params,
            }
        )
    for station in stations:
        opis_id = station["opis_id"]
        # Existing first candidates supply approximate locality anchors, not station identity.
        anchor = document["results"][opis_id]["candidates"][0]["match"]
        lat, lon = anchor["lat"], anchor["lon"]
        if not finite_number(lat, -90, 90) or not finite_number(lon, -180, 180):
            raise ValueError("Invalid locality anchor")
        params = {
            "categories": "service.vehicle.fuel",
            "filter": f"circle:{lon},{lat},10000",
            "bias": f"proximity:{lon},{lat}",
            "limit": 20,
            "lang": "en",
        }
        items.append(
            {
                "opis_id": opis_id,
                "approach": "places",
                "endpoint": PLACES_ENDPOINT,
                "params": params,
                "anchor": {
                    "lat": lat,
                    "lon": lon,
                    "source": "original_pilot_top_candidate",
                    "station_coordinate": False,
                },
            }
        )
    return items


def assess(task, payload):
    if task["approach"] == "name_first":
        rows = payload.get("results") if isinstance(payload, dict) else None
    else:
        rows = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError("Malformed candidate schema")
    return {
        "raw_response": payload,
        "candidate_count": len(rows),
        "potentially_truncated": len(rows) >= task["params"]["limit"],
        "classification": "ambiguous",
        "reason": "identity_review_required" if rows else "empty_search_inconclusive",
        "manual_review": "pending",
    }


class Comparison:
    def __init__(
        self, client, key, path, document, clock=time.monotonic, sleep=time.sleep
    ):
        self.client, self.key, self.path, self.document = client, key, path, document
        self.clock, self.sleep, self.last_started = clock, sleep, None
        self.queries = tasks(document)
        self.state = document.setdefault(
            "comparison",
            {
                "policy": POLICY,
                "max_attempts": 15,
                "attempt_count": 0,
                "attempts": [],
                "results": {},
                "status": "prepared",
            },
        )
        if (
            self.state["policy"] != POLICY
            or self.state["max_attempts"] != 15
            or self.state["attempt_count"] != len(self.state["attempts"])
            or not 0 <= self.state["attempt_count"] <= 15
        ):
            raise ValueError("Invalid comparison checkpoint/budget")

    def checkpoint(self):
        self.document["total_http_attempts"] = (
            self.document["request_count"] + self.state["attempt_count"]
        )
        save(self.path, self.document)

    def request(self, task):
        query_id = task["approach"] + ":" + task["opis_id"]
        prior = [a for a in self.state["attempts"] if a["query_id"] == query_id]
        for attempt in reversed(prior):
            if "result" in attempt:
                return attempt["result"]
        for retry in range(len(prior), 2):
            retries_used = sum(a["retry"] > 0 for a in self.state["attempts"])
            if self.state["attempt_count"] >= 15 or (retry and retries_used >= 5):
                return {
                    "classification": "ambiguous",
                    "reason": "budget_exhausted",
                    "candidate_count": 0,
                }
            if self.last_started is not None:
                self.sleep(max(0, 1 - (self.clock() - self.last_started)))
            attempt = {
                "query_id": query_id,
                "retry": retry,
                "started_at": datetime.now(UTC).isoformat(),
                "request": task,
                "status": "interrupted_or_pending",
            }
            self.state["attempt_count"] += 1
            self.state["attempts"].append(attempt)
            self.checkpoint()  # Reserve attempts before network execution.
            start = self.clock()
            self.last_started = start
            retryable, fatal = False, False
            try:
                response = self.client.get(
                    task["endpoint"], params={**task["params"], "apiKey": self.key}
                )
                attempt["http_status"] = response.status_code
                if response.status_code == 200:
                    result = assess(task, response.json())
                    attempt["status"] = "ok"
                else:
                    attempt["status"] = f"http_{response.status_code}"
                    fatal = response.status_code in (401, 403, 429)
                    retryable = response.status_code >= 500
                    result = {
                        "classification": "ambiguous",
                        "reason": attempt["status"],
                        "candidate_count": 0,
                    }
            except httpx.RequestError:
                attempt["status"] = "transport_error"
                retryable = True
                result = {
                    "classification": "ambiguous",
                    "reason": "transport_error",
                    "candidate_count": 0,
                }
            except (ValueError, TypeError):
                attempt["status"] = "malformed_response"
                result = {
                    "classification": "ambiguous",
                    "reason": "malformed_response",
                    "candidate_count": 0,
                }
            attempt["latency_ms"] = round((self.clock() - start) * 1000, 2)
            result = redact(result, self.key)
            if fatal or not retryable or retry == 1:
                attempt["result"] = result
            if fatal:
                self.state["status"] = "stopped_auth_or_quota"
            self.checkpoint()
            if retryable and retry == 0 and retries_used < 5:
                self.sleep(2)
                continue
            return result
        return {
            "classification": "ambiguous",
            "reason": "interrupted_attempts_exhausted",
            "candidate_count": 0,
        }

    def run(self):
        if self.state["status"] == "stopped_auth_or_quota":
            return
        self.state["status"] = "running"
        for task in self.queries:
            query_id = task["approach"] + ":" + task["opis_id"]
            if query_id in self.state["results"]:
                continue
            self.state["results"][query_id] = self.request(task)
            self.checkpoint()
            if self.state["status"] == "stopped_auth_or_quota":
                return
        self.state["status"] = "complete_awaiting_identity_review"
        self.checkpoint()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    path = ROOT / "data/geocoding-feasibility.json"
    document = json.loads(path.read_text())
    if not args.live:
        print(json.dumps(tasks(document), indent=2))
        return
    load_dotenv(ROOT / ".env", override=True)
    key = os.environ.get("GEOAPIFY_API_KEY", "").strip()
    if not key:
        parser.error("GEOAPIFY_API_KEY is required; value will not be logged")
    with httpx.Client(
        timeout=httpx.Timeout(15, connect=5), follow_redirects=False
    ) as client:
        comparison = Comparison(client, key, path, document)
        comparison.run()
        print(
            json.dumps(
                {
                    "comparison_attempts": comparison.state["attempt_count"],
                    "status": comparison.state["status"],
                }
            )
        )


if __name__ == "__main__":
    main()
