"""Fit Score: data integrity, formula properties, and JS/Python parity."""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from footing import fit
from scripts.build_state_policy import build, validate

HERE = Path(__file__).resolve().parent
ELIG, POLICY = fit.load_eligibility(), fit.load_policy()
STATUSES = [s["id"] for s in ELIG["statuses"]]


# ---- data -------------------------------------------------------------------------------------------
def test_policy_data_validates_against_publisher_totals():
    assert validate(build()) == []


def test_committed_policy_json_matches_build_script():
    assert json.loads(json.dumps(build())) == POLICY, "run: python scripts/build_state_policy.py"


def test_every_field_cites_a_source():
    for field, src in POLICY["field_sources"].items():
        assert src in POLICY["sources"], field
        assert POLICY["sources"][src]["url"].startswith("https://")
    for p in ELIG["programs"]:
        for s in p["sources"]:
            assert s in ELIG["sources"], (p["id"], s)


def test_every_program_answers_every_status():
    allowed = {"yes", "limited", "no", "varies"}
    for p in ELIG["programs"]:
        for s in STATUSES:
            r = fit.program_rule(ELIG, p["id"], s)
            assert r["value"] in allowed, (p["id"], s)
            if r["value"] == "limited":
                assert r["note"], f"'limited' needs a note saying who: {p['id']}/{s}"


def test_known_2026_rule_changes_are_encoded():
    # H.R. 1: refugees/asylees lost SNAP; Medicaid narrowed Oct 1 2026; public charge rule Sept 18 2026.
    assert fit.program_rule(ELIG, "snap", "refugee_asylee")["value"] == "no"
    assert fit.program_rule(ELIG, "snap", "lpr5")["value"] == "yes"
    assert "Oct 1, 2026" in fit.program_rule(ELIG, "medicaid", "refugee_asylee")["note"]
    assert "Sept 18, 2026" in fit.program_rule(ELIG, "public_charge", "tps")["note"]
    assert fit.program_rule(ELIG, "public_charge", "refugee_asylee")["value"] == "no"   # exempt
    assert fit.program_rule(ELIG, "survival", "undocumented")["value"] == "yes"
    for s in ("asylum_pending", "parole", "tps", "refugee_asylee"):   # H.R. 1: Marketplace credits end 2027
        assert "Jan 1, 2027" in fit.program_rule(ELIG, "aca", s)["note"], s


def test_camping_law_levels_are_ordered_and_documented():
    # A ban is worse than a law that pushes local enforcement, which is worse than a ban struck down in court.
    def camp(code):
        return {c["id"]: c for c in fit.fit_score(ELIG, POLICY, code, {"status": "citizen"})["components"]}["criminalization"]
    assert camp("TX")["score"] == 0            # HB 1925: statewide ban
    assert camp("GA")["score"] == 25           # "Safe Neighborhood": enforcement pressure, not a ban
    assert camp("OK")["score"] == 25
    assert camp("KY")["score"] == 50           # ban ruled unconstitutional
    # Session 3 asserted VA was Unknown here. Session 4 read the statute and confirmed there is no statewide
    # ban, so VA is now a checked "none_statewide" (75), tested in full below. A state nobody has checked is
    # still Unknown and must never be read as "no ban" - WY stands in for that case.
    assert camp("VA")["score"] == 75
    assert camp("WY")["score"] is None
    statuses = {st["camping_law"]["status"] for st in POLICY["states"].values() if st["camping_law"]}
    assert statuses <= {"in_effect", "enforcement_mandate", "contested", "none_statewide"}


# ---- formula ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("n", [1, 2, 3, 5, 6])
def test_roc_weights(n):
    w = fit.roc_weights(n)
    assert sum(w) == pytest.approx(1.0)
    assert all(a > b for a, b in zip(w, w[1:]))
    assert w[0] == pytest.approx(sum(1 / i for i in range(1, n + 1)) / n)


def test_roc_six_published_values():
    # Barron & Barrett (1996) table for n = 6.
    assert [round(x, 3) for x in fit.roc_weights(6)] == [0.408, 0.242, 0.158, 0.103, 0.061, 0.028]


def test_unknown_components_never_count_as_zero():
    r = fit.fit_score(ELIG, POLICY, "VA", {"status": "citizen"})
    known = [c for c in r["components"] if c["score"] is not None]
    expected = sum(c["weight"] * c["score"] for c in known) / sum(c["weight"] for c in known)
    assert r["score"] == pytest.approx(expected, abs=0.06)
    assert any(c["score"] is None for c in r["components"])          # VA camping law: not checked


def test_citizens_get_no_enforcement_component_but_mixed_households_do():
    ids = [c["id"] for c in fit.fit_score(ELIG, POLICY, "TX", {"status": "citizen"})["components"]]
    assert "safety" not in ids
    mixed = fit.fit_score(ELIG, POLICY, "TX", {"status": "citizen", "household": {"mixed": True}})
    assert "safety" in [c["id"] for c in mixed["components"]]


def test_high_risk_status_puts_safety_first_tonight_puts_shelter_first():
    assert fit.default_priorities(ELIG, {"status": "undocumented"})[0] == "safety"
    assert fit.default_priorities(ELIG, {"status": "tps"})[2] == "safety"
    assert fit.default_priorities(ELIG, {"status": "undocumented", "situation": {"tonight": True}})[:2] == ["shelter", "safety"]


