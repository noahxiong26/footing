"""Shared plumbing for source adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..config import Settings
from ..geo import haversine_m, walk_minutes
from ..http import Fetcher, NotCaptured, SourceHTTPError
from ..models import Place, Provenance, SourceResult


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Context:
    lat: float
    lon: float
    settings: Settings
    fetcher: Fetcher
    radius_m: int = 5000
    county_fips: str | None = None      # 5 digits, set by the Census geocoder step
    county_name: str | None = None
    state_fips: str | None = None
    state_abbr: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class Source:
    name = "base"
    license = ""
    refresh = "static"
    homepage = ""
    needs = ()            # names of keys in Settings.keys that must be set

    def run(self, ctx: Context) -> SourceResult:
        missing = [k for k in self.needs if not ctx.settings.key(k)]
        if missing and ctx.settings.mode != "replay":
            return SourceResult(self.name, "unknown", f"no API key set ({', '.join(missing)})")
        try:
            result = self.fetch(ctx)
        except NotCaptured as e:
            reason = (f"not captured in fixtures ({e})" if ctx.settings.fixture_dir
                      else "no recorded data for this place (demo data covers one tile; run live mode)")
            if missing:
                reason = f"no API key set ({', '.join(missing)}); {reason}"
            return SourceResult(self.name, "unknown", reason)
        except SourceHTTPError as e:
            return SourceResult(self.name, "error", str(e))
        except (KeyError, ValueError, TypeError, IndexError) as e:
            return SourceResult(self.name, "error", f"unexpected response shape: {e!r}")
        if result.provenance is None:
            result.provenance = self.provenance(ctx)
        return result

    def fetch(self, ctx: Context) -> SourceResult:  # pragma: no cover - abstract
        raise NotImplementedError

    def provenance(self, ctx: Context, as_of: str | None = None, url: str | None = None) -> Provenance:
        return Provenance(
            source=self.name,
            url=url or self.homepage,
            license=self.license,
            refresh=self.refresh,
            fetched_at=now_iso(),
            as_of=as_of,
            mode=ctx.settings.mode,
        )

    @staticmethod
    def place(ctx: Context, *, id: str, name: str, kind: str, lat: float, lon: float,
              source: str, tags: dict | None = None) -> Place:
        d = haversine_m(ctx.lat, ctx.lon, lat, lon)
        return Place(id=id, name=name or "(unnamed)", kind=kind, lat=lat, lon=lon,
                     source=source, tags=tags or {}, distance_m=round(d, 1),
                     walk_min=round(walk_minutes(d), 1))
