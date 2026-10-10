"""HTTP finishes before the repository read transaction."""

import hashlib
import json
from decimal import Decimal
from itertools import pairwise

from routing.fuel import RANGE, FuelStation, UnreachableRoute, optimize
from routing.geometry import bounds, match_stations
from routing.provider import ProviderError

WARNINGS = [
    "Station coverage is incomplete; only identity-reconciled coordinates are eligible.",
    "Prices are a fixed snapshot; conflicting duplicate prices use the lowest listing.",
    "Road access and station detours are unverified and excluded from fuel estimates.",
    "US endpoints are validated; the provider route may cross international borders.",
]


def displayed(value, places="0.000001"):
    return str(value.quantize(Decimal(places)))


def coverage(distance, matches, candidates):
    positions = sorted({Decimal(0), distance, *(m.miles for m in matches)})
    gaps = list(pairwise(positions))
    return {
        "scope": "reviewed_candidates_only",
        "complete_csv_coverage": False,
        "eligible_candidates": len(candidates),
        "matched_stations": len({m.station.opis_id for m in matches}),
        "route_visits": len(matches),
        "largest_gap_miles": displayed(
            max((b - a for a, b in gaps), default=Decimal(0))
        ),
        "unbridgeable_gaps": [
            {
                "from_miles": displayed(a),
                "to_miles": displayed(b),
                "gap_miles": displayed(b - a),
            }
            for a, b in gaps
            if b - a > RANGE
        ],
    }


def plan(route, repository, cache, corridor):
    revision, candidates = repository.snapshot(bounds(route.geometry, corridor))
    identity = [
        route.geometry,
        str(route.distance_miles),
        route.duration_seconds,
        [str(m) for m in route.segment_miles]
        if route.segment_miles is not None
        else None,
        revision,
        corridor,
        "full50-mpg10-matcher-v2",
    ]
    key = (
        "fuel-plan:"
        + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    )
    cached = cache.get(key)
    if cached is not None:
        return cached
    matches = match_stations(
        route.geometry, route.distance_miles, candidates, corridor, route.segment_miles
    )
    diagnostics = coverage(route.distance_miles, matches, candidates)
    indexed = {str(index): match for index, match in enumerate(matches)}
    try:
        fuel = optimize(
            route.distance_miles,
            [
                FuelStation(index, m.miles, m.station.price)
                for index, m in indexed.items()
            ],
        )
    except UnreachableRoute:
        raise ProviderError(
            "insufficient_station_coverage",
            "Verified station coverage cannot support this route within the 500-mile range",
            422,
            details={"coverage": diagnostics, "dataset_revision": revision},
        ) from None
    stops = []
    for purchase in fuel.purchases:
        match = indexed[purchase.station_id]
        station = match.station
        stops.append(
            {
                "opis_id": station.opis_id,
                "name": station.name,
                "address": station.address,
                "city": station.city,
                "state": station.state,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "price_per_gallon": str(station.price),
                "route_miles": displayed(match.miles),
                "offset_miles": match.offset_miles,
                "gallons_purchased": displayed(purchase.gallons),
                "purchase_cost": displayed(purchase.cost, "0.01"),
                "arrival_gallons": displayed(purchase.arrival_gallons),
                "departure_gallons": displayed(purchase.departure_gallons),
            }
        )
    payload = {
        "route": {"type": "Feature", "geometry": route.geometry, "properties": {}},
        "distance_miles": displayed(route.distance_miles),
        "duration_seconds": route.duration_seconds,
        "fuel_stops": stops,
        "total_fuel_cost": displayed(fuel.total_cost, "0.01"),
        "gallons_consumed": displayed(fuel.gallons_consumed),
        "gallons_purchased": displayed(fuel.gallons_purchased),
        "ending_gallons": displayed(fuel.ending_gallons),
        "initial_tank_cost": None,
        "dataset_revision": revision,
        "corridor_miles": corridor,
        "coverage": diagnostics,
        "mileage_method": "provider_steps"
        if route.segment_miles is not None
        else "scaled_geometry",
        "warnings": [
            *WARNINGS,
            "Station positions interpolate within provider steps; road access remains unverified."
            if route.segment_miles is not None
            else "No provider step mileage available: positions approximate geometry proportions scaled to total road distance.",
        ],
    }
    cache.set(key, payload, 3600)
    return payload
