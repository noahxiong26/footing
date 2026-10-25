"""Build a static, single-folder copy of the globe that runs with no server (for a shareable demo link).

    python scripts/build_standalone_demo.py out/demo
    python -m http.server -d out/demo 8799        # open http://localhost:8799/

What changes compared with the app:
  * policy data, the recorded Christiansburg receipt and the town list ship as files in data/
  * ratings go to `demo/standalone_backend.js`: a claude.ai Artifact `db` store when the page is hosted
    as an Artifact, otherwise they stay on this device only (the toast says so)
  * no satellite or label tiles (hosted pages can't load outside images), so the vector map stays visible
    when zoomed in; "Hide" blanks the page instead of opening weather.gov

STATUS: generated and served once on 2026-10-24, but the browser run-through was NOT finished.
Test it (see HANDOFF.md section 8) before showing it to anyone.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "footing" / "web"
STATIC = ROOT / "footing" / "static"
FIX = ROOT / "fixtures" / "christiansburg_2026-10-24"
TOWNS = {"ok": True, "mode": "replay", "recorded": [
    {"label": "Downtown Christiansburg, VA", "lat": 37.1299, "lon": -80.4089, "captured_at": "2026-10-24",
     "set": "christiansburg_2026-10-24"}]}

SHELL = """<title>Footing Globe</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Overpass:wght@700;800&display=swap" rel="stylesheet">
<style>
/* Night Earth, single dark look by design. */
:root { color-scheme: dark; --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; --ink: #e8ecf4; --bg: #05070f; }
html, body { height: 100%; margin: 0; background: #05070f; color: #e8ecf4; font-family: var(--sans); }
* { box-sizing: border-box; }
a { color: inherit; }
#cover { position: fixed; inset: 0; background: #ffffff; color: #1b1b1b; display: flex; align-items: center; justify-content: center; font: 16px system-ui, sans-serif; }
.g-top { padding-top: env(safe-area-inset-top, 0px); }
</style>
<style>
@@MAPLIBRE_CSS@@
</style>
<style>
@@GLOBE_CSS@@
</style>
<div id="globe-root">
  <canvas id="stars" aria-hidden="true"></canvas>
  <div id="globe-map" aria-label="Globe. States are colored by how well they fit you. Use the List button for the same information as a list."></div>
  <div class="g-loading" role="status">Loading the map...</div>
  <div class="g-top">
    <a href="#top" class="g-brand" aria-label="Footing">FOOTING</a>
    <button type="button" class="g-btn" id="g-listbtn">List</button>
    <button type="button" class="g-btn" id="g-lang">Español</button>
    <button type="button" class="g-btn hide" id="g-hide">Hide this page</button>
  </div>
  <div class="g-legend">
    <div class="g-ramp"><span id="g-low">Poor fit</span><span class="bar" aria-hidden="true"></span><span id="g-high">Good fit</span>
      <span class="unk"><i aria-hidden="true"></i><span id="g-unk">No data</span></span></div>
    <select class="g-layer" id="g-layer" aria-label="Color the map by"></select>
  </div>
  <section class="g-sheet" aria-label="Details"></section>
</div>
<div id="cover" hidden><p>Page closed.</p></div>
<script src="vendor/maplibre-gl.js"></script>
<script src="vendor/topojson-client.min.js"></script>
<script src="fit.js"></script>
<script src="i18n.js"></script>
<script src="standalone_backend.js"></script>
<script src="globe.js"></script>
<script>document.body.classList.add("on-globe"); FootingGlobe.show();</script>
"""


def receipt() -> dict:
    """The recorded Christiansburg receipt, built from fixtures exactly as replay mode builds it."""
    import os
    os.environ.setdefault("FOOTING_MODE", "replay")
    from footing.pipeline import build_receipt  # noqa: E402  (needs the env var first)
    return build_receipt(37.1299, -80.4089)


def main(out: Path, wrap: bool = True) -> None:
    if out.exists():
        shutil.rmtree(out)
    (out / "vendor").mkdir(parents=True)
    (out / "data").mkdir()
    for f in ("fit.js", "i18n.js", "globe.js"):
        shutil.copy(WEB / f, out / f)
    shutil.copy(ROOT / "demo" / "standalone_backend.js", out / "standalone_backend.js")
    for f in ("maplibre-gl.js", "topojson-client.min.js", "MAPLIBRE-LICENSE.txt", "TOPOJSON-CLIENT-LICENSE.txt"):
        shutil.copy(WEB / "vendor" / f, out / "vendor" / f)
    for f in ("states-10m.json", "countries-110m.json", "US-ATLAS-LICENSE.txt", "WORLD-ATLAS-LICENSE.txt"):
        shutil.copy(WEB / "data" / f, out / "data" / f)
    policy = {"states": json.loads((STATIC / "state_policy.json").read_text()),
              "eligibility": json.loads((STATIC / "eligibility.json").read_text())}
    (out / "data" / "policy.json").write_text(json.dumps(policy, separators=(",", ":")))
    (out / "data" / "towns.json").write_text(json.dumps(TOWNS))
    try:
        (out / "data" / "receipt-christiansburg.json").write_text(json.dumps(receipt(), default=str))
    except Exception as e:  # the globe still works; the town just shows no place markers
        print(f"warning: could not build the Christiansburg receipt ({e}); town markers will be missing")
    page = (SHELL.replace("@@MAPLIBRE_CSS@@", (WEB / "vendor" / "maplibre-gl.css").read_text())
                 .replace("@@GLOBE_CSS@@", (WEB / "globe.css").read_text()))
    if wrap:   # a plain web server needs a full document; the Artifact host adds its own skeleton (use --fragment)
        page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'
                + page + "</body></html>")
    (out / "index.html").write_text(page)
    print(f"built {out} ({sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) // 1024} KB)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(Path(args[0] if args else "out/demo"), wrap="--fragment" not in sys.argv)
