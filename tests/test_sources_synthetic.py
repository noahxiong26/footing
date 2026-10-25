"""Parsers for keyed APIs against SYNTHETIC responses (shapes from provider docs, values made up)."""
import json
import shutil

from footing.config import Settings
from footing.http import Fetcher
from footing.sources.base import Context
from footing.sources.keyed_sources import (BLSLaus, CensusACS, EIAGasoline, GooglePlacesText, HudFMR,
                                           KrogerBasket, Transitland, eia_area_for_state)
from footing.sources.open_sources import NWS, CensusGeocoder

from .conftest import HERE, POINT


def ctx(settings):
    c = Context(lat=POINT[0], lon=POINT[1], settings=settings, fetcher=Fetcher(settings))
    CensusGeocoder().run(c)
    return c


def test_acs_median_rent(full_settings):
    r = CensusACS().run(ctx(full_settings))
    assert r.status == "ok" and r.measures["median_gross_rent"].value == 1000


def test_acs_suppressed_value_is_unknown(full_settings):
    (full_settings.fixture_dir / "census_acs__rent_51121.json").write_text(
        json.dumps([["NAME", "B25064_001E", "state", "county"], ["X", "-666666666", "51", "121"]]))
    r = CensusACS().run(ctx(full_settings))
    assert r.status == "unknown" and "suppressed" in r.reason


def test_bls_latest_month(full_settings):
    r = BLSLaus().run(ctx(full_settings))
    m = r.measures["unemployment_rate"]
    assert m.value == 4.0 and m.as_of == "August 2026"


def test_hud_fmr_finds_efficiency_anywhere(full_settings):
    r = HudFMR().run(ctx(full_settings))
    assert r.measures["fmr_studio"].value == 900.0
    assert r.measures["fmr_studio"].as_of == "FY2026"


def test_eia_regional_and_national(full_settings):
    r = EIAGasoline().run(ctx(full_settings))
    assert r.measures["gas_regular"].value == 3.0
    assert r.measures["gas_regular_us"].value == 3.2
    assert "regional" in r.measures["gas_regular"].note


def test_eia_area_mapping():
    assert eia_area_for_state("VA") == "R1Z"
    assert eia_area_for_state("CA") == "SCA"
    assert eia_area_for_state("TN") == "R20"
    assert eia_area_for_state(None) == "NUS"


def test_google_places_text_search(full_settings):
    r = GooglePlacesText().run(ctx(full_settings))
    assert {p.kind for p in r.places} == {"shelter", "food_bank"}


def test_transitland_stops(full_settings):
    r = Transitland().run(ctx(full_settings))
    assert len(r.places) == 2 and r.places[0].kind == "transit_stop"


def test_kroger_basket_uses_cheapest_price(full_settings):
    r = KrogerBasket().run(ctx(full_settings))
    assert r.status == "ok"
    # first item: promo 1.5 x qty 2 = 3.0; other nine: cheapest regular 2.0 x their qty
    lines = {l["item"]: l for l in r.measures["basket_lines"].value}
    assert lines["bread"]["unit_price"] == 1.5
    assert r.measures["basket_week"].value == round(3.0 + sum(
        2.0 * l["qty"] for k, l in lines.items() if k != "bread"), 2)


def test_nws_worst_alert_severity(full_settings):
    shutil.copy(HERE / "synthetic" / "nws__alerts_freeze.json", full_settings.fixture_dir / "nws__alerts.json")
    r = NWS().run(ctx(full_settings))
    assert r.measures["worst_alert_rank"].value == 3     # Severe beats Moderate
    assert len(r.measures["alerts"].value) == 2


def test_missing_key_in_live_mode_is_unknown_not_error():
    s = Settings(mode="live", fixture_dir=None, keys={})
    c = Context(lat=POINT[0], lon=POINT[1], settings=s, fetcher=Fetcher(s), county_fips="51121")
    r = HudFMR().run(c)
    assert r.status == "unknown" and "no API key" in r.reason


def test_missing_fixture_is_unknown(tmp_path):
    s = Settings(mode="replay", fixture_dir=tmp_path)
    c = Context(lat=POINT[0], lon=POINT[1], settings=s, fetcher=Fetcher(s))
    r = NWS().run(c)
    assert r.status == "unknown" and "not captured" in r.reason
