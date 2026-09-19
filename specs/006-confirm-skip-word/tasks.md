---

description: "Task list template for feature implementation"
---

# Tasks: Confirm Before Skipping a Word Without a Sentence

**Input**: Design documents from `/specs/006-confirm-skip-word/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. `plan.md`'s Constitution Check commits explicitly to this ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`005`. Touches `src/web/session_state.py`, `src/web/app.py`, `src/web/static/app.js`, and three existing test files — no new files, directories, or dependencies (see `research.md` §5 and `plan.md`'s Project Structure).

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed (reuses Flask, PyYAML, pytest already in `pyproject.toml`) — no `pyproject.toml` change expected

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A — the new endpoint and state transition are User Story 1's own deliverable, not a shared prerequisite built before it. Proceed directly to Phase 3.

---

## Phase 3: Confirm before skipping an unwritten sentence (Priority: P1) 🎯 MVP

**Goal**: Submitting the sentence-writing step with an empty or whitespace-only sentence shows a confirmation prompt instead of silently proceeding; confirming skips straight to the next word (or completion) with no correction request ever made; declining leaves everything unchanged.

**Independent Test**: In a real browser, reach the sentence step, submit empty, confirm the prompt, and verify the session advances with no "Reviewing your sentence..." ever shown — see `quickstart.md` Scenarios 1–2.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [P] [US1] Write unit tests for a new `PracticeSession.skip_sentence()` method in `tests/unit/test_session_state.py`: raises `WrongStepError` when `step != "sentence"` (matching every other transition method's convention); when valid, advances `current_index` and sets `step` to `"recall"` (more items remain) or `"complete"` (this was the last item), per `data-model.md`'s state-machine table; updates `correct_count` from the already-known `pending_attempt["correct"]` exactly as `continue_to_next()` does; clears `pending_attempt`/`last_correction`; never sets `step` to `"feedback"`
- [X] T003 [P] [US1] Write contract tests for `POST /api/skip` in `tests/contract/test_web_api_contract.py`, per `contracts/web-api-contract-delta.md`: `200` + `GET /api/state`-shaped body when `step == "sentence"` (mid-session → `"recall"`; last item → `"complete"` with `total`/`correct` fields); `409 Conflict` + `{"error": "not awaiting a sentence"}` + no state change when `step != "sentence"`; and — patching `request_correction` the same way existing sentence tests do — assert it is **never called** for this path
- [X] T004 [P] [US1] Write a static-content assertion in `tests/unit/test_web_static_assets.py` confirming `src/web/static/app.js` contains the empty/whitespace check on the sentence input, a call to a confirmation dialog, and a fetch to `/api/skip`, per `research.md` §1–2

### Implementation for User Story 1

- [X] T005 [US1] Implement `PracticeSession.skip_sentence()` in `src/web/session_state.py`: valid only when `self.step == "sentence"` (else raise `WrongStepError("not awaiting a sentence")`, matching `POST /api/skip`'s contracted error message); construct a `PracticeAttempt` from `self.pending_attempt` with `sentence=None`/`feedback=None` and pass it to `append_attempt(self.progress_file, attempt)`; if `self.pending_attempt["correct"]` is true, increment `self.correct_count`; clear `pending_attempt`/`last_correction`; advance `current_index`; set `step` to `"complete"` if `current_index >= len(self.items)` else `"recall"` (depends on T002 failing for the right reason)
- [X] T006 [US1] Add the `POST /api/skip` route in `src/web/app.py`, following the exact pattern of the existing `post_continue` route: call `session.skip_sentence()`, catch `WrongStepError` and return `jsonify({"error": str(exc)}), 409`, otherwise return `jsonify(session.state())` (depends on T005, T003)
- [X] T007 [P] [US1] Update the `sentenceForm` submit handler in `src/web/static/app.js`: at the top of the handler (before the existing `spinnerEl.hidden = false` block), check `sentenceInput.value.trim() === ""`; if empty, call `window.confirm("You didn't write a sentence — skip this word?")` — if the learner cancels, `return` immediately with no further action and no state change; if they confirm, `await fetch("/api/skip", { method: "POST" })` then `await fetchState()` and `return` (skipping the existing spinner/`/api/sentence` logic entirely for this submission); if the sentence is non-empty, fall through to the existing unchanged behavior (depends on T004, T006)

**Checkpoint**: User Story 1 is fully functional and testable independently — `quickstart.md` Scenarios 1–2 (mid-session skip with confirm/decline, last-word skip reaching completion) can be run once T001–T007 are done; see Phase 5 for the mandatory real-browser pass.

---

## Phase 4: Skipped words still show up correctly afterward (Priority: P2)

**Goal**: A skipped word's recall correctness still counts in the end-of-session tally, and its saved practice-history entry is distinguishable from a word where a sentence was actually submitted.

**Independent Test**: Skip at least one word in an otherwise-normal session and confirm the end-of-session summary and the progress file both reflect it accurately — see `quickstart.md` Scenario 3.

### Tests for User Story 2 ⚠️ (write first, confirm it FAILS before implementation is confirmed correct)

- [X] T008 [P] [US2] Write an integration test in `tests/integration/test_web_session_flow.py` covering a full session that mixes a completed word and a skipped word: submit a recall answer, skip the sentence step via `POST /api/skip`, continue to the next word (or reach `"complete"` directly if it was last), and assert (a) `GET /api/state`'s `"complete"` `total`/`correct` fields count the skipped word's recall correctness exactly as they would a completed one, and (b) reading the progress file back shows the skipped word's block has no `sentence`/`feedback` keys while a completed word's block still has both, per `data-model.md`'s progress-log examples

### Implementation for User Story 2

- [X] T009 [US2] No new code is required: T005's `skip_sentence()` already updates `correct_count` and calls `append_attempt` with the no-sentence shape (`data-model.md` §"PracticeAttempt" / §"Progress log"). This task is a no-op confirmation once T008 passes — recorded here for traceability, not because new code is needed (depends on T005, T008)

**Checkpoint**: Both user stories' mechanisms are confirmed by automated tests. `quickstart.md` Scenario 3's progress-file inspection still benefits from one manual read-through — see Phase 5.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory real-browser validation (no JS test runner in this project — see `research.md` §5)

- [X] T010 [P] Run `ruff check` over `src/web/` and `tests/` and fix any issues
- [X] T011 Run all of `quickstart.md`'s scenarios end-to-end **in a real browser**: empty-submit confirm/decline/confirm, last-word skip reaching "Session complete", the tally and progress-file check, and a normal non-empty sentence submission showing no prompt at all — this is the only way the actual confirm-dialog UX (SC-001–SC-003) is verified; a green test suite alone is not sufficient, since `T004`/`T008` only prove the wiring and bookkeeping exist, not that the dialog itself appears/behaves correctly for a person
- [X] T012 Run the full existing test suite (`pytest -q`) and confirm every previously-passing test still passes, proving no regression to grading, the review pipeline, the progress-log format, the session tally, or the recall/sentence/feedback state machine for non-skipped words

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — trivial (confirmation only).
- **Foundational (Phase 2)**: None for this feature — skipped.
- **User Story 1 (Phase 3)**: Depends on Setup only. This is the actual feature.
- **User Story 2 (Phase 4)**: Depends on User Story 1's implementation (T005) already being in place — it contributes its own test to make already-existing bookkeeping explicit rather than assumed.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — the confirm/skip mechanism itself.
- **US2 (P2)**: Entirely dependent on US1's `skip_sentence()`/`/api/skip`; adds no new production code, only a confirming integration test.

### Within Each User Story

- Tests are written first and must fail before their corresponding implementation task: T002 fails until T005 exists; T003 fails (404/405) until T006 exists; T004 fails until T007 exists; T008 fails until T005/T006 exist.

### Parallel Opportunities

- T002, T003, T004 are independent assertions in three different files and can be written together.
- T007 (`app.js`) touches a different file than T005/T006 (`session_state.py`/`app.py`) and can be worked on in parallel with them, though it isn't meaningfully testable end-to-end until T006 lands.
- T010 (lint) can run alongside T011/T012.

---

## Parallel Example: User Story 1

```bash
# T002, T003, T004 are independent test files and can be started together:
Task: "Unit tests for skip_sentence() in tests/unit/test_session_state.py"
Task: "Contract tests for POST /api/skip in tests/contract/test_web_api_contract.py"
Task: "Static-content assertion for app.js's skip wiring in tests/unit/test_web_static_assets.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 3: User Story 1 — the confirm/skip mechanism.
3. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1–2 in a real browser.

### Incremental Delivery

1. Setup → User Story 1 → validate via quickstart Scenarios 1–2 (the core feature).
2. Add User Story 2 → validate via quickstart Scenario 3 (tally + progress-log accuracy).
3. Polish → run all quickstart scenarios, lint, and the full test suite.

---

## Notes

- `[P]` tasks touch different files or independent assertions with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to `spec.md` for traceability.
- This feature touches three existing files in `src/` (`session_state.py`, `app.py`, `static/app.js`) and extends three existing test files — no new files, models, or dependencies (see `plan.md`'s Project Structure).
- Do not consider this feature done when the test suite is green alone — T011's real-browser pass is what actually verifies the confirmation dialog's behavior, per `research.md` §5 and `quickstart.md`.
- Commit after each task or logical group.
