# How the Fit Score works

The Fit Score answers one question for one person: *of the 50 states and DC, where would I most likely find my footing?* It is personal. Two people looking at the same globe see different colors, because the score depends on their immigration status, who is with them, and what they say matters most.

Everything on this page runs on the person's phone (`footing/web/fit.js`). Their status, household and priorities are never sent to the server. `footing/fit.py` is a line-for-line Python mirror, and `tests/test_fit.py` checks that both produce the same output on the same inputs.

Data was read on October 24, 2026. Every number has a source listed in `footing/static/state_policy.json` → `sources`, and in `footing/static/eligibility.json` → `sources`.

---

## 1. What the person tells us

All questions are optional. "Prefer not to say" is always an option and is never treated as a worst case.

| Input | Choices | What it changes |
|---|---|---|
| Immigration status | U.S. citizen · green card 5+ years · green card under 5 years · refugee or asylee · Cuban/Haitian entrant · COFA citizen · asylum case pending · TPS · DACA · humanitarian parole · T/U visa or VAWA · other visa · no papers right now · not sure · prefer not to say | Which programs count as usable (Help you can use), and whether the enforcement-safety part applies at all |
| Who is with you | kids · pregnant · partner · pets · some family are U.S. citizens (mixed-status) | Children's and pregnancy coverage, SNAP for citizen children, enforcement safety for mixed families |
| Situation | need a place tonight · have a car · no ID right now · veteran · disability | "Tonight" moves Shelter space to the top; "No ID" makes ID the biggest part of Help you can use; disability exempts green-card holders from the 5-year SNAP wait and qualifies adults in non-expansion states |
| Age band | 18–24 · 25–49 · 50–61 · 62+ | Minnesota's state food program for green-card holders 50+ |
| Priority order | put six items in order with up/down buttons | The weights (section 3) |

Fifteen statuses are distinguished because the 2025–2026 federal changes split groups that used to be treated alike. For example, H.R. 1 (July 4, 2025) took SNAP away from refugees and asylees but kept it for Cuban/Haitian entrants and COFA citizens. A single "has papers" checkbox would get this wrong.

## 2. The six parts of the score

Each part is scored 0–100 for each state. A part can also be **Unknown**. Unknown is drawn hatched on the map and never counts as zero (section 4).

