from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from tests.fake_examples import FakeExampleService


def test_empty_vocabulary_pool_shows_message_and_does_not_start(tmp_path: Path, capsys):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    progress_file = tmp_path / "progress.md"

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    out = capsys.readouterr().out
    assert "no vocabulary items available" in out.lower()
    assert not progress_file.exists()


@patch("src.cli.session.ExampleService", FakeExampleService)
def test_extremely_long_answer_does_not_crash(tmp_path: Path, monkeypatch):
    # Spec 021 replaced the long-*sentence* case (sentence review is gone):
    # an absurdly long typed answer must still be graded and logged.
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    progress_file = tmp_path / "progress.md"

    answers = iter(["I received a gift " * 2000, ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "correct: false" in text
