"""Plain data records that every source normalizes into."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Provenance:
    source: str
    url: str
    license: str
    refresh: str          # live | daily | weekly | monthly | annual | static
    fetched_at: str       # when we pulled it (ISO 8601)
    as_of: str | None     # when the publisher says the data is from, if known
    mode: str             # live | replay | record


@dataclass
class Place:
    id: str
    name: str
    kind: str             # shelter, food_bank, snap_retailer, toilets, library, ...
    lat: float
    lon: float
    source: str
    tags: dict[str, Any] = field(default_factory=dict)
    distance_m: float | None = None
    walk_min: float | None = None


@dataclass
class Measure:
    id: str
    value: Any
    unit: str
    source: str
    as_of: str | None = None
    note: str = ""


@dataclass
class SourceResult:
    source: str
    status: str                      # ok | unknown | error
    reason: str = ""
    places: list[Place] = field(default_factory=list)
    measures: dict[str, Measure] = field(default_factory=dict)
    provenance: Provenance | None = None

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "status": self.status,
            "reason": self.reason,
            "place_count": len(self.places),
            "measures": {k: asdict(m) for k, m in self.measures.items()},
            "provenance": asdict(self.provenance) if self.provenance else None,
        }
