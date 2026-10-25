# Working on Footing

Read the current-session section at the top of `HANDOFF.md` first. Older session sections are history;
do not repeat completed work. Follow `docs/DATA_WORK.md` for data lookup and collection.

## Use the existing data first

- UI, scoring and parity work use committed `footing/static/va_localities.json` and replay fixtures.
  They do not need new publisher searches or a full data refresh.
- For one fact, run `python scripts/data_lookup.py <FIPS> --field <field>`; use `--list` to see the
  supported fields. This prints one field and its recorded sources, not the whole dataset.
- `data_raw/README.md` is the source/file/request index. `docs/FACT_CHECK.md` tracks disputed and
  unchecked claims. Reuse those exact sources before discovering new ones.
- Browse when verifying a current claim, resolving an identified discrepancy, filling a specific
  missing field, or doing a requested refresh. Keep the task to the affected field and localities.
  Record the result and access failures so another session can resume without rediscovery.
- Keep old captures for comparison. Never replace Unknown with a guess or a zero.

## Implementation and validation

- `footing/vafit.py` / `footing/web/vafit.js` and `footing/va.py` / `footing/web/vapoint.js` are twins;
  keep their output identical. Profiles stay on the phone; do not send them to scoring endpoints.
- Run `python -m pytest -q` and `python scripts/build_va_localities.py --check`.
- UI changes also need both `scripts/ui_globe_smoke.py` and `scripts/ui_standalone_smoke.py` and
  inspection of relevant screenshots. See `HANDOFF.md` for server commands.
- On Windows, `.venv/Scripts/python.exe` is the local test runtime. An installed Edge can run the
  smoke checks with `FOOTING_BROWSER_CHANNEL=msedge`; do not download a browser if one works already.
- Update the handoff with what changed, what actually passed, and the next unfinished item.
