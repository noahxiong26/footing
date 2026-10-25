# Settle Score factor catalog

These are the parameters behind the **Settle Receipt** for a single point (`/api/receipt`), not the Fit
Score. Two different scores:

- **Fit Score** — compares places, on the phone, from pre-built data. 50 states in `footing/fit.py`,
  Virginia's 133 localities in `footing/vafit.py`. Method: `docs/RATING_FORMULA.md`.
- **Settle Score** — scores one point in depth by calling live sources for it. That is this table.

Session 4's handoff listed this file as "still describes the 50-state version". It does not: the receipt has
always been point-based, so there is nothing state-specific to rewrite here. Live-source coverage is the
same in Virginia as anywhere else.

| Category (weight) | Parameter | Weight | Sources | Refresh | Scoring rule | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Shelter and safe sleep (18) | Shelters within 3 km | 3 | osm, google_places | daily | count, k=1 (1 shelter -> 63, 3 -> 95); zero trusted only if Google Places answered | built |
| Shelter and safe sleep (18) | Day centers within 5 km | 1 | osm, google_places | daily | count, k=1; zero trusted only if Google Places answered | built |
| Shelter and safe sleep (18) | Shelter beds per unsheltered person (CoC) | 2 | static_tables | annual | HUD HIC beds / PIT unsheltered for the county's CoC: 1.0+ -> 100, 0.2 -> 0 | built |
| Food and EBT (16) | SNAP stores within 1 km | 2 | snap | weekly | count, k=2 (USDA list is complete, so zero is real) | built |
| Food and EBT (16) | Full grocery stores taking SNAP within 2 km | 2 | snap | weekly | count of Super Store/Supermarket/Large or Medium Grocery, k=1 | built |
| Food and EBT (16) | Food banks and meal sites within 3 km | 2 | osm, google_places | daily | count, k=1.5; zero trusted only if Google Places answered | built |
| Food and EBT (16) | Restaurant Meals Program places within 3 km | 0.5 | snap | weekly | bonus only: counts when present, k=1; a zero is Unknown because only some states run the program | built |
| Cost to stay (14) | Local survival basket vs USDA Thrifty Food Plan | 3 | kroger, static_tables | live | basket/TFP week: 0.85 or less -> 100, 1.3 -> 0 | built |
| Cost to stay (14) | Regular gas vs U.S. average | 2 | eia | weekly | local/U.S.: 0.9 -> 100, 1.15 -> 0 | built |
| Cost to stay (14) | Studio Fair Market Rent as share of full-time minimum-wage pay | 3 | hud_fmr, static_tables | annual | rent / (min wage x 173.3 h): 30% -> 100, 100% -> 0 | built |
| Cost to stay (14) | Median gross rent as share of full-time minimum-wage pay | 1 | census_acs, static_tables | annual | same rule, ACS median rent as a reality check on FMR | built |
| Income and work (10) | County unemployment rate | 3 | bls_laus | monthly | 3% -> 100, 10% -> 0 | built |
| Income and work (10) | State minimum wage | 2 | static_tables | annual | $15 -> 100, $7.25 federal floor -> 0 | built |
| Income and work (10) | Employment agencies within 5 km | 2 | osm | daily | count, k=1 | built |
| Getting around (12) | Transit stops within 1 km | 3 | transitland | live | count, k=3 | built |
| Getting around (12) | Median walk to nearest store, pharmacy, library, clinic, post office | 3 | snap, osm | daily | straight line x 1.3 at 80 m/min: 10 min -> 100, 45 min -> 0; needs 3 of 5 | built |
| Health (8) | Clinics and health centers within 5 km | 2 | osm, hrsa | daily | count, k=1 | built |
| Health (8) | Pharmacies within 3 km | 1 | osm | daily | count, k=1 | built |
| Health (8) | Mental health and substance-use treatment | 1 | — | static | planned | planned |
| Hygiene and connection (8) | Public restrooms and drinking water within 2 km | 2 | osm | daily | count, k=3 | built |
| Hygiene and connection (8) | Public showers within 5 km | 2 | osm | daily | count, k=1; OSM rarely maps showers, so zero is Unknown | built |
| Hygiene and connection (8) | Laundromats within 5 km | 1 | osm | daily | count, k=1 | built |
| Hygiene and connection (8) | Public libraries (Wi-Fi, charging) within 3 km | 2 | osm | daily | count, k=1 | built |
| Kids and school (4) | Public schools within 5 km | 2 | urban_ed | annual | count, k=2 (NCES 2022-23) | built |
| Kids and school (4) | Grade levels covered within 5 km (primary, middle, high) | 1 | urban_ed | annual | 3 levels -> 100, 0 -> 0 | built |
| Weather risk (6) | Worst active NWS alert | 3 | nws | live | none -> 100, minor -> 75, moderate -> 50, severe -> 15, extreme -> 0 | built |
| Weather risk (6) | Cold-night load, next 7 nights | 2 | open_meteo | live | freezing nights + 0.35 x nights at 33-40 °F: 0 -> 100, 5 -> 0 | built |
| Weather risk (6) | Days at 95 °F or hotter, next 7 days | 1 | open_meteo | live | 0 -> 100, 4 -> 0 | built |
| Weather risk (6) | Air quality (AQI) | 1 | — | live | planned | planned |
| Paperwork and local rules (4) | USPS post offices within 5 km (General Delivery mail) | 2 | osm | daily | count, k=1; private couriers tagged as post offices are excluded | built |
| Paperwork and local rules (4) | Camping and sleeping-in-vehicle rules | 2 | static_tables | static | curated per county: ban -> 20, no ban found -> 80; empty -> Unknown | built |
| Paperwork and local rules (4) | ID and vital-records offices | 1 | — | static | planned | planned |
| Paperwork and local rules (4) | Civil legal aid offices | 1 | — | static | planned | planned |
