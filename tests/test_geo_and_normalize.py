import math

import pytest

from footing.factors import count_score, linear_score
from footing.geo import bbox, haversine_m, snap_to_tile, walk_minutes


def test_haversine_one_degree_latitude():
    assert haversine_m(37.0, -80.0, 38.0, -80.0) == pytest.approx(111_195, rel=1e-3)


def test_haversine_zero():
    assert haversine_m(37.13, -80.41, 37.13, -80.41) == 0


def test_walk_minutes_uses_detour_and_speed():
    assert walk_minutes(800) == pytest.approx(800 * 1.3 / 80)


def test_snap_to_tile_is_stable_inside_a_tile():
    a = snap_to_tile(37.1299, -80.4089)
    b = snap_to_tile(37.1201, -80.4001)
    assert a == b
    assert a[0] == "t3712_-8041"
    assert a[1:] == (37.125, -80.405)


def test_snap_to_tile_hides_raw_point():
    _, lat, lon = snap_to_tile(37.12345678, -80.98765432)
    assert round(lat, 4) == lat and round(lon, 4) == lon
    assert (lat, lon) != (37.12345678, -80.98765432)


def test_bbox_contains_point_and_radius():
    minx, miny, maxx, maxy = bbox(37.13, -80.41, 5000)
    assert minx < -80.41 < maxx and miny < 37.13 < maxy
    assert haversine_m(37.13, -80.41, maxy, -80.41) == pytest.approx(5000, rel=1e-3)


@pytest.mark.parametrize("n,k,expected", [(0, 1, 0), (1, 1, 100 * (1 - math.exp(-1))), (3, 1, 95.02)])
def test_count_score(n, k, expected):
    assert count_score(n, k) == pytest.approx(expected, abs=0.01)


def test_linear_score_both_directions_and_clamp():
    assert linear_score(3.0, good=3.0, bad=10.0) == 100
    assert linear_score(10.0, good=3.0, bad=10.0) == 0
    assert linear_score(6.5, good=3.0, bad=10.0) == pytest.approx(50)
    assert linear_score(20.0, good=15.0, bad=7.25) == 100      # higher is better
    assert linear_score(1.0, good=0.3, bad=1.0) == 0
    assert linear_score(-5.0, good=0.0, bad=5.0) == 100        # clamped
