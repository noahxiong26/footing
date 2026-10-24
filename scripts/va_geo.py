"""Virginia locality shapes from the bundled us-atlas counties-10m TopoJSON (1:10,000,000 scale).

Used by the build scripts to make footing/static/va_localities.json. The shapes are coarse: a point within
about 1-2 km of a county line can land in the neighbor, and the smallest independent cities are only a few
vertices. The confidence score accounts for this (see footing/confidence.py).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPO = ROOT / "footing" / "web" / "data" / "counties-10m.json"


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


def _ring(arcs, idxs):
    pts: list[tuple[float, float]] = []
    for i in idxs:
        a = arcs[i] if i >= 0 else list(reversed(arcs[~i]))
        pts.extend(a if not pts else a[1:])
    return pts


def va_localities() -> dict[str, dict]:
    """fips -> {name, kind, polygons: [[outer, hole...], ...]} with (lon, lat) rings."""
    topo = json.loads(TOPO.read_text(encoding="utf-8"))
    arcs = _decode_arcs(topo)
    out = {}
    for g in topo["objects"]["counties"]["geometries"]:
        fips = str(g["id"]).zfill(5)
        if not fips.startswith("51"):
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        out[fips] = {"name": g["properties"]["name"], "kind": "city" if int(fips[2:]) >= 500 else "county",
                     "polygons": [p for p in ([ring for ring in (_ring(arcs, r) for r in poly) if len(ring) >= 4]
                                              for poly in polys) if p and len(p[0]) >= 4]}
    return out
