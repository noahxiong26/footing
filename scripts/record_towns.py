"""Audit/resume the existing `footing record` CLI; no alternate source parsers.

Only inherited Settings.from_env() credentials are used. Never loads .env files.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from unittest.mock import patch
from urllib.parse import urlencode, quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from footing import cli, pipeline
from footing.config import Settings
from footing.geo import snap_to_tile
from footing.http import Fetcher, SourceHTTPError
from footing.sources.base import Source

TOWNS = {
    "roanoke": (37.2710, -79.9414, "Downtown Roanoke, VA"),
    "richmond": (37.5407, -77.4360, "Downtown Richmond, VA"),
    "blacksburg": (37.2296, -80.4139, "Downtown Blacksburg, VA"),
    "harrisonburg": (38.4496, -78.8689, "Downtown Harrisonburg, VA"),
    "alexandria": (38.8048, -77.0469, "Old Town Alexandria, VA"),
}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def record_town(slug: str, out: Path, resume: bool = False, *, timeout_s=20.0,
                browser_ua=False, fallbacks=False):
    lat, lon, label = TOWNS[slug]
    prior = {}
    if out.exists():
        if not resume:
            raise ValueError(f"{out} already exists; use --resume to retry missing requests")
        prior = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
        if prior["point"] != {"lat": lat, "lon": lon, "label": label}:
            raise ValueError(f"{out}: manifest belongs to a different point")
        if not prior.get("source_outcomes"):
            raise ValueError(f"{out}: resume requires an audited capture; preserve older captures")
    else:
        out.mkdir(parents=True)

    settings = Settings.from_env()
    secrets = [s for s in settings.keys.values() if s]

    def safe(value):
        if isinstance(value, dict):
            return {k: ("REDACTED" if re.search(
                r"^(key|api_key|apikey|registrationkey|access_token|refresh_token|client_secret|authorization)$",
                k, re.I) else safe(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [safe(v) for v in value]
        if isinstance(value, str):
            for secret in secrets:
                value = value.replace(secret, "REDACTED").replace(quote(secret, safe=""), "REDACTED")
            return re.sub(r"([?&](?:key|api_key|apikey|registrationkey)=)[^&\s]+",
                          r"\1REDACTED", value, flags=re.I)
        return value

    outcomes = {}
    requests = []
    started = timestamp()
    old_files = prior.get("files", {})

    def append_log(entry):
        with (out / "REQUESTS.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe(entry), ensure_ascii=True) + "\n")

    class AuditedFetcher(Fetcher):
        def __init__(self, config):
            if browser_ua:
                config = replace(config, user_agent="Mozilla/5.0 (compatible; Footing public-data audit)")
            super().__init__(replace(config, timeout_s=timeout_s))

        def _request(self, url, method, form, json_body, headers):
            body = super()._request(url, method, form, json_body, headers)
            # A 200 status alone is not evidence of a successful data response.
            if not body.strip():
                raise SourceHTTPError("HTTP response body was empty")
            data = json.loads(body)  # Reject HTML block/login pages before recording.
            if not isinstance(data, (dict, list)) or not data:
                raise SourceHTTPError("JSON response was empty or not an object/array")
            if self.active_source == "osm" and (
                not isinstance(data, dict) or "elements" not in data or data.get("remark")
            ):
                raise SourceHTTPError("Overpass incomplete/error response: " + safe(str(data.get("remark", "missing elements"))))
            if self.active_source == "urban_ed" and (
                not isinstance(data, dict) or not isinstance(data.get("results"), list)
            ):
                raise SourceHTTPError("Urban Institute response has no results array")
            return body

        def _record(self, source, key, data):
            # OAuth tokens are only useful in memory, never in replay fixtures.
            super()._record(source, key, safe(data))

        def json(self, source, key, url, **kwargs):
            if fallbacks and resume and source == "osm" and prior.get("source_outcomes", {}).get("osm", {}).get("status") != "ok":
                url = "https://overpass.private.coffee/api/interpreter"
            try:
                return self._audited_json(source, key, url, **kwargs)
            except (SourceHTTPError, json.JSONDecodeError):
                if not fallbacks:
                    raise
                # Identical town query, same parser; only the transport changes.
                # Public instances: https://wiki.openstreetmap.org/wiki/Overpass_API
                if source == "osm":
                    return self._audited_json(source, key,
                        ("https://overpass.maprva.org/api/interpreter" if "private.coffee" in url
                         else "https://overpass.private.coffee/api/interpreter"), **kwargs)
                # BLS documents this single-series GET alongside the default POST:
                # https://www.bls.gov/developers/api_signature.htm
                if source == "bls_laus":
                    sid = kwargs["json_body"]["seriesid"][0]
                    return self._audited_json(source, key,
                        "https://api.bls.gov/publicAPI/v1/timeseries/data/" + sid,
                        ttl_s=kwargs.get("ttl_s", 3600))
                raise

        def _audited_json(self, source, key, url, **kwargs):
            self.active_source = source
            filename = f"{source}__{key}.json"
            if browser_ua:
                kwargs["headers"] = {"Accept": "*/*", **kwargs.get("headers", {})}
            full_url = url + ("?" + urlencode(kwargs["params"], doseq=True) if kwargs.get("params") else "")
            entry = {"source": source, "file": filename, "started_at": timestamp(),
                     "method": kwargs.get("method", "GET"), "url": safe(full_url),
                     "form": safe(kwargs.get("form")), "json_body": safe(kwargs.get("json_body")),
                     "user_agent": self.settings.user_agent, "timeout_s": self.settings.timeout_s}
            try:
                if filename in old_files and filename != "kroger__token.json":
                    body = (out / filename).read_bytes()
                    if hashlib.sha256(body).hexdigest() != old_files[filename]["sha256"]:
                        raise ValueError(f"{filename}: saved response hash changed")
                    data = json.loads(body)
                    self.recorded[filename] = old_files[filename]["url"]
                    entry["outcome"] = "reused_existing_response"
                    return data
                data = super().json(source, key, url, **kwargs)
                entry["outcome"] = "captured_json"
                return data
            except Exception as exc:
                entry.update(outcome="failed", error=safe(f"{type(exc).__name__}: {exc}"))
                raise
            finally:
                entry["finished_at"] = timestamp()
                requests.append(entry)
                append_log(entry)

    original_run = Source.run

    def audited_run(source, ctx):
        source_started = timestamp()
        result = original_run(source, ctx)
        result.reason = safe(result.reason)
        outcomes[source.name] = safe({**result.to_dict(), "started_at": source_started,
                                      "finished_at": timestamp(), "homepage": source.homepage,
                                      "needs": list(source.needs),
                                      "kind": "local_static" if source.name in {"static_tables", "hrsa"} else "network"})
        # Preserve progress even if a later source/process is interrupted.
        append_log({"source_outcome": outcomes[source.name]})
        return result

    with patch.object(pipeline, "Fetcher", AuditedFetcher), patch.object(Source, "run", audited_run):
        cli.main(["record", "--lat", str(lat), "--lon", str(lon), "--label", label, "--out", str(out)])

    manifest_path = out / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for filename, info in manifest["files"].items():
        if filename in old_files and filename != "kroger__token.json":
            info.update(old_files[filename])
        else:
            entry = next(r for r in requests if r["file"] == filename and r["outcome"] == "captured_json")
            info.update({k: entry[k] for k in ("started_at", "finished_at", "method", "form", "json_body", "user_agent", "timeout_s")})
            info["sha256"] = hashlib.sha256((out / filename).read_bytes()).hexdigest()
    manifest.update(
        how="Existing footing.cli record / pipeline with scripts/record_towns.py request and source audit.",
        first_capture_started_at=prior.get("first_capture_started_at", started),
        tile=snap_to_tile(lat, lon)[0], radius_m=settings.radius_m,
        request_log="REQUESTS.jsonl", source_outcomes=outcomes,
        capture_runs=prior.get("capture_runs", []) + [{"started_at": started, "finished_at": timestamp(),
                    "resume": resume, "timeout_s": timeout_s, "browser_ua": browser_ua,
                    "fallbacks": fallbacks, "requests": len(requests),
                    "captured_json": sum(r["outcome"] == "captured_json" for r in requests),
                    "failed": sum(r["outcome"] == "failed" for r in requests)}],
    )
    manifest_path.write_text(json.dumps(safe(manifest), indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("towns", nargs="*", help="town slugs; default: all five new towns")
    ap.add_argument("--date", default=date.today().isoformat(), help="folder date only; request clocks are never overridden")
    ap.add_argument("--root", type=Path, default=Path("fixtures"))
    ap.add_argument("--resume", action="store_true", help="reuse hashed responses and retry missing requests")
    ap.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    ap.add_argument("--browser-ua", action="store_true", help="browser-compatible public-data User-Agent and Accept */*")
    ap.add_argument("--fallbacks", action="store_true", help="try the public Overpass mirror and BLS single-series GET on failure")
    args = ap.parse_args()
    date.fromisoformat(args.date)
    towns = args.towns or list(TOWNS)
    if len(towns) != len(set(towns)) or any(t not in TOWNS for t in towns):
        ap.error("choose unique town slugs from: " + ", ".join(TOWNS))
    # Preflight the entire batch before making any requests.
    for town in towns:
        folder = args.root / f"{town}_{args.date}"
        if folder.exists() and not args.resume:
            ap.error(f"{folder} exists; use --resume or choose a new folder date/root")
    for town in towns:
        record_town(town, args.root / f"{town}_{args.date}", args.resume,
                    timeout_s=args.timeout, browser_ua=args.browser_ua, fallbacks=args.fallbacks)


if __name__ == "__main__":
    main()
