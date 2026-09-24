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


@patch("src.cli.session.random.shuffle")
@patch("src.cli.session.request_correction")
def test_random_order_shuffles_the_filtered_pool(mock_request, mock_shuffle, tmp_path: Path, monkeypatch):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "sentence one.", "give up", "sentence two."])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, order="random")

    mock_shuffle.assert_called_once()


@patch("src.cli.session.random.shuffle")
@patch("src.cli.session.request_correction")
def test_sequential_order_never_shuffles(mock_request, mock_shuffle, tmp_path: Path, monkeypatch):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "sentence one.", "give up", "sentence two."])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, order="sequential")

    mock_shuffle.assert_not_called()


@patch("src.cli.session.random.shuffle")
@patch("src.cli.session.request_correction")
def test_default_order_never_shuffles(mock_request, mock_shuffle, tmp_path: Path, monkeypatch):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "sentence one.", "give up", "sentence two."])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    mock_shuffle.assert_not_called()


@patch("src.cli.session.request_correction")
def test_random_order_still_presents_every_word_exactly_once(mock_request, tmp_path: Path, monkeypatch):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "sentence one.", "give up", "sentence two."])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, order="random")

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "item: give up" in text
