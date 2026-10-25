"""Point in, Settle Receipt out.

    tile snap -> run sources -> merge places/measures -> evaluate parameters
    -> category scores -> Settle Score + confidence -> receipt (JSON-ready dict)
"""
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import asdict, replace
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import hours

from . import __version__
from .config import Settings
from .factors import (CATEGORIES, EXCLUDED_ON_PURPOSE, FRESHNESS, PARAMS, PROFILE_CATEGORY_BOOST,
                      Bundle, Unknown)
from .enrich import enrich
from .geo import haversine_m, snap_to_tile
from .http import Fetcher
from .models import Measure, Place, SourceResult
from .sources import ALL_SOURCES
from .sources.base import Context

PROFILES = {"car", "kids", "tonight", "on_foot"}
DEDUPE_M = 75.0
SOURCE_PRIORITY = ["osm", "hrsa", "snap", "urban_ed", "transitland", "google_places", "snap_name"]


def dedupe(places: list[Place]) -> list[Place]:
    """Same kind within 75 m counts once (OSM and Google often list the same pantry)."""
    order = {s: i for i, s in enumerate(SOURCE_PRIORITY)}
    kept: list[Place] = []
    for p in sorted(places, key=lambda p: order.get(p.source, 99)):
        twin = next((k for k in kept if k.kind == p.kind and
                     haversine_m(k.lat, k.lon, p.lat, p.lon) <= DEDUPE_M), None)
        if twin:
            twin.tags.setdefault("also_in", []).append(p.source)
        else:
            kept.append(p)
    return sorted(kept, key=lambda p: (p.kind, p.distance_m or 0))


def parse_profile(profile: str | list[str] | None) -> list[str]:
    if not profile:
        items: list[str] = []
    elif isinstance(profile, str):
        items = [x.strip() for x in profile.split(",") if x.strip()]
    else:
        items = list(profile)
    bad = [x for x in items if x not in PROFILES]
    if bad:
        raise ValueError(f"unknown profile option(s) {bad}; use {sorted(PROFILES)}")
    if "car" not in items and "on_foot" not in items:
        items.append("on_foot")
    return items


def _manifest_tile(folder: Path) -> str | None:
    m = folder / "MANIFEST.json"
    if not m.exists():
        return None
    point = json.loads(m.read_text(encoding="utf-8")).get("point")
    if not point:   # statewide data sets (e.g. fixtures/va_*) have no single point; they are not receipt replays
        return None
    return snap_to_tile(point["lat"], point["lon"])[0]


def resolve_replay(settings: Settings, tile: str) -> Settings:
    """Pick the recorded fixture set for this tile.

    `fixture_dir` may be one recorded set (has MANIFEST.json) or a folder of sets (one per town,
    as written by `footing record`). Fixtures belong to one tile: replaying them for any other tile
    would show one town's data under another town's name, so an uncovered tile gets no data.
    A folder without any manifest (ad-hoc test fixtures) makes no location claim and is used as is.
    """
    if settings.mode != "replay" or not settings.fixture_dir:
        return settings
    d = settings.fixture_dir
    own = _manifest_tile(d)
    if own is not None:
        return settings if own == tile else replace(settings, fixture_dir=None)
    sets = [sub for sub in sorted(d.iterdir()) if sub.is_dir() and _manifest_tile(sub)] if d.exists() else []
    if not sets:
        return settings
    matches = [sub for sub in sets if _manifest_tile(sub) == tile]
    newest = max(matches, key=_captured_at, default=None)      # re-recorded towns: newest wins
    return replace(settings, fixture_dir=newest)


def _captured_at(folder: Path) -> str:
    return json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8")).get("captured_at", "")


def recorded_sets(settings: Settings) -> list[dict]:
    """List recorded demo places (for the app's town picker)."""
    d = settings.fixture_dir
    if not d or not d.exists():
        return []
    folders = [d] if (d / "MANIFEST.json").exists() else [s for s in sorted(d.iterdir()) if (s / "MANIFEST.json").exists()]
    by_tile: dict[str, Path] = {}
    for f in folders:                       # one entry per tile: the newest recording
        t = _manifest_tile(f)
        if t is None:                       # statewide data set with no single point: not a receipt replay
            continue
        if t not in by_tile or _captured_at(f) > _captured_at(by_tile[t]):
            by_tile[t] = f
    out = []
    for f in sorted(by_tile.values(), key=lambda x: x.name):
        m = json.loads((f / "MANIFEST.json").read_text(encoding="utf-8"))
        out.append({"label": m["point"]["label"], "lat": m["point"]["lat"], "lon": m["point"]["lon"],
                    "captured_at": m["captured_at"][:10], "set": f.name})
    return out


