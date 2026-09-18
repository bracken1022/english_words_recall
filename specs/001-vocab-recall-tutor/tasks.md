---

description: "Task list template for feature implementation"
---

# Tasks: Vocabulary Recall Tutor

**Input**: Design documents from `/specs/001-vocab-recall-tutor/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present; plan.md amended 2026-09-18 for the Ollama structured-output migration — see Phase 7)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature; this overrides the "tests optional" default.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

Single project (per plan.md): `src/{models,services,cli,lib}`, `tests/{contract,integration,unit}` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md: `src/models/`, `src/services/`, `src/cli/`, `src/lib/`, `tests/contract/`, `tests/integration/`, `tests/unit/`, with `__init__.py` in each `src/` package
- [X] T002 Initialize Python 3.11+ project in `pyproject.toml` with dependencies `requests`, `PyYAML`, `rich`, and dev dependency `pytest`
- [X] T003 [P] Configure linting/formatting (`ruff`) in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared parsing/model infrastructure that both the vocabulary loader (US1) and the progress log (US3) depend on — MUST complete before any user story below

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Write unit tests for the shared Markdown block parser — a well-formed `---`-delimited YAML block parses to a dict; a malformed block (bad YAML) returns a warning instead of raising — in `tests/unit/test_markdown_blocks.py`
- [X] T005 Implement the shared `---`-delimited YAML block parser per `contracts/vocabulary-markdown-format.md` and `contracts/progress-log-format.md`: given a Markdown file, return `(list[dict], list[str warnings])`, never raising on a single bad block, in `src/lib/markdown_blocks.py` (depends on T004)
- [X] T006 [P] Write unit tests for the `VocabularyItem` model: missing `english` or `chinese` is invalid; `alternates` defaults to `[]`; `group` defaults to `None` — in `tests/unit/test_models_vocabulary_item.py`
- [X] T007 [P] Write unit tests for the `PracticeAttempt` model: `timestamp`/`item`/`answer`/`correct` are always required (`answer` may be `""`); `sentence` and `feedback` are both present or both absent — in `tests/unit/test_models_practice_attempt.py`
- [X] T008 [P] Implement `VocabularyItem` dataclass (`english: str`, `alternates: list[str] = []`, `chinese: str`, `group: str | None = None`) per data-model.md, in `src/models/vocabulary_item.py` (depends on T006)
- [X] T009 [P] Implement `PracticeAttempt` dataclass (`timestamp: str`, `item: str`, `answer: str`, `correct: bool`, `sentence: str | None = None`, `feedback: str | None = None`) per data-model.md, in `src/models/practice_attempt.py` (depends on T007)
- [X] T010 Implement the CLI entry point skeleton — argument parsing for the vocabulary directory and progress-log path, wiring to start a session — in `src/cli/__main__.py` (depends on T008, T009)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Recall the English Expression (Priority: P1) 🎯 MVP

**Goal**: Learner sees only the Chinese meaning of an item, types an English answer from memory, and is told correct/incorrect with the accepted expression revealed.

**Independent Test**: Load a vocabulary set, present one item's Chinese meaning, type an English answer, and confirm the system reports correct/incorrect — no sentence-writing or LLM correction involved.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T011 [P] [US1] Contract test for the vocabulary Markdown format per `contracts/vocabulary-markdown-format.md`: a file with one valid block loads one `VocabularyItem`; a block missing `english` or `chinese` is skipped with a warning while the rest of the file still loads — in `tests/contract/test_vocabulary_markdown_contract.py`
- [X] T012 [P] [US1] Unit tests for exact-match grading per FR-004: case-insensitive and whitespace-tolerant match against `english` or any `alternates`; a near-miss/misspelling (e.g., "recieve" vs "receive") is judged incorrect (no fuzzy tolerance); an empty answer is judged incorrect — in `tests/unit/test_matcher.py`
- [X] T013 [P] [US1] Integration test for the recall-only flow per spec Acceptance Scenarios 1-4 (US1) and quickstart Scenario 1: Chinese meaning shown with English hidden until submission; correct answer → marked correct + expression revealed; incorrect answer → marked incorrect + expression revealed; empty answer → marked incorrect, no error — in `tests/integration/test_recall_flow.py`

### Implementation for User Story 1

- [X] T014 [US1] Implement `vocabulary_loader.py`: load every Markdown file in a configured directory via `markdown_blocks`, build the pool of `VocabularyItem`s, and surface one warning per skipped invalid block without failing the rest of the load (FR-001, FR-013) — in `src/services/vocabulary_loader.py` (depends on T005, T008, T011)
- [X] T015 [US1] Implement `matcher.py`: case-insensitive, whitespace-tolerant exact-match grading against an item's `english` plus its `alternates`, with no typo/fuzzy tolerance (FR-004) — in `src/services/matcher.py` (depends on T012)
- [X] T016 [US1] Implement the recall step in `session.py`: show only the Chinese meaning, accept a free-text answer, grade it via `matcher`, and reveal the accepted expression(s) regardless of the result (FR-002, FR-003, FR-005) — in `src/cli/session.py` (depends on T014, T015, T010)
- [X] T017 [US1] Wire the recall step to run once per loaded `VocabularyItem`, strictly forward with no skip/back (FR-016) — in `src/cli/session.py` (depends on T016)

**Checkpoint**: User Story 1 is fully functional and independently testable (MVP).

---

## Phase 4: User Story 2 - Practice the Expression in a Sentence (Priority: P2)

**Goal**: After recall, the learner writes an original sentence with the target expression, and a local Ollama model reviews it for grammar/naturalness.

**Independent Test**: Supply a target expression and a learner-written sentence directly to the correction step and confirm it returns a grammar/naturalness assessment and, when applicable, a corrected version (per quickstart Scenarios 2-3).

### Tests for User Story 2 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T018 [P] [US2] Contract test for the Ollama correction call per `contracts/ollama-correction-contract.md`: a well-formed reply parses into uses-expression/needs-correction/corrected/explanation; a reply missing/garbling those labels is treated as unavailable; a non-200 response or connection error is treated as unavailable — in `tests/contract/test_ollama_correction_contract.py`
- [X] T019 [P] [US2] Integration test for the sentence-correction flow per spec Acceptance Scenarios 1-5 (US2) and quickstart Scenarios 2-3: a sentence needing correction shows the corrected version + explanation; an already-correct sentence is confirmed as correct with no invented changes; a sentence missing the target expression triggers a missing-expression message; an unreachable LLM shows "correction unavailable" and the session continues — in `tests/integration/test_sentence_correction_flow.py`

### Implementation for User Story 2

- [X] T020 [US2] Implement `llm_client.py`: build the request per `contracts/ollama-correction-contract.md`, `POST` to the local Ollama `/api/chat`, parse the labeled-line reply (`USES_EXPRESSION`/`NEEDS_CORRECTION`/`CORRECTED`/`EXPLANATION`), and treat any parse failure, non-200 status, or connection error as "unavailable" (FR-007, FR-008, FR-009, FR-010) — in `src/services/llm_client.py` (depends on T018)
- [X] T021 [US2] Extend `session.py`: after the recall step, prompt for a sentence using the target expression, call `llm_client`, and display the resulting feedback — needs-correction, already-correct, missing-expression, or unavailable (FR-006, FR-008, FR-009, FR-010) — in `src/cli/session.py` (depends on T020, T017)
- [X] T022 [US2] Attach the sentence and feedback summary to that attempt's in-memory `PracticeAttempt` alongside its recall result, ready for persistence — in `src/cli/session.py` (depends on T021, T009)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Author and Track Vocabulary as Markdown (Priority: P3)

**Goal**: Vocabulary items and practice history live entirely as plain, hand-editable Markdown files.

**Independent Test**: Hand-edit a vocabulary Markdown file to add a new item, restart the app, and confirm the new item appears; separately, complete a session and confirm the learner's history is readable as Markdown afterward (quickstart Scenario 4).

### Tests for User Story 3 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T023 [P] [US3] Contract test for the progress log format per `contracts/progress-log-format.md`: an appended attempt block round-trips on read with all its fields; a malformed block is skipped with a warning while the rest of the log still reads — in `tests/contract/test_progress_log_contract.py`
- [X] T024 [P] [US3] Integration test for the authoring flow per spec Acceptance Scenarios 1-2 (US3) and quickstart Scenario 4: a new item added to a vocabulary file is available after restart; a malformed block alongside a valid block in the same file is skipped with a warning while the valid block still loads — in `tests/integration/test_vocabulary_authoring_flow.py`
- [X] T025 [P] [US3] Integration test for progress readability per spec Acceptance Scenario 3 (US3), SC-005, and quickstart Scenario 4: after a full recall + sentence attempt, `progress.md` contains a block with item/answer/correct/sentence/feedback/timestamp, readable in a plain text editor — in `tests/integration/test_progress_log_readability.py`

### Implementation for User Story 3

- [X] T026 [US3] Implement `progress_log.py`: append a `PracticeAttempt` as a `---`-delimited YAML block to `progress.md`, and read all blocks back while skipping malformed ones with a warning (FR-011, mirroring the FR-013 tolerance pattern) — in `src/services/progress_log.py` (depends on T005, T009, T023)
- [X] T027 [US3] Wire `session.py` to call `progress_log.append(...)` once each attempt resolves, whether or not the sentence step was reached (FR-011) — in `src/cli/session.py` (depends on T026, T022)
- [X] T028 [US3] Implement the lesson/tag session filter: accept an optional `group` filter before a session starts, defaulting to the full pool when none is given (FR-015) — in `src/cli/session.py` (depends on T017)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Remaining spec Edge Cases and end-to-end validation across all stories

- [X] T029 [P] Handle an empty vocabulary pool (no valid items loaded from any file): show a clear message and do not start a session, instead of erroring (spec Edge Cases) — in `src/cli/session.py`
- [X] T030 [P] Handle an extremely long sentence submission without crashing or hanging the LLM call (spec Edge Cases) — in `src/services/llm_client.py`
- [X] T031 [P] Add `rich`-based terminal formatting for correct/incorrect results and the corrected-sentence display — in `src/cli/session.py`
- [X] T032 [P] Write `README.md` documenting setup, how to run the app, and how to point it at a local Ollama model
- [X] T033 Run all five `quickstart.md` validation scenarios end-to-end and fix any gaps found

---

## Phase 7: Ollama Runtime Migration (Plan Amendment 2026-09-18)

**Why**: `plan.md` was amended to require: calling Ollama's HTTP API only
(never spawning the `ollama` CLI — already true), a default model of
`qwen3:14b` (was `llama3.1`), structured (`format` JSON-schema) sentence
review instead of labeled-line text parsing, explicit handling of
schema-invalid-but-parseable JSON, and an explicit, tested guarantee that the
learning state machine never branches on LLM output. This phase supersedes
the relevant parts of Phase 4 (T018, T020, T021) without erasing their
history — those tasks proved the *pipeline shape* (needs-correction /
already-correct / missing-expression / unavailable) still holds; this phase
changes *how the reply is requested and parsed* and pins the new default
model.

**Goal**: `llm_client.py` requests and parses Ollama's structured JSON
output, defaults to `qwen3:14b`, and the state-machine/LLM boundary is
covered by an explicit automated test.

**Independent Test**: Per quickstart.md Scenarios 2, 3, 3b, and 6 — needs-
correction/already-correct/missing-expression behavior is unchanged from a
learner's perspective; a schema-invalid JSON reply degrades exactly like an
unavailable LLM; grading and item progression are identical whether Ollama
is up, down, or returning different feedback for the same sentence.

### Tests for Phase 7 ⚠️ (update/add first, confirm they FAIL before implementing)

- [X] T034 [P] [US2] Rewrite `tests/contract/test_ollama_correction_contract.py` per the amended `contracts/ollama-correction-contract.md`: assert the request body includes `"model": "qwen3:14b"` (default) and a `format` JSON-schema; assert a well-formed JSON `message.content` (all four keys, correct types) parses into `CorrectionResult`; add cases for JSON that parses but is missing a required key, and JSON where a key has the wrong type — both MUST be treated as unavailable (same as non-200/connection-error, already covered)
- [X] T035 [P] [US2] Add `tests/integration/test_determinism.py` per quickstart.md Scenario 6: running the same vocabulary set and answers twice — once with a mocked `needs_correction: true` reply and once with a mocked `needs_correction: false`/unavailable reply for the same sentence — produces identical grading (`correct` values) and identical item order in both runs; only the logged `feedback` text differs

### Implementation for Phase 7

- [X] T036 [US2] Update `request_correction` in `src/services/llm_client.py`: change the request payload to include a `format` JSON-schema (`uses_expression: bool`, `needs_correction: bool`, `corrected: string|null`, `explanation: string|null`, all required) instead of the labeled-line system prompt; change `model` default from `"llama3.1"` to `"qwen3:14b"`; parse `message.content` with `json.loads` and validate all four keys/types are present, treating any `JSONDecodeError`, non-dict result, or missing/mistyped key as unavailable (mirrors the existing malformed-reply handling, just JSON-based instead of regex-based) (depends on T034)
- [X] T037 [US2] Update `src/cli/__main__.py`'s `--model` default from `"llama3.1"` to `"qwen3:14b"`, and `src/cli/session.py`'s `run_sentence_step`/`run_session` default `model` parameter to match (depends on T036)
- [X] T038 [P] Update `README.md`: change the `ollama pull` example to `qwen3:14b`, update the `--model` flag's documented default, and note the app talks to Ollama's HTTP API only (never the CLI)
- [X] T039 Run quickstart.md Scenarios 2, 3, 3b, and 6 end-to-end against the updated implementation and fix any gaps found (depends on T035, T036, T037)

**Checkpoint**: All of Phase 4 (US2)'s independent test still passes, plus the new structured-output and determinism guarantees are proven by T034/T035.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 2 (Phase 4)**: Depends on Foundational; extends US1's `session.py` (T017), so build after US1.
- **User Story 3 (Phase 5)**: Depends on Foundational; T027 extends US2's attempt data (T022), so build after US2. T028 only depends on US1's T017.
- **Polish (Phase 6)**: Depends on all three user stories being complete.
- **Ollama Runtime Migration (Phase 7)**: Depends on Phase 4 (US2) and Phase 6 (T032's README) being complete — it revises their LLM-integration and documentation output rather than building on new foundations.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — the true MVP slice.
- **US2 (P2)**: Builds on US1's session loop (recall must happen before the sentence step is offered) but is independently testable via T018/T019 without US1's CLI wiring.
- **US3 (P3)**: Vocabulary authoring (T024) only needs US1's loader; progress-log persistence (T026-T027) needs US2's attempt data to be meaningful, so implement after US2.

### Within Each User Story

- Tests are written first and must fail before their corresponding implementation task.
- Models/services before CLI wiring; CLI wiring last within each story.

### Parallel Opportunities

- T003 (Setup) can run alongside T001-T002.
- T004, T006, T007 (Foundational tests, different files) can run in parallel; T008/T009 (different model files) can then run in parallel.
- Within each user story, all `[P]`-marked test tasks (different files) can run in parallel before that story's implementation tasks begin.
- T029-T032 (Polish, different files) can run in parallel; T033 runs last.
- T034 and T035 (Phase 7 tests, different files) can run in parallel; T038 (README) can run in parallel with T036/T037.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for vocabulary Markdown format in tests/contract/test_vocabulary_markdown_contract.py"
Task: "Unit tests for exact-match grading in tests/unit/test_matcher.py"
Task: "Integration test for recall-only flow in tests/integration/test_recall_flow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (blocks everything else).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 and confirm the recall drill works end-to-end with no LLM involved.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. Add User Story 1 → validate via quickstart Scenario 1 (MVP).
3. Add User Story 2 → validate via quickstart Scenarios 2-3 (needs Ollama running for the positive path, and stopped for Scenario 3).
4. Add User Story 3 → validate via quickstart Scenarios 4-5.
5. Polish → run the full quickstart.md suite (T033).

---

## Notes

- `[P]` tasks touch different files with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to spec.md for traceability.
- Constitution Principle I requires each test task to be completed, run, and confirmed failing before its paired implementation task begins.
- Commit after each task or logical group.
