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
import os
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
LANGS = ("en", "ar", "tl")   # Tagalog: added in S8, left-to-right, Latin script
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
        b = p.chromium.launch(args=ARGS, channel=os.environ.get("FOOTING_BROWSER_CHANNEL"))
        for lang in LANGS:
            for w in WIDTHS:
                tag = f"{lang}_{w}"
                ctx = b.new_context(viewport={"width": w, "height": 800 if w > 900 else 844},
                                    device_scale_factor=1, locale={"ar": "ar", "tl": "fil-PH"}.get(lang, "en-US"))
                page = ctx.new_page()
                page.on("pageerror", lambda e, tag=tag: errors.append(f"[{tag}] page error: {e}"))
                page.on("console", lambda m, tag=tag: errors.append(f"[{tag}] console: {m.text}") if (m.type == "error"
                        and "Failed to load resource" not in m.text and "net::" not in m.text)
                        or "Footing: no " in m.text else None)   # a missing reason template is a failure
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
                if lang != "en":
                    check(page.is_visible(".g-machine"), f"{lang} screen does not say it is machine translated")
                shot("01_intro", 1000)

                # Profile: status, household, situation, a priority moved up.
                page.click("[data-go=profile]")
                page.check("input[name=status][value=undocumented]")
                page.click("[data-chip='household.kids']")
                page.click("[data-chip='household.partner']")
                check(page.locator("[data-chip='household.mixed']").count() == 0, "the retired 'some family are citizens' option is back")
                page.fill("#g-beds", "6")                       # typed bedrooms: above HUD's 4, uses the +15% rule
                page.click("[data-chip='situation.car']")
                page.click("[data-crime='1']")
                before = page.inner_text(".g-pri")
                page.click(".g-pri li:nth-child(3) [data-pri][data-dir='-1']") if page.locator(
                    ".g-pri li:nth-child(3) [data-pri][data-dir='-1']").count() else page.click(".g-pri li:nth-child(3) button >> nth=0")
                check(page.inner_text(".g-pri") != before, "priority order did not change")
                # Drag with a real mouse: the last row to the top.
                last = page.locator(".g-pri li").last
                lk = last.get_attribute("data-k")
                src, dst = last.locator(".nm").bounding_box(), page.locator(".g-pri li").first.bounding_box()
                page.mouse.move(src["x"] + 20, src["y"] + src["height"] / 2)
                page.mouse.down()
                for i in range(1, 13):
                    page.mouse.move(src["x"] + 20, src["y"] + src["height"] / 2 + (dst["y"] - src["y"] - 6) * i / 12)
                    page.wait_for_timeout(16)
                page.mouse.up()
                page.wait_for_timeout(400)
                check(page.locator(".g-pri li").first.get_attribute("data-k") == lk, "dragging the last priority to the top did not move it")
                check(page.locator(".g-pri .w, .g-pri .wbar").count() == 0 or "%" not in page.inner_text(".g-pri"), "priorities still show percentages")
                page.evaluate("document.querySelector('.g-sheet').scrollTop = 0")
                shot("02_profile")
                page.locator(".g-pri").scroll_into_view_if_needed()
                shot("03_priorities")

                # Top 5.
                page.click("[data-go=save]")
                page.wait_for_selector(".g-sheet .g-list .g-row")
                page.wait_for_timeout(3500)
                check(page.locator(".g-sheet .g-list .g-row").count() == 5, "top view does not show exactly 5 places")
                stored = page.evaluate("JSON.parse(localStorage.getItem('footing.globe.profile'))")
                check(stored["status"] == "undocumented" and stored["household"]["kids"] is True
                      and stored["situation"]["car"] is True, "profile was not saved on the device")
                shot("04_top5")

                # A locality: score, mosaic, Details.
                page.click(".g-sheet .g-list .g-row >> nth=0")
                page.wait_for_selector("#g-loc-title")
                page.wait_for_timeout(1800)
                check(page.locator(".g-c2s .g-c2").count() >= 5, "locality shows fewer than 5 parts")
                check(page.locator(".g-mosaic, .g-mos, [class*=mosaic]").count() >= 1, "no score mosaic")
                shot("05_locality")
                d = page.locator(".g-c2 details >> nth=0")
                d.locator("summary").click()
                check(d.evaluate("e => e.open"), "Details did not open")
                check(len(d.locator("p.g-reason").inner_text().strip()) > 20, "Details has no reason text")
                # Every part's Details is in the person's language; only a labelled recorded quote may be English.
                det = page.evaluate("""(lang) => { const I = FootingI18n, s = FootingGlobe._state;
                  const r = FootingVaFit.fitScore(s.elig, s.va, s.selected, s.profile, (s.heat || {}).localities || {});
                  return [...document.querySelectorAll('.g-c2')].map(li => {
                    const c = r.components.find(x => x.id === li.dataset.component);
                    return {id: c.id, summary: li.querySelector('summary').textContent, want: I.t(lang, 'details'),
                      text: li.querySelector('p.g-reason').textContent, english: c.reason,
                      expect: I.vaReason(lang, c),
                      stray: [...li.querySelectorAll('p.g-reason [lang=en]')].filter(e => !e.classList.contains('g-quote')).length,
                      line: li.querySelector('.line').textContent}; }); }""", lang)
                for c in det:
                    check(c["summary"] == c["want"], f"{c['id']} Details heading is {c['summary']!r}, not {c['want']!r}")
                    check(c["text"] == c["expect"], f"{c['id']} Details text differs from FootingI18n.vaReason")
                    if lang != "en":
                        check(c["text"] != c["english"], f"{c['id']} Details is still English")
                        check(c["stray"] == 0, f"{c['id']} Details has unlabelled English")
                        check(c["line"] != c["english"], f"{c['id']} summary line is the raw English reason")
                d.scroll_into_view_if_needed()
                shot("06_details")

                # The full list and search.
                page.click(".g-nav [data-nav=list]")
                page.wait_for_selector("#g-q")
                n_all = page.locator(".g-sheet .g-list li").count()
                check(n_all == 133, f"list shows {n_all} places, not 133")
                page.fill("#g-q", "Roanoke")
                page.wait_for_timeout(200)
                shown = page.locator(".g-sheet .g-list li:visible").all_inner_texts()
                check(len(shown) == 2 and all("Roanoke" in s for s in shown), f"search 'Roanoke' shows {shown}")
                shot("07_search")
                page.fill("#g-q", "zzzz")
                page.wait_for_timeout(200)
                check(page.locator(".g-sheet .g-list li:visible").count() == 0 and page.is_visible(".g-nomatch"),
                      "search with no match does not say so")
                page.fill("#g-q", "")
                page.fill("#g-q", "Norfolk")
                page.click(".g-sheet .g-list li:visible >> nth=0")
                page.wait_for_selector("#g-loc-title")
                check(page.locator(".g-point-note").count() == 0, "list selection kept a previous point")
                citywide = page.locator("[data-component=crime] .num").inner_text()
                ranked_before = page.evaluate("JSON.stringify(FootingGlobe._state.byFips['51710'])")

                # A real mouse tap through the map canvas, not a direct call to a selection function.
                def tap_locality(lat: float, lon: float):
                    # The list-to-locality transition changes the exposed map area.
                    page.wait_for_timeout(400)
                    page.evaluate("""([lat, lon]) => { const m = FootingGlobe._state.map;
                      m.stop(); const c = m.getCanvas().getBoundingClientRect();
                      // Aim at the middle of the map a person can actually see: below the top bar, above the
                      // legend and the sheet. Longer labels (Tagalog at 320 px) make the legend taller.
                      const top = document.querySelector('.g-sheet').getBoundingClientRect().top;
                      const bar = document.querySelector('.g-top').getBoundingClientRect().bottom;
                      const leg = document.querySelector('.g-legend');
                      const floor = Math.min(top, leg && !leg.hidden ? leg.getBoundingClientRect().top : top);
                      const y = top > 150 ? (bar + floor) / 2 : c.top + c.height / 2;
                      m.easeTo({center: [lon, lat], zoom: 12, duration: 0, padding: {top: 0, bottom: 0, left: 0, right: 0},
                        offset: [0, y - (c.top + c.height / 2)]}); }""", [lat, lon])
                    page.wait_for_function("""([lat, lon]) => { const m = FootingGlobe._state.map;
                      return m.queryRenderedFeatures(m.project([lon, lat]), {layers: ['va-known', 'va-unknown']})
                        .some(f => String(f.id) === '51710'); }""", arg=[lat, lon])
                    x, y = page.evaluate("""([lat, lon]) => { const m = FootingGlobe._state.map,
                      p = m.project([lon, lat]), c = m.getCanvas().getBoundingClientRect();
                      return [c.left + p.x, c.top + p.y]; }""", [lat, lon])
                    page.mouse.click(x, y)
                    try:
                        page.wait_for_selector(".g-point-note", timeout=8000)
                    except Exception:
                        page.screenshot(path=str(OUT / f"{tag}_failed_point.png"))
                        print(page.evaluate("""([x, y]) => { const s = FootingGlobe._state; return {
                          selected: s.selected, point: s.selectedPoint,
                          click: [x,y], element: document.elementFromPoint(x,y).outerHTML.slice(0,200)
                        }; }""", [x, y]), flush=True)
                        raise

                tap_locality(36.8508, -76.2859)
                crime = page.locator("[data-component=crime]")
                expected = page.evaluate("""() => { const s = FootingGlobe._state;
                  return FootingVaFit.fitScore(s.elig, s.va, '51710', s.profile, {},
                    FootingVaFit.tileOf(36.8508, -76.2859)).components.find(c => c.id === 'crime'); }""")
                check(crime.locator(".num").inner_text() == str(round(expected["score"])), "point crime score differs from the engine")
                line = crime.locator(".line").inner_text()
                check(expected["parts"]["window_start"] in line and expected["parts"]["window_end"] in line,
                      "block summary omits the saved capture window")
                if lang == "en":
                    check("violent incidents" in line and "not counted as danger" in line, "no block-level crime summary")
                elif lang == "ar":
                    check(any("\u0600" <= ch <= "\u06ff" for ch in line), "block summary is not in Arabic")
                else:
                    check("violent incidents" not in line and "insidente" in line, f"block summary is not in Tagalog: {line!r}")
                crime.locator("summary").click()
                check(crime.locator("a[href='https://data.norfolk.gov/resource/r7bn-2egr.json']").count() == 1,
                      "point Details lacks the city incident source")
                reason = crime.locator("p.g-reason").inner_text()
                # The block count leads; the citywide FBI rate may follow as a comparison.
                check("Norfolk" in reason and f"{expected['parts']['violent']:,}" in reason.replace("\u202f", ","),
                      "point still shows the FBI-only reason")
                if lang == "en":
                    check("Norfolk police data" in reason, "point reason lost the city source wording")
                check(page.evaluate("JSON.stringify(FootingGlobe._state.byFips['51710'])") == ranked_before,
                      "a point changed the statewide locality ranking")
                crime.scroll_into_view_if_needed()
                shot("07b_norfolk_blocks")
                page.click("[data-go=locality-wide]")
                check(page.locator("[data-component=crime] .num").inner_text() == citywide,
                      "whole-locality button did not restore the FBI score")
                check(page.locator(".g-point-note").count() == 0, "whole-locality button kept the point note")

                # Missing FBI reports must stay Unknown, even after viewing a covered block.
                page.click(".g-nav [data-nav=list]")
                page.fill("#g-q", "Virginia Beach")
                page.click(".g-sheet .g-list li:visible >> nth=0")
                page.wait_for_selector("#g-loc-title")
                check(page.locator("[data-component=crime] .num").inner_text() == "?", "Virginia Beach crime is not Unknown")
                check(page.locator(".g-point-note").count() == 0, "a point leaked into another locality")
                page.locator("[data-component=crime]").scroll_into_view_if_needed()
                shot("07c_crime_unknown")

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
                if lang != "en":
                    want = page.evaluate("(l) => FootingI18n.t(l, 'outsideTap')", lang)
                    check(msg == want, f"Maryland refusal is not the {lang} sentence: {msg!r}")
                msg = tap(37.0, -75.7)                          # Atlantic, off the Eastern Shore
                check(page.evaluate("FootingGlobe._state.ratingPoint") is None and msg != "", "a tap on open water was not refused")
                if lang != "en":
                    want = page.evaluate("(l) => FootingI18n.t(l, 'waterTap')", lang)
                    check(msg == want, f"open-water refusal is not the {lang} sentence: {msg!r}")
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
                check(page.locator(".g-point-note").count() == 1, "rating pin did not become the locality point")
                check("FBI" in page.locator("[data-component=crime] details p").text_content(),
                      "a point without incident data did not fall back to the FBI")
                shot("10_after_rating", 800)

                # Forget my answers.
                page.click(".g-nav [data-nav=list]")                        # back to the map view first
                page.evaluate("FootingGlobe._state.view = 'profile'")
                page.evaluate("document.querySelector('#g-lang').dispatchEvent(new Event('change'))")
                page.wait_for_selector("[data-go=forget]")
                page.click("[data-go=forget]")
                # Forgetting now asks first, on the same "Start over" screen as the nav bar's button.
                page.wait_for_selector("[data-go=reset-confirm]")
                check(page.locator(".g-nav [data-nav=reset][aria-current=page]").count() == 1, "nav does not mark Start over")
                page.click("[data-go=reset-confirm]")
                check(page.evaluate("FootingGlobe._state.view") == "intro", "start over did not return to the start screen")
                check(page.evaluate("FootingGlobe._state.selected") is None, "start over kept the picked place")
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
