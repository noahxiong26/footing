# The Virginia data pipeline

How a number gets from a government website into the score, and how to refresh it. Every figure in
`footing/static/va_localities.json` can be traced back to a file in `data_raw/` and from there to a URL and
the day it was read.

```
data_raw/*.json                     one file per source, each documented in data_raw/README.md
        │                           (captured by hand through a real browser - see "Capturing", below)
        ▼
scripts/build_va_localities.py      matches every source by FIPS code, never by name
        │                           validates against the publisher's own totals
        │                           writes Unknown + a reason wherever data is missing
        ▼
footing/static/va_localities.json   133 localities, every field citing a source
        │
        ▼
footing/web/vafit.js                the phone scores it, so status and household never leave the device
footing/vafit.py                    the same engine in Python, for the API, the CLI and the tests
```

## Refreshing it

Deterministic: the same inputs always give the same output.

```bash
python scripts/build_va_localities.py            # rebuild footing/static/va_localities.json
python scripts/build_va_localities.py --check     # validate without writing
pytest -q                                         # 191 tests, including JS/Python parity
```

`--check` is also run by the test suite, and `tests/test_vafit.py` rebuilds the dataset and asserts the
committed file matches, so a stale commit cannot slip through.

## What the builder validates

It raises rather than writing a number it cannot stand behind:

- **Publisher totals.** HUD's Virginia state total of 7,240 people counted, 1,349 of them outside; 16
  Continuums of Care; 133 localities with a TIGER shape; every FMR row with 5 bedroom sizes in ascending
  order; every population over 2,000.
- **Name matching.** Virginia's independent cities are not part of any county, so `fips_for` keeps
  "Roanoke city" and "Roanoke County" apart, handles `BEDFORD CITY` (merged into Bedford County in 2013),
  and fails loudly on an unmatched name instead of dropping the row.
- **Agencies that straddle a county line.** Four town police departments report under two counties; each is
  placed by its own published coordinates, and only when they fall inside one of the counties it lists.
- **Incident tiles.** Each city's per-tile counts must add up to that city's `placed` total.
- **Sources.** Every `local_rule` must cite a key in `sources`, except a `checked_none_found` row, which
  must have no source and no score.

## Unknown is a value

The rule is: never guess, say why. A missing number is `null` with a reason next to it, and the engine drops
it out of the score rather than counting it as 0. Two places this matters most:

- **Virginia Beach** reported no 2025 crime to the FBI. Its counts are `null` and the reason says so; a
  stored `0` would read as a crime-free city of 450,000.
- **A locality with no camping rule** means nobody has read its code, never "no ban". Montgomery County was
  searched and nothing found, which is a third, separate answer (`checked_none_found`): shown, not scored.

## Capturing (the slow part)

The build sandbox reaches only GitHub and the package registries. Every government source was captured
through a real browser on the owner's laptop, one request pattern at a time, and the results copied
byte-for-byte rather than retyped. `data_raw/README.md` records the exact request for each file;
`scripts/capture/` holds the scripts that were pasted into the browser console.

Expect this to be most of the work on any refresh. The limits that shape it:

- The browser tool returns about 1 KB per script call, so results are written into the page and read back
  in chunks of 50 KB or less.
- Long jobs hit a 45-second limit; some sites block cross-site requests.
- HUD's FMR pages are one county at a time, 133 of them, with special cases for the Small Area FMR metros
  (the DC and Hampton Roads areas).
- The FBI's CDE is one request per agency per measure: 412 agencies.

## Capturing a source twice is the only real check

Sessions 3 and 4 captured HUD FMR, FBI CDE, HUD HIC and the CoC map independently. Comparing them is the
only verification this dataset has ever had, and it found a county mix-up that neither session's own tests
could have caught. Both captures are kept — the second as `data_raw/second_capture_*.json` — and the
builder uses the more precise of the two for months reported. If you refresh a source, **keep the old
capture** and compare. `docs/FACT_CHECK.md` records what agreed, what did not, and what is still open.

## Where agents would help, and where they would not

The merge step must stay plain, deterministic code so the same inputs always give the same output. Two
places where an agent earns its place:

- **Collection from sources with no API**: one agent per source for the 133 city and county codes, and for
  shelter hours and phone numbers. Each returns a cited row, or Unknown. Never a number from memory.
- **Verification**: a second agent that never saw the first one's work re-checks a sample against the
  publisher. The point is independence, which is exactly what made the two captures useful.
