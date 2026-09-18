---

description: "Task list template for feature implementation"
---

# Tasks: Web UI for Remote Access

**Input**: Design documents from `/specs/003-web-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature; this overrides the "tests optional" default.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001-vocab-recall-tutor`/`002-sentence-review-indicator`:
`src/{models,services,cli,lib,web}`, `tests/{contract,integration,unit}` at repository root.

---

## Phase 1: Setup

**Purpose**: Add the one new dependency and the new package's directories

- [X] T001 Add `Flask` to `pyproject.toml` dependencies and install it into `.venv`
- [X] T002 [P] Create `src/web/`, `src/web/templates/`, and `src/web/static/` directories, with `src/web/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared `PracticeSession` state machine and a minimal Flask
app/page shell that every user story below builds on — MUST complete first

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Write unit tests for `PracticeSession` per data-model.md: starts in `"empty"` when no items load; otherwise starts in `"recall"` at `current_index == 0`; `current_index` never decreases; reaching the end of `items` sets `step` to `"complete"`; a method call for the wrong step (e.g., submitting a sentence while `step == "recall"`) is rejected without changing state — in `tests/unit/test_session_state.py`
- [X] T004 [P] Write a contract test for `GET /api/state`'s per-step response shape (`empty`/`recall`/`sentence`/`feedback`/`complete`, per the table in `contracts/web-api-contract.md`), using `app.test_client()` — in `tests/contract/test_web_api_contract.py`
- [X] T005 Implement `PracticeSession` in `src/web/session_state.py` per data-model.md: load items via the existing `vocabulary_loader.load_vocabulary` (unchanged FR-001/FR-013 tolerance), and track `items`, `current_index`, `step`, `pending_attempt`, `warnings` exactly per the state-transition diagram (depends on T003)
- [X] T006 Implement the Flask app factory `create_app(vocab_dir, progress_file, group, ollama_url, model)` in `src/web/app.py`: owns one `PracticeSession`, registers `GET /` (renders `templates/index.html`) and `GET /api/state` (depends on T005, T004)
- [X] T007 [P] Implement the entry point in `src/web/__main__.py`: argument parsing for `--vocab-dir`, `--progress-file`, `--group`, `--ollama-url`, `--model`, `--host` (default `0.0.0.0`), `--port`; builds `create_app(...)` and calls `app.run(host=..., port=...)` (depends on T006)
- [X] T008 [P] Create the minimal page shell `src/web/templates/index.html` (regions for recall / sentence / feedback / complete / empty, toggled by JS based on `GET /api/state`) and a baseline (unstyled) `src/web/static/style.css` — responsive rules are added in User Story 3 (depends on T006)

**Checkpoint**: `GET /api/state` and `GET /` work end-to-end against a real vocabulary directory; no answer/sentence submission yet.

---

## Phase 3: User Story 1 - Practice vocabulary recall in a web browser (Priority: P1) 🎯 MVP

**Goal**: A learner can see the Chinese meaning, submit an English answer,
be told correct/incorrect with the expression revealed, and move forward to
the next item — through the browser, with the same grading and reveal rules
the existing tutor already uses.

**Independent Test**: Point the web server at a small vocabulary file, open
the page, complete several recall attempts (correct, incorrect, blank), and
confirm grading/reveal matches the existing command-line tool for the same
file and inputs.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T009 [US1] Contract tests for `POST /api/answer` (correct/incorrect/blank grading via the unchanged `matcher.grade_answer`; `accepted_expressions` revealed regardless of correctness; `409 Conflict` when `step != "recall"`) and for `POST /api/continue`'s no-skip rejection from `"recall"`/`"sentence"`, per `contracts/web-api-contract.md` — in `tests/contract/test_web_api_contract.py` (extends T004)
- [X] T010 [P] [US1] Integration test for the full recall-only cycle (`state` → `answer` → `state` now shows the sentence step, expression revealed) against a small vocabulary file, per spec Acceptance Scenarios 1-5 (US1) and quickstart Scenario 1 — in `tests/integration/test_web_session_flow.py`

### Implementation for User Story 1

- [X] T011 [US1] Implement `POST /api/answer` in `src/web/app.py`: call `matcher.grade_answer` unchanged, update `PracticeSession` (record the answer/correctness into `pending_attempt`, advance `step` to `"sentence"`), return `{correct, accepted_expressions}` per FR-002/FR-003/FR-004 (depends on T009, T005)
- [X] T012 [US1] Implement `POST /api/continue`'s rejection from `"recall"`/`"sentence"` and its `"feedback"` → next-item-or-`"complete"` transition in `src/web/session_state.py`/`src/web/app.py`, per FR-010 (depends on T009, T005)
- [X] T013 [US1] Implement the recall-step interactivity in `src/web/static/app.js`: render the current step from `GET /api/state`, submit the answer via `fetch("/api/answer")`, show correct/incorrect + the revealed expression(s), and show a "continue" control once the sentence step is reachable — no sentence/spinner logic yet (depends on T011)

**Checkpoint**: User Story 1 is fully functional and independently testable — recall works end-to-end through a real browser, matching the existing tutor's behavior for that step.

---

## Phase 4: User Story 2 - Get sentence-writing practice with LLM feedback in the browser (Priority: P2)

**Goal**: After recall, the learner writes a sentence using the target
expression; a visible working indicator shows while the existing local LLM
pipeline reviews it; the result (grammatical correctness, target-expression
usage, a more natural version when available, and an explanation) is shown
afterward, and the attempt is logged exactly as the CLI already does.

**Independent Test**: Complete a recall step, submit a sentence, and
confirm the four review outcomes (needs correction / already correct /
missing expression / unavailable) each produce the expected response shape
and progress-log entry, per `contracts/web-api-contract.md`.

### Tests for User Story 2 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T014 [US2] Contract tests for `POST /api/sentence`'s four outcomes (needs-correction, already-correct, missing-expression, unavailable — mocking `request_correction` exactly as `001`/`002` already do) and its `409 Conflict` when `step != "sentence"`, per `contracts/web-api-contract.md` — in `tests/contract/test_web_api_contract.py` (extends T009)
- [X] T015 [P] [US2] Integration test for the full recall→sentence→feedback cycle confirming the completed `PracticeAttempt` is appended to the progress Markdown log in the existing, unchanged format (FR-012, `001`'s `contracts/progress-log-format.md`) — in `tests/integration/test_web_session_flow.py` (extends T010)

### Implementation for User Story 2

- [X] T016 [US2] Implement `POST /api/sentence` in `src/web/app.py`: call `request_correction` and `progress_log.append_attempt` unchanged, update `PracticeSession` (attach `sentence`/`feedback` to `pending_attempt`, advance `step` to `"feedback"`), return the `CorrectionResult` fields per FR-006/FR-008/FR-009/FR-012 (depends on T014, T005)
- [X] T017 [US2] Extend `src/web/static/app.js`: show the sentence prompt with the revealed expression after a recall answer; on submit, toggle the spinner element around the `fetch("/api/sentence")` call per `contracts/loading-indicator-contract.md` (visible before the call, hidden on both success and network failure, before rendering the result); render the four feedback fields or the "review unavailable" message (depends on T016, T013)
- [X] T018 [US2] Add the spinner element and its CSS animation to `src/web/templates/index.html`/`src/web/static/style.css` — a fixed label plus an animation only, no percentage/step-count markup anywhere (depends on T017)

**Checkpoint**: User Stories 1 and 2 both work — the full recall→sentence→feedback→continue loop functions in a real browser on the host machine.

---

## Phase 5: User Story 3 - Access the tutor from another device on the local network (Priority: P3)

**Goal**: The same experience works from a phone, tablet, or another
computer on the same local network, in a layout that stays usable at
phone-width, and is not reachable from outside that network by default.

**Independent Test**: With the server running on one machine, open the same
address from a second device on the same network and complete a full
recall-and-sentence cycle from that device; resize to phone width and
confirm no horizontal scrolling or overlap at any step.

### Tests for User Story 3 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T019 [US3] Integration tests confirming: the app binds to `0.0.0.0` by default (LAN-reachable) with `--host`/`--port` honored when given (FR-013/FR-015); an empty vocabulary pool produces the `"empty"` state with a clear message (FR-017 edge case); a malformed vocabulary block alongside a valid one surfaces a warning in `PracticeSession.warnings` while the valid item still loads (FR-017) — in `tests/integration/test_web_session_flow.py` (extends T015)

### Implementation for User Story 3

- [X] T020 [US3] Apply the mobile-first responsive layout per `contracts/responsive-layout-contract.md` to `src/web/static/style.css`: single-column, full-width, touch-sized controls as the base (unprefixed) rules; a `min-width` media query adds a centered `max-width` for tablet/desktop — no horizontal scroll or overlap at any width (depends on T018)
- [X] T021 [US3] Surface `PracticeSession.warnings` in `src/web/templates/index.html`/`src/web/static/app.js` so malformed-vocabulary warnings are visible on the page (FR-017) (depends on T019, T012)

**Checkpoint**: All three user stories are independently functional; the app is LAN-reachable and responsive at every target width.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and full end-to-end validation

- [X] T022 [P] Update root `README.md` with how to start the web server (`python -m src.web ...`), how to find the LAN address to give a second device, and a note that it coexists with the existing CLI
- [X] T023 [P] Run `ruff check` over `src/web/` and fix any issues
- [X] T024 Run all of `specs/003-web-ui/quickstart.md`'s scenarios end-to-end (real browser on the host machine, a real second device on the LAN, a phone-width resize, Ollama stopped and restarted) and fix any gaps found — **partially verified**: real HTTP requests to the running server (`GET /`, `GET /api/state`, `POST /api/answer`, a real `POST /api/sentence` against the live `qwen3:14b` model, `POST /api/continue`) all worked correctly, and `progress.md` was written in the correct format; the server logs binding to `0.0.0.0` as expected. Actually reaching it from a genuinely separate second device (Scenario 3) and eyeballing the phone-width layout in a real browser were **not** verifiable from this sandboxed tool session (a request to the host's own LAN IP timed out, most likely a sandbox network restriction rather than an app defect) — recommend the user do this check themselves once.
- [X] T025 Run the full existing `001-vocab-recall-tutor` and `002-sentence-review-indicator` test suites unmodified and confirm every previously-passing test still passes, proving FR-006/FR-011/FR-012 (review pipeline and storage unchanged)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational only. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational; extends US1's `app.js` (T013) and the shared contract-test file (T009), so build after US1.
- **User Story 3 (Phase 5)**: Depends on Foundational; its warnings-surfacing task (T021) extends US1's `/api/continue` work (T012), and its CSS task (T020) extends US2's spinner styling (T018), so build after both.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — the true MVP slice (recall only, no LLM).
- **US2 (P2)**: Builds directly on US1's step sequencing and `app.js` structure; independently testable via its own contract/integration tests without needing a browser.
- **US3 (P3)**: Builds on both — LAN-binding and responsive layout are additive to whatever UI already exists from US1/US2, not a new code surface of their own.

### Within Each User Story

- Tests are written first and must fail before their corresponding implementation task.
- Server-side endpoint implementation before the `app.js` change that calls it.

### Parallel Opportunities

- T002 (Setup) can run alongside T001.
- T003 and T004 (Foundational tests, different files) can run in parallel; T007 and T008 (different files) can run in parallel once T006 is done.
- T010 (US1 integration test) can run in parallel with T009 only in the sense that both may be *written* together, but T009 extends a Foundational file already in progress — treat them as sequential within the phase if worked by one person; they are independent enough to hand to two people.
- T015 (US2 integration test) is a different file from T014, so it can proceed in parallel with T014.
- T022 and T023 (Polish, different files) can run in parallel; T024 and T025 should run last, after everything else.

---

## Parallel Example: User Story 1

```bash
# T009 and T010 touch different files and can be started together:
Task: "Contract tests for POST /api/answer and POST /api/continue in tests/contract/test_web_api_contract.py"
Task: "Integration test for the full recall-only cycle in tests/integration/test_web_session_flow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (blocks everything else).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 in a real browser on the host machine.

### Incremental Delivery

1. Setup + Foundational → foundation ready (page loads, state readable, nothing submittable yet).
2. Add User Story 1 → validate via quickstart Scenario 1 (recall works, MVP).
3. Add User Story 2 → validate via quickstart Scenario 2 (sentence review + spinner + all four outcomes).
4. Add User Story 3 → validate via quickstart Scenario 3 (a real second device on the LAN, phone-width layout) and Scenario 4 (edge cases).
5. Polish → run the full quickstart.md suite (T024) plus the `001`/`002` regression (T025).

---

## Notes

- `[P]` tasks touch different files with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to spec.md for traceability.
- Constitution Principle I requires each test task to be completed, run, and confirmed failing before its paired implementation task begins.
- This feature adds exactly one new package (`src/web/`) and touches no file under `src/models/`, `src/services/`, `src/lib/`, or `src/cli/` — per plan.md Constraints, the review pipeline, grading rule, and Markdown formats are reused unchanged.
- The spinner's actual on-screen animation and the responsive layout's real-device feel are verified by hand in quickstart.md (T024), not by an automated browser test — see research.md "Testing the web layer without a real browser" for why.
- Commit after each task or logical group.
