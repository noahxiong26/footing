"""Footing Virginia Fit: scores each of Virginia's 133 localities (95 counties + 38 independent cities) for one person.

Python twin of footing/web/vafit.js. The phone runs the JS so a person's status, household and priorities never
leave the device; this copy serves the API, the CLI and the tests. tests/test_vafit.py runs both on the same inputs
and requires identical output, so change them together.

Components (0-100, or None = Unknown and NOT counted; see docs/RATING_FORMULA.md, "Virginia Fit"):
  shelter    share of people outside + shelter beds per person for the local Continuum of Care (HUD PIT/HIC Jan 2025)
  rent       hours of minimum-wage work a week for HUD's fair market rent at the size the person needs (FY2026)
  services   full-service SNAP grocers per 10k, Restaurant Meals SNAP stores, OSM help places per 10k, how many places
             there are to go at all (log scale), fare-free buses
  laws       local rules on sleeping/camping outside (only rules we confirmed from the code or council record)
  safety     287(g) agreements with ICE covering this place (only when the person's status puts them at risk)
  crime      FBI-reported violent crime per 1,000 people, 2025 (opt-in only: off unless the person turns it on)
  community  ratings from people who have been here
Weights are Rank-Order Centroid weights of the person's priority order. Unknown parts drop out; the rest renormalize.
Confidence = sum of weight x freshness over the known parts, so missing or stale data lowers it visibly. Shelter
freshness is 0.7 where the count covers only this place, 0.6 for 2-10 places, 0.5 for the Balance of State CoC. Small places'
per-capita counts are shrunk toward the Virginia rate as if 25,000 more people lived there.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from . import va as vageo
from .fit import gamma, js_round, linear, load_eligibility, mulberry32, roc_weights, round1, round3, safety_applies

STATIC = Path(__file__).resolve().parent / "static"
COMPONENTS = ["shelter", "rent", "services", "laws", "safety", "crime", "community"]
FRESHNESS = {"shelter": 0.7, "rent": 0.95, "services": 0.6, "laws": 0.6, "safety": 0.9, "crime": 0.7}
BEDROOM_WORD = ["studio", "1-bedroom", "2-bedroom", "3-bedroom", "4-bedroom"]
SERVICE_WEIGHTS = {"grocery": 0.3, "help": 0.2, "choice": 0.2, "transit": 0.2, "meals": 0.1}
HELP_KINDS = ["food_bank", "soup_kitchen", "shelter", "day_center", "clinic", "library", "toilets", "shower",
              "drinking_water", "laundry"]


SHRINK_POP = 25000  # small places: per-capita rates are pulled toward the Virginia rate as if 25,000 more people lived there
BIG_COC = 10        # a Continuum of Care covering more localities than this says little about any one town


@lru_cache(maxsize=1)
def load_va() -> dict:
    return json.loads((STATIC / "va_localities.json").read_text(encoding="utf-8"))


def state_totals(va) -> dict:
    """Statewide sums (summed in FIPS order so both engines get the same floats)."""
    t = {"pop": 0, "grocery": 0, "help": 0, "coc_size": {}}
    for f in sorted(va["localities"]):
        loc = va["localities"][f]
        osm = loc["services"].get("osm") or {}
        t["pop"] += loc["pop_2025"]
        t["grocery"] += loc["services"]["snap"]["full_grocery"]
        for k in HELP_KINDS:
            t["help"] += osm.get(k) or 0
        code = loc["coc"]["code"]
        t["coc_size"][code] = t["coc_size"].get(code, 0) + 1
    return t


def shrunk_rate(count, pop, state_count, state_pop) -> float:
    """Per-10k rate with small-place shrinkage toward the state rate (empirical-Bayes style)."""
    return (count + state_count / state_pop * SHRINK_POP) / (pop + SHRINK_POP) * 10000


def plural(n, one, many) -> str:
    return f"{n} {one if n == 1 else many}"


def num(x) -> str:
    """Print a number the way JavaScript's String() does for the values we use (3.0 -> '3', 1.28 -> '1.28')."""
    x = float(x)
    return str(int(x)) if x.is_integer() else repr(x)


def money(x) -> str:
    return "$" + f"{int(js_round(x)):,}"


def commas(n) -> str:
    return f"{int(js_round(n)):,}"


