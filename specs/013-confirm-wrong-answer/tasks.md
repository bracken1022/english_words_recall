---

description: "Task list template for feature implementation"
---

# Tasks: Require Confirmation Before Advancing Past a Wrong Recall-Only Answer

**Input**: Design documents from `/specs/013-confirm-wrong-answer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. `plan.md`'s Constitution Check commits explicitly to this ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. This feature has exactly one user story, realized across two entry points (CLI and web UI), per spec.md FR-007.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`012`. No new files anywhere in `src/`; one existing test needs its expectations updated (it currently asserts behavior this feature intentionally changes) alongside new tests.

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed — this feature reuses `PracticeAttempt`, `append_attempt`, and `_advance_after_attempt` (all already existing since spec `012`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A — this feature has a single user story realized directly across the CLI and web entry points, with no shared prerequisite beyond Setup. Proceed directly to Phase 3.

---

## Phase 3: Manually confirm before moving on from a missed word (Priority: P1) 🎯 MVP

**Goal**: In recall-only mode, a correct answer keeps today's exact brief-auto-advance behavior; an incorrect answer now reveals the correct expression and waits indefinitely for the learner to explicitly continue, on both the CLI and the web UI.

**Independent Test**: Practice in recall-only mode; answer one word correctly (session still auto-advances) and one word incorrectly (session waits, correct expression stays visible, only advances once the learner explicitly continues).

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [P] [US1] In `tests/unit/test_session_state.py`: **update** the existing `test_submit_answer_recall_only_skips_sentence_step_and_advances` test — it currently submits a wrong answer (`"wrong"`) and asserts the session auto-advances straight to `"complete"`; per `data-model.md`, a wrong recall-only answer must now land on `self.step == "reveal"` instead, with `self.pending_attempt` still held, `self.current_index` unchanged, and nothing new written to the progress log yet — update this test's assertions for the wrong-answer case accordingly (the correct-answer case earlier in the same test is unaffected and must keep passing as-is). Then add: a test that `continue_to_next()` from `"reveal"` appends the held attempt to the progress log (no `sentence`/`feedback` fields, matching `skip_sentence()`'s shape), does not increment `correct_count` (since the attempt was incorrect), advances `current_index`, and lands on `"complete"`/`"recall"`; a test that `state()` for step `"reveal"` includes `accepted_expressions`/`answer`/`correct` (same fields `"sentence"`/`"feedback"` already expose) but no `sentence`/`feedback` dict fields; a regression test explicitly confirming the correct-answer recall-only path (`submit_answer()` → immediate `append_attempt()` + `_advance_after_attempt()`, landing on `"recall"`/`"complete"` directly, never `"reveal"`) is unchanged
- [X] T003 [P] [US1] In `tests/integration/test_session_mode.py`: add a CLI-level test that a wrong recall-only answer blocks on an extra `input()` call before the next word's Chinese meaning is printed — monkeypatch `builtins.input` with one extra scripted blank-string value after the wrong answer, and assert the progress log records both words only after all scripted inputs are consumed (mirroring this file's existing `monkeypatch.setattr("builtins.input", ...)` style); assert a correct recall-only answer needs no extra input value (regression guard)
- [X] T004 [P] [US1] In `tests/contract/test_web_api_contract.py`: add contract tests per `contracts/web-api-contract-delta.md` — `POST /api/continue` returns `200` from step `"reveal"` (previously step `"reveal"` didn't exist); a full flow test: `POST /api/select` with `mode: "recall-only"`, `POST /api/answer` with a wrong answer → `GET /api/state`'s `step` is `"reveal"` and the progress-log file does not yet contain that word's entry → `POST /api/continue` → `GET /api/state` shows the session advanced (`"recall"`/`"complete"`) and the progress-log file now contains the word's entry with no `sentence`/`feedback` fields; `POST /api/continue` still returns `409` from `"recall"`, `"sentence"`, and `"choose"` (regression guard, unchanged from spec `007`)
- [X] T005 [P] [US1] In `tests/unit/test_web_static_assets.py`: add assertions that `#continue-button` in `src/web/templates/index.html` sits **outside** `#feedback-view`'s bounds (mirroring the existing `test_word_feedback_element_exists_outside_step_sections` pattern for `#word-feedback`); add an assertion that `src/web/static/app.js` checks for `state.step === "reveal"` in the answer-submit handler and does not schedule its `setTimeout`-based auto-advance in that branch

### Implementation for User Story 1

