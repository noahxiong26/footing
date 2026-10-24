"""Virginia locality engine: data build, point checks, confidence, and exact Python/JavaScript parity."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from footing import fit, va

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
ELIG, POLICY, VA = fit.load_eligibility(), fit.load_policy(), va.load_va()

CHRISTIANSBURG = (37.1299, -80.4089)
NORFOLK_DOWNTOWN = (36.8468, -76.2852)
CVILLE_MALL = (38.0306, -78.4808)


def test_build_is_current():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_va_localities.py"), "--check"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_every_locality_has_rent_coc_and_shape_or_point():
    locs = VA["localities"]
    assert len(locs) == 133
    assert sum(1 for f in locs if int(f[2:]) >= 500) == 38          # 38 independent cities
    for f, loc in locs.items():
        assert loc["rent"]["fmr"]["0"] > 0 and loc["coc"] in VA["cocs"], f
        assert loc["shape"] or loc.get("point"), f
    assert set(VA["cocs"]) == {c for c in VA["cocs"]} and len(VA["cocs"]) == 16


def test_crime_unknown_is_never_zero():
    vb = VA["localities"]["51810"]["crime"]                         # Virginia Beach PD reported 0 months to the FBI
    assert vb["violent_per_100k"] is None and "did not" not in vb["note"] and "reported" in vb["note"]
    r = va.locality_fit(ELIG, POLICY, VA, "51810", {"status": "citizen"})
    crime = next(c for c in r["components"] if c["id"] == "crime")
    assert crime["score"] is None
    assert any(i["code"] == "missing_crime" for i in r["confidence"]["issues"])


def test_offense_rules_in_capture_script_match_json():
    js = (ROOT / "scripts" / "capture" / "va_incidents_browser.js").read_text(encoding="utf-8")
    rules = json.loads((ROOT / "footing" / "static" / "va_offense_classes.json").read_text(encoding="utf-8"))["rules"]
    block = js[js.index("var RULES = [") + len("var RULES = "):js.index("].map(")] + "]"
    assert json.loads(block) == rules


def test_good_point_is_scored_with_high_validity():
    r = va.fit_point(ELIG, POLICY, VA, *CHRISTIANSBURG, {"status": "citizen"})
    assert r["fips"] == "51121" and r["score"] is not None
    assert r["point"]["validity"] == 1.0
    assert 0 < r["confidence"]["score"] <= 100


@pytest.mark.parametrize("lat,lon,code", [
    (-80.4089, 37.1299, "swapped"),
    (37.0, -75.3, "no_locality"),
    (35.7796, -78.6382, "outside_va"),
    (91, -80, "invalid"),
    (float("nan"), -80, "invalid"),
    (None, -80, "invalid"),
])
def test_bad_points_get_no_score_and_say_why(lat, lon, code):
    r = va.fit_point(ELIG, POLICY, VA, lat, lon, {"status": "citizen"})
    assert r["score"] is None and r["confidence"]["score"] == 0
    assert r["confidence"]["issues"][0]["code"] == code


def test_rounded_coordinates_lower_confidence():
    exact = va.fit_point(ELIG, POLICY, VA, *CHRISTIANSBURG, {"status": "citizen"})
    rough = va.fit_point(ELIG, POLICY, VA, 37.1, -80.4, {"status": "citizen"})
    assert any(i["code"] == "coarse" for i in rough["confidence"]["issues"])
    assert rough["confidence"]["score"] < exact["confidence"]["score"]


def test_near_county_line_is_flagged():
    loc = VA["localities"]["51121"]["shape"][0][0]
    lon, lat = loc[0]
    lon2, lat2 = loc[1]
    pt = va.check_point(VA, (lat + lat2) / 2, (lon + lon2) / 2)       # on the edge of Montgomery County
    assert pt["ok"] and any(i["code"] == "near_boundary" for i in pt["issues"]) or \
        any(i["code"] == "snapped" for i in pt["issues"])


def test_block_level_crime_used_inside_incident_cities():
    r = va.fit_point(ELIG, POLICY, VA, *NORFOLK_DOWNTOWN, {"status": "citizen"})
    crime = next(c for c in r["components"] if c["id"] == "crime")
    assert r["fips"] == "51710" and crime["level"] == "block" and "Norfolk police" in crime["reason"]
    c2 = va.fit_point(ELIG, POLICY, VA, *CVILLE_MALL, {"status": "citizen"})
    assert next(c for c in c2["components"] if c["id"] == "crime")["level"] == "block"
    town = va.fit_point(ELIG, POLICY, VA, *CHRISTIANSBURG, {"status": "citizen"})
    assert next(c for c in town["components"] if c["id"] == "crime")["level"] == "locality"


def test_local_camping_ban_scores_zero_and_cites_source():
    r = va.locality_fit(ELIG, POLICY, VA, "51650", {"status": "citizen"})
    c = next(c for c in r["components"] if c["id"] == "criminalization")
    assert c["score"] == 0 and c["source"].startswith("https://")
    tabled = next(c for c in va.locality_fit(ELIG, POLICY, VA, "51540", {"status": "citizen"})["components"]
                  if c["id"] == "criminalization")
    assert tabled["score"] is None and "tabled" in tabled["reason"]


def test_kids_switch_rent_to_two_bedroom():
    a = va.locality_fit(ELIG, POLICY, VA, "51121", {"status": "citizen"})
    b = va.locality_fit(ELIG, POLICY, VA, "51121", {"status": "citizen", "household": {"kids": True}})
    ra = next(c for c in a["components"] if c["id"] == "affordability")
    rb = next(c for c in b["components"] if c["id"] == "affordability")
    assert "studio" in ra["reason"] and "2-bedroom" in rb["reason"] and rb["score"] < ra["score"]


def test_confidence_formula_by_hand():
    rows = [{"id": "access", "weight": 0.5, "score": 80, "spec": 1.0, "fresh": 0.9, "level": "state law"},
            {"id": "crime", "weight": 0.3, "score": None, "spec": 0, "fresh": 0, "level": "none"},
            {"id": "shelter", "weight": 0.2, "score": 50, "spec": 0.7, "fresh": 0.7, "level": "region"}]
    c = va.confidence(rows, {"validity": 0.85, "issues": [{"code": "near_boundary", "text": "x", "factor": 0.85}]})
    q = (0.5 * 1.0 * 0.9 + 0.2 * 0.7 * 0.7) / 1.0
    assert c["data_quality"] == round(q, 3) and c["score"] == round(100 * 0.85 * q)
    assert [i["code"] for i in c["issues"]] == ["near_boundary", "missing_crime", "coarse_shelter"]


def test_status_never_needed_for_locality_scores():
    r = va.locality_fit(ELIG, POLICY, VA, "51121", {})
    assert r["score"] is not None
    assert next(c for c in r["components"] if c["id"] == "access")["score"] is None


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_matches_python_exactly(tmp_path):
    pts = [list(CHRISTIANSBURG), list(NORFOLK_DOWNTOWN), list(CVILLE_MALL), [37.1, -80.4], [-80.4089, 37.1299],
           [37.0, -75.3], [35.7796, -78.6382], [91, -80], [38.8823, -77.1711], [36.8529, -75.9780],
           [37.2710, -79.9414], [37.0299, -76.3452], [38.9, -77.0], [36.95, -76.33]]
    heat = [{"lat": 37.1299, "lon": -80.4089, "n": 3, "score": 62.5, "effective_n": 2.4},
            {"lat": 37.135, "lon": -80.405, "n": 1, "score": 40, "effective_n": 1},
            {"lat": 36.85, "lon": -76.29, "n": 2, "score": 30, "effective_n": 1.7}]
    cases = [
        {"profile": {"status": "citizen"}, "rank": True, "points": pts},
        {"profile": {"status": "undocumented", "household": {"kids": True}}, "rank": True, "points": pts[:4], "heat": heat},
        {"profile": {"status": "tps", "situation": {"tonight": True}, "priorities": ["crime", "affordability"]},
         "rank": True, "points": pts[:3]},
        {"profile": {}, "points": pts},
    ]
    f = tmp_path / "cases.json"
    f.write_text(json.dumps(cases))
    out = json.loads(subprocess.check_output(["node", str(HERE / "js" / "run_va.js"), str(f)]))
    for c, js in zip(cases, out):
        community = va.community_by_locality(VA, c["heat"]) if c.get("heat") else None
        assert _norm(community) == _norm(js["community"])
        if c.get("rank"):
            assert _norm(va.rank_localities(ELIG, POLICY, VA, c["profile"], community)) == _norm(js["ranked"])
        for p, jp in zip(c["points"], js["points"]):
            assert _norm(va.fit_point(ELIG, POLICY, VA, p[0], p[1], c["profile"], community)) == _norm(jp), p


def _norm(x):
    if isinstance(x, float):
        return None if math.isnan(x) else round(x, 9)
    if isinstance(x, bool) or x is None or isinstance(x, (int, str)):
        return x
    if isinstance(x, list):
        return [_norm(i) for i in x]
    return {k: _norm(v) for k, v in x.items()}
