"""Point checks and point confidence: footing/va.py and its JS twin footing/web/vapoint.js.

Merged from the second Virginia engine main carried (its tests/test_va.py). That engine was never wired
into the app and has been retired, but its point checking was better than session 4's: it told a person
their coordinates looked swapped or rounded instead of flatly refusing them, and it let a doubtful point
lower confidence instead of being silently treated as exact. Those checks now live in the surviving engine
and are tested here, in Python and in JavaScript.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from footing import va, vafit
from footing.fit import load_eligibility

HERE = Path(__file__).resolve().parent
ELIG, VA = load_eligibility(), vafit.load_va()
CHRISTIANSBURG = (37.1299, -80.4089)
NORFOLK = (36.8508, -76.2859)
FALLS_CHURCH = (38.8847, -77.1712)     # 5 km^2 independent city: every point in it is near a line


# ---- refusals: never a guess, always a reason --------------------------------------------------------
@pytest.mark.parametrize("lat,lon,code", [
    (-80.4089, 37.1299, "swapped"),            # the commonest typo
    (37.0, -75.3, "open_water"),               # Chesapeake Bay
    (35.7796, -78.6382, "outside_virginia"),   # Raleigh
    (38.9072, -77.0369, "outside_virginia"),   # DC
    (91, -80, "off_globe"),
    (float("nan"), -80, "not_a_number"),
    (None, -80, "not_a_number"),
    ("x", -80, "not_a_number"),
])
def test_bad_points_are_refused_with_a_reason(lat, lon, code):
    r = va.check_point(lat, lon)
    assert r["ok"] is False and r["code"] == code
    assert r["validity"] == 0 and r["reason"]


def test_swapped_coordinates_say_what_you_probably_meant():
    r = va.check_point(-80.4089, 37.1299)
    assert r["suggest"] == {"lat": 37.1299, "lon": -80.4089}
    assert "37.1299, -80.4089" in r["reason"]


def test_a_point_in_another_state_names_that_state():
    assert "North Carolina" in va.check_point(35.7796, -78.6382)["reason"]


# ---- doubts: usable, but say how much to trust it ----------------------------------------------------
def test_an_exact_point_has_no_doubts():
    r = va.check_point(*CHRISTIANSBURG)
    assert r["ok"] and r["fips"] == "51121" and r["validity"] == 1.0 and r["issues"] == []


def test_rounded_coordinates_are_flagged_and_cost_validity():
    r = va.check_point(37.1, -80.4)
    assert r["ok"] and [i["code"] for i in r["issues"]] == ["coarse"]
    assert r["validity"] == 0.6 and "11 km" in r["issues"][0]["text"]


def test_near_a_locality_line_is_flagged():
    r = va.check_point(*FALLS_CHURCH)
    assert r["ok"] and any(i["code"] == "near_boundary" for i in r["issues"])
    assert r["validity"] < 1.0 and "Falls Church" in r["issues"][0]["text"]


def test_doubts_multiply():
    r = va.check_point(36.6, -83.5)      # rounded AND inside 1 km of the Lee County line
    assert [i["code"] for i in r["issues"]] == ["coarse", "near_boundary"]
    assert r["validity"] == pytest.approx(0.6 * 0.85, abs=0.001)


# ---- the point changes confidence, never the score ---------------------------------------------------
def test_a_doubtful_point_lowers_confidence_but_not_the_score():
    exact = vafit.fit_point(ELIG, VA, *CHRISTIANSBURG, {"status": "citizen"})
    rough = vafit.fit_point(ELIG, VA, 37.1, -80.4, {"status": "citizen"})
    assert exact["fips"] == rough["fips"] == "51121"
    assert exact["score"] == rough["score"], "where you tap inside a county cannot change the county's score"
    assert rough["confidence"] < exact["confidence"]
    assert [i["code"] for i in rough["point_issues"]] == ["coarse"]


def test_point_confidence_is_locality_confidence_times_validity():
    base = vafit.fit_score(ELIG, VA, "51121", {"status": "citizen"})
    pt = vafit.fit_point(ELIG, VA, 37.1, -80.4, {"status": "citizen"})
    assert pt["confidence"] == pytest.approx(round(base["confidence"] * 0.6, 3), abs=0.001)


def test_an_unusable_point_gets_no_score_at_all():
    r = vafit.fit_point(ELIG, VA, -80.4089, 37.1299, {"status": "citizen"})
    assert r["score"] is None and r["confidence"] == 0 and r["components"] == []
    assert r["point_issues"][0]["code"] == "swapped"


def test_a_good_point_still_scores_normally():
    r = vafit.fit_point(ELIG, VA, *NORFOLK, {"status": "citizen"})
    assert r["fips"] == "51710" and r["score"] is not None and r["confidence"] > 0


# ---- JS/Python parity --------------------------------------------------------------------------------
PARITY_POINTS = [
    CHRISTIANSBURG, (37.1, -80.4), FALLS_CHURCH, (-80.4089, 37.1299), (35.7796, -78.6382),
    (38.9072, -77.0369), (37.0, -75.3), (91, -80), (-91, -80), ("nan", -80), ("inf", -80),
    ("-Infinity", -80), ("x", -80), (None, -80), ("", -80), NORFOLK, (39.2, -77.2), (37.2296, -80.4139),
    (36.5, -82.2), (38.03, -78.48), (37.54, -77.43), (36.85, -76.0), (39.46, -78.35), (36.55, -79.39),
    (37.27, -76.70), (37.0, -76.4), (1.0, -80), (0, 0), (37.1299, -80.40890001), (38.9, -77.2),
]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_and_python_check_points_identically(tmp_path):
    f = tmp_path / "points.json"
    f.write_text(json.dumps(PARITY_POINTS))
    js = json.loads(subprocess.check_output(["node", str(HERE / "js" / "run_vapoint.js"), str(f)]))
    assert len(js) == len(PARITY_POINTS)
    for point, got in zip(PARITY_POINTS, js):
        want = va.check_point(*point)
        assert json.loads(json.dumps(want)) == got, point
