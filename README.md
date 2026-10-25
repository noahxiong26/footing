# Footing

**If you lost your home tonight, where in Virginia could you actually make it for a month?**
Footing is a free, open-source app for people experiencing homelessness, including immigrants whose papers
decide which help they can use. It scores all 133 Virginia cities and counties *for you*: shelter space, rent
against the minimum wage, help nearby, local rules on sleeping outside, immigration enforcement, and what
people who have been there say. Every number links to its public source, and anything we could not confirm is
a question mark, never a zero.

**Live demo:** https://noahxiong26.github.io/footing/ (published from [`site/`](site/) by GitHub Pages) ·
**Run it yourself:** `python -m http.server -d site 8000`, then open http://localhost:8000 (no keys, no server,
no network after load).

<p>
<img src="docs/screenshots/s9/1_start_globe.png" width="49%" alt="Start screen: the globe at dusk with Virginia lit">
<img src="docs/screenshots/s9/2_best_fits.png" width="49%" alt="Best fits for an example person, with a factor strip per place">
<img src="docs/screenshots/s9/3_place.png" width="49%" alt="One place: score, three numbers at a glance, Score / Help nearby / Programs tabs">
<img src="docs/screenshots/s9/5_priorities.png" width="49%" alt="About you: drag what matters most; the top three places update live">
</p>

## For judges: one minute

1. Open the demo and press **See an example person** (TPS papers, two kids, safety first). The map re-lights for her.
2. Open **About you** and drag a different priority to the top: the live preview shows the best places move.
3. Open a place: three numbers at a glance, then **Score** (every part with its source), **Help nearby** and
   **Programs** (grouped by what her papers allow, with a legal-aid caution where it matters).
4. Switch the language to Arabic (right-to-left) or Tagalog. Press **Hide this page** for the quick exit.

**What makes it different**

* **Two people see two different Virginias.** The profile is scored on the phone and never sent anywhere
  (a test checks every request).
* **Honest numbers.** No model in the scoring path; Unknown stays Unknown; every figure cites HUD, the Census,
  USDA, the FBI, ICE or the city's own code. Two independent data captures were compared and found a real bug.
* **Built for the people it serves:** nine languages (English, Spanish, Vietnamese, Korean, Chinese, Arabic,
  Amharic, Dari/Persian, Tagalog; machine translated and labelled), works from a 320 px phone, keyboard and
  screen-reader support (axe WCAG 2.2 AA: 0 violations on 18 screens), reduced motion respected.
* **Free to run:** the whole app is one 2.4 MB static folder with zero AI calls to score. Gemma 4 is used only to
  read photographed flyers and word plans in the server version, and its output is checked against the data.

How it meets the judging rubric, item by item: [`docs/RUBRIC.md`](docs/RUBRIC.md) · Submission text:
[`docs/DEVPOST.md`](docs/DEVPOST.md) · Method and citations: [`docs/RATING_FORMULA.md`](docs/RATING_FORMULA.md)
(section 8 is Virginia) · Data pipeline: [`docs/PIPELINE.md`](docs/PIPELINE.md) · What has and has not been
double-checked: [`docs/FACT_CHECK.md`](docs/FACT_CHECK.md) · Session-by-session log: [`HANDOFF.md`](HANDOFF.md).

In Virginia an independent city is not part of any county, so "Roanoke city" and "Roanoke County" are
different places with different ordinances and different rents. The data keeps them apart.

## The full app (server version)

For a single town, pick it (or share a location rounded to ~1 km) and it
prints a **Settle Receipt**: a 0–100 Settle Score built from live public data, what a week of
food and gas costs there, the nearest EBT grocery, library, restroom, clinic and post office
with their hours, and a plain reason for every number it could not find.

```
profile (on phone) ─▶ 133 VA localities × (shelter · rent · help nearby · local law · 287(g) · crime · ratings)
      ─▶ rank-order-centroid weights ─▶ Fit Score + confidence + rank range (200 re-weightings) ─▶ VA map
      ─▶ tapped point ─▶ block-level crime where a city publishes it; point doubt lowers confidence, not the score

profile (on phone) ─▶ 15 statuses × 12 programs + 51 state policy rows ─▶ 6 parts ─▶ rank-order-centroid weights
      ─▶ Fit Score per state + confidence + rank range (300 perturbed weightings) ─▶ "All states (beta)"
anonymous 1-5 ratings ─▶ ~1 km tiles ─▶ time-decayed Bayesian average ─▶ heatmap + "what people here say"

point ─▶ snap to ~1 km tile ─▶ 15 source adapters ─▶ places + measures (each with provenance)
      ─▶ 33 parameters (29 built, 4 planned) ─▶ 10 categories ─▶ Settle Score + confidence
      ─▶ receipt · 30-day plan (Gemma 4) · tonight list · pocket card · town compare
```

