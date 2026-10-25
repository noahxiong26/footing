# HANDOFF — Footing (read this first)

Last updated **2026-10-24 ~21:20 ET** by the 4th model (Claude Opus 5.5, session 4). The owner stopped the
session because of a usage cap. The full story is in **`docs/SESSION4_REPORT.md`**: what changed, what is not
finished and why, the designer notes and the sources. Sections S4.x below are the short version for whoever
builds next. The older sections from session 3 are kept below them and are still useful, but the S4 sections
win where they disagree.

## S4.0 What session 4 updated (list this first, per the human notes)

1. Footing is now **Virginia only**. It opens on the 133 counties and independent cities. The 50-state view is
   behind "All states (beta)".
2. **Virginia data pipeline:**
   - `data_raw/` holds the raw captures, documented in `data_raw/README.md`.
   - `scripts/build_va_localities.py` builds `footing/static/va_localities.json` and validates it against the
     publisher totals (`--check`).
3. **Virginia Fit Score with confidence:**
   - `footing/web/vafit.js` and `footing/vafit.py` produce identical output. `tests/js/run_vafit.js` checks this.
   - Command line: `python -m footing.vafit --kids --status tps --top 10`.
4. **Bad coordinates:** `footing/va.py` (`check_point`, `locality_at`) and `/api/va/check`. Ratings refuse
   points outside Virginia, NaN and open water. Tiles with fewer than 3 ratings are hidden. Each network has a
   daily cap, keyed on a salted hash.
5. **New UI** (`footing/web/globe.js`, `globe.css`): the Virginia map, the score mosaic, the reasoning rows with
   sources, the confidence meter, help places, bedrooms and kids, crime as opt-in, search, and a rating flow
   with Back.
6. **8 languages** in `footing/web/i18n_more.js`: en, es, vi, ko, zh, ar (right-to-left), am, fa/Dari
   (right-to-left). All are machine translated and labeled as such on screen.
7. **Smaller changes:**
   - GA and OK are scored as enforcement mandates (25).
   - Virginia is scored "no statewide ban" (75).
   - The ACA notes include the 2027 cutoff.
   - The service worker cache is v6.
   - The standalone demo includes Virginia.
8. Tests: **155 pass** (`pytest -q`). The commits are `7936355` and `853aabc`, plus this wrap-up commit.

## S4.1 Unfinished work, in priority order (do these next)

1. **Push to GitHub.**
   - This session could not: there was no repo access, and the gh token was invalid.
   - Drive folder `hack 20/25/4th` has `footing.bundle` (full history) and `footing-session4.zip`.
   - Steps: `git clone footing.bundle footing`, then `cd footing`, then
     `git remote add origin https://github.com/<owner>/footing.git`, then `git push -u origin main`.
   - Ask the owner which account to use. Earlier sessions mentioned `jordangangavarapu-cmyk` and
     `noahxiong26`.
2. **Rewrite `scripts/ui_globe_smoke.py` for the new UI.** It is out of date and will fail. It still expects
   `#g-lang` to be a button and the state view.
   - The new run should cover, at 320, 390 and 1280 px:
     - intro, then profile (status, kids, bedrooms, crime), then save;
     - top 5, locality, mosaic and reasons;
     - search;
     - layer switch;
     - every language, including Arabic RTL;
     - the rating flow (tap far out to zoom in, tap again to pin, send, the locality updates);
     - Back;
     - Forget.
   - Keep the privacy check: no profile word may leave the browser.
3. **Click through the rating flow and RTL in a real browser.** This has not been done. Fix anything that
   breaks.
4. **Publish the standalone demo as a shareable link.**
   - Build it with `python scripts/build_standalone_demo.py out/demo --fragment` and publish it as a
     claude.ai Artifact with the `db` capability for ratings.
   - It is multi-file, so pass `files` for vendor/, data/ and the JS.
   - A full-page version already builds and loads without errors at `out/demo`.
5. **Independent fact-check of `va_localities.json`.** A reviewer who did not build it should check 10 random
   localities: FMR, PIT and HIC, SNAP counts, 287(g), and the 6 local rules. Record the result in
   `docs/FACT_CHECK.md`.
