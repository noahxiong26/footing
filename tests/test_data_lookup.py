"""Compact lookups must preserve Unknown and include the sources needed to resume research."""
import json
from pathlib import Path

import pytest

from scripts.data_lookup import FIELD_SOURCES, lookup

DATA = json.loads((Path(__file__).resolve().parents[1] / "footing/static/va_localities.json")
                  .read_text(encoding="utf-8"))


@pytest.mark.parametrize("field", FIELD_SOURCES)
def test_one_field_lookup_preserves_the_capture_and_resolves_its_sources(field):
    result = lookup(DATA, "51710", field)
    assert result["field"] == field and result["value"] == DATA["localities"]["51710"][field]
    assert set(FIELD_SOURCES[field]) <= result["sources"].keys()
    assert "localities" not in result


def test_missing_crime_does_not_become_zero_or_borrow_another_citys_incidents():
    result = lookup(DATA, "51810", "crime")
    assert result["value"]["violent_2025"] is None
    assert result["value"]["unknown_reason"]
    assert result["incident_coverage"] is None and "city_incidents" not in result["sources"]


def test_a_local_rule_includes_its_specific_citation():
    result = lookup(DATA, "51520", "local_rule")
    assert result["value"]["source"] in result["sources"]


def test_incident_coverage_keeps_the_publishers_url_and_capture_dates():
    result = lookup(DATA, "51540", "crime")
    city = result["incident_coverage"]
    assert "charlottesville.org" in city["source_url"]
    assert result["sources"]["city_incidents"]["url"] == city["source_url"]
    assert city["window_start"] == "2025-10-24" and city["latest_date"] == "2026-10-23"
