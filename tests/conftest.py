import shutil
from pathlib import Path

import pytest

from footing.config import DEFAULT_FIXTURES, Settings

HERE = Path(__file__).resolve().parent
POINT = (37.1299, -80.4089)          # downtown Christiansburg, VA (fixture capture point)


@pytest.fixture
def live_settings() -> Settings:
    """Replay of the real responses captured on 2026-10-24."""
    return Settings(mode="replay", fixture_dir=DEFAULT_FIXTURES)


@pytest.fixture
def full_settings(tmp_path) -> Settings:
    """Real captures + synthetic responses for the keyed APIs, so every adapter runs."""
    d = tmp_path / "fixtures"
    shutil.copytree(DEFAULT_FIXTURES, d)
    for f in (HERE / "synthetic").glob("*.json"):
        if f.name != "nws__alerts_freeze.json":
            shutil.copy(f, d / f.name)
    return Settings(mode="replay", fixture_dir=d)
