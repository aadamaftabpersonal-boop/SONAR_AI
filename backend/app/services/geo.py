"""Distance helpers (Bible D-015: plain Haversine, no PostGIS)."""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def _check(lat: float, lng: float) -> None:
    if not (math.isfinite(lat) and math.isfinite(lng)):
        raise ValueError("coordinates must be finite")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("coordinates out of range")


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    _check(lat1, lng1)
    _check(lat2, lng2)
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def within_radius(lat1: float, lng1: float, lat2: float, lng2: float, radius_km: float) -> bool:
    return distance_km(lat1, lng1, lat2, lng2) <= radius_km


def bearing_deg(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Initial compass bearing from point 1 to point 2, 0..360 (used by the Wave 2 radar view)."""
    _check(lat1, lng1)
    _check(lat2, lng2)
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lng2 - lng1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360
