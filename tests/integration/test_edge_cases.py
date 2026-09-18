from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from src.services.llm_client import CorrectionResult


def test_empty_vocabulary_pool_shows_message_and_does_not_start(tmp_path: Path, capsys):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    progress_file = tmp_path / "progress.md"

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    out = capsys.readouterr().out
    assert "no vocabulary items available" in out.lower()
    assert not progress_file.exists()


@patch("src.cli.session.request_correction")
def test_extremely_long_sentence_does_not_crash(mock_request, tmp_path: Path, monkeypatch):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )

    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    progress_file = tmp_path / "progress.md"

    long_sentence = "I received a gift " * 2000
    answers = iter(["receive", long_sentence])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