- [X] T006 [US1] In `src/web/session_state.py`: add `"reveal"` to the `Step` type comment; in `submit_answer()`, when `self.recall_only` and the answer is **incorrect**, stash the attempt in `self.pending_attempt` (same shape as today's recall-only correct-answer attempt dict — `timestamp`, `item`, `answer`, `correct`) and set `self.step = "reveal"`, instead of finalizing immediately (the correct-answer branch is unchanged); in `continue_to_next()`, add a branch for `self.step == "reveal"` that calls `append_attempt(self.progress_file, PracticeAttempt(**self.pending_attempt))` then `self._advance_after_attempt(self.pending_attempt["correct"])` (mirroring `skip_sentence()`'s append-then-advance shape); extend `state()`'s existing `if self.step in ("sentence", "feedback"):` condition to `("sentence", "feedback", "reveal")` so `accepted_expressions`/`answer`/`correct` are exposed for `"reveal"` too — the `if self.step == "feedback":` block below it (which sets `sentence`/`feedback`) stays untouched, so those fields correctly stay absent for `"reveal"` (depends on T002 failing for the right reason)
- [X] T007 [US1] In `src/cli/session.py`: add a private `_wait_for_continue(prompt: str = "Press Enter to continue...") -> None` helper (a thin wrapper around `input()`, mirroring `_default_answer_input()`'s directness); in `run_session()`'s loop, when `mode == "recall-only"` and `not recall_attempt.correct`, call `_wait_for_continue()` immediately before the existing `append_attempt()` call for that item; when correct, or when `mode == "sentence"`, behavior is unchanged (depends on T003 failing for the right reason)
- [X] T008 [P] [US1] In `src/web/templates/index.html`: move `<button id="continue-button" type="button">Continue</button>` out of `#feedback-view` to be a persistent, top-level element (alongside `#word-feedback`, following the same pattern spec `004` already established for that element) — no change to the button's id, type, or label
- [X] T009 [US1] In `src/web/static/app.js`: add a `renderContinueButton(state)` helper that sets `continueButton.hidden = !(state.step === "feedback" || state.step === "reveal")`, called from `renderState()` alongside the existing `renderWordFeedback(state)` call; extend `renderWordFeedback()`'s existing `state.step === "sentence" || state.step === "feedback"` condition to also include `"reveal"`; in the answer-submit handler, add a branch for `state.step === "reveal"` that calls `renderState(state)` and returns immediately — no `setTimeout`, no disabling/re-enabling the input, no auto-advance — leaving the existing sentence-mode branch and the existing correct-answer timed-auto-advance branch both unchanged (depends on T006, T008, T004, T005)

**Checkpoint**: User Story 1 is fully functional and testable independently — `quickstart.md` Scenarios 1–5 (CLI correct/wrong, web correct/wrong, sentence mode unaffected) can be run once T001–T009 are done; see Phase 4 for the mandatory manual pass.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory manual validation

- [X] T010 [P] Run `ruff check` over `src/cli/`, `src/web/`, and `tests/` and fix any issues
- [X] T011 Run all of `quickstart.md`'s scenarios end-to-end: CLI correct (unchanged) and CLI wrong (waits for Enter), web correct (unchanged brief auto-advance) and web wrong (waits for an explicit Continue click, expression stays visible indefinitely), and sentence mode completely unaffected — a passing test suite proves the branch logic is invoked correctly, not that the resulting practice flow actually feels right end-to-end
- [X] T012 Run the full existing test suite (`pytest -q`) and confirm every previously-passing test still passes (aside from the one test T002 intentionally updates), proving no regression to grading, the review pipeline, the progress-log format, the session tally, the skip-word flow (`006`), the collection-choice flow (`007`), the correct-result color (`008`), voice input (`009`), the Judge/Teacher correction split (`010`), word order (`011`), or the rest of recall-only mode (`012`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — trivial (confirmation only).
- **Foundational (Phase 2)**: None for this feature — skipped.
- **User Story 1 (Phase 3)**: Depends on Setup only. This is the entire feature.
- **Polish (Phase 4)**: Depends on User Story 1 being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — realized across two independent entry points (CLI, web) that share no code path with each other for this feature.

### Within Each User Story

- Tests are written first and must fail (or, for T002's updated assertion, fail against the *new* expectation) before their corresponding implementation task: T002 fails until T006 lands; T003 fails until T007 lands; T004 fails until T006 lands; T005 fails until T008/T009 land.
- T006 (web session core) and T007 (CLI session core) touch entirely different files and have no dependency on each other — genuinely parallel once their respective tests exist.
- T008 (template) has no dependency on T006/T007 and can proceed at any time; T009 (app.js) depends on T006 (the `"reveal"` step must exist to reach), T008 (the button's new markup location), T004, and T005.

### Parallel Opportunities

- T002, T003, T004, T005 are four independent test files/concerns and can be started together.
- T006 (web core) and T007 (CLI core) are independent files and can proceed in parallel; T008 (template) can also proceed independently of both.
- T010 (lint) can run alongside T011/T012 in Phase 4.

---

## Parallel Example: User Story 1

```bash
# T002, T003, T004, T005 are independent test files and can be started together:
Task: "update + add 'reveal'-branch unit tests in tests/unit/test_session_state.py"
Task: "CLI wrong-answer pause test in tests/integration/test_session_mode.py"
Task: "POST /api/continue 'reveal'-step contract tests in tests/contract/test_web_api_contract.py"
Task: "moved continue-button + app.js 'reveal'-branch assertions in tests/unit/test_web_static_assets.py"

# T006 (web) and T007 (CLI) touch different files and can proceed together once their tests exist:
Task: "'reveal' step + continue_to_next() branch in src/web/session_state.py"
Task: "_wait_for_continue() gate in src/cli/session.py"
```

---

## Implementation Strategy

### MVP First (and only) — User Story 1

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 3: User Story 1 — both entry points.
3. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1–5.
4. Polish: lint plus the full regression suite.

---

## Notes

- `[P]` tasks touch different files or independent assertions with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to `spec.md` for traceability.
- This feature touches `src/web/session_state.py`, `src/web/templates/index.html`, `src/web/static/app.js`, and `src/cli/session.py` — **not** `src/web/app.py` (no route changes — `POST /api/continue` already dispatches to `continue_to_next()`), and no file under `src/models/`, `src/services/`, or `src/lib/`.
- T002 is the one place this feature knowingly changes an existing test's expected outcome rather than only adding new tests — call this out explicitly when reviewing the diff, since it's easy to mistake for an accidental regression rather than the intended behavior change.
- Do not consider this feature done when the test suite is green alone — T011's manual pass is what actually verifies the wait-for-continue behavior feels right end-to-end in both interfaces, per `research.md` and `quickstart.md`.
- Commit after each task or logical group.
