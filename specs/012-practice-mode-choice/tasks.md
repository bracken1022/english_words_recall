---

description: "Task list template for feature implementation"
---

# Tasks: Choose Recall-Only or Sentence Practice Mode

**Input**: Design documents from `/specs/012-practice-mode-choice/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. `plan.md`'s Constitution Check commits explicitly to this ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. This feature has exactly one user story, realized across two entry points (CLI and web UI) per spec.md FR-007.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`011`. Continues `011`'s precedent of touching both `src/cli/` and `src/web/` in the same change — no new files in `src/`, one new test file for the CLI-level mode tests.

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed — `mode` reuses the existing `PracticeAttempt`/`append_attempt` machinery, no new library required

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A — this feature has a single user story realized directly across the CLI and web entry points, with no shared prerequisite beyond Setup. Proceed directly to Phase 3.

---

## Phase 3: Choose recall-only or sentence practice before starting (Priority: P1) 🎯 MVP

**Goal**: Both the CLI and the web UI let the learner choose, once before a session starts, between today's sentence mode (recall → write a sentence → correction feedback) and a new recall-only mode (recall → straight to the next word/completion, no sentence step, no correction call at all).

**Independent Test**: Start a session, choose recall-only mode, and confirm that after answering each word the session goes straight to the next word (or completion) with no sentence prompt ever shown and no correction request made, while the completion tally still reflects every word's recall outcome.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [P] [US1] Write unit tests in `tests/unit/test_session_state.py` for the new `mode`/`self.recall_only`, per `data-model.md`: `PracticeSession.__init__(..., mode="recall-only")` in the locked branch sets `self.recall_only is True`; `mode="sentence"`/default sets it `False`; `select_collection(key, mode="recall-only")` sets `self.recall_only is True`, `mode="sentence"`/default sets it `False`; `submit_answer()` on a recall-only session (patch `src.web.session_state.request_correction` and assert it's never called) advances `self.step` directly to `"recall"` (more items) or `"complete"` (last item) — never `"sentence"` — tallies `correct_count` when correct, and writes a progress-log entry with no `sentence`/`feedback` fields (same shape as `skip_sentence()`'s existing entries); a sentence-mode/default session's `submit_answer()` behavior is unchanged (still lands on `"sentence"`)
- [X] T003 [P] [US1] Write a new integration test file `tests/integration/test_session_mode.py`, mirroring `test_session_group_filter.py`/`test_session_order.py`'s style (mocking `request_correction`, monkeypatching `builtins.input`): `run_session(..., mode="recall-only")` never calls `request_correction`, and the progress log records every word with no `sentence:`/`feedback:` lines; `mode="sentence"`/default is unaffected (unchanged existing behavior, `request_correction` still called once per word)
- [X] T004 [P] [US1] Write contract tests in `tests/contract/test_web_api_contract.py` for `POST /api/select`'s new `"mode"` field, per `contracts/web-api-contract-delta.md`: `{"collection": "unit1", "mode": "recall-only"}` is accepted (`200`); `"mode"` absent or an unrecognized value defaults to `"sentence"` (no behavior change); a full recall-only flow through the Flask test client — `POST /api/select` with `mode: "recall-only"`, then `POST /api/answer` — lands `GET /api/state`'s `step` on `"recall"`/`"complete"`, never `"sentence"`, and `request_correction` (patched) is never called; `"collection"` is still required regardless of `"mode"`'s presence, unchanged from `007`
- [X] T005 [P] [US1] Write a static-content assertion in `tests/unit/test_web_static_assets.py` confirming `src/web/static/app.js` tracks a selected mode and includes a `"mode"` key in the JSON body it posts to `/api/select`, and that `src/web/templates/index.html`'s `#choose-view` offers a mode toggle (`sentence`/`recall-only` options) alongside the existing order toggle

### Implementation for User Story 1

