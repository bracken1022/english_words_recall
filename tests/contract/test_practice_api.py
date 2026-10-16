"""Contract tests for contracts/practice-api.md (spec 021): example
sentences after each answer, "New example", and the removed
sentence-review routes."""

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from src.models.account import Account
from src.web.app import create_app

VOCAB = (
    "---\nenglish: zealous\nchinese: 热心的\ngroup: unit1\n---\n\n"
    "---\nenglish: rent\nchinese: 租金\ngroup: unit1\n---\n"
)
SENTENCES = {
    "zealous": ["She is zealous about recycling.", "He was zealous in his work."],
    "rent": ["The rent is due on Friday.", "Our rent went up again."],
}


class FakeOllama:
    def __init__(self):
        self.down = False
        self.calls: dict[str, int] = {}

    def __call__(self, url, json=None, timeout=None):
        if self.down:
            raise requests.ConnectionError()
        word = re.search(r'English: "(.*)"', json["messages"][-1]["content"]).group(1)
        n = self.calls.get(word, 0)
        self.calls[word] = n + 1
        content = {"sentence": SENTENCES[word][n % 2], "translation": "这是一个例句。"}
        return _Resp(content)


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return {"message": {"content": json.dumps(self.payload, ensure_ascii=False)}}


@pytest.fixture
def ollama():
    fake = FakeOllama()
    with patch("src.services.llm_client.requests.post", side_effect=fake):
        yield fake


def _app(tmp_path: Path):
    vocab = tmp_path / "vocab"
    vocab.mkdir(exist_ok=True)
    (vocab / "unit1.md").write_text(VOCAB, encoding="utf-8")
    return create_app(
        vocab_dir=vocab,
        progress_file=tmp_path / "p.md",
        offer_choice=True,
        accounts=[Account("lily", "pw", "Lily", tmp_path / "pl.md")],
        word_lists_dir=tmp_path / "wl",
    )


def _client(app):
    client = app.test_client()
    client.post("/api/login", json={"username": "lily", "password": "pw"})
    return client


def _wait_ready(app, client):
    state = client.get("/api/state").get_json()
    for _ in range(50):
        if state.get("example_status") != "pending":
            break
        app.example_service.wait_all(0.2)
        state = client.get("/api/state").get_json()
    return state


@pytest.mark.parametrize("mode", ["example", "sentence", "bogus"])
def test_select_maps_modes(tmp_path, ollama, mode):
    client = _client(_app(tmp_path))
    state = client.post("/api/select", json={"collection": "unit1", "mode": mode}).get_json()
    assert state["step"] == "recall"
    client.post("/api/answer", json={"answer": "zealous"})
    assert client.get("/api/state").get_json()["mode"] == "example"


def test_reveal_carries_example(tmp_path, ollama):
    app = _app(tmp_path)
    client = _client(app)
    client.post("/api/select", json={"collection": "unit1", "mode": "example"})
    client.post("/api/answer", json={"answer": "zealous"})
    state = _wait_ready(app, client)
    assert state["step"] == "reveal"
    assert state["example_status"] == "ready"
    assert state["example"]["sentence"] == SENTENCES["zealous"][0]
    assert state["example"]["translation"] == "这是一个例句。"


def test_new_example_and_unavailable(tmp_path, ollama):
    app = _app(tmp_path)
    client = _client(app)
    client.post("/api/select", json={"collection": "unit1", "mode": "example"})
    client.post("/api/answer", json={"answer": "zealous"})
    _wait_ready(app, client)
    resp = client.post("/api/example/new")
    assert resp.status_code == 200
    assert resp.get_json()["example"]["sentence"] == SENTENCES["zealous"][1]
    ollama.down = True
    resp = client.post("/api/example/new")
    assert resp.status_code == 503
    assert resp.get_json() == {"error": "Couldn't make a new example right now."}
    assert client.get("/api/state").get_json()["example"]["sentence"] == SENTENCES["zealous"][1]


def test_new_example_wrong_step(tmp_path, ollama):
    client = _client(_app(tmp_path))
    assert client.post("/api/example/new").status_code == 409


