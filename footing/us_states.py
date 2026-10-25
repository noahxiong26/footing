"""Which U.S. state is a point in? Offline, from the bundled us-atlas TopoJSON (Census cartographic boundaries).

Used to file a community rating under the right state without calling any outside service. Small TopoJSON
decoder + ray-casting point-in-polygon; no GIS dependencies on purpose.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "web" / "data" / "states-10m.json"
FIPS_TO_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC",
    "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT",
    "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY",
}


def _decode_arcs(topo: dict) -> list[list[tuple[float, float]]]:
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def _ring(arcs: list, idx: list[int]) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in idx:
        a = arcs[i] if i >= 0 else list(reversed(arcs[~i]))
        pts.extend(a if not pts else a[1:])
    return pts


@lru_cache(maxsize=1)
def _states() -> list[tuple[str, list[list[list[tuple[float, float]]]], tuple[float, float, float, float]]]:
    topo = json.loads(DATA.read_text(encoding="utf-8"))
    arcs = _decode_arcs(topo)
    out = []
    for g in topo["objects"]["states"]["geometries"]:
        abbr = FIPS_TO_ABBR.get(g["id"])
        if not abbr:
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        rings = [[_ring(arcs, r) for r in poly] for poly in polys]
        xs = [p[0] for poly in rings for r in poly for p in r]
        ys = [p[1] for poly in rings for r in poly for p in r]
        out.append((abbr, rings, (min(xs), min(ys), max(xs), max(ys))))
    return out


def _inside(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def state_at(lat: float, lon: float) -> str | None:
    """Two-letter state code (or DC) for a point, None if outside the 50 states + DC."""
    for abbr, polys, (x0, y0, x1, y1) in _states():
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        for poly in polys:
            if _inside(lon, lat, poly[0]) and not any(_inside(lon, lat, hole) for hole in poly[1:]):
                return abbr
    return None
