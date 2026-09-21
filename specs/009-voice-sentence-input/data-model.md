# Data Model: Speak Your Sentence Instead of Typing It

No new persistent entities (spec.md: presentation/utility only — audio is
transient, FR-006). This feature adds one new transient value and one new
service-layer result type, mirroring the existing `CorrectionResult`
shape.

## `TranscriptionResult` (new — `src/services/speech_client.py`)

Mirrors `llm_client.py`'s `CorrectionResult` shape and "never raise,
report unavailability instead" convention.

| Field | Type | Notes |
|---|---|---|
| `available` | `bool` | `False` for any failure: package not installed, model failed to load, audio failed to decode — the caller never needs to distinguish which |
| `text` | `str \| None` | The transcribed sentence; `None` when `available` is `False` |

```python
@dataclass
class TranscriptionResult:
    available: bool
    text: str | None
```

## In-memory audio clip (transient — never a stored entity)

| Property | Value |
|---|---|
| Lifetime | Exists only for the duration of one `POST /api/transcribe` request |
| Storage | Never written to disk; held in memory only long enough to hand off to the transcription call |
| Retention | None — discarded immediately after the response is sent (FR-006) |

## Server-level capability flag (not session state)

| Field | Type | Where it lives | Notes |
|---|---|---|---|
| `voice_available` | `bool` | `app.config`, computed once at startup (a cheap "is `faster_whisper` importable" check); merged into every `GET /api/state` response by the route handler | **Not** a `PracticeSession` field — transcription has no relationship to recall/sentence/feedback progression (research.md §3) |

## `PracticeSession` / `session_state.py` — unchanged

No fields, methods, or state transitions added or modified. Voice input
is orthogonal to the practice-session state machine entirely.

## Progress log — unchanged

Nothing about this feature touches `PracticeAttempt` or the progress-log
format: once transcribed text is reviewed and submitted, it travels
through the exact same `POST /api/sentence` path (and is logged exactly
the same way) as text the learner typed directly.
