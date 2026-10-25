"""Keyless public sources. Each was captured live on 2026-10-24 (see fixtures/MANIFEST.json)."""
from __future__ import annotations

from datetime import datetime, timezone

from ..geo import bbox
from ..models import Measure, SourceResult
from .base import Context, Source

STATE_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE",
    "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA",
    "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM",
    "36": "NY", "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}


class CensusGeocoder(Source):
    """Point -> county FIPS. Every county-level source depends on this step."""
    name = "census_geocoder"
    license = "U.S. Government work (public domain)"
    refresh = "annual"
    homepage = "https://geocoding.geo.census.gov/geocoder/"

    def fetch(self, ctx: Context) -> SourceResult:
        data = ctx.fetcher.json(
            self.name, "county",
            "https://geocoding.geo.census.gov/geocoder/geographies/coordinates",
            params={"x": ctx.lon, "y": ctx.lat, "benchmark": "Public_AR_Current",
                    "vintage": "Current_Current", "layers": "Counties", "format": "json"},
            ttl_s=30 * 86400,
        )
        counties = data["result"]["geographies"].get("Counties") or []
        if not counties:
            return SourceResult(self.name, "unknown", "point is not inside a U.S. county")
        c = counties[0]
        ctx.county_fips = c["GEOID"]
        ctx.state_fips = c["STATE"]
        ctx.county_name = c["NAME"]
        ctx.state_abbr = STATE_ABBR.get(c["STATE"])
        return SourceResult(self.name, "ok", measures={
            "county_fips": Measure("county_fips", c["GEOID"], "fips", self.name),
            "county_name": Measure("county_name", c["NAME"], "", self.name),
        })


class NWS(Source):
    """National Weather Service: active alerts for the point."""
    name = "nws"
    license = "U.S. Government work (public domain)"
    refresh = "live"
    homepage = "https://www.weather.gov/documentation/services-web-api"
    SEVERITY_RANK = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1, "Unknown": 0}

    def fetch(self, ctx: Context) -> SourceResult:
        point = f"{ctx.lat:.4f},{ctx.lon:.4f}"
        meta = ctx.fetcher.json(self.name, "points", f"https://api.weather.gov/points/{point}",
                                headers={"Accept": "application/geo+json"}, ttl_s=7 * 86400)
        alerts = ctx.fetcher.json(self.name, "alerts", "https://api.weather.gov/alerts/active",
                                  params={"point": point},
                                  headers={"Accept": "application/geo+json"}, ttl_s=600)
        rel = meta["properties"]["relativeLocation"]["properties"]
        items = []
        for f in alerts.get("features", []):
            p = f.get("properties", {})
            items.append({"event": p.get("event"), "severity": p.get("severity", "Unknown"),
                          "headline": p.get("headline"), "ends": p.get("ends") or p.get("expires")})
        worst = max((self.SEVERITY_RANK.get(a["severity"], 0) for a in items), default=-1)
        return SourceResult(self.name, "ok", measures={
            "alerts": Measure("alerts", items, "list", self.name, as_of=alerts.get("updated")),
            "worst_alert_rank": Measure("worst_alert_rank", worst, "rank -1..4", self.name,
                                        note="-1 means no active alerts"),
            "nws_city": Measure("nws_city", f"{rel.get('city')}, {rel.get('state')}", "", self.name),
            "time_zone": Measure("time_zone", meta["properties"].get("timeZone"), "IANA", self.name),
        })


class OpenMeteo(Source):
    """7-day overnight lows. Free API is non-commercial only, CC BY 4.0 attribution required."""
    name = "open_meteo"
    license = "CC BY 4.0 (free tier: non-commercial use only)"
    refresh = "live"
    homepage = "https://open-meteo.com/"

    def fetch(self, ctx: Context) -> SourceResult:
        d = ctx.fetcher.json(self.name, "forecast", "https://api.open-meteo.com/v1/forecast", params={
            "latitude": round(ctx.lat, 4), "longitude": round(ctx.lon, 4),
            "daily": "temperature_2m_min,temperature_2m_max", "temperature_unit": "fahrenheit",
            "timezone": "auto", "forecast_days": 7}, ttl_s=3 * 3600)
        lows = [t for t in d["daily"]["temperature_2m_min"] if t is not None]
        highs = [t for t in d["daily"]["temperature_2m_max"] if t is not None]
        return SourceResult(self.name, "ok", measures={
            "lows_f": Measure("lows_f", lows, "°F", self.name, as_of=d["daily"]["time"][0]),
            "freezing_nights_7d": Measure("freezing_nights_7d", sum(t <= 32 for t in lows), "nights", self.name),
            "cold_nights_7d": Measure("cold_nights_7d", sum(32 < t <= 40 for t in lows), "nights", self.name),
            "hot_days_7d": Measure("hot_days_7d", sum(t >= 95 for t in highs), "days", self.name),
        })


