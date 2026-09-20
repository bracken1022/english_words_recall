---

description: "Task list template for feature implementation"
---

# Tasks: Choose a Vocabulary Collection Before Practicing

**Input**: Design documents from `/specs/007-select-vocabulary-collection/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. `plan.md`'s Constitution Check commits explicitly to this ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`006`. Touches `src/web/session_state.py`, `src/web/app.py`, `src/web/templates/index.html`, `src/web/static/{app.js,style.css}`, and four existing test files — no new files, directories, or dependencies (see `research.md` §5 and `plan.md`'s Project Structure).

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed (reuses Flask, PyYAML, pytest already in `pyproject.toml`; collection lists are rendered with vanilla JS, no new frontend library) — no `pyproject.toml` change expected

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `PracticeSession` needs to know the full unfiltered pool, whether a collection was locked in at startup, and how to list choices from it — both user stories build directly on this. No user-story work can begin until this phase is complete.

### Tests for the foundation ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [P] Write unit tests in `tests/unit/test_session_state.py` for `PracticeSession.__init__`'s new behavior, per `data-model.md`: when `group` is `None` (not passed), `group_locked` is `False`, `all_items` holds every loaded item, `items` starts empty, and `step` is `"choose"` when `all_items` is non-empty or `"empty"` when it's empty; when `group` **is** passed, `group_locked` is `True` and `step`/`items` behave exactly as today (`"recall"`/`"empty"`, pre-filtered) — `"choose"` must never be the initial step in that mode
- [X] T003 [P] Write unit tests in `tests/unit/test_session_state.py` for the collection-listing helper, per `data-model.md`'s derived-view table: given a mixed pool (some items with `group` set to two different values, at least one item with `group is None`), the returned list is `[{"key": None, "label": "Practice everything", "count": <all items>}, ...one entry per distinct group value sorted alphabetically by key..., {"key": "__ungrouped__", "label": "Ungrouped words", "count": <ungrouped items>}]` — the `null`/"Practice everything" entry always first, named groups alphabetical, `"__ungrouped__"` last and **only present** when at least one item has `group is None`

### Implementation for the foundation

- [X] T004 Update `PracticeSession.__init__` in `src/web/session_state.py`: store `self.vocab_dir = vocab_dir` (currently discarded after the initial load); add `self.group_locked = group is not None`; keep loading via `load_vocabulary(vocab_dir)` once, store the full result as `self.all_items`; when `group_locked`, filter into `self.items` and set `self.step` exactly as today (unchanged path); when not `group_locked`, set `self.items = []` and `self.step = "choose" if self.all_items else "empty"` (depends on T002)
- [X] T005 Add a collection-listing helper to `src/web/session_state.py` (e.g. `PracticeSession._available_collections(self) -> list[dict]`), plus a module-level `UNGROUPED_KEY = "__ungrouped__"` constant, implementing exactly the ordering and shape from `data-model.md`'s derived-view table (depends on T003)
- [X] T006 Add the `"choose"` branch to `PracticeSession.state()` in `src/web/session_state.py`: when `self.step == "choose"`, return `{"step": "choose", "collections": self._available_collections(), "warnings": self.warnings}` before reaching the `self.current_item` access used by later steps, mirroring the existing early-return shape already used for `"empty"`/`"complete"` (depends on T004, T005)

**Checkpoint**: `PracticeSession` now exposes `"choose"` and the full pool correctly; both user stories can now be built on top of this.

---

## Phase 3: Choose a collection before practicing (Priority: P1) 🎯 MVP

**Goal**: Opening the web UI without a pre-selected collection shows the list of available collections before any recall content; picking one scopes the whole session to it.

**Independent Test**: In a real browser, start the app with a multi-collection vocabulary folder and confirm the choice screen appears first, and that picking a collection limits practice to just its words — see `quickstart.md` Scenarios 1–2.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T007 [P] [US1] Write unit tests in `tests/unit/test_session_state.py` for a new `PracticeSession.select_collection(key)` method, per `data-model.md`'s transition table: raises `WrongStepError` when `step != "choose"`; given a real group-value key, `None` (practice everything), or `"__ungrouped__"`, filters `self.all_items` into `self.items` preserving item order, matching the same predicate shape `--group` filtering already uses; resets `current_index=0`, `pending_attempt=None`, `last_correction=None`, `correct_count=0`; sets `step` to `"recall"` (non-empty result) or `"empty"` (defensive fallback)
- [X] T008 [P] [US1] Write contract tests in `tests/contract/test_web_api_contract.py` for `POST /api/select`, per `contracts/web-api-contract-delta.md`: `200` + `GET /api/state`-shaped `"recall"` body for a valid named-collection key; `200` + `"recall"` body including every loaded item's words when `{"collection": null}` (practice everything); `400 Bad Request` + `{"error": "missing 'collection'"}` when the request body has no `"collection"` key at all; `409 Conflict` + `{"error": "not choosing a collection"}` + no state change when `step != "choose"`; and that the progress file is left untouched by this call (no attempt is recorded by selecting a collection)
- [X] T009 [P] [US1] Write a static-content assertion in `tests/unit/test_web_static_assets.py` confirming `src/web/static/app.js` renders entries from `state.collections` (each with its label and count) and posts the chosen entry's `key` to `/api/select`

### Implementation for User Story 1

- [X] T010 [US1] Implement `PracticeSession.select_collection(key)` in `src/web/session_state.py` per T007's spec (depends on T007 failing for the right reason, T004–T006)
- [X] T011 [US1] Add the `POST /api/select` route in `src/web/app.py`: require `"collection"` in the parsed JSON body (`400` + `{"error": "missing 'collection'"}` if absent, matching the existing `POST /api/answer`/`POST /api/sentence` convention), otherwise call `session.select_collection(body["collection"])`, catch `WrongStepError` → `409` + `{"error": str(exc)}`, else return `jsonify(session.state())` (depends on T010, T008)
- [X] T012 [P] [US1] Add a new `<section id="choose-view" hidden>` to `src/web/templates/index.html`, positioned as the first step-section (before `empty-view`), left as an empty container — its contents are rendered client-side from `state.collections` (no static list markup, since the choices are data-driven)
- [X] T013 [US1] Update `src/web/static/app.js`: add `choose: document.getElementById("choose-view")` to the `views` map; add a `renderChoose(collections)` function that clears and repopulates `#choose-view` with one button per entry (showing `label` and `count`), each wired to `POST /api/select` with `{"collection": entry.key}` followed by `fetchState()`; call it from `renderState()` when `state.step === "choose"` (depends on T012, T009)
- [X] T014 [P] [US1] Add `#choose-view` styling to `src/web/static/style.css`, consistent with the existing notebook/card design (list of tappable entries using the same ink/paper/red-accent tokens and button treatment already established, showing each collection's label and word count)

**Checkpoint**: User Story 1 is fully functional and testable independently — `quickstart.md` Scenarios 1–3 (choice screen, scoped practice, no mid-session switch) can be run once T001–T014 are done; see Phase 5 for the mandatory real-browser pass.

---

## Phase 4: Start a different collection without restarting (Priority: P2)

**Goal**: Finishing a session offers a way back to the collection-choice screen, without restarting the application, and picks up any vocabulary changes made since the session started.

**Independent Test**: Finish a session and confirm a "practice again" control appears and returns to the choice screen, with counts reflecting any vocabulary files added in the meantime — see `quickstart.md` Scenarios 4–6.

### Tests for User Story 2 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T015 [P] [US2] Write unit tests in `tests/unit/test_session_state.py` for a new `PracticeSession.restart()` method, per `data-model.md`'s transition table: raises `WrongStepError` when `step != "complete"`; raises `WrongStepError` when `step == "complete"` but `group_locked` is `True`; otherwise re-runs `load_vocabulary(self.vocab_dir)`, replacing `self.warnings`/`self.all_items` (verified by writing an additional vocabulary file to the same `vocab_dir` between session creation and `restart()`, then asserting the new item is present), and sets `step` to `"choose"` (or `"empty"` if the reload now finds nothing)
- [X] T016 [P] [US2] Write contract tests in `tests/contract/test_web_api_contract.py` for `POST /api/restart`, per `contracts/web-api-contract-delta.md`: `200` + `"choose"`-shaped body when `step == "complete"` and not `group_locked`; `409 Conflict` + `{"error": "not ready to restart"}` when `step != "complete"`; `409 Conflict` when `step == "complete"` but the session was started with `--group` (`group_locked`); and that `GET /api/state`'s `"complete"` step includes `can_restart: true` for an unlocked session and `can_restart: false` for a `--group`-locked one
- [X] T017 [P] [US2] Write an integration test in `tests/integration/test_web_session_flow.py` covering the full loop through the real Flask test client: choose a collection → finish it → confirm `"complete"` has `can_restart: true` → `POST /api/restart` → confirm `"choose"` reappears — plus a second test starting `create_app(..., group="unit1")` and asserting `POST /api/select`/`POST /api/restart` both return `409` and `"choose"` is never the initial step

### Implementation for User Story 2

- [X] T018 [US2] Implement `PracticeSession.restart()` in `src/web/session_state.py` per T015's spec (depends on T015 failing for the right reason)
- [X] T019 [US2] Add `can_restart` (`not self.group_locked`) to the `"complete"` branch of `PracticeSession.state()` in `src/web/session_state.py` (depends on T016)
- [X] T020 [US2] Add the `POST /api/restart` route in `src/web/app.py`, following the same pattern as `POST /api/skip`/`POST /api/continue`: call `session.restart()`, catch `WrongStepError` → `409` + `{"error": str(exc)}`, else return `jsonify(session.state())` (depends on T018, T019, T016)
- [X] T021 [P] [US2] Add a "practice again" `<button id="restart-button" type="button" hidden>` to `#complete-view` in `src/web/templates/index.html`, alongside the existing stamp/tally content
- [X] T022 [US2] Update `src/web/static/app.js`: in `renderState()`'s `"complete"` branch, set `restartButton.hidden = !state.can_restart`; add a click handler that posts to `/api/restart` and calls `fetchState()` (depends on T021, T017)

**Checkpoint**: Both user stories are fully functional and independently testable. `quickstart.md` Scenarios 4–6 (restart, vocabulary-change pickup, locked-mode regression) still need a real-browser pass — see Phase 5.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory real-browser validation (no JS test runner in this project — see `research.md` §5)

- [X] T023 [P] Run `ruff check` over `src/web/` and `tests/` and fix any issues
- [X] T024 Run all of `quickstart.md`'s scenarios end-to-end **in a real browser**: the choice screen appearing first, a named-collection session staying scoped, no mid-session switch control ever appearing, the completion screen's "practice again" control, restart picking up a newly added vocabulary file, and a `--group`-started server showing neither the choice screen nor a restart control — a green test suite alone does not verify the dynamically-rendered choice list or button wiring actually work for a person
- [X] T025 Run the full existing test suite (`pytest -q`) and confirm every previously-passing test still passes, proving no regression to grading, the review pipeline, the progress-log format, the session tally, the skip-word flow (`006`), or the recall/sentence/feedback state machine for `--group`-locked sessions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — trivial (confirmation only).
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS both user stories — `select_collection()` and `restart()` both need `all_items`/`group_locked`/the listing helper to exist first.
- **User Story 1 (Phase 3)**: Depends on Foundational only. No dependency on US2.
- **User Story 2 (Phase 4)**: Depends on Foundational only for its core mechanism (`restart()` doesn't call `select_collection()`), but its real-world value assumes US1's choice screen exists to return to — implemented after US1 here, though the two touch mostly disjoint code.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends only on the Foundational phase.
- **US2 (P2)**: Depends only on the Foundational phase for its mechanism; ordered after US1 because "restart back to the choice screen" is only meaningful once that screen exists.

### Within Each User Story

- Tests are written first and must fail before their corresponding implementation task: T007 fails until T010 exists; T008 fails (404) until T011 exists; T009 fails until T013 exists; T015 fails until T018 exists; T016 fails (404/missing field) until T019/T020 exist; T017 fails until the full US1+US2 chain exists.

### Parallel Opportunities

- T002 and T003 (foundational tests) touch the same test file but independent assertions — can be written together.
- T007, T008, T009 (US1 tests) are three different files and can be started together.
- T012 and T014 (choose-view markup and CSS) touch different files than T010/T011 (Python) and can proceed in parallel with them; T013 (app.js) depends on T012 existing to target a real element.
- T015, T016, T017 (US2 tests) are three different files and can be started together.
- T021 (template) can proceed in parallel with T018/T019/T020 (Python); T022 (app.js) depends on T021.
- T023 (lint) can run alongside T024/T025.

---

## Parallel Example: Foundational Tests, then User Story 1 Tests

```bash
# T002 and T003 are independent assertions in the same file:
Task: "Init/group_locked tests in tests/unit/test_session_state.py"
Task: "Collection-listing helper tests in tests/unit/test_session_state.py"

# Once the foundation lands, T007/T008/T009 are three independent files:
Task: "select_collection() unit tests in tests/unit/test_session_state.py"
Task: "POST /api/select contract tests in tests/contract/test_web_api_contract.py"
Task: "app.js choose-view wiring assertion in tests/unit/test_web_static_assets.py"
```

---

## Implementation Strategy

### MVP First (Foundational + User Story 1 Only)

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 2: Foundational — `"choose"` step, full pool, `group_locked`.
3. Complete Phase 3: User Story 1 — the choice screen and scoped practice itself.
4. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1–3 in a real browser.

### Incremental Delivery

1. Setup → Foundational → User Story 1 → validate via quickstart Scenarios 1–3 (the core feature).
2. Add User Story 2 → validate via quickstart Scenarios 4–6 (restart, vocabulary-change pickup, locked-mode regression).
3. Polish → run all quickstart scenarios, lint, and the full test suite.

---

## Notes

- `[P]` tasks touch different files or independent assertions with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to `spec.md` for traceability.
- This feature touches `session_state.py`, `app.py`, `templates/index.html`, and both static frontend files — no new files, models, or dependencies (see `plan.md`'s Project Structure).
- Do not consider this feature done when the test suite is green alone — T024's real-browser pass is what actually verifies the dynamically-rendered choice list and restart control, per `research.md` §5 and `quickstart.md`.
- Commit after each task or logical group.
