"""Cross-source enrichment: facts one source knows that another misses.

Example found in the real Christiansburg data: "CVS PHARMACY 7543" is in the USDA SNAP list but
OpenStreetMap does not map it as a pharmacy. A SNAP store whose name is a pharmacy chain is
added as a pharmacy (tagged as inferred), then de-duplicated against OSM like any place.
"""
from __future__ import annotations

import re

from .models import Place

PHARMACY = re.compile(r"\b(CVS|WALGREENS|RITE AID|PHARMACY|DRUG)\b", re.I)
DISCOUNT = re.compile(r"\b(DOLLAR GENERAL|FAMILY DOLLAR|DOLLAR TREE)\b", re.I)


def enrich(places: list[Place]) -> list[Place]:
    extra: list[Place] = []
    for p in places:
        if p.kind != "snap_retailer":
            continue
        if DISCOUNT.search(p.name):
            p.tags["discount_store"] = True
        if PHARMACY.search(p.name):
            extra.append(Place(id=p.id.replace("snap:", "snapname:"), name=p.name, kind="pharmacy",
                               lat=p.lat, lon=p.lon, source="snap_name",
                               tags={"inferred_from": "USDA SNAP store name", "address": p.tags.get("address")},
                               distance_m=p.distance_m, walk_min=p.walk_min))
    return places + extra
