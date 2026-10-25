"""Real town captures: offline replay isolation and honest coverage/provenance."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from footing.config import Settings
from footing.geo import snap_to_tile
from footing.http import Fetcher, content_sha256
from footing.pipeline import build_receipt, recorded_sets, resolve_replay
from footing.sources import ALL_SOURCES

ROOT = Path(__file__).resolve().parents[1] / "fixtures"
TOWNS = {
    "roanoke": (37.2710, -79.9414, "51770"),
    "richmond": (37.5407, -77.4360, "51760"),
    "blacksburg": (37.2296, -80.4139, "51121"),
    "harrisonburg": (38.4496, -78.8689, "51660"),
    "alexandria": (38.8048, -77.0469, "51510"),
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("replay attempted a publisher request")
    monkeypatch.setattr(Fetcher, "_request", forbidden)


@pytest.mark.parametrize("town", TOWNS)
def test_real_town_replays_only_its_own_tile(town):
    lat, lon, fips = TOWNS[town]
    folder = ROOT / f"{town}_2026-10-25"
    direct = Settings(mode="replay", fixture_dir=folder)
    parent = Settings(mode="replay", fixture_dir=ROOT)
    tile = snap_to_tile(lat, lon)[0]
    assert resolve_replay(parent, tile).fixture_dir == folder
    receipt = build_receipt(lat, lon, settings=parent)
    assert receipt["tile"]["id"] == tile
    assert receipt["area"]["county_fips"] == fips
    assert receipt["place_counts"] == build_receipt(lat, lon, settings=direct)["place_counts"]
    assert folder.name in {s["set"] for s in recorded_sets(parent)}
    for other, (olat, olon, _) in TOWNS.items():
        if other == town:
            continue
        assert resolve_replay(direct, snap_to_tile(olat, olon)[0]).fixture_dir is None
        uncovered = build_receipt(olat, olon, settings=direct)
        assert uncovered["area"]["county_fips"] is None
        assert uncovered["place_counts"] == {}
        assert all(s["status"] != "ok" for s in uncovered["sources"] if s["source"] != "static_tables")
    assert resolve_replay(direct, snap_to_tile(lat + .02, lon)[0]).fixture_dir is None


@pytest.mark.parametrize("town", TOWNS)
def test_capture_manifest_and_receipt_match_actual_coverage(town):
    folder = ROOT / f"{town}_2026-10-25"
    manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["tile"] == snap_to_tile(*TOWNS[town][:2])[0]
    outcomes = manifest["source_outcomes"]
    assert set(outcomes) == {s.name for s in ALL_SOURCES}
    assert manifest["not_captured"] == {k: v["reason"] for k, v in outcomes.items() if v["status"] != "ok"}
    actual_files = {p.name for p in folder.glob("*__*.json")}
    assert actual_files == set(manifest["files"])
    requests = [json.loads(line) for line in (folder / "REQUESTS.jsonl").read_text(encoding="utf-8").splitlines()]
    for filename, metadata in manifest["files"].items():
        body = (folder / filename).read_bytes()
        assert content_sha256(body) == metadata["sha256"]
        # The Windows capture first hashed the CRLF checkout; keep that link to the original receipt.
        assert hashlib.sha256(body.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest() == metadata["sha256_windows_crlf"]
        assert json.loads(body)  # Reject empty bodies / JSON null / empty HTML.
        assert metadata["live"] and metadata["trimmed"] is False
        started = datetime.fromisoformat(metadata["started_at"])
        ended = datetime.fromisoformat(metadata["finished_at"])
        assert started.tzinfo and started <= ended
        assert any(r.get("file") == filename and r.get("outcome") == "captured_json" for r in requests)
    receipt = build_receipt(*TOWNS[town][:2], settings=Settings(mode="replay", fixture_dir=folder))
    for source in receipt["sources"]:
        captured = outcomes[source["source"]]
        if captured["status"] == "ok":
            assert source["status"] == "ok"
            assert source["place_count"] == captured["place_count"]
            assert source["measures"] == captured["measures"]
        else:
            assert source["status"] != "ok"
            assert source["reason"]
            assert not source["measures"] and source["place_count"] == 0
    for unknown in receipt["unknowns"]:
        assert unknown["reason"]
    assert all(m["value"] is None for m in receipt["money"] if m["state"] == "unknown")


def test_receipt_hash_ignores_checkout_line_endings():
    lf = b'{\n "a": 1\n}'
    assert content_sha256(lf) == content_sha256(lf.replace(b"\n", b"\r\n")) == hashlib.sha256(lf).hexdigest()
    assert content_sha256(lf) != content_sha256(b'{\n "a": 2\n}')


def test_fixtures_are_pinned_to_lf_in_git():
    attributes = (ROOT.parent / ".gitattributes").read_text(encoding="utf-8")
    assert "fixtures/** text eol=lf" in attributes
