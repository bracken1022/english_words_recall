from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from src.services.llm_client import CorrectionResult


def _write_two_item_vocab(tmp_path: Path) -> Path:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "all.md").write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    return vocab_dir


@patch("src.cli.session.request_correction")
def test_recall_only_mode_never_requests_correction(mock_request, tmp_path: Path, monkeypatch):
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "give up"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    mock_request.assert_not_called()


@patch("src.cli.session.request_correction")
def test_recall_only_mode_records_every_word_without_sentence_or_feedback(
    mock_request, tmp_path: Path, monkeypatch
):
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "give up"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "item: give up" in text
    assert "sentence:" not in text
    assert "feedback:" not in text


@patch("src.cli.session.request_correction")
def test_sentence_mode_default_still_requests_correction_per_word(
    mock_request, tmp_path: Path, monkeypatch
):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "sentence one.", "give up", "sentence two."])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    assert mock_request.call_count == 2
    text = progress_file.read_text(encoding="utf-8")
    assert "sentence: sentence one." in text
    assert "sentence: sentence two." in text


@patch("src.cli.session.request_correction")
def test_recall_only_wrong_answer_waits_for_an_extra_confirmation(
    mock_request, tmp_path: Path, monkeypatch
):
    """Spec 013: a wrong recall-only answer must block on one extra
    input() call (the "press Enter to continue" pause) before the
    session moves on to the next word."""
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    # "wrong" (incorrect answer), "" (the confirmation pause), "give up" (correct, no pause needed)
    answers = iter(["wrong", "", "give up"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "answer: wrong" in text
    assert "correct: false" in text
    assert "item: give up" in text
    # Only if the confirmation pause actually consumed the blank input()
    # value did "give up" (not "") land as the second item's real answer.
    assert "answer: give up" in text
    mock_request.assert_not_called()


@patch("src.cli.session.request_correction")
def test_recall_only_correct_answer_needs_no_extra_confirmation(
    mock_request, tmp_path: Path, monkeypatch
):
    """Regression guard: a correct recall-only answer must NOT consume an
    extra input() value — only one scripted answer per word is needed."""
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "give up"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "item: give up" in text
