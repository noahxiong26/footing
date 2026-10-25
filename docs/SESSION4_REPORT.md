# Footing: session 4 report (for designers and the next builder)

Written 2026-10-24, ~21:15 ET, by the 4th model in the rotation (Claude Opus 5.5). The session was stopped by
the owner because of a usage cap, so this report also says plainly what is **not** finished and why.

Screens from this session are in `docs/screens/session4/` (phone 390 px and desktop 1280 px).

---

## 1. What changed in this session (the list the human notes asked for)

1. **Virginia only.** The app now opens on a map of Virginia's 133 localities: 95 counties and 38 independent
   cities. In Virginia a city is not part of any county. "Roanoke city" and "Roanoke County" are different
   places with different rules, and the data keeps them apart. The earlier 50-state view still exists behind
   "All states (beta)".
2. **A Virginia data pipeline with real, sourced numbers for every locality.** Builder:
   `scripts/build_va_localities.py`. Output: `footing/static/va_localities.json`. Raw captures and how each was
   made: `data_raw/README.md`.
   - **Rent:** HUD Fair Market Rents FY2026, studio to 4 bedrooms, all 133 localities.
   - **Shelter:** HUD Point-in-Time count (Jan 2025) and Housing Inventory Count. These are counted by
     Continuum of Care (16 in Virginia), and each locality is mapped to its CoC. Checked against HUD's state
     total of 7,240 people, 1,349 of them outside.
   - **Population:** Census estimates for 2025.
   - **Food:** USDA SNAP retailers, counting full grocery stores and the Restaurant Meals Program (hot meals
     on EBT).
   - **Help places:** OpenStreetMap: food banks, clinics, shelters, restrooms, libraries, laundry and similar.
   - **Free buses:** the 7 fare-free transit systems.
   - **Local camping rules:** confirmed one by one from the city code or council record. Hampton and Bristol
     ban camping. Roanoke limits it. Charlottesville closes sites. Danville's rule is only proposed. Fairfax
     County has a clearing policy but no ordinance. Every other locality is **Unknown, not "no ban"**.
   - **Immigration enforcement:** ICE 287(g) agreements, 22 in Virginia, matched to the localities they cover.
   - **Reported crime:** FBI Crime Data Explorer 2025, all 412 Virginia agencies.
