"""End to end (spec 022 US1): select the example-recall mode, answer,
speak at sentence recall (faked recogniser), edit, reveal with the
comparison, mark. Only the mark reaches the history; no file is written
for the audio. Uses temp data only."""

import os
from pathlib import Path

import pytest

from src.services import speech_client
from src.services.speech_client import TranscriptionResult
from tests.contract import test_practice_api
from tests.contract.test_practice_api import _app, _client, _wait_ready

ollama = test_practice_api.ollama


def _files(root: Path) -> set[Path]:
    return {Path(d) / f for d, _, names in os.walk(root) for f in names}


@pytest.mark.usefixtures("ollama")
def test_speak_edit_reveal_mark(tmp_path, monkeypatch):
    heard = "She is zelous about recycling"
    monkeypatch.setattr(speech_client, "is_available", lambda: True)
    monkeypatch.setattr(speech_client, "transcribe", lambda audio: TranscriptionResult("ok", heard))

    app = _app(tmp_path)
    client = _client(app)
    client.post("/api/select", json={"collection": "unit1", "mode": "example-recall"})
    client.post("/api/answer", json={"answer": "zealous"})
    _wait_ready(app, client)
    state = client.post("/api/continue").get_json()
    assert state["step"] == "sentence-recall"
    assert state["voice_available"] is True

    files_before = _files(tmp_path)
    resp = client.post("/api/transcribe", data=b"\x1aE\xdf\xa3 webm", content_type="audio/webm")
    assert resp.get_json() == {"outcome": "ok", "text": heard}
    assert _files(tmp_path) == files_before  # nothing written for the audio

    edited = heard.replace("zelous", "zealous") + " every day"
    data = client.post(
        "/api/sentence-recall", json={"mark": "reveal", "attempt": edited}
    ).get_json()
    assert [w["word"] for w in data["comparison"]["attempt"] if w["status"] == "extra"] == [
        "every",
        "day",
    ]
    assert all(w["status"] == "same" for w in data["comparison"]["sentence"])

    after = client.post("/api/sentence-recall", json={"mark": "got"}).get_json()
    assert after["step"] == "recall"
    log = (tmp_path / "pl.md").read_text(encoding="utf-8")
    assert "sentence_recall: got" in log
    assert "zelous" not in log and "every day" not in log
