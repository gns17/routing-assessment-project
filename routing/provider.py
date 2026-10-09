"""Geoapify transport boundary; station enrichment is deliberately absent."""

import hashlib
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

import httpx

from routing.geometry import distance, points

US_STATES = {
    "AL",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
}
METERS_PER_MILE = Decimal("1609.344")


class ProviderError(Exception):
    def __init__(self, code, message, status=502, details=None):
        self.code, self.message, self.status = code, message, status
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    label: str


@dataclass(frozen=True)
class Route:
    start: Location
    finish: Location
    geometry: dict
    distance_miles: Decimal
    duration_seconds: float
    segment_miles: tuple[Decimal, ...] | None = None


def road_weights(geometry, properties, miles):
    """Use documented leg step distances; interpolate only within each step.

    No extra provider details/request is needed. Absent legs fall back explicitly;
    supplied inconsistent step indexes/distances fail rather than being trusted.
    """
    legs = properties.get("legs")
    if legs is None:
        return None
    lines = (
        [geometry["coordinates"]]
        if geometry["type"] == "LineString"
        else geometry["coordinates"]
    )
    if not isinstance(legs, list) or len(legs) != len(lines):
        raise ValueError
    weights = []
    for line, leg in zip(lines, legs, strict=True):
        steps = leg["steps"]
        if not isinstance(steps, list) or not steps:
            raise ValueError
        lengths = [distance(a, b) for a, b in pairwise(line)]
        cursor = 0
        for step in steps:
            first, last, meters = step["from_index"], step["to_index"], step["distance"]
            if (
                any(type(i) is not int for i in (first, last))
                or first != cursor
                or not first <= last < len(line)
                or not number(meters, 0, 50_000_000)
            ):
                raise ValueError
            span = lengths[first:last]
            length = sum(span)
            if not length:
                if meters:
                    raise ValueError
                weights.extend(Decimal(0) for _ in span)
            else:
                step_miles = Decimal(str(meters)) / METERS_PER_MILE
                allocation = [step_miles * Decimal(str(part / length)) for part in span]
                allocation[-1] += step_miles - sum(allocation)
                weights.extend(allocation)
            cursor = last
        if cursor != len(line) - 1:
            raise ValueError
    total = sum(weights)
    if not total or abs(total - miles) > max(
        Decimal("0.006214"), miles * Decimal("0.01")
    ):
        raise ValueError
    weights = [w * miles / total for w in weights]
    weights[-1] += miles - sum(weights)
    return tuple(weights)


def number(value, low, high):
    return (
        isinstance(value, (float, int))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and low <= value <= high
    )


