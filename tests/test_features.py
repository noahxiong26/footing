"""Open-now hours, enrichment, Gemma planner + validator, flyer reader, compare/tonight/card views."""
import json
from datetime import datetime

import pytest

from footing.enrich import enrich
from footing.flyer import FlyerError, read_flyer
from footing.gemma import GemmaClient, GemmaUnavailable, extract_json
from footing.hours import closes_today, is_open, parse
from footing.models import Place
from footing.pipeline import build_receipt
from footing.planner import candidates, make_plan, rule_based, validate
from footing.views import compare, pocket_card_svg, tonight

from .conftest import POINT

SAT_1330 = datetime(2026, 10, 24, 13, 30)   # a Saturday
MON_0800 = datetime(2026, 10, 26, 8, 0)


# ---- opening hours (strings are real OSM tags from the Christiansburg capture) ----
def test_library_hours():
    h = "Mo-Th 09:00-20:00; Fr, Sa 10:00-17:00; Su 13:00-17:00"
    assert is_open(h, SAT_1330) is True
    assert closes_today(h, SAT_1330).strftime("%H:%M") == "17:00"
    assert is_open(h, MON_0800) is False


def test_post_office_split_and_saturday():
    h = "Mo-Fr 08:00-12:00,13:00-16:30; Sa 08:00-11:00"
    assert is_open(h, datetime(2026, 10, 26, 12, 30)) is False      # lunch gap
    assert is_open(h, datetime(2026, 10, 26, 13, 5)) is True
    assert is_open(h, SAT_1330) is False


def test_off_overnight_247_and_unsupported():
    assert is_open("Mo-Fr 07:45-16:30; Sa-Su off", SAT_1330) is False
    assert is_open("Mo-Su 20:00-08:00", datetime(2026, 10, 27, 2, 0)) is True
    assert is_open("Mo-Su 20:00-08:00", datetime(2026, 10, 27, 12, 0)) is False
    assert is_open("24/7", SAT_1330) is True
    assert parse("Mo-Fr 09:00-17:00; PH off") is None                 # holidays: honest Unknown
    assert parse("sunrise-sunset") is None
    assert is_open(None, SAT_1330) is None


# ---- enrichment ----
def test_snap_pharmacy_name_becomes_pharmacy():
    snap = Place(id="snap:1", name="CVS PHARMACY 7543", kind="snap_retailer", lat=37.1, lon=-80.4,
                 source="snap", tags={"address": "550 N Franklin St"}, distance_m=1000, walk_min=16)
    dg = Place(id="snap:2", name="Dollar General 3722", kind="snap_retailer", lat=37.1, lon=-80.4, source="snap")
    out = enrich([snap, dg])
    pharm = [p for p in out if p.kind == "pharmacy"]
    assert len(pharm) == 1 and pharm[0].tags["inferred_from"] == "USDA SNAP store name"
    assert dg.tags["discount_store"] is True


def test_receipt_now_counts_cvs_as_pharmacy(live_settings):
    r = build_receipt(*POINT, settings=live_settings, now=SAT_1330)
    names = [p["name"] for p in r["nearest"]["pharmacy"]]
    assert "CVS PHARMACY 7543" in names
    lib = r["nearest"]["library"][0]
    assert lib["open_now"] is True and lib["closes"] == "17:00"


def test_replay_never_leaks_to_another_town(live_settings):
    r = build_receipt(37.2710, -79.9414, settings=live_settings)   # Roanoke, not recorded
    assert r["settle_score"] is None and r["area"]["county"] is None
    assert all(s["status"] != "ok" for s in r["sources"] if s["source"] != "static_tables")


# ---- Gemma client + planner ----
def fake_transport(payload: dict | str):
    calls = []

    def t(url, body):
        calls.append((url, body))
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return {"candidates": [{"content": {"parts": [{"text": "thinking...", "thought": True}, {"text": text}]}}]}
    t.calls = calls
    return t


def test_extract_json_from_fenced_text():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_client_requires_key():
    with pytest.raises(GemmaUnavailable):
        GemmaClient(None)


def test_planner_keeps_grounded_steps_and_drops_invented_ones(live_settings):
    r = build_receipt(*POINT, profile="kids", settings=live_settings, now=SAT_1330)
    lib_id = r["nearest"]["library"][0]["id"]
    plan = {"summary": "ok", "day1": [
        {"action": "Charge your phone at the library.", "place_id": lib_id, "why": "free power"},
        {"action": "Go to Hope Shelter.", "place_id": "osm:node/999999", "why": "invented"},
        {"action": "Go to 123 Main Street shelter.", "place_id": None, "why": "address from nowhere"},
        {"action": "Call 211 about beds tonight.", "place_id": None, "why": "no shelter confirmed"}],
        "week1": [], "month1": []}
    t = fake_transport(plan)
    out = make_plan(r, r["profile"], client=GemmaClient("k", transport=t))
    assert out["engine"].startswith("gemma-4")
    acts = [s["action"] for s in out["plan"]["day1"]]
    assert acts == ["Charge your phone at the library.", "Call 211 about beds tonight."]
    assert out["plan"]["day1"][0]["place"]["name"] == "Christiansburg Library"
    reasons = sorted(x["reason"] for x in out["removed"])
    assert "address or phone not from data" in reasons
    assert any("not in pipeline data" in x for x in reasons)
    url, body = t.calls[0]
    assert "gemma-4" in url and "CANDIDATES" in body["contents"][0]["parts"][-1]["text"]
    assert "key=" not in url
    assert "systemInstruction" in body


