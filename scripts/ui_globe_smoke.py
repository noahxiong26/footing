"""Drive the globe at phone and desktop size, screenshot each step, and check privacy.

Usage: start the server (FOOTING_MODE=replay FOOTING_RATINGS_DB=/tmp/r.sqlite uvicorn footing.api:app --port 8765),
then:   python scripts/ui_globe_smoke.py http://localhost:8765 out/globe
Fails (exit 1) on a page error, a missing element, or if the person's status or situation ever leaves the
browser in any request URL or body. Satellite/label tiles and web fonts may fail offline; that is allowed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/globe")
OUT.mkdir(parents=True, exist_ok=True)
OFFLINE_OK = ("tiles.maps.eox.at", "basemaps.cartocdn.com", "fonts.g")
SECRET_WORDS = ("undocumented", "mixed", "status", "pregnant", "no_id", "situation", "household", "priorities")
ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


def run() -> int:
    errors: list[str] = []
    sent: list[dict] = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=ARGS)
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(f"page error: {e} @ {page.url} :: {(e.stack or "")[:600]}"))
        page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error"
                and "Failed to load resource" not in m.text and "net::" not in m.text else None)
        page.on("requestfailed", lambda r: None if any(h in r.url for h in OFFLINE_OK)
                else errors.append(f"request failed: {r.url}"))
        page.on("request", lambda r: sent.append({"url": r.url, "body": r.post_data or ""}))

        def shot(name: str, full: bool = False, wait: int = 900):
            page.wait_for_timeout(wait)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)

        page.goto(f"{BASE}/#/")
        page.wait_for_selector(".g-sheet h1")
        page.wait_for_function("window.FootingGlobe._state.mapOk === true", timeout=20000)
        page.evaluate("FootingGlobe._state.spinning = false")
        shot("01_intro", wait=1200)

        assert page.is_visible("a[href='#/start']"), "intro is missing the help-near-me link"
        page.click("[data-go=profile]")
        page.check("input[name=status][value=undocumented]")
        page.click("[data-chip='household.kids']")
        page.click("[data-chip='household.mixed']")
        before = page.inner_text(".g-pri")
        page.click(".g-pri li:nth-child(3) [data-dir='-1']")           # move 3rd priority up
        after = page.inner_text(".g-pri")
        assert before != after, "priority order did not change"
        page.evaluate("document.querySelector('.g-sheet').scrollTop = 0")
        shot("02_profile")
        page.locator(".g-pri").scroll_into_view_if_needed()
        shot("03_priorities")

        page.click("[data-go=save]")
        page.wait_for_selector(".g-list .g-row")
        page.wait_for_timeout(4500)                                     # fly from space + lights coming on
        shot("04_top_fits", wait=500)
        stored = page.evaluate("JSON.parse(localStorage.getItem('footing.globe.profile'))")
        assert stored["status"] == "undocumented" and stored["household"]["kids"] is True

        page.click(".g-list .g-row >> nth=0")
        page.wait_for_selector("#g-state-title")
        page.wait_for_timeout(2500)
        shot("05_state_detail")
        page.evaluate("document.querySelector('.g-sheet').scrollTop = 520")
        shot("06_state_why")
        page.evaluate("document.querySelector('.g-sheet').scrollTop = 1400")
        shot("07_state_programs")

        page.select_option("#g-layer", "shelter")
        assert page.inner_text("#g-low") != "Poor fit", "legend did not follow the layer"
        page.evaluate("document.querySelector('.g-sheet').scrollTop = 0")
        shot("08_layer_shelter", wait=1200)
        page.select_option("#g-layer", "fit")

        page.click("#g-lang")
        page.wait_for_selector("text=Ayuda que puedes usar")
        shot("09_spanish")
        # Legend labels must never sit under the layer picker (the old Spanish "Sin datos" bug), at 390 and 320 px.
        for w in (390, 320):
            page.set_viewport_size({"width": w, "height": 844})
            page.wait_for_timeout(300)
            for lang_pass in range(2):
                hit = page.evaluate("""() => {
                  const r = (e) => e.getBoundingClientRect(), sel = r(document.querySelector('#g-layer'));
                  return ['#g-low', '#g-high', '#g-unk'].filter((id) => { const b = r(document.querySelector(id));
                    return b.right > sel.left && b.left < sel.right && b.bottom > sel.top && b.top < sel.bottom; }); }""")
                if hit:
                    errors.append(f"legend {hit} covered by the layer picker at {w}px ({'es' if lang_pass == 0 else 'en'})")
                page.click("#g-lang")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_selector("text=Ayuda que puedes usar")                # loop above ends in Spanish
        if "hours/week" in page.inner_text(".g-sheet"):
            errors.append("Spanish state view still shows the English 'why' sentence for rent")
        page.click("#g-lang")

        page.click("#g-listbtn")
        page.wait_for_selector(".g-list .g-row >> nth=50")
        shot("10_list")

        # Rate a place in Christiansburg (from the receipt's "Rate this place" link).
        page.goto(f"{BASE}/#/rate?lat=37.1299&lon=-80.4089")
        page.wait_for_selector("[data-star=overall]")
        page.wait_for_timeout(2500)
        page.click("[data-star=overall][data-n='4']")
        page.click("[data-star=safe][data-n='5']")
        page.click("[data-tag=spanish_spoken]")
        shot("11_rate")
        page.click("[data-go=send]")
        page.wait_for_selector("#g-state-title")
        page.wait_for_timeout(1500)
        shot("12_after_rating")
        heat = page.evaluate("FootingGlobe._state.heat")
        assert heat and heat["total"] >= 1, heat

        # Classic flow still works and links back.
        page.goto(f"{BASE}/#/receipt?lat=37.1299&lon=-80.4089")
        page.wait_for_selector(".receipt")
        assert page.is_visible("text=Rate this place") and page.is_hidden("#globe-root")
        page.goto(f"{BASE}/#/")
        page.wait_for_selector("#g-state-title, .g-list, .g-sheet h2")

        # "Forget my answers" wipes the profile from this phone.
        page.evaluate("FootingGlobe._state.view = 'profile'")
        page.click("#g-lang"); page.click("#g-lang")                    # re-render in profile view
        page.click("[data-go=forget]")
        assert page.evaluate("localStorage.getItem('footing.globe.profile')") is None
        assert page.evaluate("localStorage.getItem('footing.device')") is None

        # Desktop (separate context at 1x so software WebGL stays fast).
        desk = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
        d = desk.new_page()
        d.on("pageerror", lambda e: errors.append(f"page error (desktop): {e}"))
        d.on("request", lambda r: sent.append({"url": r.url, "body": r.post_data or ""}))
        d.goto(f"{BASE}/#/")
        d.wait_for_function("window.FootingGlobe._state.mapOk === true", timeout=20000)
        d.click("[data-go=skip]")
        d.wait_for_timeout(4500)
        d.click(".g-list .g-row >> nth=1")
        d.wait_for_timeout(2600)
        d.screenshot(path=str(OUT / "13_desktop_state.png"))
        b.close()

    # Privacy: the profile never leaves the device. Only /api/ratings has a body, and it has fixed keys only.
    for r in sent:
        low = (r["url"] + " " + r["body"]).lower()
        if "/api/ratings" in r["url"] and r["body"]:
            keys = set(json.loads(r["body"]))
            if not keys <= {"lat", "lon", "device", "overall", "safe", "respect", "help", "tags"}:
                errors.append(f"rating sent extra fields: {keys}")
            continue
        for w in SECRET_WORDS:
            if w in low and "maplibre" not in low and "fonts.g" not in low:
                errors.append(f"'{w}' left the device in {r['url'][:120]}")
    if errors:
        print("FAIL:\n  " + "\n  ".join(errors[:40]))
        return 1
    print(f"OK: {len(list(OUT.glob('*.png')))} screens in {OUT}; {len(sent)} requests checked, no profile data sent")
    return 0


if __name__ == "__main__":
    sys.exit(run())
