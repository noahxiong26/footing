# HANDOFF — Footing (read this first)

## S9.0 A clickable draft to review the UI; S8 checkpoint finished (2026-10-25, Claude Opus 5.5)

**Live demo (private to the owner until shared):** https://claude.ai/artifact/DDBbpzuwhFrMmQThLwLitN
The standalone app as a claude.ai Artifact with the `db` capability. It has the 133-locality Virginia map, the
score mosaic, translated Details in 9 languages, search, six recorded towns with place dots, and ratings. Ratings
go to the artifact's shared `ratings` collection for signed-in viewers who can write, and stay on the device
otherwise; the toast says which. Rebuild and republish with
`python scripts/build_standalone_demo.py out/demo-artifact --fragment`, then publish `out/demo-artifact/index.html`
with its files to the same URL. **The owner asked for this run to end on a presentable, interactive draft so
the next session can improve the UI from it.** `demo/SITES.json` (a ChatGPT Site) is superseded and unused.

What this session did, on top of S8's checkpoint:

- **Tests: 251 pass**, builder `--check` passes (Linux). S8 left 237/3 failed/8 errors on Windows.
  - Town captures: the manifests' sha256 values were taken over the Windows CRLF checkout, so all five failed on
    Linux. Hashes are now taken over LF text (`footing.http.content_sha256`), the recorder and manifest writers
    always write LF, `.gitattributes` pins `fixtures/**` to LF, and each file keeps its original
    `sha256_windows_crlf` (checked: same bytes apart from line endings).
  - `test_healthz_reports_demo` / `test_plan_tonight_card_compare` now expect six recorded towns; the "not
    recorded -> no score" case uses Danville instead of Roanoke.
  - The CP1252 errors: every Node subprocess call in the tests decodes UTF-8; a new test fails if one does not.
- **Locality JSON regenerated** from the reviewed ordinance ledger. Exactly 10 rows changed: nine `limited_ban`
  (35) park/facility rules (Arlington, Fairfax County, Henrico, Loudoun, Alexandria, Chesapeake, Fairfax city,
  Lynchburg, Newport News) and Bristol's corrected citation (still provisional broad/0). Fairfax County's
  clearing policy was replaced by FCPA §1.03(A); the test now says so. No locality has a clearing policy any more,
  so the translation corpus keeps that template covered with a synthetic row.
- **Details are translated in the app.** `globe.js` renders `FootingI18n.vaReasonParts`: own-language runs,
  English evidence quotes in `<span lang="en" dir="ltr" class="g-quote">` after a translated label, and the
  heading is `t("details")`. Unscored-law and fall-through summary lines use the translated runs too. A missing
  template falls back to the English reason under "Details (in English)" and logs `Footing: no <lang> reason`,
  which the smoke treats as a failure. Service-worker caches are v11.
- **Demo ships all six town receipts** (built from `fixtures/` with `recorded_sets`, not a hard-coded list).
- **`scripts/ui_globe_smoke.py` covers Tagalog** (en, ar, tl × 320/390/1280) and checks every Details card
  against `FootingI18n.vaReason`. Its map tap now aims between the top bar and the legend/sheet.

