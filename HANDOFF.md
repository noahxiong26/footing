# HANDOFF — Footing (read this first)

Context for any model or person picking up this repo. Last updated **2026-10-24 ~19:00 ET** by session 3
(Claude). Everything below was true at that moment; run the checks in section 3 before trusting it.

## 0. Where things stand right now

- **Sessions so far.** Session 1 built the pipeline, receipt, plan and API (GitHub `noahxiong26/footing`,
  up to commit `c9edc3d`). Session 2 added the globe, Fit Score, state policy data and ratings; it hit a
  usage cap and left its repo only in Google Drive (`hack 20/25/2nd 100%/footing`). Session 3 restored that
  repo (every file hash-checked against the Drive copy's git index), finished session 2's two open tasks,
  and fixed what it found. Its record is in Drive `hack 20/25/3rd 100%`.
- **Working and tested:** globe UI, Fit Score, state policy data, ratings, the classic receipt/plan/tonight/
  card/compare/flyer screens, and the no-server standalone demo. `pytest -q` → **123 passed**. All three
  Playwright runs pass (`ui_smoke`, `ui_globe_smoke`, `ui_standalone_smoke`). Clean install check passes.
- **Session 3 changes (commits after `eb25aa8`):**
  1. Policy data second check (`docs/FACT_CHECK.md`). Georgia and Oklahoma camping laws were scored as
     statewide bans; they are enforcement mandates → new status `enforcement_mandate` (score 25). ACA notes
     completed (all tax credits end Jan 1, 2027 for those statuses).
  2. Standalone demo clicked through end to end (`scripts/ui_standalone_smoke.py`).
  3. Rating on a phone was nearly impossible (form covered 86% of the screen before a spot was picked;
     taps below zoom 8 ignored). Fixed: short sheet until a spot is picked, far tap zooms in, Back button.
  4. Spanish legend clipping fixed (and checked automatically at 320/390 px in both languages).
  5. Spanish for every Fit Score "why" sentence (display-only; `fit.js`/`fit.py` parity untouched).
  6. Ratings: NaN/inf coordinates returned a 500 → now a 400; per-network daily limit added because device
     tokens can be minted by a script.
- **Where the code is:** session 3's commits live in the session clone. They were **not pushed** to GitHub
  (owner rule: ask first). Drive `3rd 100%` has `session3.patch` (all text changes since the Drive copy,
  except this file and screenshots) plus this `HANDOFF.md`. To rebuild: copy Drive `2nd 100%/footing`,
  `git apply session3.patch`, replace `HANDOFF.md`, run section 3. Or, once Noah OKs a push, pull GitHub.
- **Not done (needs the owner):** push to GitHub, deploy, Gemini key, demo video, Devpost [TODO]s, test on a
  real phone, a legal-aid professional's read of `eligibility.json`.

## 1. What this is

**Footing** is an entry for MLH Hacktoberfest Hack Day (Oct 24, 2026). Prize tracks: **Best Open-Source AI
Project**, **Best Use of Gemma 4**, and the **UI track** (the globe). Budget: **$25 of Google Cloud credit**.
Owner: Noah (Virginia Tech, noahxiong@vt.edu).

A free phone app for people experiencing homelessness. **The front door is a globe** (`#/`): it starts in
space and flies to the U.S.; every state is colored by a personal **Fit Score** computed on the phone from
the person's immigration status (15 options), household, situation, age band and their own priority order.
Anonymous community ratings show as a heatmap. Method: `docs/RATING_FORMULA.md`.

Under it, for a point (rounded to a ~1 km tile), a **Settle Receipt** from open public data: a 0–100 Settle
Score across 10 categories with a confidence number, dollar lines (food, gas, rent, minimum wage), nearest
EBT grocery/library/restroom/clinic/post office with open-now, and a reason for every Unknown. Built on it:
a 30-day plan by Gemma 4 checked against the data, a "Tonight" list, a printable pocket card, a town
comparison, and a flyer reader (Gemma 4 vision). The old start screen is `#/start`.

## 2. Rules the owner cares about (do not break these)

1. **Never invent data.** A missing value is `Unknown` with a reason, never 0, a guess, or another town's
   number. If you can't find something, say "couldn't find it". This is the owner's top priority.
2. **If you couldn't run or test something, say so.** Don't make it look done.
3. **"Boil the ocean"** means: finish the whole thing, with tests and docs. Search before building; test
   before claiming.
4. **Ask before anything outside the repo:** pushing to GitHub, deploying, spending cloud credit, creating
   accounts or keys. None of these has been done.
5. **"Usage aware mode":** keep a running record (Drive progress log) so a usage cap never loses work.
6. Commit trailer for Claude sessions (others: use your own attribution):
   ```
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   ```

## 3. Verify the state (3 minutes)

```bash
pip install -e ".[dev]"
pytest -q                                               # expect: 123 passed (2 tests need node)
python scripts/build_state_policy.py --check            # expect: state policy data OK
bash scripts/clean_install_check.sh                     # expect: every endpoint 200, "clean install OK"
FOOTING_MODE=replay FOOTING_RATINGS_DB=/tmp/r.sqlite uvicorn footing.api:app --port 8080 &
python scripts/ui_smoke.py http://localhost:8080 out/screens          # 7 screens
python scripts/ui_globe_smoke.py http://localhost:8080 out/globe      # 13 screens, legend + Spanish checks
python scripts/build_standalone_demo.py out/demo && python -m http.server -d out/demo 8799 &
python scripts/ui_standalone_smoke.py http://localhost:8799 out/standalone   # 9 screens, 21 place dots
python -m footing fit --status undocumented --kids --mixed           # CLI ranking: IL, VT, ME, NJ, OR on top
```

Replay mode needs no network and no keys: real responses captured 2026-10-24 for downtown Christiansburg,
VA (37.1299, −80.4089). Expected receipt: Settle Score about 77, confidence about 0.4. Every other town shows
"no demo data" — correct behavior, not a bug. **Kill servers by PID**, not `pkill -f` (it can kill your shell).

## 4. Repo map

| Path | What it is |
| --- | --- |
| `footing/config.py`, `http.py` | Settings from env (`FOOTING_MODE` live/replay/record, keys, `FOOTING_GEMMA_MODEL`); one `Fetcher` with record/replay and key scrubbing |
| `footing/sources/` | 15 data adapters (keyless, keyed, static); errors and missing keys become status rows |
| `footing/factors.py`, `pipeline.py` | Receipt scoring catalog (10 categories, 33 parameters) and `collect → dedupe → score → build_receipt` |
| `footing/gemma.py`, `planner.py`, `flyer.py` | Gemini REST client, grounded plan + validator + rule fallback, flyer reader |
| `footing/api.py` | FastAPI under `/api` (+ per-network rating limit); serves the PWA from `footing/web/` |
| `footing/web/` | Vanilla JS PWA. `app.js` (classic screens), `globe.js`/`globe.css` (globe), `fit.js` (Fit Score), `i18n.js` (English/Spanish + Spanish reasons), `sw.js` (offline; bump cache names when shell files change — now v6) |
| `footing/fit.py` ⇄ `footing/web/fit.js` | Fit Score engine, line-for-line twins; parity test runs both through node |
| `footing/static/state_policy.json` | 51 rows of state policy, **generated** by `scripts/build_state_policy.py` (edit the tables there; `--check` validates) |
| `footing/static/eligibility.json` | 15 statuses × 12 programs with notes and sources (hand-written) |
| `footing/ratings.py`, `us_states.py` | Anonymous ratings in SQLite (`FOOTING_RATINGS_DB`); offline point→state |
| `demo/standalone_backend.js`, `scripts/build_standalone_demo.py` | No-server globe for a shareable link (tested by `ui_standalone_smoke.py`) |
| `docs/RATING_FORMULA.md`, `docs/FACT_CHECK.md`, `FACTORS.md`, `docs/DEVPOST.md` | Method; what was fact-checked; receipt factor table; Devpost draft with [TODO]s |
| `tests/` | 123 tests; `tests/js/` node helpers (parity, Spanish-reason coverage); `tests/synthetic/` = **fake** responses for keyed APIs, labeled as such |

## 5. How the scores work (short)

- **Settle Score (receipt):** parameter → 0–100 (`count`: 100·(1−e^(−n/k)); `linear`: good→100, bad→0),
  category = weighted mean of known parameters, score = weighted mean of known categories (shelter 18,
  food 16, cost 14, mobility 12, income 10, health 8, hygiene 8, weather 6, kids 4, legal 4). Confidence =
  Σ(weight × coverage × freshness)/100.
- **Fit Score (globe):** six parts per state (help you can use, rent, shelter, enforcement safety, camping
  laws, ratings) weighted by the Rank-Order Centroid of the person's order, averaged over **known** parts
  only. Camping laws: ban 0, enforcement mandate 25, ban struck down 50, not checked Unknown. Confidence =
  Σ weight × freshness. 90% rank range from 300 seeded Dirichlet re-weightings. Ratings: time-decayed
  Bayesian average (prior 3/5, m = 5, half-life 90 days).
- **Weights and thresholds are design judgments, not fitted to outcome data.** Say so if asked.

## 6. Invariants with tests (keep them green)

- The person's status, household and priorities never leave the phone (`POST /api/ratings` whitelists keys;
  both globe smoke scripts scan every request).