def collect(lat: float, lon: float, settings: Settings, fetcher: Fetcher | None = None) -> tuple[Context, Bundle]:
    ctx = Context(lat=lat, lon=lon, settings=settings, fetcher=fetcher or Fetcher(settings), radius_m=settings.radius_m)
    results: dict[str, SourceResult] = {}
    for src in ALL_SOURCES:
        results[src.name] = src.run(ctx)
    places = dedupe(enrich([p for r in results.values() if r.status == "ok" for p in r.places]))
    measures: dict[str, Measure] = {}
    for r in results.values():
        if r.status == "ok":
            measures.update(r.measures)
    return ctx, Bundle(places=places, measures=measures, sources=results)


def score(bundle: Bundle, profile: list[str]) -> dict:
    cat_w = {c.id: float(c.weight) for c in CATEGORIES}
    for opt in profile:
        for cid, mult in PROFILE_CATEGORY_BOOST.get(opt, {}).items():
            cat_w[cid] *= mult
    total_w = sum(cat_w.values())
    cat_w = {k: 100.0 * v / total_w for k, v in cat_w.items()}   # renormalize to 100

    categories, unknowns = [], []
    for c in CATEGORIES:
        rows, num, den, fresh_num, all_w = [], 0.0, 0.0, 0.0, 0.0
        for p in [p for p in PARAMS if p.category == c.id]:
            w = p.weight
            for opt in profile:
                w *= p.profile_boost.get(opt, 1.0)
            all_w += w
            row = {"id": p.id, "label": p.label, "weight": round(w, 2), "unit": p.unit,
                   "sources": list(p.sources), "refresh": p.refresh, "rule": p.rule, "status": p.status}
            try:
                value = p.extract(bundle)
                s = max(0.0, min(100.0, float(p.score(value))))
                row.update(value=value, score=round(s, 1), state="known")
                num += w * s
                den += w
                fresh_num += w * FRESHNESS.get(p.refresh, 0.5)
            except Unknown as e:
                row.update(value=None, score=None, state="unknown", reason=str(e))
                unknowns.append({"category": c.id, "parameter": p.id, "reason": str(e)})
            rows.append(row)
        known = den > 0
        categories.append({
            "id": c.id, "label": c.label, "weight": round(cat_w[c.id], 2),
            "score": round(num / den, 1) if known else None,
            "state": "known" if known else "unknown",
            "coverage": round(den / all_w, 2) if all_w else 0.0,          # share of weight with data
            "freshness": round(fresh_num / den, 2) if known else 0.0,
            "parameters": rows,
        })

    known_cats = [c for c in categories if c["state"] == "known"]
    kw = sum(c["weight"] for c in known_cats)
    settle = round(sum(c["weight"] * c["score"] for c in known_cats) / kw, 1) if kw else None
    confidence = round(sum(c["weight"] * c["coverage"] * c["freshness"] for c in known_cats) / 100.0, 2)
    return {"settle_score": settle, "confidence": confidence,
            "confidence_label": "high" if confidence >= 0.6 else "medium" if confidence >= 0.35 else "low",
            "categories": categories, "unknowns": unknowns}


def money_lines(bundle: Bundle) -> list[dict]:
    """The receipt's dollar lines. Missing values say so; they are never estimated."""
    def line(label, key, unit):
        m = bundle.measures.get(key)
        if m is None:
            return {"label": label, "value": None, "unit": unit, "source": None,
                    "as_of": None, "state": "unknown"}
        return {"label": label, "value": m.value, "unit": unit, "source": m.source,
                "as_of": m.as_of, "state": "known", "note": m.note}
    return [
        line("Food, 1 week (local survival basket)", "basket_week", "USD/week"),
        line("Food, 1 week (USDA Thrifty Food Plan baseline)", "tfp_week", "USD/week"),
        line("Gas, regular", "gas_regular", "USD/gal"),
        line("Next step: studio Fair Market Rent", "fmr_studio", "USD/month"),
        line("Median gross rent (ACS)", "median_gross_rent", "USD/month"),
        line("State minimum wage", "min_wage", "USD/hour"),
    ]