**What was and was not checked here.** `scripts/ui_standalone_smoke.py` passed on the rebuilt demo (11 screens,
21 Christiansburg dots, no /api calls, no profile data sent). The extended full-app smoke ran through en and ar
and reached Tagalog at 320 px, where the old tap heuristic hit the taller legend; that fix is in, but **the full
3-language run was not repeated** (the owner switched the run's goal to the demo). The live Artifact was
published and its `ratings` store read back (empty, as expected); **nobody has clicked the hosted page yet**,
including rating as a signed-in viewer. Native-speaker review of all 8 translations is still pending.

**Computer layout (Version 2 of the Artifact, owner request: "computer friendly instead of phone first").**
At 1100 px and wider, Virginia mode shows three columns: a persistent, searchable list of all 133 places
(`.g-rail`, rendered by `renderRail()`), the map framed to the space between the panels (`sheetPad()` measures
both panels, `syncDesk()` applies the layout before any camera move), and a wider details panel
(`--panel-w: clamp(440px, 34vw, 600px)`) with larger type and two-line mosaic labels. Arabic/Persian mirror it.
Below 1100 px nothing changed. The top bar says "Hide this page" on desktop where that label is translated
(en, es); other languages keep their short label. Smoke selectors now target `.g-sheet .g-list` so the rail's
rows do not count.
**"Page closed" on the live page:** the quick exit had been triggered (most likely the "Hide" button read as
"hide this panel"), and in the hosted demo it could not be undone. The cover now has an "Open again" link,
and its CSS only shows it when not `hidden`. Checked in Chromium at 1440 px (en, ar): 133 rail rows, a rail
click opens the place and highlights it, Hide then Open again restores the app; no page errors.

**UI notes for the next pass** (seen in the Tagalog 320 px screenshot and earlier sessions):
1. At 320 px in Tagalog the legend wraps to two lines ("Hindi gaanong angkop") and covers a band of the map; the
   layer picker is cut to "Angkop para"; the brand is cut to "FOOTIN". Consider shorter legend labels or a
   collapsible legend at narrow widths.
2. The map area above the sheet is small on phones once a locality is open (about 150 px between the top bar
   and the legend).
3. Place dots use English kind names in their popups (`kind.replace(/_/g, " ")`, "min walk", "Open now").
4. Decide whether a park-only "camp only in designated areas" rule should score the same 35 as Roanoke's
   downtown sidewalk ban. Researched localities now score lower than unchecked ones (which are not counted).

**Next, in order:** review the live demo and list UI changes → run both smokes in full and look at the
screenshots → the 10-locality independent audit (sample in S8.0; audit inputs are on the Windows machine only)
→ remaining ordinance gaps from `data_raw/local_rules_research.json` next_action entries (Bristol current code
first) → native review of translations.

---

## S8.0 Claude: resume this checkpoint first (2026-10-25, Codex)

The owner asked to finish the session and hand work to **Claude**. This is an unfinished checkpoint on
`codex/claude-handoff-2026-10-25`; `b7aefc8` is the last previously verified main commit. **Do not treat
S7's green test counts or the older next-model prompt as validation of S8.** No worker committed or pushed.

What is saved:

- **Town receipts:** five new `fixtures/{roanoke,richmond,blacksburg,harrisonburg,alexandria}_2026-10-25/`
  sets, eight real responses each (40 total), manifests and append-only request logs. Read
  `docs/TOWN_CAPTURE.md`, `scripts/record_towns.py`, and `tests/test_town_captures.py`. BLS failed with
  HTTP 503; ACS/HUD/EIA/Places/Transitland/Kroger had no keys; HRSA remains an empty local table. Never
  fill those gaps with guesses. The recorder and its shell wrapper changed.
- **Ordinances:** `data_raw/local_rules_research.json` covers 23 localities: nine scoped rules, thirteen
  Unknown, and disputed Bristol. Read `docs/LOCAL_RULES_REVIEW.md` and the builder diff. Bristol's old
  broad/0 classification remains provisional. The other locality codes are not all reviewed.
  **The builder changed but generated `footing/static/va_localities.json` still needs reconciliation.**
- **Translations:** Tagalog and reusable Virginia reason templates were added in `i18n*.js`, with
  matching `reason_data` in both vafit engines. English `c.reason` is preserved. Renderer integration is
  unfinished: use `FootingI18n.vaReason(lang, component)` or `vaReasonParts(lang, component)` (escaped
  `{text, lang, kind}` runs), switch localized headings to `t("details")`, and replace raw unscored-law
  reasons too. Native-speaker review is entirely pending. Check whether a translation review doc exists.
- **Small UI fixes:** language-select arrow and popup fitting around the sheet/legend were implemented;
  caches bumped to v10. These changes have not completed browser validation.
- **Hosting:** `demo/SITES.json` records the one registered, private Site. It is **not published**.
  Reuse project `appgprj_6adda30ead888191a0b182aa7c797982`; never create another Site for this demo.
  The ignored `out/footing-site` has a Vinext starter and identity; dependency installation was stopped.
  Durable ratings backend, adapter, schema, packaging script and hosting tests were not implemented.
  Fetch a fresh source credential through Sites when resuming; no credentials were saved in the repo.
- **Independent audit inputs:** `scripts/capture_audit_sources.py` retrieved five primary bulk inputs
  (HUD FMR/HIC/PIT, ICE list, grouped USDA counts) into ignored `out/audit-sources/`, with hashes/URLs.
  Their metadata is retained in `data_raw/audit_inputs_2026-10-25_MANIFEST.json` for cross-machine resume.
  The ten-locality comparison report was **not generated**. These files are local, not in the Git push.
  Empty HTTP200 bodies must remain unverified. A browser-compatible User-Agent fixed HUD downloads;
  PIT uses `/sites/default/files/xls/2007-2025-PIT-Counts-by-CoC.xlsb`. HUD FMR has malformed workbook
  properties (`2026- 2-19...`); ignore metadata in memory only, preserve worksheet/source bytes.

Validation before this checkpoint: ordinance-focused tests 20 passed; town-focused tests 25 passed
before final OSM additions; localization-focused run 50 passed with 8 dictionary-fixture encoding
errors (Windows CP1252 vs UTF-8). These are partial runs, not an overall green suite. The current full
suite/data check must be reviewed and rerun. No S8 browser smoke has completed.

**Final checkpoint run:** `pytest -q` completed: **237 passed, 3 failed, 8 errors**. Failures:
`test_healthz_reports_demo` assumes a single capture date, `test_plan_tonight_card_compare` assumes
Roanoke is unrecorded, and `test_committed_va_json_matches_build_script` detects the pending regeneration.
The eight `tests/test_i18n_langs.py` fixture errors are CP1252 decoding of UTF-8 Node output; set explicit
UTF-8 on its subprocess call. Builder `--check` also confirms the stale generated JSON. These failures
are saved deliberately in this WIP branch, not described as a finished or deployable release.

Next, in order: review/finish current diffs; regenerate the locality JSON and reconcile the existing
Fairfax County score assertion; fix explicit UTF-8 decoding in multilingual subprocess tests; wire
the Details renderer; rerun final town/replay checks; complete the independent sample and remaining
code research; finish durable hosting; run both browser smokes including Tagalog and inspect screenshots.
Audit sample: `random.Random(20261025).sample(sorted(localities), 10)` = 51640, 51530, 51117, 51103,
51680, 51036, 51600, 51197, 51075, 51071. Fairfax **city** 51600 is distinct from Fairfax County 51059.
Keep using `AGENTS.md` and `docs/DATA_WORK.md` to avoid repeated discovery and bulk recapture.

---

## S7.0 Point crime in the panel; reuse saved data first (2026-10-25, Codex)

**S5.2 item 4 is implemented.** A map tap opens the locality panel with that point's incident tile.
After submitting a rating, its pin is also used. Norfolk and Charlottesville show the nearby violent
incident count, enforcement-call count (never scored as danger), saved date range, and the correct
city's source link. Other points retain the FBI fallback; missing reports stay Unknown. Crime stays
opt-in. The Python and JavaScript engines now expose matching structured counts/dates/source metadata.

The point score has its own label and no locality rank or rank range; the statewide list and map still
compare whole localities. "Show the whole city or county" restores that comparison, and picking from
the list clears the previous point. Only a tile and validity stay in the panel state, in memory.
All three new UI strings are machine translated in all eight languages. Service-worker caches are v9.
The expanded smoke also found Norfolk help-place phone numbers overflowing the 320 px panel. Help
rows now put the phone below the name and wrap long values; the layout checks cover this in English/Arabic.

**Owner request: reduce usage spent searching for databases/sources.** Read `AGENTS.md` and
`docs/DATA_WORK.md`. `python scripts/data_lookup.py <FIPS> --field <field>` prints one saved field
and its sources; `--list` lists fields. Use captures for implementation and replay for tests. Research
only an identified gap, discrepancy, requested refresh or current claim, and record outcomes so another
session can resume. This session made no new publisher-data searches or changes to source captures.
The session 4 report attributes most work to collection, but there is no token telemetry to quantify it.

**Validation:** 209 unit tests pass (including JS/Python parity); the Virginia builder `--check`
passes. The standalone browser smoke passes: 11 screenshots, 21 Christiansburg dots, zero API calls or
profile leakage, including a real Norfolk canvas click. The full-app smoke passes: 72 screenshots
(320/390/1280 px, English/Arabic), 1,576 requests checked, no profile data sent or layout errors. It
checks the Norfolk point, source, saved dates, unchanged statewide ranking, reset to FBI, Virginia Beach
Unknown, and the submitted rating pin. Relevant English/Arabic screenshots were visually inspected.
Results are in ignored `out/globe/` and `out/standalone/`; no new source capture or independent fact-check
was performed. The Bash clean-install script was not rerun on this Windows environment.

**This environment is Windows.** The previous session's preinstalled Chromium note was for another
environment. This session installed project dependencies in ignored `.venv/` and used installed Edge:
set `FOOTING_BROWSER_CHANNEL=msedge` for either smoke script. The map tests use `easeTo(duration=0)`
for an offset camera; MapLibre `jumpTo` ignores that offset. Sandbox child processes stalled here;
the successful test/server processes required normal local process access.

**Next:** S5.2 item 5 (publishing the standalone demo) remains undone; `out/demo` builds locally, but
no public URL has been published. Then Bristol's disputed ordinance and the independent source checks.
The data-reuse policy does not replace the independent publisher verification still needed there.

---

Last updated **2026-10-25** by the 6th model (Claude Opus 5.5), which **clicked the app through a real
browser for the first time** — see S6.x directly below. S5.x is the 5th model, which **merged sessions 3 and 4
into one `main`**; it is still the best overview. The session 4 report
(`docs/SESSION4_REPORT.md`) is still worth reading for the designer notes; where it disagrees with S5, S5
wins, because some of what it lists as unfinished is now done.

## S6.0 The app has now been clicked through a real browser

The S5 handoff said this sandbox could not run a browser. That is no longer true: Chromium and Playwright come
pre-installed (`require('playwright')`, `chromium.launch()` with no options; do **not** `playwright install`).
So S5.2 items 2 and 3 are done:

- **`scripts/ui_globe_smoke.py` is rewritten** for the Virginia app. It walks intro → profile (status, chips,
  a priority moved) → top 5 → locality → mosaic → *Details* → list of 133 + search ("Roanoke" finds exactly
  the city and the county; nonsense says "no match") → rate, at **320, 390 and 1280 px, in English and in
  Arabic**: 60 screenshots. The rate step taps the map: a tap in Baltimore and a tap in the Atlantic must be
  refused with the right reason, a tap on Christiansburg must file under Montgomery County (51121), Send must
  stay disabled until an overall rating, the POST must return 200 and the heat count must go up by exactly one.
  Then *Forget my answers* must clear the profile and device token but keep the language. On every screen it
  checks: no sideways scroll, nothing sticking out of the sheet, every top-bar control fully on screen, legend
  not under the layer picker, `dir=rtl` and right-to-left layout in Arabic, the machine-translation note shown.
  The privacy check from session 3 is kept: no profile word ever leaves the browser.
- **`scripts/ui_standalone_smoke.py` is rewritten** too (it was also still session 3's, waiting for a
  50-state list that no longer exists). It picks the rating spot with a **real mouse click through the map
  canvas**, checks 21 Christiansburg place dots appear at zoom 12, that nothing calls `/api`, and that Hide
  covers the page.

**What clicking found (all fixed, each with a check that fails on the old code):**

1. **At 320 px the Hide button — the quick exit — was pushed off screen**, in every language: off the right
   edge in English, off the left in Arabic. The top bar needed ~380 px. `globe.css` now tightens it below
   381 px and lets the brand shrink before any button does. Service-worker cache bumped to v8 so phones that
   already have the app pick up the fix.
2. **The open-water refusal was English in every language.** `globe.js` passed the engine's English reason
   straight to the toast. A tap can only be refused as outside Virginia or on water, so both now have
   translated sentences (`outsideTap`, new `waterTap`) in all 8 languages.
3. **Six languages were missing 24 strings** that silently fell back to English. Two are visible in the
   Virginia app: the "Open the {town} receipt" button and the standalone "saved on this device" toast; both
   are translated now. The rest are the 50-state beta view, digits, or unused, and are listed with reasons in
   the new `tests/test_i18n_langs.py`, which fails if any other English string goes missing in any language.

**Tests: 196 pass** (191 + 5 in `tests/test_i18n_langs.py`). Both smoke scripts pass. `clean_install_check.sh`
passes. The new translations are machine translations like the rest of S4's; they need the same native review.

**Not done, noticed while clicking:** the language picker has no dropdown arrow (`appearance: none`), so it
reads as a plain button; a place popup opened near the bottom of the map can sit under the legend. Neither
blocks anything. The *Details* reasons are still English in every language (S5.2 item 9).

## S6.1 Next, in order

S5.2 items 2 and 3 are done. Continue with **S5.2 item 4** (block-level crime in the locality panel — now
testable here: extend `ui_globe_smoke.py` to tap a Norfolk point and assert the panel shows the block-level
crime line), then 5 onward. Run both smoke scripts before you hand off:

```bash
FOOTING_MODE=replay FOOTING_RATINGS_DB=/tmp/r.sqlite uvicorn footing.api:app --port 8765 &
python scripts/ui_globe_smoke.py http://localhost:8765 out/globe          # 60 screenshots
python scripts/build_standalone_demo.py out/demo && python -m http.server -d out/demo 8799 &
python scripts/ui_standalone_smoke.py http://localhost:8799 out/standalone
```

Look at the screenshots, not just the exit code: the Hide-button bug was found by eye first.

## S5.0 The merge, in one page

Two lines of work existed and **neither contained the other**:

- **`main`** — sessions 1–3, plus a Virginia locality engine added at the end of session 3.
- **`session4`** — rebuilt from the shared Drive copy, so it never received session 3's work, then given a
  Virginia-first app: the 133-locality map, score mosaic, reasoning panel, 8 languages, VA-only ratings.

They shared no git history, but `session4`'s starting tree matched `main`'s session-2 sync point, so this
was a real 3-way merge on that point, not a copy of one side over the other.

**What was kept from each.** `session4`'s app is the base. Session 3's work that the Drive copy had lost is
restored on top: the Spanish translation of every engine reason (session 4 had silently dropped it and was
showing English — 113,832 reasons now check out with 0 untranslated), `docs/FACT_CHECK.md`,
`tests/test_i18n_reasons.py`, `scripts/ui_standalone_smoke.py`.

**Where both had solved the same problem, the merge took the better half of each.** Both sessions built a
per-network rating cap. Session 4's is SQLite-backed, so it survives a restart; session 3's read
`X-Forwarded-For`. Session 4's alone would have put **every user behind Cloud Run in one bucket** and locked
out the whole deployment after 60 ratings. The merged version has both, and answers 429 again.

**`main` was failing 4 tests when this session started.** `fixtures/va_2026-10-24/MANIFEST.json` was a
statewide capture dropped into the folder meant for single-point replay sets, and the resolver assumed every
manifest names a point, so `/api/healthz` and the receipt, plan, tonight and card endpoints raised
`KeyError`. Fixed in `footing/pipeline.py`, and the captures moved to `data_raw/` where they belong.

**Retired:** `main`'s second Virginia engine (`footing/web/va.js`, the scoring half of its `footing/va.py`,
`scripts/va_geo.py`, `tests/test_va.py`, `tests/js/run_va.js`). It scored the same 133 localities but was
never wired into the app or the API. Everything it did better was ported first — see S5.1 — and its data
and capture scripts are kept.

