"""The factor catalog: every parameter that feeds the Settle Score, in one table.

Each parameter says where its value comes from, how the raw value becomes 0-100, and how
fresh the data is. `python -m footing factors --markdown` prints this table for the docs, so
the doc and the code cannot drift apart.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable

from .models import Measure, Place, SourceResult

FRESHNESS = {"live": 1.0, "daily": 0.9, "weekly": 0.8, "monthly": 0.6, "annual": 0.4, "static": 0.5}


@dataclass
class Category:
    id: str
    label: str
    weight: float
    blurb: str


CATEGORIES = [
    Category("shelter", "Shelter and safe sleep", 18, "Somewhere to sleep, now and as a 30-day plan"),
    Category("food", "Food and EBT", 16, "Where SNAP works, free meals, real grocery stores"),
    Category("cost", "Cost to stay", 14, "Dollars: food basket, gas, next-step rent at local wages"),
    Category("income", "Income and work", 10, "Can a person earn their way out from here"),
    Category("mobility", "Getting around", 12, "Transit and walking time to everyday needs"),
    Category("health", "Health", 8, "Clinics that see people without insurance, pharmacies"),
    Category("hygiene", "Hygiene and connection", 8, "Restrooms, water, showers, laundry, libraries"),
    Category("kids", "Kids and school", 4, "Schools nearby; weight rises with 'Kids with me'"),
    Category("weather", "Weather risk", 6, "Live alerts and overnight lows for people outside"),
    Category("legal", "Paperwork and local rules", 4, "A mailing address, and rules that decide if you can stay"),
]
CATEGORY_BY_ID = {c.id: c for c in CATEGORIES}


# ---- normalizers ------------------------------------------------------------
def count_score(n: float, k: float) -> float:
    """Saturating: 0 places -> 0, k places -> 63, 3k places -> 95."""
    return 100.0 * (1.0 - math.exp(-n / k))


def linear_score(v: float, good: float, bad: float) -> float:
    """100 at `good`, 0 at `bad`, straight line between, clamped. Works in either direction."""
    if good == bad:
        return 100.0 if v == good else 0.0
    t = (v - bad) / (good - bad)
    return max(0.0, min(100.0, 100.0 * t))


# ---- the bundle a parameter reads from -------------------------------------
@dataclass
class Bundle:
    places: list[Place]
    measures: dict[str, Measure]
    sources: dict[str, SourceResult]

    def ok(self, *names: str) -> bool:
        return any(self.sources.get(n) and self.sources[n].status == "ok" for n in names)

    def within(self, kinds: set[str], radius_m: float, pred: Callable[[Place], bool] | None = None) -> list[Place]:
        return [p for p in self.places if p.kind in kinds and (p.distance_m or 0) <= radius_m
                and (pred is None or pred(p))]

    def m(self, key: str) -> Any:
        meas = self.measures.get(key)
        return meas.value if meas else None


class Unknown(Exception):
    """Raised by an extractor when the value cannot be known honestly."""


@dataclass
class Param:
    id: str
    category: str
    label: str
    weight: float
    unit: str
    sources: tuple[str, ...]
    refresh: str
    extract: Callable[[Bundle], float]
    score: Callable[[float], float]
    rule: str                                # human-readable scoring rule, shown in docs
    status: str = "built"                    # built | planned
    profile_boost: dict[str, float] = field(default_factory=dict)


SOURCE_NAMES = {"google_places": "Google Places", "osm": "OpenStreetMap", "snap": "USDA SNAP",
                "transitland": "Transitland", "hrsa": "HRSA", "urban_ed": "NCES schools"}


def _count(kinds: set[str], radius: float, *, zero_needs: tuple[str, ...] = (), sources=(),
           pred: Callable[[Place], bool] | None = None, zero_reason: str | None = None) -> Callable[[Bundle], float]:
    """Count places of `kinds` within `radius`. A zero is only trusted when one of `zero_needs`
    answered (e.g. OSM rarely maps shelters, so 0 from OSM alone is Unknown, not 0)."""
    def f(b: Bundle) -> float:
        if sources and not b.ok(*sources):
            raise Unknown(f"no data source answered ({', '.join(SOURCE_NAMES.get(x, x) for x in sources)})")
        n = len(b.within(kinds, radius, pred))
        if n == 0 and zero_needs and not b.ok(*zero_needs):
            raise Unknown(zero_reason or "none found, but OpenStreetMap often misses these; a zero needs "
                          f"{' or '.join(SOURCE_NAMES.get(x, x) for x in zero_needs)} to confirm it (or call 211)")
        return float(n)
    return f


def _measure(key: str) -> Callable[[Bundle], float]:
    def f(b: Bundle) -> float:
        v = b.m(key)
        if v is None:
            raise Unknown(f"{key} not available")
        return float(v)
    return f


def _ratio(num: str, den: str, den_scale: float = 1.0) -> Callable[[Bundle], float]:
    def f(b: Bundle) -> float:
        a, d = b.m(num), b.m(den)
        missing = [k for k, v in ((num, a), (den, d)) if v is None]
        if missing or d == 0:
            raise Unknown(f"missing {' and '.join(missing) or den + ' (zero)'}")
        return round(float(a) / (float(d) * den_scale), 3)
    return f


HOURS_PER_MONTH = 173.33  # 40 h/week * 52 / 12


def _rent_burden(rent_key: str) -> Callable[[Bundle], float]:
    def f(b: Bundle) -> float:
        rent, wage = b.m(rent_key), b.m("min_wage")
        missing = [n for n, v in ((rent_key, rent), ("min_wage (verified state rate)", wage)) if v is None]
        if missing:
            raise Unknown(f"missing {' and '.join(missing)}")
        return round(float(rent) / (float(wage) * HOURS_PER_MONTH), 3)
    return f


ESSENTIAL_KINDS = [{"snap_retailer"}, {"pharmacy"}, {"library"}, {"clinic", "health_center"}, {"post_office"}]


def _essentials_walk(b: Bundle) -> float:
    nearest = []
    for kinds in ESSENTIAL_KINDS:
        cands = [p.walk_min for p in b.places if p.kind in kinds and p.walk_min is not None]
        if cands:
            nearest.append(min(cands))
    if len(nearest) < 3:
        raise Unknown("fewer than 3 of the 5 everyday needs located")
    return round(statistics.median(nearest), 1)


def _alert_rank(b: Bundle) -> float:
    v = b.m("worst_alert_rank")
    if v is None:
        raise Unknown("NWS did not answer")
    return float(v)


ALERT_SCORE = {-1: 100.0, 0: 75.0, 1: 75.0, 2: 50.0, 3: 15.0, 4: 0.0}


def _cold_load(b: Bundle) -> float:
    fz, cold = b.m("freezing_nights_7d"), b.m("cold_nights_7d")
    if fz is None:
        raise Unknown("no overnight forecast")
    return float(fz) + 0.35 * float(cold or 0)


def _school_levels(b: Bundle) -> float:
    if not b.ok("urban_ed"):
        raise Unknown("school directory not available")
    return float(len({p.tags.get("level") for p in b.within({"school"}, 5000)} & {"primary", "middle", "high"}))


def _local_rules(b: Bundle) -> float:
    rules = b.m("local_rules")
    if not rules:
        raise Unknown("no curated local rules for this county yet")
    return 20.0 if rules.get("camping_ban") else 80.0


def _planned(why: str) -> Callable[[Bundle], float]:
    def f(b: Bundle) -> float:
        raise Unknown(f"planned: {why}")
    return f


SHELTER_SRC = ("osm", "google_places")
P = Param
PARAMS: list[Param] = [
    # shelter
    P("shelters_3km", "shelter", "Shelters within 3 km", 3, "count", SHELTER_SRC, "daily",
      _count({"shelter"}, 3000, zero_needs=("google_places",), sources=SHELTER_SRC),
      lambda n: count_score(n, 1.0), "count, k=1 (1 shelter -> 63, 3 -> 95); zero trusted only if Google Places answered",
      profile_boost={"tonight": 2.0}),
    P("day_centers_5km", "shelter", "Day centers within 5 km", 1, "count", SHELTER_SRC, "daily",
      _count({"day_center"}, 5000, zero_needs=("google_places",), sources=SHELTER_SRC),
      lambda n: count_score(n, 1.0), "count, k=1; zero trusted only if Google Places answered"),
    P("bed_pressure", "shelter", "Shelter beds per unsheltered person (CoC)", 2, "ratio", ("static_tables",), "annual",
      _measure("beds_per_unsheltered"), lambda r: linear_score(r, 1.0, 0.2),
      "HUD HIC beds / PIT unsheltered for the county's CoC: 1.0+ -> 100, 0.2 -> 0"),
    # food
    P("snap_stores_1km", "food", "SNAP stores within 1 km", 2, "count", ("snap",), "weekly",
      _count({"snap_retailer"}, 1000, sources=("snap",)), lambda n: count_score(n, 2.0),
      "count, k=2 (USDA list is complete, so zero is real)"),
    P("full_grocery_2km", "food", "Full grocery stores taking SNAP within 2 km", 2, "count", ("snap",), "weekly",
      _count({"snap_retailer"}, 2000, sources=("snap",), pred=lambda p: p.tags.get("full_grocery")),
      lambda n: count_score(n, 1.0), "count of Super Store/Supermarket/Large or Medium Grocery, k=1"),
    P("free_food_3km", "food", "Food banks and meal sites within 3 km", 2, "count", ("osm", "google_places"), "daily",
      _count({"food_bank", "soup_kitchen"}, 3000, zero_needs=("google_places",), sources=("osm", "google_places")),
      lambda n: count_score(n, 1.5), "count, k=1.5; zero trusted only if Google Places answered"),
    P("restaurant_meals_3km", "food", "Restaurant Meals Program places within 3 km", 0.5, "count", ("snap",), "weekly",
      _count({"snap_retailer"}, 3000, zero_needs=("_bonus_only",), sources=("snap",),
             zero_reason="none found; Restaurant Meals is a bonus, so a zero is not held against the town",
             pred=lambda p: p.tags.get("restaurant_meals")),
      lambda n: count_score(n, 1.0),
      "bonus only: counts when present, k=1; a zero is Unknown because only some states run the program"),
    # cost
    P("basket_vs_tfp", "cost", "Local survival basket vs USDA Thrifty Food Plan", 3, "ratio", ("kroger", "static_tables"), "live",
      _ratio("basket_week", "tfp_week"), lambda r: linear_score(r, 0.85, 1.3),
      "basket/TFP week: 0.85 or less -> 100, 1.3 -> 0"),
    P("gas_vs_us", "cost", "Regular gas vs U.S. average", 2, "ratio", ("eia",), "weekly",
      _ratio("gas_regular", "gas_regular_us"), lambda r: linear_score(r, 0.9, 1.15),
      "local/U.S.: 0.9 -> 100, 1.15 -> 0", profile_boost={"car": 2.5}),
    P("rent_burden_fmr", "cost", "Studio Fair Market Rent as share of full-time minimum-wage pay", 3, "share",
      ("hud_fmr", "static_tables"), "annual", _rent_burden("fmr_studio"), lambda s: linear_score(s, 0.3, 1.0),
      "rent / (min wage x 173.3 h): 30% -> 100, 100% -> 0"),
    P("rent_burden_acs", "cost", "Median gross rent as share of full-time minimum-wage pay", 1, "share",
      ("census_acs", "static_tables"), "annual", _rent_burden("median_gross_rent"), lambda s: linear_score(s, 0.3, 1.0),
      "same rule, ACS median rent as a reality check on FMR"),
    # income
    P("unemployment", "income", "County unemployment rate", 3, "%", ("bls_laus",), "monthly",
      _measure("unemployment_rate"), lambda v: linear_score(v, 3.0, 10.0), "3% -> 100, 10% -> 0"),
    P("min_wage", "income", "State minimum wage", 2, "USD/hour", ("static_tables",), "annual",
      _measure("min_wage"), lambda v: linear_score(v, 15.0, 7.25), "$15 -> 100, $7.25 federal floor -> 0"),
    P("job_help_5km", "income", "Employment agencies within 5 km", 2, "count", ("osm",), "daily",
      _count({"employment_agency"}, 5000, sources=("osm",)), lambda n: count_score(n, 1.0), "count, k=1"),
    # mobility
    P("transit_stops_1km", "mobility", "Transit stops within 1 km", 3, "count", ("transitland",), "live",
      _count({"transit_stop"}, 1000, sources=("transitland",)), lambda n: count_score(n, 3.0), "count, k=3",
      profile_boost={"car": 0.3}),
    P("essentials_walk", "mobility", "Median walk to nearest store, pharmacy, library, clinic, post office", 3, "min",
      ("snap", "osm"), "daily", _essentials_walk, lambda v: linear_score(v, 10.0, 45.0),
      "straight line x 1.3 at 80 m/min: 10 min -> 100, 45 min -> 0; needs 3 of 5"),
    # health
    P("clinics_5km", "health", "Clinics and health centers within 5 km", 2, "count", ("osm", "hrsa"), "daily",
      _count({"clinic", "health_center"}, 5000, sources=("osm", "hrsa")), lambda n: count_score(n, 1.0), "count, k=1"),
    P("pharmacy_3km", "health", "Pharmacies within 3 km", 1, "count", ("osm",), "daily",
      _count({"pharmacy"}, 3000, sources=("osm",)), lambda n: count_score(n, 1.0), "count, k=1"),
    # hygiene
    P("restrooms_water_2km", "hygiene", "Public restrooms and drinking water within 2 km", 2, "count", ("osm",), "daily",
      _count({"toilets", "drinking_water"}, 2000, sources=("osm",)), lambda n: count_score(n, 3.0), "count, k=3"),
    P("showers_5km", "hygiene", "Public showers within 5 km", 2, "count", ("osm",), "daily",
      _count({"shower"}, 5000, zero_needs=("google_places_showers",), sources=("osm",),
             zero_reason="none found, but OpenStreetMap rarely maps public showers; ask 211 or a day center"),
      lambda n: count_score(n, 1.0), "count, k=1; OSM rarely maps showers, so zero is Unknown"),
    P("laundry_5km", "hygiene", "Laundromats within 5 km", 1, "count", ("osm",), "daily",
      _count({"laundry"}, 5000, sources=("osm",)), lambda n: count_score(n, 1.0), "count, k=1"),
    P("library_3km", "hygiene", "Public libraries (Wi-Fi, charging) within 3 km", 2, "count", ("osm",), "daily",
      _count({"library"}, 3000, sources=("osm",)), lambda n: count_score(n, 1.0), "count, k=1"),
    # kids
    P("schools_5km", "kids", "Public schools within 5 km", 2, "count", ("urban_ed",), "annual",
      _count({"school"}, 5000, sources=("urban_ed",)), lambda n: count_score(n, 2.0), "count, k=2 (NCES 2022-23)"),
    P("school_levels_5km", "kids", "Grade levels covered within 5 km (primary, middle, high)", 1, "levels",
      ("urban_ed",), "annual", _school_levels, lambda v: linear_score(v, 3.0, 0.0), "3 levels -> 100, 0 -> 0"),
    # weather
    P("weather_alert", "weather", "Worst active NWS alert", 3, "severity", ("nws",), "live",
      _alert_rank, lambda r: ALERT_SCORE.get(int(r), 50.0),
      "none -> 100, minor -> 75, moderate -> 50, severe -> 15, extreme -> 0", profile_boost={"tonight": 1.5}),
    P("cold_nights", "weather", "Cold-night load, next 7 nights", 2, "nights", ("open_meteo",), "live",
      _cold_load, lambda v: linear_score(v, 0.0, 5.0),
      "freezing nights + 0.35 x nights at 33-40 °F: 0 -> 100, 5 -> 0"),
    P("hot_days", "weather", "Days at 95 °F or hotter, next 7 days", 1, "days", ("open_meteo",), "live",
      _measure("hot_days_7d"), lambda v: linear_score(v, 0.0, 4.0), "0 -> 100, 4 -> 0"),
    # legal
    P("post_office_5km", "legal", "USPS post offices within 5 km (General Delivery mail)", 2, "count", ("osm",),
      "daily", _count({"post_office"}, 5000, sources=("osm",)), lambda n: count_score(n, 1.0),
      "count, k=1; private couriers tagged as post offices are excluded"),
    P("local_rules", "legal", "Camping and sleeping-in-vehicle rules", 2, "curated", ("static_tables",), "static",
      _local_rules, lambda v: v, "curated per county: ban -> 20, no ban found -> 80; empty -> Unknown"),
    # planned (always Unknown until a source is wired; listed so the gaps are visible)
    P("id_help", "legal", "ID and vital-records offices", 1, "count", (), "static",
      _planned("DMV and vital-records office locations"), lambda v: v, "planned", status="planned"),
    P("legal_aid", "legal", "Civil legal aid offices", 1, "count", (), "static",
      _planned("LSC-funded legal aid office locations"), lambda v: v, "planned", status="planned"),
    P("behavioral_health", "health", "Mental health and substance-use treatment", 1, "count", (), "static",
      _planned("SAMHSA treatment locator"), lambda v: v, "planned", status="planned"),
    P("air_quality", "weather", "Air quality (AQI)", 1, "AQI", (), "live",
      _planned("AirNow or Open-Meteo air-quality API"), lambda v: v, "planned", status="planned"),
]
PARAM_BY_ID = {p.id: p for p in PARAMS}

EXCLUDED_ON_PURPOSE = {
    "crime rates": "Scoring places by crime echoes redlining and steers people away from areas with services.",
    "demographics (race, income, poverty rate)": "Footing rates access to help, never who lives somewhere.",
}

PROFILE_CATEGORY_BOOST = {
    "car": {"cost": 1.3, "mobility": 0.5},
    "kids": {"kids": 3.0},
    "tonight": {"shelter": 2.0, "weather": 1.5},
    "on_foot": {"mobility": 1.3},
}


def catalog_markdown() -> str:
    lines = ["| Category (weight) | Parameter | Weight | Sources | Refresh | Scoring rule | Status |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for c in CATEGORIES:
        for p in [p for p in PARAMS if p.category == c.id]:
            lines.append(f"| {c.label} ({c.weight:g}) | {p.label} | {p.weight:g} | "
                         f"{', '.join(p.sources) or '—'} | {p.refresh} | {p.rule} | {p.status} |")
    return "\n".join(lines)
