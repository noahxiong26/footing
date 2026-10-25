"""Runtime settings, read from environment variables.

Modes
-----
live    call the real APIs (optionally through the SQLite cache)
replay  read recorded responses from a fixture folder; never touch the network
record  call the real APIs and save each response into the fixture folder
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent
FIXTURES_ROOT = REPO_DIR / "fixtures"
DEFAULT_FIXTURES = FIXTURES_ROOT / "christiansburg_2026-10-24"

KEY_ENV = {
    "census": "CENSUS_API_KEY",
    "hud": "HUD_API_TOKEN",
    "eia": "EIA_API_KEY",
    "bls": "BLS_API_KEY",
    "google_maps": "GOOGLE_MAPS_API_KEY",
    "transitland": "TRANSITLAND_API_KEY",
    "kroger_id": "KROGER_CLIENT_ID",
    "kroger_secret": "KROGER_CLIENT_SECRET",
    "gemini": "GEMINI_API_KEY",
}
GEMMA_MODEL = os.getenv("FOOTING_GEMMA_MODEL", "gemma-4-26b-a4b-it")


@dataclass
class Settings:
    mode: str = "replay"
    fixture_dir: Path | None = DEFAULT_FIXTURES
    cache_path: Path | None = None
    keys: dict[str, str] = field(default_factory=dict)
    user_agent: str = "footing-hackday/0.1 (open-source; set FOOTING_CONTACT)"
    radius_m: int = 5000
    timeout_s: float = 20.0

    def key(self, name: str) -> str | None:
        value = self.keys.get(name)
        return value or None

    @classmethod
    def from_env(cls, **overrides) -> "Settings":
        contact = os.getenv("FOOTING_CONTACT", "set FOOTING_CONTACT")
        fixture = os.getenv("FOOTING_FIXTURES")
        cache = os.getenv("FOOTING_CACHE")
        settings = cls(
            mode=os.getenv("FOOTING_MODE", "replay"),
            fixture_dir=Path(fixture) if fixture else FIXTURES_ROOT,
            cache_path=Path(cache) if cache else None,
            keys={name: os.getenv(env, "") for name, env in KEY_ENV.items()},
            user_agent=f"footing-hackday/0.1 ({contact})",
        )
        for k, v in overrides.items():
            if v is not None:
                setattr(settings, k, v)
        if settings.mode not in {"live", "replay", "record"}:
            raise ValueError(f"FOOTING_MODE must be live, replay or record, not {settings.mode!r}")
        return settings
