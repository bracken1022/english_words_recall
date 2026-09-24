---

description: "Task list template for feature implementation"
---

# Tasks: Choose Sequential or Random Word Order

**Input**: Design documents from `/specs/011-vocabulary-order-choice/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. `plan.md`'s Constitution Check commits explicitly to this ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. This feature has exactly one user story, realized across two entry points (CLI and web UI) per spec.md FR-005.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`010`. This is the first feature since `001`–`003` to touch both `src/cli/` and `src/web/` in the same change (`plan.md`'s Project Structure) — no new files in `src/`, one new test file (`tests/integration/test_session_order.py`).

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed (`random` is standard library) — no `pyproject.toml` change expected

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A — this feature has a single user story realized directly across the CLI and web entry points, with no shared prerequisite beyond Setup. Proceed directly to Phase 3.

---

## Phase 3: Pick sequential or random order before practicing (Priority: P1) 🎯 MVP

**Goal**: Both the CLI and the web UI let the learner choose `"sequential"` (today's exact behavior, default) or `"random"` order before a session's words are first presented; either way, every word in the pool is still presented exactly once, one at a time, forward only.

**Independent Test**: Run the CLI with `--order random` and confirm all words appear, each exactly once, in a different order than the vocabulary file lists them; separately, use the web UI's choose screen to pick random order and confirm the same.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [P] [US1] Write unit tests in `tests/unit/test_session_state.py` for the new `order` parameter, per `data-model.md`: `PracticeSession.__init__(..., order="random")` in `group_locked` mode calls `random.shuffle` on `self.items` exactly once (patch `src.web.session_state.random.shuffle` and assert it's called); `order="sequential"` (and the default, omitted) never calls it; `select_collection(key, order="random")` calls `random.shuffle` on the filtered `self.items` exactly once, `order="sequential"`/default never does; regardless of `order`, `sorted(i.english for i in session.items)` before and after matches the full filtered pool (a permutation, never a different set — FR-002)
- [X] T003 [P] [US1] Write a new integration test file `tests/integration/test_session_order.py`, mirroring `test_session_group_filter.py`'s style (mocking `request_correction`, monkeypatching `builtins.input`): `run_session(..., order="random")` calls `random.shuffle` on the filtered `items` list exactly once (patch `src.cli.session.random.shuffle`); `order="sequential"`/default never calls it; the resulting progress log still contains every word in the pool exactly once regardless of order
- [X] T004 [P] [US1] Write contract tests in `tests/contract/test_web_api_contract.py` for `POST /api/select`'s new `"order"` field, per `contracts/web-api-contract-delta.md`: `{"collection": "unit1", "order": "random"}` triggers exactly one `random.shuffle` call (patch `src.web.session_state.random.shuffle`) on the resulting `self.items`; `{"collection": "unit1"}` (order omitted) and `{"collection": "unit1", "order": "not-a-real-value"}` both never call it; `"collection"` missing from the body is still a `400` regardless of `"order"`'s presence, unchanged from `007`
- [X] T005 [P] [US1] Write a static-content assertion in `tests/unit/test_web_static_assets.py` confirming `src/web/static/app.js` tracks a selected order value and includes an `"order"` key in the JSON body it posts to `/api/select`

### Implementation for User Story 1

- [X] T006 [P] [US1] In `src/web/session_state.py`: add `import random`; add `order: str = "sequential"` to `PracticeSession.__init__`, shuffling `self.items` in place with `random.shuffle` when `order == "random"`, immediately after the existing group filter in the `group_locked` branch (before `self.step` is set); add the same `order: str = "sequential"` parameter to `select_collection`, shuffling the filtered `self.items` in place the same way, after the existing key-based filter and before `current_index`/counters reset (depends on T002 failing for the right reason)
- [X] T007 [P] [US1] In `src/cli/session.py`: add `import random`; add `order: str = "sequential"` to `run_session`, shuffling the filtered `items` list in place with `random.shuffle` when `order == "random"`, immediately after the existing group filter and before the practice loop begins (depends on T003 failing for the right reason)
- [X] T008 [US1] In `src/cli/__main__.py`: add `parser.add_argument("--order", choices=["sequential", "random"], default="sequential", help="Order to present words in (default: sequential)")` and pass `order=args.order` to `run_session(...)` (depends on T007)
- [X] T009 [US1] In `src/web/app.py`: add `order: str = "sequential"` to `create_app(...)`, passed through to `PracticeSession(..., order=order)`; update the `POST /api/select` route to read `body.get("order", "sequential")` (defaulting to `"sequential"` for any missing or unrecognized value, per `contracts/web-api-contract-delta.md` — never a `400` for this field) and pass it to `session.select_collection(body["collection"], order=...)` (depends on T006, T004)
- [X] T010 [US1] In `src/web/__main__.py`: add the same `--order {sequential,random}` argparse flag as T008, and pass `order=args.order` to `create_app(...)` — per `research.md` §3, this only has any observable effect when `--group` is also given, since `PracticeSession.__init__` only consumes `order` in its `group_locked` branch; no extra conditional is needed to enforce this, it falls out of T006's implementation structurally (depends on T009)
- [X] T011 [P] [US1] Add an order toggle (two options, e.g. radio buttons or a two-button group, labeled "Sequential"/"Random", defaulting to Sequential selected) to `#choose-view` in `src/web/templates/index.html`, above or alongside the existing `#choose-list`
- [X] T012 [US1] In `src/web/static/app.js`: track the currently-selected order (default `"sequential"`) from the new toggle added in T011, and update `renderChoose`'s collection-button click handler to include `order: <selected value>` alongside `collection: entry.key` in the `POST /api/select` request body (depends on T011, T009, T005)
- [X] T013 [P] [US1] Add styling for the new order toggle in `src/web/static/style.css`, consistent with the existing notebook/card design and the established button/list treatments (depends on T011)