- [X] T006 [US1] In `src/web/session_state.py`: add `mode: str = "sentence"` to `PracticeSession.__init__`, setting `self.recall_only = mode == "recall-only"` in the existing `group_locked` (`else`) branch, and `self.recall_only = False` as a placeholder in the interactive branch (governed instead by `select_collection()`'s own `mode` argument, per `data-model.md`); add the same `mode: str = "sentence"` parameter to `select_collection`, setting `self.recall_only = mode == "recall-only"` alongside its existing `order`-driven shuffle; in `submit_answer()`, after grading (unchanged), branch on `self.recall_only` — when `True`, finalize the attempt immediately using the same four-step tail `skip_sentence()`/`continue_to_next()` already both perform (build the `PracticeAttempt` with no `sentence`/`feedback` fields, `append_attempt()` it, tally `correct_count` if correct, advance `current_index`, land on `"complete"`/`"recall"`) instead of stashing `pending_attempt` and moving to `"sentence"`; when `False` (default), behavior is unchanged. Per `research.md` §2, consider extracting the shared finalize-record-tally-advance logic into one private helper reused by `skip_sentence()`, `continue_to_next()`, and this new branch, to avoid a third inline copy — this is an internal refactor with no externally observable difference (depends on T002 failing for the right reason)
- [X] T007 [US1] In `src/cli/session.py`: add `mode: str = "sentence"` to `run_session`; per item, when `mode == "recall-only"`, build the `PracticeAttempt` directly from `run_recall_step()`'s result (`timestamp`, `item`, `answer`, `correct` — no `sentence`/`feedback` fields) and skip calling `run_sentence_step()` entirely; when `mode == "sentence"`/default, behavior is unchanged (depends on T003 failing for the right reason)
- [X] T008 [US1] In `src/cli/__main__.py`: add `parser.add_argument("--mode", choices=["sentence", "recall-only"], default="sentence", help="Practice mode: sentence-writing or recall only (default: sentence)")` and pass `mode=args.mode` to `run_session(...)` (depends on T007)
- [X] T009 [US1] In `src/web/app.py`: add `mode: str = "sentence"` to `create_app(...)`, passed through to `PracticeSession(..., mode=mode)`; update the `POST /api/select` route to read `body.get("mode", "sentence")` (defaulting to `"sentence"` for any missing or unrecognized value, per `contracts/web-api-contract-delta.md` — never a `400` for this field) and pass it to `session.select_collection(body["collection"], order=..., mode=...)` (depends on T006, T004)
- [X] T010 [US1] In `src/web/__main__.py`: add the same `--mode {sentence,recall-only}` argparse flag as T008, and pass `mode=args.mode` to `create_app(...)` — per `research.md` §4, this only has any observable effect when `--group` is also given, mirroring `--order`'s existing narrower-scope rule; no extra conditional is needed, it falls out of T006's implementation structurally (depends on T009)
- [X] T011 [P] [US1] Add a mode toggle (two options, e.g. radio buttons labeled "Sentence"/"Recall only", defaulting to Sentence selected) to `#choose-view` in `src/web/templates/index.html`, alongside the existing order toggle
- [X] T012 [US1] In `src/web/static/app.js`: track the currently-selected mode (default `"sentence"`) from the new toggle added in T011, and update `renderChoose`'s collection-button click handler to include `mode: <selected value>` alongside `collection`/`order` in the `POST /api/select` request body (depends on T011, T009, T005)
- [X] T013 [P] [US1] Add styling for the new mode toggle in `src/web/static/style.css`, reusing the existing order-toggle visual treatment (depends on T011)

**Checkpoint**: User Story 1 is fully functional and testable independently — `quickstart.md` Scenarios 1–5 (CLI sentence/recall-only, web interactive picker offering mode alongside collection/order, web `--mode` only applying with `--group`, recall-only working with the correction service stopped) can be run once T001–T013 are done; see Phase 4 for the mandatory manual pass.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory manual validation

- [X] T014 [P] Run `ruff check` over `src/cli/`, `src/web/`, and `tests/` and fix any issues
- [X] T015 Run all of `quickstart.md`'s scenarios end-to-end: CLI sentence (unchanged) and CLI `--mode recall-only`, the web UI's choose screen offering mode alongside collection/order and correctly skipping the sentence step for recall-only, `--mode` on the web CLI only applying with `--group`, and a recall-only session completing successfully with the local Ollama server stopped — a passing test suite proves the branch logic is invoked correctly, not that the resulting practice flow actually looks right end-to-end
- [X] T016 Run the full existing test suite (`pytest -q`) and confirm every previously-passing test still passes, proving no regression to grading, the review pipeline, the progress-log format, the session tally, the skip-word flow (`006`), the collection-choice flow (`007`), the correct-result color (`008`), voice input (`009`), the Judge/Teacher correction split (`010`), or word order (`011`)

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

- Tests are written first and must fail before their corresponding implementation task: T002 fails (no `mode`/`self.recall_only` exists) until T006 lands; T003 fails until T007 lands; T004 fails until T009 lands; T005 fails until T012 lands.
- T006 (web session core) and T007 (CLI session core) touch entirely different files and have no dependency on each other — genuinely parallel once their respective tests exist.
- T008 depends on T007 (needs `run_session`'s new signature); T009 depends on T006 (needs `select_collection`'s new signature) and T004; T010 depends on T009.
- T011 (template) has no dependency on the backend tasks and can proceed at any time; T012 (app.js) depends on T011 (markup to target), T009 (endpoint to accept `mode`), and T005 (its own test); T013 (CSS) depends only on T011.

### Parallel Opportunities

- T002, T003, T004, T005 are four independent test files/concerns and can be started together.
- T006 (web core) and T007 (CLI core) are independent files and can proceed in parallel; T011 (template) and T013 (CSS, once T011 lands) can also proceed alongside the backend tasks.
- T014 (lint) can run alongside T015/T016 in Phase 4.

---

## Parallel Example: User Story 1

```bash
# T002, T003, T004, T005 are independent test files and can be started together:
Task: "mode/self.recall_only unit tests in tests/unit/test_session_state.py"
Task: "New CLI mode integration tests in tests/integration/test_session_mode.py"
Task: "POST /api/select mode-field contract tests in tests/contract/test_web_api_contract.py"
Task: "app.js mode-toggle wiring assertion in tests/unit/test_web_static_assets.py"

# T006 (web) and T007 (CLI) touch different files and can proceed together once their tests exist:
Task: "mode/self.recall_only in src/web/session_state.py"
Task: "mode param in src/cli/session.py"
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
- This feature touches `src/web/session_state.py`, `src/web/app.py`, `src/web/__main__.py`, `src/web/templates/index.html`, `src/web/static/{app.js,style.css}`, `src/cli/session.py`, and `src/cli/__main__.py` — no file under `src/models/`, `src/services/`, or `src/lib/` is touched.
- Do not consider this feature done when the test suite is green alone — T015's manual pass is what actually verifies recall-only mode behaves sensibly end-to-end in both interfaces, per `research.md` and `quickstart.md`.
- Commit after each task or logical group.