def test_undisclosed_status_is_not_guessed():
    r = fit.fit_score(ELIG, POLICY, "CA", {"status": "undisclosed"})
    access = next(c for c in r["components"] if c["id"] == "access")
    assert access["score"] is None and "not scored" in access["reason"]
    blank = next(c for c in fit.fit_score(ELIG, POLICY, "CA", {})["components"] if c["id"] == "access")
    assert blank["score"] is None and "stays on this phone" in blank["reason"]
    assert r["score"] is not None                                    # still scored on status-free parts


def test_drivers_license_law_raises_undocumented_access():
    comps = lambda st: fit.components(ELIG, POLICY, st, {"status": "undocumented"})["access"]["parts"]["id"]
    assert comps("VA") == 1.0 and comps("NC") == 0.0                  # VA privilege card; NC none


def test_medicaid_expansion_matters_for_childless_citizens_only():
    h = lambda st, hh: fit.components(ELIG, POLICY, st, {"status": "citizen", "household": hh})["access"]["parts"]["health"]
    assert h("VA", {}) == 1.0 and h("TX", {}) == 0.35
    assert h("TX", {"kids": True}) == 0.75


def test_user_priorities_reweight():
    a = fit.fit_score(ELIG, POLICY, "CA", {"status": "citizen", "priorities": ["shelter"]})
    assert a["components"][0]["id"] == "shelter" and a["components"][0]["weight"] == pytest.approx(0.457, abs=1e-3)


def test_rank_robustness_is_reproducible_and_bounded():
    r1 = fit.rank_states(profile={"status": "daca"}, samples=120, seed=3)
    r2 = fit.rank_states(profile={"status": "daca"}, samples=120, seed=3)
    assert r1 == r2
    for r in r1:
        assert r["rank_p10"] <= r["rank_p90"] and 0 <= r["p_top5"] <= 1


def test_bayes_shrinks_small_samples_and_decays_old_ratings():
    now = 1_800_000_000_000
    one = fit.bayes_score([{"t": now, "stars": 5}], now)
    many = fit.bayes_score([{"t": now, "stars": 5}] * 30, now)
    assert 50 < one["score"] < many["score"] < 100
    old = fit.bayes_score([{"t": now - 365 * 86400000, "stars": 5}] * 30, now)
    assert old["score"] < many["score"]
    assert fit.bayes_score([], now)["score"] == 50.0                 # prior: neutral


def test_js_round_matches_javascript():
    assert fit.round1(0.25) == 0.3 and fit.round1(-0.25) == -0.2 and fit.js_round(2.5) == 3.0


# ---- parity -----------------------------------------------------------------------------------------
def _norm(x):
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, list):
        return [_norm(i) for i in x]
    return {k: _norm(v) for k, v in x.items()}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_engine_matches_python_exactly(tmp_path):
    now = 1_790_000_000_000
    cases = [{"profile": {"status": s}} for s in STATUSES] + [
        {"profile": {"status": "undocumented", "household": {"kids": True, "mixed": True}}},
        {"profile": {"status": "lpr", "household": {"kids": True}, "situation": {"no_id": True}}},
        {"profile": {"status": "lpr", "age_band": "62_plus"}},
        {"profile": {"status": "tps", "situation": {"tonight": True}, "priorities": ["community", "affordability"]}},
        {"profile": {"status": "citizen", "household": {"mixed": True, "pregnant": True}},
         "community": {"VA": {"n": 3, "score": 71.2, "freshness": 0.3}}},
        {"profile": {"status": "citizen"}, "ratings": [{"t": now - i * 86400000 * 9, "stars": 1 + i % 5} for i in range(23)],
         "now": now},
    ]
    f = tmp_path / "cases.json"
    f.write_text(json.dumps(cases))
    out = json.loads(subprocess.check_output(["node", str(HERE / "js" / "run_fit.js"), str(f)]))
    for c, js in zip(cases, out):
        py = fit.rank_states(profile=c["profile"], community=c.get("community"))
        assert _norm(py) == _norm(js["ranked"]), c["profile"]
        if c.get("ratings"):
            assert _norm(fit.bayes_score(c["ratings"], c["now"])) == _norm(js["bayes"])


def test_enforcement_mandate_is_not_scored_as_a_statewide_ban():
    # GA/OK "Safe Neighborhood" laws pressure cities to enforce; they are not statewide bans (session-3 finding).
    for st in ("GA", "OK"):
        assert POLICY["states"][st]["camping_law"]["status"] == "enforcement_mandate"
        crim = fit.components(ELIG, POLICY, st, {"status": "citizen"})["criminalization"]
        assert crim["score"] == 25 and "enforce" in crim["reason"]
    assert fit.components(ELIG, POLICY, "FL", {"status": "citizen"})["criminalization"]["score"] == 0


def test_aca_notes_mention_2027_cutoff_for_asylum_and_parole():
    for s in ("asylum_pending", "parole"):
        assert "Jan 1, 2027" in fit.program_rule(ELIG, "aca", s)["note"]


def test_virginia_has_no_statewide_ban_and_scores_75():
    assert POLICY["states"]["VA"]["camping_law"]["status"] == "none_statewide"
    c = fit.components(ELIG, POLICY, "VA", {"status": "citizen"})
    assert c["criminalization"]["score"] == 75
