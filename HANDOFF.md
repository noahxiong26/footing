# HANDOFF — Footing (read this first)

Last updated **2026-10-25, early hours** by the 5th model in the rotation (Claude Opus 5), which **merged
sessions 3 and 4 into one `main`**. Sections S5.x are this session. The session 4 report
(`docs/SESSION4_REPORT.md`) is still worth reading for the designer notes; where it disagrees with S5, S5
wins, because some of what it lists as unfinished is now done.

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
2. **Click the app through a real browser.** Nobody has. This sandbox cannot install one —
   `cdn.playwright.dev` is not reachable from it, and the network allowlist covers only GitHub and the
   package registries. On a laptop: `pytest -q`, then `uvicorn footing.api:app --port 8080`, then walk
   through intro → profile → top 5 → locality → mosaic → *Details* → search → rate, at 320, 390 and 1280 px,
   in English and in Arabic (right-to-left). The rating flow and RTL have never been seen working.
3. **Rewrite `scripts/ui_globe_smoke.py`.** Still session 3's; it expects the old language button and the
   state view, so it will fail against the current UI. Section S4.1 item 2 lists what it should cover. Keep
   its privacy check: no profile word may leave the browser.
4. **Show block-level crime in the locality panel.** The engines and `GET /api/va/fit` support it; the panel
   does not, because it ranks all 133 localities with no point. It needs a point — the rating pin, or a
   "near me" — and a browser to click through, which is why this session stopped at the API.
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

> You are the 6th model continuing Footing, a hackathon app for people experiencing homelessness in
> Virginia, including immigrants. Sessions 3 and 4 have been merged into one `main`. Read `HANDOFF.md`
> sections S5.0–S5.3 first, then `docs/PIPELINE.md`, `docs/FACT_CHECK.md`, and `docs/SESSION4_REPORT.md`
> for the designer notes. Run `pytest -q` (expect 191 passed) and
> `python scripts/build_va_localities.py --check`. Then work S5.2 in order.
>
> Rules from the owner:
> - Never invent data. Unknown with a reason, never a guess, and never a 0 standing in for a blank.
> - Say plainly what you could not test, and why. "Done" only counts if it is actually done.
> - Keep JS/Python parity, keep the tests green, add tests for what you change.
> - Boil the ocean: complete, tested, documented.
> - Before you hand off, update S5.0/S5.2 (or add S6.x) at the top of this file.

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
