"""Print one committed Virginia field and its recorded sources, without network calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELD_SOURCES = {
    "fmr": ["hud_fmr"],
    "coc": ["hud_pit", "hud_hic", "hud_coc_areas"],
    "pop_2025": ["census_pep"],
    "services": ["usda_snap", "osm", "apta_fare_free"],
    "help_points": ["osm"],
    "crime": ["fbi_cde", "fbi_cde_second"],
    "enforcement_287g": ["ice_287g", "va_ed1_2026"],
    "local_rule": ["hb1394_2026"],
}


def lookup(data: dict, fips: str, field: str) -> dict:
    loc = data["localities"][fips]
    keys = list(FIELD_SOURCES[field])
    result = {"fips": fips, "name": loc["name"], "field": field, "value": loc[field]}
    if field == "local_rule" and loc[field] and loc[field].get("source"):
        keys.append(loc[field]["source"])
    if field == "crime":
        city = data.get("incident_cities", {}).get(fips)
        result["incident_coverage"] = city
        if city:
            keys.append("city_incidents")
    result["sources"] = {key: data["sources"][key] for key in keys if key in data["sources"]}
    if field == "crime" and city:
        result["sources"]["city_incidents"] = {
            **result["sources"]["city_incidents"], "title": city["agency"], "url": city["source_url"],
            "as_of": f"{city['window_start']} to {city['latest_date']}",
        }
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fips", nargs="?", help="five-digit Virginia locality FIPS, e.g. 51710")
    ap.add_argument("--field", choices=FIELD_SOURCES)
    ap.add_argument("--list", action="store_true", help="list supported fields without loading data")
    args = ap.parse_args()
    if args.list:
        print("\n".join(FIELD_SOURCES))
        return
    if not args.fips or not args.field:
        ap.error("supply a FIPS and --field, or use --list")
    data = json.loads((ROOT / "footing/static/va_localities.json").read_text(encoding="utf-8"))
    if args.fips not in data["localities"]:
        ap.error(f"unknown Virginia locality FIPS: {args.fips}")
    print(json.dumps(lookup(data, args.fips, args.field), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
