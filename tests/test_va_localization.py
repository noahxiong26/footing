"""Virginia native-language Details: metadata parity and no implicit English fallback.

Uses only committed captures. Translation completeness is not linguistic review.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from footing import vafit
from footing.fit import load_eligibility

ROOT = Path(__file__).resolve().parents[1]
ELIG, VA = load_eligibility(), vafit.load_va()
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

SCRIPT = r"""
const vm = require('vm'), fs = require('fs'), path = require('path');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const web = path.join(process.argv[1], 'footing/web');
const ctx = {}; ctx.self = ctx; vm.createContext(ctx);
for (const f of ['i18n.js', 'i18n_more.js']) vm.runInContext(fs.readFileSync(path.join(web, f), 'utf8'), ctx);
const I = ctx.FootingI18n, F = require(path.join(web, 'vafit.js'));
const failures = [], descriptors = [], keys = new Set(); let translated = 0;
for (const request of input.requests) {
  const va = request.va || input.va;
  const result = F.fitScore(input.elig, va, request.fips, request.profile, request.community, request.tile);
  descriptors.push(result.components.map(c => ({id: c.id, reason_data: c.reason_data})));
  for (const c of result.components) {
    if (I.vaReason('en', c) !== c.reason) throw Error('English contract changed');
    c.reason_data.segments.forEach(s => keys.add(s.key));
    for (const lang of I.LANGS.filter(l => l !== 'en')) {
      const parts = I.vaReasonParts(lang, c), text = I.vaReason(lang, c);
      translated++;
      if (text !== parts.map(p => p.text).join(' ')) failures.push('join');
      if (text === c.reason || /\{\w+\}/.test(text)) failures.push([lang, c.id, text]);
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i];
        if (p.lang === 'en') {
          if (p.kind !== 'quote' || i === 0 || parts[i-1].kind !== 'quote_label') failures.push(['unlabelled English', p]);
          if (!c.reason_data.segments.some(s => s.key === 'recorded_note' && p.text === '“' + s.vars.text + '”')) failures.push(['unrecorded quote', p]);
        } else if (p.lang !== lang) failures.push(['wrong language', p]);
      }
    }
  }
}
let rejected = 0;
for (const c of [{reason:'old API'}, {reason_data:{version:2,segments:[]}},
  {reason_data:{version:1,segments:[{key:'brand_new_untranslated_reason',vars:{}}]}},
  {reason_data:{version:1,segments:[{key:'rent',vars:{}}]}}]) {
  try { I.vaReason('tl', c); } catch(e) { rejected++; }
}
const vars = {town:'A $& {hours}', hours:'NOT AN INSERTED VALUE'};
const literal = I.t('tl', 'openReceipt', vars);
process.stdout.write(JSON.stringify({descriptors, failures, keys:[...keys], translated, rejected, literal}));
"""


@pytest.fixture(scope="module")
def corpus():
    requests = []
    for kids in (False, True):
        for fips in sorted(VA["localities"]):
            requests.append({"fips": fips, "profile": {"status": "undocumented", "show_crime": True,
                "household": {"kids": kids, "bedrooms": int(fips) % 5}}})
    # Every saved block, including zero counts; source/date provenance must survive.
    for tile, counts in VA["incident_tiles"].items():
        requests.append({"fips": counts["fips"], "profile": {"show_crime": True}, "tile": tile})
    for n in (1, 4):
        requests.append({"fips": "51121", "profile": {}, "community": {"51121": {"n": n, "score": 70, "freshness": 0.8}}})
    # Explicit synthetic branch inputs, not asserted as real locality observations.
    rare = copy.deepcopy(VA)
    loc = rare["localities"]["51121"]
    loc["services"]["osm"] = {}
    loc["services"]["snap"]["restaurant_meals"] = 1
    loc["crime"] = None
    loc["coc"]["people_in_families"] = 0
    loc["coc"]["unsheltered_carried_from_2024"] = True
    rare["localities"] = {"51121": loc}
    requests.append({"fips": "51121", "profile": {"show_crime": True, "household": {"kids": True}}, "va": rare})
    py = []
    for r in requests:
        result = vafit.fit_score(ELIG, r.get("va", VA), r["fips"], r["profile"], r.get("community"), r.get("tile"))
        py.append([{"id": c["id"], "reason_data": c["reason_data"]} for c in result["components"]])
    got = json.loads(subprocess.run(["node", "-e", SCRIPT, str(ROOT)],
        input=json.dumps({"va": VA, "elig": ELIG, "requests": requests}),
        capture_output=True, text=True, encoding="utf8", check=True).stdout)
    return py, got


def test_python_and_js_reason_metadata_match_for_every_locality_and_block(corpus):
    py, got = corpus
    assert py == got["descriptors"]


def test_every_visible_reason_translates_without_implicit_english(corpus):
    _, got = corpus
    assert got["translated"] > 20000
    assert not got["failures"], got["failures"][:10]
    assert got["rejected"] == 4


def test_corpus_covers_unknown_law_statuses_and_both_crime_levels(corpus):
    _, got = corpus
    assert {"law_broad_ban", "law_limited_ban", "law_site_closure", "law_proposed", "law_clearing_policy",
        "law_checked_none_found", "law_unchecked", "crime_unknown", "crime_block", "crime_city", "crime_locality",
        "help_none", "meals_none", "meals", "carried", "coc_large", "coc_shared", "beds_family_none",
        "safety_task", "safety_jail", "safety_none", "community", "community_none"} <= set(got["keys"])


def test_interpolation_preserves_literal_dollars_and_placeholder_like_names(corpus):
    assert corpus[1]["literal"] == "Buksan ang tala para sa A $& {hours}"


def test_metadata_preserves_unknown_and_opt_in_semantics():
    profile = {"show_crime": True}
    beach = vafit.fit_score(ELIG, VA, "51810", profile)
    crime = next(c for c in beach["components"] if c["id"] == "crime")
    assert crime["score"] is None and crime["share"] == 0
    assert crime["reason_data"]["segments"][0]["key"] == "crime_unknown"
    assert crime["reason_data"]["segments"][1]["vars"]["text"] == VA["localities"]["51810"]["crime"]["unknown_reason"]
    assert not any(c["id"] == "crime" for c in vafit.fit_score(ELIG, VA, "51810", {})["components"])
    law = next(c for c in vafit.fit_score(ELIG, VA, "51121", {})["components"] if c["id"] == "laws")
    assert law["score"] is None and law["reason_data"]["segments"][0]["key"] == "law_checked_none_found"
