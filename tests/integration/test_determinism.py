"""The learning state machine (grading, item order) must be identical
regardless of what the local model returns — it only writes example
sentences, it never controls lesson progression (quickstart.md Scenario 6;
spec 021 replaced sentence review with examples)."""

from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from tests.fake_examples import FakeExampleService, no_examples


def _run(vocab_dir: Path, progress_file: Path, monkeypatch, service) -> str:
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    answers = iter(["receive", "", "wrong", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    with patch("src.cli.session.ExampleService", service):
        run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    return progress_file.read_text(encoding="utf-8")


def _grading_and_order(progress_text: str) -> list[tuple[str, str]]:
    """Extract (item, correct) pairs in log order."""
    pairs = []
    item = None
    for line in progress_text.splitlines():
        line = line.strip()
        if line.startswith("item:"):
            item = line.split(":", 1)[1].strip()
        elif line.startswith("correct:"):
            pairs.append((item, line.split(":", 1)[1].strip()))
    return pairs


def test_grading_and_order_identical_with_or_without_examples(tmp_path: Path, monkeypatch):
    run_a = tmp_path / "a"
    run_a.mkdir()
    text_a = _run(run_a, run_a / "progress.md", monkeypatch, FakeExampleService)

    run_b = tmp_path / "b"
    run_b.mkdir()
    text_b = _run(run_b, run_b / "progress.md", monkeypatch, no_examples)

    assert _grading_and_order(text_a) == _grading_and_order(text_b) == [
        ("receive", "true"),
        ("give up", "false"),
    ]