6. **Docs:**
   - Update `README.md` and `FACTORS.md` for Virginia; they still describe the 50-state version.
   - Add a "Virginia Fit" section to `docs/RATING_FORMULA.md`. Copy the formula from the `vafit.py` docstring
     and report section 1.
   - Write `docs/PIPELINE.md`. Report section 3 has the text.
7. **More local camping rules.** Read the city and county code for the largest localities first: Fairfax,
   Virginia Beach, Prince William, Loudoun, Chesterfield, Henrico, Norfolk, Chesapeake, Arlington, Richmond,
   Newport News, Alexandria. Add each as a cited `LOCAL_RULES` row in `scripts/build_va_localities.py`, never
   from memory.
8. **Translations:**
   - Get native review.
   - Add Tagalog.
   - Translate the "Details" reasons. This needs templated reasons in both engines; keep parity.
9. **Record more Virginia towns** for walk-time receipts: Roanoke, Richmond, Blacksburg, Harrisonburg,
   Alexandria. See `scripts/record_demo_towns.sh`. Gov and OSM sites need a normal network, not this sandbox.

## S4.2 Gotchas learned in session 4

- **Sandbox network.** The sandbox reaches only GitHub and package registries. For government data, use a
  normal laptop, or the Chrome tool with the write-into-page-and-read-back trick described in
  `data_raw/README.md`.
- **Virginia geography:**
  - Virginia has independent cities, so FIPS codes 510 and above are cities and are separate from the
    counties around them.
  - Name matching must handle pairs like "Roanoke city" and "Roanoke County"
    (`scripts/build_va_localities.py`, `fips_for`).
  - The us-atlas 10m county shapes erase small cities. Use `web/data/va-localities.json` (TIGER).
  - TIGER includes water, so `va.py` also checks the us-atlas shoreline.
- **Engine parity.** The JS and Python engines must match exactly. Use `js_round` and the `num()` printing
  helper. Sum floats in FIPS order. Run `pytest tests/test_vafit.py` after any change to either engine.
- **MapLibre locality ids:** the `va` source uses `promoteId: "fips"`, so the expression is `["id"]` and
  `feature.id` is the FIPS string.
- **Wording:** shelter data is per Continuum of Care (16 in Virginia, with the Balance of State covering 71
  localities). Never present it as "this town's shelter".
- **Three Hampton Roads CoCs** (VA-501, 505, 507) counted shelters only in 2025, so their outside count is
  carried from 2024 and flagged.

## S4.3 Prompt to paste into the next model

> You are the 5th model continuing Footing, a hackathon app for people experiencing homelessness in Virginia,
> including immigrants. Read `HANDOFF.md` sections S4.0–S4.2 first, then `docs/SESSION4_REPORT.md`, then
> `data_raw/README.md`. Run `pytest -q` (expect 155 passed) and `python scripts/build_va_localities.py --check`.
> Then work through S4.1 in order. Rules from the owner:
> - Never invent data. Use Unknown with a reason instead.
> - Say plainly what you could not test.
> - Keep JS/Python parity, keep the tests green, and add tests for what you change.
> - "Boil the ocean": complete, tested and documented.
> - Before you hand off, list what you updated at the top of HANDOFF.md.
>
> Before you stop, update S4.0/S4.1 (or add S5.x) and upload to the shared Drive folder "hack 20/25".

---

# Session 3 handoff (older; kept for reference)

## 0. Where things stand right now (read this if you are taking over)

- **Working and tested:** the globe UI (the UI-track entry), the Fit Score, state policy data,
  anonymous ratings, and everything that was there before (receipt, plan, tonight, card, compare,
  flyer). `pytest -q` → 115 passed. Both Playwright smoke runs pass. The clean-install check passes.
- **In progress when work stopped:**
  1. *Shareable demo page.* `scripts/build_standalone_demo.py` builds a no-server copy of the globe
     (`demo/standalone_backend.js` stands in for the API). It builds, but **nobody has clicked through
     it in a browser yet**. Section 8, task 1.
  2. *Independent fact-check of the policy data.* A separate review of `eligibility.json` and
     `state_policy.json` against primary sources was started and had not reported back. **Treat the
     data as checked by one person only.** Section 8, task 2.
- **Not done (needs the owner):** push to GitHub, deploy, Gemini key, demo video, Devpost [TODO]s.
- **How the work was done:** the repo was rebuilt from the Google Drive folder "hack 20/25". Then the
  globe, Fit Score, policy data and ratings were added in one commit on top of `baseline from Drive`.

