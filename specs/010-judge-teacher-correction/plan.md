# Implementation Plan: Split Sentence Review into Judge and Teacher Roles

**Branch**: `010-judge-teacher-correction` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-judge-teacher-correction/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

`src/services/llm_client.py`'s `request_correction()` currently makes one
Ollama call asking for four things at once (target-usage, grammar+
naturalness, a corrected sentence, and an explanation). This splits it
into two sequential, single-purpose calls against the same configured
model: a **Judge** call (target-usage, grammar correctness, naturalness —
nothing generated) and a **Teacher** call (explanation + rewrite),
the Teacher only made when the Judge found a grammar or naturalness
problem. `request_correction()`'s signature and `CorrectionResult`'s shape
are unchanged — every existing caller (`session_state.py`, the CLI, all
tests that patch `request_correction` itself) needs no changes at all.

## Technical Context

**Language/Version**: Python 3.11+ (single file changed: `src/services/llm_client.py`)

**Primary Dependencies**: None new — reuses `requests` and Ollama's existing structured-output (`format`) parameter, exactly as today

**Storage**: N/A

**Testing**: pytest. `tests/contract/test_ollama_correction_contract.py` tests `llm_client.py`'s own wire-level behavior directly (mocking `requests.post`, inspecting the exact JSON schema sent) — it necessarily gets rewritten for the new two-call wire format (see research.md §3); every *other* existing test (`test_session_state.py`, `test_web_api_contract.py`, `test_web_session_flow.py`) patches `request_correction` itself as an opaque function and is unaffected, since neither its signature nor `CorrectionResult`'s shape changes (spec.md FR-003, SC-001)

**Target Platform**: Existing local Ollama integration, unchanged

**Project Type**: Single project — one source file, one rewritten test file

**Performance Goals**: None set (spec.md Assumptions: explicitly not a speed optimization). Two sequential calls instead of one will likely add latency when correction is needed; that's an accepted, non-goal side effect, not something this plan tries to minimize

**Constraints**:
- MUST NOT change `request_correction()`'s public signature or `CorrectionResult`'s fields (spec.md FR-003)
- MUST NOT call the Teacher unless the Judge found a grammar or naturalness problem (FR-002)
- MUST treat a Judge failure, *or* a Teacher failure following a "needs correction" Judge verdict, identically to today's single "unavailable" outcome (FR-004, FR-005) — no new partial-result state
- MUST use the same `base_url`/`model` parameters for both calls — no new configuration surface (FR-006)
- MUST NOT touch `src/web/session_state.py`, `src/cli/session.py`, or any UI file — this is scoped entirely to `llm_client.py` (spec.md Assumptions)
- MUST satisfy the constitution's Principle II correctness check with a reviewed known-correct/known-incorrect example set (FR-008) — this is the **first** feature built since the constitution was ratified that changes language-judgment logic, so there is no existing fixture/format to reuse; this plan establishes one (research.md §4)

**Scale/Scope**: Two new private helper functions inside the existing file (`_request_judge`, `_request_teacher`), two new prompt/schema constants, `request_correction()` rewritten to orchestrate them; one existing test file rewritten; one new manual-verification example set

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Plan requires the rewritten wire-level tests (Judge-only path, Judge+Teacher path, both failure modes) to be written before `request_correction()`'s internals are changed, following this project's established red-green-refactor convention | PASS |
| II. Pedagogical Accuracy & Safety | **Directly engaged**: this changes language-judgment logic (how grammar/naturalness/usage are determined and explained). FR-008 requires, and this plan schedules, a reviewed known-correct/known-incorrect example set run manually against the live pipeline before this feature is considered done (research.md §4, quickstart.md) — the explicit correctness check the constitution requires | PASS (with required manual verification step — see quickstart.md) |
| III. Learner Data Privacy | No new data collected, stored, or sent anywhere new — the same sentence text goes to the same local model, just across two requests instead of one | PASS (N/A) |

**Post-design re-check**: Phase 1 artifacts (data-model.md, contracts/, quickstart.md) introduce no new entities, no new endpoints, and no new data collection — only a new internal call shape and a new manual-verification fixture. All three gates still PASS unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/010-judge-teacher-correction/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command) — includes the reviewed example set (FR-008)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ollama-correction-contract-delta.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── services/
    └── llm_client.py    # Rewritten internals: _request_judge/_request_teacher, request_correction() orchestrates both; CorrectionResult unchanged

tests/
└── contract/
    └── test_ollama_correction_contract.py   # Rewritten for the two-call wire format (research.md §3) — the only test file this feature touches
```

No other file is touched: `session_state.py`, `app.py`, every web/CLI test file, templates, and static assets are all unaffected (spec.md Assumptions).

**Structure Decision**: Single project (existing layout, established `001`–`009`). This is the most narrowly-scoped feature in the project so far by file count — one source file rewritten internally, one test file rewritten to match.

## Complexity Tracking

*No constitution violations requiring justification. Table omitted.*