def bedrooms(profile: dict) -> int:
    """Bedrooms the person needs: their own choice (0-4), else 2 with kids, else 1."""
    hh = profile.get("household") or {}
    b = hh.get("bedrooms")
    if isinstance(b, (int, float)) and not isinstance(b, bool) and 0 <= b <= 4 and int(b) == b:
        return int(b)
    return 2 if hh.get("kids") else 1


def rent_component(loc, wage, profile):
    b = bedrooms(profile)
    rent = loc["fmr"]["by_bedrooms"][b]
    hours = rent * 12 / (0.30 * 52 * wage)
    return {"score": round1(linear(hours, 40, 140)),
            "reason": f"{money(rent)}/month for a {BEDROOM_WORD[b]} (HUD fair market rent, FY2026, {loc['fmr']['area']}). "
                      f"At Virginia's ${wage:.2f} minimum wage that takes {int(js_round(hours))} hours of work a week "
                      f"to keep rent at 30% of pay.",
            "parts": {"rent": rent, "bedrooms": b, "hours": round1(hours)}}


def shelter_component(loc, profile, tot):
    c = loc["coc"]
    size = tot["coc_size"][c["code"]]
    kids = bool((profile.get("household") or {}).get("kids"))
    share = c["unsheltered"] / c["pit_total"]
    parts = [round1(linear(share, 0.05, 0.65))]
    beds = c["beds_family"] if kids else c["beds_year_round"]
    people = c["people_in_families"] if kids else c["pit_total"]
    fam = "family " if kids else ""
    if people > 0:
        parts.append(round1(linear(beds / people, 1.0, 0.3)))
        bed_line = f"{commas(beds)} year-round {fam}shelter beds for {commas(people)}" + (" people in families" if kids else " people")
    else:
        bed_line = f"{commas(beds)} year-round {fam}shelter beds; no " + ("families were" if kids else "one was") + " counted without a home"
    total = 0.0
    for p in parts:
        total += p
    carried = " The outside count is from Jan 2024 (this area counted shelters only in 2025)." if c["unsheltered_carried_from_2024"] else ""
    return {"score": round1(total / len(parts)),
            "reason": f"{c['name']} (Jan 2025 count): {int(js_round(100 * share))}% of {commas(c['pit_total'])} people without homes "
                      f"slept outside; {bed_line}.{carried}"
                      + (f" This count covers {size} cities and counties together, so it says little about this one." if size > BIG_COC
                         else (f" This count covers {size} cities and counties; the beds may be in a neighboring one." if size > 1 else "")),
            "precision": 0.5 / 0.7 if size > BIG_COC else (0.6 / 0.7 if size > 1 else 1),
            "parts": {"outside_share": round3(share), "beds": beds, "people": people}}


def services_component(loc, tot):
    s, pop = loc["services"], loc["pop_2025"]
    parts, why = {}, []
    groc = s["snap"]["full_grocery"] / pop * 10000
    parts["grocery"] = round1(linear(shrunk_rate(s["snap"]["full_grocery"], pop, tot["grocery"], tot["pop"]), 3.0, 0.5))
    why.append(plural(s["snap"]["full_grocery"], "full grocery store takes", "full grocery stores take") + f" EBT ({num(round1(groc))} per 10,000 people)")
    rm = s["snap"]["restaurant_meals"]
    parts["meals"] = 100 if rm > 0 else 0
    why.append(plural(rm, "restaurant takes", "restaurants take") + " SNAP for hot meals" if rm > 0 else "no restaurants take SNAP for hot meals")
    osm = s.get("osm") or {}
    help_n = sum(osm.get(k) or 0 for k in HELP_KINDS)
    if help_n > 0:
        parts["help"] = round1(linear(shrunk_rate(help_n, pop, tot["help"], tot["pop"]), 8, 0.5))
        why.append(plural(help_n, "help place", "help places") + " mapped (food, clinics, restrooms, libraries, laundry...)")
    else:
        why.append("no help places mapped in OpenStreetMap (that usually means not mapped, so it is not counted)")
    options = s["snap"]["full_grocery"] + rm + help_n
    parts["choice"] = round1(linear(math.log10(options + 1), math.log10(151), math.log10(4)))
    if s.get("fare_free_transit"):
        parts["transit"] = 100
        why.append("free buses: " + s["fare_free_transit"]["system"])
    n = d = 0.0
    for k in ("grocery", "help", "choice", "transit", "meals"):
        if k in parts:
            n += SERVICE_WEIGHTS[k] * parts[k]
            d += SERVICE_WEIGHTS[k]
    small = (f" With {commas(pop)} people, these counts are pulled toward the Virginia average so one store does not swing the score."
             if pop < SHRINK_POP else "")
    return {"score": round1(n / d), "reason": "; ".join(why) + "." + small, "parts": parts}


