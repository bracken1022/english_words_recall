"""Showing the part of speech with the meaning (spec 019,
contracts/pos-display-contract.md)."""

from pathlib import Path

from src.cli.session import run_recall_step
from src.models.vocabulary_item import VocabularyItem
from src.web.app import create_app


def test_web_state_has_pos_during_recall(tmp_path: Path):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: rent\npos: n. v.\nchinese: 租金；出租\n---\n", encoding="utf-8"
    )
    client = create_app(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md").test_client()
    assert client.get("/api/state").get_json()["pos"] == ["n.", "v."]


def test_cli_prints_labels_before_meaning(capsys):
    run_recall_step(VocabularyItem("zealous", "热心的", pos=["adj."]), answer_input=lambda: "x")
    assert "Chinese meaning: adj. 热心的" in capsys.readouterr().out.splitlines()


def test_cli_without_labels_is_unchanged(capsys):
    run_recall_step(VocabularyItem("zealous", "热心的"), answer_input=lambda: "x")
    assert "Chinese meaning: 热心的" in capsys.readouterr().out.splitlines()