# /api/transcribe came back in spec 022 (voice in sentence recall).
@pytest.mark.parametrize("route", ["/api/sentence", "/api/skip", "/api/retry-sentence"])
def test_removed_routes(tmp_path, ollama, route):
    assert _client(_app(tmp_path)).post(route, json={}).status_code == 404


def test_practice_works_without_model(tmp_path, ollama):
    ollama.down = True
    app = _app(tmp_path)
    client = _client(app)
    client.post("/api/select", json={"collection": "unit1", "mode": "example"})
    client.post("/api/answer", json={"answer": "zealous"})
    state = _wait_ready(app, client)
    assert (state["example"], state["example_status"]) == (None, "unavailable")
    assert client.post("/api/continue").get_json()["step"] == "recall"


# --- US2: POST /api/sentence-recall -----------------------------------------------


def _at_sentence_recall(app, client):
    client.post("/api/select", json={"collection": "unit1", "mode": "example-recall"})
    client.post("/api/answer", json={"answer": "zealous"})
    _wait_ready(app, client)
    return client.post("/api/continue").get_json()


def test_sentence_recall_withholds_then_reveals(tmp_path, ollama):
    app = _app(tmp_path)
    client = _client(app)
    state = _at_sentence_recall(app, client)
    assert state["step"] == "sentence-recall"
    assert state["example"] == {"sentence": None, "translation": "这是一个例句。"}
    assert SENTENCES["zealous"][0] not in json.dumps(client.get("/api/state").get_json())

    resp = client.post("/api/sentence-recall", json={"mark": "reveal"})
    assert resp.status_code == 200
    assert resp.get_json()["example"]["sentence"] == SENTENCES["zealous"][0]
    assert resp.get_json()["step"] == "sentence-recall"


def test_sentence_recall_mark_is_recorded(tmp_path, ollama):
    app = _app(tmp_path)
    client = _client(app)
    _at_sentence_recall(app, client)
    client.post("/api/sentence-recall", json={"mark": "reveal"})
    resp = client.post("/api/sentence-recall", json={"mark": "not_yet"})
    assert resp.status_code == 200
    assert resp.get_json()["step"] == "recall"
    assert "sentence_recall: not_yet" in (tmp_path / "pl.md").read_text(encoding="utf-8")


def test_sentence_recall_wrong_step(tmp_path, ollama):
    client = _client(_app(tmp_path))
    resp = client.post("/api/sentence-recall", json={"mark": "got"})
    assert resp.status_code == 409
    assert resp.get_json() == {"error": "Not recalling a sentence."}


@pytest.mark.parametrize("body", [{"mark": "maybe"}, {}, {"mark": 1}])
def test_sentence_recall_bad_mark(tmp_path, ollama, body):
    app = _app(tmp_path)
    client = _client(app)
    _at_sentence_recall(app, client)
    resp = client.post("/api/sentence-recall", json=body)
    assert resp.status_code == 400
    assert client.get("/api/state").get_json()["step"] == "sentence-recall"


# --- spec 022: the app starts without voice ---------------------------------------


def test_app_starts_without_the_voice_extra(tmp_path, ollama, monkeypatch):
    import sys

    from src.services import speech_client

    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    app = _app(tmp_path)
    assert _client(app).get("/api/state").status_code == 200
    assert speech_client.is_available() is False


def test_app_starts_when_preloading_fails(tmp_path, ollama, monkeypatch):
    from src.services import speech_client

    calls = []

    def broken():
        calls.append(1)
        raise OSError("model download failed")

    monkeypatch.setattr(speech_client, "is_available", lambda: True)
    monkeypatch.setattr(speech_client, "_get_model", broken)
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    (vocab / "unit1.md").write_text(VOCAB, encoding="utf-8")
    app = create_app(
        vocab_dir=vocab,
        progress_file=tmp_path / "p.md",
        offer_choice=True,
        accounts=[Account("lily", "pw", "Lily", tmp_path / "pl.md")],
        word_lists_dir=tmp_path / "wl",
        preload_voice=True,
    )
    speech_client.preload()  # what the startup thread runs: must not raise
    assert _client(app).get("/api/state").status_code == 200
    assert calls
