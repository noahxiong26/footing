from fastapi.testclient import TestClient

from footing.api import app

client = TestClient(app)
P = {"lat": 37.1299, "lon": -80.4089}


def test_app_shell_served():
    r = client.get("/")
    assert r.status_code == 200 and "Footing" in r.text
    assert client.get("/app.js").status_code == 200
    assert client.get("/manifest.webmanifest").status_code == 200


def test_healthz_reports_demo(monkeypatch):
    monkeypatch.setenv("FOOTING_MODE", "replay")
    h = client.get("/api/healthz").json()
    assert h["mode"] == "replay"
    # One date per recorded set, deduplicated: Christiansburg 10-24, five towns 10-25.
    dates = sorted({s["captured_at"] for s in h["recorded"]})
    assert h["captured_at"] == ", ".join(dates) == "2026-10-24, 2026-10-25"
    assert len(h["recorded"]) == 6


def test_plan_tonight_card_compare(monkeypatch):
    monkeypatch.setenv("FOOTING_MODE", "replay")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    plan = client.get("/api/plan", params={**P, "profile": "kids"}).json()
    assert plan["engine"] == "rule-based" and plan["plan"]["day1"]
    t = client.get("/api/tonight", params=P).json()
    assert "211" in t["fallback"]
    card = client.get("/api/pocket-card.svg", params=P)
    assert card.headers["content-type"].startswith("image/svg+xml")
    # Christiansburg and Roanoke are both recorded; Danville (36.586,-79.395) is not.
    c = client.get("/api/compare", params={"points": "37.1299,-80.4089;37.2710,-79.9414;36.5860,-79.3950"}).json()
    scores = c["compare"]["settle_scores"]
    assert isinstance(scores[0], (int, float)) and isinstance(scores[1], (int, float))
    assert scores[2] is None                                 # not recorded -> no score, never a guess
    assert client.get("/api/compare", params={"points": "37.1"}).status_code == 400


def test_flyer_without_key_is_503(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = client.post("/api/flyer", files={"photo": ("f.jpg", b"\xff\xd8x", "image/jpeg")})
    assert r.status_code == 503 and "Gemma 4" in r.json()["detail"]
    r = client.post("/api/flyer", files={"photo": ("f.pdf", b"%PDF", "application/pdf")})
    assert r.status_code in (400, 503)
