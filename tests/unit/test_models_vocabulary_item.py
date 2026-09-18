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
