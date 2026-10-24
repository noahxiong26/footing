"""Virginia locality Fit Score and confidence (Python mirror of footing/web/va.js).

The state Fit Score (footing/fit.py) rates Virginia as one place. This module rates each of Virginia's 133
counties and independent cities: state law still decides program access and immigration-enforcement risk, and
local data replaces the state averages for rent, shelter beds, camping rules and street safety wherever we
have it. Every answer carries a confidence score that drops when the point is doubtful (outside Virginia,
in water, swapped latitude/longitude, rounded coordinates, close to a county line) or the data is thin or
coarse. tests/test_va.py proves the JavaScript version returns identical results.

Method and sources: docs/RATING_FORMULA.md (Virginia section) and footing/static/va_localities.json.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache

from . import fit
from .fit import STATIC, clamp, js_round, linear, roc_weights, round1, round3

VA_BBOX = (36.54, -83.68, 39.47, -75.24)          # lat_min, lon_min, lat_max, lon_max
BOUNDARY_KM = 1.5
SNAP_KM = 2.0
LABELS = {"access": "Programs you can use", "affordability": "Rent", "shelter": "Shelter beds",
          "safety": "Immigration enforcement", "criminalization": "Camping rules", "community": "Community ratings",
          "crime": "Street safety"}
RULE_SCORE = {"ban_citywide": 0, "ban_partial": 35}
RENT_GOOD, RENT_BAD = 1.0, 3.0       # housing wage / minimum wage: 1x = one full-time job covers rent; 3x = three jobs


@lru_cache(maxsize=None)
def load_va() -> dict:
    return json.loads((STATIC / "va_localities.json").read_text(encoding="utf-8"))


# ---- formatting shared with JS (same rounding, same separators) -----------------------------------------------
def fixed(x: float, d: int) -> str:
    """Like JS Number.toFixed for the values we print (rounds half up on the decimal digit)."""
    p = 10 ** d
    v = js_round(x * p) / p
    return f"{v:.{d}f}"


def commas(n: float) -> str:
    return f"{int(js_round(n)):,}"


def num_str(x: float) -> str:
    """Shortest round-trip text of a float, like JS String(x) for ordinary coordinates."""
    s = repr(float(x))
    if s.endswith(".0"):
        s = s[:-2]
    return s


def decimals(x: float) -> int:
    s = num_str(x)
    return len(s.split(".")[1]) if "." in s else 0


# ---- geometry -----------------------------------------------------------------------------------------------
def _in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _in_shape(lon: float, lat: float, shape: list) -> bool:
    for poly in shape:
        if poly and _in_ring(lon, lat, poly[0]) and not any(_in_ring(lon, lat, h) for h in poly[1:]):
            return True
    return False


def _seg_km(lat: float, lon: float, a: list, b: list) -> float:
    k = math.cos(lat * math.pi / 180) * 111.32
    px, py = lon * k, lat * 110.574
    ax, ay, bx, by = a[0] * k, a[1] * 110.574, b[0] * k, b[1] * 110.574
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else clamp(((px - ax) * dx + (py - ay) * dy) / L, 0, 1)
    ex, ey = ax + t * dx - px, ay + t * dy - py
    return math.sqrt(ex * ex + ey * ey)


def _edge_km(lat: float, lon: float, shape: list) -> float:
    best = math.inf
    for poly in shape:
        for ring in poly:
            for i in range(len(ring) - 1):
                d = _seg_km(lat, lon, ring[i], ring[i + 1])
                if d < best:
                    best = d
    return best


def locate(va: dict, lat: float, lon: float) -> str | None:
    for fips, loc in va["localities"].items():
        if loc["shape"] and _in_shape(lon, lat, loc["shape"]):
            return fips
    return None


def tile_of(lat: float, lon: float) -> str:
    return f"t{math.floor(lat / 0.01)}_{math.floor(lon / 0.01)}"


def check_point(va: dict, lat, lon) -> dict:
    """Is this a usable Virginia point? Returns the locality and every doubt about the point, each with a factor."""
    issues: list[dict] = []

    def add(code: str, text: str, factor: float) -> None:
        issues.append({"code": code, "text": text, "factor": factor})

    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        lat = lon = float("nan")
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        add("invalid", "These coordinates are not a real place (latitude must be -90 to 90, longitude -180 to 180).", 0)
        return {"ok": False, "fips": None, "name": None, "tile": None, "validity": 0, "boundary_km": None, "issues": issues}
    fips = locate(va, lat, lon)
    snapped = False
    if fips is None:
        if -90 <= lon <= 90 and locate(va, lon, lat):
            add("swapped", f"These look like latitude and longitude swapped. Did you mean {num_str(lon)}, {num_str(lat)}?", 0)
            return {"ok": False, "fips": None, "name": None, "tile": None, "validity": 0, "boundary_km": None, "issues": issues}
        in_box = VA_BBOX[0] <= lat <= VA_BBOX[2] and VA_BBOX[1] <= lon <= VA_BBOX[3]
        near, near_km = None, math.inf
        if in_box:
            for f, loc in va["localities"].items():
                if loc["shape"]:
                    d = _edge_km(lat, lon, loc["shape"])
                    if d < near_km:
                        near, near_km = f, d
        if near is not None and near_km <= SNAP_KM:
            fips, snapped = near, True
            add("snapped", f"This point is just outside the map outline (water or a border); counted as "
                           f"{va['localities'][near]['name']}, {fixed(near_km, 1)} km away.", 0.6)
        elif in_box:
            add("no_locality", "This point is in Virginia's box but not inside any county or city (open water, "
                               "or a neighboring state).", 0)
            return {"ok": False, "fips": None, "name": None, "tile": None, "validity": 0, "boundary_km": None, "issues": issues}
        else:
            add("outside_va", "This point is outside Virginia. Local scores cover Virginia only; the state view still works.", 0)
            return {"ok": False, "fips": None, "name": None, "tile": None, "validity": 0, "boundary_km": None, "issues": issues}
    loc = va["localities"][fips]
    edge = _edge_km(lat, lon, loc["shape"]) if loc["shape"] else 0.0
    if min(decimals(lat), decimals(lon)) <= 1:
        add("coarse", "The coordinates are rounded (one decimal place is about 11 km), so the local numbers may be "
                      "for the wrong place.", 0.6)
    if not snapped and edge < BOUNDARY_KM:
        add("near_boundary", f"About {fixed(edge, 1)} km from the {loc['name']} line on a coarse map; the neighbor's "
                             f"numbers may apply.", 0.85)
    verts = sum(len(r) for p in loc["shape"] for r in p)
    if verts <= 6:
        add("small_shape", f"{loc['name']} is drawn with only {verts} points at this map scale, so its edges are rough.", 0.8)
    validity = 1.0
    for i in issues:
        validity *= i["factor"]
    return {"ok": True, "fips": fips, "name": loc["name"], "tile": tile_of(lat, lon), "validity": round3(validity),
            "boundary_km": round(edge * 100) / 100 if math.isfinite(edge) else None, "issues": issues}


# ---- components ---------------------------------------------------------------------------------------------
def _nb(va: dict, tile: str, key: str) -> int:
    i, j = (int(x) for x in tile[1:].split("_"))
    s = 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            t = va["tiles"].get(f"t{i + di}_{j + dj}")
            if t:
                s += t[key]
    return s


def crime_component(va: dict, fips: str, tile: str | None) -> dict:
    loc = va["localities"][fips]
    cr = loc["crime"]
    sc = va["scales"]
    rate = cr["violent_per_100k"]
    if tile and loc.get("incident_tiles"):
        city = va["incident_cities"][fips]
        v, e = _nb(va, tile, "v"), _nb(va, tile, "e")
        reason = (f"{commas(v)} violent incident{'' if v == 1 else 's'} reported within about 1.5 km in the last 12 months "
                  f"({city['name']} police data); {commas(e)} trespass, loitering or disorderly calls nearby, which show "
                  f"where police make contact and are not counted as danger.")
        if rate is not None:
            reason += f" Citywide: {fixed(rate, 1)} violent crimes per 100,000 (FBI, 2025)."
        return {"score": round1(linear(v, sc["tile_violent_3x3"]["good"], sc["tile_violent_3x3"]["bad"])), "reason": reason,
                "level": "block", "spec": 1.0, "fresh": 0.95}
    if rate is None:
        return {"score": None, "reason": cr["note"], "level": "none", "spec": 0, "fresh": 0}
    n = len([a for a in cr["agencies"] if a["months"] == 12])
    s = sc["violent_per_100k"]
    reason = (f"{fixed(rate, 1)} violent crimes per 100,000 people in 2025 ({n} police "
              f"agenc{'y' if n == 1 else 'ies'} reporting to the FBI). Virginia localities run from {fixed(s['good'], 1)} "
              f"to {fixed(s['bad'], 1)} (10th to 90th percentile).")
    if cr["note"]:
        reason += " " + cr["note"]
    return {"score": round1(linear(rate, s["good"], s["bad"])), "reason": reason, "level": "locality", "spec": 0.75, "fresh": 0.8}


def locality_components(elig: dict, policy: dict, va: dict, fips: str, profile: dict,
                        community: dict | None = None, tile: str | None = None) -> dict:
    loc = va["localities"][fips]
    base = fit.components(elig, policy, "VA", profile, None)
    out: dict[str, dict] = {}
    for k in ("access", "safety"):
        if k in base:
            out[k] = dict(base[k], level="state law", spec=1.0, fresh=fit.FRESHNESS[k])
    kids = bool((profile.get("household") or {}).get("kids"))
    br = "2" if kids else "0"
    rent = loc["rent"]
    hw = rent["housing_wage"][br]
    mw = va["min_wage"]
    out["affordability"] = {
        "score": round1(linear(hw / mw, RENT_GOOD, RENT_BAD)),
        "reason": (f"Fair Market Rent for a {'2-bedroom' if kids else 'studio'} here is ${commas(rent['fmr'][br])}/month: "
                   f"${fixed(hw, 2)}/hr full-time to afford it, {int(js_round(40 * hw / mw))} hours/week at the "
                   f"${fixed(mw, 2)} minimum wage (HUD FY2026)."),
        "level": "locality", "spec": 0.9, "fresh": 0.9}
    coc = va["cocs"][loc["coc"]]
    s = va["scales"]["beds_per_10k"]
    out["shelter"] = {
        "score": round1(linear(coc["beds_per_10k"], s["good"], s["bad"])),
        "reason": (f"{commas(coc['beds_year_round'])} year-round shelter beds in the {coc['name']} ({loc['coc']}) for "
                   f"{commas(coc['residents_2023'])} residents: {fixed(coc['beds_per_10k'], 1)} per 10,000 "
                   f"({commas(coc['beds_for_families'] if kids else coc['beds_for_adults'])} for "
                   f"{'families with children' if kids else 'adults without children'}; Jan 2025 count)."),
        "level": "region", "spec": 0.7, "fresh": 0.7}
    out["crime"] = crime_component(va, fips, tile)
    rule = loc.get("rules")
    if rule and rule["status"] in RULE_SCORE:
        out["criminalization"] = {"score": RULE_SCORE[rule["status"]],
                                  "reason": f"{rule['place']}: {rule['summary']}"
                                            + (f" {rule['penalty']}." if rule.get("penalty") else ""),
                                  "level": "locality", "spec": 1.0, "fresh": 0.8, "source": rule["source_url"]}
    elif rule:
        out["criminalization"] = {"score": None, "reason": f"{rule['place']}: {rule['summary']}", "level": "locality",
                                  "spec": 0, "fresh": 0, "source": rule["source_url"]}
    else:
        out["criminalization"] = {"score": None, "reason": f"Local camping rules not checked for {loc['name']}. "
                                  + va["rules_note"]["text"], "level": "none", "spec": 0, "fresh": 0}
    c = (community or {}).get(fips)
    if c and c.get("n", 0) > 0:
        out["community"] = {"score": c["score"], "n": c["n"], "reason":
                            f"{c['n']} rating{'' if c['n'] == 1 else 's'} from people who have been here",
                            "level": "locality", "spec": 1.0, "fresh": c.get("freshness") or 0.5}
    else:
        out["community"] = {"score": None, "reason": "No ratings yet. Be the first to rate a place here.",
                            "level": "none", "spec": 0, "fresh": 0}
    return out


def locality_priorities(elig: dict, profile: dict, comps: dict) -> list[str]:
    order = fit.default_priorities(elig, profile)
    order.insert(order.index("shelter") + 1, "crime")
    chosen = [k for k in (profile.get("priorities") or []) if k in order]
    for k in order:
        if k not in chosen:
            chosen.append(k)
    return [k for k in chosen if k in comps]


def confidence(rows: list[dict], point: dict | None) -> dict:
    """0-100. validity of the point x weighted share of the score backed by data, discounted for coarse or old data."""
    den = num = 0.0
    for r in rows:
        den += r["weight"]
        if r["score"] is not None:
            num += r["weight"] * r["spec"] * r["fresh"]
    quality = num / den if den else 0.0
    validity = point["validity"] if point else 1.0
    value = int(js_round(100 * validity * quality))
    issues = [{"code": i["code"], "text": i["text"]} for i in (point["issues"] if point else [])]
    for r in sorted(rows, key=lambda r: -r["weight"]):
        if r["score"] is None:
            issues.append({"code": "missing_" + r["id"], "text": f"{LABELS[r['id']]}: no data, so it is left out of the score."})
        elif r["spec"] < 0.8:
            where = "for the whole region" if r["level"] == "region" else "for the whole county or city, not this block"
            issues.append({"code": "coarse_" + r["id"], "text": f"{LABELS[r['id']]}: the number is {where}."})
    label = "high" if value >= 70 else ("medium" if value >= 45 else "low")
    return {"score": value, "label": label, "validity": round3(validity), "data_quality": round3(quality), "issues": issues}


def locality_fit(elig: dict, policy: dict, va: dict, fips: str, profile: dict, community: dict | None = None,
                 point: dict | None = None) -> dict:
    tile = point["tile"] if point else None
    comps = locality_components(elig, policy, va, fips, profile, community, tile)
    order = locality_priorities(elig, profile, comps)
    w = roc_weights(len(order))
    rows = []
    num = den = 0.0
    for i, k in enumerate(order):
        c = comps[k]
        rows.append({"id": k, "label": LABELS[k], "weight": round3(w[i]), "score": c["score"], "reason": c["reason"],
                     "level": c["level"], "spec": c["spec"], "fresh": c["fresh"], "source": c.get("source"),
                     "parts": c.get("parts")})
        if c["score"] is not None:
            num += w[i] * c["score"]
            den += w[i]
    conf = confidence(rows, point)
    return {"fips": fips, "name": va["localities"][fips]["name"], "score": round1(num / den) if den else None,
            "confidence": conf, "components": rows, "point": point}


def fit_point(elig: dict, policy: dict, va: dict, lat, lon, profile: dict, community: dict | None = None) -> dict:
    """Score a tapped or typed point. Bad points return no score and say why (confidence 0)."""
    pt = check_point(va, lat, lon)
    if not pt["ok"]:
        return {"fips": None, "name": None, "score": None,
                "confidence": {"score": 0, "label": "low", "validity": 0, "data_quality": 0,
                               "issues": [{"code": i["code"], "text": i["text"]} for i in pt["issues"]]},
                "components": [], "point": pt}
    return locality_fit(elig, policy, va, pt["fips"], profile, community, pt)


def rank_localities(elig: dict, policy: dict, va: dict, profile: dict, community: dict | None = None) -> list[dict]:
    out = [locality_fit(elig, policy, va, f, profile, community) for f in sorted(va["localities"])]
    known = sorted([r for r in out if r["score"] is not None], key=lambda r: (-r["score"], r["fips"]))
    for i, r in enumerate(known):
        r["rank"] = i + 1
    return out


def community_by_locality(va: dict, heat_tiles: list[dict]) -> dict:
    """Group community-rating tiles (from /api/ratings/heat) by locality and re-score them together."""
    groups: dict[str, list] = {}
    for t in heat_tiles:
        f = locate(va, t["lat"], t["lon"])
        if f:
            groups.setdefault(f, []).append(t)
    out = {}
    for f, ts in groups.items():
        n = sum(t["n"] for t in ts)
        eff = sum(t.get("effective_n", t["n"]) for t in ts)
        score = sum(t["score"] * t.get("effective_n", t["n"]) for t in ts) / eff if eff else None
        out[f] = {"n": n, "score": round1(score) if score is not None else None, "freshness": round3(min(1, eff / 10))}
    return out
