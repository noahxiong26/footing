"""site/ is the published interactive demo (GitHub Pages). It must match the app source it was built from.

Rebuild after any change to footing/web or the data: `python scripts/build_standalone_demo.py site`.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
WEB = ROOT / "footing" / "web"
pytestmark = pytest.mark.skipif(not SITE.exists(), reason="site/ not built")

REBUILD = "site/ is stale: run python scripts/build_standalone_demo.py site"


@pytest.mark.parametrize("name", ["fit.js", "vafit.js", "vapoint.js", "i18n.js", "i18n_more.js", "globe.js"])
def test_site_scripts_match_the_app(name):
    assert (SITE / name).read_bytes() == (WEB / name).read_bytes(), REBUILD


def test_site_backend_and_styles_match():
    assert (SITE / "standalone_backend.js").read_bytes() == (ROOT / "demo" / "standalone_backend.js").read_bytes(), REBUILD
    page = (SITE / "index.html").read_text(encoding="utf-8")
    assert (WEB / "globe.css").read_text(encoding="utf-8") in page, REBUILD
    assert page.startswith("<!doctype html>"), "site/ must be a full page (build without --fragment)"


def test_site_data_matches_the_committed_data():
    va = json.loads((SITE / "data" / "va.json").read_text(encoding="utf-8"))
    assert va == json.loads((ROOT / "footing" / "static" / "va_localities.json").read_text(encoding="utf-8")), REBUILD
    policy = json.loads((SITE / "data" / "policy.json").read_text(encoding="utf-8"))
    assert policy["eligibility"] == json.loads((ROOT / "footing" / "static" / "eligibility.json").read_text(encoding="utf-8")), REBUILD
    towns = json.loads((SITE / "data" / "towns.json").read_text(encoding="utf-8"))["recorded"]
    assert len(towns) == 6 and all((SITE / "data" / f"receipt-{t['set']}.json").exists() for t in towns)


def test_site_backend_never_calls_a_server():
    # globe.js only uses /api when no backend is supplied; the site always supplies standalone_backend.js.
    backend = (SITE / "standalone_backend.js").read_text(encoding="utf-8")
    assert "/api/" not in backend and "standalone: true" in backend
