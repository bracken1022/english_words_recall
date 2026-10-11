from pathlib import Path

from src.models.practice_attempt import PracticeAttempt
from src.services.progress_log import append_attempt, read_attempts


def test_appended_attempt_round_trips(tmp_path: Path):
    progress_file = tmp_path / "progress.md"
    attempt = PracticeAttempt(
        timestamp="2026-09-18T10:15:32",
        item="receive",
        answer="recieve",
        correct=False,
        sentence="I recieve a gift.",
        feedback="corrected: I received a gift.",
    )
    append_attempt(progress_file, attempt)

    attempts, warnings = read_attempts(progress_file)
    assert warnings == []
    assert len(attempts) == 1
    assert attempts[0] == attempt


def test_multiple_appends_preserve_order(tmp_path: Path):
    progress_file = tmp_path / "progress.md"
    first = PracticeAttempt(timestamp="t1", item="receive", answer="receive", correct=True)
    second = PracticeAttempt(timestamp="t2", item="give up", answer="", correct=False)
    append_attempt(progress_file, first)
    append_attempt(progress_file, second)

    attempts, warnings = read_attempts(progress_file)
    assert warnings == []
    assert [a.item for a in attempts] == ["receive", "give up"]


def test_malformed_block_skipped_rest_still_readable(tmp_path: Path):
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """
---
timestamp: t1
item: receive
---

---
timestamp: t2
item: give up
answer: ''
correct: false
---
"""
    )
    attempts, warnings = read_attempts(progress_file)
    assert len(warnings) == 1
    assert len(attempts) == 1
    assert attempts[0].item == "give up"


def test_read_missing_file_returns_empty(tmp_path: Path):
    attempts, warnings = read_attempts(tmp_path / "missing.md")
    assert attempts == []
    assert warnings == []


# --- spec 021: sentence_recall ---------------------------------------------------


def test_sentence_recall_round_trips(tmp_path: Path):
    log = tmp_path / "progress.md"
    append_attempt(log, PracticeAttempt("t1", "zealous", "zealous", True, sentence_recall="got"))
    append_attempt(log, PracticeAttempt("t2", "rent", "rent", False))
    attempts, warnings = read_attempts(log)
    assert warnings == []
    assert [a.sentence_recall for a in attempts] == ["got", None]
    assert "sentence_recall" not in log.read_text(encoding="utf-8").split("t2")[1]
