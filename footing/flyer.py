"""Snap a Flyer: Gemma 4 reads a photo of a paper flyer into fields the user then confirms.

Nothing is saved here. The result is marked community-reported and unconfirmed; the app shows
the fields for the user to fix before anything is shared.
"""
from __future__ import annotations

import re

from .gemma import GemmaClient, GemmaUnavailable

FIELDS = ("service", "organization", "days_times", "address", "phone", "eligibility", "cost", "notes")
SYSTEM = """You read photos of paper flyers for free services (meals, shelter, clinics, showers,
clothing, job help). Copy what the flyer says; do not guess or add anything that is not printed.
If a field is not on the flyer, use null. Reply with JSON only:
{"service": ..., "organization": ..., "days_times": ..., "address": ..., "phone": ...,
 "eligibility": ..., "cost": ..., "notes": ..., "readable": true/false}"""
PHONE = re.compile(r"^\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$")
MAX_BYTES = 6 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/heic"}


class FlyerError(ValueError):
    pass


def read_flyer(data: bytes, mime: str, client: GemmaClient | None = None, api_key: str | None = None) -> dict:
    if mime not in ALLOWED:
        raise FlyerError(f"unsupported image type {mime}")
    if len(data) > MAX_BYTES:
        raise FlyerError("image is larger than 6 MB")
    client = client or GemmaClient(api_key)          # raises GemmaUnavailable without a key
    raw = client.generate_json(SYSTEM, "Read this flyer.", image=(data, mime))
    out = {k: (str(raw.get(k)).strip() if raw.get(k) not in (None, "", "null") else None) for k in FIELDS}
    warnings = []
    if out["phone"] and not PHONE.match(out["phone"]):
        warnings.append("phone number does not look complete; check it against the flyer")
    if not raw.get("readable", True):
        warnings.append("the model could not read the flyer clearly; retake the photo")
    return {"fields": out, "warnings": warnings, "status": "community-reported, unconfirmed",
            "engine": client.model}


__all__ = ["read_flyer", "FlyerError", "GemmaUnavailable"]
