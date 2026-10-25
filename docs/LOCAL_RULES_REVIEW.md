# Local camping and sleeping rules: bounded review

Retrieved **2026-10-25**. This rule-only review covers Bristol, the twelve S5.2 item 8 localities, and the user's ten-locality random sample. The [research ledger](../data_raw/local_rules_research.json) preserves previous saved rows/sources, exact URLs, section locators, retrieval outcomes, coverage and next actions. It is a curated research ledger, not a verbatim publisher capture.

This pass found **nine defensible scoped rules**: one replacement (Fairfax County) and eight new rows. They use the existing `limited_ban` status and score 35. Thirteen localities retain a null rule (Unknown). Bristol retains its pre-existing provisional `broad_ban`/0 with a corrected primary citation and an explicit unresolved scope note. **Bristol is not fully settled.** No failed search, unavailable code, zoning rule or municipal summary was converted into a finding of no ban.

## Evidence and classification boundary

Research followed AGENTS.md, the current HANDOFF.md section, docs/DATA_WORK.md, data_raw/README.md, saved LOCAL_RULES and docs/FACT_CHECK.md. No other field was refreshed. Each ledger entry preserves the previous saved rule.

The nine decisions use the municipality's published **operative park/facility rule text**, including authority regulations and departmental regulations. They are not all codified criminal ordinances: exact rule headings/numbers are recorded without inventing code sections or penalties. A verified park restriction fits the existing named-area `limited_ban` definition. It establishes the stated restriction only; **broader restrictions may still exist**. These rows do not establish permission outside the reviewed property.

Existing scores remain `broad_ban=0`, `limited_ban=35`, `site_closure=60`. Proposed rules, clearing policies and checked-none-found searches remain unscored. The existing Montgomery County checked-none-found row remains uncited and unscored; search sources can be recorded separately in the ledger.

County findings do not import independent-city or incorporated-town laws. Federal/state parks, NOVA Parks and other owners require separate checks. Fairfax County 51059 and Fairfax city 51600 have separate sources and rows. Richmond is independent city 51760, not Richmond County.

## Bristol: resolved history, unresolved current scope

