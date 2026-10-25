# Second check of the policy data (2026-10-24, evening)

The 2nd session left this unfinished ("treat the data as checked by one person only"). This pass re-read
the primary or near-primary sources below and compared them with `footing/static/eligibility.json` and
`scripts/build_state_policy.py`. **Honest caveat:** it was done by another Claude session, not a person
or a different model family, so it is a second pass, not a fully independent review. A human with legal-aid
experience should still read the `eligibility.json` notes before real-world use.

## What changed

| Item | Before | After | Why |
|---|---|---|---|
| Georgia, Oklahoma camping law | `in_effect` (scored 0, same as a statewide ban) | `enforcement_mandate` (scored 25) | Stateline (June 25, 2026) describes both as "Safe Neighborhood" laws that let owners seek compensation when localities don't enforce camping laws. That pressures local enforcement; it is not a statewide ban. The method doc said "in effect = statewide ban", so the old value broke the project's own rule. |
| Marketplace (ACA) notes for asylum pending and parole | only mentioned the Jan 1, 2026 cut for people under 100% of poverty | also says all tax credits end Jan 1, 2027 (H.R. 1) | The note was true but incomplete; the 2027 cut applies to these statuses too. A test now checks it. |

## What was re-checked and matched (no change)

| Claim in the data | Source read | Result |
|---|---|---|
| HUD PIT total for Jan 2025 = 745,652 | NLIHC summary of the 2025 AHAR Part 1 (HUD release May 29, 2026) | matches (−3.4% vs 2024) |
| Public charge rule effective Sept 18, 2026; weighs non-cash benefits | Visaserve / CILaw Group summaries of the DHS rule; 22 states + DC sued Sept 14, 2026 | matches; no injunction reported as of those articles |
| PRWORA notices (HUD, DOJ, HHS, DOL, ED) set aside Sept 21, 2026, *New York v. DOJ* | NLIHC memo; NY AG decision PDF | matches; relief binds the agencies as to the plaintiff states (the method doc already says this) |
| HUD mixed-status proposed rule, Feb 2026, not final | NLIHC, NAHRO, CBPP | matches |
| H.R. 1 Medicaid restriction from Oct 1, 2026, but states may still cover lawfully residing children and pregnant people | Health Affairs Forefront ("H.R. 1 does not block states..."), Georgetown CCF (Sept 30, 2026), KFF | matches the "some states still cover children and pregnant people" wording |
| 19 states + DC issue licenses regardless of status | Newsweek map (Aug 18, 2025) listing CA, CO, CT, DE, HI, IL, MD, MA, MN, NV, NJ, NM, NY, OR, RI, UT, VT, VA, WA + DC | matches `drivers_license_all` exactly; no repeals found |
| ILRC tiers (Sept 6, 2026 map) | ilrc.org/state-law-map | spot-checked IL 1, OR 1, CA 2, ME 2, VA 3, KY 5, NH 6, AL 8, TX 9, FL 9: all match |
| NLIHC Out of Reach 2026 | 2026-OOR-VA.pdf | VA $33.37/hr, $12.77 minimum wage, 105 hours: matches |
| Louisiana and Indiana 2026 camping laws | Stateline (June 25, 2026) | match |

## Not re-checked (still single-checked)

