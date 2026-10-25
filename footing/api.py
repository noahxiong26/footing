"""HTTP API + the PWA. Run: `uvicorn footing.api:app --port 8080` (Cloud Run sets $PORT).

Every endpoint takes lat/lon but snaps them to a ~1 km tile before anything else; nothing is
logged or stored per user. Endpoints live under /api; the app itself is served at /.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, Body, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .factors import CATEGORIES, PARAMS, catalog_markdown
from . import ratings as ratings_store
from .fit import load_eligibility, load_policy
from . import va as va_geo
from .vafit import load_va
from .flyer import FlyerError, read_flyer
from .gemma import GemmaUnavailable
from .geo import snap_to_tile
from .pipeline import build_receipt, parse_profile, recorded_sets
from .planner import make_plan
from .sources import ALL_SOURCES
from .views import compare as compare_view
from .views import pocket_card_svg, tonight as tonight_view

WEB_DIR = Path(__file__).resolve().parent / "web"
_CACHE: dict[tuple, tuple[float, dict]] = {}
CACHE_TTL_S = 600
CACHE_MAX = 500

app = FastAPI(title="Footing", version="0.2.0",
              description="Settle Receipts from open public data. No accounts, no stored locations.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
router = APIRouter()


def _receipt(lat: float, lon: float, profile: str) -> dict:
    try:
        prof = parse_profile(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    tile, _, _ = snap_to_tile(lat, lon)
    settings = Settings.from_env()
    key = (tile, tuple(sorted(prof)), settings.mode, str(settings.fixture_dir))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_S:
        return hit[1]
    r = build_receipt(lat, lon, prof, settings)
    if len(_CACHE) >= CACHE_MAX:                        # bounded: drop the oldest entry
        _CACHE.pop(min(_CACHE, key=lambda k: _CACHE[k][0]))
    _CACHE[key] = (time.time(), r)
    return r


LAT = Query(..., ge=-90, le=90)
LON = Query(..., ge=-180, le=180)
PROFILE = Query("", description="comma list: car,kids,tonight,on_foot")


@router.get("/healthz")
def healthz() -> dict:
    settings = Settings.from_env()
    out: dict = {"ok": True, "mode": settings.mode}
    if settings.mode == "replay":
        sets = recorded_sets(settings)
        out["recorded"] = sets
        if sets:
            out.update(demo_label=", ".join(s["label"] for s in sets),
                       captured_at=", ".join(sorted({s["captured_at"] for s in sets})))
    return out


@router.get("/receipt")
def receipt(lat: float = LAT, lon: float = LON, profile: str = PROFILE) -> dict:
    return _receipt(lat, lon, profile)


@router.get("/compare")
def compare(points: str = Query(..., description="lat,lon;lat,lon (2 or 3 places)"),
            profile: str = PROFILE) -> dict:
    try:
        pts = [tuple(float(x) for x in p.split(",")) for p in points.split(";") if p.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="points must look like 37.13,-80.41;37.27,-79.94")
    if not 2 <= len(pts) <= 3 or any(len(p) != 2 for p in pts):
        raise HTTPException(status_code=400, detail="give 2 or 3 points as lat,lon;lat,lon")
    receipts = [_receipt(lat, lon, profile) for lat, lon in pts]
    return {"compare": compare_view(receipts), "receipts": receipts}


@router.get("/tonight")
def tonight(lat: float = LAT, lon: float = LON) -> dict:
    return tonight_view(_receipt(lat, lon, "tonight"))


@router.get("/plan")
def plan(lat: float = LAT, lon: float = LON, profile: str = PROFILE,
         lang: str = Query("English", max_length=30)) -> dict:
    r = _receipt(lat, lon, profile)
    return make_plan(r, r["profile"], language=lang, api_key=Settings.from_env().key("gemini"))


@router.get("/pocket-card.svg")
def pocket_card(request: Request, lat: float = LAT, lon: float = LON, profile: str = PROFILE) -> Response:
    r = _receipt(lat, lon, profile)
    clat, clon = r["tile"]["center"]
    link = str(request.base_url) + f"#/receipt?lat={clat}&lon={clon}&profile={profile}"
    return Response(pocket_card_svg(r, link), media_type="image/svg+xml")


@router.post("/flyer")
async def flyer(photo: UploadFile = File(...)) -> dict:
    data = await photo.read()
    try:
        return read_flyer(data, photo.content_type or "", api_key=Settings.from_env().key("gemini"))
    except FlyerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GemmaUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Flyer reading needs Gemma 4: {e}")


@router.get("/factors")
def factors() -> dict:
    return {"categories": [c.__dict__ for c in CATEGORIES],
            "parameters": [{k: v for k, v in p.__dict__.items() if not callable(v)} for p in PARAMS],
            "markdown": catalog_markdown()}


@router.get("/policy")
def policy() -> dict:
    """State policy facts + federal eligibility rules. The phone computes the Fit Score from these locally,
    so the person's status is never sent to this server."""
    return {"states": load_policy(), "eligibility": load_eligibility()}


@router.get("/va")
def va_data() -> dict:
    """Virginia's 133 cities and counties: rents, shelter counts, services, local rules, 287(g), crime, all sourced.
    The phone scores them itself (footing/web/vafit.js) so the person's status and household stay on the device."""
    return load_va()


@router.get("/va/check")
def va_check(lat: str = Query(...), lon: str = Query(...)) -> dict:
    """Is this point usable? Never guesses: returns ok=False with a plain reason for NaN, impossible numbers,
    points outside Virginia, and points on open water."""
    return va_geo.check_point(lat, lon)


def _client_network(request: Request) -> str | None:
    """The caller's address as the API sees it, for the per-network daily cap in footing/ratings.py.

    Behind a proxy (Cloud Run, any load balancer) request.client.host is the proxy, so every person would
    share one bucket and the cap would lock out a whole deployment. X-Forwarded-For's first entry is the
    original client. The address is never stored: ratings.py keeps only a salted hash of it.
    """
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else None)


@router.post("/ratings")
def add_rating(request: Request, body: dict = Body(...)) -> dict:

    try:
        return ratings_store.add(body, network=_client_network(request))
    except ratings_store.RatingError as e:
        # The per-network cap is rate limiting, not bad input, so it gets 429 and not 400.
        raise HTTPException(status_code=429 if "this network" in str(e) else 400, detail=str(e))


@router.get("/ratings/heat")
def ratings_heat() -> dict:
    return ratings_store.heat()


@router.get("/sources")
def sources() -> list[dict]:
    return [{"name": s.name, "license": s.license, "refresh": s.refresh, "needs_keys": list(s.needs),
             "homepage": s.homepage} for s in ALL_SOURCES]


app.include_router(router, prefix="/api")
app.include_router(router)          # unprefixed aliases kept for scripts and older tests
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
