"""A small, honest parser for OSM `opening_hours`.

It understands the forms that cover most real tags ("Mo-Fr 09:00-17:00; Sa 10:00-14:00",
"Mo-Th 09:00-20:00; Fr, Sa 10:00-17:00; Su 13:00-17:00", "24/7", "Su off", split hours like
"08:00-12:00,13:00-16:30", overnight ranges like "20:00-08:00"). Anything else (public
holidays, months, sunrise, comments) returns None, which the app shows as "hours unknown".
"""
from __future__ import annotations

import re
from datetime import datetime, time

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
_TIME_RANGE = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")
_UNSUPPORTED = re.compile(r"\b(PH|SH|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|sunrise|sunset|dawn|dusk|week)\b|\"|\[")


def _days(spec: str) -> set[int] | None:
    out: set[int] = set()
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        if "-" in part:
            a, b = part.split("-", 1)
            if a not in DAYS or b not in DAYS:
                return None
            i, j = DAYS.index(a), DAYS.index(b)
            rng = range(i, j + 1) if i <= j else list(range(i, 7)) + list(range(0, j + 1))
            out.update(rng)
        elif part in DAYS:
            out.add(DAYS.index(part))
        else:
            return None
    return out


def _ranges(spec: str) -> list[tuple[int, int]] | None:
    out = []
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        m = _TIME_RANGE.match(part)
        if not m:
            return None
        h1, m1, h2, m2 = map(int, m.groups())
        if h1 > 24 or h2 > 24 or m1 > 59 or m2 > 59:
            return None
        out.append((h1 * 60 + m1, h2 * 60 + m2))
    return out


def parse(text: str | None) -> dict[int, list[tuple[int, int]]] | None:
    """Return {weekday: [(start_min, end_min), ...]} or None if not understood."""
    if not text or _UNSUPPORTED.search(text):
        return None
    text = text.strip()
    if text == "24/7":
        return {d: [(0, 1440)] for d in range(7)}
    week: dict[int, list[tuple[int, int]]] = {d: [] for d in range(7)}
    for rule in [r.strip() for r in text.split(";") if r.strip()]:
        tokens = rule.split()
        # split into a day part (may contain ", ") and a time/off part
        time_idx = next((i for i, t in enumerate(tokens) if t[0].isdigit() or t in ("off", "closed")), None)
        if time_idx is None:
            return None
        day_spec = " ".join(tokens[:time_idx]).replace(" ", "")
        time_spec = "".join(tokens[time_idx:])
        days = _days(day_spec) if day_spec else set(range(7))
        if days is None:
            return None
        if time_spec in ("off", "closed"):
            for d in days:
                week[d] = []
            continue
        rng = _ranges(time_spec)
        if rng is None:
            return None
        for d in days:
            week[d] = list(rng)          # a later rule replaces earlier ones for its days
    return week


def is_open(text: str | None, when: datetime) -> bool | None:
    week = parse(text)
    if week is None:
        return None
    d, minute = when.weekday(), when.hour * 60 + when.minute
    for start, end in week[d]:
        if start <= end and start <= minute < end:
            return True
        if start > end and minute >= start:          # overnight, before midnight
            return True
    for start, end in week[(d - 1) % 7]:             # overnight range that began yesterday
        if start > end and minute < end:
            return True
    return False


def closes_today(text: str | None, when: datetime) -> time | None:
    week = parse(text)
    if not week:
        return None
    minute = when.hour * 60 + when.minute
    for start, end in week[when.weekday()]:
        if start <= minute < end or (start > end and minute >= start):
            e = end % 1440
            return time(e // 60, e % 60)
    return None
