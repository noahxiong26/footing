"""Virginia Fit: data integrity, bad-input handling, formula properties, and JS/Python parity."""
import json
import math
import shutil
import subprocess

import pytest

from footing import va as vageo
from footing import vafit
from footing.fit import load_eligibility
from scripts.build_va_localities import build, validate

ELIG, VA = load_eligibility(), vafit.load_va()
LOCS = VA["localities"]
HERE = __import__("pathlib").Path(__file__).resolve().parent


# ---- data -------------------------------------------------------------------------------------------
def test_va_data_validates_against_publisher_totals():
    assert validate(VA) == []


def test_committed_va_json_matches_build_script():
    assert json.loads(json.dumps(build())) == json.loads(json.dumps(VA)), "run: python scripts/build_va_localities.py"


def test_every_locality_has_a_shape_and_data():
    shapes = {d["fips"] for d in vageo.localities()}
    assert len(LOCS) == 133 and set(LOCS) == shapes
    assert sum(1 for l in LOCS.values() if l["kind"] == "city") == 38


def test_every_va_field_cites_a_source():
    for field, src in VA["field_sources"].items():
        if src == "local_rule.source":      # each rule names its own source, checked below
            continue
        assert src in VA["sources"], field
    for f, l in LOCS.items():
        if l["local_rule"]:
            assert l["local_rule"]["source"] in VA["sources"], f
    for s in VA["sources"].values():
        assert s["url"].startswith("https://")


def test_city_and_county_with_same_name_stay_apart():
    assert LOCS["51770"]["name"] == "Roanoke city" and LOCS["51161"]["name"] == "Roanoke County"
    assert LOCS["51770"]["local_rule"]["status"] == "limited_ban" and LOCS["51161"]["local_rule"] is None


# ---- bad coordinates ----------------------------------------------------------------------------------
@pytest.mark.parametrize("lat,lon,code,fips", [
    (37.2296, -80.4139, "ok", "51121"),            # Blacksburg (Montgomery County)
    (37.1318, -80.5764, "ok", "51750"),            # Radford city, not Montgomery or Pulaski
    (38.8823, -77.1711, "ok", "51610"),            # Falls Church city (2 sq mi)
    (37.5407, -77.4360, "ok", "51760"),            # Richmond city
    (37.30, -76.10, "open_water", None),            # Chesapeake Bay
    (38.9072, -77.0369, "outside_virginia", None),  # Washington, DC
    (35.7796, -78.6382, "outside_virginia", None),  # Raleigh, NC
    (float("nan"), -77.0, "not_a_number", None),
    (float("inf"), -77.0, "not_a_number", None),
    ("abc", -77.0, "not_a_number", None),
    (95.0, -77.0, "off_globe", None),
    (48.8566, 2.3522, "outside_virginia", None),    # Paris
])
def test_check_point_never_guesses(lat, lon, code, fips):
    r = vageo.check_point(lat, lon)
    assert r["code"] == code, r
    assert r["ok"] == (code == "ok")
    if fips:
        assert r["fips"] == fips
    if not r["ok"]:
        assert r["reason"]


# ---- formula ----------------------------------------------------------------------------------------
def test_scores_are_in_range_and_confidence_reflects_known_parts():
    for r in vafit.rank_localities(ELIG, VA, {}, robustness=False):
        assert r["score"] is not None and 0 <= r["score"] <= 100
        assert 0 < r["confidence"] <= 1
        known = [c for c in r["components"] if c["score"] is not None]
        assert math.isclose(sum(c["share"] for c in known), 1.0, abs_tol=0.003)
        for c in r["components"]:
            assert c["reason"], (r["name"], c["id"])


def test_unknown_is_never_zero():
    r = vafit.fit_score(ELIG, VA, "51121", {})
    laws = next(c for c in r["components"] if c["id"] == "laws")
    assert laws["score"] is None and laws["contribution"] == 0 and laws["share"] == 0
    assert "not counted" in laws["reason"]


def test_local_camping_rules_score_as_documented():
    get = lambda f: next(c for c in vafit.fit_score(ELIG, VA, f, {})["components"] if c["id"] == "laws")
    assert get("51650")["score"] == 0          # Hampton: broad ban
    assert get("51770")["score"] == 35         # Roanoke city: limited ban
    assert get("51540")["score"] == 60         # Charlottesville: site closure
    assert get("51590")["score"] is None       # Danville: proposed only
    assert get("51059")["score"] is None       # Fairfax County: policy, not ordinance


