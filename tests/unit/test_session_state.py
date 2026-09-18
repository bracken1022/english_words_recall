from pathlib import Path

import pytest

from src.web.session_state import PracticeSession, WrongStepError


def _write_vocab(tmp_path: Path) -> Path:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    return vocab_dir


def test_empty_pool_starts_in_empty_step(tmp_path: Path):
    vocab_dir = tmp_path / "empty_vocab"
    vocab_dir.mkdir()
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert session.step == "empty"
    assert session.items == []


def test_non_empty_pool_starts_in_recall_step_at_index_zero(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert session.step == "recall"
    assert session.current_index == 0
    assert len(session.items) == 2


def test_submit_answer_advances_to_sentence_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    result = session.submit_answer("receive")
    assert result["correct"] is True
    assert session.step == "sentence"


def test_submit_answer_rejected_when_not_in_recall_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    with pytest.raises(WrongStepError):
        session.submit_answer("receive")


def test_continue_rejected_from_recall_and_sentence(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    with pytest.raises(WrongStepError):
        session.continue_to_next()
    session.submit_answer("receive")
    with pytest.raises(WrongStepError):
        session.continue_to_next()


def test_current_index_never_decreases_and_ends_in_complete(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")

    session.submit_answer("receive")
    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    assert session.current_index == 0
    session.continue_to_next()
    assert session.current_index == 1
    assert session.step == "recall"

    session.submit_answer("give up")
    session.submit_sentence("I gave up.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    session.continue_to_next()
    assert session.current_index == 2
    assert session.step == "complete"


def test_continue_from_complete_is_a_no_op(tmp_path: Path):
    vocab_dir = tmp_path / "one_item"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    session.continue_to_next()
    assert session.step == "complete"
    session.continue_to_next()  # no-op, must not raise
    assert session.step == "complete"


def _stub():
    from src.services.llm_client import CorrectionResult

    return CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