def nearest(bundle: Bundle, per_kind: int = 3, now: datetime | None = None) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for p in bundle.places:
        out.setdefault(p.kind, [])
        if len(out[p.kind]) < per_kind:
            row = {k: v for k, v in asdict(p).items() if k in
                   ("id", "name", "lat", "lon", "distance_m", "walk_min", "source", "tags")}
            oh = p.tags.get("opening_hours")
            row["hours_known"] = hours.parse(oh) is not None
            row["open_now"] = hours.is_open(oh, now) if now else None
            closes = hours.closes_today(oh, now) if now else None
            row["closes"] = closes.strftime("%H:%M") if closes else None
            out[p.kind].append(row)
    # Always include the two nearest full grocery stores: a corner store is not a food plan.
    have = {r["id"] for r in out.get("snap_retailer", [])}
    groc = [p for p in bundle.places if p.kind == "snap_retailer" and p.tags.get("full_grocery")]
    for p in groc[:2]:
        if p.id not in have:
            out.setdefault("snap_retailer", []).append(
                {k: v for k, v in asdict(p).items() if k in
                 ("id", "name", "lat", "lon", "distance_m", "walk_min", "source", "tags")}
                | {"hours_known": False, "open_now": None, "closes": None})
    return out


def local_now(tz_name: str | None) -> datetime | None:
    if not tz_name:
        return None
    try:
        return datetime.now(ZoneInfo(tz_name))
    except ZoneInfoNotFoundError:
        return None


def build_receipt(lat: float, lon: float, profile: str | list[str] | None = None,
                  settings: Settings | None = None, now: datetime | None = None) -> dict:
    settings = settings or Settings.from_env()
    prof = parse_profile(profile)
    tile, clat, clon = snap_to_tile(lat, lon)
    settings = resolve_replay(settings, tile)
    ctx, bundle = collect(clat, clon, settings)
    scored = score(bundle, prof)
    in_radius = Bundle(places=[p for p in bundle.places if (p.distance_m or 0) <= settings.radius_m],
                       measures=bundle.measures, sources=bundle.sources)
    tz = bundle.m("time_zone")
    now = now or local_now(tz)
    counts: dict[str, int] = {}
    for p in in_radius.places:
        counts[p.kind] = counts.get(p.kind, 0) + 1
    return {
        "receipt_version": 1,
        "pipeline_version": __version__,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": settings.mode,
        "tile": {"id": tile, "center": [clat, clon], "note": "input point snapped to a ~1 km tile; raw location is not used or stored"},
        "area": {"county_fips": ctx.county_fips, "county": ctx.county_name, "state": ctx.state_abbr,
                 "nws_city": bundle.m("nws_city")},
        "profile": prof,
        **{k: scored[k] for k in ("settle_score", "confidence", "confidence_label")},
        "money": money_lines(bundle),
        "categories": scored["categories"],
        "unknowns": scored["unknowns"],
        "alerts": bundle.m("alerts") or [],
        "place_counts": dict(sorted(counts.items())),
        "place_counts_radius_m": settings.radius_m,
        "nearest": nearest(in_radius, now=now),
        "local_time": now.isoformat(timespec="minutes") if now else None,
        "time_zone": tz,
        "lows_f": bundle.m("lows_f"),
        "sources": [r.to_dict() for r in bundle.sources.values()],
        "excluded_on_purpose": EXCLUDED_ON_PURPOSE,
    }


def record_fixture_set(lat: float, lon: float, label: str, out_dir: Path, settings: Settings) -> dict:
    """Call every source live, save each response as a fixture, and write MANIFEST.json.
    Keys are never written to disk (URLs in the manifest are redacted)."""
    rec = replace(settings, mode="record", fixture_dir=out_dir)
    _, clat, clon = snap_to_tile(lat, lon)
    fetcher = Fetcher(rec)
    _, bundle = collect(clat, clon, rec, fetcher)
    manifest = {
        "fixture_set": out_dir.name,
        "point": {"lat": lat, "lon": lon, "label": label},
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "how": "Recorded with `footing record` (live API calls).",
        "files": {f: {"url": u, "live": True, "trimmed": False} for f, u in sorted(fetcher.recorded.items())},
        "not_captured": {r.source: r.reason for r in bundle.sources.values() if r.status != "ok"},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
