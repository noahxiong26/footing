# Town capture handoff — 2026-10-25

Five independent point-receipt captures use the existing `footing.cli record` command and pipeline.
No other town's responses were copied. Existing Christiansburg fixtures remain unchanged.
The folder date is the native date, 2026-10-25, America/New_York. Request timestamps are actual UTC
clock readings, including retries, without backdating. The pipeline snaps each point to its own
approximately 1 km tile. The search radius is 5,000 m.

| Town | Input latitude, longitude | Census FIPS |
| --- | --- | --- |
| Roanoke | 37.2710, -79.9414 | 51770 |
| Richmond | 37.5407, -77.4360 | 51760 |
| Blacksburg | 37.2296, -80.4139 | 51121 (Montgomery County) |
| Harrisonburg | 38.4496, -78.8689 | 51660 |
| Alexandria | 38.8048, -77.0469 | 51510 |

## Run and resume

Run from the repository root. Only optional keys inherited through `Settings.from_env()` are used.
Neither script loads `.env` or prints credentials.

```powershell
.venv/Scripts/python.exe -u scripts/record_towns.py --date 2026-10-25
.venv/Scripts/python.exe -u scripts/record_towns.py roanoke --date 2026-10-25 --resume --browser-ua --timeout 45 --fallbacks
```

`scripts/record_demo_towns.sh` delegates to this wrapper and selects the local virtual environment
when available; `FOOTING_PYTHON` can specify an interpreter path. Its default batch is these five
towns; pass slugs to narrow it. Christiansburg/Radford are excluded. Existing output is refused
unless `--resume` is explicit. Omit `--date` for today's local date; it changes folder naming only.
Use a new date/root for fresh responses: resume reuses successful requests, verifies their SHA-256,
and retains their original request timestamps and metadata.

The wrapper temporarily instruments the existing fetcher/source runner within its own process.
The CLI, source adapters, source order, parsers, snapping and engines are unchanged.

- `MANIFEST.json` retains the complete file manifest and `not_captured` reasons, adding all 15
  source outcomes, parsed measures/place counts, required key names, request methods/bodies,
  real start/end times, response hashes and capture-run history.
- `REQUESTS.jsonl` appends request and source outcomes, including failures and reused responses.
  Authorization headers are omitted and credential fields are redacted. The underlying fetcher
  may make two transport attempts within one logged request interval.
- Empty HTTP 200 bodies, HTML instead of JSON, empty JSON objects/arrays, incomplete Overpass
  replies and malformed school replies are rejected. A valid response with an empty results or
  features array can establish a genuine zero; failed access cannot.

Complete successful JSON payloads are retained, apart from credential redaction. Schools use the
adapter's state request and county filter; each town made its own request. SNAP includes the full
bounding-envelope response; receipts apply the radius to place counts. These are point-tile
captures, not complete city inventories. Publisher dates remain in responses and source outcomes.

## Access attempts and coverage

The sandbox probe failed DNS resolution on all attempted publishers and saved no responses.
Normal network access was requested through escalation. Ignored probe directories are
`out/town_capture_probe/roanoke` and `out/town_capture_normal_probe/roanoke`; no probe response
was copied into any fixture.

The first pass saved seven responses per town: Census geography, NWS points/alerts, Open-Meteo,
SNAP metadata/retailers and Urban Institute schools. Overpass timed out and BLS returned HTTP 503
for all five. Final retry results are recorded below after validation.

Retries use `Mozilla/5.0 (compatible; Footing public-data audit)`, `Accept: */*` (retaining
source-specific Accept headers), and a 45-second timeout. After the default Overpass endpoint
failed, resume tries Private.coffee then MapRVA's Virginia instance with the same town query and
parser. These are documented [public Overpass instances](https://wiki.openstreetmap.org/wiki/Overpass_API).
BLS retries the adapter's POST, then the [documented single-series GET](https://www.bls.gov/developers/api_signature.htm).
Exact URLs, queries/bodies, times and failures are preserved per town for efficient retries.

Six adapters lack inherited keys: `census_acs` (census), `hud_fmr` (hud), `eia` (eia),
`google_places` (google_maps), `transitland` (transitland), and `kroger` (kroger_id/kroger_secret).
HRSA uses the existing empty `footing/static/hrsa_sites.csv`; it remains Unknown without a network
request. `static_tables` supplies existing dated minimum-wage and USDA food-baseline values locally;
those are not fresh captures. No missing source was replaced with a guess or zero.

Before retrying, inspect `source_outcomes`, `not_captured` and failed log entries. Supply optional
keys through the normal environment when available, then resume the affected town. HRSA needs a
separately scoped local-table import. An access failure is not evidence of absence.

## Replay validation

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_town_captures.py tests/test_fixture_sets.py tests/test_sources_live_fixtures.py
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe scripts/build_va_localities.py --check
.venv/Scripts/python.exe -m footing receipt --lat 37.2710 --lon -79.9414 --mode replay --fixtures fixtures
```

The new tests prohibit network calls and check discovery, correct FIPS, parent/direct agreement,
refusal of the other four towns and a neighboring tile, file hashes/timestamps, complete source
outcomes, and receipt measures/counts matching actual coverage. Missing sources retain reasons
and supply no measures/places; Unknown money values remain null.

Replay generates new receipt/provenance timestamps while parsing historical fixtures. Date the
capture using manifest request times and publisher observations, not replay's `generated_at` or
source `fetched_at`.

This document is the capture handoff. HANDOFF/README, engines, UI, builder and old fixtures are
outside this task's edits. No commit/push or UI changes are included.
