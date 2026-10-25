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
    with pytest.raises(ratings.RatingError, match="Virginia only"):
        ratings.add({"lat": 51.5, "lon": -0.12, "device": DEV, "overall": 3}, conn, NOW)


def test_one_rating_per_place_per_day_and_daily_cap(conn):
    ratings.add({**CBURG, "device": DEV, "overall": 3}, conn, NOW)
    with pytest.raises(ratings.RatingError, match="already rated"):
        ratings.add({**CBURG, "device": DEV, "overall": 5}, conn, NOW + 3_600_000)
    ratings.add({**CBURG, "device": DEV, "overall": 5}, conn, NOW + 90_000_000)   # next day is fine
    for i in range(ratings.MAX_PER_DEVICE_PER_DAY - 1):
        ratings.add({"lat": 37.13 + 0.02 * (i + 1), "lon": -79.6, "device": DEV, "overall": 3}, conn, NOW + 90_000_000)
    with pytest.raises(ratings.RatingError, match="limit"):
        ratings.add({"lat": 36.9, "lon": -79.6, "device": DEV, "overall": 3}, conn, NOW + 90_000_000)


def test_heat_aggregates_with_bayesian_shrinkage(conn):
    for i in range(6):
        ratings.add({**CBURG, "device": f"{DEV}-{i}", "overall": 5, "safe": 4, "tags": ["pets_ok"]}, conn, NOW)
    ratings.add({"lat": 37.27, "lon": -79.94, "device": DEV, "overall": 1}, conn, NOW)
    h = ratings.heat(conn, NOW)
    assert h["total"] == 7 and h["states"]["VA"]["n"] == 7
    cburg = next(x for x in h["tiles"] if x["n"] == 6)
    assert 50 < cburg["score"] < 100
    assert cburg["dimensions"]["safe"] is not None and cburg["dimensions"]["respect"] is None
    assert cburg["tags"] == {"pets_ok": 6}
    assert len(h["tiles"]) == 1 and h["hidden_tiles"] == 1          # a single rating never shows as its own tile
    roanoke = h["localities"]["51770"]                                 # ...but it counts for Roanoke city
    assert roanoke["n"] == 1 and 25 < roanoke["score"] < 50           # one 1-star rating moves it only a little
    assert h["localities"]["51121"]["n"] == 6                          # Montgomery County


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


@pytest.mark.parametrize("lat,lon,msg", [
    ("nan", -80.4, "not a real number"), (float("inf"), -80.4, "not a real number"), (37.1, "x", "pair of numbers"),
    (137.1, -80.4, "Latitude must be"), (38.9072, -77.0369, "Virginia only"), (37.30, -76.10, "open water"),
])
def test_bad_coordinates_are_refused_with_a_reason(conn, lat, lon, msg):
    with pytest.raises(ratings.RatingError, match=msg):
        ratings.add({"lat": lat, "lon": lon, "device": DEV, "overall": 3}, conn, NOW)
    assert conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == 0


def test_network_cap_uses_a_hash_never_the_address(conn, monkeypatch):
    monkeypatch.setattr(ratings, "MAX_PER_NETWORK_PER_DAY", 3)
    for i in range(3):
        ratings.add({"lat": 37.13 + 0.02 * i, "lon": -80.41, "device": f"{DEV}-{i}", "overall": 3}, conn, NOW, network="203.0.113.7")
    with pytest.raises(ratings.RatingError, match="this network"):
        ratings.add({"lat": 37.3, "lon": -80.41, "device": f"{DEV}-x", "overall": 3}, conn, NOW, network="203.0.113.7")
    ratings.add({"lat": 37.3, "lon": -80.41, "device": f"{DEV}-y", "overall": 3}, conn, NOW, network="198.51.100.2")
    stored = [r[0] for r in conn.execute("SELECT network FROM ratings")]
    assert all(s and "203.0" not in s and len(s) == 32 for s in stored)


def test_api_va_data_and_point_check(tmp_path, monkeypatch):
    client = TestClient(app)
    d = client.get("/api/va").json()
    assert len(d["localities"]) == 133
    assert client.get("/api/va/check", params={"lat": 37.2296, "lon": -80.4139}).json()["fips"] == "51121"
    assert client.get("/api/va/check", params={"lat": "nan", "lon": "1"}).json()["code"] == "not_a_number"
    for path in ("/vafit.js", "/data/va-localities.json"):
        assert client.get(path).status_code == 200, path


def test_network_cap_is_a_429_and_reads_through_the_proxy(tmp_path, monkeypatch):
    """Session 3 capped by network in the API, session 4 in the store. Merged: the store keeps the count,
    the API still reads X-Forwarded-For (behind Cloud Run request.client.host is the proxy, so without this
    one bucket would cover every user) and still answers 429, which is the status for rate limiting."""
    monkeypatch.setenv("FOOTING_RATINGS_DB", str(tmp_path / "r.sqlite"))
    monkeypatch.setattr(ratings, "MAX_PER_NETWORK_PER_DAY", 3)
    client = TestClient(app)
    codes = []
    for i in range(5):            # a new device token every time, and a new spot, from one address
        body = {"lat": 37.10 + i * 0.03, "lon": -80.40, "device": f"minted-token-{i:08d}", "overall": 1}
        codes.append(client.post("/api/ratings", json=body, headers={"x-forwarded-for": "203.0.113.9"}).status_code)
    assert codes == [200, 200, 200, 429, 429]
    other = client.post("/api/ratings", json={**CBURG, "device": "another-person-token", "overall": 4},
                        headers={"x-forwarded-for": "198.51.100.7"})
    assert other.status_code == 200, other.text


def test_bad_input_is_still_400_not_429(tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTING_RATINGS_DB", str(tmp_path / "r.sqlite"))
    client = TestClient(app)
    r = client.post("/api/ratings", json={"lat": 38.9072, "lon": -77.0369, "device": DEV, "overall": 3},
                    headers={"x-forwarded-for": "203.0.113.11"})
    assert r.status_code == 400 and "Virginia only" in r.json()["detail"]
