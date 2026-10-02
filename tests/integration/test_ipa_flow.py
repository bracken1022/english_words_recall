"""Showing IPA pronunciations after a word is revealed (spec 017,
contracts/ipa-display-contract.md)."""

from pathlib import Path
from unittest.mock import patch

from src.cli import session as cli_session
from src.cli.session import run_recall_step, run_sentence_step
from src.models.vocabulary_item import VocabularyItem
from src.services.llm_client import CorrectionResult
from src.web.app import create_app


def _client(tmp_path: Path):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: receive\nipa: rɪˈsiːv\nchinese: 收到\n---\n", encoding="utf-8"
    )
    app = create_app(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    return app.test_client()


def test_web_ipa_appears_only_after_answer(tmp_path: Path):
    client = _client(tmp_path)
    assert "ipa" not in client.get("/api/state").get_json()
    client.post("/api/answer", json={"answer": "wrong"})
    assert client.get("/api/state").get_json()["ipa"] == "rɪˈsiːv"


def test_cli_prints_pronunciation_after_answer(capsys):
    run_recall_step(VocabularyItem("receive", "收到", ipa="rɪˈsiːv"), answer_input=lambda: "x")
    lines = capsys.readouterr().out.splitlines()
    assert "/rɪˈsiːv/" not in lines[0]
    assert "Pronunciation: /rɪˈsiːv/" in lines


def test_cli_without_ipa_prints_no_pronunciation(capsys):
    run_recall_step(VocabularyItem("receive", "收到"), answer_input=lambda: "receive")
    assert "Pronunciation" not in capsys.readouterr().out


@patch("src.cli.session.request_correction")
def test_sentence_prompt_shows_ipa(mock_request, capsys):
    mock_request.return_value = CorrectionResult(
        available=False,
        uses_expression=None,
        needs_correction=None,
        corrected=None,
        explanation=None,
    )
    run_sentence_step("receive", sentence_input=lambda: "I got it.", ipa="rɪˈsiːv")
    assert 'Write a sentence using "receive" /rɪˈsiːv/:' in capsys.readouterr().out
    run_sentence_step("receive", sentence_input=lambda: "I got it.")
    assert 'Write a sentence using "receive":' in capsys.readouterr().out


def test_run_session_passes_ipa_to_sentence_step(tmp_path: Path, monkeypatch):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: receive\nipa: rɪˈsiːv\nchinese: 收到\n---\n", encoding="utf-8"
    )
    captured = {}

    def fake_sentence_step(target, **kwargs):
        captured.update(kwargs)
        return "I got it.", "already correct"

    monkeypatch.setattr(cli_session, "run_sentence_step", fake_sentence_step)
    monkeypatch.setattr("builtins.input", lambda *_: "receive")
    cli_session.run_session(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md")
    assert captured["ipa"] == "rɪˈsiːv"
