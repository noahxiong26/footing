"""Offline regression checks for scoped ordinance research; never request publishers."""
from copy import deepcopy
from datetime import date
import json

import pytest

from scripts import build_va_localities as builder


PRIORITY = {
    "51520", "51059", "51810", "51153", "51107", "51041", "51087",
    "51710", "51550", "51013", "51760", "51700", "51510",
}
SAMPLE = {
    "51640", "51530", "51117", "51103", "51680", "51036", "51600",
    "51197", "51075", "51071",
}
SCOPED = {"51059", "51107", "51087", "51550", "51013", "51700", "51510", "51600", "51680"}


@pytest.fixture
def research():
    return deepcopy(builder.LOCAL_RULES_RESEARCH)


@pytest.fixture(scope="module")
def fresh():
    return builder.build()


def test_research_covers_exact_requested_batch_with_dated_outcomes(research):
    assert set(research["localities"]) == PRIORITY | SAMPLE
    for fips, review in research["localities"].items():
        assert review["observations"], fips
        assert review["next_action"], fips
        for observation in review["observations"]:
            assert observation["url"].startswith("https://")
            assert date.fromisoformat(observation["retrieved_on"]) == date(2026, 10, 25)
            assert all(observation[k] for k in ("section", "coverage", "summary", "outcome"))
        # Previous saved claims remain available even when replaced by a better source.
        assert "previous_rule" in review and "previous_source" in review


def test_scoped_rule_export_is_repeatable_and_faithful_to_evidence(research, fresh):
    rules, sources = builder.reviewed_local_rules(research)
    assert set(rules) == SCOPED
    assert builder.reviewed_local_rules(research) == (rules, sources)
    for fips, (status, note, source_id) in rules.items():
        row = fresh["localities"][fips]["local_rule"]
        assert row == {"status": status, "note": note, "source": source_id, "score": 35}
        assert status == "limited_ban"
        assert fresh["sources"][source_id] == sources[source_id]
        assert sources[source_id]["read_on"] == "2026-10-25"
        evidence = research["localities"][fips]["observations"][
            research["localities"][fips]["decision"]["evidence_index"]
        ]
        assert evidence["section"] in sources[source_id]["note"]
        assert evidence["coverage"] in sources[source_id]["note"]


@pytest.mark.parametrize("outcome", [
    "access_failure", "primary_summary_read", "indexed_code_excerpt", "primary_index_read",
])
def test_failed_access_summaries_and_search_excerpts_cannot_create_scores(research, outcome):
    review = research["localities"]["51059"]
    review["observations"][review["decision"]["evidence_index"]]["outcome"] = outcome
    with pytest.raises(ValueError, match="primary operative"):
        builder.reviewed_local_rules(research)


def test_park_scope_cannot_silently_become_a_broad_ban(research):
    research["localities"]["51059"]["decision"]["status"] = "broad_ban"
    with pytest.raises(ValueError, match="geographic scope"):
        builder.reviewed_local_rules(research)


@pytest.mark.parametrize("index", [-1, True, 999])
def test_invalid_evidence_reference_is_rejected(research, index):
    research["localities"]["51059"]["decision"]["evidence_index"] = index
    with pytest.raises(ValueError, match="evidence index"):
        builder.reviewed_local_rules(research)


def test_fairfax_city_and_county_cannot_exchange_research(research, fresh):
    research["localities"]["51059"]["name"] = "Fairfax city"
    with pytest.raises(ValueError, match="name/FIPS mismatch"):
        builder.reviewed_local_rules(research)
    county = fresh["localities"]["51059"]
    city = fresh["localities"]["51600"]
    assert county["name"] == "Fairfax County"
    assert city["name"] == "Fairfax city"
    assert county["local_rule"]["source"] != city["local_rule"]["source"]


def test_unverified_zoning_and_failed_searches_stay_unknown(research, fresh):
    unknown = (PRIORITY | SAMPLE) - SCOPED - {"51520"}
    for fips in unknown:
        assert research["localities"][fips]["decision"] is None
        assert fresh["localities"][fips]["local_rule"] is None, fips
    # A blank decision has no effect even if it carries an accessible zoning source.
    assert builder.reviewed_local_rules(research)[0].keys() == SCOPED


def test_bristol_is_explicitly_disputed_instead_of_falsely_resolved(research, fresh):
    review = research["localities"]["51520"]
    assert review["progress"] == "disputed_scope" and review["decision"] is None
    assert review["previous_rule"]["status"] == "broad_ban"
    row = fresh["localities"]["51520"]["local_rule"]
    assert row["status"] == "broad_ban" and row["score"] == 0
    assert "provisional" in row["note"] and "unverified" in row["note"]
    assert row["source"] == "bristol_council_2024"
    assert "Class 4" not in row["note"]  # stale 2022 penalty must not masquerade as current law


def test_rule_batch_does_not_refresh_other_locality_fields(fresh):
    saved = json.loads(builder.OUT.read_text(encoding="utf-8"))
    for fips, row in fresh["localities"].items():
        assert {k: v for k, v in row.items() if k != "local_rule"} == {
            k: v for k, v in saved["localities"][fips].items() if k != "local_rule"
        }
    for name in ("state", "field_sources", "incident_cities", "incident_tiles", "incident_scale"):
        assert fresh[name] == saved[name]
    assert builder.validate(fresh) == []


@pytest.mark.parametrize("status,score", [
    ("no_ban", 100), ("limited_ban", 0), ("proposed", 35),
    ("clearing_policy", 0), ("checked_none_found", 0),
])
def test_validation_rejects_invented_statuses_and_inconsistent_scores(fresh, status, score):
    data = deepcopy(fresh)
    data["localities"]["51059"]["local_rule"].update(status=status, score=score)
    assert builder.validate(data)


def test_searched_none_remains_unscored_and_uncited(fresh):
    row = fresh["localities"]["51121"]["local_rule"]
    assert row["status"] == "checked_none_found"
    assert row["source"] is None and row["score"] is None
