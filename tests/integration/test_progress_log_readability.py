from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from tests.fake_examples import FakeExampleService


@patch("src.cli.session.ExampleService", FakeExampleService)
def test_progress_log_readable_after_full_attempt(tmp_path: Path, monkeypatch):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    progress_file = tmp_path / "progress.md"

    answers = iter(["receive", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "answer: receive" in text
    assert "correct: true" in text
    # Spec 021: no reviewed sentence any more.
    assert "sentence:" not in text
    assert "feedback:" not in text