## Run it in 30 seconds (no keys, no network)

```bash
pip install -e ".[dev]"
FOOTING_MODE=replay uvicorn footing.api:app --port 8080     # open http://localhost:8080
python -m footing receipt --lat 37.1299 --lon -80.4089 --profile car,kids   # same data, CLI
pytest -q                                                    # 209 tests
python scripts/build_va_localities.py --check                 # validate the Virginia data
python scripts/data_lookup.py 51710 --field crime             # one saved field + sources; no network
python -m footing.vafit --kids --status tps --top 10          # Virginia ranking, CLI
python scripts/build_standalone_demo.py out/demo             # no-server copy of the app
python scripts/ui_standalone_smoke.py http://localhost:8799 out/standalone   # click-through of that copy
python scripts/ui_globe_smoke.py http://localhost:8765 out/globe   # full app, 3 widths x English/Arabic (server on 8765)
python -m footing fit --status undocumented --kids --mixed  # Fit Score ranking, CLI
```

Replay mode serves **real responses captured on 2026-10-24** for downtown Christiansburg, VA
(`fixtures/christiansburg_2026-10-24/`, see its `MANIFEST.json`). Other towns show
"no demo data" and every score as Unknown: recorded data is never reused for a different place.
Keyed sources show as Unknown because no keys were set when the fixtures were captured.

## What the app does

| Screen | What it shows | Where it comes from |
| --- | --- | --- |
| **Virginia map** (`#/`) | All 133 cities and counties coloured by your Fit Score (or by ratings, shelter, rent, local law). Hatched = no data. Search, and a list of all 133 | `vafit.js` on the phone + `/api/va` |
| **Locality** | "How the score adds up": a mosaic where each part's width is how much it matters to you and its height is how well the place does, then one row per part with the number, its share of your score, a plain sentence, and *Details* with the linked sources. Confidence meter with "based on 4 of 6 parts" | `vafit.js` |
| **All states (beta)** | The earlier 50-state globe: Earth from space, flies to the U.S., colours every state by your Fit Score | `fit.js` + `/api/policy` |
| **About you** | 15 immigration statuses (incl. "prefer not to say"), household, situation, age band, and a reorderable priority list that shows each item's weight live | stays in `localStorage`; "Forget my answers" wipes it |
| **State** | Score, rank, confidence, 90% rank range, a bar per part with its reason, the programs you can use there, a public-charge caution, 211 and legal-aid links, sources | `fit.js` |
| **Rate a place** | 1-5 stars on overall / felt safe / respected / could get help, plus fixed tags. Filed under a ~1 km tile, no text | `POST /api/ratings` |
| **Receipt** | Settle Score, 10 category bars, dollar lines (food week, gas, studio rent), nearest places with open/closed now | `/api/receipt` |
| **30-day plan** | Day 1 / Week 1 / Month 1 steps, each tied to a real place from the receipt | `/api/plan`: Gemma 4 when `GEMINI_API_KEY` is set, a rule-based plan otherwise |
| **Tonight** | Places open now within an hour's walk, tonight's low, "Call 211" when no shelter is confirmed | `/api/tonight` |
| **Pocket card** | A printable pocket-size card with up to 5 places, hours, 211, and a QR back to the receipt | `/api/pocket-card.svg` |
| **Compare** | Two or three towns side by side; Unknown is never compared | `/api/compare` |
| **Snap a flyer** | Photo of a paper flyer → service, days/times, phone, address, marked "community-reported, unconfirmed" | `POST /api/flyer` (Gemma 4 vision) |

The front end is a no-build PWA (`footing/web/`): large tap targets, works at 320 px, high
contrast, 8 languages (Arabic and Persian/Dari right-to-left), a "Hide" button that jumps to a weather
page, no sign-in.
The only thing the server stores is anonymous ratings (tile, hour, stars, fixed tags, a salted hash
of a random device token). The service worker keeps the last good answer
for each screen, so a receipt or plan opened once still shows with no signal.

### Gemma 4 grounding

