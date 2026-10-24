# Footing

**Where could you land for the next 30 days?** Footing is a free, open-source phone app for
people experiencing homelessness. Pick a town (or share a location rounded to ~1 km) and it
prints a **Settle Receipt**: a 0–100 Settle Score built from live public data, what a week of
food and gas costs there, the nearest EBT grocery, library, restroom, clinic and post office
with their hours, and a plain reason for every number it could not find.

```
point ─▶ snap to ~1 km tile ─▶ 15 source adapters ─▶ places + measures (each with provenance)
      ─▶ 33 parameters (29 built, 4 planned) ─▶ 10 categories ─▶ Settle Score + confidence
      ─▶ receipt · 30-day plan (Gemma 4) · tonight list · pocket card · town compare
```

## Run it in 30 seconds (no keys, no network)

```bash
pip install -e ".[dev]"
FOOTING_MODE=replay uvicorn footing.api:app --port 8080     # open http://localhost:8080
python -m footing receipt --lat 37.1299 --lon -80.4089 --profile car,kids   # same data, CLI
pytest -q                                                    # 74 tests
```

Replay mode serves **real responses captured on 2026-10-24** for downtown Christiansburg, VA
(`fixtures/christiansburg_2026-10-24/`, see its `MANIFEST.json`). Other towns show
"no demo data" and every score as Unknown: recorded data is never reused for a different place.
Keyed sources show as Unknown because no keys were set when the fixtures were captured.

## What the app does

| Screen | What it shows | Where it comes from |
| --- | --- | --- |
| **Receipt** | Settle Score, 10 category bars, dollar lines (food week, gas, studio rent), nearest places with open/closed now | `/api/receipt` |
| **30-day plan** | Day 1 / Week 1 / Month 1 steps, each tied to a real place from the receipt | `/api/plan`: Gemma 4 when `GEMINI_API_KEY` is set, a rule-based plan otherwise |
| **Tonight** | Places open now within an hour's walk, tonight's low, "Call 211" when no shelter is confirmed | `/api/tonight` |
| **Pocket card** | A printable pocket-size card with up to 5 places, hours, 211, and a QR back to the receipt | `/api/pocket-card.svg` |
| **Compare** | Two or three towns side by side; Unknown is never compared | `/api/compare` |
| **Snap a flyer** | Photo of a paper flyer → service, days/times, phone, address, marked "community-reported, unconfirmed" | `POST /api/flyer` (Gemma 4 vision) |

The front end is a no-build PWA (`footing/web/`): large tap targets, works at 320 px, high
contrast, no sign-in, nothing stored on the server. The service worker keeps the last good answer
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