class SnapRetailers(Source):
    """USDA SNAP Retailer Locator (ArcGIS Feature Service). Refreshed about every 2 weeks."""
    name = "snap"
    license = "U.S. Government work (public domain)"
    refresh = "weekly"
    homepage = "https://www.fna.usda.gov/snap/retailer-locator"
    URL = ("https://services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/"
           "snap_retailer_location_data/FeatureServer/0")
    FULL_GROCERY = {"Super Store", "Supermarket", "Large Grocery Store", "Medium Grocery Store"}

    def fetch(self, ctx: Context) -> SourceResult:
        meta = ctx.fetcher.json(self.name, "layer_meta", self.URL, params={"f": "json"}, ttl_s=86400)
        ms = meta.get("editingInfo", {}).get("dataLastEditDate")
        as_of = (datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat() if ms else None)
        minx, miny, maxx, maxy = bbox(ctx.lat, ctx.lon, ctx.radius_m)
        features, offset = [], 0
        while True:
            key = "retailers" if offset == 0 else f"retailers_o{offset}"
            data = ctx.fetcher.json(self.name, key, self.URL + "/query", params={
                "where": "1=1", "geometry": f"{minx:.5f},{miny:.5f},{maxx:.5f},{maxy:.5f}",
                "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "true",
                "outSR": 4326, "resultOffset": offset, "resultRecordCount": 1000, "f": "json"},
                ttl_s=86400)
            if "error" in data:
                raise ValueError(data["error"].get("message"))
            features.extend(data.get("features", []))
            if not data.get("exceededTransferLimit") or ctx.settings.mode == "replay" or offset > 10000:
                break
            offset += len(data.get("features", [])) or 1000
        places = []
        for f in features:
            a = f["attributes"]
            store_type = a.get("Store_Type") or ""
            places.append(self.place(
                ctx, id=f"snap:{a['Record_ID']}", name=a.get("Store_Name", ""), kind="snap_retailer",
                lat=a["Latitude"], lon=a["Longitude"], source=self.name,
                tags={"store_type": store_type, "full_grocery": store_type in self.FULL_GROCERY,
                      "restaurant_meals": "restaurant" in store_type.lower(),
                      "incentive_program": a.get("Incentive_Program"),
                      "address": f"{a.get('Store_Street_Address')}, {a.get('City')}"}))
        res = SourceResult(self.name, "ok", places=places)
        res.provenance = self.provenance(ctx, as_of=as_of, url=self.homepage)
        return res


OSM_QUERY = """[out:json][timeout:25];
(
  nwr["amenity"="social_facility"](around:{r},{lat},{lon});
  nwr["amenity"~"^(toilets|shower|drinking_water|library|pharmacy|post_office|food_bank|clinic|community_centre)$"](around:{r},{lat},{lon});
  nwr["shop"="laundry"](around:{r},{lat},{lon});
  nwr["office"="employment_agency"](around:{r},{lat},{lon});
);
out center tags;"""

SHELTER_FOR_OK = {"", "homeless", "underprivileged", "displaced", "unemployed"}