Gemma 4 (`gemma-4-26b-a4b-it` by default, via the Gemini API) writes the plan and reads flyers.
Its output is checked before anyone sees it: every step must point to a `place_id` that the
pipeline found, and any address or phone number not taken from data is removed. If nothing
survives the check, or the API is down or over quota, the rule-based plan is shown instead and
the screen says so.

## Run it live

```bash
cp .env.example .env           # fill in the keys you have; every key is optional
set -a; . ./.env; set +a
FOOTING_MODE=live uvicorn footing.api:app --port 8080
```

### Record demo towns (do this on a laptop before the demo)

```bash
scripts/record_demo_towns.sh        # Christiansburg, Blacksburg, Radford, Roanoke -> fixtures/<town>_<date>/
python -m footing record --lat 37.27 --lon -79.94 --label "Downtown Roanoke, VA" --out fixtures/roanoke_2026-10-24
```

Each set gets a `MANIFEST.json` (point, time, URL per file with keys redacted, and a
`not_captured` list). In replay mode the server picks the set whose tile matches the request;
if a town was recorded twice, the newest set wins.

### Deploy (Cloud Run)

```bash
PROJECT=<gcp-project> scripts/deploy_cloud_run.sh          # dry run: prints every command
PROJECT=<gcp-project> scripts/deploy_cloud_run.sh --yes    # does it
```

Keys go to Secret Manager; the service scales to zero with at most 2 instances. The script ends
with the quota caps to set in the console (Places Text Search ≤160/day keeps a month inside the
free Pro tier). `scripts/clean_install_check.sh` installs the package the way the Dockerfile does
and checks every endpoint; CI runs it with the tests.

## API

All endpoints are under `/api` (also served without the prefix). `lat`/`lon` are snapped to a
~1 km tile before any source is called, and responses never echo the raw point.

| Endpoint | Notes |
| --- | --- |
| `GET /api/healthz` | mode, recorded demo sets |
| `GET /api/receipt?lat&lon&profile=car,kids,on_foot` | full receipt JSON (cached 10 min per tile+profile) |
| `GET /api/plan?lat&lon&profile&lang=English` | grounded 30-day plan |
| `GET /api/tonight?lat&lon` | open-now list |
| `GET /api/pocket-card.svg?lat&lon` | printable card |
| `GET /api/compare?points=lat,lon;lat,lon[;lat,lon]` | 2–3 places |
| `POST /api/flyer` (multipart `photo`) | jpeg/png/webp/heic, ≤6 MB; 503 without a Gemini key |
| `GET /api/factors`, `GET /api/sources` | the factor catalog and source list |
| `GET /api/policy` | `state_policy.json` + `eligibility.json` (the phone scores with these) |
| `GET /api/va` | all 133 Virginia localities with every field and its source (the phone scores with this) |
| `GET /api/va/check?lat&lon` | is this point usable? names the problem, or lists what makes it doubtful |
| `GET /api/va/fit?lat&lon&status&kids&bedrooms&crime` | score the locality a point falls in, point doubt folded into confidence |
| `POST /api/ratings` | `{lat, lon, device, overall, safe?, respect?, help?, tags?}`; any other key is rejected |
| `GET /api/ratings/heat` | per-tile and per-state Bayesian scores for the heatmap |

## Sources

| Source | What it feeds | Key | Status on 2026-10-24 |
| --- | --- | --- | --- |
| Census Geocoder | point → county FIPS | none | captured live |
| NWS `api.weather.gov` | active alerts, time zone | none (User-Agent) | captured live (no alerts that day) |
| Open-Meteo | 7-night lows, hot days | none (non-commercial, CC BY 4.0) | captured live |
| USDA SNAP Retailer Locator (ArcGIS) | EBT stores, store type | none | captured live (data edited 2026-10-21) |
| OpenStreetMap Overpass | food banks, restrooms, water, libraries, laundromats, clinics, pharmacies, USPS, job agencies, shelters, opening hours | none (ODbL) | captured live |
| Urban Institute Education Data (NCES CCD 2022) | schools by level | none | captured live; county filter is ignored by the API, so we filter locally |
| Census ACS 5-year | median gross rent | Census key (keyless calls got "Missing Key") | not captured |
| BLS LAUS | county unemployment | optional | not captured |
| HUD Fair Market Rent | studio rent | HUD token | not captured |
| EIA | weekly regional + U.S. gas price | EIA key | not captured |
| Google Places Text Search | shelters, pantries, day centers | Maps key + billing | not captured |
| Transitland | transit stops | Transitland key | not captured |
| Kroger | live survival-basket price | client id + secret | not captured |
| Static tables | DOL minimum wage (VA, MD, WV, NC, TN), USDA Thrifty Food Plan June 2026, county→CoC crosswalk (VA-521, VA-502), HUD HIC/PIT, HRSA sites, local rules | none | wage, TFP and crosswalk filled; HIC/PIT, HRSA and local rules are empty templates |

