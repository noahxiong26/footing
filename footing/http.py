"""One door to the network: live calls, an SQLite response cache, and fixture replay/record.

Every source asks for data through `Fetcher.json(source, key, url, ...)`. The (source, key)
pair names the fixture file `<source>__<key>.json`, so recorded data stays readable.
"""
from __future__ import annotations

import hashlib
import re
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .config import Settings


class NotCaptured(Exception):
    """Replay mode, and no fixture exists for this request."""


class SourceHTTPError(Exception):
    pass


class Fetcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._db: sqlite3.Connection | None = None
        self.recorded: dict[str, str] = {}      # fixture file -> URL (record mode)
        if settings.cache_path and settings.mode == "live":
            settings.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(settings.cache_path)
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS responses (k TEXT PRIMARY KEY, fetched REAL, body TEXT)"
            )

    # ---- public -------------------------------------------------------
    def json(
        self,
        source: str,
        key: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        form: dict[str, str] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        ttl_s: int = 3600,
    ) -> Any:
        full_url = url + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
        if self.settings.mode == "replay":
            return self._replay(source, key)
        cache_key = hashlib.sha256(
            f"{method} {full_url} {form} {json_body}".encode()
        ).hexdigest()
        cached = self._cache_get(cache_key, ttl_s)
        if cached is not None:
            return cached
        body = self._request(full_url, method, form, json_body, headers)
        data = json.loads(body)
        self._cache_put(cache_key, body)
        if self.settings.mode == "record":
            self._record(source, key, data)
            self.recorded[f"{source}__{key}.json"] = re.sub(r"(key|api_key|apikey|registrationkey)=[^&]+", r"\1=REDACTED", full_url)
        return data

    # ---- replay / record ---------------------------------------------
    def _path(self, source: str, key: str) -> Path:
        if not self.settings.fixture_dir:
            raise NotCaptured(f"{source}/{key}: no fixture folder configured")
        return self.settings.fixture_dir / f"{source}__{key}.json"

    def _replay(self, source: str, key: str) -> Any:
        path = self._path(source, key)
        if not path.exists():
            raise NotCaptured(f"{source}/{key}: not in fixture set {path.parent.name}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _record(self, source: str, key: str, data: Any) -> None:
        path = self._path(source, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, indent=1)
        for secret in self.settings.keys.values():   # some APIs echo the request (and key) back
            if secret and len(secret) >= 6:
                text = text.replace(secret, "REDACTED")
        path.write_text(text, encoding="utf-8")

    # ---- network -------------------------------------------------------
    def _request(self, url, method, form, json_body, headers) -> str:
        h = {"User-Agent": self.settings.user_agent, "Accept": "application/json, */*"}
        h.update(headers or {})
        data = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_body is not None:
            data = json.dumps(json_body).encode()
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        last_err: Exception | None = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.settings.timeout_s) as resp:
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                last_err = SourceHTTPError(f"HTTP {e.code} from {urllib.parse.urlsplit(url).netloc}")
                if e.code not in (429, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = SourceHTTPError(f"network error: {e}")
            time.sleep(1.5 * (attempt + 1))
        raise last_err or SourceHTTPError("unknown network error")

    # ---- cache ---------------------------------------------------------
    def _cache_get(self, k: str, ttl_s: int) -> Any:
        if not self._db:
            return None
        row = self._db.execute("SELECT fetched, body FROM responses WHERE k=?", (k,)).fetchone()
        if row and time.time() - row[0] < ttl_s:
            return json.loads(row[1])
        return None

    def _cache_put(self, k: str, body: str) -> None:
        if not self._db:
            return
        self._db.execute("REPLACE INTO responses VALUES (?,?,?)", (k, time.time(), body))
        self._db.commit()
