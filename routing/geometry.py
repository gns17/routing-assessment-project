"""Storage-independent corridor matching with approximate road chainage."""

import math
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

EARTH_MILES = 3958.7613


@dataclass(frozen=True)
class Candidate:
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    price: Decimal
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Match:
    station: Candidate
    miles: Decimal
    offset_miles: float


def distance(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (*a[:2], *b[:2]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_MILES * math.asin(min(1, math.sqrt(h)))


def points(geometry):
    lines = (
        [geometry["coordinates"]]
        if geometry["type"] == "LineString"
        else geometry["coordinates"]
    )
    flattened = []
    for line in lines:
        if flattened and distance(flattened[-1], line[0]) > 0.000001:
            raise ValueError("Disconnected route geometry")
        flattened.extend(line if not flattened else line[1:])
    return flattened


def bounds(geometry, corridor):
    if not math.isfinite(corridor) or corridor <= 0:
        raise ValueError("Corridor must be positive and finite")
    coordinates = points(geometry)
    latitudes = [p[1] for p in coordinates]
    longitudes = [p[0] for p in coordinates]
    lat_pad = math.degrees(corridor / EARTH_MILES)
    lon_pad = lat_pad / max(
        0.01,
        math.cos(math.radians(max(abs(min(latitudes)), abs(max(latitudes))) + lat_pad)),
    )
    return (
        min(latitudes) - lat_pad,
        max(latitudes) + lat_pad,
        min(longitudes) - lon_pad,
        max(longitudes) + lon_pad,
    )


def match_stations(geometry, road_miles, candidates, corridor, segment_miles=None):
    """Project locally onto segments; road weights preserve provider step mileage.

    Nearby consecutive segments are one visit only when their shared vertex is
    also inside the corridor. Thus an out-and-back road preserves both visits.
    """
    if not math.isfinite(corridor) or corridor <= 0:
        raise ValueError("Corridor must be positive and finite")
    coordinates = points(geometry)
    lengths = [distance(a, b) for a, b in pairwise(coordinates)]
    total = sum(lengths)
    if not total:
        if road_miles:
            raise ValueError("Positive road distance with degenerate geometry")
        return []
    if segment_miles is None:
        weights = [road_miles * Decimal(str(length / total)) for length in lengths]
        weights[-1] += road_miles - sum(weights)
    else:
        weights = list(segment_miles)
        if (
            len(weights) != len(lengths)
            or any(not w.is_finite() or w < 0 for w in weights)
            or abs(sum(weights) - road_miles) > Decimal("0.000001")
        ):
            raise ValueError("Invalid segment mileage")
    segments, cumulative = [], Decimal(0)
    for a, b, length, weight in zip(
        coordinates, coordinates[1:], lengths, weights, strict=False
    ):
        if length:
            scale = math.cos(math.radians((a[1] + b[1]) / 2))
            dx, dy = (b[0] - a[0]) * scale, b[1] - a[1]
            lat_pad = math.degrees(corridor / EARTH_MILES) * 1.01
            lon_pad = lat_pad / max(
                0.01, math.cos(math.radians(max(abs(a[1]), abs(b[1])) + lat_pad))
            )
            box = (
                min(a[0], b[0]) - lon_pad,
                max(a[0], b[0]) + lon_pad,
                min(a[1], b[1]) - lat_pad,
                max(a[1], b[1]) + lat_pad,
            )
            segments.append((a, b, cumulative, weight, scale, dx, dy, box))
        elif weight:
            raise ValueError("Nonzero mileage on a zero-length segment")
        cumulative += weight
    matches = []
    for station in candidates:
        best = None
        location = [station.longitude, station.latitude]
        for a, b, start, weight, scale, dx, dy, box in segments:
            west, east, south, north = box
            if not (
                west <= station.longitude <= east and south <= station.latitude <= north
            ):
                if best is not None:
                    matches.append(best)
                    best = None
                continue
            px, py = (station.longitude - a[0]) * scale, station.latitude - a[1]
            fraction = max(0, min(1, (px * dx + py * dy) / (dx * dx + dy * dy)))
            projected = [
                a[0] + fraction * (b[0] - a[0]),
                a[1] + fraction * (b[1] - a[1]),
            ]
            offset = distance(projected, location)
            if offset <= corridor:
                position = min(
                    road_miles,
                    (start + weight * Decimal(str(fraction))).quantize(
                        Decimal("0.000001")
                    ),
                )
                current = Match(station, position, offset)
                if best is not None and distance(a, location) > corridor:
                    matches.append(best)
                    best = None
                if best is None or offset < best.offset_miles:
                    best = current
            elif best is not None:
                matches.append(best)
                best = None
        if best is not None:
            matches.append(best)
    return sorted(matches, key=lambda m: (m.miles, m.station.price, m.station.opis_id))
