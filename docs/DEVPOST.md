# Footing — Devpost draft

> Draft for the MLH Hacktoberfest Hack Day submission (Oct 24, 2026). Prize tracks: **Best
> Open-Source AI Project** and **Best Use of Gemma 4**. Lines marked **[TODO]** need your input;
> everything else matches what the code does today.

**Tagline:** Where could you land for the next 30 days? A Settle Receipt for people without a home,
built only from public data, that says "we don't know" instead of guessing.

## Inspiration

When you lose housing, the first question is not "where is the nearest shelter" but "can I make it
*here* for a month?" That depends on things scattered across a dozen agencies: whether a grocery
store nearby takes EBT, what a week of food and a tank of gas cost, whether the library is open
tonight to charge a phone, how cold tonight gets, whether the kids can enroll at a school. Apps
that exist list shelters. None of them add it up, and the ones that try fill gaps with guesses,
which is dangerous when someone walks two miles on bad information.

[TODO: one or two sentences of your own on why the team picked this — e.g. something you saw in
Blacksburg/Christiansburg.]

## What it does

Footing prints a **Settle Receipt** for any point in the U.S.:

* A **Settle Score (0–100)** over 10 categories: shelter, food and EBT, cost to stay, income,
  getting around, health, hygiene and connection, kids and school, weather risk, paperwork and local rules.
* **Dollar lines**: a week of food (USDA Thrifty Food Plan, and a live local basket when Kroger is
  connected), regular gas (EIA), studio Fair Market Rent (HUD), state minimum wage (DOL).
* **Nearest places with open/closed right now**: EBT grocery, library, restroom, water, clinic,
  pharmacy, laundromat, post office (General Delivery), job center.
* A **confidence** number, and for every Unknown, the reason.

From the receipt:

* **30-day plan (Gemma 4)** — Day 1 / Week 1 / Month 1 steps. Every step is tied to a place the
  pipeline actually found; Gemma output naming any other place, address or phone is removed
  before it is shown, and the removed steps are listed. No key or no quota → a rule-based plan.
* **Tonight** — what is open now within an hour's walk, tonight's low, and "Call 211" when no
  shelter is confirmed (we never invent one).
* **Pocket card** — a printable card with up to five places, their hours, 211, and a QR code back
  to the receipt, for when the phone dies.
* **Compare towns** — two or three places side by side. Unknown is never compared against a number.
* **Snap a flyer (Gemma 4 vision)** — photograph a paper flyer on a church door; Gemma pulls out
  the service, days, phone and address, labeled "community-reported, unconfirmed."

No account, no sign-in, nothing stored. The location is rounded to a ~1 km tile on the phone's
side of the API before any source is called.

## How we built it

* **Pipeline (Python):** 15 source adapters behind one fetcher with live / record / replay modes
  and an SQLite cache. Keyless: Census Geocoder, NWS, Open-Meteo, USDA SNAP Retailer Locator,
  OpenStreetMap Overpass, Urban Institute Education Data. Keyed: Census ACS, BLS LAUS, HUD FMR,
  EIA, Google Places, Transitland, Kroger. Static: DOL minimum wage, USDA Thrifty Food Plan,
  county→CoC crosswalk.
* **Scoring:** 33 parameters (29 built), each normalized to 0–100 by a documented count or linear
  rule (`FACTORS.md`). Category and overall scores average only what is known; confidence weighs
  coverage and freshness.
* **Gemma 4** (`gemma-4-26b-a4b-it` via the Gemini API) for the plan and the flyer reader, with a
  grounding validator in front of the user.
* **API:** FastAPI. **App:** a no-build PWA (vanilla JS) with an offline cache.
* **Tests:** 74 pytest tests on real captured responses (Christiansburg, VA, Oct 24 2026) and
  labeled synthetic responses, a Playwright run of every screen at phone size, and a clean-install
  check of the packaged app.
* **Deploy:** Cloud Run from source, keys in Secret Manager, max 2 instances, and Places quotas
  sized to stay inside the free tier of our $25 Google Cloud credit.

## Challenges we ran into

* **Honest zeros.** OpenStreetMap maps almost no shelters, so "0 shelters" was a lie. We made
  sparse-source zeros count as Unknown until a second source confirms.
* **Replay leaking across towns.** Our first demo mode replayed Christiansburg's data for Roanoke
  and showed a confident score for a town we had never queried. Recorded data now answers only for
  its own 1 km tile, with a test that fails if it ever leaks again.
* **Grocery ≠ EBT store.** The nearest EBT retailer was a specialty shop. The planner now prefers
  full grocery stores by USDA store type.
* **APIs that don't do what the docs say:** the Urban Institute API ignores its county filter, the
  Census API now wants a key, and OSM tags FedEx counters as post offices.

## Accomplishments we're proud of

* Every number on screen can be traced to a source and a timestamp, and every missing number says why.
* The model cannot send someone to a place that does not exist.
* It runs offline from recorded data, so the demo does not depend on venue Wi-Fi.

## What we learned

[TODO: in your words. Suggestions: how much "live" public data is really annual; how much the
UX changes when you design for a cracked phone at 5% battery.]

## What's next

* Fill shelter capacity from HUD HIC/PIT (loader written) and HRSA health-center sites.
* Verify the keyed sources live, and record Blacksburg, Radford and Roanoke for the demo.
* Spanish plan and receipt (the plan endpoint already takes `lang`).
* Partner with the local CoC (VA-521) and 211 Virginia to confirm shelter data.

## Built with

python · fastapi · gemma-4 · gemini-api · google-places · cloud-run · openstreetmap · usda-snap ·
national-weather-service · open-meteo · census · hud · eia · bls · playwright · pwa

## Links

* GitHub: [TODO: repo URL after you push]
* Demo: [TODO: Cloud Run URL after deploy, or "runs locally in replay mode"]
* Video: [TODO]

## Demo script (2 minutes)

1. Start screen → tap **Kids with me** → **Christiansburg, VA**. Point out the demo-mode notice
   (real data recorded today) and the 1 km rounding line.
2. Receipt: score ~77, confidence medium. Open **Shelter: Unknown** → the reason ("none found, but
   OpenStreetMap often misses these; a zero needs Google Places to confirm it (or call 211)").
   This is the honesty pitch.
3. **30-day plan** → with a key, Gemma 4 writes it; show the "removed steps" note if any.
4. **Tonight** → what is open now (on a Saturday afternoon: the library, until 17:00), tonight's
   low, Call 211.
5. **Pocket card** → print preview.
6. **Compare** → Roanoke shows "no data" instead of a made-up score.
7. **Snap a flyer** → photograph a real flyer (bring one).
