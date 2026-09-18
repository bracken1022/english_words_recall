from src.models.vocabulary_item import VocabularyItem
from src.services.matcher import grade_answer


def test_exact_match_is_correct():
    item = VocabularyItem(english="receive", chinese="收到")
    assert grade_answer(item, "receive") is True


def test_case_insensitive_match_is_correct():
    item = VocabularyItem(english="receive", chinese="收到")
    assert grade_answer(item, "Receive") is True


def test_whitespace_tolerant_match_is_correct():
    item = VocabularyItem(english="receive", chinese="收到")
    assert grade_answer(item, "  receive  ") is True


def test_alternate_expression_is_correct():
    item = VocabularyItem(english="receive", chinese="收到", alternates=["accept"])
    assert grade_answer(item, "accept") is True


def test_misspelling_is_incorrect_no_fuzzy_tolerance():
    item = VocabularyItem(english="receive", chinese="收到")
    assert grade_answer(item, "recieve") is False


def test_empty_answer_is_incorrect():
    item = VocabularyItem(english="receive", chinese="收到")
    assert grade_answer(item, "") is False


def test_unrelated_answer_is_incorrect():
    item = VocabularyItem(english="receive", chinese="收到")
    assert grade_answer(item, "give up") is False