| Part | What it measures | Formula | Source |
|---|---|---|---|
| **Help you can use** (`access`) | Can this person get food help, health coverage and an ID here? | Rank-order-centroid mix of food, health and ID (61% / 28% / 11%; ID moves to the top when "No ID right now" is chosen). Each piece is 0–1 (below). | Federal rules by status (H.R. 1, PRWORA, KFF, NILC), plus state add-ons (KFF state health coverage, NILC state food programs, NCSL driver's licenses) |
| **Rent you can afford** (`affordability`) | How far a minimum-wage job is from a 2-bedroom at fair market rent | `ratio = housing wage ÷ state minimum wage`, mapped linearly from 1.5 (=100) to 5.0 (=0) | NLIHC *Out of Reach 2026*; U.S. DOL state minimum wage table (July 1, 2026) |
| **Shelter space** (`shelter`) | How many people without homes had to sleep outside | `unsheltered ÷ total`, mapped linearly from 5% (=100) to 65% (=0) | HUD 2025 Point-in-Time count (state totals add up to HUD's 745,652) |
| **Safety from immigration enforcement** (`safety`) | How much state law limits cooperation with immigration enforcement | `100 × (9 − tier) ÷ 8` on ILRC's 9-tier scale (tier 1 = most protective) | ILRC *State Map on Immigration Enforcement* |
| **Laws against sleeping outside** (`criminalization`) | Is there a statewide camping ban? | statewide ban in effect = 0, state forces cities to enforce local bans (GA, OK "Safe Neighborhood" laws) = 25, in court = 50, confirmed no statewide ban but some local bans (VA) = 75, not checked = Unknown | State statutes (FL HB 1365, TX HB 1925, TN, LA, IN, KY bans; GA, OK enforcement mandates), after *City of Grants Pass v. Johnson* (2024) |
| **What people here say** (`community`) | Ratings from people who have been there | Time-decayed Bayesian average (section 6) | Footing users |

**Safety only applies when it is relevant.** It is included for statuses at medium or high risk (asylum pending, TPS, DACA, parole, T/U/VAWA, visa, no papers, not sure) and for anyone in a mixed-status family. For a citizen, the part is simply not shown. It is not scored as 100, because a citizen should not see Oregon outrank Ohio for a reason that does not affect them.

### Help you can use: the pieces

`yes = 1.0`, `some/check = 0.5`, `no = 0`, read from `eligibility.json` for the person's status, then adjusted for the state:

- **Food** is the larger of federal SNAP and the state's own program for immigrants SNAP leaves out (CA CFAP, ME, WA FAP, IL, NM, MN 50+). Citizen children in a mixed family still count as 0.5. Green-card holders with kids get 0.75, because children qualify now and adults wait 5 years.
- **Health** for full-eligibility statuses is 1.0 in a Medicaid expansion state. In the 10 non-expansion states it is 0.75 with kids, pregnancy or disability and 0.35 otherwise. For other statuses it depends on whether the state covers children regardless of status (15 jurisdictions) and on the state's adult program (open = 1.0, limited = 0.6). The floor is 0.25, for ER care under EMTALA, community health centers and emergency Medicaid, which everyone can use.
- **ID** is 1.0 for lawful statuses and 0.75 for a pending asylum case. Otherwise it is 1.0 only in the 19 states plus DC that license people regardless of status, and 0 elsewhere.

## 3. How much each part counts

People are good at saying what matters *more*. They are bad at saying "safety is 37% and rent is 22%". So Footing asks for an **order** and turns it into weights with the **Rank-Order Centroid** (Barron & Barrett, 1996):

```
w_k = (1/n) · Σ_{i=k..n} 1/i
```

In simulation studies, ROC weights choose the same best option as the decision-maker's true (unknown) weights more often than other rank-based schemes do (Barron & Barrett 1996; Ahn & Park 2008). The weights for six items are:

| Position | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Weight | 40.8% | 24.2% | 15.8% | 10.3% | 6.1% | 2.8% |

With five items (no safety part) the weights are 45.7 / 25.7 / 15.7 / 9.0 / 4.0%. The live percentages are shown next to each item while the person reorders them, so the math is never hidden.

### Default order, before the person changes it

| Person | Default order | Why |
|---|---|---|
| Lawful, no mixed family | Help · Rent · Shelter · Camping laws · Ratings | Housing cost is the main driver of homelessness (CASPEH, UCSF 2023). Unmet health needs are near-universal among unhoused adults (73% in Baggett et al. 2010). |
| Medium risk or mixed family | Help · Rent · **Safety** · Shelter · Camping laws · Ratings | Enforcement fear is real but can be balanced against concrete help |
| High risk (no papers, not sure) | **Safety** · Help · Rent · Shelter · Camping laws · Ratings | 46% of likely-undocumented immigrants avoided assistance because of immigration fears (KFF/NYT survey, 2025). Help that is unsafe to ask for is not help. |
| "I need a place tonight" | **Shelter** first, then the above | Tonight beats next month |

Ratings start last because they are sparse at launch. Their weight rises if the person moves them up.

## 4. Combining the parts

```
Fit = Σ w_k · s_k  /  Σ w_k          (summed over KNOWN parts only)
```

If a part is Unknown, its weight is spread over the parts that are known. **Unknown is not zero.** A state is not punished because we have not yet checked its camping law. Instead, the uncertainty appears in the confidence:

```
Confidence = Σ w_k · freshness_k      (over known parts)
```

Freshness is 0.9 for policy data checked in 2026 (eligibility, wages and rents, enforcement tier), 0.7 for the January 2025 shelter count, 0.6 for the camping-law table, and between 0 and 1 for ratings, depending on how many recent ratings there are. The labels are high ≥ 0.70, medium ≥ 0.45, otherwise low. Michigan for a person who has not given a status is a good example: the biggest part (Help) is Unknown, so its confidence is **low**, and the screen says so.

### Worked example

Take Illinois, for a person with no papers, kids, and a mixed-status family, using the default order:

| Part | Weight | Score | Reason shown |
|---|---|---|---|
| Safety | 0.408 | 100 | ILRC tier 1 of 9 |
| Help you can use | 0.242 | 69.4 | SNAP for citizen children (0.5) · state covers children regardless of status (1.0) · license regardless of status (1.0) → 0.611·0.5 + 0.278·1 + 0.111·1 |
| Rent | 0.158 | 85.0 | $30.36/hr housing wage ÷ $15.00 minimum = 2.02 |
| Shelter | 0.103 | 84.6 | 14% of 14,576 slept outside |
| Camping laws | 0.061 | Unknown | not checked |
| Ratings | 0.028 | Unknown | none yet |

Fit = (40.8 + 16.8 + 13.4 + 8.7) ÷ 0.911 = **87.5**. Confidence is 0.80, which is high.

## 5. Ranks you can trust: the robustness check

A ranked order is not an exact preference, so the screen also tests how much the ranking depends on the precise weights. Footing re-ranks every state under 300 random weightings drawn from a Dirichlet distribution centered on the person's ROC weights (concentration κ = 30, so each weighting stays close to what the person said). This is the uncertainty analysis recommended for composite indicators by Saisana, Saltelli & Tarantola (2005) and the OECD/JRC *Handbook on Constructing Composite Indicators* (2008).

The state screen shows the 10th–90th percentile rank: "In 90% of reasonable weightings it ranks between #2 and #9", or "stays at #1". For a state with a wide range, its exact place is a judgement call, and the person can see that. The random draws use a seeded generator (mulberry32 plus Marsaglia–Tsang gamma sampling), so the same inputs always give the same ranges on any phone and in Python.

## 6. Community ratings

People who have been somewhere can rate it 1–5 on overall, *I felt safe*, *people treated me with respect* and *I could get help*, and tick fixed tags such as "shelter was full", "police moved people along" or "Spanish spoken". There is no free text, so no names and no doxxing.

```
score = (Σ d_i · stars_i + m · prior) / (Σ d_i + m),   d_i = 0.5^(age_i / 90 days),   prior = 3, m = 5
shown as 100 · (score − 1) / 4
```

- **Shrinkage.** One 5-star rating moves a place from 50 to 58, not to 100. A place needs about five ratings before its own data outweighs the neutral prior. This is the standard Bayesian-average defense against a single loud vote.
- **Decay.** A rating counts half as much after 90 days. Shelters fill up and police sweeps come and go, so old news fades.
- **Privacy.** A rating is snapped to a ~1 km tile, its time is rounded to the hour, and the device token is salted and hashed. The rating body is checked against a fixed list of keys. If anything else is sent, such as a status or household field, the server rejects the request with "never include profile data". This is tested in `tests/test_ratings_and_globe_api.py`, and the browser smoke test inspects every request.
- **Abuse limits.** One rating per device per tile per day, and at most 20 per device per day.

On the map, ratings appear as a heatmap (zoomed out) that turns into rated tiles (zoomed in). They also feed the *What people here say* part for that state.

## 7. What this score does not know

We list these so nobody mistakes the score for more than it is:

- **The camping-law table is incomplete.** States we have not confirmed are Unknown, not "no ban".
- **No job-market, weather or transit data at state level.** The town receipt (`/receipt`) has weather, transit and services for recorded towns. The state score does not.
- **State averages hide cities.** Rent in Chicago is not rent in Carbondale. Zoom into a recorded town for the local picture.
- **The law is moving.** The public charge rule (effective Sept 18, 2026), the vacatur of the PRWORA notices (*New York v. DOJ*, D.R.I., Sept 2026, which binds only the plaintiff states), and HUD's proposed mixed-status rule (Feb 2026, not final) can all change. Every program row links its source and date. The app always recommends a legal aid office before applying when a green card may be in the person's future.
- **Program reasons are in English only.** The interface is fully translated into Spanish, but the per-state "why" sentences come from the data files and are English for now.

## 8. The Virginia score

Sections 1–7 describe the 50-state score, which rates Virginia as one place. Footing now opens on
Virginia's **133 localities** — 95 counties and 38 independent cities — and scores each one separately.
State law still decides program access and immigration-enforcement risk; local data replaces the state
averages everywhere we have it. Engine: `footing/web/vafit.js` on the phone, with a line-for-line Python
twin in `footing/vafit.py`. `tests/test_vafit.py` runs both on the same inputs and requires identical
output, so neither can drift.

**In Virginia a city is not part of any county.** "Roanoke city" (FIPS 51770) and "Roanoke County" (51161)
are different places with different ordinances, different police forces and different rents. FIPS codes 510
and above are cities. Every source is matched by FIPS code, never by name.

### 8.1 The seven parts

| Part | What it measures | How it is scored | Source |
|---|---|---|---|
| **Shelter beds** (`shelter`) | Whether there is anywhere indoors, and how many had to sleep out | share of people counted outside, and beds per person, for the locality's Continuum of Care | HUD Point-in-Time and Housing Inventory Count, Jan 2025 |
| **Rent** (`rent`) | Hours of minimum-wage work for the rent of the size you need | hours a week for HUD's Fair Market Rent at $12.77/hr | HUD FMR FY2026 |
| **Help nearby** (`services`) | Whether there is anything to walk to | grocers taking EBT per 10k (0.3), mapped help places per 10k (0.2), how many places there are at all, on a log scale (0.2), fare-free buses (0.2), hot-meal EBT stores (0.1) | USDA SNAP retailers, OpenStreetMap, APTA/DRPT |
| **Local laws** (`laws`) | This city's or county's rules on sleeping outside | broad ban 0, limited ban 35, site closure 60; proposed, clearing policy and searched-and-nothing-found are shown but **not scored** | city code and council records, one at a time |
| **Immigration enforcement** (`safety`) | 287(g) agreements covering this place | task force model 10, jail model 40, none listed 80. Only included when the person's status is at risk | ICE 287(g) list |
| **Reported crime** (`crime`) | Violent crime reported to police | **off unless the person turns it on** — see 8.4 | FBI CDE 2025, plus city incident reports where published |
| **What people here say** (`community`) | Ratings from people who have been there | section 6, grouped by locality | Footing users |

Weights are the rank-order-centroid weights of section 3, over the person's priority order. **Unknown parts
drop out and the rest renormalise; nothing is ever scored 0 because we could not find it.**

### 8.2 Small places are pulled toward the state rate

A town of 2,000 with one grocery store is not a food paradise. Per-person counts are shrunk toward the
Virginia rate as if 25,000 more people lived there (`SHRINK_POP`), so one lucky shop in a tiny place cannot
outrank a city with twenty.

### 8.3 Confidence, and the point you tapped

Confidence is the sum of `weight × freshness` over the parts that are **known**, so a missing or stale part
visibly lowers it. Freshness is 0.95 for rent, 0.9 for enforcement, 0.7 for shelter and crime, 0.6 for
services and laws.

**Shelter is the weakest number in the whole score and the score says so.** HUD counts by Continuum of
Care, not by town. Virginia has 16, and the Balance of State CoC covers 71 localities with a single count.
Freshness drops to 0.5 there, 0.6 for a CoC covering 2–10 localities, and 0.7 where the count covers only
that place. Covington shares Roanoke's count, but the beds are about 50 miles away: the screen says the
beds may be in a neighbouring locality, and confidence falls.

When the score comes from a **tapped or typed point** (`fit_point`, `GET /api/va/fit`), the point's own
reliability multiplies that confidence — and never the score, because where you tap inside a county cannot
change that county's rent:

| Point | Effect |
|---|---|
| not a number, off the globe, outside Virginia, on open water | refused, no score, with a plain reason |
| latitude and longitude swapped | refused, and it suggests what you probably meant |
| rounded to one decimal place (about 11 km) | × 0.6 — the numbers may be a neighbouring locality's |
| within 1 km of the locality line | × 0.85 — in Virginia the neighbour is often a separate city with its own rules |

### 8.4 Why crime is off by default

Footing does not count reported crime unless the person asks for it, for four reasons:

1. Crime reports measure where police write reports as much as where danger is.
2. Using them pushes people away from poorer and Black neighbourhoods — the redlining pattern.
3. People without homes are far more often victims than offenders.
4. Virginia Beach's police department reported nothing for 2025, so the state's largest agency is missing.

Where a city publishes incident-level reports — **Norfolk and Charlottesville** — a point is scored on the
violent incidents in the 3×3 tiles around it (about 3 km across) over 12 months, against a scale whose
"bad" end is the 90th percentile of the recorded tiles. Everywhere else, and for any whole locality, it is
the FBI's yearly figure, and the reason says which one it used.

**Trespass, loitering, drunkenness and similar calls are counted and shown, and never scored as danger.**
They record where police make contact, which is disproportionately where unhoused people already are. The
tile at Charlottesville's downtown mall has more of those than violent incidents; scoring them as risk
would steer someone away from exactly the public places they are most likely to be.

### 8.5 What the Virginia score still does not know

- **121 of 133 localities' camping rules are Unknown**, and Unknown is never shown as "no ban". Six are
  confirmed; Montgomery County was searched with nothing found, which is recorded as its own answer.
- **Shelter is per Continuum of Care, not per town** (8.3). HUD does not publish bed locations.
- **Block-level crime exists for two cities only**, and the UI does not surface it yet.
- **Reasons are built in English.** The interface is translated into 8 languages and the one-line summaries
  are translated; the detailed "why" text inside *Details* is English, and is labelled as such.
- **All translations are machine translations**, and every screen says so.

## References

- Barron, F. H., & Barrett, B. E. (1996). Decision quality using ranked attribute weights. *Management Science*, 42(11), 1515–1523.
- Ahn, B. S., & Park, K. S. (2008). Comparing methods for multiattribute decision making with ordinal weights. *Computers & Operations Research*, 35(5), 1660–1670.
- Saisana, M., Saltelli, A., & Tarantola, S. (2005). Uncertainty and sensitivity analysis techniques as tools for the quality assessment of composite indicators. *J. Royal Statistical Society A*, 168(2), 307–323.
- OECD & JRC (2008). *Handbook on Constructing Composite Indicators: Methodology and User Guide*.
- Marsaglia, G., & Tsang, W. W. (2000). A simple method for generating gamma variables. *ACM Trans. Math. Software*, 26(3), 363–372.
- Kushel, M., et al. (2023). *Toward a New Understanding: The California Statewide Study of People Experiencing Homelessness*. UCSF Benioff Homelessness and Housing Initiative.
- Baggett, T. P., O'Connell, J. J., Singer, D. E., & Rigotti, N. A. (2010). The unmet health care needs of homeless adults: a national study. *American Journal of Public Health*, 100(7), 1326–1333.
- KFF / New York Times (2025). Survey of Immigrants. Data and policy sources for every state field are in `footing/static/state_policy.json` and `footing/static/eligibility.json`, with URLs and the dates they were read.
