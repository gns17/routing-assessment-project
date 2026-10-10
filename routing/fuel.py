"""Pure fixed-route purchasing model. No storage, framework, or HTTP dependencies."""

from dataclasses import dataclass
from decimal import Decimal

TANK = Decimal(50)
MPG = Decimal(10)
RANGE = TANK * MPG


class UnreachableRoute(ValueError):
    """The reconciled priced stations cannot bridge the supplied route."""


@dataclass(frozen=True)
class FuelStation:
    station_id: str
    miles: Decimal
    price: Decimal


@dataclass(frozen=True)
class Purchase:
    station_id: str
    miles: Decimal
    price: Decimal
    gallons: Decimal
    cost: Decimal
    arrival_gallons: Decimal
    departure_gallons: Decimal


@dataclass(frozen=True)
class FuelPlan:
    purchases: tuple[Purchase, ...]
    gallons_consumed: Decimal
    gallons_purchased: Decimal
    total_cost: Decimal
    ending_gallons: Decimal


def optimize(distance: Decimal, stations: list[FuelStation]) -> FuelPlan:
    """Optimal purchases on the given route, starting full, with no ending reserve.

    Inventory includes the free-to-this-journey initial tank. Fuel is divisible;
    stop penalties, access detours, supply constraints, and road choice are absent.
    """
    if not isinstance(distance, Decimal) or not distance.is_finite() or distance < 0:
        raise ValueError("Distance must be a finite nonnegative Decimal")
    for station in stations:
        if (
            not isinstance(station.miles, Decimal)
            or not station.miles.is_finite()
            or not 0 <= station.miles <= distance
            or not isinstance(station.price, Decimal)
            or not station.price.is_finite()
            or station.price <= 0
        ):
            raise ValueError("Invalid station position or price")
    ordered = sorted(stations, key=lambda s: (s.miles, s.price, s.station_id))
    # A co-located expensive station can never improve cost or reachability.
    points = []
    for station in ordered:
        if not points or station.miles != points[-1].miles:
            points.append(station)
    terminal = FuelStation("destination", distance, Decimal(0))
    points.append(terminal)
    inventory, position = TANK, Decimal(0)
    purchases = []
    for index, station in enumerate(points):
        used = (station.miles - position) / MPG
        if used > inventory:
            raise UnreachableRoute("No feasible fuel plan with reconciled stations")
        inventory -= used
        position = station.miles
        if station is terminal:
            break
        cheaper = next(
            (
                s
                for s in points[index + 1 :]
                if s.miles - position <= RANGE and s.price < station.price
            ),
            None,
        )
        target = (
            (cheaper.miles - position) / MPG
            if cheaper is not None
            else min(TANK, (distance - position) / MPG)
        )
        gallons = max(Decimal(0), target - inventory)
        if gallons:
            purchases.append(
                Purchase(
                    station.station_id,
                    position,
                    station.price,
                    gallons,
                    gallons * station.price,
                    inventory,
                    inventory + gallons,
                )
            )
            inventory += gallons
    bought = sum((p.gallons for p in purchases), Decimal(0))
    cost = sum((p.cost for p in purchases), Decimal(0))
    return FuelPlan(tuple(purchases), distance / MPG, bought, cost, inventory)