NOT_SCORED = {"proposed": "not adopted.", "clearing_policy": "not an ordinance.",
              "checked_none_found": "we found no ban, but we did not read the whole code, so this is not a "
                                    "confirmed 'no ban'."}


def laws_component(loc, state):
    """Local rules on sleeping outside. Only a confirmed rule is scored; everything else is shown, not scored.

    There are three different things here and the person is told which one applies: a rule we confirmed and
    scored, a rule we found but cannot score (proposed, or a clearing policy that is not an ordinance, or a
    search that turned up nothing), and a place nobody has checked. A blank has never meant "no ban".
    """
    r = loc.get("local_rule")
    if r and r.get("score") is not None:
        return {"score": r["score"], "reason": r["note"], "source": r["source"]}
    if r:
        return {"score": None, "reason": r["note"] + " Not scored: " + NOT_SCORED.get(r["status"], "not an ordinance."),
                "source": r["source"]}
    return {"score": None, "reason": state["camping_law"]["note"] + f" We have not checked {loc['name']}'s own code yet, so this part is not counted."}


def safety_component(loc, state):
    g = loc.get("enforcement_287g") or []
    tfm = [x for x in g if x["model"] == "Task Force Model"]
    state_note = " " + state["state_287g"]["note"]
    if tfm:
        return {"score": 10, "reason": f"{tfm[0]['agency']} has a 287(g) task force agreement with ICE (signed {tfm[0]['signed']}): "
                                       f"local officers can question and arrest people about immigration status during regular work." + state_note}
    if g:
        return {"score": 40, "reason": f"{g[0]['agency']} has a 287(g) {g[0]['model'].lower()} agreement with ICE (signed {g[0]['signed']}): "
                                       f"people booked into jail can be held for ICE." + state_note}
    return {"score": 80, "reason": f"No local 287(g) agreement with ICE is listed for {loc['name']} (ICE list, Oct 2026). "
                                   f"Federal agents can still act anywhere." + state_note}


def tile_of(lat, lon):
    """The ~1 km tile a point falls in, keyed the way the builder writes them."""
    return f"t{math.floor(lat * 100)}_{math.floor(lon * 100)}"


def neighbourhood(va, tile, key):
    """Sum one incident class over the 3x3 tiles around `tile`, about 3 km across."""
    i, j = (int(x) for x in tile[1:].split("_"))
    total = 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            t = va["incident_tiles"].get(f"t{i + di}_{j + dj}")
            if t:
                total += t[key]
    return total


def crime_component(va, loc, fips, tile=None):
    """Reported crime, as local as the data allows.

    Norfolk and Charlottesville publish incident-level reports, so for a point in one of them we count the
    violent incidents in the 3x3 tiles around it (about 3 km across) over 12 months. Everywhere else, and
    for a whole locality with no point, it is the FBI's yearly figure for the city or county.

    Trespass, loitering, drunkenness and similar calls are counted separately and never as danger. They
    measure where police make contact, which is disproportionately where unhoused people already are, so
    scoring them as risk would push someone away from the places they are most likely to be.
    """
    if tile and fips in va.get("incident_cities", {}) and va["incident_tiles"].get(tile):
        city = va["incident_cities"][fips]
        sc = va["incident_scale"]
        v = neighbourhood(va, tile, "v")
        e = neighbourhood(va, tile, "e")
        reason = (f"{commas(v)} violent incident{'' if v == 1 else 's'} reported within about 1.5 km in the last "
                  f"12 months ({city['name']} police data); {commas(e)} trespass, loitering or disorderly calls "
                  f"nearby, which show where police make contact and are not counted as danger.")
        c = loc.get("crime") or {}
        if c.get("violent_per_1k") is not None:
            reason += f" Citywide: {num(c['violent_per_1k'])} violent crimes per 1,000 people (FBI, 2025)."
        return {"score": round1(linear(v, sc["good"], sc["bad"])), "coverage": 1.0, "level": "block",
                "freshness": 0.95, "reason": reason, "source": "city_incidents",
                "parts": {"level": "block", "violent": v, "enforcement": e,
                          "window_start": city["window_start"], "window_end": city["latest_date"]}}
    c = loc.get("crime")
    if not c or c.get("violent_per_1k") is None:
        return {"score": None, "coverage": 0, "level": "none",
                "reason": "Not counted: " + (c["unknown_reason"] if c and c.get("unknown_reason") else "no FBI data for this place.")}
    return {"score": round1(linear(c["violent_per_1k"], 1.0, 8.0)), "coverage": 0 if c.get("coverage") is None else c["coverage"],
            "level": "locality",
            "reason": f"{num(c['violent_per_1k'])} violent crimes reported to the FBI per 1,000 people in 2025 ({commas(c['violent_2025'])} reports). "
                      f"Reports reflect policing as well as danger; people without homes are more often victims than offenders."}