- `fit.js` and `fit.py` give identical results. Spanish reasons are display-only (`i18n.js`), so parity is
  unaffected; `tests/test_i18n_reasons.py` checks every generated reason has Spanish.
- Unknown never counts as zero; "prefer not to say" is never scored as the worst case.
- `state_policy.json` reconciles: PIT totals sum to HUD's 745,652; sheltered + unsheltered = total; NLIHC
  hours ≈ 40 × housing wage ÷ minimum wage. Camping statuses ⊆ {in_effect, enforcement_mandate, contested}.
- Replay data never answers for a different tile. Sparse-source zeros are Unknown.
- Gemma output naming a place/address/phone not in the data is removed; if nothing survives, the rule-based
  plan is shown. Keys never appear in recorded files or URLs. The raw input point is never echoed back.
- Ratings: bad coordinates are a 400; per-device and per-network daily limits.

## 7. Done vs not done

**Done and tested here:** everything in section 0; classic screens at 390 px (no horizontal scroll at
320 px); globe at 390 and 1280 px in software WebGL; standalone demo click-through; policy data second check.

**Built but never run against the real service** (synthetic responses or a stub only): Census ACS, BLS LAUS,
HUD FMR, EIA, Google Places, Transitland, Kroger, Gemma 4 plan and flyer. The flyer sends the image as
`inline_data`; Google's Gemma docs show the Files API (`file_data`). Highest-risk unknown.

