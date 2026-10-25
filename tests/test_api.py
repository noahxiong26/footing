from fastapi.testclient import TestClient

from footing.api import app

client = TestClient(app)


def test_health():
    assert client.get("/healthz").json()["ok"] is True


def test_receipt_endpoint_snaps_location(monkeypatch):
    monkeypatch.setenv("FOOTING_MODE", "replay")
    r = client.get("/receipt", params={"lat": 37.1299, "lon": -80.4089, "profile": "kids"})
    assert r.status_code == 200
    body = r.json()
    assert body["tile"]["center"] == [37.125, -80.405]
    assert "37.1299" not in r.text and "-80.4089" not in r.text   # raw point never echoed


def test_bad_profile_is_400(monkeypatch):
    monkeypatch.setenv("FOOTING_MODE", "replay")
    r = client.get("/receipt", params={"lat": 37.13, "lon": -80.41, "profile": "jetpack"})
    assert r.status_code == 400


def test_factors_and_sources():
    f = client.get("/factors").json()
    assert len(f["categories"]) == 10 and f["parameters"]
    assert any(s["name"] == "osm" for s in client.get("/sources").json())
