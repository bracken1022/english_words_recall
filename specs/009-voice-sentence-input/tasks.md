---

description: "Task list template for feature implementation"
---

# Tasks: Speak Your Sentence Instead of Typing It

**Input**: Design documents from `/specs/009-voice-sentence-input/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. `plan.md`'s Constitution Check commits explicitly to this ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. This feature has exactly one user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`008`, plus one new service module. Touches `pyproject.toml`, `src/services/speech_client.py` (new), `src/web/app.py`, `src/web/templates/index.html`, `src/web/static/{app.js,style.css}`, and four test files (one new: `tests/unit/test_speech_client.py`) — see `plan.md`'s Project Structure.

---

## Phase 1: Setup

**Purpose**: Add the new optional dependency, at the packaging level, before any code depends on it

- [X] T001 Add a new `voice` optional-dependencies group to `pyproject.toml` — `voice = ["faster-whisper>=1.0"]` — alongside the existing `dev` group; confirm the base install (`pip install -e .`) and `dev` install remain completely unaffected (per `research.md` §1 and spec.md FR-007, this MUST stay optional, never added to the required `dependencies` list)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A — this feature has a single user story with no shared prerequisite beyond Setup. Proceed directly to Phase 3.

---

## Phase 3: Speak a sentence instead of typing it (Priority: P1) 🎯 MVP

**Goal**: A microphone control on the sentence-writing step records a short clip, a local speech-to-text service transcribes it, and the recognized text lands in the same editable sentence field a typed sentence already uses — with the app remaining fully usable, voice included as a graceful no-op, whether or not the optional dependency is installed or working.

**Independent Test**: In a real browser (on `localhost`, per the secure-context requirement), speak a sentence on the sentence-writing step and confirm it appears as editable text in the field; separately, with the optional dependency absent, confirm the mic control never appears and typing is unaffected — see `quickstart.md` Scenarios 1–4.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [P] [US1] Write unit tests in `tests/unit/test_speech_client.py` (new file) for a `TranscriptionResult` dataclass and a transcription function in `src/services/speech_client.py`, per `data-model.md`: `TranscriptionResult` has `available: bool` and `text: str | None`, with `text` `None` whenever `available` is `False`; the transcription function returns `available=False, text=None` (never raises) when the `faster_whisper` package is not importable, when the (mocked) model call raises an exception, or when the model call returns empty/no segments; and returns `available=True, text="<joined transcript>"` when the (mocked) model call succeeds — mock the model call itself, never load a real model in this test
- [X] T003 [P] [US1] Write contract tests in `tests/contract/test_web_api_contract.py` for `POST /api/transcribe` and the new `voice_available` field, per `contracts/web-api-contract-delta.md`: `200` + `{"available": true, "text": "..."}` when the (patched) transcription call succeeds; `200` + `{"available": false, "text": null}` when it fails or the request body is empty — never a `4xx`/`5xx` for either case; `GET /api/state` includes `voice_available: true`/`false` matching whether the speech-to-text dependency is (mock-)available, present on every step's response, not just `"sentence"`; and confirm this call is accepted regardless of the practice session's current step (no `409` case exists for it)
- [X] T004 [P] [US1] Write an integration test in `tests/integration/test_web_session_flow.py` covering a full recall → (mocked) transcribe → review → submit flow through the real Flask test client: `POST /api/transcribe` with the transcription call patched to return recognized text, confirm the response shape, then `POST /api/sentence` with that same text and confirm it's submitted and logged exactly as a typed sentence would be (no new progress-log field or behavior)
- [X] T005 [P] [US1] Write a static-content assertion in `tests/unit/test_web_static_assets.py` confirming `src/web/static/app.js` wires up `MediaRecorder`/`getUserMedia`, a fetch to `/api/transcribe`, and hides/disables the mic control based on `state.voice_available` — matching `research.md` §6's "no JS/browser test runner" convention

### Implementation for User Story 1

- [X] T006 [US1] Implement `TranscriptionResult` and a transcription function (e.g. `transcribe(audio: bytes, content_type: str) -> TranscriptionResult`) in `src/services/speech_client.py` (new file), mirroring `llm_client.py`'s shape: a module-level, lazily-constructed `WhisperModel` singleton (loaded on first call, not at import time, per `research.md` §2); catch `ImportError` (package not installed) and any model-load/transcription exception, returning `TranscriptionResult(available=False, text=None)` in every failure case rather than raising (depends on T002 failing for the right reason)
- [X] T007 [US1] In `src/web/app.py`: add a cheap, startup-time `voice_available` check (attempt `import faster_whisper`, catching `ImportError`) stored in `app.config`; merge it into every `GET /api/state` response (`{**session.state(), "voice_available": app.config["VOICE_AVAILABLE"]}`); add the stateless `POST /api/transcribe` route reading the raw request body and `Content-Type`, calling `speech_client.transcribe(...)`, and returning its `TranscriptionResult` as JSON — no `WrongStepError`/`409` handling, since this endpoint has no relationship to the practice-session step (`research.md` §3) (depends on T006, T003)
- [X] T008 [P] [US1] Add a microphone `<button>` and a transcribing-indicator element (reusing the existing `.spinner`/`.spinner__dot` markup shape with different text, e.g. "Transcribing...") near the sentence input in `src/web/templates/index.html`, both initially hidden
- [X] T009 [US1] In `src/web/static/app.js`: on `renderState()`, show/hide the mic button based on `state.voice_available`; wire the mic button to request microphone access, record via `MediaRecorder` (picking a supported MIME type per `research.md` §4), and on stop, show the transcribing indicator, `POST` the recorded `Blob` to `/api/transcribe` with its own `type` as `Content-Type`, then set `sentenceInput.value` to the returned `text` (only when `available` is `true`) and hide the indicator — never calling `/api/sentence` automatically (spec.md FR-002) (depends on T008, T007, T005)
- [X] T010 [P] [US1] Add styling for the mic button and transcribing indicator in `src/web/static/style.css`, consistent with the existing notebook/card design and the established spinner/button treatments (depends on T008)

**Checkpoint**: User Story 1 is fully functional and testable independently — `quickstart.md` Scenarios 1–4 (transcribe into the field, typing still works and review-before-submit holds, graceful fallback with the dependency absent, nothing leaves the machine/nothing retained) can be run once T001–T010 are done; see Phase 4 for the mandatory real-browser pass.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory real-browser validation (no JS/browser/audio test runner in this project — see `research.md` §6)

- [X] T011 [P] Run `ruff check` over `src/` and `tests/` and fix any issues
- [X] T012 Run all of `quickstart.md`'s scenarios end-to-end **in a real browser on `localhost`**: speaking a sentence transcribes into the field for review, editing and submitting behaves exactly as typed text always has, the mic control never appears and nothing else is affected when the optional dependency is absent, and a network inspector confirms no request leaves the machine and no new file appears on disk after transcribing — a green test suite alone cannot verify any of this, since no automated test in this project can record or transcribe real audio
- [X] T013 Run the full existing test suite (`pytest -q`) and confirm every previously-passing test still passes, proving no regression to grading, the review pipeline, the progress-log format, the session tally, the skip-word flow (`006`), the collection-choice flow (`007`), or the correct-result color (`008`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — adds the optional dependency declaration only.
- **Foundational (Phase 2)**: None for this feature — skipped.
- **User Story 1 (Phase 3)**: Depends on Setup only. This is the entire feature.
- **Polish (Phase 4)**: Depends on User Story 1 being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories or features — a self-contained addition alongside the existing sentence-writing step.

### Within Each User Story

- Tests are written first and must fail before their corresponding implementation task: T002 fails (import error — `speech_client.py` doesn't exist yet) until T006 exists; T003 fails (404) until T007 exists; T004 fails until T006/T007 exist; T005 fails until T009 exists.

### Parallel Opportunities

- T002, T003, T004, T005 are four independent test files and can be started together.
- T008 (template) and T010 (CSS) touch different files than T006/T007 (Python) and can proceed in parallel with them; T009 (`app.js`) depends on both T008 (needs the markup to target) and T007 (needs the endpoint to call).
- T011 (lint) can run alongside T012/T013 in Phase 4.

---

## Parallel Example: User Story 1

```bash
# T002, T003, T004, T005 are independent test files and can be started together:
Task: "TranscriptionResult/speech_client unit tests in tests/unit/test_speech_client.py"
Task: "POST /api/transcribe + voice_available contract tests in tests/contract/test_web_api_contract.py"
Task: "Full record->transcribe->review->submit integration test in tests/integration/test_web_session_flow.py"
Task: "app.js voice-wiring static assertion in tests/unit/test_web_static_assets.py"
```

---

## Implementation Strategy

### MVP First (and only) — User Story 1

1. Complete Phase 1: Setup — declare the optional dependency.
2. Complete Phase 3: User Story 1 — the entire feature.
3. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1–4 in a real browser on `localhost`, both with and without the optional dependency installed.
4. Polish: lint plus the full regression suite.

---

## Notes

- `[P]` tasks touch different files or independent assertions with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to `spec.md` for traceability.
- This feature adds exactly one new source file (`src/services/speech_client.py`) and one new test file (`tests/unit/test_speech_client.py`); every other touched file already exists. `src/web/session_state.py` and `src/cli/` are untouched (per `plan.md`'s Constraints).
- Do not consider this feature done when the test suite is green alone — T012's real-browser pass is the only way this feature's actual claims (transcription works, nothing leaves the machine, nothing is retained, graceful fallback) are verified, per `research.md` and `quickstart.md`.
- Commit after each task or logical group.
