# Implementation Plan: Confirm Before Skipping a Word Without a Sentence

**Branch**: `006-confirm-skip-word` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-confirm-skip-word/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

When a learner tries to submit the sentence-writing step with an empty (or
whitespace-only) sentence, the web UI must ask them to confirm they want to
skip the word instead of silently sending nothing off for correction. On
confirmation, the session advances straight to the next word (or to
completion) without ever entering the `"feedback"` step for that word; on
decline, nothing changes. The skip is recorded in the progress log as an
attempt with no sentence, and the end-of-session tally continues to count
the word's recall correctness exactly as before.

This is implemented entirely client-side-triggered (empty-input detection
in `app.js`, using the browser's native confirmation dialog) plus one new
server endpoint (`POST /api/skip`) and one new `PracticeSession` state
transition (`"sentence"` → `"recall"`/`"complete"`, bypassing `"feedback"`).
No changes to the recall step, the CLI, the vocabulary format, or the
sentence-correction pipeline are needed.

## Technical Context

**Language/Version**: Python 3.11+ (backend, per `pyproject.toml`); vanilla ES2017 JavaScript, HTML, CSS (frontend — no build step, no framework)

**Primary Dependencies**: Flask 3.x (web routes), PyYAML (progress log), the project's existing `matcher`/`llm_client`/`progress_log`/`vocabulary_loader` services (unchanged)

**Storage**: Plain Markdown files (`progress.md`, vocabulary `*.md`) — no database; this feature adds no new storage, only a new (already-supported) shape of `PracticeAttempt` record

**Testing**: pytest, three existing tiers (`tests/contract`, `tests/integration`, `tests/unit`); no JS test runner — frontend behavior is covered by static-content assertions (established convention, see `tests/unit/test_web_static_assets.py`) plus manual verification via `quickstart.md`

**Target Platform**: Existing LAN-reachable Flask dev server (`src/web`); single learner, no auth

**Project Type**: Single project (existing `src/`, `tests/` layout — see `003-web-ui`'s plan; this feature adds no new top-level directories)

**Performance Goals**: N/A — single learner, local requests; the whole point of skipping is to *avoid* an LLM round-trip, so this path is faster than the normal one

**Constraints**:
- MUST NOT call `request_correction` (the Ollama pipeline) for a skipped word (FR-003)
- MUST NOT introduce a database or change the progress-log file format (existing `001`/`003` constraints, unchanged)
- MUST follow the additive "Contract Delta" convention already established by `004-web-ui-ux-polish` for amending `003-web-ui`'s API contract, rather than rewriting it
- Applies to the web UI only — `src/cli/session.py` is intentionally unchanged (see spec.md Assumptions)

**Scale/Scope**: One new endpoint, one new `PracticeSession` method, a small `app.js` change to the existing sentence-form submit handler; no new template markup required (native `confirm()` dialog satisfies the "pop up a message" requirement — see research.md)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Plan requires contract test (`POST /api/skip`), unit tests (`PracticeSession.skip_sentence`), and an integration test (full skip flow) to be written before the corresponding implementation, following the project's existing red-green-refactor convention (see `tasks.md`, produced next) | PASS |
| II. Pedagogical Accuracy & Safety | This feature generates no new language judgment — it explicitly *avoids* invoking correction for empty input. No new correctness check is needed because no new language content is produced or scored. | PASS (N/A) |
| III. Learner Data Privacy | No new data is collected; a skipped attempt stores *less* than a normal one (no sentence text). Uses the existing `PracticeAttempt`/progress-log mechanism unchanged. | PASS |

**Pre-existing requirement note** (not a constitution gate, but a direct conflict this plan must resolve explicitly): `001-vocab-recall-tutor` FR-016 and `003-web-ui` FR-010 both say the learner must not be able to "skip an unanswered item" or move backward. This feature is read as a narrow, deliberate exception: by the time the sentence step exists, the recall step for that item has already been answered (right or wrong) — this feature only ever skips the *follow-on sentence*, never the recall answer, and adds no backward navigation. This interpretation is recorded in spec.md's Assumptions rather than silently applied.

**Post-design re-check**: Phase 1 artifacts (data-model.md, contracts/web-api-contract-delta.md, quickstart.md) introduce no new entities, no new storage, and no new language-generation/scoring logic beyond what was already assessed above — all three gates still PASS unchanged. The one new endpoint (`POST /api/skip`) and one new `PracticeSession` method are additive and match existing conventions exactly (see research.md §3–5).

## Project Structure

### Documentation (this feature)

```text
specs/006-confirm-skip-word/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── web-api-contract-delta.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── models/
│   └── practice_attempt.py     # UNCHANGED — already supports sentence=None/feedback=None
├── services/
│   └── progress_log.py         # UNCHANGED — already omits sentence/feedback when None
├── cli/                        # UNCHANGED — out of scope (see spec.md Assumptions)
└── web/
    ├── app.py                  # + POST /api/skip route
    ├── session_state.py        # + PracticeSession.skip_sentence()
    ├── templates/index.html    # UNCHANGED — no new markup needed
    └── static/
        ├── app.js              # + empty-sentence detection, confirm(), call to /api/skip
        └── style.css           # UNCHANGED

tests/
├── contract/
│   └── test_web_api_contract.py         # + POST /api/skip cases
├── integration/
│   └── test_web_session_flow.py         # + end-to-end skip scenario
└── unit/
    ├── test_session_state.py             # + skip_sentence() transition/count tests
    └── test_web_static_assets.py          # + assertion that app.js wires up the confirm/skip path
```

**Structure Decision**: Single project (existing Option 1 layout, already established by `001`–`005`). This feature only touches the existing `src/web/` slice of that layout; no new projects, packages, or directories are introduced.

## Complexity Tracking

*No constitution violations requiring justification. Table omitted.*
