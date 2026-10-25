"""Every language must carry every English string, except the short list below that falls back to English on
purpose. Without this, a new string added in English silently shows up in English on an Arabic or Korean
screen: that is how the open-water refusal and the receipt button went untranslated (found in session 6 by
clicking the app through a browser)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "footing" / "web"

# Allowed to fall back to English, and why. Keep this short; anything a Virginia user can see belongs in all 8.
ENGLISH_FALLBACK_OK = {
    # The 50-state view is labelled beta and was never translated beyond Spanish.
    "lede", "top", "allStates", "c_access", "c_affordability", "c_criminalization",
    "l_affordability", "lo_affordability", "hi_affordability",
    # Digits and numeric ranges read the same.
    "age18", "age25", "age50", "age62", "bed1", "bed2", "bed3", "bed4",
    # Not used by any screen any more.
    "hide", "rateHelp", "offlineTiles", "demoTown", "_end",
}

SCRIPT = """
const vm = require('vm'), fs = require('fs'), path = require('path');
const ctx = {}; ctx.self = ctx; vm.createContext(ctx);
for (const f of ['i18n.js', 'i18n_more.js']) vm.runInContext(fs.readFileSync(path.join(process.argv[1], f), 'utf8'), ctx);
const I = ctx.FootingI18n;
const out = {};
for (const l of I.LANGS) out[l] = Object.keys(I.strings[l] || {});
process.stdout.write(JSON.stringify({ langs: I.LANGS, rtl: I.RTL, keys: out, en: I.strings.en }));
"""


@pytest.fixture(scope="module")
def i18n():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    r = subprocess.run(["node", "-e", SCRIPT, str(WEB)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_every_language_has_every_string_a_virginia_user_can_see(i18n):
    en = set(i18n["keys"]["en"])
    for lang in i18n["langs"]:
        missing = sorted(en - set(i18n["keys"][lang]) - ENGLISH_FALLBACK_OK)
        assert not missing, f"{lang} is missing {missing}"


def test_the_fallback_list_only_names_real_strings(i18n):
    assert ENGLISH_FALLBACK_OK <= set(i18n["keys"]["en"]), ENGLISH_FALLBACK_OK - set(i18n["keys"]["en"])


def test_unused_fallback_strings_really_are_unused():
    js = "".join((WEB / f).read_text(encoding="utf8") for f in ("globe.js", "app.js") if (WEB / f).exists())
    for key in ("hide", "rateHelp", "offlineTiles", "demoTown"):
        assert f't("{key}"' not in js, f"{key} is used by a screen, so it must be translated"


def test_map_tap_refusals_have_their_own_translated_sentence(i18n):
    for key in ("outsideTap", "waterTap"):
        for lang in i18n["langs"]:
            assert key in i18n["keys"][lang], (key, lang)


def test_rtl_languages_are_known(i18n):
    assert set(i18n["rtl"]) == {"ar", "fa"} and set(i18n["rtl"]) <= set(i18n["langs"])
