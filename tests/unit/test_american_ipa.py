"""Unit tests for the American IPA checks (spec 018 research R4,
contracts/enrichment-validation.md): check_american_ipa() enforces the
Oxford Learner's Dictionaries NAmE convention, and is_heteronym() marks
words whose pronunciation depends on the meaning."""

from pathlib import Path

import pytest
import yaml

from src.lib.ipa import HETERONYMS, check_american_ipa, is_heteronym

FIXTURE = yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "fixtures" / "american_ipa.yml").read_text("utf-8")
)


@pytest.mark.parametrize("entry", FIXTURE["words"], ids=lambda e: e["english"])
def test_reviewed_american_transcriptions_pass(entry):
    assert check_american_ipa(entry["ipa"]) == []


@pytest.mark.parametrize("ipa", FIXTURE["british_counterparts"])
def test_british_transcriptions_fail(ipa):
    assert check_american_ipa(ipa) != []


def test_fixture_size():
    assert len(FIXTURE["words"]) >= 30
    assert len(FIXTURE["british_counterparts"]) >= 10


def test_ascii_g_is_rejected():
    assert "use ɡ (U+0261), not g" in check_american_ipa("go")


@pytest.mark.parametrize("ipa", ["ˈbɝd", "ˈbetɚ", "ˈbeɾər"])
def test_other_conventions_rejected(ipa):
    problems = check_american_ipa(ipa)
    assert any(p.startswith("not American IPA (OALD NAmE style)") for p in problems)


@pytest.mark.parametrize(
    "ipa, marker",
    [
        ("hɒt", "ɒ"),
        ("ɡəʊ", "əʊ"),
        ("ˈwɔːtə(r)", "(r)"),
        ("bɜːd", "ɜː without r"),
        ("hɪə", "ɪə"),
        ("keə", "eə"),
        ("ʃʊə", "ʊə"),
    ],
)
def test_british_markers_named(ipa, marker):
    assert f"British IPA marker: {marker}" in check_american_ipa(ipa)


def test_flap_mark_is_allowed():
    assert check_american_ipa("ˈbet̬ər") == []


def test_stress_rules():
    assert any("more than one primary stress" in p for p in check_american_ipa("ˈˈzeləs"))
    assert any("no primary stress" in p for p in check_american_ipa("zeləs"))
    assert check_american_ipa("ˈtend tə") == []
    assert check_american_ipa("ˌmeɪk ˈʌp fər") == []


@pytest.mark.parametrize("word", ["Record", " lead ", "tear", "wind", "minute", "present", "object"])
def test_heteronyms(word):
    assert is_heteronym(word)


@pytest.mark.parametrize("word", ["zealous", "receive", "records"])
def test_not_heteronyms(word):
    assert not is_heteronym(word)


def test_heteronym_list_size():
    assert len(HETERONYMS) >= 40


def test_stress_mark_between_vowel_and_r():
    assert check_american_ipa("ˌekstrətəˈrestriəl") == []
    assert check_american_ipa("ˌekstrətɜːˈrestriəl") == []
