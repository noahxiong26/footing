# Footing — Devpost submission

> Submission text for the MLH Hacktoberfest Hack Day. Prize tracks: **UI track** (primary), **Best Open-Source
> AI Project**, **Best Use of Gemma 4**. Lines marked **[TODO]** need the team's own words; everything else
> matches what the code does today (2026-10-25). How each judging criterion is met: [`RUBRIC.md`](RUBRIC.md).

**Tagline:** If you lost your home tonight, where in Virginia could you actually make it for a month?

## Inspiration

When you lose housing, the question is not only "where is the nearest shelter" but "can I make it *here*?"
The answer is scattered across a dozen agencies: shelter counts, rents against the minimum wage, which food
and health programs your papers allow, whether this city punishes sleeping outside, whether the sheriff works
with ICE. Apps that exist list shelters. None add it up for one person, and the ones that try fill gaps with
guesses, which is dangerous when someone walks two miles on bad information.

[TODO: one or two sentences of your own on why the team picked this.]

## What it does

Footing scores all **133 Virginia cities and counties** for one person and shows the result on a globe that
follows the real sun: at night, the places that fit you glow like lit windows.

* **Tell it about you, privately.** Immigration papers (15 choices, including "prefer not to say"), who is with
  you, how many bedrooms (0 to 8), your situation, and what matters most. Everything stays on the phone; a
  browser test checks every request and fails if any answer leaves the device. **See an example person** shows
  the whole flow without typing anything.
* **Drag what matters most to the top.** The ranking re-orders live, and a preview shows the top three places
  move as you drag. Two people see two different Virginias. Each place shows a 90% rank range from 200
  re-weightings, so a "#4" that could easily be "#9" says so.
* **Open a place and see the answer before any reading:** hours of minimum-wage work a week to pay rent, the
  share of people without homes who slept outside, help places nearby. Then three tabs:
  * **Score:** each part as a bar, with its plain-language reason and a link to the source (HUD, the Census,
    USDA, the FBI, ICE's 287(g) list, the city's own code). Parts we could not confirm are a striped "?",
    never a zero. A rough everyday-cost estimate is shown and labelled as an estimate, never scored.
  * **Help nearby:** mapped food, clinics, libraries, restrooms and laundries, with hours and phones.
  * **Programs:** 18 programs plus an ID row, grouped by what *your* papers allow (You can use / Check first / Not open to you),
    including subsidized housing, rapid re-housing, HUD-VASH, energy help, Lifeline, school meals and child
    care, with a "talk to legal aid first" warning where public charge applies.
* **Rate a place** (1–5 stars, tags like "shelter was full" or "Spanish spoken"); ratings become a heatmap with
  a Bayesian average so one review can't paint a town red. Only a ~1 km tile, the hour, stars and tags are kept.
* **Nine languages** (English, Spanish, Vietnamese, Korean, Chinese, Arabic, Amharic, Dari/Persian, Tagalog),
  right-to-left where needed, machine translated and labelled as such on every screen.
* **Safety:** "Hide this page" blanks the screen at once; "Start over" clears everything after a confirmation.

The server version adds a **Settle Receipt** for any point in the U.S. (live public data for one ~1 km tile),
a **30-day plan** and a **flyer reader** written by **Gemma 4** and checked against the data before anyone
sees them, a "tonight" list, a printable pocket card and town comparison.

## How we built it

* **Data pipeline (Python):** HUD Fair Market Rent FY2026, HUD Point-in-Time and Housing Inventory 2025 (16
  Continuums of Care), Census population estimates and TIGER boundaries, USDA SNAP retailers, OpenStreetMap,
  FBI Crime Data Explorer (412 agencies), city incident data for Norfolk and Charlottesville, ICE 287(g), and
  local camping ordinances read from city codes. A builder validates everything against publisher totals and
  writes Unknown with a reason whenever a value is missing.
* **Scoring on the phone:** a Fit Score engine in JavaScript with a line-for-line Python twin; a test runs both
  on every locality and requires identical output. Rank-Order Centroid weights from the person's ordering.
* **Gemma 4** (`gemma-4-26b-a4b-it` via the Gemini API) for the plan and the flyer reader, behind a grounding
  validator: a step must point to a place the pipeline found; any address or phone not in the data is removed.
* **UI:** MapLibre GL 5 globe projection, a sky texture computed from the sun's position (NOAA declination and
  equation of time), a no-build vanilla-JS PWA with an offline cache, drag-to-reorder with transform-only
  animation, WAI-ARIA tabs, a skip link and live-region announcements.
* **Hosting:** the interactive demo is one 2.4 MB static folder (`site/`) on GitHub Pages: no server, no keys,
  zero AI calls to score. The server version runs on Cloud Run.
* **Tests:** 261 pytest tests (engine parity, data validation, translations in all nine languages, replay
  isolation, the published site matching its source) and two Playwright smoke runs; the full one covers 108
  screens in English, Arabic and Tagalog at 320, 390 and 1280 px, including a real mouse drag. An axe-core
  audit finds 0 WCAG 2.2 AA violations on 18 screens.

## Challenges we ran into

* **The law changed under us.** Between July 2025 and September 2026, SNAP, Medicaid, the ACA credits, public
  charge and the PRWORA notices all changed, and a court partly undid one change. A single "documented /
  undocumented" switch would be wrong for refugees, TPS holders and green-card holders, so we model 15 statuses
  and date every rule.
* **Virginia's independent cities.** "Roanoke city" and "Roanoke County" are different places with different
  rents and ordinances; small cities vanish on common map files. Everything is keyed by FIPS code.
* **Two captures disagreed, and that found a bug.** Comparing two independent FBI captures showed Farmville
  PD's crime assigned to the wrong county, quintupling its rate. Agencies are now placed by their coordinates.
* **"Unknown" on a map.** An unchecked place must not look like a bad place: it is striped, and its weight moves
  to what we do know.
* **Crime data is not danger data.** Trespass and loitering calls show where police make contact with people
  without homes; they are counted and shown but never scored as danger, and crime is off unless you turn it on.

## Accomplishments we're proud of

* Every number on screen traces to a public source and a date, and every missing number says why.
* A person can see which places fit their family without telling a server anything about themselves.
* The model can't send someone to a place that does not exist.
* It runs free, offline after the first load, on a 320 px phone, in nine languages.

## What we learned

[TODO: in your words.]

## What's next

* An independent fact-check of ten random localities, end to end, off the publishers' own pages.
* Camping rules for the remaining localities, read from each code.
* Native-speaker review of all eight translations, and testing with screen-reader users and people with lived
  experience of homelessness.
* Partner with Virginia's Continuums of Care and 211 Virginia to confirm shelter data.

## Built with

javascript · maplibre-gl · python · fastapi · gemma-4 · gemini-api · playwright · axe-core · github-pages ·
cloud-run · hud · census · usda-snap · fbi-crime-data · openstreetmap · pwa

## Links

* Live demo: https://noahxiong26.github.io/footing/ (after Pages is enabled; see README)
* GitHub: https://github.com/noahxiong26/footing
* Video: [TODO: link after upload]
