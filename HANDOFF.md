# HANDOFF — Footing (read this first)

Context for any model or person picking up this repo on another computer. Written 2026-10-24
14:15 ET (the commit that added this file). Everything below was true at that moment; run the
checks in "Verify the state" before trusting it.

**Get the code:** `git clone https://github.com/noahxiong26/footing` (private repo, owner
noahxiong26; ask Noah for access). Pull before you start and push your commits when you stop.

## 1. What this is

**Footing** is an entry for MLH Hacktoberfest Hack Day (Oct 24, 2026). Prize tracks: **Best
Open-Source AI Project** and **Best Use of Gemma 4**. Budget: **$25 of Google Cloud credit**.
Owner: Noah (Virginia Tech, noahxiong@vt.edu).

A free phone app for people experiencing homelessness. Given a point (rounded to a ~1 km tile),
it builds a **Settle Receipt** from open public data:

- a 0–100 **Settle Score** across 10 categories, with a confidence number;
- dollar lines: a week of food, gas, studio rent, minimum wage;
- the nearest EBT grocery, library, restroom, clinic, post office, and whether each is open now;
- a reason for every number it could not find.

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
   Claude-Session: https://claude.ai/code/session_019ax9T5LyumQyVTYyEp5WKD
   ```

## 3. Verify the state (2 minutes)

```bash
pip install -e ".[dev]"
pytest -q                                   # expect: 74 passed
FOOTING_MODE=replay uvicorn footing.api:app --port 8080   # open http://localhost:8080
bash scripts/clean_install_check.sh         # expect: every endpoint 200, "clean install OK"
python scripts/ui_smoke.py http://localhost:8080 out/screens   # needs Playwright Chromium
git log --oneline                           # 5 commits as of this file
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
| `tests/` | 74 tests. `tests/synthetic/` = **fake** responses for keyed APIs, built from provider docs and labeled as such |
| `scripts/` | `record_demo_towns.sh`, `deploy_cloud_run.sh` (dry run unless `--yes`), `clean_install_check.sh`, `ui_smoke.py`, `load_hud_hic_pit.py` |
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

## 6. Invariants with tests (keep them green)

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
- pipeline, scoring, API and all 7 screens (Playwright at 390 px; no horizontal scroll at 320 px)
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

**Data gaps:**
- HUD HIC/PIT (the loader is written; it needs the real xlsx)
- HRSA sites
- Christiansburg camping ordinance (Municode)
- the SNAP fixture covers only a ~2 km box (10 stores)

## 8. Next tasks, in priority order

1. **Get a Gemini key from Google AI Studio** (owner action) and run the plan and the flyer for
   real. If `inline_data` fails for Gemma, switch `flyer.py` to the Files API and add a test.
2. **Record demo towns** on a machine with normal internet:
   `scripts/record_demo_towns.sh` (reads keys from `.env`). Check each `MANIFEST.json`
   `not_captured` list. Commit the fixture folders.
3. **Add keys one at a time** and fix the adapters against real responses. Replace the matching
   `tests/synthetic/` file with a real recorded one where the terms allow.
4. **Fill the static tables:**
   - `scripts/load_hud_hic_pit.py --hic … --pit … --year 2024`
   - HRSA site download → `hrsa_sites.csv`
   - `local_rules.json`, using only rules you can cite
5. **Deploy, with the owner's OK:** `PROJECT=<id> scripts/deploy_cloud_run.sh` (dry run), then
   `--yes`. Set the Places quota (≤160 Text Search/day) and a $20 budget alert. A budget only
   alerts; it doesn't stop charges.
6. **GitHub:** pushed 2026-10-24 to `noahxiong26/footing` (private). Before submitting, make it
   public with the owner's OK (the open-source prize needs a public link) and check that the
   CI run in the Actions tab passes.
7. Demo video; fill the Devpost [TODO]s (owner's words).

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

## 10. Prompt to paste into the next model

> You are continuing work on Footing, a hackathon app in this repo. Read `HANDOFF.md` fully,
> then `README.md` and `footing/factors.py`. Run the checks in section 3 and report what
> differs. Then work through section 8 in order. Rules: never invent data (Unknown with a
> reason instead), say plainly what you could not test, keep the tests green and add tests
> for what you change, and ask before pushing, deploying, spending cloud credit, or creating
> accounts. When you stop, update section 7 and section 8 of `HANDOFF.md` so the next person
> can continue.
