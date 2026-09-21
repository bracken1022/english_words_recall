# Research: Speak Your Sentence Instead of Typing It

No open `NEEDS CLARIFICATION` markers — both real forks (local vs. cloud
transcription; hard vs. soft dependency) were already resolved in
spec.md's Clarifications sessions before planning began. This file
records the remaining design decisions and the alternatives considered.

## 1. Which local speech-to-text library

**Decision**: `faster-whisper` (a CTranslate2-based reimplementation of
OpenAI's Whisper), used with a small model (`base` or `small`) by default.

**Rationale**: This project has stayed deliberately light on dependencies
(`requests`, `PyYAML`, `rich`, `Flask` — no ML/numeric stack at all
today). Plain `openai-whisper` requires a full PyTorch install (hundreds
of MB, GPU wheels by default) for what is, here, short CPU-only
inference on single sentences. `faster-whisper` gets the same Whisper
model family's accuracy with a much lighter CTranslate2 runtime and no
PyTorch dependency, and it bundles `av` (PyAV/ffmpeg bindings) for audio
decoding — so it can be handed the browser-recorded clip directly
(webm/opus, ogg/opus, mp4/aac, etc.) without this app shelling out to
`ffmpeg` itself.

**Alternatives considered**:
- **`openai-whisper`** — rejected: heavier dependency (PyTorch) for the
  same underlying model family, no accuracy benefit for this use case.
- **Vosk** — rejected: lighter still and fully offline, but noticeably
  lower accuracy than Whisper-family models for general speech, and this
  project already has a "local LLM does the judgment work" precedent
  (Ollama) that a small Whisper model fits more naturally alongside than
  a much simpler acoustic-only recognizer.
- **A separate local server process** (mirroring Ollama's own
  install-and-run-a-server pattern, e.g. `whisper.cpp`'s server mode) —
  rejected: the clarification answer ("may require installing a new local
  speech-recognition **library**") points at an in-process Python
  dependency, not a second standalone service for the learner to
  separately install, configure a URL for, and keep running. One process
  to run (`python -m src.web`) stays simpler than two.

## 2. Where the model lives and when it loads

**Decision**: A single `WhisperModel` instance, lazily constructed on the
*first* transcription request and cached for the lifetime of the process
(module-level singleton in `speech_client.py`) — not loaded at server
startup.

**Rationale**: Mirrors exactly how Ollama's own availability is already
handled: `create_app()` never pings Ollama at startup either — reachability
is only discovered lazily, per-request, inside `submit_sentence()`
(`session_state.py`). Loading Whisper weights (and, on first-ever run,
downloading them) can take anywhere from under a second to tens of
seconds; doing that at startup would make every server launch slow even
for learners who never use voice input. Loading it lazily keeps startup
fast unconditionally, and the first voice attempt simply absorbs that
one-time cost (with the transcribing-indicator, §5, covering the wait).

**Two-tier availability, mirroring `CorrectionResult.available`**:
- `GET /api/state`'s `voice_available` field reflects a cheap,
  startup-time check: is the `faster_whisper` package importable at all?
  (FR-007's "optional dependency" — if it isn't installed, this is
  `False` and the mic button never appears.)
- `POST /api/transcribe`'s own `available` field (see contract) reflects
  whether *that specific call* actually produced text — covering the
  rarer case where the package is installed but model loading fails for
  some other reason (e.g. first-run download failed with no network,
  corrupted cache). The client treats either signal identically: hide/stop
  offering voice input, fall back to typing, matching FR-004.

**Alternatives considered**:
- **Eager load at startup** — rejected per FR-007: would make every
  server launch pay Whisper's load/download cost even when no learner
  ever uses voice input, and a slow/failed load shouldn't be allowed to
  slow down or block startup for an optional feature.

## 3. Endpoint shape and where it lives

**Decision**: A new, stateless `POST /api/transcribe` in `src/web/app.py`,
independent of `PracticeSession`/`session_state.py` entirely — it takes
recorded audio and returns text, with no relationship to which recall/
sentence/feedback step is active. `voice_available` is computed once from
the optional-dependency check and merged into `get_state()`'s JSON
response at the route level (`app.py`), not added as a `PracticeSession`
field, since it's a server capability, not session state.

**Rationale**: Transcription has no bearing on session progression —
unlike `POST /api/sentence`/`POST /api/skip`, there's no "wrong step" for
recording audio; a learner could equally use it while just staring at the
field, before deciding what to say. Keeping `PracticeSession` unaware of
voice input entirely preserves the existing, already-tested separation
between practice-flow state and server-level capability/config (which
already lives in `app.config`, e.g. `OLLAMA_URL`/`MODEL`).

**Alternatives considered**:
- **Gate `POST /api/transcribe` on `step == "sentence"`** — rejected: adds
  a `WrongStepError`-style restriction spec.md never asked for, and would
  need updating every time a future step also wants voice input (e.g. if
  the recall step ever grew a voice option) for no correctness benefit —
  transcription is inert on its own; only *submitting* the resulting text
  is already step-gated via the existing `POST /api/sentence` endpoint.

## 4. Audio format and capture

**Decision**: The client records via `MediaRecorder`, picking the first
browser-supported MIME type from a small preferred list (e.g.
`audio/webm;codecs=opus`, falling back through a couple of alternatives
via `MediaRecorder.isTypeSupported()`), and uploads the resulting `Blob`
as the request body with its own `type` as the `Content-Type` header.
`faster-whisper`'s bundled `av`-based decoding accepts common containers
directly, so no server-side transcoding step is added.

**Rationale**: Every mainstream desktop/mobile browser that supports
`MediaRecorder` at all supports at least one of `av`'s well-supported
containers (webm/opus chief among them on Chrome/Firefox/Android; Safari
support is comparatively newer and narrower — noted as a known gap in
`quickstart.md` rather than worked around, matching this project's
existing "manual browser pass documents what it documents" convention
rather than adding untested transcoding complexity).

**Alternatives considered**:
- **Force a single specific format via client-side re-encoding** —
  rejected: would need a JS audio-encoding library with no server-side
  benefit, since the chosen decode path already accepts what browsers
  natively produce.

## 5. Loading state while transcribing

**Decision**: Reuse the existing spinner pattern (`#spinner`/`.spinner`,
`spinner__dot`, "Reviewing your sentence..." — `src/web/static/style.css`)
for a second, separately-labeled instance ("Transcribing..." or similar)
shown while `POST /api/transcribe` is in flight, exactly mirroring how
the sentence-review spinner already covers the Ollama round trip.

**Rationale**: This project already solved "tell the learner a local-model
call is in progress" once (spec `002`'s loading-indicator contract); reusing
that exact visual vocabulary for a second local-model call is more
consistent than inventing a new one, and needs no new CSS beyond an extra
label/id.

**Alternatives considered**: A distinct waveform/recording-specific
animation — rejected as unnecessary polish beyond what was asked, and a
second visual language for "a local model is thinking" would undercut
the consistency the existing spinner already provides.

## 6. Test strategy

**Decision**: Same three tiers as `006`/`007`/`008`:
- `tests/unit/test_speech_client.py` (**new**) — the transcription
  function's own logic (turning a raw model result into the
  `available`/`text` shape, handling a missing-package/model-load
  failure as `available=False`), with the actual `WhisperModel` call
  mocked/patched — never a real model load in the test suite.
- `tests/contract/test_web_api_contract.py` — `POST /api/transcribe`
  HTTP-level behavior (200 with text, `available: false` on failure,
  a `voice_available` field on `GET /api/state`), again with the
  transcription call patched.
- `tests/integration/test_web_session_flow.py` — one full
  record → transcribe (mocked) → review → submit scenario through the
  real Flask test client.
- `tests/unit/test_web_static_assets.py` — static-content assertion that
  `app.js` wires up `MediaRecorder`, the upload to `/api/transcribe`, and
  hides the mic control when `voice_available` is false — matching the
  established "no JS/browser test runner" convention.

**Alternatives considered**: Recording and transcribing real audio in the
test suite — rejected outright: no CI environment is guaranteed to have
the optional dependency, a downloaded model, or a microphone, and
transcription accuracy isn't a unit-testable property regardless: the
manual `quickstart.md` pass is what actually proves this works.
