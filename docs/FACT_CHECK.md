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
