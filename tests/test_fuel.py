import random
from decimal import Decimal as D

import pytest

from routing.fuel import FuelStation, UnreachableRoute, optimize


def station(identifier, miles, price):
    return FuelStation(identifier, D(miles), D(price))


def test_short_trip_uses_initial_inventory_without_purchases():
    plan = optimize(D(100), [station("cheap", 50, 1)])
    assert plan.total_cost == 0 and plan.gallons_purchased == 0
    assert plan.gallons_consumed == 10 and plan.ending_gallons == 40


def test_exact_range_and_unreachable():
    assert optimize(D(500), []).ending_gallons == 0
    with pytest.raises(UnreachableRoute):
        optimize(D("500.0001"), [])
    with pytest.raises(UnreachableRoute):
        optimize(D(1200), [station("a", 400, 3), station("b", 901, 2)])


def test_partial_fill_to_cheaper_station_and_final_purchase():
    plan = optimize(D(1200), [station("expensive", 400, 4), station("cheap", 700, 2)])
    assert [(p.station_id, p.gallons) for p in plan.purchases] == [
        ("expensive", D(20)),
        ("cheap", D(50)),
    ]
    assert plan.total_cost == 180
    assert plan.gallons_consumed == 120 and plan.gallons_purchased == 70
    assert plan.ending_gallons == 0


def test_competing_prices_and_same_position():
    plan = optimize(D(900), [station("costly", 400, 9), station("cheap", 400, 2)])
    assert len(plan.purchases) == 1
    assert plan.purchases[0].station_id == "cheap"
    assert plan.purchases[0].gallons == 40
    assert plan.total_cost == 80


def test_inventory_conservation_and_decimal_precision():
    plan = optimize(
        D("1000.25"), [station("a", "400.25", "3.00733333"), station("b", 800, "2.9")]
    )
    assert D(50) + plan.gallons_purchased - plan.gallons_consumed == plan.ending_gallons
    assert all(
        0 <= p.arrival_gallons <= p.departure_gallons <= 50 for p in plan.purchases
    )
    assert plan.total_cost == sum(p.cost for p in plan.purchases)


@pytest.mark.parametrize("distance", [D(-1), D("NaN"), D("Infinity"), 100])
def test_invalid_distance(distance):
    with pytest.raises(ValueError):
        optimize(distance, [])


@pytest.mark.parametrize(
    "item",
    [
        station("a", -1, 3),
        station("a", 101, 3),
        station("a", 20, 0),
        station("a", 20, "NaN"),
    ],
)
def test_invalid_station(item):
    with pytest.raises(ValueError):
        optimize(D(100), [item])


def oracle(distance, stops):
    """Enumerate every integer-gallon purchase, not the greedy decision rule."""
    states = {50: D(0)}
    previous = 0
    for miles, price in stops + [(distance, None)]:
        burn = (miles - previous) // 10
        arrivals = {fuel - burn: cost for fuel, cost in states.items() if fuel >= burn}
        if not arrivals:
            return None
        if price is None:
            return min(arrivals.values())
        states = {}
        for fuel, cost in arrivals.items():
            for buy in range(51 - fuel):
                total = cost + D(buy) * D(price)
                states[fuel + buy] = min(states.get(fuel + buy, D("Infinity")), total)
        previous = miles


def test_greedy_matches_exhaustive_optimum_on_small_cases():
    rng = random.Random(17)
    for _ in range(35):
        distance = rng.randrange(60, 161) * 10
        positions = sorted(rng.sample(range(1, distance // 10), 4))
        stops = [(p * 10, rng.choice(["2.10", "3.25", "4.90"])) for p in positions]
        expected = oracle(distance, stops)
        items = [
            station(str(i), miles, price) for i, (miles, price) in enumerate(stops)
        ]
        if expected is None:
            with pytest.raises(UnreachableRoute):
                optimize(D(distance), items)
        else:
            assert optimize(D(distance), items).total_cost == expected
