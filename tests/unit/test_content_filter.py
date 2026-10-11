"""Unit tests for src/lib/content_filter.py (spec 021, Constitution II):
generated examples must suit a family learner."""

import pytest

from src.lib.content_filter import BLOCKLIST, is_clean


@pytest.mark.parametrize("text", ["She is a zealous supporter.", "我们去公园。", "The class assessed it."])
def test_clean(text):
    assert is_clean(text)


@pytest.mark.parametrize("word", sorted(BLOCKLIST)[:10])
def test_blocked_words(word):
    assert not is_clean(f"This is {word.upper()}!")


def test_chinese_block_entries():
    chinese = [w for w in BLOCKLIST if any("一" <= c <= "鿿" for c in w)]
    assert chinese
    assert not is_clean(f"这是{chinese[0]}。")


def test_blocklist_size():
    assert len(BLOCKLIST) >= 30


def test_studied_word_is_exempt():
    assert not is_clean("They used torture.")
    assert is_clean("They used torture.", allow={"torture", "tortured"})
    assert not is_clean("They used torture and porn.", allow={"torture"})