def test_planner_falls_back_without_key(live_settings):
    r = build_receipt(*POINT, profile="kids", settings=live_settings)
    out = make_plan(r, r["profile"], api_key=None)
    assert out["engine"] == "rule-based" and "rule-based" in out["note"]
    day1 = [s["action"] for s in out["plan"]["day1"]]
    assert day1[0].startswith("Call 211")            # no shelter confirmed -> 211, not a guess
    assert any("homeless liaison" in s["action"] for s in out["plan"]["week1"])
    assert out["removed"] == []                       # rule-based plan is grounded by construction


def test_rule_based_prefers_full_grocery(live_settings):
    r = build_receipt(*POINT, settings=live_settings)
    plan = rule_based(r, r["profile"])
    ebt = next(s for s in plan["day1"] if s["action"].startswith("Use EBT"))
    assert candidates(r)[ebt["place_id"]]["full_grocery"] is True


def test_ungrounded_model_plan_falls_back(live_settings):
    r = build_receipt(*POINT, settings=live_settings)
    bad = {"summary": "x", "day1": [{"action": "Go to 12 Oak Street.", "place_id": None}],
           "week1": "not a list", "month1": [{"action": "y", "place_id": ["weird"]}]}
    out = make_plan(r, r["profile"], client=GemmaClient("k", transport=fake_transport(bad)))
    assert out["engine"] == "rule-based" and "no steps" in out["note"] and out["plan"]["day1"]
    assert len(out["removed"]) == 2
    clean, removed = validate(["not", "a", "dict"], {})
    assert removed[0]["reason"] == "malformed" and clean["day1"] == []


def test_validate_caps_steps():
    cands = {"a": {"id": "a", "name": "A"}}
    plan = {"day1": [{"action": f"step {i}", "place_id": "a"} for i in range(9)]}
    clean, _ = validate(plan, cands)
    assert len(clean["day1"]) == 4


# ---- flyer ----
def test_flyer_fields_and_warnings():
    t = fake_transport({"service": "Free hot meals", "days_times": "Tue 5-7pm", "phone": "540-555",
                        "address": None, "readable": True})
    out = read_flyer(b"\xff\xd8fake", "image/jpeg", client=GemmaClient("k", transport=t))
    assert out["fields"]["service"] == "Free hot meals" and out["fields"]["address"] is None
    assert out["status"] == "community-reported, unconfirmed"
    assert any("phone" in w for w in out["warnings"])
    part = t.calls[0][1]["contents"][0]["parts"][0]
    assert part["inline_data"]["mime_type"] == "image/jpeg"


def test_flyer_rejects_bad_input():
    with pytest.raises(FlyerError):
        read_flyer(b"x", "application/pdf", client=GemmaClient("k", transport=fake_transport({})))
    with pytest.raises(GemmaUnavailable):
        read_flyer(b"x", "image/png", api_key=None)


# ---- views ----
def test_tonight_puts_open_places_first_and_admits_no_shelter(live_settings):
    r = build_receipt(*POINT, profile="tonight", settings=live_settings, now=SAT_1330)
    t = tonight(r)
    assert t["places"][0]["name"] == "Christiansburg Library" and t["places"][0]["open_now"] is True
    assert t["shelter_data"] == "unknown" and "211" in t["message"]
    assert t["tonight_low_f"] == 42.8
    assert all(p["walk_min"] is None or p["walk_min"] <= 60 for p in t["places"])


def test_compare_does_not_compare_unknowns(live_settings, full_settings):
    a = build_receipt(*POINT, settings=live_settings)
    b = build_receipt(*POINT, settings=full_settings)
    c = compare([a, b])
    assert len(c["categories"]) == 10
    assert any("Not compared" in x for x in c["what_changes"])


def test_pocket_card_is_valid_svg_with_qr(live_settings):
    import xml.etree.ElementTree as ET
    r = build_receipt(*POINT, settings=live_settings, now=SAT_1330)
    svg = pocket_card_svg(r, "https://example.org/#/receipt?lat=37.125&lon=-80.405")
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "Call 211" in svg and "Christiansburg Library" in svg
    assert "(unnamed)" not in svg
