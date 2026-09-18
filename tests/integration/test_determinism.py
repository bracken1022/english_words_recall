"""The learning state machine (grading, item order) must be identical
regardless of what Ollama returns — Ollama only evaluates language quality,
it never controls lesson progression (quickstart.md Scenario 6)."""

from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from src.services.llm_client import CorrectionResult


def _run(vocab_dir: Path, progress_file: Path, monkeypatch, correction_result: CorrectionResult) -> str:
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    answers = iter(["receive", "sentence one.", "wrong", "sentence two."])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    with patch("src.cli.session.request_correction") as mock_request:
        mock_request.return_value = correction_result
        run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    return progress_file.read_text(encoding="utf-8")


def _grading_and_order(progress_text: str) -> list[tuple[str, str]]:
    """Extract (item, correct) pairs in log order, ignoring feedback text."""
    pairs = []
    item = None
    for line in progress_text.splitlines():
        line = line.strip()
        if line.startswith("item:"):
            item = line.split(":", 1)[1].strip()
        elif line.startswith("correct:"):
            pairs.append((item, line.split(":", 1)[1].strip()))
    return pairs


def test_grading_and_order_identical_regardless_of_llm_verdict(tmp_path: Path, monkeypatch):
    needs_correction = CorrectionResult(
        available=True, uses_expression=True, needs_correction=True, corrected="X", explanation="Y"
    )
    already_correct = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )

    run_a = tmp_path / "a"
    run_a.mkdir()
    text_a = _run(run_a, run_a / "progress.md", monkeypatch, needs_correction)

    run_b = tmp_path / "b"
    run_b.mkdir()
    text_b = _run(run_b, run_b / "progress.md", monkeypatch, already_correct)

    assert _grading_and_order(text_a) == _grading_and_order(text_b) == [
        ("receive", "true"),
        ("give up", "false"),
    ]
    # The feedback text is the only thing allowed to differ between the two runs.
    assert "corrected: X" in text_a
    assert "already correct" in text_b


def test_grading_and_order_identical_when_llm_unavailable(tmp_path: Path, monkeypatch):
    already_correct = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    unavailable = CorrectionResult(
        available=False, uses_expression=None, needs_correction=None, corrected=None, explanation=None
    )

    run_a = tmp_path / "a"
    run_a.mkdir()
    text_a = _run(run_a, run_a / "progress.md", monkeypatch, already_correct)

    run_b = tmp_path / "b"
    run_b.mkdir()
    text_b = _run(run_b, run_b / "progress.md", monkeypatch, unavailable)

    assert _grading_and_order(text_a) == _grading_and_order(text_b)
