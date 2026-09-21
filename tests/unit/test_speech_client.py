"""Unit tests for src/services/speech_client.py (spec 009).

The actual model call is always mocked (patching `_get_model`) — this
project never loads a real Whisper model in the test suite (research.md
§6), and `faster-whisper` is an optional dependency that may not even be
installed in the environment running these tests."""

from unittest.mock import MagicMock, patch

from src.services.speech_client import TranscriptionResult, is_available, transcribe


def _fake_model(text: str):
    segment = MagicMock()
    segment.text = text
    model = MagicMock()
    model.transcribe.return_value = ([segment], MagicMock())
    return model


def test_transcription_result_shape():
    result = TranscriptionResult(available=True, text="hello")
    assert result.available is True
    assert result.text == "hello"


def test_is_available_false_when_package_not_installed():
    """faster-whisper is not installed in this dev/test environment
    (it's an optional extra, per pyproject.toml's `voice` group) — this
    exercises the real, unmocked import-failure path."""
    assert is_available() is False


@patch("src.services.speech_client._get_model")
def test_transcribe_success_joins_segments(mock_get_model):
    mock_get_model.return_value = _fake_model("I received a gift yesterday.")
    result = transcribe(b"fake audio bytes", content_type="audio/webm")
    assert result.available is True
    assert result.text == "I received a gift yesterday."


@patch("src.services.speech_client._get_model")
def test_transcribe_unavailable_when_model_call_raises(mock_get_model):
    mock_get_model.side_effect = RuntimeError("model failed to load")
    result = transcribe(b"fake audio bytes", content_type="audio/webm")
    assert result.available is False
    assert result.text is None


@patch("src.services.speech_client._get_model")
def test_transcribe_unavailable_when_no_segments_recognized(mock_get_model):
    model = MagicMock()
    model.transcribe.return_value = ([], MagicMock())
    mock_get_model.return_value = model
    result = transcribe(b"fake audio bytes", content_type="audio/webm")
    assert result.available is False
    assert result.text is None


def test_transcribe_unavailable_when_audio_empty():
    result = transcribe(b"", content_type="audio/webm")
    assert result.available is False
    assert result.text is None


def test_transcribe_unavailable_when_package_not_installed():
    """Same real, unmocked import-failure path as is_available() above,
    exercised through transcribe() this time."""
    result = transcribe(b"fake audio bytes", content_type="audio/webm")
    assert result.available is False
    assert result.text is None
