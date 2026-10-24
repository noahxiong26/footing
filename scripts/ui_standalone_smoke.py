"""Click through the no-server demo built by scripts/build_standalone_demo.py.

    python scripts/build_standalone_demo.py out/demo
    python -m http.server -d out/demo 8799 &
    python scripts/ui_standalone_smoke.py http://localhost:8799 out/standalone

Steps (HANDOFF section 8, task 1): intro -> About you -> Show my map -> a state -> Zoom in on Virginia
(Christiansburg place dots must appear) -> Rate a place -> Hide. Also checks Spanish, that nothing calls
/api (there is no server), and that the profile never leaves the page. Exit 1 on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8799"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/standalone")
OUT.mkdir(parents=True, exist_ok=True)
ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
OFFLINE_OK = ("fonts.g",)
SECRET_WORDS = ("undocumented", "mixed", "pregnant", "no_id", "household", "priorities")


def run() -> int:
    errors: list[str] = []
    urls: list[str] = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=ARGS)
        page = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1).new_page()
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
        shot("01_intro", 1200)

        page.click("[data-go=profile]")
        page.check("input[name=status][value=undocumented]")
        page.click("[data-chip='household.kids']")
        shot("02_about_you")
        page.click("[data-go=save]")
        page.wait_for_selector(".g-list .g-row")
        page.wait_for_timeout(4000)
        shot("03_top_fits")

        page.click("#g-listbtn")
        page.wait_for_selector(".g-list .g-row >> nth=50")
        page.click("[data-state=VA]")
        page.wait_for_selector("#g-state-title")
        assert "Virginia" in page.inner_text("#g-state-title")
        page.wait_for_timeout(2500)
        shot("04_virginia")

        page.click("[data-go=fly]")
        page.wait_for_timeout(4200)                                   # 3.5 s fly-in
        page.evaluate("FootingGlobe._state.map.fire('moveend')")      # make sure the town check runs
        try:
            page.wait_for_selector(".g-place", timeout=8000)
        except Exception:
            errors.append("zoomed into Virginia but no Christiansburg place dots appeared")
        n_places = page.locator(".g-place").count()
        shot("05_christiansburg_places", 1200)

        page.click("[data-go=rate]")
        page.wait_for_selector(".g-pick")                            # short sheet: map stays tappable
        sheet_top = page.evaluate("document.querySelector('.g-sheet').getBoundingClientRect().top")
        if sheet_top < 844 * 0.45:
            errors.append(f"rating sheet covers the map before a spot is picked (top={sheet_top:.0f}px)")
        page.mouse.click(195, int((110 + sheet_top) / 2))            # tap the map between header and sheet
        page.wait_for_selector("[data-star=overall]", timeout=5000)
        page.click("[data-star=overall][data-n='4']")
        page.click("[data-tag=spanish_spoken]")
        shot("06_rate")
        page.click("[data-go=send]")
        page.wait_for_selector("#g-state-title", timeout=8000)
        toast = page.locator(".g-toast").inner_text() if page.locator(".g-toast").count() else ""
        shot("07_after_rating")
        heat = page.evaluate("FootingGlobe._state.heat")
        if not (heat and heat.get("total", 0) >= 1):
            errors.append(f"rating did not reach the heatmap: {heat}")
        if "this device" not in toast.lower():
            errors.append(f"standalone rating toast should say it stays on this device, got: {toast!r}")

        page.click("#g-lang")
        page.wait_for_selector("text=Por qué esta calificación")
        shot("08_spanish")
        page.click("#g-lang")

        page.click("#g-hide")
        page.wait_for_timeout(500)
        if not page.is_visible("#cover"):
            errors.append("Hide did not cover the page")
        shot("09_hidden")
        b.close()

    for u in urls:
        if "/api/" in u:
            errors.append(f"standalone page called a server API: {u[:120]}")
        low = u.lower()
        for w in SECRET_WORDS:
            if w in low and "maplibre" not in low:
                errors.append(f"'{w}' left the page in {u[:120]}")
    if errors:
        print("FAIL:\n  " + "\n  ".join(errors[:30]))
        return 1
    print(f"OK: standalone demo, {len(list(OUT.glob('*.png')))} screens, {n_places} place dots in Christiansburg, "
          f"{len(urls)} requests, none to /api, no profile data sent")
    return 0


if __name__ == "__main__":
    sys.exit(run())
