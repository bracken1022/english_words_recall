---

description: "Task list template for feature implementation"
---

# Tasks: Fix Web UI State Visibility

**Input**: Design documents from `/specs/005-fix-ui-visibility-bug/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. Given this is a single-root-cause CSS bug (research.md), the automated coverage is a static regression guard (the fix's mechanism is present in the shipped file) — the actual visual proof is the mandatory manual `quickstart.md` pass, since no automated test in this project can render CSS (research.md "Testing this without browser automation").

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`-`004`: `src/web/static/style.css`, `tests/unit/test_web_static_assets.py` at repository root. This is the smallest feature in the project so far — one file changed.

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed (a one-rule CSS fix plus a static-content test) — no `pyproject.toml` change expected

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A — the fix itself (one CSS rule) is User Story 1's own deliverable, not a shared prerequisite built before it. Proceed directly to Phase 3.

---

## Phase 3: Only the current step's question/answer content is shown (Priority: P1) 🎯 MVP

**Goal**: The empty-pool and session-complete messages, and each step's own content, are only ever rendered when their state actually applies — restoring what `app.js`'s already-correct `hidden`-toggling logic was supposed to produce all along.

**Independent Test**: In a real browser, step through a full practice cycle on a non-empty vocabulary set and confirm at each point that only that step's content is visible — see `quickstart.md` Scenarios 1-2.

### Tests for User Story 1 ⚠️ (write first, confirm it FAILS before implementing)

- [X] T002 [US1] Write a regression-guard test asserting `src/web/static/style.css` contains a rule targeting `[hidden]` that sets `display: none` with `!important` priority, per `research.md`'s chosen fix and `contracts/visibility-guarantee-contract.md` — in `tests/unit/test_web_static_assets.py`

### Implementation for User Story 1

- [X] T003 [US1] Add `[hidden] { display: none !important; }` to `src/web/static/style.css`, per research.md — no other rule in the file is removed or altered, so `section`/`.spinner`'s own `display: flex` still applies whenever they are *not* hidden (depends on T002)

**Checkpoint**: The regression-guard test passes. `quickstart.md` Scenarios 1-2 (empty/complete messages, recall-vs-sentence exclusivity) still need a real-browser pass — see Phase 5.

---

## Phase 4: The review-loading message only appears during an actual review (Priority: P2)

**Goal**: "Reviewing your sentence..." and its spinner are covered by the same fix, confirmed explicitly rather than assumed.

**Independent Test**: In a real browser, watch the sentence-practice step from before submission, through an in-progress review, to the result — see `quickstart.md` Scenario 3.

### Tests for User Story 2 ⚠️ (write first, confirm it FAILS before implementing)

- [X] T004 [P] [US2] Write a regression-guard test asserting the spinner element in `src/web/templates/index.html` uses the `hidden` boolean attribute (not an inline style or a separate, uncovered toggling mechanism), so it is provably covered by T003's global rule — in `tests/unit/test_web_static_assets.py` (different assertion than T002; may share the file)

### Implementation for User Story 2

- [X] T005 [US2] No separate implementation is needed: T003's fix already covers the spinner, since it also relies on the `hidden` attribute. This task is a no-op confirmation once T004 passes — recorded here for traceability, not because new code is required (depends on T003, T004)

**Checkpoint**: Both user stories' mechanism confirmed by the regression-guard tests. `quickstart.md` Scenario 3 still needs a real-browser pass — see Phase 5.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory real-browser validation

- [X] T006 [P] Run `ruff check` over `src/web/` and `tests/` and fix any issues
- [X] T007 Run all of `specs/005-fix-ui-visibility-bug/quickstart.md`'s scenarios end-to-end **in a real browser** (Scenarios 1-4) — this is the only way this feature's actual visual claims (SC-001 through SC-005) are verified; do not treat a green test suite alone as sufficient (research.md) — **verified**: real headless-Chrome screenshots (not just curl/DOM inspection) confirm Scenario 1's empty-pool case (only the empty message, nothing else) and Scenario 2 (recall step shows only the question+input; after submission, only word feedback + sentence prompt/input — the vocabulary-answer input is gone, matching the user's exact original complaint). The spinner's mid-request timing (Scenario 3, step 2) was **not** directly screenshotted — that needs live JS execution during an in-flight fetch (real interactive browser automation), out of scope per `003`'s established decision. Its correctness is inferred from the same `[hidden]` fix mechanism (T004's regression test) plus the fact its JS show/hide calls were already correct pre-fix, not directly observed. Scenario 4 (full `003`/`004` regression) confirmed via T008's full automated suite, not a manual re-click-through.
- [X] T008 Run the full existing `001`-`004` test suites unmodified and confirm every previously-passing test still passes, proving FR-008 (no regression to grading, the review pipeline, progress-log format, word-feedback rendering, the duplicate-submission guard, input/button grouping, or responsive layout)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — trivial (confirmation only).
- **Foundational (Phase 2)**: None for this feature — skipped.
- **User Story 1 (Phase 3)**: Depends on Setup only. This is the actual fix.
- **User Story 2 (Phase 4)**: Depends on User Story 1's fix (T003) already being in place — it has no code of its own, only a confirming test.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — the fix itself.
- **US2 (P2)**: Entirely dependent on US1's single CSS rule; contributes its own test to make that coverage explicit rather than assumed.

### Within Each User Story

- Tests are written first and must fail before their corresponding implementation task (T002 fails until T003 is applied; T004 should already pass once T003 lands, since the spinner already used `hidden` before this feature — confirming that is the point of T004/T005).

### Parallel Opportunities

- T004 (US2 test) can be written in parallel with T002 (US1 test) — different assertions, and neither depends on the other, though both live in the same file.
- T006 (Polish) can run alongside T007.

---

## Parallel Example: User Stories 1 & 2

```bash
# T002 and T004 are independent assertions and can be started together:
Task: "Regression-guard test for the [hidden] override rule in tests/unit/test_web_static_assets.py"
Task: "Regression-guard test confirming the spinner uses the hidden attribute in tests/unit/test_web_static_assets.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 3: User Story 1 — the actual fix.
3. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1-2 in a real browser.

### Incremental Delivery

1. Setup → User Story 1 → validate via quickstart Scenarios 1-2 (the core fix).
2. Add User Story 2 → validate via quickstart Scenario 3 (spinner, already covered — confirm it).
3. Polish → run quickstart Scenario 4 (full `003`/`004` regression) plus lint plus the full test suite.

---

## Notes

- `[P]` tasks touch different files or independent assertions with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to spec.md for traceability.
- This is the smallest feature in the project: one file changed
  (`src/web/static/style.css`, one rule added), one test file extended.
  No file under `src/models/`, `src/services/`, `src/lib/`, `src/cli/`, or
  `001`-`004`'s trees is touched.
- Do not consider this feature done when the test suite is green — T007's
  real-browser pass is the actual proof, per research.md and quickstart.md.
- Commit after each task or logical group.
