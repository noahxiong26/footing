# data_raw — what was captured, from where, and how

These files are the raw inputs for `scripts/build_va_localities.py` (which writes `footing/static/va_localities.json`)
and for `footing/web/data/va-localities.json` (the Virginia map shapes). Captured on **2026-10-24 (ET)** by Claude
(session 4), through a real Chrome browser, because the build sandbox can only reach GitHub and package registries.
Each file is exactly what the source returned, filtered to Virginia; nothing was typed in by hand.

How the capture worked: a script ran inside a browser tab on the source's own site (so the request is the same
one a person's browser makes), wrote the result into the page, and the page text was copied out unchanged.
`/home/claude/tools/grab.py` (not in the repo) pulled each payload out of the session transcript by its marker.

| File | Source | Request | Notes |
| --- | --- | --- | --- |
| `hud_fmr_fy2026_va.json` | HUD FY2026 FMR Documentation System | `…/FY2026_code/2026summary.odn?year=2026&fmrtype=Final&selection_type=county&fips=<5-digit>99999` for all 133 localities | DC and Hampton Roads metros use Small Area FMRs for vouchers; the metro-wide FMR is read from the page HUD links "for other programs". Southampton County and Franklin city: page lists FY2026 values directly. |
| `hud_pit_2024_2025_va_coc.json` | HUD `2007-2025-PIT-Counts-by-CoC.xlsb` | parsed in the browser with SheetJS 0.18.5, sheets 2025 and 2024, rows `VA-*` | 2025 Virginia CoC totals sum to 7,240 people / 1,349 unsheltered = HUD's state total. VA-501/505/507 did sheltered-only counts in 2025. |
| `hud_hic_2025_va_coc.json` | HUD `2007-2025-HIC-Counts-by-CoC.xlsx` | sheet 2025, rows `VA-*` | Year-round, family, adult-only, seasonal and overflow beds. |
| `hud_coc_by_locality.json` | HUD eGIS `Continuum_of_Care_Grantee_Areas` | point-in-polygon query at a point inside each locality (`va_interior_points.json`) | Middlesex, York and Poquoson were re-queried at a land point (the first point was on water). |
| `census_pep_v2025_va.json` | Census `co-est2025-alldata.csv` | rows STATE=51 | `[name, POPESTIMATE2025, POPESTIMATE2024]`. |
| `osm_va_services_2026-10-25.json` | Overpass API, statewide | amenities/social facilities/laundry/job offices inside `ISO3166-2=US-VA` | Classified with the same rules as `classify_osm` in `footing/sources/open_sources.py`; counted per locality with the us-atlas county shapes. OSM base timestamp 2026-10-25T00:21Z. `pts` = shelters, food banks, meal sites, day centers and free/community clinics only. |
| `usda_snap_retailers_va_by_county.json` | USDA FNS SNAP retailer feature service | `where State='VA'`, count grouped by County and Store_Type | Layer last edited 2026-10-21. |
| `fbi_cde_va_agencies_2025.json` | FBI Crime Data Explorer | `/LATEST/agency/byStateAbbr/VA`, then `/LATEST/summarized/agency/{ORI}/{violent-crime,property-crime}?from=01-2025&to=12-2025` for all 412 agencies | Virginia Beach PD reported 0 months for 2025. |
| `ice_287g_va_2026-10-24.json` | ICE 287(g) "Participating Agencies" spreadsheet | `ice.gov/file-download/download/public/209716`, rows STATE=VIRGINIA | 22 agreements; "Hopewell County Sheriff" is Hopewell city's sheriff. |
| `va_interior_points.json` | computed here | a point inside each locality (centroid, or the nearest grid point inside) | Used only for the CoC lookup. |

The Virginia shapes (`footing/web/data/va-localities.json`) are Census TIGERweb `State_County/MapServer/1`
(`where STATE='51'`, `maxAllowableOffset=0.0009`, `geometryPrecision=5`), turned into TopoJSON in the browser with
`topojson-server@3.0.1` at quantization 4e4. Borders are accurate to roughly 100 m. TIGER county shapes include
water, so `footing/va.py` also checks the us-atlas shoreline to tell open water from land.

To refresh: repeat the requests above (any normal laptop can reach these hosts directly), replace the files,
run `python scripts/build_va_localities.py`, then `pytest -q`.
