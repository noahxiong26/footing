"""Click the Virginia app through a real browser, at phone and desktop sizes, in English and Arabic.

Usage: start the server
    FOOTING_MODE=replay FOOTING_RATINGS_DB=/tmp/r.sqlite uvicorn footing.api:app --port 8765
then
    python scripts/ui_globe_smoke.py http://localhost:8765 out/globe

Walks intro -> profile -> top 5 -> locality -> mosaic -> Details -> list + search -> rate (pin by tapping the map,
including taps that must be refused) -> send -> forget, at 320, 390 and 1280 px, in English and in Arabic
(right-to-left). Screenshots every step into OUT.

Fails (exit 1) on a page error, a missing element, horizontal overflow, the legend hidden under the layer
picker, wrong text direction, or if any profile word (status, household, situation, priorities) ever leaves
the browser in a request URL or body. Satellite/label tiles and web fonts may fail offline; that is allowed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/globe")
OUT.mkdir(parents=True, exist_ok=True)
OFFLINE_OK = ("tiles.maps.eox.at", "basemaps.cartocdn.com", "fonts.g", "demotiles.maplibre.org")
SECRET_WORDS = ("undocumented", "mixed", "status", "pregnant", "no_id", "situation", "household", "priorities")
ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
WIDTHS = (320, 390, 1280)
LANGS = ("en", "ar")
CHRISTIANSBURG = (37.1299, -80.4089)

# Run in the page: everything that must hold on every screen, whatever the width or language.
LAYOUT_CHECK = """() => {
  const out = [], vw = window.innerWidth;
  const de = document.documentElement;
  if (de.scrollWidth > vw + 1) out.push('page scrolls sideways: ' + de.scrollWidth + ' > ' + vw);
  const sh = document.querySelector('.g-sheet');
  if (sh) {
    if (sh.scrollWidth > sh.clientWidth + 1) out.push('sheet content wider than the sheet: ' + sh.scrollWidth + ' > ' + sh.clientWidth);
    const r = sh.getBoundingClientRect();
    if (r.left < -1 || r.right > vw + 1) out.push('sheet off screen: ' + Math.round(r.left) + '..' + Math.round(r.right));
    // Any visible button or link inside the sheet that sticks out past its edges.
    sh.querySelectorAll('button, a, input, select, .g-chip').forEach((e) => {
      const b = e.getBoundingClientRect();
      if (b.width && (b.right > r.right + 1 || b.left < r.left - 1)) out.push('control sticks out: ' + (e.textContent || e.tagName).trim().slice(0, 40));
    });
  }
  // The top bar holds the Hide button, the quick exit: every control in it must be fully on screen.
  document.querySelectorAll('.g-top > *').forEach((e) => {
    const b = e.getBoundingClientRect();
    if (b.width && (b.left < -1 || b.right > vw + 1)) out.push('top bar control off screen: ' + (e.id || e.className) + ' ' + Math.round(b.left) + '..' + Math.round(b.right));
  });
  const leg = document.querySelector('.g-legend'), sel = document.querySelector('#g-layer');
  if (leg && !leg.hidden && sel) {
    const s = sel.getBoundingClientRect();
    ['#g-low', '#g-high', '#g-unk'].forEach((id) => {
      const b = document.querySelector(id).getBoundingClientRect();
      if (b.width && b.right > s.left && b.left < s.right && b.bottom > s.top && b.top < s.bottom) out.push('legend ' + id + ' under the layer picker');
    });
  }
  return out;
}"""


def run() -> int:
    errors: list[str] = []
    sent: list[dict] = []
    shots = 0
    with sync_playwright() as p:
        b = p.chromium.launch(args=ARGS)
        for lang in LANGS:
            for w in WIDTHS:
                tag = f"{lang}_{w}"
                ctx = b.new_context(viewport={"width": w, "height": 800 if w > 900 else 844},
                                    device_scale_factor=1, locale="ar" if lang == "ar" else "en-US")
                page = ctx.new_page()
                page.on("pageerror", lambda e, tag=tag: errors.append(f"[{tag}] page error: {e}"))
                page.on("console", lambda m, tag=tag: errors.append(f"[{tag}] console: {m.text}") if m.type == "error"
                        and "Failed to load resource" not in m.text and "net::" not in m.text else None)
                page.on("requestfailed", lambda r, tag=tag: None if any(h in r.url for h in OFFLINE_OK)
                        else errors.append(f"[{tag}] request failed: {r.url}"))
                page.on("request", lambda r: sent.append({"url": r.url, "body": r.post_data or ""}))

                def shot(name: str, wait: int = 500):
                    nonlocal shots
                    page.wait_for_timeout(wait)
                    page.screenshot(path=str(OUT / f"{tag}_{name}.png"))
                    shots += 1
                    for problem in page.evaluate(LAYOUT_CHECK):
                        errors.append(f"[{tag}] {name}: {problem}")

                def check(cond: bool, msg: str):
                    if not cond:
                        errors.append(f"[{tag}] {msg}")

                # Language is chosen before the app starts, the way a returning person's phone would have it.
                page.add_init_script(f"try {{ localStorage.setItem('footing.lang', JSON.stringify('{lang}')); }} catch (e) {{}}")
                page.goto(f"{BASE}/#/")
                page.wait_for_selector(".g-sheet h1")
                page.wait_for_function("window.FootingGlobe._state.mapOk === true", timeout=30000)
                page.evaluate("FootingGlobe._state.spinning = false")
                want_dir = "rtl" if lang == "ar" else "ltr"
                check(page.evaluate("document.documentElement.dir") == want_dir, f"dir is not {want_dir}")
                check(page.evaluate("document.documentElement.lang") == lang, f"lang attribute is not {lang}")
                if lang == "ar":
                    check(page.evaluate("getComputedStyle(document.querySelector('.g-sheet')).direction") == "rtl",
                          "sheet text is not laid out right-to-left")
                    check(page.is_visible(".g-machine"), "Arabic screen does not say it is machine translated")
                shot("01_intro", 1000)

                # Profile: status, household, situation, a priority moved up.
                page.click("[data-go=profile]")
                page.check("input[name=status][value=undocumented]")
                page.click("[data-chip='household.kids']")
                page.click("[data-chip='household.mixed']")
                page.click("[data-chip='situation.car']")
                before = page.inner_text(".g-pri")
                page.click(".g-pri li:nth-child(3) [data-pri][data-dir='-1']") if page.locator(
                    ".g-pri li:nth-child(3) [data-pri][data-dir='-1']").count() else page.click(".g-pri li:nth-child(3) button >> nth=0")
                check(page.inner_text(".g-pri") != before, "priority order did not change")
                page.evaluate("document.querySelector('.g-sheet').scrollTop = 0")
                shot("02_profile")
                page.locator(".g-pri").scroll_into_view_if_needed()
                shot("03_priorities")

                # Top 5.
                page.click("[data-go=save]")
                page.wait_for_selector(".g-list .g-row")
                page.wait_for_timeout(3500)
                check(page.locator(".g-list .g-row").count() == 5, "top view does not show exactly 5 places")
                stored = page.evaluate("JSON.parse(localStorage.getItem('footing.globe.profile'))")
                check(stored["status"] == "undocumented" and stored["household"]["kids"] is True
                      and stored["situation"]["car"] is True, "profile was not saved on the device")
                shot("04_top5")

                # A locality: score, mosaic, Details.
                page.click(".g-list .g-row >> nth=0")
                page.wait_for_selector("#g-loc-title")
                page.wait_for_timeout(1800)
                check(page.locator(".g-c2s .g-c2").count() >= 5, "locality shows fewer than 5 parts")
                check(page.locator(".g-mosaic, .g-mos, [class*=mosaic]").count() >= 1, "no score mosaic")
                shot("05_locality")
                d = page.locator(".g-c2 details >> nth=0")
                d.locator("summary").click()
                check(d.evaluate("e => e.open"), "Details did not open")
                check(len(d.locator("p[lang=en]").inner_text().strip()) > 20, "Details has no reason text")
                d.scroll_into_view_if_needed()
                shot("06_details")

                # The full list and search.
                page.click("#g-listbtn")
                page.wait_for_selector("#g-q")
                n_all = page.locator(".g-list li").count()
                check(n_all == 133, f"list shows {n_all} places, not 133")
                page.fill("#g-q", "Roanoke")
                page.wait_for_timeout(200)
                shown = page.locator(".g-list li:visible").all_inner_texts()
                check(len(shown) == 2 and all("Roanoke" in s for s in shown), f"search 'Roanoke' shows {shown}")
                shot("07_search")
                page.fill("#g-q", "zzzz")
                page.wait_for_timeout(200)
                check(page.locator(".g-list li:visible").count() == 0 and page.is_visible(".g-nomatch"),
                      "search with no match does not say so")
                page.fill("#g-q", "")
                page.click(".g-list li:visible >> nth=2")
                page.wait_for_selector("#g-loc-title")

                # Rate: open from the locality, then tap the map. Bad taps must be refused with the right reason.
                page.click("[data-go=rate]")
                page.wait_for_selector(".g-sheet h2")
                shot("08_rate_prompt", 800)

                def tap(lat: float, lon: float) -> str:
                    page.evaluate("""([lat, lon]) => { const m = FootingGlobe._state.map;
                      m.jumpTo({center: [lon, lat], zoom: 12});
                      m.fire('click', {lngLat: new maplibregl.LngLat(lon, lat), point: m.project([lon, lat])}); }""", [lat, lon])
                    page.wait_for_timeout(250)
                    t = page.locator(".g-toast")
                    return t.inner_text() if t.count() else ""

                msg = tap(39.29, -76.61)                       # Baltimore
                check(page.evaluate("FootingGlobe._state.ratingPoint") is None and msg != "", "a tap in Maryland was not refused")
                if lang == "ar":
                    check(any("\u0600" <= ch <= "\u06ff" for ch in msg), f"Maryland refusal is not in Arabic: {msg!r}")
                msg = tap(37.0, -75.7)                          # Atlantic, off the Eastern Shore
                check(page.evaluate("FootingGlobe._state.ratingPoint") is None and msg != "", "a tap on open water was not refused")
                if lang == "ar":
                    check(any("\u0600" <= ch <= "\u06ff" for ch in msg), f"open-water refusal is not in Arabic: {msg!r}")
                else:
                    check("open water" in msg, f"open-water tap gave the wrong reason: {msg!r}")
                tap(*CHRISTIANSBURG)
                page.wait_for_selector("[data-star=overall]")
                rp = page.evaluate("FootingGlobe._state.ratingPoint")
                check(rp and rp["fips"] == "51121", f"Christiansburg tap landed in {rp and rp['fips']}, not Montgomery County")
                check(page.is_disabled("[data-go=send]"), "Send is enabled before an overall rating")
                page.click("[data-star=overall][data-n='4']")
                page.click("[data-star=safe][data-n='5']")
                page.click("[data-tag=spanish_spoken]")
                check(page.is_enabled("[data-go=send]"), "Send stays disabled after an overall rating")
                shot("09_rate_filled")
                total_before = (page.evaluate("FootingGlobe._state.heat") or {}).get("total", 0)
                with page.expect_response(lambda r: "/api/ratings" in r.url and r.request.method == "POST") as resp:
                    page.click("[data-go=send]")
                check(resp.value.status == 200, f"rating POST returned {resp.value.status}")
                page.wait_for_timeout(1500)
                heat = page.evaluate("FootingGlobe._state.heat") or {}
                check(heat.get("total", 0) == total_before + 1, f"heat total {heat.get('total')} did not go up by one")
                check(page.evaluate("FootingGlobe._state.view") != "rate", "still on the rate screen after sending")
                shot("10_after_rating", 800)

                # Forget my answers.
                page.click("#g-listbtn")                        # back to the map view first
                page.evaluate("FootingGlobe._state.view = 'profile'")
                page.evaluate("document.querySelector('#g-lang').dispatchEvent(new Event('change'))")
                page.wait_for_selector("[data-go=forget]")
                page.click("[data-go=forget]")
                check(page.evaluate("localStorage.getItem('footing.globe.profile')") is None, "forget left the profile behind")
                check(page.evaluate("localStorage.getItem('footing.device')") is None, "forget left the device token behind")
                check(page.evaluate("JSON.parse(localStorage.getItem('footing.lang'))") == lang, "forget also wiped the language")
                ctx.close()
        b.close()

    # Privacy: the profile never leaves the device. Only /api/ratings has a body, and it has fixed keys only.
    for r in sent:
        low = (r["url"] + " " + r["body"]).lower()
        if "/api/ratings" in r["url"] and r["body"]:
            keys = set(json.loads(r["body"]))
            if not keys <= {"lat", "lon", "device", "overall", "safe", "respect", "help", "tags"}:
                errors.append(f"rating sent extra fields: {keys}")
            continue
        for word in SECRET_WORDS:
            if word in low and "maplibre" not in low and "fonts.g" not in low:
                errors.append(f"'{word}' left the device in {r['url'][:120]}")
    if errors:
        print("FAIL:\n  " + "\n  ".join(dict.fromkeys(errors)))
        return 1
    print(f"OK: {shots} screens in {OUT} ({len(LANGS)} languages x {len(WIDTHS)} widths); "
          f"{len(sent)} requests checked, no profile data sent")
    return 0


if __name__ == "__main__":
    sys.exit(run())
