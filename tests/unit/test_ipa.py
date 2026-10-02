"""Unit tests for src/lib/ipa.py (spec 017, data-model.md "IPA value rules")."""

import pytest

from src.lib.ipa import display_ipa, normalize_ipa


def test_missing_is_none():
    assert normalize_ipa(None) == (None, None)


@pytest.mark.parametrize("raw", ["rɪˈsiːv", "/rɪˈsiːv/", "[rɪˈsiːv]", "  /rɪˈsiːv/ "])
def test_normalizes_brackets_and_space(raw):
    assert normalize_ipa(raw) == ("rɪˈsiːv", None)


def test_phrase_keeps_inner_space():
    assert normalize_ipa("ˈtend tə") == ("ˈtend tə", None)


@pytest.mark.parametrize("raw", [123, "", "//", "123", "/12ə/", "ˈː", "a" * 101])
def test_invalid_values(raw):
    value, problem = normalize_ipa(raw)
    assert value is None
    assert "is not a pronunciation" in problem


def test_problem_quotes_raw_value():
    assert 'ipa "123"' in normalize_ipa("123")[1]


def test_display():
    assert display_ipa("rɪˈsiːv") == "/rɪˈsiːv/"
    assert display_ipa(None) == ""


# --- check_british_ipa (research R6) --------------------------------------------

from src.lib.ipa import check_british_ipa


@pytest.mark.parametrize(
    "ipa",
    [
        "rɪˈsiːv",
        "ˈteɪbl̩",
        "ˈtend tə",
        "ˌɪmprəvaɪˈzeɪʃn̩",
        "ˈwæɡən",
        "bʌlk",
        "ˈpɪtʃə",
        "dɪˈspjuːt",
        "ˈskænti",
        "ˈrɪvə",
        "ˈdʒɜːni",
        "braɪt",
        "ˈpeɪʃnt",
        "ˈfɑːðə(r)",
        "ˌkaʊntərˈækt",
    ],
)
def test_valid_british_ipa(ipa):
    assert check_british_ipa(ipa) == []


@pytest.mark.parametrize("ipa", ["ˈrɪvɚ", "ˈsoʊ", "ˈɹɪvə"])
def test_american_symbols_rejected(ipa):
    assert check_british_ipa(ipa)


def test_ascii_g_rejected_with_hint():
    problems = check_british_ipa("ˈwægən")
    assert any("ɡ" in p for p in problems)


def test_missing_primary_stress():
    assert check_british_ipa("rɪsiːv")


def test_double_primary_stress_in_one_word():
    assert check_british_ipa("ˈrɪˈsiːv")


@pytest.mark.parametrize("ipa", ["ˈwɔːrm", "ˈrɪvər"])
def test_rhotic_r_rejected(ipa):
    assert any("non-rhotic" in p for p in check_british_ipa(ipa))


def test_phrase_needs_one_stress_but_not_on_function_word():
    assert check_british_ipa("ˈtend tə") == []
    assert check_british_ipa("tend tə")


def test_phrase_content_words_need_some_stress():
    assert check_british_ipa("ˌɡɪv əˈweɪ") == []
    assert check_british_ipa("ˈɡɪv əweɪ")
