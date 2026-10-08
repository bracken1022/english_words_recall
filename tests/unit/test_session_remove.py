"""PracticeSession.remove_current / undo_remove (spec 020, research R5):
removing the current word moves the session on, keeps any attempt already
made, and can be undone only until the next action."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.llm_client import CorrectionResult
from src.web.session_state import PracticeSession, WrongStepError

VOCAB = (
    "---\nenglish: zealous\nchinese: 热心的\ngroup: unit1\n---\n\n"
    "---\nenglish: rent\nchinese: 租金\ngroup: unit1\n---\n\n"
    "---\nenglish: tyre\nchinese: 轮胎\ngroup: unit1\n---\n"
)


def _session(tmp_path: Path, **kwargs) -> PracticeSession:
    vocab = tmp_path / "vocab"
    vocab.mkdir(exist_ok=True)
    (vocab / "unit1.md").write_text(VOCAB, encoding="utf-8")
    return PracticeSession(vocab_dir=vocab, progress_file=tmp_path / "progress.md", **kwargs)


class Recorder:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def __call__(self, item):
        if self.error:
            raise self.error
        self.calls.append(item.english)
        return f"token-{item.english}"


def _log(tmp_path):
    path = tmp_path / "progress.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def test_remove_at_recall_moves_on_without_recording(tmp_path):
    session = _session(tmp_path)
    remove = Recorder()
    assert session.remove_current(remove) == {"english": "zealous", "chinese": "热心的"}
    assert remove.calls == ["zealous"]
    assert session.step == "recall"
    assert session.current_item.english == "rent"
    assert [i.english for i in session.items] == ["rent", "tyre"]
    assert [i.english for i in session.all_items] == ["rent", "tyre"]
    assert session.correct_count == 0
    assert _log(tmp_path) == ""


def test_remove_at_reveal_logs_the_held_attempt(tmp_path):
    session = _session(tmp_path, mode="recall-only")
    session.submit_answer("wrong")
    assert session.step == "reveal"
    session.remove_current(Recorder())
    assert "zealous" in _log(tmp_path)
    assert session.current_item.english == "rent"


@patch("src.web.session_state.request_correction")
def test_remove_at_sentence_logs_like_skip(mock_request, tmp_path):
    session = _session(tmp_path)
    session.submit_answer("zealous")
    assert session.step == "sentence"
    session.remove_current(Recorder())
    assert "zealous" in _log(tmp_path)
    assert session.correct_count == 1
    assert session.step == "recall"


def test_removing_last_word_completes(tmp_path):
    session = _session(tmp_path)
    for _ in range(3):
        session.remove_current(Recorder())
    assert session.step == "complete"
    assert session.items == []


@pytest.mark.parametrize("setup", ["choose", "complete", "empty"])
def test_wrong_steps_raise(tmp_path, setup):
    if setup == "choose":
        session = _session(tmp_path, offer_choice=True)
    elif setup == "empty":
        (tmp_path / "none").mkdir()
        session = PracticeSession(vocab_dir=tmp_path / "none", progress_file=tmp_path / "p.md")
    else:
        session = _session(tmp_path, mode="recall-only")
        while session.step != "complete":
            session.submit_answer("x")
            session.continue_to_next()
    remove = Recorder()
    with pytest.raises(WrongStepError):
        session.remove_current(remove)
    assert remove.calls == []


@patch("src.web.session_state.request_correction")
def test_wrong_step_feedback(mock_request, tmp_path):
    mock_request.return_value = CorrectionResult(True, True, False, None, None)
    session = _session(tmp_path)
    session.submit_answer("zealous")
    session.submit_sentence("I am zealous.", base_url="x", model="m")
    assert session.step == "feedback"
    with pytest.raises(WrongStepError):
        session.remove_current(Recorder())


def test_failed_removal_leaves_session_unchanged(tmp_path):
    session = _session(tmp_path)
    with pytest.raises(OSError):
        session.remove_current(Recorder(error=OSError("disk full")))
    assert session.current_item.english == "zealous"
    assert len(session.items) == 3
    assert session.pending_undo is None


def test_item_filter_applies_on_every_load(tmp_path):
    def drop_rent(items):
        return [i for i in items if i.english != "rent"]

    session = _session(tmp_path, offer_choice=True, item_filter=drop_rent)
    assert [i.english for i in session.all_items] == ["zealous", "tyre"]
    session.select_collection("unit1", order="sequential", mode="recall-only")
    session.end_session()
    assert [i.english for i in session.all_items] == ["zealous", "tyre"]
    session.set_vocab_dir(session.vocab_dir)
    assert [i.english for i in session.all_items] == ["zealous", "tyre"]
    session.select_collection("unit1", order="sequential", mode="recall-only")
    while session.step != "complete":
        session.submit_answer("x")
        session.continue_to_next()
    session.restart()
    assert [i.english for i in session.all_items] == ["zealous", "tyre"]


# --- US2: undo straight away ---------------------------------------------------


def test_undo_restores_word_as_current(tmp_path):
    session = _session(tmp_path)
    session.remove_current(Recorder())
    restored = []
    session.undo_remove(restored.append)
    assert restored == ["token-zealous"]
    assert session.step == "recall"
    assert session.current_item.english == "zealous"
    assert [i.english for i in session.items] == ["zealous", "rent", "tyre"]
    assert [i.english for i in session.all_items] == ["zealous", "rent", "tyre"]
    assert session.pending_undo is None


def test_undo_after_completing(tmp_path):
    session = _session(tmp_path, offer_choice=True)
    session.select_collection("unit1", mode="recall-only")
    for _ in range(3):
        session.remove_current(Recorder())
    assert session.step == "complete"
    session.undo_remove(lambda _t: None)
    assert (session.step, session.current_item.english) == ("recall", "tyre")
    assert [i.english for i in session.all_items] == ["tyre"]


def test_undo_with_nothing_pending(tmp_path):
    with pytest.raises(WrongStepError):
        _session(tmp_path).undo_remove(lambda _t: None)


def test_undo_window_closes_on_next_action(tmp_path):
    session = _session(tmp_path, mode="recall-only")
    session.remove_current(Recorder())
    session.submit_answer("rent")
    with pytest.raises(WrongStepError):
        session.undo_remove(lambda _t: None)


def test_failed_undo_leaves_session_unchanged(tmp_path):
    session = _session(tmp_path)
    session.remove_current(Recorder())

    def boom(_token):
        raise OSError("disk full")

    with pytest.raises(OSError):
        session.undo_remove(boom)
    assert session.current_item.english == "rent"
    assert session.pending_undo is not None
