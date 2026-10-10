"""Conditional fuel scenarios. No Django models, HTTP, station writes or optimizer edits."""

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from routing.fallback_data import locality_key
from routing.fuel import MPG, RANGE, TANK, FuelStation, UnreachableRoute, optimize
from routing.geometry import Candidate, bounds, match_stations
from routing.planning import displayed
from routing.provider import ProviderError

POLICY = "conditional-areas-v1"
WARNINGS = [
    {
        "code": "conditional_scenario",
        "message": "Fuel quantities and expenditure are conditional on assumed locations and availability; not driving instructions.",
    },
    {
        "code": "unverified_driving_feasibility",
        "message": "The mathematical scenario does not establish reachable fuel stops or a 500-mile driving guarantee.",
    },
    {
        "code": "unknown_station_position",
        "message": "A locality reference point does not establish where any associated station is located.",
    },
    {
        "code": "unverified_access_detours",
        "message": "Entrances, access detours, fuel availability and additional mileage are excluded and unverified.",
    },
    {
        "code": "route_access_and_chainage_approximation",
        "message": "Positions interpolate within provider steps, or use scaled geometry when steps are absent. US endpoints do not ensure the whole route stays in the US.",
    },
    {
        "code": "historical_snapshot_prices",
        "message": "CSV snapshot prices remain attached to OPIS identities; current prices and the initial tank cost are unknown.",
    },
]


@dataclass(frozen=True)
class SeedStation:
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    price: Decimal
    fingerprint: str
    latitude: float | None
    longitude: float | None
    enrichment_status: str
    enrichment_fingerprint: str
    enrichment_policy: str
    enrichment_metadata: dict

    @property
    def verified(self):
        return (
            self.enrichment_status == "accepted"
            and self.latitude is not None
            and self.longitude is not None
            and self.enrichment_fingerprint == self.fingerprint
            and bool(self.enrichment_policy)
        )

    def identity(self):
        # No coordinates in seed identity. A town anchor is never assigned to it.
        return {
            "opis_id": self.opis_id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "price_per_gallon": str(self.price),
        }


@dataclass(frozen=True)
class ScenarioLocation:
    id: str
    quality: str
    label: str
    latitude: float
    longitude: float
    stations: tuple[SeedStation, ...]
    source: dict
    road_uncertainty: Decimal | None
    access_bound: Decimal | None

    @property
    def chosen(self):
        return min(self.stations, key=lambda s: (s.price, s.opis_id))

    def payload(self):
        area = self.quality == "locality_approximation"
        return {
            "location_id": self.id,
            "location_quality": self.quality,
            "label": self.label,
            "assumed_point": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "represents": "locality reference point, NOT station location"
                if area
                else "station site, NOT verified entrance",
            },
            "candidate_stations": [
                s.identity()
                for s in sorted(self.stations, key=lambda s: (s.price, s.opis_id))
            ],
            "modeled_price_candidate_opis_id": self.chosen.opis_id,
            "modeled_price_per_gallon": str(self.chosen.price),
            "provenance": self.source,
            "uncertainty": {
                "route_mile_bound": str(self.road_uncertainty)
                if self.road_uncertainty is not None
                else None,
                "access_detour_bound_miles": str(self.access_bound)
                if self.access_bound is not None
                else None,
                "station_position_known": self.quality == "verified_station_site",
                "position_is_physical_estimate": self.quality
                == "estimated_physical_station",
                "entrance_verified": False,
            },
            "navigation_destination": False,
        }


def locations(stations, catalog):
    groups = defaultdict(list)
    result = []
    stale = 0
    for station in stations:
        if station.verified:
            result.append(
                ScenarioLocation(
                    f"verified:{station.opis_id}",
                    "verified_station_site",
                    station.name,
                    station.latitude,
                    station.longitude,
                    (station,),
                    station.enrichment_metadata,
                    Decimal(0),
                    None,
                )
            )
            continue
        estimated = catalog.station_estimates.get(station.opis_id)
        if estimated and estimated["location_fingerprint"] == station.fingerprint:
            bound = estimated.get("route_mile_uncertainty")
            access = estimated.get("access_detour_bound_miles")
            result.append(
                ScenarioLocation(
                    f"estimated:{station.opis_id}",
                    "estimated_physical_station",
                    station.name,
                    estimated["latitude"],
                    estimated["longitude"],
                    (station,),
                    {
                        "source": estimated["source"],
                        "identity_evidence": estimated["evidence"],
                        "uncertainty_evidence": estimated["uncertainty"],
                        "bound_evidence": estimated.get("bound_evidence"),
                    },
                    Decimal(str(bound)) if bound is not None else None,
                    Decimal(str(access)) if access is not None else None,
                )
            )
        else:
            if estimated:
                stale += 1
            groups[locality_key(station.city, station.state)].append(station)
    for key, group in sorted(groups.items()):
        point = catalog.localities.get(key)
        if point:
            result.append(
                ScenarioLocation(
                    f"locality:{key}",
                    "locality_approximation",
                    f"{point['city']}, {point['state']}",
                    point["latitude"],
                    point["longitude"],
                    tuple(group),
                    point["source"],
                    None,
                    None,
                )
            )
    return result, stale


