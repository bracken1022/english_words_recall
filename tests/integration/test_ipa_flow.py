"""Showing IPA pronunciations after a word is revealed (spec 017,
contracts/ipa-display-contract.md)."""

from pathlib import Path

from src.cli.session import run_recall_step
from src.models.vocabulary_item import VocabularyItem
from src.web.app import create_app
from tests.fake_examples import FakeExampleService


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


def test_cli_pronunciation_comes_before_the_example(capsys):
    # Spec 021 replaced the sentence prompt (which carried the IPA) with
    # the example sentence, shown after the pronunciation.
    run_recall_step(
        VocabularyItem("receive", "收到", ipa="rɪˈsiːv"),
        answer_input=lambda: "receive",
        examples=FakeExampleService(),
    )
    out = capsys.readouterr().out
    assert out.index("Pronunciation: /rɪˈsiːv/") < out.index("Example: ")