**Checkpoint**: User Story 1 is fully functional and testable independently — `quickstart.md` Scenarios 1–4 (CLI sequential/random, web interactive picker offering both, `--order` only applying alongside `--group`) can be run once T001–T013 are done; see Phase 4 for the mandatory manual pass.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory manual validation (a shuffle's actual visible effect isn't something the automated suite asserts directly — see `research.md` §6)

- [X] T014 [P] Run `ruff check` over `src/cli/`, `src/web/`, and `tests/` and fix any issues
- [X] T015 Run all of `quickstart.md`'s scenarios end-to-end: CLI with sequential (unchanged) and `--order random`, the web UI's choose screen offering both and producing a visibly different order on repeated "Practice again" shuffles, and confirming `--order` on the web CLI has no effect without `--group` — a passing test suite only proves shuffle-was-invoked, not that the resulting practice flow actually looks right end-to-end
- [X] T016 Run the full existing test suite (`pytest -q`) and confirm every previously-passing test still passes, proving no regression to grading, the review pipeline, the progress-log format, the session tally, the skip-word flow (`006`), the collection-choice flow (`007`), the correct-result color (`008`), voice input (`009`), or the Judge/Teacher correction split (`010`)

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

- Tests are written first and must fail before their corresponding implementation task: T002 fails (no `order` param exists) until T006 lands; T003 fails until T007 lands; T004 fails until T009 lands; T005 fails until T012 lands.
- T006 (web session core) and T007 (CLI session core) touch entirely different files and have no dependency on each other — genuinely parallel.
- T008 depends on T007 (needs `run_session`'s new signature); T009 depends on T006 (needs `select_collection`'s new signature) and T004; T010 depends on T009.
- T011 (template) has no dependency on the backend tasks and can proceed at any time; T012 (app.js) depends on T011 (markup to target), T009 (endpoint to accept `order`), and T005 (its own test); T013 (CSS) depends only on T011.

### Parallel Opportunities

- T002, T003, T004, T005 are four independent test files/concerns and can be started together.
- T006 (web core) and T007 (CLI core) are independent files and can proceed in parallel; T011 (template) and T013 (CSS, once T011 lands) can also proceed alongside the backend tasks.
- T014 (lint) can run alongside T015/T016 in Phase 4.

---

## Parallel Example: User Story 1

```bash
# T002, T003, T004, T005 are independent test files and can be started together:
Task: "order-param unit tests in tests/unit/test_session_state.py"
Task: "New CLI order integration tests in tests/integration/test_session_order.py"
Task: "POST /api/select order-field contract tests in tests/contract/test_web_api_contract.py"
Task: "app.js order-toggle wiring assertion in tests/unit/test_web_static_assets.py"

# T006 (web) and T007 (CLI) touch different files and can proceed together once their tests exist:
Task: "order param in src/web/session_state.py"
Task: "order param in src/cli/session.py"
```

---

## Implementation Strategy

### MVP First (and only) — User Story 1

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 3: User Story 1 — both entry points.
3. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1–4.
4. Polish: lint plus the full regression suite.

---

## Notes

- `[P]` tasks touch different files or independent assertions with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to `spec.md` for traceability.
- This feature touches `src/web/session_state.py`, `src/web/app.py`, `src/web/__main__.py`, `src/web/templates/index.html`, `src/web/static/{app.js,style.css}`, `src/cli/session.py`, and `src/cli/__main__.py` — no file under `src/models/`, `src/services/`, or `src/lib/` is touched.
- Do not consider this feature done when the test suite is green alone — T015's manual pass is what actually verifies the shuffle behaves sensibly end-to-end in both interfaces, per `research.md` and `quickstart.md`.
- Commit after each task or logical group.