- Every remaining ILRC tier, every OOR row and every minimum wage (only spot checks above).
- Kentucky "contested" status (relies on NHLC's report of a court ruling).
- The status-by-program grid for `hud_housing`, `work` and `public_charge` beyond the items above.

## Sources

- Stateline, "2 years after Grants Pass, 14 states, 350 cities have tougher laws on street homelessness" (2026-06-25): https://stateline.org/2026/06/25/2-years-after-grants-pass-14-states-350-cities-have-tougher-laws-on-street-homelessness/
- NLIHC, 2025 AHAR summary: https://nlihc.org/resource/hud-2025-annual-homelessness-assessment-report-finds-first-reduction-overall-homelessness
- NLIHC, PRWORA notices vacated: https://nlihc.org/resource/court-vacates-prwora-notices-hud-and-other-federal-agencies
- Visaserve, public charge rule takes effect: https://visaserve.com/new-public-charge-rule-takes-effect-today-as-22-states-sue-to-block-it/
- NLIHC, HUD mixed-status proposed rule: https://nlihc.org/resource/hud-publishes-proposed-mixed-status-rule
- Health Affairs Forefront: https://www.healthaffairs.org/content/forefront/hr-1-does-not-block-states-offering-medicaid-and-chip-lawfully-residing-children-and
- Georgetown CCF (2026-09-30): https://ccf.georgetown.edu/2026/09/30/new-policies-pose-risks-to-health-of-lawfully-present-immigrant-families-and-children-including-u-s-citizen-children/
- Newsweek license map: https://newsweek.com/map-shows-states-immigration-driving-licenses-2115122
- ILRC state map: https://www.ilrc.org/state-law-map
- NLIHC Out of Reach 2026, Virginia: https://nlihc.org/sites/default/files/oor/2026-OOR-VA.pdf

---

# Virginia locality data: what the merge cross-checked (2026-10-25)

Sessions 3 and 4 both built a Virginia locality dataset, independently, from their own captures of the same
publishers. Neither had been checked against anything. Merging them made each one a check on the other,
which is the only real review either has had. **This is still two Claude sessions, not a person**: the open
items below need someone who can open the publishers' sites.

## Agreed, independently, with no changes needed

| Field | Result |
|---|---|
| HUD Fair Market Rents FY2026, studio to 4 bedrooms | identical for all **133** localities |
| HUD Continuum of Care mapping (which CoC each locality is in) | identical for all **133** |
| FBI CDE offence counts, per agency | identical for all **240** agencies both captures hold |

## Found and fixed by the comparison

| Item | Was | Now | Why |
|---|---|---|---|
| **Farmville PD** (and St. Paul, Saltville, Kilmarnock) | Session 4's builder took the first county the FBI lists, so Farmville's 37 violent and 153 property offences landed in **Cumberland County** (population 9,664), quintupling its violent count | placed by the agency's own published coordinates, which fall in **Prince Edward County**, where the town is seated | The FBI lists `CUMBERLAND, PRINCE EDWARD` for agencies that straddle a line. Splitting the counts would invent a division the data does not contain. All four such agencies resolve to the county the town is seated in. |
| **Months reported** for Middleburg, Remington and Quantico PD | session 4's capture said 12 of 12 for all three | 11, 3 and 0, from the second capture, and each is flagged as a coverage gap | Session 4's capture records only 12 or 0 and nothing between, so it appears to have inferred "reported at all" rather than reading the monthly breakdown. Taking the lower value flags a partial year instead of counting it as a full one. |
| **Virginia Beach** crime counts | stored as `0` with a null rate | stored as `null` with the reason | Virginia Beach PD reported nothing for 2025. A stored `0` reads as a crime-free city of 450,000. |
| **Montgomery County** camping rule | absent, which the engine shows as "not checked yet" | `checked_none_found`, shown and still not scored | A search that found no ordinance is weaker than "no ban" and stronger than "not checked". The codes were not read line by line, so it is not a confirmed "no ban". |

After these fixes the two captures agree on **violent and property counts for all 133 localities**.

## Open: needs someone who can reach the sources

1. **Bristol's camping ordinance.** The two sessions read the same summary and classified it differently:
   session 4 as a broad ban (scored 0), session 3 as a partial ban (scored 35), on the grounds that parks
   and other city land are not "public rights of way". Neither read the ordinance; both cited news coverage.
   **Kept at 0**, because the two errors do not cost the same: scoring Bristol harsher than it is costs
   someone an option, scoring it gentler sends them somewhere they can be charged. Read Bristol City Code
   and set it properly.
2. **The three months-reported disagreements.** Open CDE for ORI `VA0530200` (Middleburg), `VA0300100`
   (Remington) and `VA0750400` (Quantico) and record the real figures. Effect today is 5 property offences
   in Loudoun County, so this is tidiness, not a correctness risk.
3. **The other 127 localities' camping rules** are still Unknown, and Unknown is never shown as "no ban".
   Six are confirmed (Hampton, Bristol, Roanoke, Charlottesville, Danville, Fairfax County) plus Montgomery
   as searched-and-nothing-found.
4. **Ten random localities end to end.** Still the right next check: FMR, PIT, HIC, SNAP counts, 287(g) and
   the local rule, read off the publishers' own pages. Nobody has done this.
5. **The block-level incident data** (Norfolk, Charlottesville) exists in one capture only, so it has no
   second opinion. `data_raw/city_incidents_MANIFEST.json` records the capture method and its own internal
   checks (tile totals equal the placed counts, which the builder re-verifies on every build).

