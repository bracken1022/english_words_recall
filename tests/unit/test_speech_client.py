"""Local speech-to-text for sentence recall (spec 022, research R1/R2/R5).
A fake WhisperModel stands in; no test loads a real model."""

import builtins
import io
import sys
import tempfile
from types import SimpleNamespace

import pytest

from src.services import speech_client


class FakeModel:
    def __init__(self, texts=(), error=None):
        self.texts = texts
        self.error = error
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))
        if self.error:
            raise self.error
        return [SimpleNamespace(text=t) for t in self.texts], None


@pytest.fixture
def model(monkeypatch):
    fake = FakeModel(texts=[" She is a zealous", " supporter of the team. "])
    monkeypatch.setattr(speech_client, "_get_model", lambda: fake)
    return fake


def test_ok_joins_and_trims(model):
    result = speech_client.transcribe(b"audio")
    assert result.outcome == "ok"
    assert result.text == "She is a zealous supporter of the team."


def test_english_only_with_voice_filter_from_memory(model):
    speech_client.transcribe(b"audio")
    audio, kwargs = model.calls[0]
    assert isinstance(audio, io.BytesIO)
    assert audio.getvalue() == b"audio"
    assert kwargs["language"] == "en"
    assert kwargs["vad_filter"] is True
    assert "initial_prompt" not in kwargs and "hotwords" not in kwargs


@pytest.mark.parametrize("texts", [(), ("   ",), ("", " ")])
def test_nothing_heard(monkeypatch, texts):
    monkeypatch.setattr(speech_client, "_get_model", lambda: FakeModel(texts=texts))
    result = speech_client.transcribe(b"audio")
    assert result.outcome == "nothing_heard"
    assert result.text is None


def test_model_error_is_unavailable(monkeypatch):
    monkeypatch.setattr(speech_client, "_get_model", lambda: FakeModel(error=RuntimeError("bad")))
    result = speech_client.transcribe(b"audio")
    assert (result.outcome, result.text) == ("unavailable", None)


def test_model_load_failure_is_unavailable(monkeypatch):
    def fail():
        raise OSError("no model")

    monkeypatch.setattr(speech_client, "_get_model", fail)
    assert speech_client.transcribe(b"audio").outcome == "unavailable"


def test_empty_audio_never_reaches_the_model(model):
    assert speech_client.transcribe(b"").outcome == "unavailable"
    assert model.calls == []


def test_not_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    monkeypatch.setattr(speech_client, "_model", None)
    assert speech_client.is_available() is False
    monkeypatch.undo()
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    monkeypatch.setattr(speech_client, "_model", None)
    # Not patched here: the real _get_model must fail softly.
    monkeypatch.setattr(speech_client, "_get_model", speech_client._load_model)
    assert speech_client.transcribe(b"audio").outcome == "unavailable"


def test_preload_never_raises(monkeypatch):
    def fail():
        raise OSError("no model")

    monkeypatch.setattr(speech_client, "_get_model", fail)
    speech_client.preload()


def test_writes_no_file(model, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("audio must not be written to disk")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", forbidden)
    monkeypatch.setattr(tempfile, "mkstemp", forbidden)
    assert speech_client.transcribe(b"audio").outcome == "ok"


def test_configure_changes_model_size(monkeypatch):
    monkeypatch.setattr(speech_client, "_model", None)
    speech_client.configure("small")
    try:
        assert speech_client.model_size() == "small"
    finally:
        speech_client.configure(speech_client.DEFAULT_MODEL_SIZE)
