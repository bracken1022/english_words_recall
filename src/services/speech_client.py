"""Client for local speech-to-text transcription (spec 009, FR-005/FR-006).

Boundary rule: TranscriptionResult is a simple text-or-unavailable payload,
mirroring llm_client.CorrectionResult's "never raise, report unavailability
instead" convention. faster-whisper is an optional dependency (FR-007) —
this module MUST remain importable, and every public function MUST degrade
to available=False, even when it isn't installed at all.
"""

import io
from dataclasses import dataclass

DEFAULT_MODEL_SIZE = "base"

_model = None  # lazily-constructed WhisperModel singleton (research.md #2)


@dataclass
class TranscriptionResult:
    available: bool
    text: str | None


def _unavailable() -> TranscriptionResult:
    return TranscriptionResult(available=False, text=None)


def is_available() -> bool:
    """Cheap, startup-time check: is the optional speech-to-text package
    installed? Does not load the (possibly large) model itself — used for
    GET /api/state's `voice_available` field (data-model.md)."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(DEFAULT_MODEL_SIZE)
    return _model


def transcribe(audio: bytes, content_type: str = "") -> TranscriptionResult:
    """Transcribe *audio* (raw bytes as uploaded by the browser) into text
    using a local Whisper model. Never raises: package not installed,
    model failed to load, or audio failed to decode are all reported as
    available=False rather than propagated (data-model.md)."""
    if not audio:
        return _unavailable()

    try:
        model = _get_model()
        segments, _info = model.transcribe(io.BytesIO(audio))
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception:  # noqa: BLE001 — untrusted upload decoded by a native
        # (ctranslate2/av) library with no stable, enumerable exception
        # contract; any failure here must degrade to "unavailable" rather
        # than ever crash the request (data-model.md, spec 009 FR-007).
        return _unavailable()

    if not text:
        return _unavailable()

    return TranscriptionResult(available=True, text=text)
