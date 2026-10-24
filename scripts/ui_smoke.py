"""Drive the PWA in headless Chromium at phone size and screenshot every screen.

Usage: start the server (FOOTING_MODE=replay uvicorn footing.api:app --port 8765), then
  python scripts/ui_smoke.py http://localhost:8765 out/screens
Fails (exit 1) on any console error or missing element.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/screens")
OUT.mkdir(parents=True, exist_ok=True)
Q = "lat=37.1299&lon=-80.4089"


def main() -> int:
    errors: list[str] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(m.text)
                if m.type == "error" and "Failed to load resource" not in m.text else None)
        # Network failures are judged by URL: web fonts may be blocked offline; nothing else may fail.
        page.on("requestfailed", lambda r: errors.append(f"request failed: {r.url}")
                if "fonts.g" not in r.url else None)
        page.on("response", lambda r: errors.append(f"HTTP {r.status}: {r.url}")
                if r.status >= 400 and "/api/flyer" not in r.url else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        def shot(name: str, full: bool = True):
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)

        page.goto(f"{BASE}/#/start")                # "#/" is the globe now; the classic start screen lives here
        page.wait_for_selector("#locate")
        page.click("[data-chip=kids]")
        assert page.get_attribute("[data-chip=kids]", "aria-pressed") == "true"
        shot("1_start", full=False)

        page.click("[data-town='0']")
        page.wait_for_selector(".receipt")
        assert "SETTLE RECEIPT" in page.inner_text(".receipt")
        page.click("[data-cat='0']")
        assert page.is_visible("#cat-0")
        shot("2_receipt")

        page.goto(f"{BASE}/#/plan?{Q}&profile=kids")
        page.wait_for_selector(".step")
        page.check(".step input >> nth=0")
        shot("3_plan", full=False)

        page.goto(f"{BASE}/#/tonight?{Q}")
        page.wait_for_selector("text=Call 211 now")
        shot("4_tonight", full=False)

        page.goto(f"{BASE}/#/card?{Q}")
        page.wait_for_selector(".card-frame img")
        page.wait_for_function("document.querySelector('.card-frame img').naturalWidth > 0")
        shot("5_pocket_card", full=False)

        page.goto(f"{BASE}/#/compare?{Q}")
        page.wait_for_selector("[data-o]")
        page.click("[data-o='37.271,-79.9414']")
        page.wait_for_selector(".cmp table")
        shot("6_compare")

        page.goto(f"{BASE}/#/flyer")
        page.wait_for_selector("#photo")
        shot("7_flyer", full=False)
        b.close()
    if errors:
        print("Console errors:\n  " + "\n  ".join(errors))
        return 1
    print(f"OK: 7 screens in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