**Tests: 191 pass.** `main` had 138 (and 4 failing); `session4` had 155.

## S5.1 What the merge added that neither side had alone

**1. The two datasets checked each other, and that found a real bug.** Sessions 3 and 4 had each captured
HUD FMR, FBI CDE, HUD HIC and the CoC map independently. They agreed on rent for all 133 localities and the
CoC mapping for all 133 — but not on crime, and the reason was a bug: the FBI lists agencies that straddle a
county line under both counties (`CUMBERLAND, PRINCE EDWARD`), and the builder took the first name, so
**Farmville PD's 37 violent offences went to Cumberland County, population 9,664**, quintupling its count.
Four agencies were affected. Each is now placed by its own published coordinates. After that, and after
taking the more precise of the two captures for months-reported, **the two captures agree on crime counts
for all 133 localities**. Written up in `docs/FACT_CHECK.md`.

**2. Point checks that say what is wrong.** Session 4's was pass/fail: swapped latitude and longitude came
back as "outside Virginia", and coordinates rounded to one decimal place (about 11 km) were treated as
exact. `footing/va.py` now returns `issues` and a `validity`, and `vafit.fit_point` folds validity into
**confidence and never into the score** — where you tap inside a county cannot change that county's rent.
`footing/web/vapoint.js` is the JS twin; `tests/test_va_point.py` runs 30 points through both and requires
identical output.

