"""Build footing/static/va_localities.json: one row per Virginia locality (95 counties + 38 independent cities).

    python scripts/build_va_localities.py           # rebuild from data_raw/
    python scripts/build_va_localities.py --check   # rebuild in memory and validate against the committed file

Inputs are raw captures in data_raw/ (see data_raw/README.md for every URL, date and method). Nothing here is
estimated: a value we could not get stays null, and the row says why. Hand-compiled tables (local camping rules,
fare-free transit) are below, and every row cites a source a person can open.

Matching rules worth knowing:
  * Virginia's independent cities are not part of any county. "ROANOKE" in a federal file means Roanoke County,
    "ROANOKE CITY" means the city. Names that exist only as a city (NORFOLK, LYNCHBURG...) map to the city.
  * Crime: agencies are filed under the locality in the FBI's `counties` field; agencies with no county (state
    police troops, universities) are placed by their coordinates. A locality's rate uses only agencies that
    report a population (police departments and sheriffs), and is Unknown when an agency covering 25% or more
    of the people there did not report all 12 months.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw"
OUT = ROOT / "footing" / "static" / "va_localities.json"
sys.path.insert(0, str(ROOT))

from footing.va import locality_at, localities  # noqa: E402

READ_ON = "2026-10-24"

SOURCES = {
    "census_tiger": {"title": "TIGERweb State_County MapServer, layer 1 (counties), STATE='51'", "publisher": "U.S. Census Bureau",
                     "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
                     "as_of": "current vintage", "read_on": READ_ON,
                     "note": "Generalized to ~100 m (maxAllowableOffset 0.0009) and quantized for the app."},
    "census_pep": {"title": "County population totals, Vintage 2025 (co-est2025-alldata.csv)", "publisher": "U.S. Census Bureau",
                   "url": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/counties/totals/",
                   "as_of": "July 1, 2025 estimate", "read_on": READ_ON},
    "hud_fmr": {"title": "FY 2026 Fair Market Rent Documentation System", "publisher": "HUD Office of Policy Development and Research",
                "url": "https://www.huduser.gov/portal/datasets/fmr/fmrs/FY2026_code/select_Geography.odn",
                "as_of": "FY2026 (Oct 1, 2025 - Sep 30, 2026)", "read_on": READ_ON,
                "note": "Read one county page at a time. Where HUD uses Small Area FMRs (DC and Hampton Roads metros), "
                        "the metro-wide FMR from the linked 'other programs' page is used."},
    "hud_pit": {"title": "2007-2025 PIT Counts by CoC (2025 AHAR Part 1)", "publisher": "HUD",
                "url": "https://www.huduser.gov/portal/datasets/ahar/2025-ahar-part-1-pit-estimates-of-homelessness-in-the-us.html",
                "as_of": "January 2025 count", "read_on": READ_ON,
                "note": "VA-501, VA-505 and VA-507 did a sheltered-only count in 2025; their unsheltered numbers equal "
                        "the 2024 count (carried forward)."},
    "hud_hic": {"title": "2007-2025 HIC Counts by CoC", "publisher": "HUD",
                "url": "https://www.huduser.gov/portal/sites/default/files/xls/2007-2025-HIC-Counts-by-CoC.xlsx",
                "as_of": "January 2025 inventory", "read_on": READ_ON},
    "hud_coc_areas": {"title": "Continuum of Care Grantee Areas (feature service)", "publisher": "HUD eGIS",
                      "url": "https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/Continuum_of_Care_Grantee_Areas/FeatureServer/0",
                      "as_of": "current service (no vintage in the data)", "read_on": READ_ON,
                      "note": "Queried at a point inside each locality."},
    "osm": {"title": "OpenStreetMap via Overpass API (statewide query)", "publisher": "OpenStreetMap contributors (ODbL)",
            "url": "https://overpass-api.de/", "as_of": "OSM base 2026-10-25T00:21Z", "read_on": READ_ON,
            "note": "Volunteer-mapped. A zero means 'not mapped', not 'none here'."},
    "usda_snap": {"title": "SNAP Retailer Locator data (feature service, counts by county and store type)", "publisher": "USDA FNS",
                  "url": "https://services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/snap_retailer_location_data/FeatureServer/0",
                  "as_of": "layer edited 2026-10-21", "read_on": READ_ON},
    "fbi_cde": {"title": "Crime Data Explorer, agency summaries (violent and property crime, Jan-Dec 2025)", "publisher": "FBI UCR",
                "url": "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend",
                "as_of": "2025 calendar year (CDE refreshed 2026-10-15)", "read_on": READ_ON,
                "note": "Reported offenses, not risk. Reporting and policing differ by place."},
    "fbi_cde_second": {"title": "Crime Data Explorer, agency summaries - second independent capture",
                       "publisher": "FBI UCR", "url": "https://cde.ucr.cjis.gov",
                       "as_of": "2025 calendar year", "read_on": READ_ON,
                       "note": "Captured separately from fbi_cde on the same day. Used to cross-check the offence "
                               "counts (they agree for all 240 shared agencies) and for months reported, where it is "
                               "the more precise of the two. See docs/FACT_CHECK.md."},
    "city_incidents": {"title": "Police incident reports, 12 months, geocoded to ~1 km tiles (Norfolk and Charlottesville)",
                       "publisher": "City of Norfolk and City of Charlottesville open data; U.S. Census batch geocoder",
                       "url": "https://data.norfolk.gov/resource/r7bn-2egr.json",
                       "as_of": "2025-10-24 to 2026-10-24", "read_on": READ_ON,
                       "note": "Counts per tile only. No address, incident ID or officer name was kept. Trespass, "
                               "loitering, drunkenness and similar calls are bucketed as 'enforcement' and are never "
                               "counted as danger: they show where police make contact, which is where unhoused "
                               "people already are. Capture method: data_raw/city_incidents_MANIFEST.json."},
    "ice_287g": {"title": "287(g) Participating Agencies", "publisher": "U.S. Immigration and Customs Enforcement",
                 "url": "https://www.ice.gov/identify-and-arrest/287g", "as_of": "file downloaded 2026-10-24", "read_on": READ_ON},
    "va_ed1_2026": {"title": "Spanberger ends agreement between state law enforcement agencies and ICE", "publisher": "Cardinal News",
                    "url": "https://cardinalnews.org/2026/02/05/spanberger-ends-agreement-between-state-law-enforcement-agencies-and-ice/",
                    "as_of": "2026-02-05", "read_on": READ_ON,
                    "note": "Executive Directive One ended state agencies' 287(g) agreements; local agreements are not affected."},
    "apta_fare_free": {"title": "Universal Fare-Free Public Transit Systems (August 13, 2026)", "publisher": "American Public Transportation Association",
                       "url": "https://www.apta.com/wp-content/uploads/2026/06/Fare-Free-Systems-08.13.2026.pdf",
                       "as_of": "2026-08-13", "read_on": READ_ON},
    "drpt_trip_2025": {"title": "Transit Ridership Incentive Program, FY2025 report (RD611)", "publisher": "Virginia DRPT",
                       "url": "https://rga.lis.virginia.gov/Published/2025/RD611/PDF", "as_of": "October 2025", "read_on": READ_ON},
    "hb1394_2026": {"title": "Virginia House committee kills bill to decriminalize homelessness", "publisher": "WHRO",
                    "url": "https://www.whro.org/2026-02-08/virginia-house-committee-kills-bill-to-decriminalize-homelessness",
                    "as_of": "2026-02-08", "read_on": READ_ON},
    "roanoke_camping": {"title": "Virginia bill could overturn Roanoke's homeless camping ban", "publisher": "WSLS 10",
                        "url": "https://www.wsls.com/news/local/2026/02/04/virginia-bill-could-overturn-roanokes-homeless-camping-ban",
                        "as_of": "2026-02-04", "read_on": READ_ON},
    "bristol_camping": {"title": "Bristol, Virginia City Council passes public camping ban", "publisher": "WSET",
                        "url": "https://wset.com/news/local/bristol-virginia-city-council-passes-public-camping-ban",
                        "as_of": "2022-08-09", "read_on": READ_ON},
    "hampton_camping": {"title": "Hampton bans camping and sleeping on public property", "publisher": "WHRO",
                        "url": "https://www.whro.org/local-government/2026-04-09/hampton-bans-camping-and-sleeping-on-public-property",
                        "as_of": "2026-04-09", "read_on": READ_ON},
    "cville_tabled": {"title": "City Council tables ordinance that would ban encampments on public property", "publisher": "29News",
                      "url": "https://www.29news.com/2025/09/03/city-council-tables-ordinance-that-would-ban-encampments-public-property/",
                      "as_of": "2025-09-03", "read_on": READ_ON},
    "cville_free_bridge": {"title": "Free Bridge encampment deadline (Charlottesville)", "publisher": "VPM",
                           "url": "https://www.vpm.org/news/2026-08-07/free-bridge-rivanna-river-cville-displacement-homelessness",
                           "as_of": "2026-08-07", "read_on": READ_ON},
    "danville_postponed": {"title": "Danville City Council postpones vote on ordinance to ban camping on city property", "publisher": "WSLS 10",
                           "url": "https://wsls.com/news/local/2022/10/19/danville-city-council-postpones-vote-on-ordinance-to-ban-camping-on-city-property",
                           "as_of": "2022-10-19", "read_on": READ_ON},
    "fairfax_encampments": {"title": "NAACP still has concerns about Fairfax County's clearing of homeless encampments", "publisher": "FFXnow",
                            "url": "https://www.ffxnow.com/2025/04/01/naacp-still-has-concerns-about-fairfax-countys-clearing-of-homeless-encampments/",
                            "as_of": "2025-04-01", "read_on": READ_ON},
}

# ---- Local rules on sleeping/camping in public, Virginia (hand-compiled; every row cites a source) -------------------
# status: broad_ban (camping/sleeping banned on public property broadly) | limited_ban (named areas only) |
#         site_closure (one site closed, trespass enforced) | proposed (debated, not adopted) | clearing_policy
# Anything not listed here is NOT "no rule": it is "not checked yet".
LOCAL_RULES = {
    "51650": ("broad_ban", "Camping and sleeping outdoors on public property is a Class 2 misdemeanor (up to 6 months and "
              "$1,000). Police must warn several times and offer housing help before a summons. Approved April 8, 2026.",
              "hampton_camping"),
    # Scored as a broad ban, but this one is a judgement call and the merge recorded it rather than hiding it.
    # Session 4 read "streets, sidewalks, alleys and other public rights of way" as a broad ban (0); session 3
    # read the same summary as a partial ban (35), because parks and other city land are not rights of way.
    # Neither session read the ordinance itself - both cited news coverage. Kept at 0 because the cost of the
    # two errors is not equal: scoring Bristol harsher than it is costs someone an option, scoring it gentler
    # sends them somewhere they can be charged. docs/FACT_CHECK.md asks for the city code to settle it.
    "51520": ("broad_ban", "Camping on city streets, sidewalks, alleys and other public rights of way is a Class 4 "
              "misdemeanor (up to $250). Passed August 9, 2022. Whether the ban reaches parks and other city "
              "land, rather than only rights of way, has not been confirmed from the city code.", "bristol_camping"),
    "51770": ("limited_ban", "Camping on downtown sidewalks is a Class 4 misdemeanor (up to $250). In effect since 2022.",
              "roanoke_camping"),
    "51540": ("site_closure", "The Free Bridge encampment by the Rivanna River closed on Sept 1, 2026; staying there can "
              "mean arrest. A citywide ban was tabled on Sept 2, 2025. The city opened a temporary shelter at 2000 Holiday Drive.",
              "cville_free_bridge"),
    "51590": ("proposed", "A ban on camping on city property was proposed in Oct 2022; the vote was postponed. "
              "We could not confirm what happened after.", "danville_postponed"),
    "51059": ("clearing_policy", "The county clears encampments on land it owns under its own guidelines (not an "
              "ordinance we could find). Other owners (state, schools, parks) can use trespass law.", "fairfax_encampments"),
    # Searched and found nothing. That is weaker than "no ban" and stronger than "not checked yet", so it is
    # recorded as its own status and still not scored: the town and county codes were not read line by line.
    "51121": ("checked_none_found", "A news and ordinance search on 2026-10-24 found no camping or sleeping ban for "
              "Montgomery County, Blacksburg or Christiansburg. The town and county codes were not read line by line, "
              "so this is not a confirmed 'no ban'.", None),
}
# proposed / clearing_policy / checked_none_found: shown to the person, never scored.
RULE_SCORE = {"broad_ban": 0, "limited_ban": 35, "site_closure": 60}

# ---- Fare-free buses (APTA list Aug 2026; DRPT zero-fare projects FY2025) ------------------------------------------
FARE_FREE = {
    "51510": ("DASH", "apta_fare_free"),
    "51121": ("Blacksburg Transit", "apta_fare_free"),
    "51600": ("City of Fairfax CUE Bus", "apta_fare_free"),
    "51630": ("FXBGO! (Fredericksburg Regional Transit)", "apta_fare_free"),
    "51760": ("GRTC (Greater Richmond Transit Company)", "apta_fare_free"),
    "51540": ("Charlottesville Area Transit", "drpt_trip_2025"),
    "51730": ("Petersburg Area Transit", "drpt_trip_2025"),
}


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def name_index():
    """Upper-case name -> fips, with ' CITY' for cities whose name also exists as a county."""
    locs = localities()
    count = {}
    for d in locs:
        count[d["short"].upper()] = count.get(d["short"].upper(), 0) + 1
    idx = {}
    for d in locs:
        base = d["short"].upper()
        if d["kind"] == "city":
            idx[base + " CITY"] = d["fips"]
            if count[base] == 1:
                idx[base] = d["fips"]
        else:
            idx[base] = d["fips"]
            idx[base + " COUNTY"] = d["fips"]
    return idx


def fips_for(name: str, idx: dict) -> str | None:
    n = " ".join(name.replace("’", "'").strip().upper().split())
    if n == "BEDFORD CITY":            # merged into Bedford County in 2013
        n = "BEDFORD"
    return idx.get(n)


def reported_months() -> dict:
    """Months each agency actually reported in 2025, from whichever of the two captures is more precise.

    The FBI's CDE was captured twice, independently, on the same day: data_raw/fbi_cde_va_agencies_2025.json
    (412 agencies) and data_raw/second_capture_fbi_cde_agencies_2025_va.json (240, the ones with a
    population). They agree on the offence counts of every one of the 240 agencies they share. They disagree
    on months reported for exactly three: Middleburg PD (12 vs 11), Remington PD (12 vs 3) and Quantico PD
    (12 vs 0). The first capture records only 12 or 0 and nothing between, so it looks like it inferred
    "reported at all" rather than reading the monthly breakdown, which the second did.

    Neither can be re-checked from the build sandbox, which cannot reach cde.ucr.cjis.gov, so this takes the
    LOWER of the two. That is the conservative direction: a partial year is flagged as a coverage gap
    instead of being counted as a full one. All three are small town departments with 0 violent offences
    between them, so the whole effect is 5 property offences in Loudoun County. Written up in
    docs/FACT_CHECK.md for someone who can open CDE to settle.
    """
    second = load("second_capture_fbi_cde_agencies_2025_va.json")
    out = {}
    for row in second["rows"]:
        a = dict(zip(second["cols"], row))
        out[a["ori"]] = (a["months_violent"], a["months_property"])
    return out


def crime_by_locality(idx: dict, pop: dict) -> dict:
    raw = load("fbi_cde_va_agencies_2025.json")
    cols = raw["columns"]
    months = reported_months()
    agg: dict[str, dict] = {}
    for row in raw["rows"]:
        a = dict(zip(cols, row))
        if a["ori"] in months:
            mv, mp = months[a["ori"]]
            a["violent_months"] = min(a["violent_months"], mv)
            a["property_months"] = min(a["property_months"], mp)
        names = [x.strip() for x in (a["counties"] or "").split(",") if x.strip()]
        names = [n for n in names if n not in ("NOT SPECIFIED", "UNMAPPED COUNTY")]
        # Four town police departments straddle a county line and the FBI lists both counties (Farmville,
        # St. Paul, Saltville, Kilmarnock). Taking the first name put Farmville's 37 violent offences in
        # Cumberland County, population 9,664, which quintupled its count; the town is seated in Prince
        # Edward. Splitting the counts between counties would invent a division the data does not contain,
        # so place the agency where its own published coordinates fall, and only when they land in one of
        # the counties it lists. All four resolve to the county the town is actually seated in.
        f = None
        if len(names) > 1 and a["lat"] is not None:
            hit = locality_at(a["lat"], a["lon"])
            if hit and hit["fips"] in {fips_for(n, idx) for n in names}:
                f = hit["fips"]
        if not f and names:
            f = fips_for(names[0], idx)
        if not f and a["lat"] is not None:
            hit = locality_at(a["lat"], a["lon"])
            f = hit["fips"] if hit else None
        if not f:
            continue
        g = agg.setdefault(f, {"violent": 0, "property": 0, "pop_covered": 0, "agencies": 0, "gaps": [], "no_pop_offenses": 0})
        if (a["population"] or 0) > 0:
            g["agencies"] += 1
            if a["violent_months"] == 12 and a["property_months"] == 12:
                g["violent"] += a["violent_2025"] or 0
                g["property"] += a["property_2025"] or 0
                g["pop_covered"] += a["population"]
            else:
                g["gaps"].append({"agency": a["agency"], "population": a["population"], "months": a["violent_months"]})
        else:
            g["no_pop_offenses"] += (a["violent_2025"] or 0)
    out = {}
    for f, g in agg.items():
        p = pop.get(f)
        big_gap = [x for x in g["gaps"] if p and x["population"] >= 0.25 * p]
        rate = None
        reason = None
        if big_gap:
            reason = f"{big_gap[0]['agency']} reported {big_gap[0]['months']} of 12 months for 2025 to the FBI."
        elif g["pop_covered"] <= 0:
            reason = "No reporting agency with a population here."
        else:
            rate = round(1000 * g["violent"] / g["pop_covered"], 2)
        # "Unknown is never zero" has to hold in the stored data too, not just in the score: where no
        # agency produced a usable year, the counts are null and the reason says why.
        out[f] = {"violent_2025": g["violent"] if rate is not None else None,
                  "property_2025": g["property"] if rate is not None else None,
                  "pop_covered": g["pop_covered"],
                  "coverage": round(min(1.0, g["pop_covered"] / p), 3) if p else None,
                  "violent_per_1k": rate, "property_per_1k": round(1000 * g["property"] / g["pop_covered"], 2) if rate is not None else None,
                  "unknown_reason": reason, "gaps": g["gaps"]}
    return out



def incident_tiles() -> tuple[dict, dict, dict]:
    """Block-level incident counts for the two cities that publish them, as ~1 km (0.01 degree) tiles.

    Captured by main's session-3 run (data_raw/city_incidents_MANIFEST.json describes exactly how) and kept
    through the session 3 / session 4 merge, because no other Virginia source is finer than a whole city.
    Only Norfolk and Charlottesville publish incident-level data we could geocode; everywhere else stays on
    the FBI's per-agency yearly figures, and the score says which it used.

    Returns (cities, tiles, scale): tiles are keyed "t{lat*100}_{lon*100}" with v/p/e counts, and scale is
    the good/bad pair for a 3x3 tile neighbourhood, taken from the recorded tiles themselves.
    """
    raw = load("city_incidents_tiles_2026-10-24.json")
    classes = json.loads((ROOT / "footing" / "static" / "va_offense_classes.json").read_text(encoding="utf-8"))
    cities, tiles = {}, {}
    for c in raw["cities"]:
        total = {"v": 0, "p": 0, "e": 0}
        for t in c["tiles"]:
            tiles[t["tile"]] = {"lat": t["lat"], "lon": t["lon"], "fips": c["fips"],
                                "v": t["violent"], "p": t["property"], "e": t["enforcement"]}
            total["v"] += t["violent"]
            total["p"] += t["property"]
            total["e"] += t["enforcement"]
        placed = c["placed"]
        if total["v"] + total["p"] + total["e"] != placed:
            raise SystemExit(f"{c['name']}: tile counts {total} do not add up to placed={placed}")
        cities[c["fips"]] = {"name": c["name"], "agency": c["agency"], "source_url": c["source_url"],
                             "license": c["license"], "window_start": raw["window_start"],
                             "latest_date": c["latest_date"], "records_in_window": c["records_in_window"],
                             "used": c["used"], "placed": placed, "not_placed": c["not_placed"],
                             "by_class": c["by_class"], "tile_count": len(c["tiles"])}
    # How many violent incidents in a 3x3 block of tiles (about 3 km across) counts as a lot? Take it from
    # the recorded tiles rather than a round number: 0 is the best case, the 90th percentile is the worst.
    sums = []
    for key, t in tiles.items():
        i, j = (int(x) for x in key[1:].split("_"))
        sums.append(sum(tiles.get(f"t{i + di}_{j + dj}", {}).get("v", 0) for di in (-1, 0, 1) for dj in (-1, 0, 1)))
    sums.sort()
    bad = float(sums[min(len(sums) - 1, int(round(0.9 * (len(sums) - 1))))]) if sums else 0.0
    scale = {"good": 0, "bad": bad,
             "rule": "violent incidents in the 3x3 tiles around a point (about 3 km across) over 12 months; "
                     "bad = 90th percentile of the recorded tiles"}
    return cities, tiles, {"classes_about": classes["about"], "scale": scale}


def build() -> dict:
    idx = name_index()
    pops = {k: v[1] for k, v in load("census_pep_v2025_va.json")["out"].items()}
    fmr = load("hud_fmr_fy2026_va.json")
    coc_of = {k: v.split("|")[0] for k, v in load("hud_coc_by_locality.json")["out"].items()}
    pit = {r["CoC Number"]: r for r in load("hud_pit_2024_2025_va_coc.json")["2025"]}
    hic = {r["CoC Number"]: r for r in load("hud_hic_2025_va_coc.json")["rows"]}
    osm = load("osm_va_services_2026-10-25.json")
    snap_rows = load("usda_snap_retailers_va_by_county.json")["rows"]
    ice = load("ice_287g_va_2026-10-24.json")["rows"]
    crime = crime_by_locality(idx, pops)
    inc_cities, inc_tiles, inc_meta = incident_tiles()

    snap: dict[str, dict] = {}
    for county, kind, n in snap_rows:
        f = fips_for(county, idx)
        if not f:
            raise SystemExit(f"SNAP county not matched: {county}")
        s = snap.setdefault(f, {"total": 0, "full_grocery": 0, "restaurant_meals": 0})
        s["total"] += n
        if kind in ("Supermarket", "Super Store", "Grocery Store"):
            s["full_grocery"] += n
        if kind == "Restaurant Meals Program":
            s["restaurant_meals"] += n

    enforce: dict[str, list] = {}
    for r in ice:
        county = r["county"].strip()
        f = fips_for(county.replace(" County", "").replace(" COUNTY", ""), idx)
        if county.lower().startswith("hopewell"):          # ICE lists "Hopewell County"; Hopewell is an independent city
            f = "51670"
        if not f:
            raise SystemExit(f"287(g) county not matched: {county}")
        enforce.setdefault(f, []).append({"agency": r["agency"].strip(), "model": r["model"].strip(), "signed": r["signed"]})

    points: dict[str, list] = {}
    for kind, lat, lon, f, name, hours, phone, osm_id in osm["pts"]:
        points.setdefault(f, []).append({"kind": kind, "lat": lat, "lon": lon, "name": name or None,
                                         "hours": hours or None, "phone": phone or None, "osm": osm_id})

    rows = {}
    for d in localities():
        f = d["fips"]
        code = coc_of[f]
        p, h = pit[code], hic[code]
        carried = p["Count Types"] == "Sheltered-Only Count"
        rows[f] = {
            "name": d["name"], "kind": d["kind"], "center": list(d["center"]), "pop_2025": pops[f],
            "fmr": {"area": fmr[f]["area"], "by_bedrooms": fmr[f]["fmr"]},
            "coc": {"code": code, "name": p["CoC Name"], "pit_total": p["Overall Homeless"],
                    "sheltered": p["Sheltered Total Homeless"], "unsheltered": p["Unsheltered Homeless"],
                    "unsheltered_carried_from_2024": carried,
                    "people_in_families": p["Overall Homeless People in Families"],
                    "beds_year_round": h["Total Year-Round Beds (ES, TH, SH)"],
                    "beds_family": h["Total Beds for Households with Children (ES, TH, SH)"],
                    "beds_adult_only": h["Total Beds for Households without Children (ES, TH, SH)"],
                    "seasonal_beds": h["Total Seasonal Beds (ES)"], "overflow_beds": h["Total Overflow Beds (ES)"]},
            "services": {"osm": osm["counts"].get(f, {}), "snap": snap.get(f, {"total": 0, "full_grocery": 0, "restaurant_meals": 0}),
                         "fare_free_transit": ({"system": FARE_FREE[f][0], "source": FARE_FREE[f][1]} if f in FARE_FREE else None)},
            "help_points": points.get(f, []),
            "local_rule": ({"status": LOCAL_RULES[f][0], "note": LOCAL_RULES[f][1], "source": LOCAL_RULES[f][2],
                            "score": RULE_SCORE.get(LOCAL_RULES[f][0])} if f in LOCAL_RULES else None),
            "enforcement_287g": enforce.get(f, []),
            "crime": crime.get(f),
        }
    return {
        "about": "Virginia localities for the Footing Fit Score. Every field cites SOURCES. null = we could not get it "
                 "(the reason is next to it). A missing local rule means 'not checked yet', never 'no rule'.",
        "built_on": READ_ON,
        "state": {"camping_law": {"status": "none_statewide",
                                  "note": "No statewide camping ban. HB1394 (2026), which would have stopped cities from "
                                          "punishing people for sleeping in public, was continued to 2027.",
                                  "source": "hb1394_2026"},
                  "state_287g": {"status": "ended", "note": "State agencies' 287(g) agreements ended by Executive "
                                 "Directive One (Feb 2026). Sheriffs' and towns' agreements continue.", "source": "va_ed1_2026"},
                  "min_wage": 12.77},
        "field_sources": {"center": "census_tiger", "pop_2025": "census_pep", "fmr": "hud_fmr", "coc": "hud_coc_areas",
                          "coc.pit": "hud_pit", "coc.beds": "hud_hic", "services.osm": "osm", "services.snap": "usda_snap",
                          "services.fare_free_transit": "apta_fare_free", "help_points": "osm",
                          "local_rule": "local_rule.source", "enforcement_287g": "ice_287g", "crime": "fbi_cde", "crime.months": "fbi_cde_second",
                          "incident_tiles": "city_incidents"},
        "sources": SOURCES,
        "incident_cities": inc_cities,
        "incident_tiles": inc_tiles,
        "incident_scale": inc_meta["scale"],
        "offense_classes_about": inc_meta["classes_about"],
        "localities": rows,
    }


def validate(data: dict) -> list[str]:
    errs = []
    L = data["localities"]
    if len(L) != 133:
        errs.append(f"expected 133 localities, got {len(L)}")
    if sum(1 for x in L.values() if x["kind"] == "city") != 38:
        errs.append("expected 38 independent cities")
    by_coc = {}
    for f, x in L.items():
        by_coc[x["coc"]["code"]] = x["coc"]
        b = x["fmr"]["by_bedrooms"]
        if len(b) != 5 or any(v <= 0 for v in b) or b[4] < b[0]:
            errs.append(f"{f}: odd FMR {b}")
        if not x["pop_2025"] or x["pop_2025"] < 2000:
            errs.append(f"{f}: odd population {x['pop_2025']}")
        rule = x["local_rule"]
        if rule and rule["status"] == "checked_none_found":
            # A search that found nothing has nothing to cite; it must also never carry a score.
            if rule["source"] is not None or rule["score"] is not None:
                errs.append(f"{f}: a 'checked, none found' rule must have no source and no score")
        elif rule and rule["source"] not in data["sources"]:
            errs.append(f"{f}: local rule cites unknown source")
    if len(by_coc) != 16:
        errs.append(f"expected 16 CoCs, got {len(by_coc)}")
    total = sum(c["pit_total"] for c in by_coc.values())
    unsh = sum(c["unsheltered"] for c in by_coc.values())
    if (total, unsh) != (7240, 1349):                 # HUD's 2025 Virginia state totals (state_policy.json)
        errs.append(f"PIT by CoC {total}/{unsh} != Virginia state total 7240/1349")
    if abs(sum(x["pop_2025"] for x in L.values()) - 8_880_107) > 0:
        errs.append("Census population does not sum to the Vintage 2025 state total used at build time")
    if sum(len(x["enforcement_287g"]) for x in L.values()) != 22:
        errs.append("expected 22 Virginia 287(g) agreements in the ICE file")
    for k, s in data["sources"].items():
        if not s["url"].startswith("https://"):
            errs.append(f"source {k} url")
    return errs


def main(argv):
    data = build()
    errs = validate(data)
    if "--check" in argv:
        committed = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
        if committed != json.loads(json.dumps(data)):
            errs.append("committed va_localities.json differs from a fresh build (run scripts/build_va_localities.py)")
        if errs:
            print("\n".join(errs)); sys.exit(1)
        print("Virginia locality data OK"); return
    if errs:
        print("\n".join(errs)); sys.exit(1)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(data['localities'])} localities, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