## 1. What this is

**Footing** is an entry for MLH Hacktoberfest Hack Day (Oct 24, 2026). Prize tracks: **Best
Open-Source AI Project**, **Best Use of Gemma 4**, and the **UI track** (the globe below was built for it). Budget: **$25 of Google Cloud credit**.
Owner: Noah (Virginia Tech, noahxiong@vt.edu).

A free phone app for people experiencing homelessness. Given a point (rounded to a ~1 km tile),
it builds a **Settle Receipt** from open public data:

- a 0–100 **Settle Score** across 10 categories, with a confidence number;
- dollar lines: a week of food, gas, studio rent, minimum wage;
- the nearest EBT grocery, library, restroom, clinic, post office, and whether each is open now;
- a reason for every number it could not find.

**The front door is a globe** (`#/`). It starts from space and flies to the U.S. Then every state
is colored by a personal **Fit Score**, computed on the phone from the person's immigration status
(15 options), household, situation, age band and their own priority order. Anonymous community
ratings show as a heatmap. Method: `docs/RATING_FORMULA.md`. The old start screen is now `#/start`.

Built on top of the receipt: a 30-day plan written by Gemma 4 and checked against the data, a
"Tonight" list, a printable pocket card with a QR code, a town comparison, and a flyer reader
(Gemma 4 vision).

## 2. Rules the owner cares about (do not break these)

1. **Never invent data.** A missing value is `Unknown` with a reason. Never turn it into 0, a
   guess, or another town's number. If you can't find something, say "couldn't find it". This
   is the owner's top priority.
2. **If you couldn't run or test something, say so.** Don't make it look done.
3. **"Boil the ocean"** means: finish the whole thing, with tests and docs. Search before
   building, and test before claiming.
4. **Ask before anything outside the repo:** pushing to GitHub, deploying, spending cloud credit,
   or creating accounts and keys. None of these has been done yet.
5. Commit trailer used so far (keep it if you are Claude; use your own attribution otherwise):
   ```
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   Claude-Session: https://claude.ai/code/session_019ax9T5LyumQyVTYyEp5WKD   (globe work: session_01AUJ3PWFBBvHLsP91kJFjXT)
   ```

## 3. Verify the state (2 minutes)

```bash
pip install -e ".[dev]"
pytest -q                                   # expect: 115 passed
python scripts/build_state_policy.py --check   # expect: all state-policy checks pass
FOOTING_MODE=replay uvicorn footing.api:app --port 8080   # open http://localhost:8080
bash scripts/clean_install_check.sh         # expect: every endpoint 200, "clean install OK"
python scripts/ui_smoke.py http://localhost:8080 out/screens   # classic flow; needs Playwright Chromium
# globe run-through: start the server with a throwaway ratings DB, then
FOOTING_MODE=replay FOOTING_RATINGS_DB=/tmp/r.sqlite uvicorn footing.api:app --port 8080
python scripts/ui_globe_smoke.py http://localhost:8080 out/globe  # 13 screens + "no profile data sent"
python -m footing fit --status undocumented --kids --mixed        # CLI ranking; expect IL, VT, ME, OR, NJ on top
git log --oneline
```

Replay mode needs no network and no keys. It serves real responses captured on 2026-10-24 for
downtown Christiansburg, VA (37.1299, −80.4089). Expected receipt: Settle Score about 77–79,
confidence about 0.4 (medium), and 7 of 15 sources OK. Every other town shows "no demo data".
That is correct behavior, not a bug.

## 4. Repo map

