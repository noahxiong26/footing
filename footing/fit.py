"""Fit Score reference implementation (Python mirror of footing/web/fit.js).

The phone runs the JavaScript version so a person's status never leaves the device. This module exists so
the formula can be tested, documented and run from the CLI, and tests/test_fit_parity.py proves both
implementations return identical results for the same inputs. Method and citations: docs/RATING_FORMULA.md.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

STATIC = Path(__file__).resolve().parent / "static"
COMPONENTS = ["access", "affordability", "shelter", "safety", "criminalization", "community"]
FRESHNESS = {"access": 0.9, "affordability": 0.9, "shelter": 0.7, "safety": 0.9, "criminalization": 0.6}
VALUE = {"yes": 1.0, "limited": 0.5, "varies": 0.5, "no": 0.0}
LAWFUL = ["citizen", "lpr5", "lpr", "refugee_asylee", "cuban_haitian", "cofa", "asylum_pending", "tps",
          "daca", "parole", "survivor", "visa"]
FULL_HEALTH = ["citizen", "lpr5", "cuban_haitian", "cofa"]
HUMANITARIAN = ["refugee_asylee", "tps", "asylum_pending", "parole", "survivor"]
STATE_FOOD_BY_STATUS = {
    "CA": {"lpr": 1.0, "refugee_asylee": 1.0, "parole": 1.0, "survivor": 1.0, "cuban_haitian": 1.0},
    "ME": {"lpr": 0.75, "refugee_asylee": 0.75, "asylum_pending": 0.75, "tps": 0.75, "parole": 0.75, "survivor": 0.75},
    "WA": {"lpr": 1.0, "refugee_asylee": 1.0, "parole": 1.0, "tps": 1.0, "survivor": 1.0, "asylum_pending": 0.5},
    "IL": {"survivor": 1.0, "asylum_pending": 0.5},
    "NM": {"refugee_asylee": 0.25, "survivor": 0.25, "parole": 0.25},
}
U32 = 0xFFFFFFFF


@lru_cache(maxsize=None)
def load_policy() -> dict:
    return json.loads((STATIC / "state_policy.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_eligibility() -> dict:
    return json.loads((STATIC / "eligibility.json").read_text(encoding="utf-8"))


def js_round(x: float) -> float:
    """JavaScript Math.round (half rounds up), not Python's banker's rounding."""
    return float(math.floor(x + 0.5))


def round1(x: float) -> float:
    return js_round(x * 10) / 10


def round3(x: float) -> float:
    return js_round(x * 1000) / 1000


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)


def linear(v: float, good: float, bad: float) -> float:
    return clamp(100 * (v - bad) / (good - bad), 0, 100)


def roc_weights(n: int) -> list[float]:
    """Rank-Order Centroid weights: w_k = (1/n) * sum_{i=k..n} 1/i (Barron & Barrett, 1996)."""
    out = []
    for k in range(1, n + 1):
        s = 0.0
        for i in range(k, n + 1):
            s += 1 / i
        out.append(s / n)
    return out


def status_info(elig: dict, status: str | None) -> dict | None:
    return next((s for s in elig["statuses"] if s["id"] == status), None)


def program_rule(elig: dict, program_id: str, status: str | None) -> dict:
    for p in elig["programs"]:
        if p["id"] != program_id:
            continue
        r = p["rule"].get(status) or p["rule"].get("*")
        if not r:
            return {"value": "varies", "note": ""}
        return {"value": r[0], "note": r[1]}
    return {"value": "varies", "note": ""}


def safety_applies(elig: dict, profile: dict) -> str | None:
    info = status_info(elig, profile.get("status"))
    risk = info["risk"] if info else "unknown"
    if risk in ("high", "medium"):
        return risk
    if (profile.get("household") or {}).get("mixed"):
        return "medium"
    return None


def food_access(elig, st, code, profile):
    s, hh, sit = profile.get("status"), profile.get("household") or {}, profile.get("situation") or {}
    rule = program_rule(elig, "snap", s)
    snap = VALUE[rule["value"]]
    why = "SNAP: " + rule["value"]
    if s == "lpr" and sit.get("disability"):
        snap, why = 1.0, "SNAP: yes (disability exemption from the 5-year wait)"
    elif s == "lpr" and hh.get("kids"):
        snap, why = max(snap, 0.75), "SNAP: children can get it now; adults wait 5 years"
    if snap == 0 and hh.get("mixed") and hh.get("kids"):
        snap, why = 0.5, "SNAP: U.S.-citizen children in the family can get it"
    state_val, state_why = 0.0, ""
    table = STATE_FOOD_BY_STATUS.get(code)
    if table and s in table:
        state_val = table[s]
        state_why = st["state_food_immigrants"]["note"] if st["state_food_immigrants"] else ""
    if code == "MN" and s == "lpr" and profile.get("age_band") in ("50_61", "62_plus"):
        state_val = 1.0
        state_why = st["state_food_immigrants"]["note"] if st["state_food_immigrants"] else ""
    if state_val > snap:
        return {"value": state_val, "why": "State food program: " + state_why}
    return {"value": snap, "why": why}


def health_access(elig, st, profile):
    s, hh, sit = profile.get("status"), profile.get("household") or {}, profile.get("situation") or {}
    base, base_why = 0.25, "ER care, health centers and emergency Medicaid only"
    child_or_preg = bool(hh.get("kids") or hh.get("pregnant"))
    if s in FULL_HEALTH:
        if st["medicaid_expansion"]:
            return {"value": 1.0, "why": "Medicaid expansion state: low-income adults qualify"}
        if child_or_preg or sit.get("disability"):
            return {"value": 0.75, "why": "No Medicaid expansion; kids, pregnancy or disability can still qualify"}
        return {"value": 0.35, "why": "No Medicaid expansion: most adults without kids fall in the coverage gap"}
    if s == "lpr":
        if child_or_preg:
            return {"value": 0.75, "why": "Many states cover lawfully residing kids and pregnant people now"}
        return {"value": 0.5, "why": "5-year Medicaid wait; Marketplace tax credits available"}
    adults, kids = st["health_adults_all"], st["health_children_all"]
    if adults:
        adult_val = 1.0 if adults["status"] == "open" else (0.6 if adults["status"] == "limited" else base)
        adult_why = "State program for adults: " + adults["status"] + ". " + adults["note"]
    else:
        adult_val, adult_why = base, base_why
    if s in HUMANITARIAN:
        if hh.get("kids"):
            if kids:
                return {"value": 1.0, "why": "State covers children regardless of status"}
            return {"value": 0.6, "why": "Many states cover lawfully residing children"}
        if hh.get("pregnant"):
            return {"value": 0.6, "why": "Many states cover lawfully residing pregnant people"}
        if adult_val > 0.35:
            return {"value": adult_val, "why": adult_why}
        return {"value": 0.35, "why": "No Medicaid for adults since Oct 1, 2026; limited Marketplace help"}
    if hh.get("kids") and kids:
        return {"value": 1.0, "why": "State covers children regardless of status"}
    if hh.get("pregnant"):
        return {"value": max(0.5, adult_val), "why": "Emergency Medicaid covers labor and delivery"}
    return {"value": adult_val, "why": adult_why}


def id_access(st, profile):
    s = profile.get("status")
    if s == "asylum_pending":
        return {"value": 0.75, "why": "Most states license people with a pending case and work permit"}
    if s in LAWFUL:
        return {"value": 1.0, "why": "Can get a state ID or license with your documents"}
    if st["drivers_license_all"]:
        return {"value": 1.0, "why": "State issues a " + st["drivers_license_all"]["form"] + " regardless of status"}
    return {"value": 0.0, "why": "State requires proof of lawful presence for a license"}


def access_component(elig, st, code, profile):
    if profile.get("status") == "undisclosed":
        return {"score": None, "reason": "You chose not to say your status, so this part is not scored. Help that is open to everyone is listed below."}
    if not profile.get("status"):
        return {"score": None, "reason": "Add your status (it stays on this phone) to see which programs you can use here."}
    order = ["id", "food", "health"] if (profile.get("situation") or {}).get("no_id") else ["food", "health", "id"]
    w = roc_weights(3)
    parts = {"food": food_access(elig, st, code, profile), "health": health_access(elig, st, profile),
             "id": id_access(st, profile)}
    total = 0.0
    for i in range(3):
        total += w[i] * parts[order[i]]["value"]
    return {"score": round1(100 * total),
            "reason": parts["food"]["why"] + "; " + parts["health"]["why"] + "; " + parts["id"]["why"],
            "parts": {k: round3(v["value"]) for k, v in (("food", parts["food"]), ("health", parts["health"]), ("id", parts["id"]))}}


def components(elig, policy, code, profile, community=None):
    st = policy["states"][code]
    out = {"access": access_component(elig, st, code, profile)}
    ratio = st["housing_wage_2br"] / st["min_wage"]
    out["affordability"] = {
        "score": round1(linear(ratio, 1.5, 5.0)),
        "reason": f"{st['oor_hours_at_min_wage']} hours/week at the ${st['min_wage']:.2f} minimum wage to afford a "
                  f"2-bedroom (${st['housing_wage_2br']:.2f}/hr needed)"}
    out["shelter"] = {
        "score": round1(linear(st["unsheltered_share"], 0.05, 0.65)),
        "reason": f"{int(js_round(100 * st['unsheltered_share']))}% of {st['pit_total']:,} people without homes slept "
                  f"outside (Jan 2025 count)"}
    risk = safety_applies(elig, profile)
    if risk:
        out["safety"] = {"score": round1(100 * (9 - st["enforcement_tier"]) / 8),
                         "reason": f"State law: {st['enforcement_label']} (tier {st['enforcement_tier']} of 9)"}
    elif profile.get("status") in (None, "", "undisclosed"):
        out["safety"] = {"score": None, "reason": "Shown only if your status could be affected by immigration enforcement."}
    camp = st["camping_law"]
    if camp and camp["status"] == "in_effect":
        out["criminalization"] = {"score": 0, "reason": "Statewide camping law: " + camp["note"]}
    elif camp and camp["status"] == "contested":
        out["criminalization"] = {"score": 50, "reason": "Statewide camping law in court: " + camp["note"]}
    else:
        out["criminalization"] = {"score": None, "reason": "Not checked: we have not confirmed a statewide camping law either way."}
    c = (community or {}).get(code)
    if c and c.get("n", 0) > 0:
        out["community"] = {"score": c["score"], "n": c["n"], "freshness": c.get("freshness"),
                            "reason": f"{c['n']} rating{'' if c['n'] == 1 else 's'} from people who have been here"}
    else:
        out["community"] = {"score": None, "reason": "No ratings yet. Be the first to rate a place here."}
    return out


def default_priorities(elig, profile):
    order = ["access", "affordability", "shelter", "criminalization", "community"]
    risk = safety_applies(elig, profile)
    if risk == "high":
        order.insert(0, "safety")
    elif risk == "medium":
        order.insert(2, "safety")
    if (profile.get("situation") or {}).get("tonight"):
        order.remove("shelter")
        order.insert(0, "shelter")
    return order


def priorities(elig, profile, comps):
    default = default_priorities(elig, profile)
    chosen = [k for k in (profile.get("priorities") or []) if k in default]
    for k in default:
        if k not in chosen:
            chosen.append(k)
    return [k for k in chosen if k in comps]


def aggregate(order, weights, comps):
    num = den = conf = 0.0
    for i, k in enumerate(order):
        c = comps[k]
        if c.get("score") is None:
            continue
        num += weights[i] * c["score"]
        den += weights[i]
        f = (c.get("freshness") or 0.5) if k == "community" else FRESHNESS[k]
        conf += weights[i] * f
    return {"score": num / den if den > 0 else None, "confidence": conf}


def fit_score(elig, policy, code, profile, community=None):
    comps = components(elig, policy, code, profile, community)
    order = priorities(elig, profile, comps)
    w = roc_weights(len(order))
    agg = aggregate(order, w, comps)
    rows = [{"id": k, "weight": round3(w[i]), "score": comps[k]["score"], "reason": comps[k]["reason"],
             "parts": comps[k].get("parts")} for i, k in enumerate(order)]
    conf = round3(agg["confidence"])
    return {"state": code, "name": policy["states"][code]["name"],
            "score": None if agg["score"] is None else round1(agg["score"]),
            "confidence": conf, "confidence_label": "high" if conf >= 0.7 else ("medium" if conf >= 0.45 else "low"),
            "components": rows}


# ---- seeded randomness (bit-identical to the JS mulberry32) -------------------------------------------
def mulberry32(seed: int):
    state = [seed & U32]

    def imul(a: int, b: int) -> int:
        return (a * b) & U32

    def rand() -> float:
        state[0] = (state[0] + 0x6D2B79F5) & U32
        t = state[0]
        t = imul(t ^ (t >> 15), t | 1)
        t = (t ^ ((t + imul(t ^ (t >> 7), t | 61)) & U32)) & U32
        return ((t ^ (t >> 14)) & U32) / 4294967296
    return rand


def _normal(rand):
    u1 = rand()
    if u1 < 1e-12:
        u1 = 1e-12
    u2 = rand()
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


def gamma(rand, alpha: float) -> float:
    """Marsaglia & Tsang (2000) gamma sampler, same call order as the JS version."""
    if alpha < 1:
        u = rand()
        if u < 1e-12:
            u = 1e-12
        return gamma(rand, alpha + 1) * u ** (1 / alpha)
    d = alpha - 1 / 3
    c = 1 / math.sqrt(9 * d)
    while True:
        x = _normal(rand)
        v = 1 + c * x
        if v <= 0:
            continue
        v = v * v * v
        u2 = rand()
        if u2 < 1e-12:
            u2 = 1e-12
        if math.log(u2) < 0.5 * x * x + d - d * v + d * math.log(v):
            return d * v


def rank_states(elig=None, policy=None, profile=None, community=None, robustness=True, samples=300, kappa=30, seed=7):
    elig = elig or load_eligibility()
    policy = policy or load_policy()
    profile = profile or {}
    codes = sorted(policy["states"])
    results = [fit_score(elig, policy, c, profile, community) for c in codes]
    known = [r for r in results if r["score"] is not None]
    known.sort(key=lambda r: (-r["score"], r["state"]))
    for i, r in enumerate(known):
        r["rank"] = i + 1
    if not robustness or not known:
        return results
    rand = mulberry32(seed)
    order = [c["id"] for c in known[0]["components"]]
    base = roc_weights(len(order))
    comps_by_state = {r["state"]: {c["id"]: c for c in r["components"]} for r in known}
    ranks = {r["state"]: [] for r in known}
    for _ in range(samples):
        g = [gamma(rand, max(0.5, kappa * w)) for w in base]
        tot = 0.0
        for x in g:
            tot += x
        w = [x / tot for x in g]
        scored = [(r["state"], aggregate(order, w, comps_by_state[r["state"]])["score"]) for r in known]
        scored.sort(key=lambda x: (-x[1], x[0]))
        for i, (st, _) in enumerate(scored):
            ranks[st].append(i + 1)
    for r in known:
        rs = sorted(ranks[r["state"]])
        r["rank_p10"] = rs[math.floor(0.1 * (len(rs) - 1))]
        r["rank_p90"] = rs[math.floor(0.9 * (len(rs) - 1))]
        r["p_top5"] = round3(sum(1 for x in rs if x <= 5) / len(rs))
    return results


def bayes_score(ratings: list[dict], now_ms: float, m: float = 5, prior: float = 3, half_life_days: float = 90) -> dict:
    """Time-decayed Bayesian average of 1-5 star ratings, reported 0-100 (Evan Miller; IMDb weighted rating)."""
    half = half_life_days * 86400000
    sw = sx = 0.0
    for r in ratings:
        age = max(0, now_ms - r["t"])
        w = 0.5 ** (age / half)
        sw += w
        sx += w * r["stars"]
    avg = (sx + m * prior) / (sw + m)
    return {"n": len(ratings), "score": round1(100 * (avg - 1) / 4), "effective_n": round3(sw),
            "freshness": round3(min(1, sw / 10))}