def components(va, fips, profile, community=None, tile=None):
    loc, state, out, tot = va["localities"][fips], va["state"], {}, state_totals(va)
    out["shelter"] = shelter_component(loc, profile, tot)
    out["rent"] = rent_component(loc, state["min_wage"], profile)
    out["services"] = services_component(loc, tot)
    out["laws"] = laws_component(loc, state)
    if safety_applies(profile["_elig"], profile):
        out["safety"] = safety_component(loc, state)
    if profile.get("show_crime"):
        out["crime"] = crime_component(va, loc, fips, tile)
    c = (community or {}).get(fips)
    if c and c.get("n", 0) > 0:
        out["community"] = {"score": c["score"], "n": c["n"], "freshness": c.get("freshness"),
                            "reason": f"{c['n']} rating{'' if c['n'] == 1 else 's'} from people who have been here"}
    else:
        out["community"] = {"score": None, "reason": "No ratings yet. Be the first to rate a place here."}
    _reason_data(va, fips, profile, out)
    return out


def _reason_data(va, fips, profile, out):
    """Presentation descriptors; never parse English or infer facts from scores.

    The English reason remains compatible. Recorded evidence notes are labelled
    explicitly by the translator, rather than silently falling back to English.
    """
    loc, state = va["localities"][fips], va["state"]

    def add(component, key, **values):
        out[component].setdefault("reason_data", {"version": 1, "segments": []})["segments"].append(
            {"key": key, "vars": values})

    def note(component, text):
        if text:
            add(component, "recorded_note", text=text)

    b = bedrooms(profile)
    rent = loc["fmr"]["by_bedrooms"][b]
    wage = state["min_wage"]
    add("rent", "rent", rent=money(rent), size=b, area=loc["fmr"]["area"],
        wage=f"{wage:.2f}", hours=int(js_round(rent * 12 / (0.30 * 52 * wage))))
    c = loc["coc"]
    kids = bool((profile.get("household") or {}).get("kids"))
    p = out["shelter"]["parts"]
    add("shelter", "shelter", name=c["name"], pct=int(js_round(100 * (c["unsheltered"] / c["pit_total"]))),
        total=commas(c["pit_total"]))
    add("shelter", ("beds_family" if kids else "beds") if p["people"] > 0 else
        ("beds_family_none" if kids else "beds_none"), beds=commas(p["beds"]), people=commas(p["people"]))
    if c["unsheltered_carried_from_2024"]:
        add("shelter", "carried")
    size = state_totals(va)["coc_size"][c["code"]]
    if size > 1:
        add("shelter", "coc_large" if size > BIG_COC else "coc_shared", n=size)
    s, pop = loc["services"], loc["pop_2025"]
    add("services", "grocery", n=s["snap"]["full_grocery"],
        rate=num(round1(s["snap"]["full_grocery"] / pop * 10000)))
    rm = s["snap"]["restaurant_meals"]
    add("services", "meals" if rm > 0 else "meals_none", n=rm)
    help_n = sum((s.get("osm") or {}).get(k) or 0 for k in HELP_KINDS)
    add("services", "help" if help_n > 0 else "help_none", n=help_n)
    if s.get("fare_free_transit"):
        add("services", "transit", system=s["fare_free_transit"]["system"])
    if pop < SHRINK_POP:
        add("services", "shrink", pop=commas(pop))
    r = loc.get("local_rule")
    if r:
        add("laws", "law_" + r["status"])
        note("laws", r["note"])
    else:
        add("laws", "law_unchecked", place=loc["name"])
        note("laws", state["camping_law"]["note"])
    if "safety" in out:
        g = loc.get("enforcement_287g") or []
        tfm = [a for a in g if a["model"] == "Task Force Model"]
        if tfm or g:
            a = (tfm or g)[0]
            add("safety", "safety_task" if tfm else "safety_jail", agency=a["agency"], signed=a["signed"])
            if not tfm:
                note("safety", a["model"])
        else:
            add("safety", "safety_none", place=loc["name"])
        note("safety", state["state_287g"]["note"])
    if "crime" in out:
        cc, crime = out["crime"], loc.get("crime") or {}
        if cc["level"] == "block":
            p, city = cc["parts"], va["incident_cities"][fips]
            add("crime", "crime_block", v=commas(p["violent"]), e=commas(p["enforcement"]),
                name=city["name"], start=p["window_start"], end=p["window_end"])
            if crime.get("violent_per_1k") is not None:
                add("crime", "crime_city", rate=num(crime["violent_per_1k"]))
        elif cc["level"] == "none":
            add("crime", "crime_unknown")
            note("crime", crime.get("unknown_reason"))
        else:
            add("crime", "crime_locality", rate=num(crime["violent_per_1k"]), n=commas(crime["violent_2025"]))
    n = out["community"].get("n")
    add("community", "community" if n else "community_none", n=n or 0)


