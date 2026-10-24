"""Small geometry helpers. No GIS dependencies on purpose."""
from __future__ import annotations

import math

EARTH_R_M = 6_371_008.8
TILE_DEG = 0.01            # about 1.1 km north-south; the privacy and cache unit
WALK_M_PER_MIN = 80.0      # about 3 mph
DETOUR_FACTOR = 1.3        # straight line -> street distance


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_M * math.asin(math.sqrt(a))


def walk_minutes(distance_m: float) -> float:
    return distance_m * DETOUR_FACTOR / WALK_M_PER_MIN


def snap_to_tile(lat: float, lon: float) -> tuple[str, float, float]:
    """Return (tile_id, center_lat, center_lon). Raw coordinates never go further."""
    i = math.floor(lat / TILE_DEG)
    j = math.floor(lon / TILE_DEG)
    clat = round((i + 0.5) * TILE_DEG, 4)
    clon = round((j + 0.5) * TILE_DEG, 4)
    return f"t{i}_{j}", clat, clon


def bbox(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat) around a point."""
    dlat = math.degrees(radius_m / EARTH_R_M)
    dlon = math.degrees(radius_m / (EARTH_R_M * math.cos(math.radians(lat))))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat
