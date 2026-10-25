"""Build footing/static/state_policy.json: one row per state + DC, every field cited.

Each table below is transcribed from ONE public source (listed in SOURCES with the date the source says it
was updated and the date we read it). Run:

    python scripts/build_state_policy.py            # writes footing/static/state_policy.json
    python scripts/build_state_policy.py --check    # validates only (also run by the test-suite)

Rules (same as the rest of Footing): a value we could not confirm is left out (null), never guessed. A
missing value means "not checked", not "no". Validation checks totals against the publisher's own
published totals, so a transcription slip fails loudly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "footing" / "static" / "state_policy.json"
READ_ON = "2026-10-24"

SOURCES = {
    "ilrc_enforcement": {
        "title": "ILRC State Map on Immigration Enforcement",
        "publisher": "Immigrant Legal Resource Center",
        "url": "https://www.ilrc.org/state-map-immigration-enforcement",
        "as_of": "2026-09-06", "read_on": READ_ON,
        "note": "9 tiers. 1 = most protective of immigrants, 9 = most far-reaching state laws committing local "
                "resources to immigration enforcement. Covers state legislation, not executive orders.",
    },
    "ncsl_dl": {
        "title": "States Offering Driver's Licenses to Immigrants",
        "publisher": "National Conference of State Legislatures",
        "url": "https://www.ncsl.org/immigration/states-offering-drivers-licenses-to-immigrants",
        "as_of": "2023-03-13", "read_on": READ_ON,
        "note": "19 states + DC issue a license or driving-privilege card without proof of lawful presence. "
                "No repeals reported; 2026 secondary sources still count 19 states + DC.",
    },
    "kff_medicaid_expansion": {
        "title": "Status of State Action on the Medicaid Expansion Decision",
        "publisher": "KFF",
        "url": "https://www.kff.org/affordable-care-act/state-indicator/state-activity-around-expanding-medicaid-under-the-affordable-care-act/",
        "as_of": "2026-10", "read_on": READ_ON,
    },
    "dol_min_wage": {
        "title": "State Minimum Wage Laws",
        "publisher": "U.S. Department of Labor, Wage and Hour Division",
        "url": "https://www.dol.gov/agencies/whd/minimum-wage/state",
        "as_of": "2026-07-01", "read_on": READ_ON,
        "note": "Basic rate for most employers. States with no or lower state rate use the federal $7.25.",
    },
    "nlihc_oor_2026": {
        "title": "Out of Reach 2026: The High Cost of Housing",
        "publisher": "National Low Income Housing Coalition",
        "url": "https://nlihc.org/oor",
        "as_of": "2026-07", "read_on": READ_ON,
        "note": "Two-bedroom Housing Wage = hourly full-time wage needed to afford a 2-BR at Fair Market Rent "
                "without paying more than 30% of income.",
    },
    "hud_pit_2025": {
        "title": "2007-2025 PIT Estimates by State (2025 AHAR Part 1)",
        "publisher": "U.S. Department of Housing and Urban Development",
        "url": "https://www.huduser.gov/portal/datasets/ahar/2025-ahar-part-1-pit-estimates-of-homelessness-in-the-us.html",
        "as_of": "2025-01 count, published 2026-05", "read_on": READ_ON,
        "note": "Read from the '2025' sheet of 2007-2025-PIT-Counts-by-State.xlsb. National total 745,652 "
                "matches HUD's published figure.",
    },
    "kff_state_health": {
        "title": "State Health Coverage for Immigrants and Implications for Health Coverage and Care",
        "publisher": "KFF",
        "url": "https://www.kff.org/racial-equity-and-health-policy/state-health-coverage-for-immigrants-and-implications-for-health-coverage-and-care/",
        "as_of": "2026-06-11", "read_on": READ_ON,
    },
    "nilc_state_food": {
        "title": "State-Funded Food Assistance Programs (Table)",
        "publisher": "National Immigration Law Center",
        "url": "https://www.nilc.org/resources/state_food/",
        "as_of": "2026-08-18", "read_on": READ_ON,
    },
    "camping_laws": {
        "title": "Statewide laws restricting camping/sleeping in public (compiled)",
        "publisher": "Stateline (2026-06-25); National Homelessness Law Center (2026-06-25); state statutes",
        "url": "https://stateline.org/2026/06/25/2-years-after-grants-pass-14-states-350-cities-have-tougher-laws-on-street-homelessness/",
        "as_of": "2026-06-25", "read_on": READ_ON,
        "note": "NHLC counts 14 states but does not publish the list in text; we include only the states we could "
                "confirm by name. Every other state is null = not checked, NOT 'no law'.",
    },
}

# ---- ILRC tiers (Sept 6, 2026) --------------------------------------------------------------------------
ILRC_TIERS = {
    1: ("Most protective", "IL OR"),
    2: ("Broad sanctuary protections", "CA CO ME NJ VT WA"),
    3: ("Meaningful, more limited protections", "CT DC MD MA NM NY VA"),
    4: ("Smaller steps", "DE HI MN NV RI"),
    5: ("No law either way", "AK KY MI NE PA WI"),
    6: ("Mandates participation or bans sanctuary policies", "KS MO MT NH ND OH SD UT WY"),
    7: ("Broad anti-sanctuary law", "AR GA ID IN SC TN"),
    8: ("Fairly comprehensive anti-immigrant law", "AL AZ IA LA MS NC OK WV"),
    9: ("Most far-reaching enforcement laws", "FL TX"),
}

# ---- Driver's license regardless of status (NCSL): state -> (year enacted, form) ----------------------
DL_ALL = {
    "CA": (2013, "license"), "CO": (2013, "license"), "CT": (2013, "license"), "DE": (2015, "driving privilege card"),
    "HI": (2015, "license"), "IL": (2012, "license"), "MD": (2013, "license"), "MA": (2022, "license"),
    "MN": (2023, "license"), "NV": (2013, "driver authorization card"), "NJ": (2019, "license"),
    "NM": (2003, "license"), "NY": (2019, "license"), "OR": (2019, "license"), "RI": (2022, "license"),
    "UT": (2005, "driving privilege card"), "VT": (2013, "privilege card"), "VA": (2020, "driving privilege card"),
    "WA": (1993, "license"), "DC": (2013, "limited-purpose license"),
}

# ---- Medicaid expansion NOT adopted (KFF, Oct 2026). All other 40 states + DC: adopted and implemented. --
MEDICAID_NOT_ADOPTED = set("AL FL GA KS MS SC TN TX WI WY".split())

# ---- DOL basic minimum wage (July 1, 2026). Regional rates: we store the statewide/standard rate. --------
MIN_WAGE = {
    "AL": 7.25, "AK": 14.00, "AZ": 15.15, "AR": 11.00, "CA": 16.90, "CO": 15.16, "CT": 16.94, "DE": 15.00,
    "DC": 18.40, "FL": 14.00, "GA": 7.25, "HI": 16.00, "ID": 7.25, "IL": 15.00, "IN": 7.25, "IA": 7.25,
    "KS": 7.25, "KY": 7.25, "LA": 7.25, "ME": 15.10, "MD": 15.00, "MA": 15.00, "MI": 13.73, "MN": 11.41,
    "MS": 7.25, "MO": 15.00, "MT": 10.85, "NE": 15.00, "NV": 12.00, "NH": 7.25, "NJ": 15.92, "NM": 12.00,
    "NY": 16.00, "NC": 7.25, "ND": 7.25, "OH": 11.00, "OK": 7.25, "OR": 15.55, "PA": 7.25, "RI": 16.00,
    "SC": 7.25, "SD": 11.85, "TN": 7.25, "TX": 7.25, "UT": 7.25, "VT": 14.42, "VA": 12.77, "WA": 17.13,
    "WV": 8.75, "WI": 7.25, "WY": 7.25,
}
MIN_WAGE_NOTES = {
    "NY": "$17.00 in NYC, Nassau, Suffolk and Westchester; $16.00 elsewhere (stored).",
    "OR": "$16.80 Portland metro; $14.55 non-urban counties; $15.55 standard (stored).",
    "OH": "$11.00 for employers with gross receipts of $405,000 or more.",
    "OK": "$7.25 for larger employers; federal $7.25 applies to most other workers.",
    "FL": "DOL table (July 1, 2026) shows $14.00; Florida's constitution schedules $15.00 from Sept 30, 2026.",
}

# ---- NLIHC Out of Reach 2026: (2-BR housing wage $/hr, hours/week at minimum wage) ----------------------
OOR_2026 = {
    "AL": (20.91, 115), "AK": (30.59, 87), "AZ": (32.87, 87), "AR": (20.82, 76), "CA": (52.79, 125),
    "CO": (36.44, 96), "CT": (38.98, 92), "DE": (32.20, 86), "DC": (43.19, 94), "FL": (37.93, 108),
    "GA": (29.84, 165), "HI": (49.38, 123), "ID": (27.12, 150), "IL": (30.36, 81), "IN": (24.13, 133),
    "IA": (21.39, 118), "KS": (21.70, 120), "KY": (21.64, 119), "LA": (21.88, 121), "ME": (32.32, 86),
    "MD": (37.60, 100), "MA": (48.59, 130), "MI": (25.53, 74), "MN": (28.92, 101), "MS": (20.01, 110),
    "MO": (22.19, 59), "MT": (29.97, 110), "NE": (23.08, 62), "NV": (33.33, 111), "NH": (39.24, 216),
    "NJ": (43.89, 110), "NM": (25.15, 84), "NY": (48.46, 121), "NC": (27.11, 150), "ND": (20.92, 115),
    "OH": (23.82, 87), "OK": (21.85, 121), "OR": (33.43, 86), "PA": (28.87, 159), "RI": (33.95, 85),
    "SC": (25.99, 143), "SD": (21.03, 71), "TN": (26.21, 145), "TX": (29.93, 165), "UT": (30.42, 168),
    "VT": (32.38, 90), "VA": (33.37, 105), "WA": (39.84, 93), "WV": (19.23, 88), "WI": (24.76, 137),
    "WY": (20.76, 115),
}

# ---- HUD 2025 PIT by state: (overall, sheltered, unsheltered) ------------------------------------------
PIT_2025_RAW = (
    "AK,2655,2081,574;AL,4137,1912,2225;AR,2720,1274,1446;AZ,15259,6762,8497;CA,181934,66351,115583;"
    "CO,16687,11614,5073;CT,3735,2902,833;DC,5138,4340,798;DE,1573,1406,167;FL,27888,14726,13162;"
    "GA,12284,5631,6653;HI,6828,2786,4042;IA,2816,2205,611;ID,2697,1349,1348;IL,14576,12502,2074;"
    "IN,6675,5143,1532;KS,2658,1830,828;KY,5789,3791,1998;LA,3688,2136,1552;MA,28311,26563,1748;"
    "MD,7120,6219,901;ME,2413,2132,281;MI,10155,8439,1716;MN,8392,6571,1821;MO,8345,5713,2632;"
    "MS,1245,726,519;MT,2263,1557,706;NC,15512,10712,4800;ND,861,695,166;NE,2656,2369,287;NH,2406,1754,652;"
    "NJ,13714,11728,1986;NM,4683,2537,2146;NV,9905,4991,4914;NY,145560,139704,5856;OH,12196,9718,2478;"
    "OK,5174,3239,1935;OR,27202,10702,16500;PA,14834,11952,2882;RI,2373,1755,618;SC,4398,2975,1423;"
    "SD,1450,1087,363;TN,8850,4774,4076;TX,28031,15870,12161;UT,4584,3538,1046;VA,7240,5891,1349;"
    "VT,3386,3116,270;WA,31721,14688,17033;WI,5243,4767,476;WV,1925,1042,883;WY,535,437,98"
)
# Territories in the same sheet (kept only so the national total can be checked against HUD's figure).
PIT_2025_TERRITORIES = {"GU": (861, 82, 779), "PR": (2060, 478, 1582), "VI": (311, 70, 241)}
HUD_PUBLISHED_TOTAL_2025 = 745_652

# ---- KFF state-funded coverage regardless of immigration status (June 2026) ----------------------------
HEALTH_CHILDREN_ALL = {
    "CA": "", "CO": "Enrollment capped (25,000 or funding); cutbacks planned Jan 2027.",
    "CT": "New enrollment for children under 16; can stay enrolled through 18.", "IL": "", "ME": "", "MA": "",
    "MN": "", "NJ": "", "NY": "", "OR": "", "RI": "", "UT": "New enrollment in funded open-enrollment windows.",
    "VT": "", "WA": "", "DC": "",
}
HEALTH_ADULTS_ALL = {  # value: (status, note); status: open | limited | closed
    "CA": ("closed", "Adult enrollment closed Jan 2026 (except pregnant adults and former foster youth under 26)."),
    "CO": ("limited", "OmniSalud subsidized Marketplace plans; cap cut to 6,700, lottery-based new enrollment."),
    "DC": ("limited", "New enrollment only ages 21-25 since Oct 2025; all 21+ coverage planned to end by Oct 2027."),
    "IL": ("closed", "Adults 42-64 program ended July 2025; 65+ enrollment paused since 2023."),
    "NY": ("limited", "Ages 65+ only."),
    "OR": ("open", "Healthier Oregon covers adults regardless of status (age range not stated by KFF)."),
    "WA": ("limited", "Program up to 138% FPL closed to new enrollment; Cascade Care subsidies continue, funding limited."),
    "MN": ("closed", "Adult (18+) coverage ended Jan 2026."),
}

# ---- NILC state-funded food assistance for immigrants not eligible for SNAP (Aug 18, 2026) --------------
STATE_FOOD = {
    "CA": ("lawful", "CFAP: qualified/lawfully present groups; adults 55+ regardless of status from Oct 2027."),
    "IL": ("narrow", "People with pending/approved T or U visas and derivatives; some asylum applicants."),
    "ME": ("lawful", "Immigrants barred by 1996 law, some PRUCOLs (asylum applicants, TPS, SIJ); hardship criteria."),
    "MN": ("narrow", "MFAP: immigrants 50+ ineligible for SNAP only because of the 1996 law."),
    "NM": ("one_time", "One-time payment (6 months of SNAP) for qualified immigrants cut off by H.R. 1 in 2026."),
    "WA": ("lawful", "FAP: qualified immigrants, PRUCOLs, lawfully present; trafficking/crime survivors; some asylum applicants."),
}

# ---- Statewide camping laws we could confirm by name (others: not checked) ------------------------------
CAMPING = {
    "FL": ("in_effect", "HB 1365 (2024): bans public sleeping/camping; counties may designate areas. Effective Oct 1, 2024."),
    "TX": ("in_effect", "HB 1925 (2021): camping in unapproved public places is a Class C misdemeanor."),
    "TN": ("in_effect", "2022 law: camping on state property is a Class E felony (Tenn. Code 39-14-414)."),
    # GA and OK do not ban camping statewide; their 'Safe Neighborhood' laws pressure cities to enforce
    # local bans (owners can seek compensation). Scored separately from a statewide ban.
    "GA": ("enforcement_mandate", "'Safe Neighborhood' law: owners can seek compensation if localities don't enforce camping laws."),
    "OK": ("enforcement_mandate", "'Safe Neighborhood' law: owners can seek compensation if localities don't enforce camping laws."),
    "LA": ("in_effect", "2026 law making unauthorized public camping a crime; adds a Homelessness Court diversion."),
    "IN": ("in_effect", "2026 law banning unauthorized camping, sleeping and sheltering on state or local public land (from July 2026)."),
    "KY": ("contested", "HB 5 (2024) unlawful-camping offense; NHLC reports a court ruled the statewide ban unconstitutional."),
    # Virginia (checked in depth in session 4, see build_va_localities.py): no statewide ban; cities and counties
    # set their own rules. Scored 75, not 100, because local bans exist (Hampton, Bristol, Roanoke).
    "VA": ("none_statewide", "No statewide camping ban; some cities ban it (Hampton, Bristol) or limit it (Roanoke). HB1394 (2026), which would have stopped cities from punishing sleeping outside, was continued to 2027."),
}

NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11",
    "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30",
    "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
}


def pit_table() -> dict[str, tuple[int, int, int]]:
    out = {}
    for row in PIT_2025_RAW.split(";"):
        st, a, b, c = row.split(",")
        out[st] = (int(a), int(b), int(c))
    return out


def build() -> dict:
    tier_of = {st: (n, label) for n, (label, sts) in ILRC_TIERS.items() for st in sts.split()}
    pit = pit_table()
    states = {}
    for st, name in NAMES.items():
        hw, hrs = OOR_2026[st]
        total, sheltered, unsheltered = pit[st]
        dl = DL_ALL.get(st)
        ha = HEALTH_ADULTS_ALL.get(st)
        food = STATE_FOOD.get(st)
        camp = CAMPING.get(st)
        states[st] = {
            "name": name, "fips": FIPS[st],
            "enforcement_tier": tier_of[st][0], "enforcement_label": tier_of[st][1],
            "drivers_license_all": {"year": dl[0], "form": dl[1]} if dl else False,
            "medicaid_expansion": st not in MEDICAID_NOT_ADOPTED,
            "min_wage": MIN_WAGE[st], "min_wage_note": MIN_WAGE_NOTES.get(st),
            "housing_wage_2br": hw, "oor_hours_at_min_wage": hrs,
            "pit_total": total, "pit_sheltered": sheltered, "pit_unsheltered": unsheltered,
            "unsheltered_share": round(unsheltered / total, 4),
            "health_children_all": ({"note": HEALTH_CHILDREN_ALL[st] or None} if st in HEALTH_CHILDREN_ALL else False),
            "health_adults_all": ({"status": ha[0], "note": ha[1]} if ha else False),
            "state_food_immigrants": ({"scope": food[0], "note": food[1]} if food else False),
            # camping: confirmed laws only; None = we did not confirm either way
            "camping_law": ({"status": camp[0], "note": camp[1]} if camp else None),
        }
    return {
        "about": "State policy facts that change where a person can land. Every field cites SOURCES. "
                 "False = the source's complete list does not include this state. "
                 "null = not checked (never read as 'no').",
        "built_on": READ_ON,
        "field_sources": {
            "enforcement_tier": "ilrc_enforcement", "drivers_license_all": "ncsl_dl",
            "medicaid_expansion": "kff_medicaid_expansion", "min_wage": "dol_min_wage",
            "housing_wage_2br": "nlihc_oor_2026", "oor_hours_at_min_wage": "nlihc_oor_2026",
            "pit_total": "hud_pit_2025", "pit_sheltered": "hud_pit_2025", "pit_unsheltered": "hud_pit_2025",
            "unsheltered_share": "hud_pit_2025", "health_children_all": "kff_state_health",
            "health_adults_all": "kff_state_health", "state_food_immigrants": "nilc_state_food",
            "camping_law": "camping_laws",
        },
        "sources": SOURCES,
        "states": states,
    }


def validate(data: dict) -> list[str]:
    errs = []
    s = data["states"]
    if len(s) != 51:
        errs.append(f"expected 51 jurisdictions, got {len(s)}")
    tiers = [x["enforcement_tier"] for x in s.values()]
    if sorted({t for t in tiers}) != list(range(1, 10)):
        errs.append("ILRC tiers must cover 1..9")
    if sum(1 for x in s.values() if x["drivers_license_all"]) != 20:
        errs.append("NCSL: expected 19 states + DC with licenses regardless of status")
    if sum(1 for x in s.values() if not x["medicaid_expansion"]) != 10:
        errs.append("KFF: expected 10 non-expansion states")
    if sum(1 for x in s.values() if x["health_children_all"]) != 15:
        errs.append("KFF: expected 15 jurisdictions covering children regardless of status")
    total = sum(x["pit_total"] for x in s.values()) + sum(v[0] for v in PIT_2025_TERRITORIES.values())
    if total != HUD_PUBLISHED_TOTAL_2025:
        errs.append(f"PIT total {total} != HUD published {HUD_PUBLISHED_TOTAL_2025}")
    for st, x in s.items():
        if x["pit_sheltered"] + x["pit_unsheltered"] != x["pit_total"]:
            errs.append(f"{st}: sheltered + unsheltered != total")
        # NLIHC's hours column must agree with housing wage / minimum wage (catches transcription slips).
        implied = 40 * x["housing_wage_2br"] / x["min_wage"]
        if abs(implied - x["oor_hours_at_min_wage"]) > 1.5:
            errs.append(f"{st}: OOR hours {x['oor_hours_at_min_wage']} vs implied {implied:.1f}")
        if not (7.25 <= x["min_wage"] <= 20):
            errs.append(f"{st}: implausible minimum wage {x['min_wage']}")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    data = build()
    errs = validate(data)
    for e in errs:
        print("ERROR:", e)
    if errs:
        return 1
    if not args.check:
        OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)} ({len(data['states'])} jurisdictions)")
    else:
        print("state policy data OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
