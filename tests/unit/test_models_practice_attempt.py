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


# --- spec 021: optional sentence-recall self-mark -------------------------------


def test_sentence_recall_mark():
    from src.models.practice_attempt import PracticeAttempt, PracticeAttemptError

    attempt = PracticeAttempt("2026-10-11T10:00:00+00:00", "zealous", "zealous", True, sentence_recall="got")
    assert attempt.sentence_recall == "got"
    PracticeAttempt("t", "x", "x", True, sentence_recall="not_yet")
    PracticeAttempt("t", "x", "x", True)
    with pytest.raises(PracticeAttemptError):
        PracticeAttempt("t", "x", "x", True, sentence_recall="maybe")


def test_old_block_with_sentence_feedback_still_loads():
    from src.models.practice_attempt import PracticeAttempt

    block = {"timestamp": "t", "item": "x", "answer": "x", "correct": True,
             "sentence": "I x.", "feedback": "Good."}  # fmt: skip
    attempt = PracticeAttempt.from_block(block)
    assert (attempt.sentence, attempt.feedback, attempt.sentence_recall) == ("I x.", "Good.", None)