**3. Block-level crime.** `main` had the finest crime data anyone captured — 12 months of Norfolk and
Charlottesville incident reports in 189 tiles of about 1 km — and no way to show it. A point in either city
is now scored on the violent incidents in the 3×3 tiles around it instead of the citywide rate. Trespass,
loitering and drunkenness calls are counted, shown, and **never scored as danger**; there is a test that
fails if Charlottesville's downtown mall stops being an enforcement hotspot, so nobody "fixes" that by
accident.

**4. "Searched and found nothing" is its own answer.** Montgomery County's code was searched and no camping
ban turned up. That is weaker than "no ban" and stronger than "not checked yet", so it is a third status,
shown and still not scored, and the builder refuses to let such a row carry a source or a score.

**5. Unknown is never zero in the stored data either.** Virginia Beach reported no 2025 crime to the FBI and
its counts were stored as `0`. They are `null` now, with the reason.

## S5.2 Do this next, in order

1. ~~Push to GitHub.~~ **Done.** The merge went up as PR #1 and the owner merged it into `main`
   (`bd47f69`), so `main` now has everything above, including the `footing/pipeline.py` fix. The
   `merge/session4-into-main` branch is identical to `main` and can be deleted.
2. ~~Click the app through a real browser.~~ **Done in S6.0.** Original note, kept for history: Nobody has. This sandbox cannot install one —
   `cdn.playwright.dev` is not reachable from it, and the network allowlist covers only GitHub and the
   package registries. On a laptop: `pytest -q`, then `uvicorn footing.api:app --port 8080`, then walk
   through intro → profile → top 5 → locality → mosaic → *Details* → search → rate, at 320, 390 and 1280 px,
   in English and in Arabic (right-to-left). The rating flow and RTL have never been seen working.
