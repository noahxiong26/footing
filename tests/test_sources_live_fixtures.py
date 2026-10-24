"""Parsers against REAL responses captured 2026-10-24 (fixtures/christiansburg_2026-10-24)."""
from footing.http import Fetcher
from footing.sources.base import Context
from footing.sources.open_sources import (NWS, CensusGeocoder, OpenMeteo, OSMOverpass, SnapRetailers,
                                          UrbanSchools, classify_osm)

from .conftest import POINT


def ctx(settings):
    c = Context(lat=POINT[0], lon=POINT[1], settings=settings, fetcher=Fetcher(settings))
    CensusGeocoder().run(c)
    return c


def test_geocoder_resolves_montgomery_county(live_settings):
    c = ctx(live_settings)
    assert c.county_fips == "51121"
    assert c.county_name == "Montgomery County"
    assert c.state_abbr == "VA"


def test_nws_no_active_alerts_at_capture(live_settings):
    r = NWS().run(ctx(live_settings))
    assert r.status == "ok"
    assert r.measures["alerts"].value == []
    assert r.measures["worst_alert_rank"].value == -1
    assert r.measures["nws_city"].value == "Christiansburg, VA"


def test_open_meteo_counts_cold_nights(live_settings):
    r = OpenMeteo().run(ctx(live_settings))
    assert r.measures["lows_f"].value == [42.8, 38.4, 38.0, 41.4, 44.5, 41.2, 42.6]
    assert r.measures["freezing_nights_7d"].value == 0
    assert r.measures["cold_nights_7d"].value == 2          # 38.4 and 38.0
    assert r.measures["hot_days_7d"].value == 0


def test_snap_parses_all_retailers_and_flags_full_grocery(live_settings):
    r = SnapRetailers().run(ctx(live_settings))
    assert r.status == "ok"
    assert len(r.places) == 10
    kroger = next(p for p in r.places if p.name == "Kroger 345")
    assert kroger.tags["full_grocery"] is True
    assert kroger.tags["store_type"] == "Super Store"
    assert r.provenance.as_of == "2026-10-21"                 # dataLastEditDate from the layer


def test_osm_keeps_help_and_drops_senior_living_and_couriers(live_settings):
    r = OSMOverpass().run(ctx(live_settings))
    kinds = {p.kind for p in r.places}
    names = {p.name for p in r.places}
    assert "Agape Center NRV" in names and "food_bank" in kinds
    assert "Christiansburg Library" in names
    assert "FedEx" not in names                               # tagged amenity=post_office in OSM
    assert "Commonwealth Senior Living" not in names          # social_facility for seniors
    assert "shelter" not in kinds                             # real finding: OSM maps no shelter here
    assert "4 OSM features ignored" in r.reason


def test_classify_osm_rules():
    assert classify_osm({"amenity": "social_facility", "social_facility": "shelter",
                         "social_facility:for": "homeless"}) == "shelter"
    assert classify_osm({"amenity": "social_facility", "social_facility": "shelter",
                         "social_facility:for": "senior"}) is None
    assert classify_osm({"amenity": "social_facility", "social_facility": "outreach",
                         "social_facility:for": "homeless"}) == "day_center"
    assert classify_osm({"amenity": "post_office", "operator": "United States Postal Service"}) == "post_office"
    assert classify_osm({"amenity": "shelter"}) is None       # a bus or picnic shelter
    assert classify_osm({"shop": "laundry"}) == "laundry"


def test_urban_schools_filters_county_and_real_schools(live_settings):
    r = UrbanSchools().run(ctx(live_settings))
    names = {p.name for p in r.places}
    assert "CHRISTIANSBURG HIGH" in names
    assert "NEW RIVER VALLEY JUVENILE DETENTION HOME" not in names   # school_level -2
    assert {p.tags["level"] for p in r.places} == {"primary", "middle", "high"}
    assert len(r.places) == 19