def test_rent_uses_the_bedrooms_the_person_needs():
    hours = lambda p: next(c for c in vafit.fit_score(ELIG, VA, "51121", p)["components"] if c["id"] == "rent")["parts"]
    assert hours({})["bedrooms"] == 1
    assert hours({"household": {"kids": True}})["bedrooms"] == 2
    assert hours({"household": {"kids": True, "bedrooms": 3}})["bedrooms"] == 3
    assert hours({"household": {"bedrooms": 0}})["rent"] == LOCS["51121"]["fmr"]["by_bedrooms"][0]
    assert hours({"household": {"bedrooms": 9}})["bedrooms"] == 1          # out of range -> default
    assert hours({"household": {"bedrooms": True}})["bedrooms"] == 1       # not a number -> default
    assert hours({"household": {"bedrooms": 4}})["hours"] > hours({"household": {"bedrooms": 0}})["hours"]


def test_kids_switch_shelter_to_family_beds():
    c = lambda p: next(x for x in vafit.fit_score(ELIG, VA, "51760", p)["components"] if x["id"] == "shelter")
    assert c({"household": {"kids": True}})["parts"]["beds"] == LOCS["51760"]["coc"]["beds_family"]
    assert c({})["parts"]["beds"] == LOCS["51760"]["coc"]["beds_year_round"]


def test_safety_only_for_people_at_risk_and_287g_task_force_scores_low():
    ids = lambda p: [c["id"] for c in vafit.fit_score(ELIG, VA, "51009", p)["components"]]
    assert "safety" not in ids({"status": "citizen"})
    assert ids({"status": "undocumented"})[0] == "safety"
    amherst = next(c for c in vafit.fit_score(ELIG, VA, "51009", {"status": "undocumented"})["components"] if c["id"] == "safety")
    assert amherst["score"] == 10 and "task force" in amherst["reason"]


def test_crime_is_off_unless_asked_and_unknown_when_reporting_is_missing():
    assert "crime" not in [c["id"] for c in vafit.fit_score(ELIG, VA, "51121", {})["components"]]
    on = {"show_crime": True}
    assert next(c for c in vafit.fit_score(ELIG, VA, "51121", on)["components"] if c["id"] == "crime")["score"] is not None
    vb = next(c for c in vafit.fit_score(ELIG, VA, "51810", on)["components"] if c["id"] == "crime")
    assert vb["score"] is None and "Not counted" in vb["reason"]       # Virginia Beach PD sent no 2025 data


def test_small_places_are_shrunk_toward_the_state_rate():
    tot = vafit.state_totals(VA)
    tiny = vafit.shrunk_rate(1, 2000, tot["grocery"], tot["pop"])
    raw = 1 / 2000 * 10000
    state = tot["grocery"] / tot["pop"] * 10000
    assert state < tiny < raw


def test_community_ratings_count_and_raise_confidence():
    base = vafit.fit_score(ELIG, VA, "51121", {})
    rated = vafit.fit_score(ELIG, VA, "51121", {}, {"51121": {"n": 8, "score": 90.0, "freshness": 0.9}})
    assert rated["confidence"] > base["confidence"]
    assert next(c for c in rated["components"] if c["id"] == "community")["score"] == 90.0


def test_priorities_reorder_weights():
    r = vafit.fit_score(ELIG, VA, "51121", {"priorities": ["services", "rent"]})
    assert [c["id"] for c in r["components"]][:2] == ["services", "rent"]
    assert r["components"][0]["weight"] > r["components"][1]["weight"]


def test_robust_rank_band_contains_rank():
    for r in vafit.rank_localities(ELIG, VA, {}, samples=60):
        assert r["rank_p10"] <= r["rank_p90"]


# ---- JS/Python parity --------------------------------------------------------------------------------
CASES = [
    {"profile": {}},
    {"profile": {"household": {"kids": True}}},
    {"profile": {"status": "undocumented", "household": {"kids": True, "bedrooms": 3}}},
    {"profile": {"status": "tps", "situation": {"tonight": True}}},
    {"profile": {"status": "citizen", "show_crime": True, "priorities": ["crime", "services"]}},
    {"profile": {"household": {"bedrooms": 0, "mixed": True}, "priorities": ["rent"]},
     "community": {"51121": {"n": 4, "score": 72.5, "freshness": 0.8}, "51760": {"n": 1, "score": 25.0, "freshness": 0.4}}},
    {"profile": {"status": "undisclosed", "household": {"bedrooms": 4}}, "samples": 50},
]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_and_python_agree(tmp_path):
    f = tmp_path / "cases.json"
    f.write_text(json.dumps(CASES))
    js = json.loads(subprocess.check_output(["node", str(HERE / "js" / "run_vafit.js"), str(f)]))
    for case, got in zip(CASES, js):
        want = vafit.rank_localities(ELIG, VA, case["profile"], case.get("community"), samples=case.get("samples", 200))
        assert json.loads(json.dumps(want)) == got, case
