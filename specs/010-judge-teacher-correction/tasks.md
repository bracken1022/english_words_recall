---

description: "Task list template for feature implementation"
---

# Tasks: Split Sentence Review into Judge and Teacher Roles

**Input**: Design documents from `/specs/010-judge-teacher-correction/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (Test-First Development, NON-NEGOTIABLE) mandates tests before implementation for every feature and bug fix; this overrides the "tests optional" default. `plan.md`'s Constitution Check commits explicitly to this ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`009`. This is the most narrowly-scoped feature so far: one source file rewritten internally (`src/services/llm_client.py`) and one test file rewritten to match (`tests/contract/test_ollama_correction_contract.py`) — no other file is touched (`plan.md`'s Project Structure).

---

## Phase 1: Setup

**Purpose**: Confirm no new project setup is required

- [X] T001 Confirm no new dependencies are needed (reuses `requests` and Ollama's existing structured-output parameter, exactly as today) — no `pyproject.toml` change expected

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: N/A — the Judge/Teacher split itself is User Story 1's own deliverable, not a shared prerequisite built before it. Proceed directly to Phase 3.

---

## Phase 3: One focused job per prompt (Priority: P1) 🎯 MVP

**Goal**: `request_correction()` makes a Judge request (grammar/target-usage/naturalness only) and, only when the Judge found a problem, a Teacher request (explanation + rewrite only) — producing the exact same `CorrectionResult` shape as today.

**Independent Test**: Review the Judge prompt/schema and the Teacher prompt/schema in `contracts/ollama-correction-contract-delta.md` separately against `quickstart.md`'s example sentences and confirm each does only its own job.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL before implementing)

- [X] T002 [US1] Rewrite `tests/contract/test_ollama_correction_contract.py` for the two-call flow, per `contracts/ollama-correction-contract-delta.md` and `research.md` §3 (mock `requests.post` with a `side_effect` list and inspect `mock_post.call_args_list`, not just the last call): (a) an already-correct-and-natural Judge reply results in exactly one `requests.post` call, with that call's `format.required` equal to `{"uses_expression", "grammatically_correct", "natural"}`, and the returned `CorrectionResult` has `needs_correction=False`, `corrected=None`, `explanation=None`; (b) a Judge reply with `grammatically_correct` or `natural` set to `false` results in a **second** `requests.post` call whose `format.required` equals `{"corrected", "explanation"}`, and the returned `CorrectionResult` has `needs_correction=True` with `corrected`/`explanation` taken from that second call's reply; (c) a Judge-call failure (connection error, non-200 status, non-JSON content, valid JSON missing one of the three required keys, or a wrong-typed field) results in `available=False` with exactly one `requests.post` call made (Teacher never invoked); (d) a Judge reply indicating correction is needed, followed by a Teacher-call failure (same failure modes as (c), applied to the second call), results in `available=False` for the **whole** result — not a partial one (spec.md FR-005); (e) both calls use the identical `model`/`base_url` values passed to `request_correction()` when both are made

### Implementation for User Story 1

- [X] T003 [US1] In `src/services/llm_client.py`, add `_JUDGE_SYSTEM_PROMPT`, `_JUDGE_RESPONSE_FORMAT` (`type: object`, properties `uses_expression`/`grammatically_correct`/`natural` all `boolean`, all three `required` — per `contracts/ollama-correction-contract-delta.md` Request 1), a `_JudgeVerdict` dataclass with fields `uses_expression: bool`, `grammatically_correct: bool`, `natural: bool` (per `data-model.md`), and `_request_judge(target_expression, sentence, base_url, model, timeout) -> _JudgeVerdict | None` — returns `None` (never raises) for a connection error, non-200 status, unparseable/non-object JSON, or a missing/wrong-typed required key, mirroring the existing `_parse_reply` validation discipline (depends on T002 failing for the right reason)
- [X] T004 [US1] In `src/services/llm_client.py`, add `_TEACHER_SYSTEM_PROMPT`, `_TEACHER_RESPONSE_FORMAT` (`type: object`, properties `corrected`/`explanation` both `string`, both `required` — per `contracts/ollama-correction-contract-delta.md` Request 2), and `_request_teacher(target_expression, sentence, base_url, model, timeout) -> tuple[str, str] | None` — same never-raises, `None`-on-any-failure discipline as `_request_judge` (depends on T003; same file, sequential)
- [X] T005 [US1] Rewrite `request_correction()` in `src/services/llm_client.py` to orchestrate `_request_judge()` then, only when `not (verdict.grammatically_correct and verdict.natural)`, `_request_teacher()`, assembling `CorrectionResult` exactly per `data-model.md`'s call-flow diagram (Judge failure or Teacher failure both return the existing `_unavailable()` helper); remove the now-unused single-call constants (`_SYSTEM_PROMPT`, `_RESPONSE_FORMAT`, `_REQUIRED_FIELDS`, `_parse_reply`) once nothing references them (depends on T003, T004, T002)

**Checkpoint**: User Story 1 is fully functional and testable independently — the rewritten `tests/contract/test_ollama_correction_contract.py` passes, proving the two-call orchestration and both failure modes behave per contract; see Phase 5 for the mandatory manual correctness check.

---

## Phase 4: Nothing else changes (Priority: P2)

**Goal**: Confirm every existing caller of `request_correction()` — the practice-session flow, the CLI, and every test that isn't `test_ollama_correction_contract.py` — needs no changes and sees no difference.

**Independent Test**: Run the existing automated test suite unmodified (excluding the file just rewritten in Phase 3) and confirm every test still passes; separately, exercise the web UI's practice flow and confirm the feedback shown is unchanged.

### Verification for User Story 2 (no new code — confirms Phase 3's implementation didn't leak outward)

- [X] T006 [US2] Run `pytest -q` and confirm every test outside `tests/contract/test_ollama_correction_contract.py` still passes unmodified — in particular `tests/unit/test_session_state.py` (which injects `CorrectionResult` directly via `correction_fn`, never touching `requests.post`) and every web contract/integration test that patches `request_correction` as an opaque function (spec.md SC-001, `research.md` §3) (depends on T005)
- [X] T007 [US2] Follow `quickstart.md`'s "Regression check": start the web UI against any vocabulary folder, submit a sentence with a deliberate mistake and a separate already-correct sentence, and confirm the feedback shown for each is indistinguishable from before this feature (depends on T005, T006)

**Checkpoint**: Both user stories confirmed. `quickstart.md`'s manual correctness check (FR-008) still needs to run — see Phase 5.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Lint and the mandatory Principle II correctness check (no automated test can verify live-model judgment quality — see `research.md` §4)

- [X] T008 [P] Run `ruff check` over `src/services/llm_client.py` and `tests/contract/test_ollama_correction_contract.py`
- [X] T009 Run `quickstart.md`'s manual correctness check: all 7 example sentences against a live local Ollama server with `qwen3:14b`, confirming each `needs_correction` verdict matches expectations and, where `True`, that `corrected`/`explanation` read as accurate and natural — a human judgment call, and the actual Constitution Principle II correctness check this feature requires (FR-008); do not consider this feature done without it
- [X] T010 Run the full existing test suite (`pytest -q`) one final time and confirm every test passes, proving no regression to grading, the review pipeline, the progress-log format, the session tally, the skip-word flow (`006`), the collection-choice flow (`007`), the correct-result color (`008`), or voice input (`009`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — trivial (confirmation only).
- **Foundational (Phase 2)**: None for this feature — skipped.
- **User Story 1 (Phase 3)**: Depends on Setup only. This is the actual Judge/Teacher split.
- **User Story 2 (Phase 4)**: Depends on User Story 1's implementation (T005) already being in place — it adds no new production code, only confirms nothing outside `llm_client.py` was affected.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — the split itself.
- **US2 (P2)**: Entirely dependent on US1's implementation; contributes verification only.

### Within Each User Story

- T002 is written first and must fail against the *old* (pre-T003–T005) single-call implementation before it's considered a valid test-first task — e.g., assertion (a)'s "exactly one `requests.post` call with `format.required == {uses_expression, grammatically_correct, natural}`" fails today because the current single call's schema has four different required keys.
- T003 and T004 both edit `src/services/llm_client.py` and are sequential, not parallel.

### Parallel Opportunities

- None within Phase 3 — T002 (tests) must exist before T003–T005 (implementation), and T003/T004/T005 all edit the same file in sequence.
- T008 (lint) can run alongside T009/T010 in Phase 5.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (trivial).
2. Complete Phase 3: User Story 1 — the Judge/Teacher split itself.
3. **STOP and VALIDATE**: rewritten contract tests pass.

### Incremental Delivery

1. Setup → User Story 1 → validate via the rewritten `test_ollama_correction_contract.py`.
2. Add User Story 2 → validate via the full suite (minus the rewritten file) plus a manual web-UI regression pass.
3. Polish → the mandatory Principle II manual correctness check (T009), lint, and one final full-suite run.

---

## Notes

- `[P]` tasks touch different files or independent assertions with no unmet dependency.
- `[Story]` labels map every user-story-phase task back to `spec.md` for traceability.
- This feature touches exactly two files: `src/services/llm_client.py` and `tests/contract/test_ollama_correction_contract.py`. No file under `src/web/`, `src/cli/`, `src/models/`, or any template/static asset is touched (`plan.md`'s Constraints).
- Do not consider this feature done when the automated suite is green alone — T009's manual correctness check against a live model is the actual Constitution Principle II proof, per `research.md` §4 and `quickstart.md`.
- Commit after each task or logical group.
