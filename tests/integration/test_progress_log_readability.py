from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from src.services.llm_client import CorrectionResult


@patch("src.cli.session.request_correction")
def test_progress_log_readable_after_full_attempt(mock_request, tmp_path: Path, monkeypatch):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )

    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    progress_file = tmp_path / "progress.md"

    answers = iter(["receive", "I received a gift."])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "answer: receive" in text
    assert "correct: true" in text
    assert "sentence: I received a gift." in text
    assert "feedback: already correct" in text
