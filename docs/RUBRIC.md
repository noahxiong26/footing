# Footing against the judging rubric

This maps each line of the "responsibility and feasibility" half of the rubric (50 of the points) to
evidence a judge or the next developer can open. The other half of the rubric was not visible in the
slide we have; add it here when known. Each row says what is **done**, where to see it, and what is
**not done**. Nothing here is a claim the code does not back.

Updated 2026-10-25 (S9). Live demo: the claude.ai Artifact linked in `HANDOFF.md` S9.0.

## Responsible AI, ethics and accessibility (25)

### Safety and grounding (10)
*Explicit guardrails against hallucinations, adversarial inputs, bias and harmful output.*

| Guardrail | Where |
| --- | --- |
| **No model in the scoring path.** Every score is a deterministic formula over cited public data, identical in Python and JavaScript (parity tests). | `footing/vafit.py`, `footing/web/vafit.js`, `tests/test_vafit.py` |
| **Unknown is never zero.** A missing value is shown as "?" with a reason and left out of the score; confidence drops instead. | `vafit.laws_component`, builder `validate()`, README "Honesty rules" |
| **Every number links to its source** and capture date. | Details under each factor; `va_localities.json → sources` |
| **Gemma 4 output is checked before anyone sees it** (plan and flyer reader): every step must point to a place the pipeline found; any address or phone not in the data is removed; on failure the rule-based plan is shown and the screen says so. | `footing/flyer.py`, `footing/planner.py`, README "Gemma 4 grounding" |
| **Adversarial input.** Flyer uploads: 6 MB cap, image types only. Ratings: points outside Virginia, on open water or NaN are refused on the phone **and** re-checked on the server; fixed fields only; per-device and per-network daily caps on a salted hash. | `footing/flyer.py`, `footing/va.py`, `footing/ratings.py` |
| **Bias.** Crime is off unless the person turns it on; trespass/loitering calls are counted but never scored as danger (a test fails if this changes); people without homes are more often victims, and the screen says so. Rent is measured against the minimum wage, not an average income. | `tests/test_vafit.py`, crime question in About you |
| **Legal caution.** Immigration answers come with a "before you apply" warning and free legal help, not advice. | Programs tab |
| **Two independent data captures were compared**, and the disagreement found a real bug (Farmville's crime assigned to the wrong county). | `docs/FACT_CHECK.md` |

**Not done:** the independent 10-locality fact-check (sample in `HANDOFF.md`); four new program pages cited but not yet read row-by-row; native-speaker review of the machine translations (labelled on every screen).

### Privacy and data ethics (8)
*Responsible data handling, confidentiality, collecting only what you need.*

| Practice | Where |
| --- | --- |
| **The profile never leaves the phone.** Status, household and priorities are scored on the device; the globe smoke checks 4,000+ requests and fails if any profile word is sent. | `scripts/ui_globe_smoke.py` (privacy check) |
| **A rating stores only** the ~1 km tile, the hour, stars and fixed tags. No profile, no text, no device id in the shared store; the network address only as a salted hash for the daily cap. | `footing/ratings.py`, `demo/standalone_backend.js` |
| **Reset my answers / Start over** clears everything stored on the device (except the chosen language) after an in-page confirmation. | nav "Start over" |
| **Quick exit.** "Hide this page" blanks the screen at once. | top bar |
| **No accounts, no tracking, no analytics.** Keys travel in headers and are scrubbed from recorded captures. | README "Honesty rules" |

### Inclusive design (7)
*WCAG-aligned UI: keyboard navigation, readable contrast, screen-reader support.*

| Practice | Evidence |
| --- | --- |
| **Automated WCAG 2.2 AA audit: 0 violations** on 18 screens (Start, About you, Best fits, place Score/Help/Programs tabs, All places, Rate, Start over) in English at 1280 px and Arabic at 390 px, axe-core 4.10.2, 2026-10-25. | rerun: see `HANDOFF.md` S9 |
| **Keyboard:** skip link to the panel; every control is a real button; place tabs follow the ARIA tabs pattern (arrow keys, Home/End); priorities can be reordered with buttons as well as by drag; visible focus rings. | `globe.js` |
| **Screen readers:** headings receive focus on screen change; toasts and priority moves are announced in a polite live region; the live preview is a live region; decorative visuals are `aria-hidden`. | `globe.js` |
| **9 languages** (English, Spanish, Vietnamese, Korean, Chinese, Arabic, Amharic, Dari/Persian, Tagalog) with right-to-left layout, chosen for Virginia's largest immigrant communities. Every visible string is checked for a translation by a test. | `footing/web/i18n*.js`, `tests/test_i18n_langs.py` |
| **Small screens and motion:** works from 320 px; all animation stops under `prefers-reduced-motion`. | smoke at 320/390/1280 px |

**Not done:** testing with real screen-reader users and with people who have experienced homelessness.

## Feasibility, scalability and sustainability (25)

### Deployment viability (10)
*A low-friction path to deploy for resource-constrained nonprofits and community groups.*

* **The whole app is one static folder (~2.4 MB):** no server, no database, no API keys. `python scripts/build_standalone_demo.py out/demo` builds it; any free static host (or a claude.ai Artifact, as now) serves it.
* **Works offline after the first visit** (service worker) and on old phones (no build step, plain JavaScript).
* **Optional server** (FastAPI, one Dockerfile, Cloud Run) adds live town receipts and the Gemma features; the static demo does not need it.
* **Data refresh is plain code:** `scripts/build_va_localities.py` rebuilds and validates against publisher totals (`--check`).

### Inference cost efficiency (8)
*Balances token use, model size and hosting cost sustainably.*

* **Scoring uses zero model calls.** The ranking of 133 places, the 90% rank ranges (200 sampled weightings) and the live preview all run on the phone in milliseconds.
* **Gemma 4 is used only where a model adds something** (reading a photographed flyer, wording a plan), with a small open model (`gemma-4-26b-a4b-it`), a rule-based fallback, and nothing called when the key is absent.
* **Data collection reuses saved captures** instead of re-searching (`AGENTS.md`, `docs/DATA_WORK.md`, `scripts/data_lookup.py`); replay fixtures keep tests and demos at $0.
* **Hosting cost of the demo: $0.**

### Documentation and maintenance (7)
*Clear setup guide, mapped API dependencies, open-source docs.*

* `README.md`: run in 30 seconds with no keys; every data source with its URL and as-of date; the API.
* `docs/PIPELINE.md` (data pipeline), `docs/DATA_WORK.md` (how to find or refresh a fact), `docs/FACT_CHECK.md` (open questions), `docs/RATING_FORMULA.md`, `AGENTS.md` (rules for AI coding agents), `HANDOFF.md` (what changed each session, what passed, what is next).
* 252 automated tests including JS/Python parity; two browser smoke scripts.
* Apache-2.0 license.