def default_priorities(elig, profile):
    order = ["shelter", "rent", "services", "laws", "community"]
    risk = safety_applies(elig, profile)
    if risk == "high":
        order.insert(0, "safety")
    elif risk == "medium":
        order.insert(2, "safety")
    if (profile.get("situation") or {}).get("tonight") and order[0] != "shelter":
        order.remove("shelter")
        order.insert(0, "shelter")
    if profile.get("show_crime"):
        order.append("crime")
    return order


def priorities(elig, profile, comps):
    d = default_priorities(elig, profile)
    chosen = [k for k in (profile.get("priorities") or []) if k in d]
    for k in d:
        if k not in chosen:
            chosen.append(k)
    return [k for k in chosen if k in comps]


def _freshness(k, c):
    if c.get("freshness") is not None and k != "community":
        return c["freshness"]            # block-level crime carries its own; it is fresher than a yearly total
    if k == "community":
        return c.get("freshness") or 0.5
    if k == "crime":
        return FRESHNESS["crime"] * (c.get("coverage") or 0)
    if k == "shelter":
        return FRESHNESS["shelter"] * c.get("precision", 1)
    return FRESHNESS[k]


def aggregate(order, weights, comps):
    n = d = conf = 0.0
    for i, k in enumerate(order):
        c = comps[k]
        if c.get("score") is None:
            continue
        n += weights[i] * c["score"]
        d += weights[i]
        conf += weights[i] * _freshness(k, c)
    return {"score": n / d if d > 0 else None, "confidence": conf}


def _with_elig(profile, elig):
    p = dict(profile or {})
    p["_elig"] = elig
    return p


def fit_score(elig, va, fips, profile, community=None, tile=None):
    p = _with_elig(profile, elig)
    comps = components(va, fips, p, community, tile)
    order = priorities(elig, p, comps)
    w = roc_weights(len(order))
    agg = aggregate(order, w, comps)
    known = 0.0
    for i, k in enumerate(order):
        if comps[k].get("score") is not None:
            known += w[i]
    rows = []
    for i, k in enumerate(order):
        c = comps[k]
        has = c.get("score") is not None
        rows.append({"id": k, "weight": round3(w[i]), "share": round3(w[i] / known) if has and known > 0 else 0,
                     "contribution": round1(w[i] / known * c["score"]) if has and known > 0 else 0,
                     "score": c["score"] if has else None, "reason": c["reason"], "reason_data": c["reason_data"], "parts": c.get("parts"),
                     "source": c.get("source")})
    conf = round3(agg["confidence"])
    return {"fips": fips, "name": va["localities"][fips]["name"],
            "score": None if agg["score"] is None else round1(agg["score"]), "confidence": conf,
            "confidence_label": "high" if conf >= 0.7 else ("medium" if conf >= 0.45 else "low"), "components": rows}


