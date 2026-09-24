# Implementation Plan: Require Confirmation Before Advancing Past a Wrong Recall-Only Answer

**Branch**: `013-confirm-wrong-answer` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-confirm-wrong-answer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

In recall-only mode, `submit_answer()` currently always finalizes the
attempt and auto-advances, correct or not. This splits that in two: a
**correct** answer keeps today's exact behavior (finalize, advance
immediately — the web UI's existing brief timed reveal is unchanged); an
**incorrect** answer now stops in a new `"reveal"` step instead of
advancing — the attempt is held (not yet written to the progress log),
the correct expression stays exposed via `state()` indefinitely, and
nothing advances until the learner explicitly continues. That explicit
continue reuses the **existing** `continue_to_next()` method and
`POST /api/continue` endpoint (already used by sentence mode's
`"feedback"` step) — no new endpoint. The CLI gets an equivalent
"press Enter to continue" pause, gating the already-existing
`append_attempt()` call, only when recall-only and the answer was wrong.

## Technical Context

**Language/Version**: Python 3.11+; vanilla JS for the web UI changes

**Primary Dependencies**: None new

**Storage**: N/A — same progress-log format, only the timing of one
`append_attempt()` call changes (spec.md FR-006)

**Testing**: pytest, existing tiers, plus the established "static content
assertion" tier for `app.js`/`index.html` (no JS test runner in this
project). Key behavioral assertions: recall-only + correct behaves
exactly as before (regression guard); recall-only + incorrect stops in
`"reveal"`, does not write to the progress log or advance
`current_index` until `continue_to_next()` is called; `continue_to_next()`
now accepts `"reveal"` in addition to `"feedback"`; sentence mode is
completely unaffected.

**Target Platform**: Existing CLI and web UI, both (spec.md FR-007)

**Project Type**: Single project — touches both `src/cli/` and
`src/web/`, continuing `011`/`012`'s precedent

**Performance Goals**: N/A

**Constraints**:
- MUST NOT change sentence mode's behavior at all (spec.md FR-005) —
  `continue_to_next()`'s existing `"feedback"`-step branch is untouched,
  only a new `"reveal"`-step branch is added alongside it
- MUST NOT introduce a new HTTP endpoint — the existing
  `POST /api/continue` already does exactly what's needed (advance past
  a held attempt); extending which step it's valid from is sufficient
- MUST NOT change what gets recorded in the progress log or how the
  completion tally is computed (spec.md FR-006) — only *when* the
  already-existing `append_attempt()` call for a recall-only attempt
  happens (immediately for correct, deferred until continue for
  incorrect)
- The correct-answer path's existing brief automatic reveal (introduced
  as a bugfix following spec `012`) is explicitly unchanged (spec.md
  FR-001, Assumptions)

**Scale/Scope**: One new `Step` value (`"reveal"`), one new branch each
in `PracticeSession.submit_answer()` and `continue_to_next()`, one
extended tuple in `state()`, one new small CLI helper for the "press
Enter to continue" pause, and a UI change reusing the existing Continue
button rather than adding a new one. No new files in `src/`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Plan requires unit tests (session_state, CLI session) proving the new `"reveal"` branch's hold-then-continue behavior, a regression test proving the correct-answer path is unchanged, and contract tests for `POST /api/continue`'s newly-valid originating step, all written before implementation | PASS |
| II. Pedagogical Accuracy & Safety | No language generation/correction/scoring logic touched — purely a change to *when* an already-computed, already-correct recall result is revealed and advanced past | PASS (N/A) |
| III. Learner Data Privacy | No new data collected or stored — same progress-log fields, same attempt shape, only persisted at a different moment for the incorrect-answer case | PASS (N/A) |

**Post-design re-check**: Phase 1 artifacts introduce no new entities, no
persistence changes, and no language-judgment changes — only a new step
value, two new small method branches (both reusing existing
infrastructure — `_advance_after_attempt`, `append_attempt`,
`PracticeAttempt`), and a UI change that reuses rather than duplicates
the existing Continue button. All three gates still PASS unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/013-confirm-wrong-answer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── web-api-contract-delta.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── session.py           # + a small "press Enter to continue" pause, called only for recall-only + incorrect, gating the existing append_attempt() call for that one case
└── web/
    ├── app.py                 # no route changes — POST /api/continue already dispatches to continue_to_next()
    ├── session_state.py       # + "reveal" Step value; submit_answer() branches recall-only correct (unchanged) vs. incorrect (new: hold, step="reveal"); continue_to_next() gains a "reveal" branch (append then _advance_after_attempt); state()'s accepted_expressions/answer/correct tuple extended to include "reveal"
    ├── templates/index.html   # move #continue-button out of #feedback-view to a persistent element (like #word-feedback), so it's reusable for both "feedback" and the new "reveal" step
    └── static/
        └── app.js             # answerForm handler gains a third branch for state.step === "reveal" (render and stop — no timer); renderWordFeedback() and a new renderContinueButton() extend their step checks to include "reveal"

tests/
├── contract/
│   └── test_web_api_contract.py         # + POST /api/continue valid from "reveal"; full recall-only-wrong-then-continue flow through the test client
├── integration/
│   └── test_session_mode.py             # + CLI recall-only wrong-answer pause test (mirrors existing style)
└── unit/
    ├── test_session_state.py             # + submit_answer()/continue_to_next() "reveal" branch tests; regression test for the unchanged correct-answer path
    └── test_web_static_assets.py          # + assertions for app.js's new branch and the moved/shared continue-button markup
```

**Structure Decision**: Single project (existing Option 1 layout,
established `001`–`012`). No new files anywhere in `src/`.

## Complexity Tracking

*No constitution violations requiring justification. Table omitted.*
