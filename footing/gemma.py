"""Minimal Gemini API client for Gemma 4 (text + image in, JSON text out).

Uses the documented REST shape: POST
  https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent  (key in the x-goog-api-key header)
with `systemInstruction`, `contents[].parts[]` (text or inline_data) and a thinking level.
The transport is injectable so tests never touch the network.
"""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request
from typing import Any, Callable

from .config import GEMMA_MODEL

Transport = Callable[[str, dict], dict]
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GemmaUnavailable(Exception):
    pass


def _http_transport(url: str, body: dict, api_key: str) -> dict:
    # Key goes in a header, not the URL, so it never lands in proxy or server logs.
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise GemmaUnavailable(f"Gemini API HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise GemmaUnavailable(f"Gemini API unreachable: {e}") from e


def extract_json(text: str) -> Any:
    """Models sometimes wrap JSON in ``` fences or add a sentence; take the first JSON object."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:end + 1])


class GemmaClient:
    def __init__(self, api_key: str | None, model: str = GEMMA_MODEL, transport: Transport | None = None):
        if not api_key and transport is None:
            raise GemmaUnavailable("GEMINI_API_KEY is not set")
        self.api_key = api_key or ""
        self.model = model
        self.transport = transport or (lambda url, body: _http_transport(url, body, self.api_key))

    def generate_json(self, system: str, user: str, image: tuple[bytes, str] | None = None,
                      thinking: str = "minimal") -> dict:
        parts: list[dict] = []
        if image:
            data, mime = image
            parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
        parts.append({"text": user})
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.2, "thinkingConfig": {"thinkingLevel": thinking}},
        }
        url = ENDPOINT.format(model=self.model)
        resp = self.transport(url, body)
        try:
            cand = resp["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought"))
        except (KeyError, IndexError) as e:
            raise GemmaUnavailable(f"unexpected Gemini response: {str(resp)[:200]}") from e
        try:
            return extract_json(text)
        except (ValueError, json.JSONDecodeError) as e:
            raise GemmaUnavailable(f"model did not return valid JSON: {e}") from e
