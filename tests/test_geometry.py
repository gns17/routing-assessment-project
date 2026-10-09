from decimal import Decimal

import pytest

from routing.geometry import Candidate, bounds, match_stations


def station(lon=-100, lat=35, identity=1):
    return Candidate(identity, "Synthetic", "Test", "Test", "NM", Decimal(3), lat, lon)


def line(coords):
    return {"type": "LineString", "coordinates": coords}


def test_segment_projection_corridor_and_scaled_chainage():
    geometry = line([[-101, 35], [-99, 35]])
    result = match_stations(geometry, Decimal(800), [station(), station(lat=36)], 1)
    assert len(result) == 1
    assert result[0].miles == Decimal(400)
    assert result[0].offset_miles == 0
    south, north, west, east = bounds(geometry, 1)
    assert south < 35 < north and west < -101 and east > -99


def test_loop_preserves_multiple_passes():
    geometry = line(
        [[-101, 35], [-99, 35], [-99, 37], [-101, 37], [-101, 35], [-99, 35]]
    )
    result = match_stations(geometry, Decimal(900), [station()], 1)
    assert len(result) == 2
    assert result[0].miles < result[1].miles


def test_multiline_and_degenerate_route():
    geometry = {
        "type": "MultiLineString",
        "coordinates": [[[-101, 35], [-100, 35]], [[-100, 35], [-99, 35]]],
    }
    assert len(match_stations(geometry, Decimal(100), [station()], 1)) == 1
    assert (
        match_stations(line([[-100, 35], [-100, 35]]), Decimal(0), [station()], 1) == []
    )
    geometry["coordinates"][1][0] = [-90, 40]
    with pytest.raises(ValueError, match="Disconnected"):
        match_stations(geometry, Decimal(100), [station()], 1)


@pytest.mark.parametrize("corridor", [0, -1, float("nan"), float("inf")])
def test_invalid_corridor(corridor):
    with pytest.raises(ValueError):
        bounds(line([[-101, 35], [-99, 35]]), corridor)


def test_corridor_boundary():
    geometry = line([[-101, 35], [-99, 35]])
    candidate = station(lat=35.01)
    offset = match_stations(geometry, Decimal(100), [candidate], 2)[0].offset_miles
    assert len(match_stations(geometry, Decimal(100), [candidate], offset)) == 1
    assert not match_stations(geometry, Decimal(100), [candidate], offset - 0.0001)
