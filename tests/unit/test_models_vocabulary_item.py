import pytest

from src.models.vocabulary_item import VocabularyItem, VocabularyItemError


def test_valid_item_defaults():
    item = VocabularyItem(english="receive", chinese="收到")
    assert item.english == "receive"
    assert item.chinese == "收到"
    assert item.alternates == []
    assert item.group is None


def test_valid_item_with_alternates_and_group():
    item = VocabularyItem(english="receive", chinese="收到", alternates=["accept"], group="unit1")
    assert item.alternates == ["accept"]
    assert item.group == "unit1"


def test_missing_english_is_invalid():
    with pytest.raises(VocabularyItemError):
        VocabularyItem(english="", chinese="收到")


def test_missing_chinese_is_invalid():
    with pytest.raises(VocabularyItemError):
        VocabularyItem(english="receive", chinese="")


def test_from_block_builds_item_from_dict():
    item = VocabularyItem.from_block({"english": "receive", "chinese": "收到", "alternates": ["accept"]})
    assert item.english == "receive"
    assert item.alternates == ["accept"]


def test_from_block_missing_required_field_raises():
    with pytest.raises(VocabularyItemError):
        VocabularyItem.from_block({"chinese": "收到"})


def test_non_string_english_is_invalid():
    """Defense in depth: a non-string field (e.g. a YAML parser resolving
    an unquoted word like "on" to a boolean) must be rejected here too,
    at load time, rather than crashing later mid-session when that word
    is graded (src/services/matcher.py)."""
    with pytest.raises(VocabularyItemError):
        VocabularyItem(english=True, chinese="收到")


def test_non_string_chinese_is_invalid():
    with pytest.raises(VocabularyItemError):
        VocabularyItem(english="on", chinese=True)


def test_non_string_alternate_is_invalid():
    with pytest.raises(VocabularyItemError):
        VocabularyItem(english="on", chinese="在……上", alternates=["off", True])


def test_non_string_group_is_invalid():
    with pytest.raises(VocabularyItemError):
        VocabularyItem(english="on", chinese="在……上", group=True)


def test_from_block_with_non_string_alternate_raises():
    with pytest.raises(VocabularyItemError):
        VocabularyItem.from_block({"english": "on", "chinese": "在……上", "alternates": [True]})


# --- spec 017: ipa -------------------------------------------------------------


def test_ipa_defaults_to_none():
    item = VocabularyItem(english="receive", chinese="收到")
    assert item.ipa is None
    assert item.ipa_problem is None


def test_from_block_reads_and_normalizes_ipa():
    item = VocabularyItem.from_block({"english": "receive", "chinese": "收到", "ipa": "/rɪˈsiːv/"})
    assert item.ipa == "rɪˈsiːv"


def test_from_block_invalid_ipa_keeps_word():
    item = VocabularyItem.from_block({"english": "receive", "chinese": "收到", "ipa": 42})
    assert item.ipa is None
    assert "is not a pronunciation" in item.ipa_problem


def test_ipa_does_not_affect_accepted_expressions():
    item = VocabularyItem(english="receive", chinese="收到", alternates=["accept"], ipa="rɪˈsiːv")
    assert item.accepted_expressions() == ["receive", "accept"]


def test_ipa_problem_not_compared_or_shown():
    a = VocabularyItem(english="x", chinese="y", ipa_problem="bad")
    b = VocabularyItem(english="x", chinese="y")
    assert a == b
    assert "ipa_problem" not in repr(a)
