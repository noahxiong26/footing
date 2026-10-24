"""The grounded 30-Day Plan.

Gemma 4 writes the plan, but it may only point at places the pipeline found. Every step's
`place_id` must be in the candidate list built from the receipt; anything else is dropped and
reported. Addresses and phone numbers are never taken from the model: the app fills them in
from the receipt data. Without a key (or if Gemma fails) a deterministic rule-based plan is
returned and clearly labeled, so the demo never breaks.
"""
from __future__ import annotations

import re
from typing import Any

from .config import GEMMA_MODEL
from .gemma import GemmaClient, GemmaUnavailable

PLAN_KINDS = ["shelter", "day_center", "soup_kitchen", "food_bank", "snap_retailer", "library", "toilets",
              "drinking_water", "shower", "laundry", "clinic", "health_center", "pharmacy", "post_office",
              "employment_agency", "school", "transit_stop"]
PHASES = ("day1", "week1", "month1")
MAX_STEPS = 4
ADDRESSY = re.compile(r"\b\d{2,5}\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Ln|Lane|Way)\b|\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}", re.I)

SYSTEM = """You help a person experiencing homelessness plan their next 30 days in one area.
Rules you must follow:
- Use ONLY places from the CANDIDATES list, referenced by their exact "id". Never invent a place,
  address, phone number, opening hour, price or program.
- A step may have "place_id": null only for actions that need no specific place (for example
  calling 211 or asking a school about its homeless liaison).
- Plain words, about a 6th-grade reading level, short sentences, no judgement.
- At most 4 steps per phase. Prefer places that are open now and a short walk away.
- Reply with JSON only, exactly this shape:
{"summary": "...", "day1": [{"action": "...", "place_id": "... or null", "why": "..."}],
 "week1": [...], "month1": [...]}"""