3. ~~Rewrite `scripts/ui_globe_smoke.py`.~~ **Done in S6.0.** Still session 3's; it expects the old language button and the
   state view, so it will fail against the current UI. Section S4.1 item 2 lists what it should cover. Keep
   its privacy check: no profile word may leave the browser.
4. ~~Show block-level crime in the locality panel.~~ **Done in S7.0**, using a map tap or a submitted
   rating pin. Whole-locality ranking stays separate from the point score.
5. **Publish the standalone demo as a link.** `python scripts/build_standalone_demo.py out/demo --fragment`,
   then publish as a claude.ai Artifact with the `db` capability for ratings. It is multi-file, so pass
   `files` for `vendor/`, `data/` and the JS (`vapoint.js` is now one of them). A full-page build loads
   clean at `out/demo`.
6. **Settle Bristol.** Two sessions read the same ordinance summary and scored it differently (0 vs 35), and
   neither read the city code. It is kept at 0 because the errors do not cost the same: harsher costs
   someone an option, gentler sends them somewhere they can be charged. Read Bristol City Code and set it.
7. **The independent fact-check nobody has done.** Ten random localities, end to end, off the publishers'
   own pages: FMR, PIT, HIC, SNAP counts, 287(g), local rule. `docs/FACT_CHECK.md` has the list of open
   items; add the result there.