class Geoapify:
    def __init__(self, key, client=None, cache=None):
        if not key:
            raise ProviderError(
                "provider_not_configured", "Routing provider is not configured", 503
            )
        self.key, self.cache = key, cache
        self.client = client or httpx.Client()
        self.owns_client = client is None
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.owns_client:
            self.client.close()

    def cache_key(self, kind, value):
        digest = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        return f"geoapify-v2:{kind}:{digest}"

    def cached(self, key):
        return self.cache.get(key) if self.cache is not None else None

    def remember(self, key, value, ttl):
        if self.cache is not None:
            self.cache.set(key, value, ttl)

    def request(self, endpoint, params):
        if self.calls >= 3:
            raise ProviderError("request_limit", "Provider request limit reached", 503)
        self.calls += 1
        try:
            response = self.client.get(
                "https://api.geoapify.com/v1/" + endpoint,
                params={**params, "apiKey": self.key},
                timeout=httpx.Timeout(15, connect=5),
                follow_redirects=False,
            )
        except httpx.RequestError:
            raise ProviderError(
                "provider_unavailable", "Routing provider could not be reached", 503
            ) from None
        if response.status_code == 429:
            raise ProviderError(
                "provider_rate_limited",
                "Routing provider quota is temporarily unavailable",
                503,
            )
        if response.status_code in (401, 403):
            raise ProviderError(
                "provider_authentication", "Routing provider authentication failed", 503
            )
        if response.status_code >= 500:
            raise ProviderError(
                "provider_unavailable",
                "Routing provider is temporarily unavailable",
                503,
            )
        if response.status_code != 200:
            raise ProviderError(
                "provider_response", "Routing provider could not process this request"
            )
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise TypeError
            return data
        except (ValueError, TypeError):
            raise ProviderError(
                "provider_response", "Routing provider returned invalid data"
            ) from None

    def geocode(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 300:
            raise ProviderError(
                "invalid_location",
                "Provide a location string of at most 300 characters",
                400,
            )
        text = " ".join(text.split())
        key = self.cache_key("location", text.casefold())
        cached = self.cached(key)
        if cached is not None:
            return cached
        data = self.request(
            "geocode/search",
            {
                "text": text,
                "filter": "countrycode:us",
                "format": "json",
                "limit": 5,
                "lang": "en",
            },
        )
        rows = data.get("results")
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise ProviderError("provider_response", "Geocoder returned invalid data")
        valid = []
        for row in rows:
            rank = row.get("rank") or {}
            if (
                row.get("country_code") == "us"
                and isinstance(row.get("state_code"), str)
                and row.get("state_code") in US_STATES
                and number(row.get("lat"), -90, 90)
                and number(row.get("lon"), -180, 180)
                and isinstance(rank, dict)
                and number(rank.get("confidence"), 0.8, 1)
            ):
                point = Location(
                    row["lat"], row["lon"], str(row.get("formatted", text))
                )
                if not any(
                    abs(point.latitude - p.latitude) < 0.0001
                    and abs(point.longitude - p.longitude) < 0.0001
                    for p in valid
                ):
                    valid.append(point)
        if not valid:
            raise ProviderError(
                "location_not_resolved",
                "Provide a more specific contiguous-US location",
                422,
            )
        if len(valid) > 1:
            raise ProviderError(
                "ambiguous_location",
                "Location is ambiguous; include address, city and state",
                422,
            )
        self.remember(key, valid[0], 86400)
        return valid[0]

    def route(self, start_text, finish_text):
        start, finish = self.geocode(start_text), self.geocode(finish_text)
        key = self.cache_key(
            "route",
            [
                start.latitude,
                start.longitude,
                finish.latitude,
                finish.longitude,
                "drive",
                "metric",
            ],
        )
        cached = self.cached(key)
        if cached is not None:
            return Route(start, finish, *cached)
        if (start.latitude, start.longitude) == (finish.latitude, finish.longitude):
            return Route(
                start,
                finish,
                {
                    "type": "LineString",
                    "coordinates": [
                        [start.longitude, start.latitude],
                        [finish.longitude, finish.latitude],
                    ],
                },
                Decimal(0),
                0,
            )
        data = self.request(
            "routing",
            {
                "waypoints": f"{start.latitude},{start.longitude}|{finish.latitude},{finish.longitude}",
                "mode": "drive",
                "units": "metric",
                "format": "geojson",
            },
        )
        features = data.get("features")
        if not isinstance(features, list):
            raise ProviderError("provider_response", "Router returned invalid data")
        if not features:
            raise ProviderError("route_not_found", "No driving route was found", 422)
        try:
            feature = features[0]
            geometry, properties = feature["geometry"], feature["properties"]
            if not isinstance(geometry, dict) or not isinstance(properties, dict):
                raise TypeError
            units = properties.get("distance_units", "meters")
            if not isinstance(units, str) or units.lower() != "meters":
                raise ValueError
            lines = (
                [geometry["coordinates"]]
                if geometry["type"] == "LineString"
                else geometry["coordinates"]
            )
            if geometry["type"] not in ("LineString", "MultiLineString") or not lines:
                raise ValueError
            for line in lines:
                if not isinstance(line, list) or len(line) < 2:
                    raise ValueError
                for point in line:
                    if (
                        not isinstance(point, list)
                        or len(point) < 2
                        or not number(point[0], -180, 180)
                        or not number(point[1], -90, 90)
                    ):
                        raise ValueError
            if not number(properties["distance"], 0, 50_000_000) or not number(
                properties["time"], 0, 10_000_000
            ):
                raise ValueError
            miles = Decimal(str(properties["distance"])) / METERS_PER_MILE
            duration = properties["time"]
            flat = points(geometry)
            if not miles or not any(distance(a, b) for a, b in pairwise(flat)):
                raise ValueError
            weights = road_weights(geometry, properties, miles)
        except (KeyError, TypeError, ValueError, IndexError):
            raise ProviderError(
                "provider_response", "Router returned invalid geometry or distance"
            ) from None
        self.remember(key, (geometry, miles, duration, weights), 3600)
        return Route(start, finish, geometry, miles, duration, weights)