def reference_inventory(distance, purchases, reference_positions):
    """Check a modeled scenario at independent positions if supplied for validation.

    A negative intermediate inventory cannot be hidden by a balanced final sum.
    This helper never changes optimized purchases or reads models/reference files.
    """
    inventory, position = TANK, Decimal(0)
    arrivals = []
    for purchase in purchases:
        actual = reference_positions[purchase.station_id]
        if actual < position:
            return {"valid": False, "reason": "reference_order_changed"}
        inventory -= (actual - position) / MPG
        arrivals.append(inventory)
        if inventory < 0 or inventory + purchase.gallons > TANK:
            return {
                "valid": False,
                "reason": "reference_inventory_violation",
                "arrival_gallons": str(inventory),
            }
        inventory += purchase.gallons
        position = actual
    inventory -= (distance - position) / MPG
    return {
        "valid": inventory >= 0,
        "ending_gallons": str(inventory),
        "minimum_arrival_gallons": str(min(arrivals, default=TANK)),
    }


def conservative_check(distance, purchases, indexed):
    # Unknown is not zero. Site-coordinate confidence never becomes an access bound.
    # Check only purchased locations; an unused unbounded hint must not hide a
    # violation at a used bounded station. Mixed unknown segments remain unknown.
    unknown = False
    inventory_low = inventory_high = TANK
    prior_low = prior_high = Decimal(0)
    for purchase in purchases:
        match, loc = indexed[purchase.station_id]
        if loc.road_uncertainty is None or loc.access_bound is None:
            unknown = True
            break
        low = max(Decimal(0), match.miles - loc.road_uncertainty)
        high = min(distance, match.miles + loc.road_uncertainty)
        maximum = high - prior_low + loc.access_bound
        minimum = max(Decimal(0), low - prior_high)
        if maximum > RANGE or inventory_low - maximum / MPG < 0:
            return {
                "status": "violated",
                "reason": "Worst-case arrival inventory or range fails supplied bounds.",
            }
        inventory_low -= maximum / MPG
        inventory_high -= minimum / MPG
        if inventory_high + purchase.gallons > TANK:
            return {
                "status": "violated",
                "reason": "Fixed modeled purchase could exceed tank capacity within supplied bounds.",
            }
        inventory_low += purchase.gallons
        inventory_high += purchase.gallons
        prior_low, prior_high = low, high
    if unknown:
        return {
            "status": "unknown",
            "reason": "Unbounded station position or driving access; no safety margin invented.",
        }
    if distance - prior_low > RANGE or inventory_low - (distance - prior_low) / MPG < 0:
        return {
            "status": "violated",
            "reason": "Worst-case final fuel inventory fails supplied bounds.",
        }
    return {
        "status": "within_supplied_bounds",
        "reason": "Conditional model only; bound evidence is not a verified driving route.",
    }


