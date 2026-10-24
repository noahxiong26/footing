"""Community ratings store, offline state lookup, and the globe's API + static files."""
import pytest
from fastapi.testclient import TestClient

from footing import ratings
from footing.api import app
from footing.us_states import state_at

NOW = 1_790_000_000_000
DEV = "device-token-0123456789"
CBURG = {"lat": 37.1299, "lon": -80.4089}


@pytest.fixture
def conn(tmp_path):
    c = ratings.connect(tmp_path / "r.sqlite")
    yield c
    c.close()


@pytest.mark.parametrize("pt,expected", [((37.1299, -80.4089), "VA"), ((38.9072, -77.0369), "DC"),
                                         ((39.0997, -94.5786), "MO"), ((39.1141, -94.6275), "KS"),
                                         ((21.3069, -157.8583), "HI"), ((61.2181, -149.9003), "AK"),
                                         ((51.5, -0.12), None)])
def test_state_at(pt, expected):
    assert state_at(*pt) == expected


def test_rating_is_snapped_and_filed_by_state(conn):
    out = ratings.add({**CBURG, "device": DEV, "overall": 4, "safe": 5, "tags": ["spanish_spoken"]}, conn, NOW)
    assert out["state"] == "VA" and out["center"] == [37.125, -80.405]
    row = conn.execute("SELECT lat, lon, device FROM ratings").fetchone()
    assert (row[0], row[1]) == (37.125, -80.405)                    # raw point is never stored
    assert DEV not in row[2]                                        # device token stored hashed only


def test_profile_data_is_rejected(conn):
    for bad in ({"status": "undocumented"}, {"immigration_status": "tps"}, {"note": "free text"}, {"name": "x"}):
        with pytest.raises(ratings.RatingError, match="never include profile data"):
            ratings.add({**CBURG, "device": DEV, "overall": 3, **bad}, conn, NOW)
    assert conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == 0


@pytest.mark.parametrize("body,msg", [
    ({"overall": 6}, "1 to 5"), ({"overall": 2.5}, "1 to 5"), ({"overall": True}, "1 to 5"), ({}, "required"),
    ({"overall": 3, "tags": ["ice_spotted"]}, "tags"), ({"overall": 3, "device": "short"}, "device"),
])
def test_validation(conn, body, msg):
    with pytest.raises(ratings.RatingError, match=msg):
        ratings.add({**CBURG, "device": DEV, **body}, conn, NOW)


def test_outside_us_rejected(conn):
    with pytest.raises(ratings.RatingError, match="50 states"):
        ratings.add({"lat": 51.5, "lon": -0.12, "device": DEV, "overall": 3}, conn, NOW)


def test_one_rating_per_place_per_day_and_daily_cap(conn):
    ratings.add({**CBURG, "device": DEV, "overall": 3}, conn, NOW)
    with pytest.raises(ratings.RatingError, match="already rated"):
        ratings.add({**CBURG, "device": DEV, "overall": 5}, conn, NOW + 3_600_000)
    ratings.add({**CBURG, "device": DEV, "overall": 5}, conn, NOW + 90_000_000)   # next day is fine
    for i in range(ratings.MAX_PER_DEVICE_PER_DAY - 1):
        ratings.add({"lat": 37.13 + 0.02 * (i + 1), "lon": -80.41, "device": DEV, "overall": 3}, conn, NOW + 90_000_000)
    with pytest.raises(ratings.RatingError, match="limit"):
        ratings.add({"lat": 36.9, "lon": -80.41, "device": DEV, "overall": 3}, conn, NOW + 90_000_000)


def test_heat_aggregates_with_bayesian_shrinkage(conn):
    for i in range(6):
        ratings.add({**CBURG, "device": f"{DEV}-{i}", "overall": 5, "safe": 4, "tags": ["pets_ok"]}, conn, NOW)
    ratings.add({"lat": 37.27, "lon": -79.94, "device": DEV, "overall": 1}, conn, NOW)
    h = ratings.heat(conn, NOW)
    assert h["total"] == 7 and h["states"]["VA"]["n"] == 7
    t = {x["tile"]: x for x in h["tiles"]}
    cburg = next(x for x in h["tiles"] if x["n"] == 6)
    roanoke = next(x for x in h["tiles"] if x["n"] == 1)
    assert 50 < cburg["score"] < 100 and 25 < roanoke["score"] < 50     # one 1-star rating moves it only a little
    assert cburg["dimensions"]["safe"] is not None and cburg["dimensions"]["respect"] is None
    assert cburg["tags"] == {"pets_ok": 6}
    assert len(t) == 2


def test_api_policy_ratings_and_static(tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTING_RATINGS_DB", str(tmp_path / "api.sqlite"))
    client = TestClient(app)
    p = client.get("/api/policy").json()
    assert len(p["states"]["states"]) == 51 and p["eligibility"]["programs"]
    assert client.get("/api/ratings/heat").json()["total"] == 0
    r = client.post("/api/ratings", json={**CBURG, "device": DEV, "overall": 4})
    assert r.status_code == 200 and r.json()["state"] == "VA"
    assert client.post("/api/ratings", json={**CBURG, "device": DEV, "overall": 4, "status": "daca"}).status_code == 400
    assert client.get("/api/ratings/heat").json()["states"]["VA"]["n"] == 1
    for path in ("/fit.js", "/globe.js", "/globe.css", "/i18n.js", "/vendor/maplibre-gl.js",
                 "/vendor/topojson-client.min.js", "/data/states-10m.json", "/data/countries-110m.json"):
        assert client.get(path).status_code == 200, path
