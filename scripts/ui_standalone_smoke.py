"""Click through the no-server demo built by scripts/build_standalone_demo.py.

    python scripts/build_standalone_demo.py out/demo
    python -m http.server -d out/demo 8799 &
    python scripts/ui_standalone_smoke.py http://localhost:8799 out/standalone

Steps: intro -> About you -> top 5 -> list + search -> Montgomery County -> zoom into Christiansburg (the
recorded town's place dots must appear) -> Rate a place, picking the spot with a real mouse tap on the map ->
send -> Spanish -> Hide. Also checks that nothing calls /api (there is no server), and that the profile never
leaves the page. Exit 1 on any failure.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8799"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/standalone")
OUT.mkdir(parents=True, exist_ok=True)
ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
OFFLINE_OK = ("fonts.g", "tiles.maps.eox.at", "basemaps.cartocdn.com")
SECRET_WORDS = ("undocumented", "mixed", "pregnant", "no_id", "household", "priorities")
CHRISTIANSBURG = (37.1299, -80.4089)
H = 844


def run() -> int:
    errors: list[str] = []
    urls: list[str] = []
    n_places = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=ARGS, channel=os.environ.get("FOOTING_BROWSER_CHANNEL"))
        page = b.new_context(viewport={"width": 390, "height": H}, device_scale_factor=1).new_page()
        page.on("pageerror", lambda e: errors.append(f"page error: {e}"))
        page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error"
                and "Failed to load resource" not in m.text and "net::" not in m.text else None)
        page.on("requestfailed", lambda r: None if any(h in r.url for h in OFFLINE_OK)
                else errors.append(f"request failed: {r.url}"))
        page.on("request", lambda r: urls.append(r.url + " " + (r.post_data or "")))

        def shot(name: str, wait: int = 700):
            page.wait_for_timeout(wait)
            page.screenshot(path=str(OUT / f"{name}.png"))

        page.goto(BASE + "/")
        page.wait_for_selector(".g-sheet h1")
        page.wait_for_function("window.FootingGlobe._state.mapOk === true", timeout=25000)
        page.evaluate("FootingGlobe._state.spinning = false")
        if page.locator("a[href='#/start']").count():
            errors.append("standalone intro links to 'help near me', which needs the server")
        shot("01_intro", 1200)

        page.click("[data-go=profile]")
        page.check("input[name=status][value=undocumented]")
        page.click("[data-chip='household.kids']")
        page.click("[data-crime='1']")
        shot("02_about_you")
        page.click("[data-go=save]")
        page.wait_for_selector(".g-sheet .g-list .g-row")
        page.wait_for_timeout(3500)
        if page.locator(".g-sheet .g-list .g-row").count() != 5:
            errors.append("top view does not show 5 places")
        shot("03_top_fits")

        page.click(".g-nav [data-nav=list]")
        page.wait_for_selector("#g-q")
        page.fill("#g-q", "Norfolk")
        page.click(".g-sheet .g-list li:visible >> nth=0")
        page.wait_for_selector("#g-loc-title")
        page.wait_for_timeout(400)
        page.evaluate("""() => { const m = FootingGlobe._state.map; m.stop();
          const c = m.getCanvas().getBoundingClientRect();
          const top = document.querySelector('.g-sheet').getBoundingClientRect().top;
          m.easeTo({center: [-76.2859, 36.8508], zoom: 12, duration: 0,
            padding: {top: 0, bottom: 0, left: 0, right: 0},
            offset: [0, (110 + top) / 2 - (c.top + c.height / 2)]}); }""")
        page.wait_for_timeout(500)
        x, y = page.evaluate("""() => { const m = FootingGlobe._state.map, p = m.project([-76.2859, 36.8508]),
          c = m.getCanvas().getBoundingClientRect(); return [c.left + p.x, c.top + p.y]; }""")
        page.mouse.click(x, y)
        page.wait_for_selector(".g-point-note")
        crime = page.locator("[data-component=crime]")
        if "violent incidents" not in crime.locator(".line").inner_text():
            errors.append("standalone map tap did not show block incidents")
        crime.scroll_into_view_if_needed()
        shot("03b_norfolk_blocks")
        page.click(".g-nav [data-nav=list]")
        page.wait_for_selector("#g-q")
        page.fill("#g-q", "Montgomery")
        page.wait_for_timeout(200)
        page.click(".g-sheet .g-list li:visible >> nth=0")
        page.wait_for_selector("#g-loc-title")
        if "Montgomery" not in page.inner_text("#g-loc-title"):
            errors.append(f"search led to {page.inner_text('#g-loc-title')!r}, not Montgomery County")
        if page.locator("a[href^='#/receipt']").count():
            errors.append("standalone locality links to the receipt, which needs the server")
        shot("04_montgomery", 1800)

        # Zoom into the recorded town: its places (shelter, food, clinic...) appear as dots from zoom 10.5.
        page.evaluate("""([lat, lon]) => { const m = FootingGlobe._state.map; m.jumpTo({center: [lon, lat], zoom: 12});
                         m.fire('zoomend'); }""", list(CHRISTIANSBURG))
        try:
            page.wait_for_selector(".g-place", timeout=8000)
        except Exception:
            errors.append("zoomed into Christiansburg but no place dots appeared")
        n_places = page.locator(".g-place").count()
        shot("05_christiansburg_places", 1200)

        page.click("[data-go=rate]")
        page.wait_for_timeout(400)
        sheet_top = page.evaluate("document.querySelector('.g-sheet').getBoundingClientRect().top")
        if sheet_top < H * 0.45:
            errors.append(f"rating sheet covers the map before a spot is picked (top={sheet_top:.0f}px)")
        shot("06_rate_prompt")
        # A real tap, through the canvas, on Christiansburg - moved into the open strip of map first.
        page.evaluate("""([lat, lon, top]) => { const m = FootingGlobe._state.map;
            const y = (110 + top) / 2, c = m.getCanvas().getBoundingClientRect();
            m.easeTo({center: [lon, lat], zoom: 12, duration: 0,
              padding: {top: 0, bottom: 0, left: 0, right: 0}, offset: [0, y - (c.top + c.height / 2)]}); }""",
                      [*CHRISTIANSBURG, sheet_top])
        page.wait_for_timeout(300)
        x, y = page.evaluate("""([lat, lon]) => { const m = FootingGlobe._state.map, p = m.project([lon, lat]),
            c = m.getCanvas().getBoundingClientRect(); return [c.left + p.x, c.top + p.y]; }""", list(CHRISTIANSBURG))
        page.mouse.click(x, y)
        try:
            page.wait_for_selector("[data-star=overall]", timeout=5000)
        except Exception:
            errors.append(f"a tap on Christiansburg at ({x:.0f},{y:.0f}) did not set a rating spot")
            b.close()
            return report(errors, urls, 0)
        rp = page.evaluate("FootingGlobe._state.ratingPoint")
        if not rp or rp.get("fips") != "51121":
            errors.append(f"tap on Christiansburg filed under {rp and rp.get('fips')}, not Montgomery County (51121)")
        page.click("[data-star=overall][data-n='4']")
        page.click("[data-tag=spanish_spoken]")
        shot("07_rate")
        page.click("[data-go=send]")
        page.wait_for_function("FootingGlobe._state.view !== 'rate'", timeout=8000)
        toast = page.locator(".g-toast").inner_text() if page.locator(".g-toast").count() else ""
        shot("08_after_rating")
        heat = page.evaluate("FootingGlobe._state.heat")
        if page.locator(".g-point-note").count() != 1:
            errors.append("standalone rating pin did not become the locality point")
        if not (heat and heat.get("total", 0) >= 1):
            errors.append(f"rating did not reach the heatmap: {heat}")
        if "this device" not in toast.lower() and "montgomery" not in toast.lower():
            errors.append(f"rating toast does not say where the rating went: {toast!r}")

        page.select_option("#g-lang", "es")
        page.wait_for_timeout(400)
        if page.evaluate("document.documentElement.lang") != "es" or "Calificar" not in page.inner_text(".g-sheet"):
            errors.append("switching to Spanish did not translate the screen")
        shot("09_spanish")
        page.select_option("#g-lang", "en")

        page.click("#g-hide")
        page.wait_for_timeout(500)
        if not page.is_visible("#cover"):
            errors.append("Hide did not cover the page")
        shot("10_hidden")
        b.close()
    return report(errors, urls, n_places)


def report(errors: list[str], urls: list[str], n_places: int) -> int:
    for u in urls:
        if "/api/" in u:
            errors.append(f"standalone page called a server API: {u[:120]}")
        low = u.lower()
        for w in SECRET_WORDS:
            if w in low and "maplibre" not in low:
                errors.append(f"'{w}' left the page in {u[:120]}")
    if errors:
        print("FAIL:\n  " + "\n  ".join(dict.fromkeys(errors)))
        return 1
    print(f"OK: standalone demo, {len(list(OUT.glob('*.png')))} screens, {n_places} place dots in Christiansburg, "
          f"{len(urls)} requests, none to /api, no profile data sent")
    return 0


if __name__ == "__main__":
    sys.exit(run())
