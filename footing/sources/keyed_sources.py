"""Sources that need a free API key (or, for Google, a billing account).

None of these could be exercised live from the build environment on 2026-10-24: the team had
no keys yet, and the sandbox cannot reach these hosts. Request/response shapes follow each
provider's public documentation; the parsers are unit-tested against synthetic responses in
tests/synthetic/. Run `footing receipt --mode record` once with keys to capture real fixtures.
"""
from __future__ import annotations

import base64

from ..models import Measure, SourceResult
from .base import Context, Source


class CensusACS(Source):
    """ACS 5-year: median gross rent by county (B25064_001E).

    Found live on 2026-10-24: api.census.gov now answers keyless requests with a "Missing Key"
    page, even though its help page still describes 500 keyless queries per day.
    """
    name = "census_acs"
    license = "U.S. Government work (public domain)"
    refresh = "annual"
    homepage = "https://www.census.gov/data/developers/data-sets/acs-5year.html"
    needs = ("census",)
    YEAR = 2023
    MISSING_SENTINELS = {-666666666, -999999999, -888888888, -222222222}

    def fetch(self, ctx: Context) -> SourceResult:
        if not ctx.county_fips:
            return SourceResult(self.name, "unknown", "county not resolved")
        params = {"get": "NAME,B25064_001E", "for": f"county:{ctx.county_fips[2:]}",
                  "in": f"state:{ctx.county_fips[:2]}"}
        if ctx.settings.key("census"):
            params["key"] = ctx.settings.key("census")
        rows = ctx.fetcher.json(self.name, f"rent_{ctx.county_fips}",
                                f"https://api.census.gov/data/{self.YEAR}/acs/acs5",
                                params=params, ttl_s=30 * 86400)
        header, row = rows[0], rows[1]
        rent = int(row[header.index("B25064_001E")])
        if rent in self.MISSING_SENTINELS or rent < 0:
            return SourceResult(self.name, "unknown", "ACS suppressed this estimate")
        res = SourceResult(self.name, "ok", measures={
            "median_gross_rent": Measure("median_gross_rent", rent, "USD/month", self.name,
                                         as_of=f"ACS {self.YEAR - 4}-{self.YEAR} 5-year")})
        res.provenance = self.provenance(ctx, as_of=f"ACS 5-year ending {self.YEAR}")
        return res


class BLSLaus(Source):
    """BLS Local Area Unemployment Statistics, county unemployment rate (monthly).

    Series id: LAUCN + 5-digit county FIPS + 0000000003. v2 needs a free key (500 queries/day);
    v1 works without one (25/day). Browser GETs were answered "website is busy" on 2026-10-24,
    so this adapter uses the documented POST form.
    """
    name = "bls_laus"
    license = "U.S. Government work (public domain)"
    refresh = "monthly"
    homepage = "https://www.bls.gov/lau/"

    def fetch(self, ctx: Context) -> SourceResult:
        if not ctx.county_fips:
            return SourceResult(self.name, "unknown", "county not resolved")
        sid = f"LAUCN{ctx.county_fips}0000000003"
        body: dict = {"seriesid": [sid]}
        version = "v1"
        if ctx.settings.key("bls"):
            body["registrationkey"] = ctx.settings.key("bls")
            version = "v2"
        data = ctx.fetcher.json(self.name, f"unemployment_{ctx.county_fips}",
                                f"https://api.bls.gov/publicAPI/{version}/timeseries/data/",
                                method="POST", json_body=body, ttl_s=7 * 86400)
        if data.get("status") != "REQUEST_SUCCEEDED":
            return SourceResult(self.name, "error", "; ".join(data.get("message", [])) or "BLS request failed")
        series = data["Results"]["series"][0]["data"]
        if not series:
            return SourceResult(self.name, "unknown", f"no data for {sid}")
        latest = series[0]
        value = float(latest["value"])
        as_of = f"{latest['periodName']} {latest['year']}"
        res = SourceResult(self.name, "ok", measures={
            "unemployment_rate": Measure("unemployment_rate", value, "%", self.name, as_of=as_of,
                                         note="not seasonally adjusted")})
        res.provenance = self.provenance(ctx, as_of=as_of, url=f"https://data.bls.gov/timeseries/{sid}")
        return res


