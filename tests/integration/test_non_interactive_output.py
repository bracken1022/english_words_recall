"""Non-interactive output fallback per quickstart.md Scenario 3 (spec 002):
when the console isn't an interactive terminal, the indicator falls back to
one plain message instead of animating, and the app still completes
normally. Spec 021: the indicator now covers writing an example."""

import io
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from src.cli import session as session_module
from src.cli.session import run_session
from tests.fake_examples import FakeExampleService


@patch("src.cli.session.ExampleService", FakeExampleService)
def test_non_interactive_session_shows_fallback_message_and_completes(tmp_path: Path, monkeypatch):
    buffer = io.StringIO()
    non_terminal_console = Console(file=buffer, force_terminal=False)
    monkeypatch.setattr(session_module, "console", non_terminal_console)

    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    progress_file = tmp_path / "progress.md"

    answers = iter(["receive", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    output = buffer.getvalue()
    assert "\x1b[" not in output  # no ANSI/spinner escape codes leaked into non-tty output
    assert "Writing an example..." in output  # the one-line fallback message
    assert "Example: I received a gift from my aunt." in output

    # and the practice attempt was still recorded correctly (learning behavior unchanged)
    progress_text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in progress_text
    assert "correct: true" in progress_text