def classify_osm(tags: dict) -> str | None:
    """Map OSM tags to Footing kinds. Returns None for things that are not help for this user
    (senior housing, nursing homes, private couriers tagged as post offices...)."""
    amenity = tags.get("amenity")
    if amenity == "social_facility":
        sf = tags.get("social_facility", "")
        sf_for = tags.get("social_facility:for", "")
        if sf == "shelter" and sf_for in SHELTER_FOR_OK:
            return "shelter"
        if sf in ("food_bank", "soup_kitchen", "clothing_bank"):
            return sf
        if sf == "outreach" and sf_for in ("homeless", "underprivileged"):
            return "day_center"
        return None
    if amenity == "post_office":
        op = (tags.get("operator", "") + " " + tags.get("name", "")).lower()
        return "post_office" if ("postal service" in op or "post office" in op) else None
    if amenity in ("food_bank",):
        return "food_bank"
    if amenity in ("toilets", "shower", "drinking_water", "library", "pharmacy", "clinic",
                   "community_centre"):
        return amenity
    if tags.get("shop") == "laundry":
        return "laundry"
    if tags.get("office") == "employment_agency":
        return "employment_agency"
    return None


class OSMOverpass(Source):
    """OpenStreetMap via Overpass. Cache hard: the public server asks for <10k queries/day."""
    name = "osm"
    license = "ODbL 1.0 (© OpenStreetMap contributors)"
    refresh = "daily"
    homepage = "https://wiki.openstreetmap.org/wiki/Overpass_API"

    def fetch(self, ctx: Context) -> SourceResult:
        q = OSM_QUERY.format(r=ctx.radius_m, lat=round(ctx.lat, 4), lon=round(ctx.lon, 4))
        data = ctx.fetcher.json(self.name, "amenities", "https://overpass-api.de/api/interpreter",
                                method="POST", form={"data": q}, ttl_s=86400)
        places, skipped = [], 0
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            kind = classify_osm(tags)
            if kind is None:
                skipped += 1
                continue
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat is None or lon is None:
                continue
            keep = {k: tags[k] for k in ("opening_hours", "phone", "website", "fee", "access",
                                          "internet_access", "wheelchair", "note") if k in tags}
            places.append(self.place(ctx, id=f"osm:{el['type']}/{el['id']}", name=tags.get("name", ""),
                                     kind=kind, lat=lat, lon=lon, source=self.name, tags=keep))
        res = SourceResult(self.name, "ok", places=places,
                           reason=f"{skipped} OSM features ignored (not relevant to this user)")
        res.provenance = self.provenance(ctx, as_of=data.get("osm3s", {}).get("timestamp_osm_base"),
                                         url="https://www.openstreetmap.org/copyright")
        return res


class UrbanSchools(Source):
    """NCES Common Core of Data via the Urban Institute Education Data API.

    Found live on 2026-10-24: the `county_code` filter is ignored by the API, so we query the
    whole state (fips=) and filter locally. Cache it for a week.
    """
    name = "urban_ed"
    license = "Urban Institute Education Data Portal terms; NCES data public domain"
    refresh = "annual"
    homepage = "https://educationdata.urban.org/documentation/"
    YEAR = 2022
    LEVELS = {1: "primary", 2: "middle", 3: "high", 4: "other"}

    def fetch(self, ctx: Context) -> SourceResult:
        if not ctx.state_fips:
            return SourceResult(self.name, "unknown", "county not resolved")
        data = ctx.fetcher.json(
            self.name, f"schools_{ctx.state_fips}",
            f"https://educationdata.urban.org/api/v1/schools/ccd/directory/{self.YEAR}/",
            params={"fips": int(ctx.state_fips)}, ttl_s=7 * 86400)
        rows = list(data.get("results", []))
        page = 1
        while data.get("next") and ctx.settings.mode != "replay" and page < 30:
            page += 1
            data = ctx.fetcher.json(self.name, f"schools_{ctx.state_fips}_p{page}", data["next"],
                                    ttl_s=7 * 86400)
            rows.extend(data.get("results", []))
        places = []
        for s in rows:
            if s.get("county_code") != ctx.county_fips or s.get("school_status") != 1:
                continue
            if s.get("school_level") not in self.LEVELS or s.get("latitude") is None:
                continue
            places.append(self.place(ctx, id=f"nces:{s['ncessch']}", name=s.get("school_name", ""),
                                     kind="school", lat=s["latitude"], lon=s["longitude"],
                                     source=self.name,
                                     tags={"level": self.LEVELS[s["school_level"]],
                                           "district": s.get("lea_name"), "phone": s.get("phone")}))
        res = SourceResult(self.name, "ok", places=places)
        res.provenance = self.provenance(ctx, as_of=f"school year {self.YEAR}-{self.YEAR + 1}")
        return res
