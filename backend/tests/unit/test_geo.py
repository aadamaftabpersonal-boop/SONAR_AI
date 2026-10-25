import math

import pytest

from app.services.geo import bearing_deg, distance_km, within_radius


def test_known_distance_bengaluru_to_chennai():
    # roughly 290 km great-circle
    d = distance_km(12.9716, 77.5946, 13.0827, 80.2707)
    assert 285 < d < 295


def test_zero_distance():
    assert distance_km(12.97, 77.59, 12.97, 77.59) == 0


def test_antipodes_are_half_the_circumference():
    d = distance_km(0, 0, 0, 180)
    assert d == pytest.approx(math.pi * 6371.0088, rel=1e-6)


def test_boundary_is_inclusive():
    d = distance_km(12.97, 77.59, 12.98, 77.60)
    assert within_radius(12.97, 77.59, 12.98, 77.60, d)
    assert not within_radius(12.97, 77.59, 12.98, 77.60, d - 0.001)


@pytest.mark.parametrize("bad", [(91, 0), (0, 181), (float("nan"), 0), (0, float("inf"))])
def test_rejects_bad_coordinates(bad):
    with pytest.raises(ValueError):
        distance_km(bad[0], bad[1], 0, 0)


@pytest.mark.parametrize(
    ("to", "expected"),
    [((1, 0), 0), ((0, 1), 90), ((-1, 0), 180), ((0, -1), 270)],
)
def test_bearing_at_compass_points(to, expected):
    assert bearing_deg(0, 0, to[0], to[1]) == pytest.approx(expected, abs=0.5)
