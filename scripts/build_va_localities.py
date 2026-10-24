"""Build footing/static/va_localities.json: one row per Virginia county and independent city (133).

Inputs (all real captures, see fixtures/va_2026-10-24/MANIFEST.json):
  hud_fmr_fy2026_va.json        HUD FY2026 Fair Market Rents (revised), 0-4 bedrooms, per locality
  fbi_cde_agencies_2025_va.json FBI Crime Data Explorer, 2025 violent + property offenses per agency
  hud_hic_2025_va.json          HUD 2025 Housing Inventory Count, beds per CoC
  hud_coc_membership_va.json    which CoC each locality is in (HUD CoC Grantee Areas layer)
  city_incidents_tiles.json     Norfolk + Charlottesville police incidents, last 12 months, per ~1 km tile
and footing/static/va_local_rules.json (hand-checked, cited) plus the bundled 1:10M locality shapes.

Run: python scripts/build_va_localities.py          (writes the file)
     python scripts/build_va_localities.py --check  (fails if the committed file is stale)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.va_geo import va_localities  # noqa: E402

FIX = ROOT / "fixtures" / "va_2026-10-24"
STATIC = ROOT / "footing" / "static"
OUT = STATIC / "va_localities.json"

# Town police departments that FBI CDE lists under two counties: filed under the county most of the town is in.
TOWN_COUNTY = {"VA0730100": "PRINCE EDWARD",   # Farmville
               "VA0510100": "LANCASTER",       # Kilmarnock
               "VA0860200": "SMYTH",           # Saltville
               "VA0960500": "WISE"}            # St. Paul


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def pct(values: list[float], q: float) -> float:
    v = sorted(values)
    if not v:
        return 0.0
    pos = q * (len(v) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def r4(x: float) -> float:
    return round(x, 4)


def build() -> dict:
    shapes = va_localities()
    fmr = load("hud_fmr_fy2026_va.json")
    cde = load("fbi_cde_agencies_2025_va.json")
    hic = load("hud_hic_2025_va.json")
    coc = load("hud_coc_membership_va.json")
    inc = load("city_incidents_tiles.json")
    rules = json.loads((STATIC / "va_local_rules.json").read_text(encoding="utf-8"))
    policy = json.loads((STATIC / "state_policy.json").read_text(encoding="utf-8"))
    min_wage = policy["states"]["VA"]["min_wage"]

    loc: dict[str, dict] = {}
    name_to_fips: dict[str, str] = {}
    for fips10, cname, area, metro, pop, f0, f1, f2, f3, f4 in fmr["rows"]:
        fips = fips10[:5]
        kind = "city" if int(fips[2:]) >= 500 else "county"
        key = cname.upper().replace(" COUNTY", "") if kind == "county" else cname.upper()
        name_to_fips[key] = fips
        fmr_by_br = {"0": f0, "1": f1, "2": f2, "3": f3, "4": f4}
        loc[fips] = {
            "name": cname, "kind": kind, "pop2023": pop,
            "rent": {"fmr": fmr_by_br, "fmr_area": area, "metro": bool(metro),
                     "housing_wage": {b: round(v * 12 / 0.30 / 2080, 2) for b, v in fmr_by_br.items()}},
        }
    assert len(loc) == 133, len(loc)

    # ---- crime: FBI CDE agencies -> locality ---------------------------------------------------------------
    cols = cde["cols"]
    agencies: dict[str, list[dict]] = {f: [] for f in loc}
    unmatched = []
    for row in cde["rows"]:
        a = dict(zip(cols, row))
        county = TOWN_COUNTY.get(a["ori"], a["county"])
        fips = name_to_fips.get(county)
        if fips is None:
            unmatched.append((a["ori"], a["name"], county))
            continue
        agencies[fips].append(a)
    assert not unmatched, unmatched
    for fips, ags in agencies.items():
        full = [a for a in ags if a["months_violent"] == 12 and a["months_property"] == 12 and a["violent"] is not None]
        pop_all = sum(a["population"] or 0 for a in ags)
        pop_full = sum(a["population"] or 0 for a in full)
        crime = {"agencies": [{"name": a["name"], "ori": a["ori"], "violent": a["violent"], "property": a["property"],
                               "population": a["population"], "months": min(a["months_violent"], a["months_property"])}
                              for a in sorted(ags, key=lambda x: x["ori"])]}
        if not full or pop_full <= 0:
            crime.update(violent_per_100k=None, property_per_100k=None, coverage=0.0,
                         note=("No police agency here reported 2025 crime to the FBI." if ags else
                               "No city, town or county police agency is listed for this locality in FBI CDE."))
        else:
            v = sum(a["violent"] for a in full)
            p = sum(a["property"] for a in full)
            crime.update(violent=v, property=p, population=pop_full,
                         violent_per_100k=round(v / pop_full * 1e5, 1), property_per_100k=round(p / pop_full * 1e5, 1),
                         coverage=round(pop_full / pop_all, 3) if pop_all else 1.0,
                         note=None if len(full) == len(ags) else
                         f"{len(ags) - len(full)} of {len(ags)} agencies reported fewer than 12 months and are left out.")
        loc[fips]["crime"] = crime
    rates_v = [d["crime"]["violent_per_100k"] for d in loc.values() if d["crime"]["violent_per_100k"] is not None]
    rates_p = [d["crime"]["property_per_100k"] for d in loc.values() if d["crime"]["property_per_100k"] is not None]

    # ---- shelter capacity: HUD HIC 2025 per CoC ----------------------------------------------------------------
    hic_cols = hic["cols"]
    beds = {r[0]: dict(zip(hic_cols, r)) for r in hic["va"]}
    names = dict(hic["names"])
    members: dict[str, list[str]] = {}
    for fips, c in coc["coc_by_fips"].items():
        loc[fips]["coc"] = c
        members.setdefault(c, []).append(fips)
    cocs = {}
    for c, fl in sorted(members.items()):
        residents = sum(loc[f]["pop2023"] for f in fl)
        b = beds[c]
        yr = b["Total Year-Round Beds (ES, TH, SH)"]
        cocs[c] = {"name": names[c], "localities": sorted(fl), "residents_2023": residents,
                   "beds_year_round": yr, "beds_seasonal": b["Total Seasonal Beds (ES)"],
                   "beds_overflow": b["Total Overflow Beds (ES)"],
                   "beds_for_adults": b["Total Beds for Households without Children (ES, TH, SH)"],
                   "beds_for_families": b["Total Beds for Households with Children (ES, TH, SH)"],
                   "beds_per_10k": round(yr / residents * 1e4, 2)}
    bed_rates = [c["beds_per_10k"] for c in cocs.values()]

    # ---- local rules -------------------------------------------------------------------------------------------
    for fips, r in rules["by_fips"].items():
        loc[fips]["rules"] = r

    # ---- incident tiles (Norfolk, Charlottesville) ---------------------------------------------------------------
    tiles = {}
    inc_cities = {}
    for c in inc["cities"]:
        inc_cities[c["fips"]] = {"name": c["name"], "agency": c["agency"], "source_url": c["source_url"],
                                 "license": c["license"], "window_start": inc["window_start"],
                                 "latest_date": c["latest_date"], "records_in_window": c["records_in_window"],
                                 "by_class": c["by_class"], "placed": c["placed"], "used": c["used"],
                                 "not_placed": c["not_placed"]}
        for t in c["tiles"]:
            tiles[t["tile"]] = {"lat": t["lat"], "lon": t["lon"], "fips": c["fips"],
                                "v": t["violent"], "p": t["property"], "e": t["enforcement"]}
        loc[c["fips"]]["incident_tiles"] = True

    def nb_sum(tid: str, key: str) -> int:
        i, j = (int(x) for x in tid[1:].split("_"))
        s = 0
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                t = tiles.get(f"t{i + di}_{j + dj}")
                if t:
                    s += t[key]
        return s
    nb_v = [nb_sum(t, "v") for t in tiles]

    # ---- shapes --------------------------------------------------------------------------------------------------
    for fips, s in shapes.items():
        loc[fips]["shape"] = [[[[r4(x), r4(y)] for x, y in ring] for ring in poly] for poly in s["polygons"]]
    loc["51610"]["point"] = [38.88492, -77.1727]      # Falls Church: too small for a 1:10M shape (FBI CDE agency point)

    return {
        "about": "Virginia locality data for Footing: rents, crime, shelter beds, local rules and shapes for all 95 counties "
                 "and 38 independent cities. Built by scripts/build_va_localities.py from captures in fixtures/va_2026-10-24.",
        "built_from": "fixtures/va_2026-10-24",
        "min_wage": min_wage,
        "sources": {
            "rent": {"title": "HUD FY2026 Fair Market Rents (revised)", "url": "https://www.huduser.gov/portal/datasets/fmr/fmr2026/FY26_FMRs_revised.xlsx", "as_of": "FY2026"},
            "crime": {"title": "FBI Crime Data Explorer, offenses known to law enforcement, by agency", "url": "https://cde.ucr.cjis.gov", "as_of": "calendar 2025",
                      "note": "FBI 'violent crime' = murder, rape, robbery, aggravated assault. Agencies' own populations; county sheriffs cover areas outside towns that have their own police."},
            "incidents": {"title": "City police incident feeds (Norfolk, Charlottesville)", "as_of": inc["window_start"] + " to " + inc["captured_at"][:10],
                          "note": "Offense labels sorted by footing/static/va_offense_classes.json; geocoded by block with the Census batch geocoder; counted per 0.01-degree tile. No address or incident ID is kept."},
            "shelter": {"title": "HUD 2025 Housing Inventory Count by CoC", "url": "https://www.huduser.gov/portal/sites/default/files/xls/2007-2025-HIC-Counts-by-CoC.xlsx", "as_of": "January 2025"},
            "coc_map": {"title": "HUD Continuum of Care Grantee Areas", "url": coc["layer"]},
            "rules": {"title": "Footing local rules table (cited per row)", "url": "footing/static/va_local_rules.json", "as_of": "2026-10-24"},
            "shapes": {"title": "us-atlas counties-10m (U.S. Census cartographic boundaries, 1:10,000,000)", "url": "https://github.com/topojson/us-atlas"},
        },
        "scales": {
            "violent_per_100k": {"good": round(pct(rates_v, 0.1), 1), "bad": round(pct(rates_v, 0.9), 1), "rule": "10th and 90th percentile of Virginia localities with data"},
            "property_per_100k": {"good": round(pct(rates_p, 0.1), 1), "bad": round(pct(rates_p, 0.9), 1)},
            "beds_per_10k": {"good": round(pct(bed_rates, 0.9), 2), "bad": round(pct(bed_rates, 0.1), 2), "rule": "90th and 10th percentile of Virginia's 16 CoCs"},
            "tile_violent_3x3": {"good": 0, "bad": round(pct(nb_v, 0.9), 1), "rule": "violent incidents in the 3x3 tiles around a point (about 3 km across), 12 months; bad = 90th percentile of recorded tiles"},
        },
        "rules_note": rules["state_note"],
        "rule_statuses": rules["statuses"],
        "cocs": cocs,
        "incident_cities": inc_cities,
        "tiles": dict(sorted(tiles.items())),
        "localities": dict(sorted(loc.items())),
    }


def main() -> int:
    data = build()
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=False, sort_keys=False) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("va_localities.json is stale: run python scripts/build_va_localities.py")
            return 1
        print("va_localities.json OK")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(text) // 1024} KB): {len(data['localities'])} localities, "
          f"{len(data['tiles'])} incident tiles, scales {data['scales']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
