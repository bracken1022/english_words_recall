"""Local speech-to-text for sentence recall (spec 022; first added for
spec 009, research R1).

faster-whisper is an optional dependency (the `voice` extra): this module
stays importable without it, and every public function degrades to
"unavailable" rather than raising. Privacy rules (FR-004, FR-005):
- the audio is decoded from memory (io.BytesIO): never written to disk,
  never logged, and dropped when the request ends;
- the recognised text is returned, never logged or stored;
- the expected sentence is never given to the model (no prompt or hot
  words), so it can't "hear" the right answer and hide a mistake
  (research R2).
"""

import contextlib
import io
import threading
from dataclasses import dataclass

DEFAULT_MODEL_SIZE = "base"

_model = None  # lazily loaded WhisperModel, shared by all requests
_model_size = DEFAULT_MODEL_SIZE
_lock = threading.Lock()


@dataclass(frozen=True)
class TranscriptionResult:
    outcome: str  # "ok" | "nothing_heard" | "unavailable"
    text: str | None = None


def is_available() -> bool:
    """Is the optional package installed? Doesn't load the model."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def configure(model_size: str) -> None:
    """Use a different Whisper model size (e.g. "small", research R1)."""
    global _model, _model_size
    with _lock:
        if model_size != _model_size:
            _model, _model_size = None, model_size


def model_size() -> str:
    return _model_size


def _load_model():
    from faster_whisper import WhisperModel

    # int8 is the usual CPU setting: quick, and no float16 warning.
    return WhisperModel(_model_size, compute_type="int8")


def _get_model():
    global _model
    with _lock:
        if _model is None:
            _model = _load_model()
        return _model


def preload() -> None:
    """Load the model ahead of the first recording (SC-001). Never raises."""
    # A missing or broken model just means no voice.
    with contextlib.suppress(Exception):
        _get_model()


def transcribe(audio: bytes) -> TranscriptionResult:
    """English text for one recording. Never raises."""
    if not audio:
        return TranscriptionResult("unavailable")
    try:
        model = _get_model()
        segments, _info = model.transcribe(
            io.BytesIO(audio),
            language="en",
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception:  # noqa: BLE001 — an untrusted upload decoded by native
        # libraries (ctranslate2/av) with no stable exception contract; any
        # failure means "voice isn't working", never a crashed request.
        return TranscriptionResult("unavailable")
    if not text:
        return TranscriptionResult("nothing_heard")
    return TranscriptionResult("ok", text)
