---

description: "Task list template for feature implementation"
---

# Tasks: Show a Correct Recall Result in Green

**Input**: Design documents from `/specs/008-correct-result-green/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md (all present; no `contracts/` — this feature adds no new interface)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. `plan.md`'s Constitution Check commits explicitly to this ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. This feature has exactly one user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`007`. This is the smallest feature in the project so far: one source file changed (`src/web/static/style.css`), one test file extended (`tests/unit/test_web_static_assets.py`) — no new files, directories, or dependencies (see `plan.md`'s Project Structure).

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed (a CSS-only color change plus a static-content test) — no `pyproject.toml` change expected

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A — the change itself (a color token pair plus one rule) is User Story 1's own deliverable, not a shared prerequisite built before it. Proceed directly to Phase 3.

---

## Phase 3: See a correct answer marked in green (Priority: P1) 🎯 MVP

**Goal**: The recall-step result banner shows green for a correct answer instead of the red used today, while an incorrect answer's appearance and the ✓/✗ symbol distinction stay exactly as they are.

**Independent Test**: In a real browser, answer a recall step correctly and confirm the result reads in green; answer incorrectly and confirm it's unchanged — see `quickstart.md` Scenarios 1–2.

### Tests for User Story 1 ⚠️ (write first, confirm it FAILS before implementing)

- [X] T002 [US1] Write a static-content regression test in `tests/unit/test_web_static_assets.py`: parse `src/web/static/style.css`, locate the `.feedback-correct { ... }` rule body (the color-override rule, not the existing `.feedback-correct::before` symbol rule), and assert it references a `--green` custom property and does **not** reference `--red`; separately assert `.feedback-incorrect` still resolves to `--red` (i.e., no new `.feedback-incorrect` color override rule was added) per `research.md` §2–3

### Implementation for User Story 1

- [X] T003 [US1] Add `--green: #2f6d3a;` and `--green-tint: #e3efe4;` to the light `:root` block in `src/web/static/style.css`, and `--green: #5fbd6e;` / `--green-tint: #1f3324;` to the existing `@media (prefers-color-scheme: dark) { :root { ... } }` block, alongside the existing `--red`/`--red-tint` tokens (depends on T002 failing for the right reason)
- [X] T004 [US1] Add a `.feedback-correct { color: var(--green); background: var(--green-tint); border-color: var(--green); }` rule in `src/web/static/style.css`, placed after the existing `#word-feedback` base rule so it overrides just those three properties — do not add or change anything in `.feedback-correct::before`, `.feedback-incorrect`, `#word-feedback`'s other properties, `src/web/static/app.js`, or `src/web/templates/index.html` (depends on T003, T002)

**Checkpoint**: User Story 1 is fully functional and testable independently — `quickstart.md` Scenarios 1–3 (correct is green, incorrect unchanged, still distinguishable without color) can be run once T001–T004 are done; see Phase 4 for the mandatory real-browser pass, including dark mode (Scenario 4).

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory real-browser validation (no JS/browser test runner in this project — see `research.md` §3)

- [X] T005 [P] Run `ruff check` over `src/web/` and `tests/` and fix any issues (unlikely to find anything — no Python changed — but confirms nothing else regressed)
- [X] T006 Run all of `quickstart.md`'s scenarios end-to-end **in a real browser**, in both light and dark presentations: a correct answer reads green, an incorrect answer is pixel-for-pixel unchanged from before this feature, both remain distinguishable with color removed, and the green is legible (not washed out) in dark mode — a green test suite alone only proves the CSS token changed, not that it looks right or stays legible, per `research.md` §1 and §3
- [X] T007 Run the full existing test suite (`pytest -q`) and confirm every previously-passing test still passes, proving no regression to grading, the review pipeline, the progress-log format, the session tally, the skip-word flow (`006`), or the collection-choice flow (`007`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — trivial (confirmation only).
- **Foundational (Phase 2)**: None for this feature — skipped.
- **User Story 1 (Phase 3)**: Depends on Setup only. This is the entire feature.
- **Polish (Phase 4)**: Depends on User Story 1 being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories or features — a self-contained color change.

### Within Each User Story

- T002 (test) is written first and must fail (`.feedback-correct` still resolves to `--red`, and `--green` doesn't exist yet) until T003/T004 land.

### Parallel Opportunities

- None meaningful within Phase 3 — T003 and T004 both touch `src/web/static/style.css` and are ordered (tokens must exist before the rule that references them).
- T005 (lint) can run alongside T006/T007 in Phase 4.

---

## Implementation Strategy

### MVP First (and only) — User Story 1

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 3: User Story 1 — the token pair and the one rule.
3. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1–4 in a real browser (light and dark).
4. Polish: lint plus the full regression suite.

---

## Notes

- `[P]` tasks touch different files or independent assertions with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to `spec.md` for traceability.
- This feature touches exactly one source file (`src/web/static/style.css`) and one test file (`tests/unit/test_web_static_assets.py`) — no file under `src/models/`, `src/services/`, `src/cli/`, `src/web/app.py`, `src/web/session_state.py`, `src/web/static/app.js`, or `src/web/templates/index.html` is touched.
- Do not consider this feature done when the test suite is green alone — T006's real-browser pass (light and dark) is the actual proof, per `research.md` and `quickstart.md`.
- Commit after each task or logical group.