State policy data (`footing/static/state_policy.json`, rebuilt and validated by
`python scripts/build_state_policy.py --check`), each field with its source and date: ILRC immigration
enforcement tiers, NCSL/NILC driver's licenses regardless of status, KFF Medicaid expansion and state
immigrant health coverage, DOL state minimum wage (July 1, 2026), NLIHC *Out of Reach 2026* housing
wage, HUD 2025 Point-in-Time counts (state totals reconcile to HUD's 745,652), NILC state food programs,
and statewide camping laws. Program rules by immigration status (`eligibility.json`) reflect H.R. 1
(SNAP, Medicaid from Oct 1 2026, ACA credits from Jan 1 2027), the Sept 18 2026 public charge rule, the
Sept 2026 vacatur of the PRWORA notices, and HUD's Feb 2026 mixed-status proposal (not final).

SNAP store names that say CVS, Walgreens, Rite Aid or Pharmacy also count as pharmacies (marked
"inferred from USDA SNAP store name"). Opening hours come from OSM `opening_hours`; anything the
parser does not fully understand (holidays, sunrise, comments) is shown as hours unknown.

## How a number is made

Each parameter turns a raw value into 0–100 with one of two rules (full table in `FACTORS.md`):

* **count**: `100 × (1 − e^(−n/k))`, so 0 → 0, k → 63, 3k → 95.
* **linear**: 100 at a "good" value, 0 at a "bad" value, clamped.

A category score is the weighted mean of its *known* parameters. The Settle Score is the weighted
mean of *known* categories. Confidence is `Σ weight × coverage × freshness / 100`, where coverage
is the share of a category's weight that had data and freshness runs from 1.0 (live) to 0.4 (annual).
Profile chips (car, kids, tonight, on foot) re-weight categories; they never change the data.

## Honesty rules built into the code

* A missing value is **Unknown** with a reason; it never becomes 0 and never gets guessed.
* A zero from a sparse source is not trusted: OSM maps almost no shelters, so "0 shelters" from
  OSM alone is Unknown until Google Places (or 211) confirms it.
* Recorded data answers only for its own tile (`resolve_replay`, tested).
* Model output that names a place, address or phone not in the data is removed and listed.
* Flyer readings are labeled "community-reported, unconfirmed" and saved nowhere.
* Couriers tagged as post offices, senior housing and bus shelters are filtered out (`classify_osm`).
* Keys never reach disk: recorded URLs and bodies are scrubbed; the Gemini key travels in a header.
* Crime and demographic data are excluded on purpose (`EXCLUDED_ON_PURPOSE`).

## Not done yet

* Globe: the camping-law table covers 8 states (6 bans or contested bans, plus Georgia and Oklahoma, whose
  laws push local enforcement and score 25); the rest are Unknown (not "no ban"). Policy data had a second
  check on Oct 24 (`docs/FACT_CHECK.md`) but has not been reviewed by a legal-aid professional. No state-level
  job or weather data. Per-state "why" sentences are translated; notes quoted from source documents
  stay in English and are marked "(en inglés)". Satellite imagery (EOX
  Sentinel-2 cloudless, CC BY-NC-SA) is non-commercial and needs a connection; the vector map works
  offline. Ratings live in SQLite (`FOOTING_RATINGS_DB`); on Cloud Run that is per-instance and
  temporary until a volume or database is attached.

* Keyed sources and Gemma are tested against **synthetic** responses (`tests/synthetic/`, labeled)
  and a local stub; none has been called live with a real key. Run `scripts/record_demo_towns.sh`
  with keys to verify them.
* `static/coc_capacity.csv`, `static/hrsa_sites.csv` and `static/local_rules.json` are empty.
  `scripts/load_hud_hic_pit.py --hic <HIC.xlsx> --pit <PIT.xlsx> --year 2024` fills the first from
  HUD's AHAR files (tested on workbooks shaped like HUD's, not yet on the real files).
* The SNAP fixture covers a ~2 km box around the point (10 stores), not the full 5 km radius.
* The flyer reader sends the photo inline; Google's Gemma docs show the Files API instead. Inline
  images are untested with Gemma 4.

License: Apache-2.0. Data stays under each provider's terms (listed per source in `footing sources`).