def _find_key(obj, key):
    """Depth-first search for the first value stored under `key` (tolerant JSON parsing)."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_key(v, key)
            if found is not None:
                return found
    return None


class HudFMR(Source):
    """HUD Fair Market Rent, efficiency (studio) unit, by county. Needs a free HUD token."""
    name = "hud_fmr"
    license = "U.S. Government work (public domain)"
    refresh = "annual"
    homepage = "https://www.huduser.gov/portal/dataset/fmr-api.html"
    needs = ("hud",)

    def fetch(self, ctx: Context) -> SourceResult:
        if not ctx.county_fips:
            return SourceResult(self.name, "unknown", "county not resolved")
        entity = f"{ctx.county_fips}99999"
        data = ctx.fetcher.json(self.name, f"fmr_{ctx.county_fips}",
                                f"https://www.huduser.gov/hudapi/public/fmr/data/{entity}",
                                headers={"Authorization": f"Bearer {ctx.settings.key('hud') or ''}"},
                                ttl_s=30 * 86400)
        studio = _find_key(data, "Efficiency")
        year = _find_key(data, "year")
        if studio is None:
            return SourceResult(self.name, "unknown", "no Efficiency rent in HUD response")
        res = SourceResult(self.name, "ok", measures={
            "fmr_studio": Measure("fmr_studio", float(studio), "USD/month", self.name,
                                  as_of=f"FY{year}" if year else None)})
        res.provenance = self.provenance(ctx, as_of=f"FY{year}" if year else None)
        return res


# EIA weekly retail regular gasoline: a few states have their own series; the rest fall back to
# their PADD region. Codes follow EIA's duoarea facet; confirm once in the EIA API browser.
EIA_STATE_SERIES = {"CA": "SCA", "CO": "SCO", "FL": "SFL", "MA": "SMA", "MN": "SMN", "NY": "SNY",
                    "OH": "SOH", "TX": "STX", "WA": "SWA"}
EIA_PADD = {
    "R1X": "CT ME MA NH RI VT", "R1Y": "DE DC MD NJ NY PA", "R1Z": "FL GA NC SC VA WV",
    "R20": "IL IN IA KS KY MI MN MO NE ND SD OH OK TN WI", "R30": "AL AR LA MS NM TX",
    "R40": "CO ID MT UT WY", "R50": "AK AZ CA HI NV OR WA",
}


def eia_area_for_state(state: str | None) -> str:
    if state in EIA_STATE_SERIES:
        return EIA_STATE_SERIES[state]
    for code, states in EIA_PADD.items():
        if state and state in states.split():
            return code
    return "NUS"


class EIAGasoline(Source):
    name = "eia"
    license = "U.S. Government work (public domain)"
    refresh = "weekly"
    homepage = "https://www.eia.gov/opendata/"
    needs = ("eia",)

    def _latest(self, ctx: Context, area: str):
        d = ctx.fetcher.json(self.name, f"gas_{area}", "https://api.eia.gov/v2/petroleum/pri/gnd/data/",
                             params={"api_key": ctx.settings.key("eia") or "", "frequency": "weekly",
                                     "data[0]": "value", "facets[product][]": "EPMR",
                                     "facets[duoarea][]": area, "sort[0][column]": "period",
                                     "sort[0][direction]": "desc", "offset": 0, "length": 1},
                             ttl_s=86400)
        row = d["response"]["data"][0]
        return float(row["value"]), row["period"]

    def fetch(self, ctx: Context) -> SourceResult:
        area = eia_area_for_state(ctx.state_abbr)
        local, period = self._latest(ctx, area)
        national, _ = self._latest(ctx, "NUS")
        res = SourceResult(self.name, "ok", measures={
            "gas_regular": Measure("gas_regular", local, "USD/gal", self.name, as_of=f"week of {period}",
                                   note=f"EIA area {area}" + ("" if area.startswith("S") else " (regional average)")),
            "gas_regular_us": Measure("gas_regular_us", national, "USD/gal", self.name, as_of=f"week of {period}"),
        })
        res.provenance = self.provenance(ctx, as_of=f"week of {period}")
        return res


class GooglePlacesText(Source):
    """Places API (New) Text Search, Pro field mask only (no Enterprise fields -> cheaper SKU).

    Fills the gap OSM leaves for shelters, pantries and day centers. 5,000 free Text Search Pro
    calls per month; this source makes 4 calls per fresh tile.
    """
    name = "google_places"
    license = "Google Maps Platform Terms (display with attribution; limited caching)"
    refresh = "live"
    homepage = "https://developers.google.com/maps/documentation/places/web-service/text-search"
    needs = ("google_maps",)
    QUERIES = {"shelter": "homeless shelter", "food_bank": "food pantry",
               "soup_kitchen": "free meals soup kitchen", "day_center": "homeless day center"}
    FIELD_MASK = "places.id,places.displayName,places.location,places.formattedAddress,places.types"

    def fetch(self, ctx: Context) -> SourceResult:
        places = []
        for kind, query in self.QUERIES.items():
            d = ctx.fetcher.json(self.name, f"text_{kind}", "https://places.googleapis.com/v1/places:searchText",
                                 method="POST",
                                 headers={"X-Goog-Api-Key": ctx.settings.key("google_maps") or "",
                                          "X-Goog-FieldMask": self.FIELD_MASK},
                                 json_body={"textQuery": query, "pageSize": 10, "locationBias": {"circle": {
                                     "center": {"latitude": ctx.lat, "longitude": ctx.lon},
                                     "radius": float(min(ctx.radius_m, 50000))}}},
                                 ttl_s=86400)
            for p in d.get("places", []):
                loc = p.get("location", {})
                places.append(self.place(ctx, id=f"gplace:{p['id']}",
                                         name=p.get("displayName", {}).get("text", ""), kind=kind,
                                         lat=loc["latitude"], lon=loc["longitude"], source=self.name,
                                         tags={"address": p.get("formattedAddress"),
                                               "match": "text search (less precise than a category)"}))
        return SourceResult(self.name, "ok", places=places)


class Transitland(Source):
    name = "transitland"
    license = "Per-feed GTFS licenses; Transitland API terms"
    refresh = "live"
    homepage = "https://www.transit.land/documentation/rest-api/"
    needs = ("transitland",)

    def fetch(self, ctx: Context) -> SourceResult:
        d = ctx.fetcher.json(self.name, "stops", "https://transit.land/api/v2/rest/stops",
                             params={"lat": round(ctx.lat, 5), "lon": round(ctx.lon, 5), "radius": 1000,
                                     "limit": 100, "apikey": ctx.settings.key("transitland") or ""},
                             ttl_s=86400)
        places = []
        for s in d.get("stops", []):
            lon, lat = s["geometry"]["coordinates"][:2]
            places.append(self.place(ctx, id=f"tl:{s.get('onestop_id')}", name=s.get("stop_name", ""),
                                     kind="transit_stop", lat=lat, lon=lon, source=self.name,
                                     tags={"wheelchair_boarding": s.get("wheelchair_boarding")}))
        return SourceResult(self.name, "ok", places=places)


class KrogerBasket(Source):
    """Live shelf prices at the nearest Kroger-family store for the Footing survival basket."""
    name = "kroger"
    license = "Kroger Developer terms"
    refresh = "live"
    homepage = "https://developer.kroger.com/"
    needs = ("kroger_id", "kroger_secret")

    def fetch(self, ctx: Context) -> SourceResult:
        from ..staticdata import load_basket
        basket = load_basket()
        headers = {}
        if ctx.settings.mode != "replay":
            raw = f"{ctx.settings.key('kroger_id')}:{ctx.settings.key('kroger_secret')}".encode()
            tok = ctx.fetcher.json(self.name, "token", "https://api.kroger.com/v1/connect/oauth2/token",
                                   method="POST", headers={"Authorization": "Basic " + base64.b64encode(raw).decode()},
                                   form={"grant_type": "client_credentials", "scope": "product.compact"},
                                   ttl_s=1500)
            headers = {"Authorization": f"Bearer {tok['access_token']}"}
        locs = ctx.fetcher.json(self.name, "locations", "https://api.kroger.com/v1/locations",
                                params={"filter.lat.near": ctx.lat, "filter.lon.near": ctx.lon,
                                        "filter.radiusInMiles": 10, "filter.limit": 1},
                                headers=headers, ttl_s=7 * 86400)
        if not locs.get("data"):
            return SourceResult(self.name, "unknown", "no Kroger-family store within 10 miles")
        store = locs["data"][0]
        total, missing, lines = 0.0, [], []
        for item in basket["items"]:
            d = ctx.fetcher.json(self.name, f"product_{item['id']}", "https://api.kroger.com/v1/products",
                                 params={"filter.term": item["term"], "filter.locationId": store["locationId"],
                                         "filter.limit": 10}, headers=headers, ttl_s=86400)
            prices = []
            for prod in d.get("data", []):
                for it in prod.get("items", []):
                    price = it.get("price") or {}
                    p = price.get("promo") or price.get("regular")
                    if p:
                        prices.append(float(p))
            if not prices:
                missing.append(item["id"])
                continue
            cost = min(prices) * item["qty"]
            total += cost
            lines.append({"item": item["id"], "unit_price": min(prices), "qty": item["qty"]})
        if missing and len(missing) > len(basket["items"]) // 3:
            return SourceResult(self.name, "unknown", f"too many basket items not found: {missing}")
        res = SourceResult(self.name, "ok", measures={
            "basket_week": Measure("basket_week", round(total, 2), "USD/week", self.name,
                                   note=f"store {store.get('name')}; items not found: {missing or 'none'}"),
            "basket_lines": Measure("basket_lines", lines, "list", self.name),
        })
        return res