**Not built:** Gemma function-calling tools; Kroger "EBT stretch" UI; Transitland departures; SAMHSA, legal
aid, ID offices, air quality (listed as `planned`, always Unknown).

**Limits:** camping-law table covers 8 states; quoted source notes stay English in Spanish mode; satellite
tiles (EOX, non-commercial) and labels need network; ratings SQLite is per-instance on Cloud Run; the
standalone demo shows place dots on a plain map (no tiles); not tested on a real phone GPU; ratings are open
to brigading beyond the per-network limit (no accounts by design).

**Data gaps:** HUD HIC/PIT xlsx (loader written), HRSA sites, Christiansburg camping ordinance, the SNAP
fixture covers only a ~2 km box (10 stores).

## 8. Next tasks, in priority order

1. **Owner OK to push** session 3's commits to GitHub (or apply `session3.patch` to the Drive copy).
2. **Open the globe on a real phone** (iPhone Safari, Android Chrome). Only software WebGL so far.
3. **Record the demo video** with the script in `docs/DEVPOST.md` (step 6 now uses tap-to-pick rating).
4. **Gemini key** (owner) → run plan and flyer for real; if `inline_data` fails, switch `flyer.py` to the
   Files API and add a test.
5. **Deploy** with the owner's OK: `PROJECT=<id> scripts/deploy_cloud_run.sh` (dry run), then `--yes`. Set the
   Places quota (≤160 Text Search/day) and a $20 budget alert (alerts only; it doesn't stop charges).
6. **Record more demo towns** on a normal laptop: `scripts/record_demo_towns.sh`; commit fixture folders.
7. **Legal-aid read of `eligibility.json`**; finish the camping-law table (cite each statute); re-run
   `build_state_policy.py` when ILRC, NLIHC, HUD or DOL publish new numbers.
8. Ideas backlog: county layer (TopoJSON already vendored), Spanish source notes, a "near me now" view on the
   globe, ratings moderation without accounts (k-anonymity: hide tiles with < 3 ratings).

## 9. Gotchas

- `pkill -f "<pattern>"` can match your own shell. Kill by PID.
- A non-editable install puts the package in site-packages, away from `fixtures/`; the Dockerfile sets
  `FOOTING_FIXTURES=/app/fixtures`. `clean_install_check.sh` catches this class of bug.
- Urban Institute API ignores `county_code` (filter locally). Census API needs a key. BLS answers "busy" to
  browser GETs (adapter uses POST). OSM tags some FedEx counters as post offices (filtered).
- `uvicorn` without `--reload` serves old code; restart after edits.
- MapLibre: `setPadding()` adds to per-call `padding`; keep the sheet's space in `setPadding(sheetPad())`.
- Bump `sw.js` cache names whenever shell files change, or phones keep the old globe.
- Playwright on the globe: use 1× device scale for desktop under software WebGL; mid-spin screenshots tear.

## 10. Prompt to paste into the next model (Claude, GPT/Codex, or anything else)

> You are continuing work on Footing, a hackathon app in this repo. Read `HANDOFF.md` fully (start with
> section 0), then `README.md`, `docs/RATING_FORMULA.md`, `docs/FACT_CHECK.md` and `footing/fit.py`. Run the
> checks in section 3 and report anything that differs. Then work through section 8 in order. Rules: never
> invent data (Unknown with a reason instead); say plainly what you could not run or test; keep `fit.js` and
> `fit.py` identical (the parity test enforces it); keep the tests green and add tests for what you change;
> bump `sw.js` cache names when web files change; ask before pushing, deploying, spending cloud credit, or
> creating accounts. Keep a short progress log in Drive `hack 20/25/<n>th 100%` as you go. When you stop,
> update sections 0, 7 and 8 of `HANDOFF.md`.
