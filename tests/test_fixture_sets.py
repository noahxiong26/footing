"""Multi-town replay: each recorded set answers only for its own tile, and `footing record` writes a manifest."""
import json
import shutil

from footing.config import DEFAULT_FIXTURES, Settings
from footing.geo import snap_to_tile
from footing.http import Fetcher
from footing.pipeline import build_receipt, record_fixture_set, recorded_sets, resolve_replay

from .conftest import POINT

ROANOKE = (37.2710, -79.9414)


def _parent_with_two_sets(tmp_path):
    root = tmp_path / "fixtures"
    shutil.copytree(DEFAULT_FIXTURES, root / "christiansburg")
    fake = root / "roanoke"
    fake.mkdir()
    (fake / "MANIFEST.json").write_text(json.dumps({
        "point": {"lat": ROANOKE[0], "lon": ROANOKE[1], "label": "Test Roanoke"},
        "captured_at": "2026-10-24T00:00:00Z", "files": {}}))
    return root


def test_parent_folder_picks_matching_set(tmp_path):
    s = Settings(mode="replay", fixture_dir=_parent_with_two_sets(tmp_path))
    c = resolve_replay(s, snap_to_tile(*POINT)[0])
    r = resolve_replay(s, snap_to_tile(*ROANOKE)[0])
    nowhere = resolve_replay(s, snap_to_tile(38.0, -78.0)[0])
    assert c.fixture_dir.name == "christiansburg"
    assert r.fixture_dir.name == "roanoke"
    assert nowhere.fixture_dir is None


def test_recorded_sets_lists_each_town(tmp_path):
    s = Settings(mode="replay", fixture_dir=_parent_with_two_sets(tmp_path))
    labels = [x["label"] for x in recorded_sets(s)]
    assert labels == ["Downtown Christiansburg, VA", "Test Roanoke"]


def test_parent_folder_receipt_is_same_as_direct(tmp_path):
    s = Settings(mode="replay", fixture_dir=_parent_with_two_sets(tmp_path))
    a = build_receipt(*POINT, settings=s)
    b = build_receipt(*POINT, settings=Settings(mode="replay", fixture_dir=DEFAULT_FIXTURES))
    assert a["settle_score"] == b["settle_score"] is not None


def test_live_mode_is_untouched():
    s = Settings(mode="live", fixture_dir=None)
    assert resolve_replay(s, "x") is s


def test_record_writes_manifest_and_redacts_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(Fetcher, "_request", lambda self, *a, **k: "{}")
    out = tmp_path / "rec"
    s = Settings(mode="live", keys={"hud": "SECRET123", "eia": "SECRET456"})
    m = record_fixture_set(*POINT, "Test point", out, s)
    manifest = json.loads((out / "MANIFEST.json").read_text())
    assert manifest["point"]["label"] == "Test point" and manifest["files"]
    text = (out / "MANIFEST.json").read_text()
    assert "SECRET" not in text
    for f in manifest["files"]:
        assert (out / f).exists()
    assert resolve_replay(Settings(mode="replay", fixture_dir=tmp_path), snap_to_tile(*POINT)[0]).fixture_dir == out
    assert m["not_captured"]          # empty responses don't pretend to be data


def test_fetcher_redacts_query_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(Fetcher, "_request", lambda self, *a, **k: '{"ok": 1}')
    f = Fetcher(Settings(mode="record", fixture_dir=tmp_path))
    f.json("eia", "gas", "https://api.eia.gov/v2/x", params={"api_key": "SECRET", "frequency": "weekly"})
    assert f.recorded == {"eia__gas.json": "https://api.eia.gov/v2/x?api_key=REDACTED&frequency=weekly"}


def test_recorded_body_never_contains_a_key(tmp_path, monkeypatch):
    monkeypatch.setattr(Fetcher, "_request", lambda self, *a, **k: '{"request": {"api_key": "SECRETKEY9"}}')
    f = Fetcher(Settings(mode="record", fixture_dir=tmp_path, keys={"eia": "SECRETKEY9"}))
    f.json("eia", "gas", "https://api.eia.gov/v2/x")
    assert "SECRETKEY9" not in (tmp_path / "eia__gas.json").read_text()


def test_newest_set_wins_for_same_tile(tmp_path):
    root = _parent_with_two_sets(tmp_path)
    newer = root / "christiansburg_newer"
    newer.mkdir()
    (newer / "MANIFEST.json").write_text(json.dumps({
        "point": {"lat": POINT[0], "lon": POINT[1], "label": "Newer"}, "captured_at": "2026-11-01T00:00:00Z"}))
    s = resolve_replay(Settings(mode="replay", fixture_dir=root), snap_to_tile(*POINT)[0])
    assert s.fixture_dir.name == "christiansburg_newer"
