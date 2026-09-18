---

description: "Task list template for feature implementation"
---

# Tasks: Web UI State & Feedback Polish

**Input**: Design documents from `/specs/004-web-ui-ux-polish/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature; this overrides the "tests optional" default. For the pure-CSS/copy pieces (User Stories 2 and 3), tests are lightweight static-content assertions (the class names and wording actually exist in the shipped files) rather than rendered-pixel checks — deep visual verification stays manual in `quickstart.md`, matching the project's established convention (`002`/`003` research.md).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`/`002`/`003`: `src/web/{session_state.py,app.py,templates/,static/}`, `tests/{contract,integration,unit}` at repository root. This feature touches only files already established by `003-web-ui` plus one new test file.

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed (this feature is presentation changes plus one small backend field-exposure change) — no `pyproject.toml` change expected

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A for this feature — the backend/structural change that might otherwise be "foundational" (`session_state.py`'s new fields and guard, and moving the word-feedback element out of the per-step sections) is itself User Story 1's own independent deliverable, not a prerequisite shared by stories that don't need it. Proceed directly to Phase 3.

---

## Phase 3: User Story 1 - The page always shows exactly one step's controls (Priority: P1) 🎯 MVP

**Goal**: The sentence-practice section stays hidden until the vocabulary answer is submitted, then shows together with the word feedback (regardless of correctness); the loading state is visible only while a review is actually in progress; a second sentence submission is prevented, both in the UI and on the server, while one is outstanding.

**Independent Test**: Drive the app through load → submit word answer → submit sentence → review completes, confirming at each point that exactly one primary area plus (where applicable) the persistent word-feedback element is visible, that a reload mid-sentence-step still shows the word feedback, and that a second sentence submission while one is in flight is rejected.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [US1] Unit tests for `PracticeSession.state()` per data-model.md: the `"sentence"` and `"feedback"` steps include `answer` and `correct` (sourced from `pending_attempt`); the `"recall"`, `"empty"`, and `"complete"` steps do not include them — in `tests/unit/test_session_state.py`
- [X] T003 [US1] Unit test for the server-side duplicate-submission guard per research.md's deterministic re-entrant approach: a `correction_fn` that calls `submit_sentence` again on the same `PracticeSession` from inside itself causes that inner call to raise `WrongStepError` — in `tests/unit/test_session_state.py` (same file as T002, sequential)
- [X] T004 [P] [US1] Contract tests for the additive `GET /api/state` fields (`answer`/`correct` present for `"sentence"`/`"feedback"`, absent otherwise) and for `POST /api/sentence`'s new `409` when a review is already in progress, per `contracts/web-api-contract-delta.md` — in `tests/contract/test_web_api_contract.py`
- [X] T005 [P] [US1] Integration test: after submitting a vocabulary answer (both a correct case and an incorrect case), the word feedback and the sentence-practice prompt/input are both present in `GET /api/state`'s response at once; a second `POST /api/sentence` sent while `_review_in_progress` is `True` is rejected with `409` — in `tests/integration/test_web_session_flow.py`
- [X] T006 [P] [US1] New test file asserting `templates/index.html` has a word-feedback element that exists outside the `recall-view`/`sentence-view`/`feedback-view` `<section>` elements (a simple string/structure check, not a rendering check) — in `tests/unit/test_web_static_assets.py`

### Implementation for User Story 1

- [X] T007 [US1] In `src/web/session_state.py`: add a `_review_in_progress` bool (per data-model.md), set before calling `correction_fn` in `submit_sentence` and cleared in a `finally`; raise `WrongStepError` if `submit_sentence` is called while it's already `True`; extend `state()` to include `answer`/`correct` for the `"sentence"`/`"feedback"` steps, read from `pending_attempt` (depends on T002, T003)
- [X] T008 [US1] Restructure `src/web/templates/index.html`: move the word-feedback element out of `#recall-view` into its own element that isn't inside any of the five `showOnly()`-managed `<section>`s (depends on T006)
- [X] T009 [US1] Update `src/web/static/app.js`: render the word-feedback element from `GET /api/state`'s `answer`/`correct` fields whenever `step` is `"sentence"` or `"feedback"` (not only from the transient `POST /api/answer` response, so it survives a reload); disable the sentence form's input and button for the duration of the `fetch("/api/sentence")` call, re-enabling in its `finally` (depends on T007, T008, T004, T005)

**Checkpoint**: User Story 1 is fully functional — sentence-section timing, word-feedback persistence (including across a reload), and the duplicate-submission guard (client + server) are all in place.

---

## Phase 4: User Story 2 - Word-answer feedback is clear without relying on color alone (Priority: P2)

**Goal**: Word-answer feedback is shown in a distinct color per outcome (green/red) and always paired with explicit "Correct"/"Incorrect" wording, exactly matching the requested format.

**Independent Test**: Submit a correct and an incorrect word answer; confirm each result's text alone states the outcome, and that each is styled with its own distinct color class.

### Tests for User Story 2 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T010 [P] [US2] Test asserting `src/web/static/style.css` defines `.feedback-correct` and `.feedback-incorrect` selectors, and that `src/web/static/app.js` contains the literal wording fragments `"Correct:"` and `"Incorrect. The correct expression is:"` per `contracts/ui-rendering-contract.md` — in `tests/unit/test_web_static_assets.py` (extends T006's file)

### Implementation for User Story 2

- [X] T011 [US2] Add `.feedback-correct { color: <green> }` and `.feedback-incorrect { color: <red> }` to `src/web/static/style.css`; update the word-feedback rendering in `src/web/static/app.js` (built in T009) to toggle the matching class based on `correct` and to use the exact wording `Correct: <expressions>` / `Incorrect. The correct expression is: <expressions>` (depends on T010, T009)

**Checkpoint**: User Stories 1 and 2 both hold — word feedback is shown at the right time (US1) and is unambiguous without color (US2).

---

## Phase 5: User Story 3 - The word-answer input and its submit control read as one unit (Priority: P3)

**Goal**: The vocabulary-answer input and its submit button (and, for consistency, the sentence input and its button) are presented as one visually grouped row, never with the button pushed onto its own line.

**Independent Test**: View the vocabulary-question step at both desktop and phone widths and confirm the input and button are adjacent, not detached.

### Tests for User Story 3 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T012 [P] [US3] Test asserting `src/web/static/style.css` defines a `.field-row` selector using a row flex layout, and that both the `answer-form` and `sentence-form` in `templates/index.html` wrap their input and button in an element carrying that class — in `tests/unit/test_web_static_assets.py` (extends T006/T010's file)

### Implementation for User Story 3

- [X] T013 [US3] In `src/web/templates/index.html`, wrap each `<input>`+`<button>` pair (in both `answer-form` and `sentence-form`) in a `.field-row` container; in `src/web/static/style.css`, add `.field-row { display: flex; gap: 8px; }` with the input set to `flex: 1` instead of `width: 100%` (removing the rule that pushes the button onto its own line), keeping the existing mobile-first/responsive rules from `003-web-ui`'s `responsive-layout-contract.md` intact (depends on T012)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint and full end-to-end validation

- [X] T014 [P] Run `ruff check` over `src/web/` and `tests/` and fix any issues
- [X] T015 Run all of `specs/004-web-ui-ux-polish/quickstart.md`'s scenarios end-to-end (real browser: grouping at both widths, color+text feedback, sentence-section timing across a reload, loading-state timing, and the duplicate-submission guard from a second tab if testable) and fix any gaps found
- [X] T016 Run the full existing `001-vocab-recall-tutor`, `002-sentence-review-indicator`, and `003-web-ui` test suites unmodified and confirm every previously-passing test still passes, proving FR-011 (grading, review pipeline, and progress log unchanged)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; trivial (confirmation only).
- **Foundational (Phase 2)**: None for this feature — skipped.
- **User Story 1 (Phase 3)**: Depends on Setup only. This is the MVP — it fixes the two real *behavioral* bugs (lost word feedback, no duplicate-submission guard) and the sentence-timing requirement.
- **User Story 2 (Phase 4)**: Depends on User Story 1 having built the persistent word-feedback element (T008/T009) — it only adds color/wording on top of that element.
- **User Story 3 (Phase 5)**: Independent of User Stories 1 and 2 at the code level (a different part of the template/CSS), but sequenced last here since it's the lowest-priority, purely cosmetic change.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — fixes the real behavioral bugs found in `research.md`.
- **US2 (P2)**: Builds directly on US1's word-feedback element; not meaningfully separable from it in the code, though its own test/behavior (color + wording) is independently verifiable.
- **US3 (P3)**: No code dependency on US1/US2 — could be done in parallel by a second person, but is sequenced last here since it's cosmetic-only.

### Within Each User Story

- Tests are written first and must fail before their corresponding implementation task.

### Parallel Opportunities

- T004, T005, T006 (US1 tests, different files) can run in parallel; T002/T003 are sequential with each other (same file).
- T010 (US2) and T012 (US3) touch the same test file as T006 but can still be handed to different people since they're additive to a shared file already scaffolded by T006 — treat as sequential if worked solo.
- T014 (Polish) can run alongside the early parts of T015.

---

## Parallel Example: User Story 1

```bash
# T004, T005, and T006 touch different files and can be started together:
Task: "Contract tests for the extended GET /api/state fields in tests/contract/test_web_api_contract.py"
Task: "Integration test for combined word-feedback + sentence visibility and the duplicate-submission 409 in tests/integration/test_web_session_flow.py"
Task: "Static-structure test for the persistent word-feedback element in tests/unit/test_web_static_assets.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 3: User Story 1.
3. **STOP and VALIDATE**: run quickstart.md Scenarios 3, 4, and 5 — the real bugs (lost word feedback, missing duplicate-submission guard) are fixed.

### Incremental Delivery

1. Setup → User Story 1 → validate via quickstart Scenarios 3-5 (the behavioral fixes).
2. Add User Story 2 → validate via quickstart Scenario 2 (color + wording).
3. Add User Story 3 → validate via quickstart Scenario 1 (grouping).
4. Polish → run quickstart Scenario 6 (full `001`/`002`/`003` regression) plus lint.

---

## Notes

- `[P]` tasks touch different files with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to spec.md for traceability.
- Constitution Principle I requires each test task to be completed, run, and confirmed failing before its paired implementation task begins — for User Stories 2 and 3, "failing" means the asserted class/wording/structure doesn't exist yet, which is still a meaningful red-green cycle even though the checks are static-content assertions rather than rendered-output checks.
- This feature touches no file under `src/models/`, `src/services/`, or `src/lib/`, and no file in `001`/`002`'s trees — per plan.md Constraints, grading, the review pipeline, and the progress-log format are untouched.
- Commit after each task or logical group.
