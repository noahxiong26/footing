"""Virginia's 133 localities (95 counties + 38 independent cities): offline point lookup and location checks.

Footing focuses on Virginia. This module answers two questions without calling any outside service:

  * which Virginia locality is a point in? (bundled us-atlas county TopoJSON, Census cartographic boundaries)
  * is this point usable at all? A point can be bad in several ways, and each gets a plain reason instead of
    a made-up answer: not a number, off the globe, outside Virginia, or in open water (cartographic boundaries
    are clipped to the shoreline, so a point in the Chesapeake Bay is in no locality).

In Virginia, independent cities are not part of any county, so "Roanoke city" (51770) and "Roanoke County"
(51161) are different places with different rules. FIPS codes 510 and above are cities.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from .geo import haversine_m
from .us_states import _decode_arcs, _inside, _ring, state_at

WEB_DATA = Path(__file__).resolve().parent / "web" / "data"
# Census TIGERweb county boundaries for Virginia (current vintage, read 2026-10-24), generalized to ~100 m and
# quantized; see data_raw/README.md. TIGER boundaries include water area, so they answer "which locality".
DATA = WEB_DATA / "va-localities.json"
# us-atlas (Census cartographic, clipped to the shoreline, simplified for 1:10M). Used only to spot open water.
SHORE = WEB_DATA / "counties-10m.json"
WATER_TOLERANCE_M = 2000   # the 1:10M shoreline is coarse; closer than this to land counts as land
# Rough box around Virginia, used to tell "just over the border / offshore" from "nowhere near".
VA_BBOX = (-83.68, 36.54, -75.24, 39.47)


def locality_name(fips: str, short: str) -> str:
    """'Roanoke' + 51770 -> 'Roanoke city'; 51161 -> 'Roanoke County'."""
    return f"{short} city" if int(fips[2:]) >= 510 else f"{short} County"


@lru_cache(maxsize=1)
def localities() -> list[dict]:
    topo = json.loads(DATA.read_text(encoding="utf-8"))
    arcs = _decode_arcs(topo)
    out = []
    for g in topo["objects"]["localities"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        rings = [[_ring(arcs, r) for r in poly] for poly in polys]
        xs = [p[0] for poly in rings for r in poly for p in r]
        ys = [p[1] for poly in rings for r in poly for p in r]
        # area-weighted centroid of the outer rings (shoelace), good enough for a label point
        a_sum = cx = cy = 0.0
        for poly in rings:
            r = poly[0]
            for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
                c = x1 * y2 - x2 * y1
                a_sum += c
                cx += (x1 + x2) * c
                cy += (y1 + y2) * c
        center = (round(cy / (3 * a_sum), 4), round(cx / (3 * a_sum), 4)) if a_sum else (sum(ys) / len(ys), sum(xs) / len(xs))
        short = g["properties"]["name"]
        out.append({"fips": g["id"], "short": short, "name": g["properties"].get("full") or locality_name(g["id"], short),
                    "kind": "city" if int(g["id"][2:]) >= 510 else "county",
                    "rings": rings, "bbox": (min(xs), min(ys), max(xs), max(ys)), "center": center})
    out.sort(key=lambda d: d["fips"])
    return out


def by_fips() -> dict[str, dict]:
    return {d["fips"]: d for d in localities()}


def locality_at(lat: float, lon: float) -> dict | None:
    for d in localities():
        x0, y0, x1, y1 = d["bbox"]
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        for poly in d["rings"]:
            if _inside(lon, lat, poly[0]) and not any(_inside(lon, lat, h) for h in poly[1:]):
                return d
    return None


@lru_cache(maxsize=1)
def _shore() -> list:
    topo = json.loads(SHORE.read_text(encoding="utf-8"))
    arcs = _decode_arcs(topo)
    out = []
    for g in topo["objects"]["counties"]["geometries"]:
        if not g["id"].startswith("51"):
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        out.extend(_ring(arcs, poly[0]) for poly in polys)
    return out


def _seg_dist_m(lat, lon, a, b) -> float:
    # project to a local flat plane (fine at these distances), then point-to-segment distance
    kx = math.cos(math.radians(lat)) * 111_320.0
    ky = 110_540.0
    ax, ay = (a[0] - lon) * kx, (a[1] - lat) * ky
    bx, by = (b[0] - lon) * kx, (b[1] - lat) * ky
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx, ay + t * dy)


def distance_to_land_m(lat: float, lon: float) -> float:
    """0 if on (cartographic) land, else metres to the nearest Virginia shoreline segment."""
    rings = _shore()
    if any(_inside(lon, lat, r) for r in rings):
        return 0.0
    return min(_seg_dist_m(lat, lon, r[i], r[i + 1]) for r in rings for i in range(len(r) - 1))


def check_point(lat, lon) -> dict:
    """Classify an input point. Never guesses: a point that is not usable comes back with ok=False and why.

    Returns {"ok": bool, "code": str, "reason": str, "fips"?: str, "name"?: str}
      codes: ok | not_a_number | off_globe | outside_virginia | open_water
    """
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"ok": False, "code": "not_a_number", "reason": "That location is not a pair of numbers."}
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return {"ok": False, "code": "not_a_number", "reason": "That location is not a real number (NaN or infinity)."}
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return {"ok": False, "code": "off_globe", "reason": "Latitude must be -90..90 and longitude -180..180."}
    d = locality_at(lat, lon)
    if d:
        if distance_to_land_m(lat, lon) > WATER_TOLERANCE_M:
            return {"ok": False, "code": "open_water", "fips": d["fips"], "name": d["name"],
                    "reason": f"That point is on open water (inside {d['name']}'s water area). Move it onto land."}
        return {"ok": True, "code": "ok", "reason": "", "fips": d["fips"], "name": d["name"]}
    st = state_at(lat, lon)
    if st and st != "VA":
        from .fit import load_policy
        name = load_policy()["states"].get(st, {}).get("name", st)
        return {"ok": False, "code": "outside_virginia", "state": st,
                "reason": f"That point is in {name}. Footing covers Virginia only for now."}
    x0, y0, x1, y1 = VA_BBOX
    if x0 <= lon <= x1 and y0 <= lat <= y1:
        return {"ok": False, "code": "open_water",
                "reason": "That point is on open water or right on a border, not inside a Virginia city or county."}
    return {"ok": False, "code": "outside_virginia", "reason": "That point is outside Virginia. Footing covers Virginia only for now."}