8. **The other 121 localities' camping rules.** Largest first: Fairfax, Virginia Beach, Prince William,
   Loudoun, Chesterfield, Henrico, Norfolk, Chesapeake, Arlington, Richmond, Newport News, Alexandria. Each
   is a cited `LOCAL_RULES` row in `scripts/build_va_localities.py`, read from the code, never from memory.
9. **Translations.** Native review; add Tagalog (8th-largest group); translate the *Details* reasons, which
   needs templated reasons in both engines with parity kept.
10. **Record more towns** for walk-time receipts: Roanoke, Richmond, Blacksburg, Harrisonburg, Alexandria.
    See `scripts/record_demo_towns.sh`. Needs a normal network.

## S5.3 Gotchas, including the ones that cost this session time

- **Two engines, two twins, and parity is enforced.** `vafit.js`/`vafit.py` score localities;
  `vapoint.js`/`va.py` check points. Change one of a pair and `pytest` fails. Use `js_round` and the `num()`
  printer, and sum floats in FIPS order. Python's `float()` accepts `"nan"` and `"-Infinity"` as text and JS
  `Number()` does not — `vapoint.js` handles that explicitly, because the parity test caught it.
- **`fixtures/` is for single-point replay sets only.** Each needs a `MANIFEST.json` naming one point.
  Statewide captures go in `data_raw/`. Putting one in `fixtures/` is what broke `main`.
- **Virginia geography.** FIPS 510 and above are independent cities, separate from the counties around them.
  Name matching must keep "Roanoke city" and "Roanoke County" apart (`fips_for`), and `BEDFORD CITY` merged
  into Bedford County in 2013. The us-atlas 10m shapes erase small cities, so locality lookup uses TIGER
  (`web/data/va-localities.json`); TIGER includes water, so open-water detection needs the us-atlas
  shoreline as a second check. The phone does not download that file, so `footing/ratings.py` re-checks a
  rating server-side before storing it.