The [2022 council packet](https://d3n9y02raazwpg.cloudfront.net/bristolva/97b1562e-f625-11ec-baa3-0050569183fa-9a2ee4f8-c7d7-4526-ad5b-591383a5deed-1658767296.pdf), Ordinance 22-9, printed p.29, supplies original §74-8: both prohibition and camping definition enumerate city streets, sidewalks, alleys and other public rights-of-way. The **limited** interpretation was better supported for that version than an all-city-land claim. It also contained a motor-vehicle sleeping exception.

The [August 27, 2024 packet](https://d3n9y02raazwpg.cloudfront.net/bristolva/1aedca2c-9eab-11ee-a93d-0050569183fa-f5eb21b6-13a7-4f7f-a766-a9c62b975c0d-1724431285.pdf), Ordinance 24-13 amending §74-8, printed pp.82–83 (PDF indexes 81–82), adds city-owned property to the definition and exceptions and marks deletion of the motor-vehicle exception. But the operative prohibition still enumerates streets, sidewalks, alleys and rights-of-way. Broadening a definition does not unambiguously broaden that separate prohibition.

The [August 27 minutes in the September 10 packet](https://d3n9y02raazwpg.cloudfront.net/bristolva/c0146623-9eaa-11ee-a93d-0050569183fa-f5eb21b6-13a7-4f7f-a766-a9c62b975c0d-1725633176.pdf), printed pp.53–54, item F.1, record staff's explanation of expansion to public property, a failed postponement (2–3), and adoption (3–2). This proves adoption and legislative intent, not reconciliation of the conflicting sentences. The draft's blank adoption fields and printed 9-12-24 history line are not adoption evidence. The penalty redline extracts as “class 41”; screenshot fetches failed, so this review does not assert a final penalty.

[Current compiled code](https://library.municode.com/va/bristol/codes/code_of_ordinances) returned HTTP 403/inaccessible routes. Normal-process publisher API access returned 403. Browser fallbacks timed out. Exact failed routes are recorded in the ledger. The builder preserves the **existing conservative broad score provisionally**, removes the stale 2022 penalty claim, cites the primary amendment packet and explicitly states that scope is unverified. This is a retained disputed row, not a verified broad ban.

Next: obtain current/clerk-certified §74-8 and final signed Ordinance 24-13 and reconcile the operative clause and definition. Do not downgrade solely from 2022 text or claim parks are safe.

## Priority batch

All retrievals: 2026-10-25. “Unknown” means no new scored row, not no restriction.

| Locality / FIPS | Result and exact provision | Coverage and remaining gap |
| --- | --- | --- |
| Bristol city 51520 | Provisional broad/0; Ordinances 22-9 and 24-13, §74-8; see above. | Current compiled scope unresolved. |
| Fairfax County 51059 | Limited/35 replaces clearing policy. [FCPA Regulations Appendix 6 §1.03(A)](https://www.fairfaxcounty.gov/parks/sites/parks/files/Assets/documents/administrative/policy-appendix-regulations.pdf): overnight lodging/camping sites only in posted camping areas; register/pay. | FCPA land only. Full 26 MB manual parser failed; separate appendix and current [camping rules](https://www.fairfaxcounty.gov/parks/rules/camping) readable. Not Fairfax city, NOVA Parks or all county land. |
| Virginia Beach city 51810 | Unknown. [Publisher index §§23-54–23-56](https://library.municode.com/va/virginia_beach/codes/code_of_ordinances?nodeId=CO_CH23OF); current operative text inaccessible. | Clerk-hosted PIN Ministry slides quote sleeping rules but are a submitted advocacy presentation, not independent code verification. Read sections, beach rules, exceptions and uncodified changes. |
| Prince William County 51153 | Unknown. [County article, principle 5](https://www.pwcva.gov/news/leaving-no-trace-our-parks) says no camping in county parks; formal regulation not retrieved. §13-320.1 addresses RV/trailer parking. | Municipal summary is a lead, not verified operative text. Excludes Manassas/Manassas Park, towns and federal/state parks. |
| Loudoun County 51107 | Limited/35. [PRCS Policy 3-3 §4.12](https://www.loudoun.gov/DocumentCenter/View/115605), PDF p.120: overnight camping requests require permits. | PRCS park facilities only. §1092.04 concerns closed-park entry. Policy effective 2002, revised 2004; retrieval is not a new enactment date. Town parks/other land unverified. |
| Chesterfield County 51041 | Unknown. [County page](https://www.chesterfield.gov/163/Parks-and-Facilities) cites §§20-4(a), 20-9(c)/(e): hours, overnight parking, towing. Code link failed. | These do not establish a camping-specific prohibition. Read current Chapter 20 and offenses. |
| Henrico County 51087 | Limited/35. [RP0001 item 11](https://henrico.gov/assets/RP-Policy-General-Rules-and-Regulations.pdf), PDF p.3: prior written director approval to camp. | Public recreational property only. Effective 2023-10-01, revised 2024-09-17. Old §14-46 PDF returned 404; current code shell empty. No criminal penalty inferred. |
| Norfolk city 51710 | Unknown. Outdoor code inaccessible. [Library conduct item 4](https://norfolk.gov/6090/Policies) bans sleeping indoors. | Indoor library policy and RV parking definitions do not establish an outdoor camping law. Nebraska/UK results excluded. |
| Chesapeake city 51550 | Limited/35. [Northwest River Park rules, Campsites and Cabins](https://www.cityofchesapeake.net/3015/Campground-Rules-and-Regulations): no long-term camping, 14 nights/30 days, no sleeping without tent/hammock or in non-camping vehicle. | Campground only. General city public-space code unverified; no citywide/all-parks claim. |
| Arlington County 51013 | Limited/35. [Park/Facilities Use Rules item 2](https://www.arlingtonva.us/Government/Departments/Parks-Recreation/About/Arlington-County-Park-Rules-Regulations): permit and designated place required. | County park facilities only, not federal parks/all public land. No enactment date or penalty invented. |
| Richmond city 51760 | Unknown pending code. [City Good Neighbor guide, §8-273](https://www.rva.gov/sites/default/files/2021-08/Richmond%27s%20Guide%20to%20Being%20a%20Good%20Neighbor%20-%20RVA.gov_.pdf) describes camping/tenting/bench restrictions. | Direct code and historical council attachment fetches failed. Strong municipal-summary lead, not completed operative-code verification. |
| Newport News city 51700 | Limited/35. [Park Rules item 16](https://nnparksandrec.org/parks-rules-ordinances/): camping only in Newport News Park Campground. | Department park/watershed property; some holdings extend into York County. No import of York County laws or all-public-land ban. |
| Alexandria city 51510 | Limited/35. [Fort Ward, Prohibited Activities—Camping](https://www.alexandriava.gov/parks/location/fort-ward-park-historic-site): overnight temporary-shelter camping restricted; conditional large-group exception. | Fort Ward only. §6-1-8 and any nighttime street/square rule remain unverified; third-party summaries not substituted. |

## Random sample: local rules only

The user supplied the sample from `random.Random(20261025).sample(sorted(localities), 10)`. Other fields belong to the user's parallel fact-check.

| Locality / FIPS | Primary check and result | Remaining action |
| --- | --- | --- |
| Galax city 51640 | Unknown. [Code index](https://ecode360.com/GA1297), through 2026-08-10; Chapters 107, 127, 89 and §§143-1–143-3 examined/searched. Selected camping/sleeping searches found no match. Trespass after notice is not a specific camping ban/site closure. | Remaining code, park rules and amendments; selected-chapter searches do not prove absence. |
| Buena Vista city 51530 | Unknown. [City code](https://library.municode.com/va/buena_vista/codes/code_of_ordinances) and municipal parks page: 403. | Current code and Glen Maury/public-property rules. Exclude Colorado results. |
| Mecklenburg County 51117 | Unknown. [Zoning §7.1-5(G), pp.115–116](https://www.mecklenburgva.com/DocumentCenter/View/1107/Zoning-Ordinance-Effective-July-1-2026): campground residency/180-day limit. | Facility land use does not establish public-space camping law. Separate towns/federal/state property. Not North Carolina. |
| Lancaster County 51103 | Unknown. [County code index](https://www.lancova.com/page2.asp?pageID=30); indexed Land Development Code §§19-1-3, 19-2-1–19-2-7 regulates recreational-equipment habitation. Direct page empty. | Public-space rules and amendments. RV zoning does not establish camping law. Not Pennsylvania. |
| Lynchburg city 51680 | Limited/35. [General Park Rules item 9](https://www.lynchburgparksandrec.com/wp-content/uploads/2021/07/2021_07_Park_Rules.pdf): camping only in designated areas. | City parks only. General code returned 403. File path 2021/07 is not a 2026 enactment date. |
| Charles City County 51036 | Unknown. [Lawrence Lewis Jr. Park](https://www.charlescityva.us/facilities/facility/details/Lawrence-Lewis-Jr-Park-5) and [rental policy Section 1, p.6](https://charlescityva.us/DocumentCenter/View/4877/Charles-City-County---Parks-and-Recreation-Rental-Application---3-20---complete---fillable): registered one-night primitive camping. Code click failed. | A rental option/condition does not establish a general ordinance or absence. Virginia, not Iowa. |
| Fairfax city 51600 | Limited/35. [Parks Rules §1.02(10)](https://www.fairfaxva.gov/files/assets/city/v/1/parks-amp-rec/documents/2018-park-rules-ordinance-adopted-10918.pdf): advance written city permission to camp. | Independent city's park property only. [City code portal](https://www.fairfaxva.gov/Government/City-Codes) warns codification is annual; review uncodified changes/broader property. |
| Wythe County 51197 | Unknown. [Code portal](https://www.wytheco.org/484/Codes-Ordinances); indexed §22-40 concerns campground development permits; direct fetch failed. Rural Retreat Lake rules concern that campground. | Current code/uncodified archives. Do not import Town of Wytheville Crystal Springs rules or state/federal campground rules. |
| Goochland County 51075 | Unknown. [Publisher](https://library.municode.com/va/goochland_county/code_of_ordinances): 403; [parks department](https://www.goochlandva.us/236/Parks-Recreation) lists hours only. | Public-space/park code and uncodified enactments. No score from hours/failed searches. |
| Giles County 51071 | Unknown. [Current zoning, effective 2026-08-24](https://virginiasmtnplayground.com/wp-content/uploads/2026/08/Official-Zoning-Ordinance-CURRENT-8-24-2026.pdf), §302.141-1 and §§602.02-22, 602.04-3, 603.03-3: private seasonal camps, stored RV occupancy and campground development. | Not a general public camping ordinance. Earlier indexed §302.140-1 is outdated. Review county public-space rules and towns separately. |

## Implementation and integration

The builder reads explicit non-null decisions from the ledger into `LOCAL_RULES` and their citations into `SOURCES`. It requires readable primary operative text, an allowed evidence kind, matching scope/status, name/FIPS agreement, section/coverage, retrieval date and a distinct source ID. Blank decisions do not create rows. Generic validation rejects invented statuses and scores inconsistent with status. Legacy sources remain available.

Owned files: builder, ledger, this review and new `tests/test_local_rules_research.py`. The committed `footing/static/va_localities.json` is not overwritten in this shared-workspace batch. The integration owner must regenerate it after review; fresh-build equality checks will detect this pending change. No engine/UI changes or browser smoke run are part of this batch.

Validation results are recorded in the stop checkpoint below.

## Stop checkpoint for Claude / main agent

Stopped at user request on 2026-10-25. No new research, commits or pushes. HANDOFF.md and docs/FACT_CHECK.md were not edited. Engine/UI files and other agents' changes were not edited.

- Completed: `.venv/Scripts/python.exe -m pytest -q tests/test_local_rules_research.py` — **20 passed in 8.13s**.
- Completed: `.venv/Scripts/python.exe scripts/build_va_localities.py --check` — **exit 1**, committed locality JSON differs from the fresh build. Generated JSON is outside this batch's owned files and remains pending integration; no publisher-total validation errors were reported.
- Full `.venv/Scripts/python.exe -m pytest -q` was started but still had no output at stop time. Interrupted its session 13684 with Ctrl-C; tool reported exit 1. **No completed full-suite result.**
- Scoped `git diff --check` was started but still had no output. Interrupted session 73386 with Ctrl-C; exit 1, **no completed whitespace-check result**. No remaining running unified exec session from this batch is known.
- No UI smoke checks were run; no UI or engine files were changed by this batch.

Saved files: `scripts/build_va_localities.py`, `data_raw/local_rules_research.json`, `docs/LOCAL_RULES_REVIEW.md`, `tests/test_local_rules_research.py`. The ledger covers all 23 requested localities: nine scoped rules, thirteen null/Unknown decisions, one disputed Bristol scope. Bristol's pre-existing broad/0 is retained provisionally, with primary evidence and explicit uncertainty; **the requested current-code resolution remains incomplete**.

Next for integration: review the nine park/facility classifications and Bristol note; regenerate `footing/static/va_localities.json` under the main agent's ownership; reconcile any existing Fairfax County score assertion with the approved classification; run the full suite and builder `--check`. Resume legal gaps from each ledger entry's exact URLs/next_action rather than rediscovering sources. This checkpoint does not authorize a commit/push by this worker.
