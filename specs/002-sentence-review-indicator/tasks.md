---

description: "Task list template for feature implementation"
---

# Tasks: Sentence-Review Loading Indicator

**Input**: Design documents from `/specs/002-sentence-review-indicator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature; this overrides the "tests optional" default.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Every task includes an exact file path

## Path Conventions

Single project (per plan.md, same layout as `001-vocab-recall-tutor`):
`src/{models,services,cli,lib}`, `tests/{contract,integration,unit}` at
repository root.

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is actually required

- [X] T001 Confirm `rich` is already declared as a dependency in `pyproject.toml` (it is, from `001-vocab-recall-tutor`) — no new dependency, version bump, or config change is needed for this feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A for this feature — there is no shared infrastructure to build
before User Story 1 that isn't already part of User Story 1 itself (the
`run_with_indicator` wrapper *is* the MVP deliverable, not a prerequisite to
it). Proceed directly to Phase 3.

---

## Phase 3: User Story 1 - See that the app is still working (Priority: P1) 🎯 MVP

**Goal**: An indeterminate, animating indicator appears immediately after the
learner submits a sentence and stays visible for the entire wait, with no
fabricated progress value; on non-interactive output it falls back to one
plain message instead of animating.

**Independent Test**: Submit a sentence with `request_correction` mocked to
delay before returning; confirm the indicator is active for the duration of
that call and never renders a percentage/step count (per
`contracts/loading-indicator-contract.md`).

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [P] [US1] Contract test for the timing/display-mode contract per `contracts/loading-indicator-contract.md`: with a fake terminal console (`is_terminal=True`), `run_with_indicator` enters `console.status(message, spinner="dots")` **before** calling `func` and exits it after `func` returns; with a fake non-terminal console (`is_terminal=False`), it calls `console.print(message)` once and never calls `console.status` at all — in `tests/contract/test_loading_indicator_contract.py`
- [X] T003 [P] [US1] Unit tests for `run_with_indicator`: `func` is called exactly once with the given `*args, **kwargs`; the function's return value is passed back unchanged; the fixed `message` string never contains a `%` character or digit sequence resembling a percentage/step count — in `tests/unit/test_loading_indicator.py`
- [X] T004 [P] [US1] Integration test: with `request_correction` mocked to block briefly before returning, submitting a sentence in `run_sentence_step` shows the indicator was active for that call and the existing correction feedback text appears afterward, unchanged from `001-vocab-recall-tutor`'s current behavior — extend `tests/integration/test_sentence_correction_flow.py`

### Implementation for User Story 1

- [X] T005 [US1] Implement `run_with_indicator(console, message, func, *args, **kwargs)` in `src/cli/loading_indicator.py` per `contracts/loading-indicator-contract.md`: terminal branch uses `console.status(message, spinner="dots")` around the call to `func`; non-terminal branch (`console.is_terminal` is `False`) calls `console.print(message)` once and does **not** call `console.status` (research.md: it renders nothing there); always returns `func`'s result unmodified; the indicator is stopped before any exception from `func` propagates (depends on T002, T003)
- [X] T006 [US1] Wire `run_sentence_step` in `src/cli/session.py` to call `request_correction(...)` only through `run_with_indicator(console, "Reviewing your sentence...", request_correction, target_expression, sentence, base_url=base_url, model=model)`, with no other change to its existing result-branching logic (FR-006) (depends on T005, T004)

**Checkpoint**: User Story 1 is fully functional and independently testable — the indicator reliably appears for the duration of a sentence review.

---

## Phase 4: User Story 2 - The indicator clears correctly however the review ends (Priority: P2)

**Goal**: In every existing review outcome (needs correction, already correct,
missing target expression, or unavailable), the indicator is gone by the time
that outcome's message is shown — never overlapping, never left behind, and
never artificially held on screen for a fast response.

**Independent Test**: Run each of the four existing outcome cases and confirm
the indicator is closed before each outcome's message prints; confirm a
near-instant response still clears cleanly with no added delay.

### Tests for User Story 2 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T007 [P] [US2] Extend `tests/integration/test_sentence_correction_flow.py`'s four existing outcome cases (needs-correction, already-correct, missing-expression, unavailable) to additionally assert the indicator was closed (the `console.status` context exited, or the non-terminal print already happened) before that case's feedback text is printed
- [X] T008 [P] [US2] Unit test proving no artificial delay exists: a `func` that returns immediately completes through `run_with_indicator` with no added sleep/minimum-duration logic — assert on elapsed wall-clock time being negligible (e.g., under 50ms) — in `tests/unit/test_loading_indicator.py`
- [X] T009 [P] [US2] Integration test for the non-interactive fallback per quickstart.md Scenario 3: with a non-terminal console, completing a sentence review still shows the one-line fallback message, produces no corrupted/ANSI output, and completes with correct feedback — in `tests/integration/test_non_interactive_output.py`

### Implementation for User Story 2

- [X] T010 [US2] Address any gap surfaced by T007-T009 (e.g., call-site ordering in `run_sentence_step` that could let feedback print before the indicator closes); if none is found, this task is a no-op confirmation recorded in the PR/commit notes (depends on T007, T008, T009)
- [X] T011 [US2] Run the full existing `001-vocab-recall-tutor` test suite (`tests/`) unmodified and confirm every previously-passing test still passes, proving FR-006 (learning behavior unchanged) — no file changes expected from this task itself

**Checkpoint**: User Stories 1 and 2 both function correctly; the full regression suite (001 + 002) is green.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and full end-to-end validation

- [X] T012 [P] Update root `README.md`'s "Running" section with a one-line note that sentence review now shows a progress spinner (or a plain message on non-interactive output)
- [X] T013 Run all of `specs/002-sentence-review-indicator/quickstart.md`'s scenarios end-to-end (interactive spinner, all four outcomes, non-interactive fallback, and the full `001-vocab-recall-tutor` regression) and fix any gaps found

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; trivial (confirmation only).
- **Foundational (Phase 2)**: None for this feature — skipped.
- **User Story 1 (Phase 3)**: Depends on Setup only. This is the whole MVP.
- **User Story 2 (Phase 4)**: Depends on User Story 1 (T005/T006) being in place — it tests and hardens the same wrapper's behavior across all outcomes rather than building new components.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — delivers the indicator itself. True MVP slice.
- **US2 (P2)**: Builds directly on US1's `run_with_indicator`/`session.py` wiring; not independently buildable without it, but independently *testable* (its tests target outcomes/timing, not new code surface).

### Within Each User Story

- Tests are written first and must fail before their corresponding implementation task.
- T005 (the wrapper) before T006 (wiring it into `session.py`).

### Parallel Opportunities

- T002, T003, T004 (US1 tests, different files) can run in parallel.
- T007, T008, T009 (US2 tests, different/extended files) can run in parallel.
- T012 (Polish, README) can run in parallel with T013's earlier scenarios, though T013 itself should run last as a final check.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for the timing/display-mode contract in tests/contract/test_loading_indicator_contract.py"
Task: "Unit tests for run_with_indicator in tests/unit/test_loading_indicator.py"
Task: "Integration test for a slow-review call in tests/integration/test_sentence_correction_flow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 3: User Story 1.
3. **STOP and VALIDATE**: run quickstart.md Scenario 1 and confirm the spinner appears and animates for the duration of a real (or deliberately slowed) review call.

### Incremental Delivery

1. Setup → User Story 1 → validate via quickstart Scenario 1 (MVP: the indicator exists and works).
2. Add User Story 2 → validate via quickstart Scenarios 2-3 (all outcomes clear correctly; non-interactive fallback is safe).
3. Polish → run quickstart Scenario 4 (full `001-vocab-recall-tutor` regression) plus the README note.

---

## Notes

- `[P]` tasks touch different files with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to spec.md for traceability.
- Constitution Principle I requires each test task to be completed, run, and confirmed failing before its paired implementation task begins.
- This feature changes exactly one existing file (`src/cli/session.py`, one call site) and adds exactly one new file (`src/cli/loading_indicator.py`); `src/models/`, `src/services/`, and `src/lib/` are untouched, per plan.md Constraints.
- Commit after each task or logical group.
