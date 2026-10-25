# Finding data without repeating collection

The session 4 report identifies source collection as most of that session's work: 133 HUD county
pages, FBI requests for 412 agencies, and browser transfer limits. It does not contain token telemetry,
so this is evidence of expensive collection, not a measured share of account usage.

For implementation, use the saved data. A refresh is a separate task with a named source, field,
geography and reason. Replay mode lets the app and its tests run without publisher requests.

## Quick lookup

```sh
python scripts/data_lookup.py --list
python scripts/data_lookup.py 51710 --field crime
python scripts/data_lookup.py 51121 --field fmr
python scripts/data_lookup.py 51540 --field local_rule
```

The lookup prints the committed value, its recorded source metadata and, for crime, the city's
incident coverage if available. It makes no network requests and does not assert the value is current.
Use `data_raw/README.md` for exact capture requests and `docs/FACT_CHECK.md` for verification gaps.

| Need | Start here | Saved capture / implementation |
| --- | --- | --- |
| Rent | `fmr` | `data_raw/hud_fmr_fy2026_va.json` |
| Shelter counts and service area | `coc` | `data_raw/hud_{pit_2024_2025_va_coc,hic_2025_va_coc,coc_by_locality}.json` |
| Population | `pop_2025` | `data_raw/census_pep_v2025_va.json` |
| Groceries and help | `services`, `help_points` | USDA SNAP / OSM captures in `data_raw/README.md` |
| Citywide crime | `crime` | `data_raw/fbi_cde_va_agencies_2025.json` plus `second_capture_fbi_cde_agencies_2025_va.json` |
| Block incidents | `crime` | `data_raw/city_incidents_tiles_2026-10-24.json`, `city_incidents_MANIFEST.json` |
| Immigration enforcement | `enforcement_287g` | `data_raw/ice_287g_va_2026-10-24.json` |
| Local camping rule | `local_rule` | `LOCAL_RULES` in `scripts/build_va_localities.py`; open items in `docs/FACT_CHECK.md` |
| One-town receipt | `fixtures/<town>_<date>/MANIFEST.json` | `footing/pipeline.py` replay mode; never reuse another town's capture |

## When collection is needed

1. State the gap: field, FIPS codes, capture vintage, and why another request is needed. A UI change
   alone is not a reason to recapture a source. Current legal or eligibility advice still needs current
   primary-source verification; saved captures are historical evidence.
2. Check the saved URL, capture script and existing fact-check. Prefer the publisher's bulk file or
   documented endpoint when it contains the required data; reuse the saved request pattern otherwise.
3. Fetch only the necessary source/geography. Keep progress per source or FIPS so a partial run resumes
   at the first missing record. Avoid running overlapping collectors against the same source.
4. Record the exact URL, observation date, coverage, outcome (including no result or access failure),
   and next unresolved action in the capture manifest or fact-check. An access failure is not evidence
   of absence. Retry when access or the request has changed, rather than rediscovering the same URL.
5. Preserve the previous capture, compare the changed rows, rebuild, and validate. Separately requested
   independent verification must still read the publisher: reusing a capture is not a second check.

The most useful savings here come from avoiding repeated discovery and bulk recapture during coding.
Do not cut verification or replace missing values to make a session cheaper.