| Path | What it is |
| --- | --- |
| `footing/config.py` | Settings from env: `FOOTING_MODE` (live / replay / record), `FOOTING_FIXTURES`, `FOOTING_CACHE`, API keys, `FOOTING_GEMMA_MODEL` (default `gemma-4-26b-a4b-it`) |
| `footing/http.py` | One `Fetcher` for all network calls: live, record, replay, and an SQLite cache. Scrubs keys from saved files |
| `footing/sources/` | 15 adapters. `open_sources.py` (keyless), `keyed_sources.py`, `static_sources.py`. `base.py` turns errors and missing keys into status rows |
| `footing/static/` | Hand-checked tables: minimum wage (VA/MD/WV/NC/TN), USDA Thrifty Food Plan (June 2026), county→CoC crosswalk. **Empty templates:** `coc_capacity.csv`, `hrsa_sites.csv`, `local_rules.json` |
| `footing/factors.py` | **The scoring catalog.** 10 categories, 33 parameters, the normalizers, and why each zero is or isn't trusted |
| `footing/pipeline.py` | `collect` → `dedupe` → `score` → `build_receipt`. `resolve_replay` picks the fixture set for a tile. `record_fixture_set` |
| `footing/enrich.py`, `hours.py` | Infers pharmacies from SNAP names; parses OSM `opening_hours` (returns None when unsure) |
| `footing/gemma.py`, `planner.py`, `flyer.py` | Gemini REST client, grounded plan + validator + rule-based fallback, flyer reader |
| `footing/views.py` | Compare, tonight, pocket-card SVG |
| `footing/api.py` | FastAPI under `/api`; also serves the PWA from `footing/web/` at `/` |
| `footing/web/` | Vanilla JS PWA, no build step. `app.js` (hash routes), `sw.js` (offline), `styles.css` |
| `fixtures/<town>_<date>/` | Recorded responses + `MANIFEST.json` (point, time, URLs, what was trimmed, what wasn't captured) |
| `tests/` | 115 tests (`test_fit.py` includes a JS⇄Python parity run through node). `tests/synthetic/` = **fake** responses for keyed APIs, built from provider docs and labeled as such |
| `scripts/` | `record_demo_towns.sh`, `deploy_cloud_run.sh` (dry run unless `--yes`), `clean_install_check.sh`, `ui_smoke.py`, `load_hud_hic_pit.py` |
| `footing/web/globe.js`, `globe.css`, `i18n.js` | The globe UI (MapLibre GL 5.24 globe projection, vendored in `web/vendor/`), English + Spanish strings |
| `footing/web/fit.js` ⇄ `footing/fit.py` | The Fit Score engine, line-for-line twins. JS runs on the phone; Python serves the CLI (`python -m footing fit`) and the tests |
| `footing/static/state_policy.json` | 51 rows of state policy with sources. **Generated** by `scripts/build_state_policy.py` (edit the tables there, then run it; `--check` validates) |
| `footing/static/eligibility.json` | 15 statuses × 12 programs, each rule with a plain note, plus sources. Hand-written; `tests/test_fit.py` checks completeness |
| `footing/ratings.py`, `footing/us_states.py` | Anonymous ratings in SQLite (`FOOTING_RATINGS_DB`), and an offline point→state lookup |
| `footing/web/data/` | us-atlas / world-atlas TopoJSON (offline borders) |
| `demo/standalone_backend.js`, `scripts/build_standalone_demo.py` | No-server copy of the globe for a shareable link (built, not yet clicked through) |
| `docs/RATING_FORMULA.md` | How the Fit Score and ratings work, weights, worked example, limits, references |
| `README.md`, `FACTORS.md`, `docs/DEVPOST.md` | Public docs; the generated factor table; the Devpost draft with [TODO]s for the owner |

## 5. How the score works (short version; full table in `FACTORS.md`)

- **Parameters** turn a raw value into 0–100:
  - `count`: 100·(1 − e^(−n/k))
  - `linear`: 100 at a "good" value, 0 at a "bad" value, clamped in between
- **Category score** = weighted mean of its known parameters.
- **Settle Score** = weighted mean of the known categories. Category weights: shelter 18,
  food 16, cost 14, mobility 12, income 10, health 8, hygiene 8, weather 6, kids 4, legal 4.
- **Confidence** = Σ(category weight × coverage × freshness) / 100.
- **Profile chips** (car, kids, tonight, on_foot) multiply weights, then renormalize. They
  never change data.
- **Weights and thresholds are design judgments, not fitted to outcome data.** Say so if asked.
  Change them only in `factors.py`, then regenerate the table with
  `python -m footing factors --markdown > FACTORS.md`.

**Fit Score (globe), short version; full method in `docs/RATING_FORMULA.md`:** six parts per state
(help you can use, rent, shelter, enforcement safety, camping laws, ratings), weighted by the
Rank-Order Centroid of the person's priority order, averaged over *known* parts only. Confidence =
Σ weight × freshness. A 90% rank range comes from 300 seeded Dirichlet re-weightings. Ratings use a
time-decayed Bayesian average (prior 3/5, m = 5, half-life 90 days).

## 6. Invariants with tests (keep them green)

- **The person's status, household and priorities never leave the phone.** `POST /api/ratings`
  rejects any key outside its whitelist; `ui_globe_smoke.py` scans every request body and URL.
- `fit.js` and `fit.py` give identical results (`test_javascript_engine_matches_python_exactly`).
- Unknown parts never count as zero; "prefer not to say" is never scored as the worst case.
- `state_policy.json` reconciles: PIT state totals sum to HUD's 745,652; sheltered + unsheltered =
  total; NLIHC hours ≈ 40 × housing wage ÷ minimum wage.
- Replay data never answers for a different tile (`test_replay_never_leaks_to_another_town`,
  `tests/test_fixture_sets.py`).
- A zero from a sparse source (OSM shelters, showers) is Unknown, not 0.
- Gemma output naming a place, address or phone that isn't in the data gets removed. If nothing
  survives, the rule-based plan is shown.
- Keys never appear in recorded files, manifests, or URLs (`test_record_writes_manifest_and_redacts_keys`,
  `test_recorded_body_never_contains_a_key`). The Gemini key goes in the `x-goog-api-key` header.
- The raw input point is never echoed back. Only the tile is.

## 7. Done vs not done

**Done and tested here:**
- the globe: intro, about-you, priorities, top fits, state detail, layers, Spanish, list, rating,
  forget-me, desktop panel (Playwright at 390 px and 1280 px, software WebGL)
- state policy data (51 rows) and eligibility rules: totals reconcile with publishers, every field
  cites a source read on Oct 24. A second, independent fact-check was started but **not finished**
- source URLs in `eligibility.json` were opened and checked (one dead ed.gov link was replaced with NCHE)
- pipeline, scoring, API and all 7 classic screens (Playwright at 390 px; no horizontal scroll at 320 px)
- multi-town replay, record command, clean install, CI workflow file
- dry-run deploy script, Devpost draft

**Built but NEVER run against the real service** (only synthetic responses or a local stub):
- Census ACS, BLS LAUS, HUD FMR, EIA, Google Places, Transitland, Kroger
- Gemma 4 plan and flyer. The flyer sends the image as `inline_data`, but Google's Gemma docs
  show the Files API (`file_data`). This is the highest-risk unknown.

**Not built:**
- Gemma function-calling tools (the plan uses JSON prompting instead)
- Kroger "EBT stretch" meter UI
- Transitland departures / radar view
- SAMHSA, legal aid, ID offices and air quality (listed as `planned`, so they always show Unknown)

**Globe limits:**
- camping-law table covers 8 states; others are Unknown
- per-state "why" sentences are English only (UI strings are translated)
- satellite tiles (EOX, non-commercial) and labels (CARTO) need network; borders work offline
- ratings SQLite is per-instance on Cloud Run until a volume/DB is attached
- not tested on a real phone GPU, only Chromium with SwiftShader
- standalone demo (`scripts/build_standalone_demo.py`): builds; **not clicked through in a browser**
- known UI bug: in Spanish at phone width the legend's "Sin datos" label is clipped behind the layer
  picker (see `docs/screenshots/09_spanish.png`). Fix in `.g-ramp` in `globe.css` (let it wrap or shorten the label)

**Data gaps:**
- HUD HIC/PIT (the loader is written; it needs the real xlsx)
- HRSA sites
- Christiansburg camping ordinance (Municode)
- the SNAP fixture covers only a ~2 km box (10 stores)

## 8. Next tasks, in priority order

**Globe / UI track first (the judging is soon):**

1. **Finish the shareable demo.** Run `python scripts/build_standalone_demo.py out/demo`, then
   `python -m http.server -d out/demo 8799` and open http://localhost:8799/. Click through: intro →
   About you → Show my map → a state → Zoom in on Virginia (Christiansburg place dots should
   appear) → Rate a place → Hide. Fix whatever breaks. To host it as a claude.ai Artifact, build
   with `--fragment` and publish the folder with the `db` capability (ratings then become shared).
   If you only want a link fast, deploying the real app (task 7) also works.
2. **Second check of the policy data.** Ask someone (or a fresh model) to verify, against
   primary sources, every status × program rule in `footing/static/eligibility.json`, the
   driver's-license list, the Medicaid non-expansion list and the camping-law states in
   `scripts/build_state_policy.py`. Fix the tables, run `python scripts/build_state_policy.py`,
   then `pytest -q`. Never fill a gap with a guess. Mark it Unknown (`null`) instead.
3. **Open it on a real phone** (iPhone Safari and an Android Chrome). The globe was only tested
   in desktop Chromium with software WebGL.
4. **Record the demo video** using the globe script in `docs/DEVPOST.md`.

**Then the rest:**

5. **Get a Gemini key from Google AI Studio** (owner action) and run the plan and the flyer for
   real. If `inline_data` fails for Gemma, switch `flyer.py` to the Files API and add a test.
6. **Record demo towns** on a machine with normal internet:
   `scripts/record_demo_towns.sh` (reads keys from `.env`). Check each `MANIFEST.json`
   `not_captured` list. Commit the fixture folders.
7. **Add keys one at a time** and fix the adapters against real responses. Replace the matching
   `tests/synthetic/` file with a real recorded one where the terms allow.
8. **Fill the static tables:**
   - `scripts/load_hud_hic_pit.py --hic … --pit … --year 2024`
   - HRSA site download → `hrsa_sites.csv`
   - `local_rules.json`, using only rules you can cite
9. **Deploy, with the owner's OK:** `PROJECT=<id> scripts/deploy_cloud_run.sh` (dry run), then
   `--yes`. Set the Places quota (≤160 Text Search/day) and a $20 budget alert. A budget only
   alerts; it doesn't stop charges.
10. Fill the Devpost [TODO]s (owner's words).
11. Globe follow-ups: finish the camping-law table (cite each statute), translate the reason
   sentences, county-level layer (the counties TopoJSON is already vendored), and re-run
   `build_state_policy.py` whenever ILRC, NLIHC, HUD or DOL publish new numbers.

## 9. Gotchas from this build

- `pkill -f "<pattern>"` can match and kill your own shell. Kill by PID instead.
- A non-editable install puts the package in site-packages, so the repo's `fixtures/` folder is
  not next to it. The Dockerfile sets `FOOTING_FIXTURES=/app/fixtures`. Use
  `clean_install_check.sh` to catch this class of bug.
- The Urban Institute API ignores `county_code`, so query by state and filter locally. The Census
  API now requires a key. BLS answered "busy" to browser GETs, so the adapter uses POST. OSM tags
  some FedEx counters as post offices; they are filtered out.
- The Cloud sandbox this was built in could not reach government APIs (HTTP 403) or Docker Hub.
  The fixtures were captured through a browser. A normal laptop should not have these limits.
- `uvicorn` without `--reload` keeps serving old code. Restart it after edits.
- MapLibre: padding set with `map.setPadding()` is *added* to per-call `padding` in
  `cameraForBounds`/`fitBounds`; doing both overflowed the viewport and threw "reading 'center'".
  Keep the sheet's space in `setPadding(sheetPad())` and pass only `padding: 16` per call.
- Hash changes don't reload the page, and 2× DPR screenshots under software WebGL are slow; the
  globe smoke uses a separate 1× context for desktop. Screenshots taken mid-spin can look torn.
- Bump the cache names in `sw.js` whenever shell files change, or phones keep the old globe.

## 10. Putting it on GitHub

The repo has full git history (`git log`). From the unzipped folder:

```bash
git remote add origin https://github.com/<you>/footing.git    # create an empty repo on GitHub first
git push -u origin main
```

CI (`.github/workflows/ci.yml`) then runs the policy-data check, the tests and the clean-install check.
Nothing secret is in the repo: `.env` is git-ignored, and recorded fixtures have keys scrubbed.

## 11. Prompt to paste into the next model

> You are continuing work on Footing, a hackathon app in this repo. Read `HANDOFF.md` fully
> (start with section 0), then `README.md`, `docs/RATING_FORMULA.md` and `footing/factors.py`. Run the checks in section 3 and report what
> differs. Then work through section 8 in order. Rules: never invent data (Unknown with a
> reason instead), say plainly what you could not test, keep the tests green and add tests
> for what you change, and ask before pushing, deploying, spending cloud credit, or creating
> accounts. When you stop, update section 7 and section 8 of `HANDOFF.md` so the next person
> can continue.
