# Implementation Plan: Sentence-Review Loading Indicator

**Branch**: `002-sentence-review-indicator` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-sentence-review-indicator/spec.md`

## Summary

A display-only addition to the existing CLI tutor (`specs/001-vocab-recall-tutor`):
while `run_sentence_step` waits on the local LLM's sentence review, show a
continuously animating, indeterminate spinner (via `rich`, already a
dependency) so the learner can tell the app is still working. The spinner
carries no progress data (no percentage/step count, per FR-004), starts the
instant the request begins, and is removed the instant it settles — for
every existing outcome (needs correction, already correct, missing
expression, or unavailable) unchanged. On non-interactive output, it falls
back to a single plain message instead of animating, since `rich`'s spinner
renders nothing at all there (verified below). No grading, correction, or
data-persistence logic changes.

## Technical Context

**Language/Version**: Python 3.11+ (same project as `001-vocab-recall-tutor`)

**Primary Dependencies**: `rich` (already a dependency) — specifically
`rich.console.Console.status()`, which provides an indeterminate spinner as a
context manager; no new dependency is introduced

**Storage**: N/A — this feature adds no persisted data and does not touch the
existing Markdown vocabulary/progress storage from `001-vocab-recall-tutor`

**Testing**: `pytest` (existing). The indicator's start/stop is asserted by
injecting a test double for the spinner call (or a `rich.console.Console`
bound to a non-`StringIO`/captured stream) rather than by scraping ANSI
animation frames from captured output, which is not a meaningful thing to
assert.

**Target Platform**: Cross-platform terminal (same as `001-vocab-recall-tutor`)

**Project Type**: Single project — command-line application (same as
`001-vocab-recall-tutor`; no new interface is introduced)

**Performance Goals**: The indicator must add no perceptible delay before
appearing (starts in the same call that currently just invokes
`request_correction` directly) and no measurable overhead to the review
request itself — `rich.Console.status()`'s background refresh is negligible
compared to LLM inference latency.

**Constraints**: MUST NOT change `request_correction`'s request/response
handling, the grading/matching logic, or what is written to the progress log
(FR-006) — the indicator wraps the existing call site in `session.py` only.
MUST NOT render a fabricated percentage/step count (FR-004). MUST degrade
safely when `sys.stdout` is not a terminal: verified directly that
`rich.Console.status()` renders **nothing** when `console.is_terminal` is
`False` (see `research.md`), so the implementation MUST explicitly branch on
`console.is_terminal` and print a single plain message in that case (FR-007)
rather than relying on `rich` to handle it.

**Scale/Scope**: Single learner, single review request at a time — identical
scope to `001-vocab-recall-tutor`; this feature only adds UI feedback around
an already-existing single-request call.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development | Tests for the indicator's start/stop behavior (across all four review outcomes, plus the non-terminal fallback) are written before the wrapper is implemented — see Project Structure and `tasks.md` (next command). | PASS |
| II. Pedagogical Accuracy & Safety | This feature makes no change to language judgment, correction content, or the correctness-validation approach already established in `001-vocab-recall-tutor` (FR-006 explicitly forbids it). There is nothing new here for this principle to gate. | PASS |
| III. Learner Data Privacy | No new data is collected, displayed, or persisted — the indicator is transient UI state only, gone the instant the request settles, never written to the progress log. | PASS |

No violations to justify; **Complexity Tracking** is not needed for this feature.

**Post-Phase 1 re-check**: `data-model.md` confirms no new entities; the one
contract added (`contracts/loading-indicator-contract.md`) describes UI
timing only, not a new external dependency or data flow. All three gates
still PASS after design.

## Project Structure

### Documentation (this feature)

```text
specs/002-sentence-review-indicator/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── cli/
│   ├── loading_indicator.py   # NEW: run_with_indicator(console, message, func, *a, **kw) —
│   │                          # spinner via console.status() when console.is_terminal,
│   │                          # else one plain message; always returns func's result unchanged
│   └── session.py             # CHANGED: run_sentence_step wraps its existing
│                               # request_correction(...) call with run_with_indicator(...);
│                               # no other logic in session.py changes
├── models/                    # unchanged (from 001)
├── services/                  # unchanged (from 001) — llm_client.py's request/response
│                               # handling is not modified by this feature
└── lib/                       # unchanged (from 001)

tests/
├── contract/
│   └── test_loading_indicator_contract.py   # NEW: asserts the timing contract in
│                                              # contracts/loading-indicator-contract.md
├── integration/
│   └── test_sentence_correction_flow.py     # EXTENDED (from 001): each existing outcome
│                                              # case now also asserts indicator start/stop
└── unit/
    └── test_loading_indicator.py            # NEW: run_with_indicator behavior in isolation
                                               # (terminal vs. non-terminal, return-value passthrough,
                                               # indicator stops even if func raises)
```

**Structure Decision**: No change to the single-project CLI layout established
in `001-vocab-recall-tutor`. This feature adds exactly one new file
(`src/cli/loading_indicator.py`) and one wrapped call site
(`src/cli/session.py`'s `run_sentence_step`); `src/models/`, `src/services/`,
and `src/lib/` are untouched, matching the Constraints above.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
