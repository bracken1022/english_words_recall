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
