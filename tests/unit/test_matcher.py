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


def test_alternate_that_looks_like_a_yaml_boolean_word_is_matched_as_text():
    """Regression test for a reported crash: an alternate expression that
    happens to be "on"/"off"/"yes"/"no" must still be a plain string by
    the time it reaches grading (the fix lives in the YAML block parser,
    src/lib/markdown_blocks.py — this confirms grading itself works
    correctly once that's true)."""
    item = VocabularyItem(english="upon", chinese="在……上", alternates=["on"])
    assert grade_answer(item, "on") is True
    assert grade_answer(item, "upon") is True