def candidates(receipt: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for kind in PLAN_KINDS:
        for p in receipt.get("nearest", {}).get(kind, []):
            out[p["id"]] = {"id": p["id"], "kind": kind, "name": p["name"], "walk_min": p.get("walk_min"),
                            "open_now": p.get("open_now"), "closes": p.get("closes"),
                            "hours": p.get("tags", {}).get("opening_hours"),
                            "phone": p.get("tags", {}).get("phone"),
                            "address": p.get("tags", {}).get("address"),
                            "full_grocery": bool(p.get("tags", {}).get("full_grocery"))}
    return out


def _context(receipt: dict, profile: list[str], language: str) -> str:
    cands = candidates(receipt)
    lines = [f"LANGUAGE: {language}", f"PROFILE: {', '.join(profile) or 'none'}",
             f"AREA: {receipt['area'].get('nws_city') or receipt['area'].get('county')}",
             f"LOCAL TIME: {receipt.get('local_time') or 'unknown'}",
             f"WEATHER ALERTS: {[a.get('event') for a in receipt.get('alerts', [])] or 'none'}",
             f"NEXT 7 NIGHT LOWS (F): {receipt.get('lows_f') or 'unknown'}",
             "MONEY: " + "; ".join(f"{m['label']}: {m['value'] if m['value'] is not None else 'unknown'}"
                                   for m in receipt.get("money", [])),
             "UNKNOWN (do not guess these): " + "; ".join(u["parameter"] for u in receipt.get("unknowns", [])),
             "CANDIDATES:"]
    for c in cands.values():
        lines.append(f'- id="{c["id"]}" kind={c["kind"]} name="{c["name"]}" walk={c["walk_min"]} min '
                     f'open_now={c["open_now"]} hours="{c["hours"] or "unknown"}"')
    return "\n".join(lines)


def validate(plan: dict, cands: dict[str, dict]) -> tuple[dict, list[dict]]:
    """Keep only grounded steps. Returns (clean_plan, removed_steps_with_reasons)."""
    if not isinstance(plan, dict):
        return {"summary": "", **{p: [] for p in PHASES}}, [{"phase": None, "step": plan, "reason": "malformed"}]
    clean: dict[str, Any] = {"summary": str(plan.get("summary", ""))[:400]}
    removed: list[dict] = []
    for phase in PHASES:
        steps = []
        raw_steps = plan.get(phase)
        for step in (raw_steps if isinstance(raw_steps, list) else [])[:MAX_STEPS * 2]:
            if not isinstance(step, dict) or not step.get("action"):
                removed.append({"phase": phase, "step": step, "reason": "malformed"})
                continue
            pid = step.get("place_id")
            if pid is not None and not isinstance(pid, str):
                removed.append({"phase": phase, "step": step, "reason": "malformed"})
                continue
            if pid in (None, "", "null"):
                if ADDRESSY.search(step["action"]) or ADDRESSY.search(str(step.get("why", ""))):
                    removed.append({"phase": phase, "step": step, "reason": "address or phone not from data"})
                    continue
                steps.append({"action": step["action"], "why": step.get("why", ""), "place": None})
            elif pid in cands:
                steps.append({"action": step["action"], "why": step.get("why", ""), "place": cands[pid]})
            else:
                removed.append({"phase": phase, "step": step, "reason": f"place_id {pid!r} not in pipeline data"})
                continue
            if len(steps) >= MAX_STEPS:
                break
        clean[phase] = steps
    return clean, removed


def _first(cands: dict[str, dict], *kinds: str) -> dict | None:
    pool = [c for c in cands.values() if c["kind"] in kinds]
    pool.sort(key=lambda c: (c["open_now"] is False, c["walk_min"] if c["walk_min"] is not None else 1e9))
    return pool[0] if pool else None


def rule_based(receipt: dict, profile: list[str]) -> dict:
    """Deterministic plan from the same candidates. Used when Gemma is unavailable."""
    c = candidates(receipt)
    day1, week1, month1 = [], [], []

    def add(lst, action, why, place):
        action = action.replace("..", ".")
        lst.append({"action": action, "why": why, "place_id": place["id"] if place else None})

    shelter = _first(c, "shelter")
    if shelter:
        add(day1, f"Ask about a bed tonight at {shelter['name']}.", "Closest shelter we found.", shelter)
    else:
        add(day1, "Call 211 and ask which shelters have beds tonight.",
            "We could not confirm any shelter near here from public data.", None)
    meal = _first(c, "soup_kitchen", "food_bank")
    if meal:
        add(day1, f"Get food at {meal['name']}.", "Free food close by.", meal)
    grocery = [x for x in c.values() if x["kind"] == "snap_retailer" and x["full_grocery"]]
    store = min(grocery, key=lambda x: x["walk_min"] or 1e9) if grocery else _first(c, "snap_retailer")
    if store:
        add(day1, f"Use EBT at {store['name']}.", "Closest store that takes SNAP.", store)
    lib = _first(c, "library")
    if lib:
        add(day1, f"Charge your phone and use Wi-Fi at {lib['name']}.", "Free power, internet and a warm seat.", lib)
    post = _first(c, "post_office")
    if post:
        add(week1, f"Ask {post['name']} about General Delivery mail.",
            "A free mailing address for benefits, job and ID paperwork.", post)
    clinic = _first(c, "health_center", "clinic")
    if clinic:
        add(week1, f"Visit {clinic['name']} for any health needs.", "Closest clinic we found.", clinic)
    job = _first(c, "employment_agency")
    if job:
        add(week1, f"Register with {job['name']}.", "Help finding work nearby.", job)
    if "kids" in profile:
        school = _first(c, "school")
        add(week1, "Ask the school district for its homeless liaison so your kids can enroll right away.",
            "Federal law protects school enrollment for children without a fixed address.", school)
    add(month1, "Ask 211 or the local housing program about rapid rehousing.",
        "The next step toward your own place.", None)
    money = {m["label"]: m for m in receipt.get("money", [])}
    fmr = money.get("Next step: studio Fair Market Rent", {}).get("value")
    if fmr:
        add(month1, f"Plan for a studio around ${fmr:,.0f} a month, the local Fair Market Rent.",
            "Know the target before you start saving.", None)
    return {"summary": "A starting plan built from the places we found near you.",
            "day1": day1, "week1": week1, "month1": month1}


def make_plan(receipt: dict, profile: list[str], language: str = "English",
              client: GemmaClient | None = None, api_key: str | None = None) -> dict:
    cands = candidates(receipt)
    engine, note = "rule-based", ""
    try:
        client = client or GemmaClient(api_key)
        raw = client.generate_json(SYSTEM, _context(receipt, profile, language))
        engine = client.model
    except GemmaUnavailable as e:
        raw, note = rule_based(receipt, profile), f"Gemma unavailable ({e}); rule-based plan shown."
    plan, removed = validate(raw, cands)
    if engine != "rule-based" and not any(plan[p] for p in PHASES):
        # Every model step was ungrounded or malformed: show the grounded rule-based plan instead.
        plan, _ = validate(rule_based(receipt, profile), cands)
        engine, note = "rule-based", "Gemma's plan had no steps we could check against the data; rule-based plan shown."
    return {"engine": engine, "note": note, "language": language, "plan": plan, "removed": removed,
            "grounding": "Every place comes from the pipeline's data; model output that names any other place is removed.",
            "model_default": GEMMA_MODEL}