- **Shelter data is per Continuum of Care, not per town.** 16 in Virginia; the Balance of State covers 71
  localities with one count. Never present it as "this town's shelter". Confidence drops accordingly.
- **MapLibre locality ids:** the `va` source uses `promoteId: "fips"`, so the expression is `["id"]` and
  `feature.id` is the FIPS string.
- **The sandbox network** reaches GitHub and the package registries and nothing else. No government source,
  no browser download. Capture on a laptop; `data_raw/README.md` has the method, `docs/PIPELINE.md` the
  whole pipeline.
- **Keep an old capture when you refresh a source.** Comparing two independent captures is the only real
  check this data has ever had, and it is what found the Farmville bug.

## S5.4 Prompt for the next model

> You are the 7th model continuing Footing, a hackathon app for people experiencing homelessness in
> Virginia, including immigrants. Sessions 3 and 4 have been merged into one `main`. Read `HANDOFF.md`
> sections S6.0–S6.1 and S5.0–S5.3 first, then `docs/PIPELINE.md`, `docs/FACT_CHECK.md`, and `docs/SESSION4_REPORT.md`
> for the designer notes. Run `pytest -q` (expect 196 passed) and
> `python scripts/build_va_localities.py --check`. Then work S5.2 in order.
>
> Rules from the owner:
> - Never invent data. Unknown with a reason, never a guess, and never a 0 standing in for a blank.
> - Say plainly what you could not test, and why. "Done" only counts if it is actually done.
> - Keep JS/Python parity, keep the tests green, add tests for what you change.
> - Boil the ocean: complete, tested, documented.
> - Before you hand off, run both UI smoke scripts (S6.1) and add S7.x at the top of this file.

---

# Session 4 handoff (older; the report it points to is still useful)

Last updated **2026-10-24 ~21:20 ET** by the 4th model (Claude Opus 5.5, session 4). The owner stopped the
session because of a usage cap. The full story is in **`docs/SESSION4_REPORT.md`**: what changed, what is not
finished and why, the designer notes and the sources.

**Read S5.x above first — several items below are now done:** the GitHub push problem (S4.1 item 1) is now
just "needs push access"; the Spanish reason text S4 listed as missing was session 3's work and is restored;
the bad-coordinate handling is extended; and `fixtures/` no longer holds the statewide capture.

## S4.0 What session 4 updated

1. Footing is **Virginia only**. It opens on the 133 counties and independent cities. The 50-state view is
   behind "All states (beta)".
2. **Virginia data pipeline:** `data_raw/` holds the raw captures, documented in `data_raw/README.md`.
   `scripts/build_va_localities.py` builds `footing/static/va_localities.json` and validates it against the
   publisher totals (`--check`).
3. **Virginia Fit Score with confidence:** `footing/web/vafit.js` and `footing/vafit.py` produce identical
   output. Command line: `python -m footing.vafit --kids --status tps --top 10`.
4. **Bad coordinates:** `footing/va.py` and `/api/va/check`. Ratings refuse points outside Virginia, NaN and
   open water. Tiles with fewer than 3 ratings are hidden. Each network has a daily cap on a salted hash.
5. **New UI** (`footing/web/globe.js`, `globe.css`): the Virginia map, the score mosaic, the reasoning rows
   with sources, the confidence meter, help places, bedrooms and kids, crime as opt-in, search, and a rating
   flow with Back.
6. **8 languages** in `footing/web/i18n_more.js`: en, es, vi, ko, zh, ar (RTL), am, fa/Dari (RTL). All
   machine translated and labelled as such on screen.
7. **Smaller changes:** GA and OK scored as enforcement mandates (25); Virginia "no statewide ban" (75); ACA
   notes include the 2027 cutoff; the standalone demo includes Virginia.

## S4.2 Gotchas learned in session 4

(Superseded in part by S5.3, which repeats the ones that still matter.)

- **Sandbox network.** Only GitHub and package registries. For government data use a normal laptop, or the
  Chrome tool with the write-into-page-and-read-back trick in `data_raw/README.md`.
- **Three Hampton Roads CoCs** (VA-501, 505, 507) counted shelters only in 2025, so their outside count is
  carried from 2024 and flagged.
- **Engine parity.** The JS and Python engines must match exactly.
