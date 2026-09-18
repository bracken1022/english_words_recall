from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from src.services.llm_client import CorrectionResult


@patch("src.cli.session.request_correction")
def test_group_filter_only_practices_matching_items(mock_request, tmp_path: Path, monkeypatch):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )

    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "all.md").write_text(
        "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
        "---\nenglish: give up\nchinese: 放弃\ngroup: unit2\n---\n"
    )
    progress_file = tmp_path / "progress.md"

    answers = iter(["receive", "I received a gift."])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, group="unit1")

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "give up" not in text


def test_no_filter_practices_all_items(tmp_path: Path, monkeypatch):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "all.md").write_text(
        "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
        "---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    progress_file = tmp_path / "progress.md"

    with patch("src.cli.session.request_correction") as mock_request:
        mock_request.return_value = CorrectionResult(
            available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
        )
        answers = iter(["receive", "sentence one.", "give up", "sentence two."])
        monkeypatch.setattr("builtins.input", lambda *_: next(answers))
        run_session(vocab_dir=vocab_dir, progress_file=progress_file, group=None)

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "item: give up" in text