3. **Virginia Fit Score with a confidence score.** The engine is `footing/web/vafit.js`, with a Python twin in
   `footing/vafit.py`. Both produce identical output, and a node test checks this. It has seven parts:
   shelter, rent, help nearby, local laws, immigration safety (only if the person's status is at risk),
   reported crime (off unless turned on), and community ratings. Each part is 0–100 or Unknown. Unknown parts
   drop out and are never counted as 0.
   - **Confidence** = the sum of weight × freshness over the parts that are known. Shelter data from the
     Balance of State CoC, which covers 71 localities with one count, has lower confidence because it says
     little about any one town.
   - **Small-place correction:** small places' per-person counts are pulled toward the Virginia average, so a
     town of 2,000 with one grocery store does not look like a food paradise.
   - **Stability band:** each place also gets a range like "usually #2–#7", taken from 200 re-weightings.
4. **Bad coordinates and poor data.** `footing/va.py` classifies any point and never guesses. Its answers are
   ok, not a number (NaN/infinity/text), off the globe, outside Virginia (it names the state), or on open water
   (inside a county's water area such as the Chesapeake Bay). Ratings use it, so bad points are refused with a
   plain reason. On the rating side:
   - A tile with fewer than 3 ratings is never shown on its own; it still counts toward its city or county.
   - Each network gets a daily cap, keyed on a salted hash so the IP address is never stored.
   - Each device still has its cap too.
5. **New UI for the reasoning: "How the score adds up".**
   - **Score mosaic:** each part is a column. Its width is how much the person said it matters, its height is
     how well the place does, and the filled area is the score. Striped columns are parts with no data, left
     out.
   - **Below the mosaic:** one row per part with:
     - the score;
     - "45% of your score";
     - one plain-language line in the person's language, built from the numbers;
     - a "Details" fold with the full English reason and the linked sources with their dates.
   - **Confidence meter:** shows the medium and high thresholds, plus "Based on 4 of 6 parts".
   - **Lists:** help places in the locality, with phone and hours when OpenStreetMap has them, and a
     searchable list of all 133 places.
6. **Kids and preferred rooms as parameters.**
   - The bedroom choice (studio to 4, or "pick for me") changes which rent is used.
   - Kids switch the shelter measure to family beds per person in families.
7. **Languages: 8.** English, Spanish, Vietnamese, Korean, Chinese, Arabic, Amharic, and Persian/Dari.
   - The six new ones were picked from Virginia's largest groups who speak English less than very well
     (ACS 2024 via MPI): Spanish 285,838; Vietnamese 32,334; Korean 30,581; Chinese 22,344; Amharic/Somali
     group 17,173; Arabic 16,568; Persian/Dari 15,483; Tagalog 12,358. Tagalog is not done yet.
   - Arabic and Persian lay out right-to-left.
   - **All translations are machine translations, including Spanish from earlier sessions, and each screen
     says so.** Program notes and the "Details" text stay in English.
8. **Smaller fixes:**
   - Georgia and Oklahoma "Safe Neighborhood" laws are scored as enforcement mandates (25), not statewide
     bans.
   - Virginia's state camping status is "no statewide ban" (75).
   - The ACA notes now include the Jan 1, 2027 tax-credit cutoff for pending asylum and parole.
   - The service-worker cache is now v6.
   - New endpoints `/api/va` and `/api/va/check`.
   - The standalone demo builder now includes the Virginia data.
9. **Tests:** 155 pass. The baseline had 115.

## 2. What is NOT finished, and why

| Not done | State | Why |
| --- | --- | --- |
| **Push to GitHub** | Not pushed. A `footing.bundle` with full history and a zip are on Drive in `hack 20/25/4th`. | This session's GitHub access only covers `first-paycheck-simulator`. No `footing` repo exists that it can reach, and the `gh` token is invalid. Someone with the account must create an empty repo, then run `git clone footing.bundle footing && cd footing && git remote add origin <url> && git push -u origin main`. |
| **Updated Playwright smoke** | `scripts/ui_globe_smoke.py` is **out of date**. It expects the old language button and the state view, so it will fail against the new UI. | No time left. I tested the new UI with an ad-hoc script at 390 px and 1280 px, for both the server app and the standalone demo: intro, profile, top 5, locality, mosaic and reasons, with no page errors. The rating flow, the search list, Arabic RTL and the 320 px width were **not** clicked through. |
| **Rating flow in the new UI** | Code written: a short sheet until a spot is picked, a far-out tap zooms in, a tap outside Virginia is refused, plus a Back button. | Covered by server tests, **not** by a browser run. |
| **Translation review** | Machine translated, labeled on screen. | Needs native speakers, ideally from Virginia community groups. |
| **Spanish (and other) "Details" text** | The reasons inside "Details" are English only. The one-line summaries are translated. | The engine builds its reasons in English, and both engines must match exactly. Translating them means templating inside both engines. |
| **Tagalog** | Not added. | 8th-largest group, and ran out of time. |
| **Local camping rules for the other 127 localities** | Unknown. | Each one needs a person to read the city or county code. The 6 done here took a long time each. |
| **More recorded towns (Roanoke, Blacksburg, Richmond...)** | Only Christiansburg has a recorded "receipt" with walk times. | Not started. |
| **Published demo link (Artifact)** | `out/demo` builds and loads, and the zip is on Drive. It was not published as a link. | Out of time. |
| **Independent fact-check of the Virginia data** | Not done. | A separate reviewer should spot-check 10 localities against the sources in `data_raw/README.md`. |
| **docs/PIPELINE.md, README and FACTORS updates** | The pipeline is described in section 4 of this report. README and FACTORS still describe the 50-state version. | Out of time. |

### Why this session took so long

- **The sandbox can only reach GitHub and package registries.** Every government source was captured through
  a real Chrome window, one request pattern at a time: HUD, Census, USDA, FBI, ICE, OSM and TIGER. That runs
  into several limits:
  - The browser tool returns about 1 KB per script call.
  - Long jobs hit a 45-second limit.
  - Some sites block cross-site requests.
  - Results had to be written into the page and read back in ≤50 KB chunks.
  - HUD rent pages are one county per page, 133 times, with special cases for Small Area FMR metros.
  - The FBI data is one request per agency per measure, 412 agencies.

  This was most of the session.
- **The repo had to be rebuilt from Drive first.** There was no git remote. A few large files came back
  truncated and had to be re-assembled.
- **Boundary problems.** The simplified national county shapes erase small cities like Falls Church, so I
  switched to Census TIGER shapes for Virginia. TIGER includes water, so open-water detection needed a second
  shoreline check.
- **Checking before building.** Every number was checked against the publisher's totals, so nothing is
  invented and Unknown stays Unknown. That is slower, but it is the owner's rule.

## 3. Thoughts, issues and ideas for the designers

### What the score says today (default profile)

- **The top places are Covington, Lynchburg, Alleghany County, Roanoke city and Danville.** Small, cheap
  places in the southwest and southside rank high. Northern Virginia ranks low, because rent there takes
  121 hours a week at minimum wage.
- **This is honest, but it has a real weakness.** Shelter data exists only per Continuum of Care. Covington
  shares Roanoke's count, but the beds are in Roanoke, about 50 miles away. The screen says "the beds may be in
  a neighboring one", and confidence drops. A designer should still decide whether to show distance-to-beds.
  The data for that, HUD HIC by project, is not public with addresses.

### Crime: why it is opt-in and not in the default score

Footing does not score crime by default, for four reasons:
- Crime reports measure where police write reports as much as where danger is.
- Using them pushes people away from poorer and Black neighborhoods, the redlining pattern.
- People without homes are more often victims than offenders.
- Virginia Beach PD sent no 2025 data, so the city's largest agency would be missing.

Crime is therefore off unless the person turns it on, and the layer only appears after that. **Better safety
signals we already have:**
- the "I felt safe" rating;
- the "police moved people along" tag;
- 287(g) agreements;
- local camping bans.

**Idea:** show "felt safe" from ratings as its own map layer once there are enough ratings.

### Bad coordinates and poor data

The rule is "never guess, say why", and section 1, point 4 covers it. **Idea:** when a place has low
confidence, sort it below places with the same score and higher confidence, and show the stripes more
strongly.

### Score representation (human note)

The mosaic replaces the old bar list. **Open questions for designers:**
- Is the width-times-height idea clear to someone in a hurry? Test with 3 to 5 people. A fallback could be a
  stacked bar that adds up to the score.
- The labels under narrow columns truncate ("Lo...", "W...").
- Should the mosaic animate when the person reorders priorities in the profile? This would be a single
  intentional motion.

### Other ideas

- **A "compare 2 places" view using two mosaics side by side.** The old app has `/compare` for points.
- **A statewide tab.** SNAP, Medicaid and ID rules are the same everywhere in Virginia, and they are now shown
  as "the same everywhere in Virginia". A tab could keep them from repeating on every locality.
- **Make 211 more prominent at night** when "I need a place tonight" is chosen.
- **Low-bandwidth mode:** the map and data are about 2 MB. A text-only list view could be the first paint on
  slow phones.

### Multi-agent pipeline? (human note)

The pipeline today:

```
raw captures (data_raw/*.json, one file per source, documented)
    -> scripts/build_va_localities.py
         - matches by FIPS code
         - validates against publisher totals
         - writes Unknown with a reason when data is missing
    -> footing/static/va_localities.json
    -> the phone scores it (vafit.js)
```

**It does not need to be multi-agent to run.** A refresh is deterministic:
1. Download the files.
2. Run the builder.
3. Run the tests.

**Agents would help in two places:**
- **Collection from sources with no API.** One agent per source, for local ordinances (133 city and county
  codes) and shelter hours and phone numbers. Each returns a cited row, or Unknown.
- **Verification.** A second agent that never saw the first agent's work re-checks a sample against the
  source.

Keep the merge step as plain code, so the same inputs always give the same output.

## 4. Sources

Every source has a URL, publisher and as-of date in `footing/static/va_localities.json` → `sources`. The raw
files and their exact requests are listed in `data_raw/README.md`. The main publishers:
- HUD (FMR FY2026, PIT and HIC 2025, CoC areas);
- U.S. Census (TIGERweb, population estimates v2025);
- USDA FNS (SNAP retailers);
- FBI Crime Data Explorer;
- ICE (287(g) participating agencies, read Oct 24, 2026);
- OpenStreetMap (Overpass, Oct 25, 2026 UTC);
- APTA and Virginia DRPT (fare-free transit);
- Virginia Executive Directive One (2026);
- HB1394 (2026);
- city code and council records for Hampton, Bristol, Roanoke, Charlottesville, Danville and Fairfax County.