def fit_point(elig, va, lat, lon, profile, community=None):
    """Score the locality a tapped or typed point falls in, using the point for everything it can tell us.

    Two things depend on where the point is. In Norfolk and Charlottesville, which publish incident-level
    reports, the crime part switches from the citywide FBI figure to the 3x3 tiles around the point. And
    the point's own doubt - rounded coordinates, a spot a few hundred metres from a city line - lowers
    CONFIDENCE and is listed in `point_issues`.

    Everything else is a property of the whole city or county, so it cannot change with the tap: rent,
    shelter beds and local law are the same anywhere inside the locality, and the score reflects that. An
    unusable point gets no score at all and says why (footing.va.check_point).
    Mirrored in footing/web/vapoint.js and footing/web/vafit.js.
    """
    pt = vageo.check_point(lat, lon)
    if not pt["ok"]:
        return {"fips": None, "name": None, "score": None, "confidence": 0.0, "confidence_label": "low",
                "components": [], "point": pt, "point_issues": [{"code": pt["code"], "text": pt["reason"]}]}
    out = fit_score(elig, va, pt["fips"], profile, community, tile=tile_of(float(lat), float(lon)))
    out["confidence"] = round3(out["confidence"] * pt["validity"])
    out["confidence_label"] = ("high" if out["confidence"] >= 0.7 else
                               "medium" if out["confidence"] >= 0.45 else "low")
    out["point"] = pt
    out["point_issues"] = [{"code": i["code"], "text": i["text"]} for i in pt["issues"]]
    return out


def rank_localities(elig=None, va=None, profile=None, community=None, robustness=True, samples=200, kappa=30, seed=11):
    """Score and rank all localities; with robustness, re-rank under seeded Dirichlet re-weightings (same as JS)."""
    elig = elig or load_eligibility()
    va = va or load_va()
    profile = profile or {}
    results = [fit_score(elig, va, f, profile, community) for f in sorted(va["localities"])]
    known = [r for r in results if r["score"] is not None]
    known.sort(key=lambda r: (-r["score"], r["fips"]))
    for i, r in enumerate(known):
        r["rank"] = i + 1
    if not robustness or not known:
        return results
    rand = mulberry32(seed)
    order = [c["id"] for c in known[0]["components"]]
    base = roc_weights(len(order))
    comps_by = {r["fips"]: {c["id"]: c for c in r["components"]} for r in known}
    ranks = {r["fips"]: [] for r in known}
    for _ in range(samples):
        g = [gamma(rand, max(0.5, kappa * w)) for w in base]
        tot = 0.0
        for x in g:
            tot += x
        w = [x / tot for x in g]
        scored = [(r["fips"], aggregate(order, w, comps_by[r["fips"]])["score"]) for r in known]
        scored.sort(key=lambda x: (-x[1], x[0]))
        for i, (f, _v) in enumerate(scored):
            ranks[f].append(i + 1)
    for r in known:
        rs = sorted(ranks[r["fips"]])
        r["rank_p10"] = rs[int(0.1 * (len(rs) - 1))]
        r["rank_p90"] = rs[int(0.9 * (len(rs) - 1))]
    return results


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Rank Virginia's 133 cities and counties for one person (offline).")
    ap.add_argument("--status", default=None, help="immigration status id from eligibility.json (stays local)")
    ap.add_argument("--kids", action="store_true", help="household includes children")
    ap.add_argument("--bedrooms", type=int, default=None, help="bedrooms needed, 0-4 (default 1, or 2 with kids)")
    ap.add_argument("--tonight", action="store_true", help="needs a place to sleep tonight")
    ap.add_argument("--crime", action="store_true", help="also count FBI-reported violent crime (off by default)")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    hh = {"kids": a.kids}
    if a.bedrooms is not None:
        hh["bedrooms"] = a.bedrooms
    profile = {"status": a.status, "household": hh, "situation": {"tonight": a.tonight}, "show_crime": a.crime}
    res = [r for r in rank_localities(profile=profile) if r["score"] is not None]
    res.sort(key=lambda r: r["rank"])
    if a.json:
        print(json.dumps(res[: a.top], indent=1))
        return
    for r in res[: a.top]:
        print(f"{r['rank']:>3}. {r['name']:<28} {r['score']:5.1f}  confidence {r['confidence_label']:<6} "
              f"(rank {r['rank_p10']}-{r['rank_p90']} if priorities shift)")


if __name__ == "__main__":
    main()
