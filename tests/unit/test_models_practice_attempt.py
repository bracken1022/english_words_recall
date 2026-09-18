import pytest

from src.models.practice_attempt import PracticeAttempt, PracticeAttemptError


def test_valid_recall_only_attempt():
    attempt = PracticeAttempt(
        timestamp="2026-09-18T10:15:32",
        item="receive",
        answer="",
        correct=False,
    )
    assert attempt.sentence is None
    assert attempt.feedback is None


def test_valid_full_attempt_with_sentence_and_feedback():
    attempt = PracticeAttempt(
        timestamp="2026-09-18T10:15:32",
        item="receive",
        answer="receive",
        correct=True,
        sentence="I received a gift.",
        feedback="already correct",
    )
    assert attempt.sentence == "I received a gift."
    assert attempt.feedback == "already correct"


def test_sentence_without_feedback_is_invalid():
    with pytest.raises(PracticeAttemptError):
        PracticeAttempt(
            timestamp="2026-09-18T10:15:32",
            item="receive",
            answer="receive",
            correct=True,
            sentence="I received a gift.",
            feedback=None,
        )


def test_feedback_without_sentence_is_invalid():
    with pytest.raises(PracticeAttemptError):
        PracticeAttempt(
            timestamp="2026-09-18T10:15:32",
            item="receive",
            answer="receive",
            correct=True,
            sentence=None,
            feedback="already correct",
        )


def test_missing_required_field_is_invalid():
    with pytest.raises(PracticeAttemptError):
        PracticeAttempt(timestamp="", item="receive", answer="receive", correct=True)
