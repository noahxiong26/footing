"""Every language must carry every English string, except the short list below that falls back to English on
purpose. Without this, a new string added in English silently shows up in English on an Arabic or Korean
screen: that is how the open-water refusal and the receipt button went untranslated (found in session 6 by
clicking the app through a browser)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "footing" / "web"

# Allowed to fall back to English, and why. Anything visible in Virginia belongs in all nine.
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
process.stdout.write(JSON.stringify({ langs: I.LANGS, rtl: I.RTL, machine: I.MACHINE,
  keys: out, en: I.strings.en, strings: I.strings, reasons: I.vaReasonTemplates }));
"""


@pytest.fixture(scope="module")
def i18n():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    r = subprocess.run(["node", "-e", SCRIPT, str(WEB)], capture_output=True, text=True, encoding="utf-8", check=True)
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


def test_tagalog_has_language_option_and_honest_review_metadata(i18n):
    assert "tl" in i18n["langs"] and "tl" in i18n["machine"] and "tl" not in i18n["rtl"]
    assert i18n["strings"]["tl"]["langName"] == "Tagalog"
    assert "Hindi pa" in i18n["strings"]["tl"]["machine"]
    assert set(i18n["machine"]) == set(i18n["langs"]) - {"en"}


def test_visible_strings_keep_all_interpolation_slots(i18n):
    for lang in i18n["langs"]:
        for key, english in i18n["en"].items():
            if key in ENGLISH_FALLBACK_OK:
                continue
            translated = i18n["strings"][lang][key]
            assert translated.strip(), (lang, key)
            assert sorted(re.findall(r"\{\w+\}", translated)) == sorted(re.findall(r"\{\w+\}", english)), (lang, key)


def test_data_driven_status_and_program_labels_have_no_english_fallback(i18n):
    # English/Spanish labels come from eligibility.json; the other languages use st_/p_.
    eligibility = json.loads((ROOT / "footing/static/eligibility.json").read_text(encoding="utf8"))
    for lang in set(i18n["langs"]) - {"en", "es"}:
        for section, prefix in (("statuses", "st_"), ("programs", "p_")):
            for item in eligibility[section]:
                key = prefix + item["id"]
                assert i18n["strings"][lang].get(key), (lang, key)


def test_every_reason_template_is_explicitly_translated(i18n):
    tables = i18n["reasons"]
    assert set(tables) == set(i18n["langs"])
    for lang, table in tables.items():
        assert set(table) == set(tables["en"]), lang
        for key, text in table.items():
            assert text.strip(), (lang, key)
            assert sorted(re.findall(r"\{\w+\}", text)) == sorted(re.findall(r"\{\w+\}", tables["en"][key])), (lang, key)
            if lang != "en":
                assert text != tables["en"][key], (lang, key)


def test_node_text_output_is_always_decoded_as_utf8():
    """Windows decodes subprocess text as CP1252 by default and broke on translated output (S8.0)."""
    import re
    here = Path(__file__).resolve().parent
    for path in here.glob("test_*.py"):
        src = path.read_text(encoding="utf-8")
        for call in re.findall(r"subprocess\.run\((?:[^()]|\([^()]*\))*\)", src):
            if "text=True" in call:
                assert 'encoding="utf-8"' in call or 'encoding="utf8"' in call, (path.name, call[:80])
