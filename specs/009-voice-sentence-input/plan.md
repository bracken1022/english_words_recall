# Implementation Plan: Speak Your Sentence Instead of Typing It

**Branch**: `009-voice-sentence-input` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-voice-sentence-input/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Adds a microphone control next to the sentence-writing step's text input.
The browser records a short audio clip, uploads it to a new stateless
endpoint, and a local speech-to-text model transcribes it — never a
cloud service — returning plain text that lands in the same field a
typed sentence already uses, for the learner to review/edit before
submitting exactly as today. The local transcription library is an
**optional** dependency: if it isn't installed, or a transcription
attempt fails, voice input is simply not offered and the app is otherwise
completely unaffected, mirroring exactly how the existing local
sentence-correction service (Ollama) already degrades gracefully today.

## Technical Context

**Language/Version**: Python 3.11+ (backend, per `pyproject.toml`); vanilla ES2017 JavaScript, HTML, CSS (frontend — no build step, no framework, consistent with `005`–`008`)

**Primary Dependencies**: **New, optional**: `faster-whisper` (CTranslate2-based local Whisper inference — lighter runtime footprint than plain `openai-whisper`, no PyTorch requirement for inference, decodes common browser-recorded audio containers via its bundled `av`/ffmpeg support without this app invoking `ffmpeg` itself). Added as a new optional-dependencies group (e.g. `voice`), never the base install, so FR-007's "optional, non-blocking" requirement is enforced at the packaging level, not just at runtime. Existing dependencies (Flask, requests, PyYAML, rich) are unchanged.

**Storage**: N/A for this app's own data model — a cached Whisper model file is managed automatically by `faster-whisper`/`huggingface_hub` in the user's local cache directory, outside this app's `vocabulary`/`progress.md` files entirely; no new file format, no new persistent entity (spec.md FR-006: audio itself is never persisted)

**Testing**: pytest, existing three tiers; the new speech-transcription call is always mocked/patched in automated tests (mirroring how `request_correction` is already patched everywhere), since (a) no CI environment is guaranteed to have the optional dependency or a downloaded model, and (b) transcription *accuracy* isn't something a unit test can meaningfully assert — real end-to-end audio verification is a manual `quickstart.md` step, consistent with this project's established "no browser/audio test runner" convention

**Target Platform**: Existing Flask dev server (`src/web`); voice *capture* additionally requires a secure browser context (HTTPS or `localhost`) per browser platform rules, independent of where transcription happens — an existing, disclosed limitation (spec.md Assumptions), not something this plan works around

**Project Type**: Single project (existing `src/`, `tests/` layout, unchanged) — web UI only; the CLI (`src/cli/`) is out of scope (see Constraints)

**Performance Goals**: Transcribing a single short practice sentence (a few seconds of speech) on CPU with a small Whisper model ("base" or "small") should complete in roughly the same few-second ballpark the existing Ollama correction call already takes — no stricter target is set, matching this project's existing precedent of not setting hard latency budgets for local-model calls

**Constraints**:
- MUST NOT make `faster-whisper` (or any speech-to-text library) a required dependency — the app MUST start and remain fully usable, voice included as a graceful no-op, whether or not it's installed or working (FR-007)
- MUST NOT send recorded audio anywhere off the learner's own machine/local network (FR-005) — no cloud STT API, no browser-native `SpeechRecognition`/`webkitSpeechRecognition` (which routes through the browser vendor's cloud service on Chrome/Android)
- MUST NOT persist recorded audio beyond producing one transcription (FR-006) — no temp file left on disk after the request completes, no audio in the progress log
- MUST NOT auto-submit a sentence from speech — recognized text always lands in the existing field for review first (FR-002)
- MUST NOT change the CLI (`src/cli/`) — this feature is scoped to the web UI only, the same scoping decision `006`/`007` already made for their own web-only interactive features; a terminal prompt has no equivalent to a browser's microphone capture
- MUST follow the additive "Contract Delta" convention already established (`004`/`006`/`007`) for amending `003-web-ui`'s API contract with one new endpoint

**Scale/Scope**: One new optional dependency, one new service module (`src/services/speech_client.py`, mirroring `llm_client.py`'s shape), one new stateless Flask endpoint (`POST /api/transcribe`), one new always-present `voice_available` field on `GET /api/state`, and frontend additions (a mic button, `MediaRecorder`-based capture, a transcribing indicator reusing the existing spinner pattern) — no changes to `PracticeSession`'s state machine, since transcription doesn't affect session progression at all

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Plan requires unit tests for the new speech-client module (with the actual model call mocked), contract tests for `POST /api/transcribe` and the new `voice_available` field, all written before their implementation, following this project's established red-green-refactor convention | PASS |
| II. Pedagogical Accuracy & Safety | Transcription doesn't generate, correct, score, or explain language content — it converts speech to text mechanically, and FR-002's mandatory review-before-submit step keeps the learner as the final authority on what text is actually submitted for correction, so no independent "known-correct/known-incorrect" test suite is needed for transcription itself | PASS |
| III. Learner Data Privacy | Directly engaged and satisfied: recorded audio (voice, the principle's own named example) is processed only by a local service (FR-005), never retained (FR-006), and this plan documents exactly what's collected (a transient audio clip) and why (to produce text for the existing sentence field) before implementation begins, per the principle's own requirement | PASS |

**Post-design re-check**: Phase 1 artifacts (data-model.md, contracts/, quickstart.md) introduce one new transient concept (an in-flight audio clip, never stored) and one new stateless endpoint — no new persistent entity, no change to the practice-session state machine. All three gates still PASS unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/009-voice-sentence-input/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── web-api-contract-delta.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── models/                     # UNCHANGED
├── services/
│   ├── llm_client.py            # UNCHANGED — existing Ollama client, unaffected
│   └── speech_client.py         # NEW — local speech-to-text client, mirrors llm_client.py's shape
├── cli/                         # UNCHANGED — out of scope (see Constraints)
└── web/
    ├── app.py                   # + POST /api/transcribe, + voice_available merged into GET /api/state
    ├── session_state.py         # UNCHANGED — transcription is orthogonal to session progression
    ├── templates/index.html     # + mic button and transcribing-indicator markup near the sentence input
    └── static/
        ├── app.js               # + recording capture (MediaRecorder), + upload/transcribe wiring
        └── style.css            # + mic button / transcribing-indicator styling, consistent with existing design

tests/
├── contract/
│   └── test_web_api_contract.py         # + POST /api/transcribe cases, + voice_available field cases
├── integration/
│   └── test_web_session_flow.py         # + one end-to-end "record → transcribe → review → submit" scenario (transcription mocked)
└── unit/
    ├── test_speech_client.py             # NEW — transcription client unit tests (model call mocked)
    └── test_web_static_assets.py          # + assertion that app.js wires up recording/upload/mic-button-visibility

pyproject.toml                    # + new "voice" optional-dependencies group (faster-whisper)
```

**Structure Decision**: Single project (existing Option 1 layout, established `001`–`008`). This feature adds one new service module and one new test module alongside the existing `src/web/` slice; no new top-level directories.

## Complexity Tracking

*No constitution violations requiring justification. Table omitted.*