def plan_best_effort(
    route, repository, cache, catalog, station_corridor=1, area_corridor=10
):
    revision, stations = repository.snapshot()
    identity = [
        route.geometry,
        str(route.distance_miles),
        route.duration_seconds,
        [str(x) for x in route.segment_miles]
        if route.segment_miles is not None
        else None,
        revision,
        catalog.version,
        station_corridor,
        area_corridor,
        POLICY,
        "best_effort",
    ]
    key = (
        "best-effort-plan:"
        + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    )
    cached = cache.get(key)
    if cached is not None:
        return cached
    prepared, stale = locations(stations, catalog)
    # Internal IDs identify scenario locations, never invented OPIS stations.
    groups = {n: loc for n, loc in enumerate(prepared)}
    matched = []
    for area, corridor in [(False, station_corridor), (True, area_corridor)]:
        south, north, west, east = bounds(route.geometry, corridor)
        candidates = [
            Candidate(
                n, loc.label, "", "", "", loc.chosen.price, loc.latitude, loc.longitude
            )
            for n, loc in groups.items()
            if (loc.quality == "locality_approximation") == area
            and south <= loc.latitude <= north
            and west <= loc.longitude <= east
        ]
        visits = match_stations(
            route.geometry,
            route.distance_miles,
            candidates,
            corridor,
            route.segment_miles,
        )
        if area:
            # One assumed opportunity per locality, not independent fuel stops
            # each time a broad area overlaps a different route segment.
            closest = {}
            for visit in visits:
                previous = closest.get(visit.station.opis_id)
                if previous is None or (visit.offset_miles, visit.miles) < (
                    previous.offset_miles,
                    previous.miles,
                ):
                    closest[visit.station.opis_id] = visit
            visits = list(closest.values())
        matched.extend(visits)
    matched.sort(key=lambda m: (m.miles, m.station.price, m.station.opis_id))
    indexed = {
        str(n): (match, groups[match.station.opis_id])
        for n, match in enumerate(matched)
    }
    counts = Counter()
    for loc in prepared:
        counts[loc.quality] += len(loc.stations)
    matched_ids = {match.station.opis_id for match in matched}
    diagnostics = {
        "complete_csv_coverage": False,
        "scope": "conditional_location_hints",
        "candidate_count_units": "OPIS records, not independently located stations",
        "candidate_counts": {
            quality: counts[quality]
            for quality in [
                "verified_station_site",
                "estimated_physical_station",
                "locality_approximation",
            ]
        },
        "seed_stations": len(stations),
        "unique_location_hints": len(prepared),
        "matched_location_hints": len(matched_ids),
        "route_candidate_counts": {
            quality: sum(
                len(groups[n].stations)
                for n in matched_ids
                if groups[n].quality == quality
            )
            for quality in [
                "verified_station_site",
                "estimated_physical_station",
                "locality_approximation",
            ]
        },
        "route_location_counts": {
            quality: sum(groups[n].quality == quality for n in matched_ids)
            for quality in [
                "verified_station_site",
                "estimated_physical_station",
                "locality_approximation",
            ]
        },
        "unlocated_stations": len(stations) - sum(counts.values()),
        "stale_estimated_identities_excluded": stale,
        "locality_search_corridor_miles": area_corridor,
        "locality_corridor_is_not_station_access_bound": True,
    }
    positions = sorted({Decimal(0), route.distance_miles, *(m.miles for m in matched)})
    diagnostics["largest_assumed_gap_miles"] = displayed(
        max((b - a for a, b in pairwise(positions)), default=Decimal(0))
    )
    try:
        fuel = optimize(
            route.distance_miles,
            [
                FuelStation(index, m.miles, loc.chosen.price)
                for index, (m, loc) in indexed.items()
            ],
        )
    except UnreachableRoute:
        raise ProviderError(
            "insufficient_best_effort_coverage",
            "Location hints cannot construct even a conditional 500-mile-range scenario",
            422,
            details={
                "planning_mode": "best_effort",
                "status": "unavailable",
                "fuel_feasibility": "unverified",
                "coverage": diagnostics,
                "dataset_revision": revision,
                "location_data_version": catalog.version,
                "warning_codes": [w["code"] for w in WARNINGS],
            },
        ) from None
    purchased = []
    for purchase in fuel.purchases:
        match, location = indexed[purchase.station_id]
        purchased.append(
            {
                **location.payload(),
                "assumed_route_miles": displayed(match.miles),
                "reference_point_offset_miles": match.offset_miles,
                "modeled_gallons_purchased": displayed(purchase.gallons),
                "conditional_purchase_cost": displayed(purchase.cost, "0.01"),
                "modeled_arrival_gallons": displayed(purchase.arrival_gallons),
                "modeled_departure_gallons": displayed(purchase.departure_gallons),
            }
        )
    bound_check = conservative_check(route.distance_miles, fuel.purchases, indexed)
    if bound_check["status"] == "violated":
        raise ProviderError(
            "uncertain_fuel_plan_rejected",
            "Conditional purchases fail conservative supplied uncertainty bounds",
            422,
            details={
                "planning_mode": "best_effort",
                "fuel_feasibility": "unverified",
                "uncertainty_check": bound_check,
                "coverage": diagnostics,
            },
        )
    payload = {
        "planning_mode": "best_effort",
        "status": "estimated",
        "fuel_feasibility": "unverified",
        "route": {"type": "Feature", "geometry": route.geometry, "properties": {}},
        "distance_miles": displayed(route.distance_miles),
        "duration_seconds": route.duration_seconds,
        "fuel_stops": [],
        "total_fuel_cost": None,
        "gallons_purchased": None,
        "estimated_fuel_expenditure": displayed(fuel.total_cost, "0.01"),
        "gallons_consumed": displayed(fuel.gallons_consumed),
        "initial_tank_cost": None,
        "conditional_scenario": {
            "mathematically_feasible_under_assumed_positions": True,
            "assumptions": {
                "initial_tank_gallons": 50,
                "tank_capacity_gallons": 50,
                "mpg": 10,
                "maximum_range_miles": 500,
                "ending_reserve_gallons": 0,
                "stop_penalty": 0,
                "locality_price_selection": "lowest associated CSV snapshot listing; hypothetical availability",
            },
            "gallons_purchased": displayed(fuel.gallons_purchased),
            "ending_gallons": displayed(fuel.ending_gallons),
            "purchases": purchased,
            "uncertainty_check": bound_check,
        },
        "approximate_fueling_areas": [
            p for p in purchased if p["location_quality"] == "locality_approximation"
        ],
        "dataset_revision": revision,
        "location_data_version": catalog.version,
        "location_data_provenance": catalog.provenance,
        "coverage": diagnostics,
        "mileage_method": "provider_steps"
        if route.segment_miles is not None
        else "scaled_geometry",
        "warnings": [w["message"] for w in WARNINGS],
        "warning_codes": [w["code"] for w in WARNINGS],
    }
    cache.set(key, payload, 3600)
    return payload
