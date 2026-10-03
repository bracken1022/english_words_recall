"""Unit tests for enrichment validation (spec 018,
contracts/enrichment-validation.md). The model's output is untrusted:
these pure functions decide what may reach a vocabulary file."""

import pytest

from src.services.enrichment import ImportItem, validate_chinese, validate_item
from src.services.enrichment_client import EnrichmentReply

UNUSABLE = "meaning was unusable"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("热心的;热情的", "热心的；热情的"),
        ("热心的,热情的", "热心的；热情的"),
        ("热心的，热情的", "热心的；热情的"),
        ("热心的； 热情的", "热心的；热情的"),
        (" 收到 ", "收到"),
        ("收到；接受；接待；欢迎", "收到；接受；接待；欢迎"),
        ("是…的典范", "是…的典范"),
    ],
)
def test_valid_chinese(raw, expected):
    assert validate_chinese(raw) == (expected, None)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        None,
        42,
        "hello",
        "a\nb热",
        "一；二；三；四；五",
        "热心；；热情",
        "热" * 41,
        "n. 热心",
        "adj. 热心的",
        "【热心】",
        "热心 used in a sentence",
    ],
)
def test_unusable_chinese(raw):
    assert validate_chinese(raw) == (None, UNUSABLE)


# --- IPA rules 1-7, in order (US4; IPA from the offline dictionary) ----------


def _validated(english, supplied=None, alternates=None):
    item = ImportItem(english=english, position="line 1", supplied=supplied or {})
    reply = EnrichmentReply(outcome="ok", chinese="热心的", alternates=alternates or [])
    validate_item(item, reply)
    assert item.state == "enriched"
    return item


def test_rule1_supplied_ipa_kept_whatever_accent():
    item = _validated("receive", supplied={"ipa": "rɪˈsiːv", "chinese": "收到"})
    assert (item.ipa, item.ipa_review) == ("rɪˈsiːv", None)


@pytest.mark.parametrize("word", ["NASA", "UK"])
def test_rule2_abbreviations(word):
    item = _validated(word)
    assert (item.ipa, item.ipa_review) == (None, "abbreviation — check how it's said")


@pytest.mark.parametrize("supplied", [{}, {"chinese": "记录"}])
def test_rule3_heteronyms_always_need_review(supplied):
    # The dictionary can't tell which meaning a word is used in.
    item = _validated("record", supplied=supplied)
    assert (item.ipa, item.ipa_review) == (None, "pronunciation depends on the meaning")


def test_rule4_ambiguous_dictionary_entry():
    item = _validated("research")
    assert (item.ipa, item.ipa_review) == (
        None,
        "more than one pronunciation — check which one you need",
    )


def test_rule5_not_in_dictionary():
    item = _validated("zxqvword")
    assert (item.ipa, item.ipa_review) == (None, "not in the pronunciation dictionary")


def test_rule5_spelling_variant_is_looked_up():
    item = _validated("epitomise", alternates=["epitomize"])
    assert (item.ipa, item.ipa_review) == ("ɪˈpɪtəmaɪz", None)


def test_rule5_synonym_alternate_is_never_looked_up():
    # A learner-supplied synonym must not lend its pronunciation.
    item = _validated("zxqvword", supplied={"alternates": ["zealous"]})
    assert (item.ipa, item.ipa_review) == (None, "not in the pronunciation dictionary")


def test_rule6_failed_check(monkeypatch):
    from src.lib.us_pronunciation import Lookup
    from src.services import enrichment

    monkeypatch.setattr(enrichment, "lookup_american_ipa", lambda *a, **k: Lookup("hɒt"))
    item = _validated("hot")
    assert item.ipa is None
    assert item.ipa_review == "dictionary pronunciation failed check: British IPA marker: ɒ"


@pytest.mark.parametrize(
    "english, ipa", [("zealous", "ˈzeləs"), ("tend to", "ˈtend tə"), ("Tyre", "ˈtaɪər")]
)
def test_rule7_dictionary_pronunciation(english, ipa):
    item = _validated(english)
    assert (item.ipa, item.ipa_review) == (ipa, None)
