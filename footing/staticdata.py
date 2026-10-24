"""Loaders for hand-maintained tables in footing/static/. Each table cites its source."""
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"


@lru_cache(maxsize=None)
def _json(name: str) -> dict:
    return json.loads((STATIC_DIR / name).read_text(encoding="utf-8"))


def _csv(name: str) -> list[dict]:
    with open(STATIC_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_basket() -> dict:
    return _json("survival_basket.json")


def min_wage(state_abbr: str | None) -> tuple[float | None, str]:
    t = _json("state_min_wage.json")
    if state_abbr and state_abbr in t["states_usd_hr"]:
        return t["states_usd_hr"][state_abbr], t["as_of"]
    return None, t["as_of"]


def tfp_weekly(person: str | None = None) -> tuple[float, str]:
    t = _json("thrifty_food_plan.json")
    key = person or t["default_person_for_basket"]
    return t["weekly_usd"][key], t["plan"]


def coc_capacity(county_fips: str | None) -> dict | None:
    if not county_fips:
        return None
    for row in _csv("coc_capacity.csv"):
        if row.get("county_fips") == county_fips:
            return row
    return None


def hrsa_sites() -> list[dict]:
    return _csv("hrsa_sites.csv")


def local_rules(county_fips: str | None) -> dict | None:
    if not county_fips:
        return None
    return _json("local_rules.json")["by_county_fips"].get(county_fips)
