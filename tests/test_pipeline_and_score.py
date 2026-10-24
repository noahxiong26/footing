import json

import pytest

from footing.factors import CATEGORIES, PARAMS, Bundle, catalog_markdown
from footing.pipeline import build_receipt, dedupe, parse_profile, score

from .conftest import POINT


def test_category_weights_sum_to_100():
    assert sum(c.weight for c in CATEGORIES) == 100


def test_every_param_has_a_category_and_rule():
    ids = {c.id for c in CATEGORIES}
    for p in PARAMS:
        assert p.category in ids and p.rule and p.weight > 0


def test_receipt_from_real_captures(live_settings):
    r = build_receipt(*POINT, profile="car,kids", settings=live_settings)
    assert r["area"]["county_fips"] == "51121"
    assert 0 <= r["settle_score"] <= 100
    states = {c["id"]: c["state"] for c in r["categories"]}
    # no keys -> these categories must be Unknown, never zero
    assert states["shelter"] == "unknown" and states["cost"] == "unknown"
    shelter = next(c for c in r["categories"] if c["id"] == "shelter")
    assert shelter["score"] is None
    reasons = {u["parameter"]: u["reason"] for u in r["unknowns"]}
    assert "needs Google Places to confirm it" in reasons["shelters_3km"]
    money = {m["label"]: m for m in r["money"]}
    assert money["Gas, regular"]["state"] == "unknown" and money["Gas, regular"]["value"] is None
    assert money["State minimum wage"]["value"] == 12.77
    json.dumps(r)                                    # fully serializable


def test_full_run_every_built_param_is_known(full_settings):
    r = build_receipt(*POINT, profile="", settings=full_settings)
    unknown_built = [u for u in r["unknowns"]
                     if next(p for p in PARAMS if p.id == u["parameter"]).status == "built"]
    allowed = {"bed_pressure", "local_rules", "showers_5km", "restaurant_meals_3km",
               "transit_stops_1km", "day_centers_5km"}
    assert {u["parameter"] for u in unknown_built} <= allowed
    assert r["confidence"] > 0.4


def test_unknown_category_does_not_drag_score(live_settings):
    r = build_receipt(*POINT, settings=live_settings)
    known = [c for c in r["categories"] if c["state"] == "known"]
    kw = sum(c["weight"] for c in known)
    expected = sum(c["weight"] * c["score"] for c in known) / kw
    assert r["settle_score"] == pytest.approx(expected, abs=0.1)


def test_confidence_drops_when_sources_missing(live_settings, full_settings):
    a = build_receipt(*POINT, settings=live_settings)["confidence"]
    b = build_receipt(*POINT, settings=full_settings)["confidence"]
    assert b > a


def test_profiles_reweight():
    assert parse_profile("") == ["on_foot"]
    assert parse_profile("car") == ["car"]
    with pytest.raises(ValueError):
        parse_profile("helicopter")
    empty = Bundle(places=[], measures={}, sources={})
    w_foot = {c["id"]: c["weight"] for c in score(empty, ["on_foot"])["categories"]}
    w_kids = {c["id"]: c["weight"] for c in score(empty, ["on_foot", "kids"])["categories"]}
    assert w_kids["kids"] > w_foot["kids"]
    assert sum(w_kids.values()) == pytest.approx(100, abs=0.05)


def test_dedupe_merges_osm_and_google_copies(full_settings):
    r = build_receipt(*POINT, settings=full_settings)
    food = r["nearest"]["food_bank"]
    assert len(food) == 1 and food[0]["source"] == "osm"
    assert "google_places" in food[0]["tags"]["also_in"]


def test_catalog_markdown_lists_every_param():
    md = catalog_markdown()
    for p in PARAMS:
        assert p.label in md


def test_nothing_known_gives_no_score_not_zero(tmp_path):
    from footing.config import Settings
    r = build_receipt(*POINT, settings=Settings(mode="replay", fixture_dir=tmp_path))
    assert r["settle_score"] is None
    assert r["confidence"] == 0.0
