"""Community ratings: people who have been somewhere say how it went. Feeds the globe heatmap.

Privacy by construction:
  * a rating is filed under the ~1 km tile (never the raw point) and the Virginia city or county it is in;
  * the heatmap only shows a tile once at least MIN_TILE_N ratings are in it (fewer stay inside the city/county total);
  * no names, no free text (fixed tags only, so there is nothing to moderate and nothing personal to leak);
  * no immigration status or any profile field is accepted - the request schema has no place for it;
  * the device token is hashed with a server salt and only used to stop repeat ratings; time is kept to the hour;
  * the network address is never stored, only a salted hash used for a generous per-network daily cap (many people
    share one library or shelter Wi-Fi, so the cap is high).

Bad input never becomes a guess: footing.va.check_point turns NaN, impossible numbers, points outside Virginia and
points on open water into a plain refusal with a reason.

Scoring: time-decayed Bayesian average (prior 3 of 5 with weight m = 5, half-life 90 days), reported 0-100.
With one or two ratings a tile stays near neutral; it takes several consistent ratings to move it.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from .fit import bayes_score
from .geo import snap_to_tile
from .va import check_point

DIMENSIONS = ("overall", "safe", "respect", "help")
TAGS = ("shelter_full", "shelter_had_beds", "police_moved_people", "welcoming_immigrants", "spanish_spoken",
        "pets_ok", "quiet_place_to_rest", "outlets_wifi", "clean_restrooms", "free_meals_nearby")
MAX_PER_DEVICE_PER_DAY = 20
MAX_PER_NETWORK_PER_DAY = 60
MIN_TILE_N = 3
_LOCK = threading.Lock()


class RatingError(ValueError):
    pass


def _db_path() -> Path:
    return Path(os.getenv("FOOTING_RATINGS_DB", ".cache/ratings.sqlite"))


def _salt(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT v FROM meta WHERE k='salt'").fetchone()
    if row:
        return row[0]
    s = secrets.token_hex(16)
    conn.execute("INSERT INTO meta VALUES ('salt', ?)", (s,))
    return s


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    conn.execute("""CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY, tile TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL, state TEXT NOT NULL,
        hour_ms INTEGER NOT NULL, device TEXT NOT NULL, overall INTEGER NOT NULL,
        safe INTEGER, respect INTEGER, help INTEGER, tags TEXT NOT NULL)""")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ratings)")}
    for col in ("fips", "network"):            # added in session 4; older databases get the columns
        if col not in cols:
            conn.execute(f"ALTER TABLE ratings ADD COLUMN {col} TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS ratings_tile ON ratings(tile)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ratings_once ON ratings(device, tile, hour_ms)")
    return conn


def _stars(v, name: str, required: bool) -> int | None:
    if v is None:
        if required:
            raise RatingError(f"{name} is required (1-5)")
        return None
    if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 5:
        raise RatingError(f"{name} must be a whole number from 1 to 5")
    return v


def add(body: dict, conn: sqlite3.Connection | None = None, now_ms: float | None = None, network: str | None = None) -> dict:
    """Validate and store one rating. Unknown keys are rejected so nothing personal can slip in.

    `network` is the caller's address as seen by the API (never from the request body); only its salted hash is kept."""
    allowed = {"lat", "lon", "device", "tags", *DIMENSIONS}
    extra = set(body) - allowed
    if extra:
        raise RatingError(f"unexpected fields: {sorted(extra)} (ratings never include profile data)")
    if body.get("lat") is None or body.get("lon") is None:
        raise RatingError("lat and lon are required")
    where = check_point(body["lat"], body["lon"])
    if not where["ok"]:
        raise RatingError(where["reason"])
    lat, lon = float(body["lat"]), float(body["lon"])
    device = str(body.get("device") or "")
    if not 16 <= len(device) <= 64:
        raise RatingError("device token must be 16-64 characters")
    tags = body.get("tags") or []
    if not isinstance(tags, list) or any(t not in TAGS for t in tags) or len(tags) > len(TAGS):
        raise RatingError(f"tags must be from {list(TAGS)}")
    stars = {d: _stars(body.get(d), d, d == "overall") for d in DIMENSIONS}
    tile, clat, clon = snap_to_tile(lat, lon)
    state, fips = "VA", where["fips"]
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    hour_ms = int(now_ms // 3_600_000 * 3_600_000)
    own = conn is None
    conn = conn or connect()
    try:
        with _LOCK:
            salt = _salt(conn)
            dev = hashlib.sha256((salt + device).encode()).hexdigest()[:32]
            net = hashlib.sha256((salt + "net:" + network).encode()).hexdigest()[:32] if network else None
            if net:
                n_net = conn.execute("SELECT COUNT(*) FROM ratings WHERE network=? AND hour_ms>=?",
                                     (net, hour_ms - 86_400_000)).fetchone()[0]
                if n_net >= MAX_PER_NETWORK_PER_DAY:
                    raise RatingError("too many ratings from this network today; try again tomorrow")
            day = conn.execute("SELECT COUNT(*) FROM ratings WHERE device=? AND hour_ms>=?",
                               (dev, hour_ms - 86_400_000)).fetchone()[0]
            if day >= MAX_PER_DEVICE_PER_DAY:
                raise RatingError("daily rating limit reached on this device")
            dup = conn.execute("SELECT 1 FROM ratings WHERE device=? AND tile=? AND hour_ms>=?",
                               (dev, tile, hour_ms - 86_400_000)).fetchone()
            if dup:
                raise RatingError("you already rated this place today")
            conn.execute("INSERT INTO ratings (tile, lat, lon, state, hour_ms, device, overall, safe, respect, help, tags, fips, network) "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (tile, clat, clon, state, hour_ms, dev, stars["overall"], stars["safe"], stars["respect"],
                          stars["help"], json.dumps(sorted(set(tags))), fips, net))
            conn.commit()
    finally:
        if own:
            conn.close()
    return {"ok": True, "tile": tile, "center": [clat, clon], "state": state, "fips": fips, "name": where["name"]}


def heat(conn: sqlite3.Connection | None = None, now_ms: float | None = None) -> dict:
    """Per-tile, per-locality and per-state scores. Dimensions are scored separately (null if never rated).
    Tiles with fewer than MIN_TILE_N ratings are left out of `tiles` (they still count in their locality)."""
    own = conn is None
    conn = conn or connect()
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    try:
        rows = conn.execute("SELECT tile, lat, lon, state, hour_ms, overall, safe, respect, help, tags, fips FROM ratings").fetchall()
    finally:
        if own:
            conn.close()
    by_tile: dict[str, list] = {}
    by_state: dict[str, list] = {}
    by_fips: dict[str, list] = {}
    for r in rows:
        by_tile.setdefault(r[0], []).append(r)
        by_state.setdefault(r[3], []).append(r)
        if r[10]:
            by_fips.setdefault(r[10], []).append(r)

    def summarize(rs: list) -> dict:
        out = bayes_score([{"t": r[4], "stars": r[5]} for r in rs], now_ms)
        dims = {}
        for i, d in enumerate(DIMENSIONS[1:], start=6):
            vals = [{"t": r[4], "stars": r[i]} for r in rs if r[i] is not None]
            dims[d] = bayes_score(vals, now_ms)["score"] if vals else None
        tags: dict[str, int] = {}
        for r in rs:
            for t in json.loads(r[9]):
                tags[t] = tags.get(t, 0) + 1
        out.update(dimensions=dims, tags=tags)
        return out

    tiles = [{"tile": t, "lat": rs[0][1], "lon": rs[0][2], "state": rs[0][3], **summarize(rs)}
             for t, rs in sorted(by_tile.items()) if len(rs) >= MIN_TILE_N]
    states = {s: summarize(rs) for s, rs in sorted(by_state.items())}
    localities = {f: summarize(rs) for f, rs in sorted(by_fips.items())}
    return {"tiles": tiles, "localities": localities, "states": states,
            "hidden_tiles": sum(1 for rs in by_tile.values() if len(rs) < MIN_TILE_N), "min_tile_n": MIN_TILE_N,
            "method": "time-decayed Bayesian average, prior 3/5 with m=5, half-life 90 days", "total": len(rows)}
