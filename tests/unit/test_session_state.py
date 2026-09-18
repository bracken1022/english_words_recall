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


def test_state_omits_answer_and_correct_for_recall_empty_complete(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert "answer" not in session.state()
    assert "correct" not in session.state()

    empty_dir = tmp_path / "empty_vocab"
    empty_dir.mkdir()
    empty_session = PracticeSession(vocab_dir=empty_dir, progress_file=tmp_path / "p2.md")
    assert "answer" not in empty_session.state()
    assert "correct" not in empty_session.state()


def test_state_includes_answer_and_correct_for_sentence_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("wrong")
    state = session.state()
    assert state["step"] == "sentence"
    assert state["answer"] == "wrong"
    assert state["correct"] is False


def test_state_includes_answer_and_correct_for_feedback_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    state = session.state()
    assert state["step"] == "feedback"
    assert state["answer"] == "receive"
    assert state["correct"] is True


def test_concurrent_sentence_submission_is_rejected(tmp_path: Path):
    """Simulates 'a second request arrives while the first is still
    running' deterministically: correction_fn re-enters submit_sentence on
    the same session before returning (research.md)."""
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")

    inner_raised = {}

    def reentrant_correction(*args, **kwargs):
        try:
            session.submit_sentence("a second sentence", base_url="x", model="m")
        except WrongStepError as exc:
            inner_raised["error"] = exc
        return _stub()

    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=reentrant_correction)

    assert "error" in inner_raised
    assert session.step == "feedback"  # the original (outer) call still completed normally
