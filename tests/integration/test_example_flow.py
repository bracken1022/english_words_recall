"""Example sentences end to end (spec 021): saved into a learner's own
list on first sight and reused later; shown by the command-line tutor."""

import io
from unittest.mock import patch

from src.cli.session import run_recall_step
from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem
from src.web.app import create_app
from tests.contract.test_practice_api import SENTENCES, FakeOllama, _wait_ready


def test_own_list_example_saved_and_reused(tmp_path):
    fake = FakeOllama()
    with patch("src.services.llm_client.requests.post", side_effect=fake):
        vocab = tmp_path / "vocab"
        vocab.mkdir()
        app = create_app(
            vocab_dir=vocab, progress_file=tmp_path / "p.md", offer_choice=True,
            accounts=[Account("lily", "pw", "Lily", tmp_path / "pl.md")],
            word_lists_dir=tmp_path / "wl",
        )  # fmt: skip
        client = app.test_client()
        client.post("/api/login", json={"username": "lily", "password": "pw"})
        data = {"file": (io.BytesIO("zealous, 热心的\nrent, 租金\n".encode()), "unit1.csv")}
        client.post("/api/word-lists", data=data, content_type="multipart/form-data")
        client.post("/api/select", json={"collection": "unit1", "mode": "example"})
        client.post("/api/answer", json={"answer": "zealous"})
        state = _wait_ready(app, client)
        assert state["example"]["sentence"] == SENTENCES["zealous"][0]
        text = (tmp_path / "wl" / "lily" / "unit1.md").read_text(encoding="utf-8")
        assert "example: She is zealous about recycling." in text

        calls = dict(fake.calls)
        client.post("/api/end")
        client.post("/api/select", json={"collection": "unit1", "mode": "example"})
        client.post("/api/answer", json={"answer": "zealous"})
        state = client.get("/api/state").get_json()
        assert state["example"]["sentence"] == SENTENCES["zealous"][0]
        assert fake.calls.get("zealous") == calls.get("zealous")


class _Examples:
    def __init__(self, example):
        self.example = example

    def get_or_make(self, item, timeout):
        return self.example


def test_cli_prints_example(capsys):
    item = VocabularyItem("zealous", "热心的")
    example = {"sentence": "She is zealous about recycling.", "translation": "她热衷于回收利用。"}
    run_recall_step(item, answer_input=lambda: "zealous", examples=_Examples(example))
    out = capsys.readouterr().out.splitlines()
    assert "Example: She is zealous about recycling." in out
    assert any(line.strip() == "她热衷于回收利用。" for line in out)


def test_cli_without_example(capsys):
    run_recall_step(VocabularyItem("zealous", "热心的"), answer_input=lambda: "x", examples=_Examples(None))
    assert "(No example right now.)" in capsys.readouterr().out


def test_cli_recall_only_prints_no_example(capsys):
    run_recall_step(VocabularyItem("zealous", "热心的"), answer_input=lambda: "x")
    assert "Example" not in capsys.readouterr().out


# --- US2: sentence recall in the command-line tutor ------------------------------


def _run_example_recall(tmp_path, monkeypatch, inputs, service=None):
    from src.cli.session import run_session
    from tests.fake_examples import FakeExampleService

    vocab = tmp_path / "vocab"
    vocab.mkdir()
    (vocab / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n", encoding="utf-8")
    progress = tmp_path / "p.md"
    answers = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    service = service or FakeExampleService()
    with patch("src.cli.session.ExampleService", lambda *a, **k: service):
        run_session(vocab_dir=vocab, progress_file=progress, mode="example-recall")
    assert next(answers, None) is None, "every scripted input was used"
    return progress.read_text(encoding="utf-8")


def test_cli_sentence_recall_got_it(tmp_path, monkeypatch, capsys):
    # answer, continue, show the sentence, "yes I got it"
    log = _run_example_recall(tmp_path, monkeypatch, ["receive", "", "", "y"])
    out = capsys.readouterr().out
    assert "Recall the sentence: 我收到了姨妈的礼物。" in out
    assert "sentence_recall: got" in log


def test_cli_sentence_recall_not_yet(tmp_path, monkeypatch):
    log = _run_example_recall(tmp_path, monkeypatch, ["receive", "", "", "maybe", "n"])
    assert "sentence_recall: not_yet" in log


def test_cli_sentence_recall_skip(tmp_path, monkeypatch):
    log = _run_example_recall(tmp_path, monkeypatch, ["receive", "", "s"])
    assert "item: receive" in log
    assert "sentence_recall" not in log


def test_cli_sentence_recall_without_example(tmp_path, monkeypatch, capsys):
    from tests.fake_examples import FakeExampleService

    log = _run_example_recall(
        tmp_path, monkeypatch, ["receive", ""], service=FakeExampleService(example=None)
    )
    assert "Recall the sentence" not in capsys.readouterr().out
    assert "sentence_recall" not in log
