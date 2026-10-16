"""Contract tests for spec 022 contracts/practice-api.md: voice input in
sentence recall (POST /api/transcribe) and the attempt comparison on
reveal. The recogniser is faked; no real model is loaded."""

from pathlib import Path

import pytest

from src.services import speech_client
from src.services.speech_client import TranscriptionResult
from tests.contract import test_practice_api
from tests.contract.test_practice_api import _app, _at_sentence_recall, _client

ollama = test_practice_api.ollama  # every test here runs with the fake model
pytestmark = pytest.mark.usefixtures("ollama")

SENTENCE = "She is zealous about recycling."


class FakeRecogniser:
    def __init__(self, result=None):
        self.result = result or TranscriptionResult("ok", "She is zelous about recycling")
        self.calls: list[bytes] = []

    def __call__(self, audio):
        self.calls.append(audio)
        return self.result


@pytest.fixture
def recogniser(monkeypatch):
    fake = FakeRecogniser()
    monkeypatch.setattr(speech_client, "transcribe", fake)
    monkeypatch.setattr(speech_client, "is_available", lambda: True)
    return fake


def _post_audio(client, data=b"fake-webm-bytes", content_type="audio/webm"):
    return client.post("/api/transcribe", data=data, content_type=content_type)


def _ready(tmp_path: Path):
    app = _app(tmp_path)
    client = _client(app)
    state = _at_sentence_recall(app, client)
    assert state["step"] == "sentence-recall"
    return client, state


# --- US1 --------------------------------------------------------------------------


def test_transcribe_at_sentence_recall(tmp_path, recogniser):
    client, _state = _ready(tmp_path)
    before = client.get("/api/state").get_json()
    resp = _post_audio(client)
    assert resp.status_code == 200
    assert resp.get_json() == {"outcome": "ok", "text": "She is zelous about recycling"}
    assert recogniser.calls == [b"fake-webm-bytes"]
    assert client.get("/api/state").get_json() == before


def test_state_reports_voice_available(tmp_path, recogniser):
    state = _ready(tmp_path)[1]
    assert state["voice_available"] is True


def test_reveal_with_attempt_returns_comparison(tmp_path, recogniser):
    client, _state = _ready(tmp_path)
    resp = client.post(
        "/api/sentence-recall", json={"mark": "reveal", "attempt": "She is zelous about recycling"}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["example"]["sentence"] == SENTENCE
    assert data["comparison"]["sentence"] == [
        {"word": "She", "status": "same"},
        {"word": "is", "status": "same"},
        {"word": "zealous", "status": "missing"},
        {"word": "about", "status": "same"},
        {"word": "recycling.", "status": "same"},
    ]
    assert {"word": "zelous", "status": "extra"} in data["comparison"]["attempt"]
    assert "comparison" not in client.get("/api/state").get_json()


@pytest.mark.parametrize("body", [{"mark": "reveal"}, {"mark": "reveal", "attempt": "   "}])
def test_reveal_without_attempt_has_null_comparison(tmp_path, recogniser, body):
    client, _state = _ready(tmp_path)
    data = client.post("/api/sentence-recall", json=body).get_json()
    assert data["comparison"] is None
    assert data["sentence_revealed"] is True


@pytest.mark.parametrize("attempt", [3, ["a"], "x" * 1001], ids=["number", "list", "too-long"])
def test_reveal_rejects_bad_attempt(tmp_path, recogniser, attempt):
    client, _state = _ready(tmp_path)
    resp = client.post("/api/sentence-recall", json={"mark": "reveal", "attempt": attempt})
    assert resp.status_code == 400
    assert client.get("/api/state").get_json()["sentence_revealed"] is False


def test_attempt_at_the_limit_is_accepted(tmp_path, recogniser):
    client, _state = _ready(tmp_path)
    resp = client.post("/api/sentence-recall", json={"mark": "reveal", "attempt": "x" * 1000})
    assert resp.status_code == 200


def test_transcribe_needs_login(tmp_path, recogniser):
    client = _app(tmp_path).test_client()
    assert _post_audio(client).status_code == 401
    assert recogniser.calls == []


# --- US2: practice still works without voice --------------------------------------


@pytest.fixture
def no_voice(monkeypatch):
    monkeypatch.setattr(speech_client, "is_available", lambda: False)


@pytest.mark.usefixtures("no_voice")
def test_not_installed_reports_unavailable(tmp_path):
    client, state = _ready(tmp_path)
    assert state["voice_available"] is False
    resp = _post_audio(client)
    assert resp.status_code == 200
    assert resp.get_json() == {"outcome": "unavailable", "text": None}


@pytest.mark.usefixtures("no_voice")
@pytest.mark.parametrize("mark", ["got", "not_yet", "skip"])
def test_sentence_recall_works_without_voice(tmp_path, mark):
    client, _state = _ready(tmp_path)
    data = client.post(
        "/api/sentence-recall", json={"mark": "reveal", "attempt": "She is"}
    ).get_json()
    assert data["sentence_revealed"] is True
    assert client.post("/api/sentence-recall", json={"mark": mark}).get_json()["step"] == "recall"


def test_nothing_heard_passes_through(tmp_path, recogniser):
    recogniser.result = TranscriptionResult("nothing_heard")
    client, _state = _ready(tmp_path)
    resp = _post_audio(client)
    assert resp.status_code == 200
    assert resp.get_json() == {"outcome": "nothing_heard", "text": None}


def test_empty_recording_is_rejected(tmp_path, recogniser):
    client, _state = _ready(tmp_path)
    resp = _post_audio(client, data=b"")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "No recording received."}
    assert recogniser.calls == []


def test_recording_over_1mb_is_rejected(tmp_path, recogniser):
    client, _state = _ready(tmp_path)
    resp = _post_audio(client, data=b"x" * (1024 * 1024 + 1))
    assert resp.status_code == 413
    assert resp.get_json() == {"error": "The recording is too long."}
    assert recogniser.calls == []


def test_upload_keeps_its_own_too_large_message(tmp_path):
    client = _client(_app(tmp_path))
    resp = client.post(
        "/api/word-lists",
        data=b"x" * (1024 * 1024 + 1),
        content_type="multipart/form-data; boundary=x",
    )
    assert resp.status_code == 413
    assert resp.get_json() == {"error": "The file is larger than 1 MB."}


def _post_and_expect_409(client, recogniser):
    resp = _post_audio(client)
    assert resp.status_code == 409
    assert resp.get_json() == {"error": "Voice is only for recalling a sentence."}
    assert recogniser.calls == []


def test_transcribe_rejected_outside_sentence_recall(tmp_path, recogniser):
    app = _app(tmp_path)
    client = _client(app)
    _post_and_expect_409(client, recogniser)  # choose
    client.post("/api/select", json={"collection": "unit1", "mode": "example-recall"})
    _post_and_expect_409(client, recogniser)  # recall
    client.post("/api/answer", json={"answer": "zealous"})
    _post_and_expect_409(client, recogniser)  # reveal
    test_practice_api._wait_ready(app, client)
    client.post("/api/continue")
    client.post("/api/sentence-recall", json={"mark": "reveal"})
    _post_and_expect_409(client, recogniser)  # sentence already shown
    client.post("/api/sentence-recall", json={"mark": "got"})
    client.post("/api/answer", json={"answer": "rent"})
    test_practice_api._wait_ready(app, client)
    client.post("/api/continue")
    client.post("/api/sentence-recall", json={"mark": "skip"})
    assert client.get("/api/state").get_json()["step"] == "complete"
    _post_and_expect_409(client, recogniser)  # complete
