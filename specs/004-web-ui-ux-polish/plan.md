# Implementation Plan: Web UI State & Feedback Polish

**Branch**: `004-web-ui-ux-polish` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-web-ui-ux-polish/spec.md`

## Summary

A presentation-only fix pass over `003-web-ui`'s existing page
(`src/web/templates/index.html`, `static/style.css`, `static/app.js`),
grounded in concrete gaps found by re-reading that code against this
feature's five requirements:

1. **Input/button detachment (real bug)**: `input[type="text"] { width:
   100% }` inside a `flex-direction: column` section pushes the submit
   button onto its own line below a full-width input — exactly the
   "awkwardly detached" symptom described. Fix: wrap each input+button pair
   in a row container.
2. **No color, and wording doesn't match the requested format (real gap)**:
   `recallResultEl.textContent` is set but never colored, and reads
   "Correct! Accepted expression(s): …" rather than the requested "Correct:
   …" / "Incorrect. The correct expression is: …". Fix: add
   correct/incorrect CSS classes and update the JS string.
3. **Word feedback is lost when the sentence step appears (real bug)**: the
   feedback text lives inside `#recall-view`, which `showOnly()` hides the
   instant the step advances to `"sentence"` — so the two things Story 1's
   Acceptance Scenario 2 requires shown *together* currently cannot be,
   structurally. Fix: move the word-feedback element out of the
   per-step `<section>`s into a small persistent area rendered from state,
   and extend `GET /api/state` to carry the recall outcome for the
   `"sentence"`/`"feedback"` steps (data already held in
   `PracticeSession.pending_attempt` — no new business logic).
4. **No duplicate-submission guard (real bug)**: nothing disables the
   sentence form while a review is in flight; a second click before the
   first request resolves would fire a second, concurrent
   `POST /api/sentence` (the server only rejects wrong-step requests, and
   the step doesn't advance until the first request's blocking call
   returns). Fix: disable the sentence input/button for the duration of the
   request.
5. **Loading-indicator timing**: already correct in the current code
   (shown before the fetch, hidden in its `finally`, hidden again
   defensively on arrival at the `"sentence"` step) — kept as-is, verified
   by the extended tests rather than rewritten.

## Technical Context

**Language/Version**: Python 3.11+ / vanilla JS+CSS (same as `003-web-ui`,
no new language or version)

**Primary Dependencies**: None new. Same as `003-web-ui` — Flask on the
server, no client-side framework or build step.

**Storage**: Unchanged — no new data, no new persistence. The one backend
touch (below) exposes existing in-memory `PracticeSession` fields through
`GET /api/state`; nothing new is written to disk.

**Testing**: `pytest` + Flask's `app.test_client()` for the extended
`GET /api/state` shape and the duplicate-submission guard's server-visible
effect (a second `POST /api/sentence` while the first is conceptually
"in flight" — see research.md for how this is tested without real
concurrency). Visual claims (color, grouping, no-flash timing) are manual
checks in `quickstart.md`, matching `002`/`003`'s established approach.

**Target Platform**: Same running web server as `003-web-ui`; no new
platform.

**Project Type**: Presentation-layer fix within the existing
`003-web-ui` web application — no new project/package.

**Performance Goals**: No change — this feature touches no LLM call timing
or non-LLM endpoint latency; it only changes what is rendered and adds two
already-computed fields to one JSON response.

**Constraints**: MUST NOT change vocabulary grading (`matcher`), the
sentence-review pipeline (`request_correction`), or progress-log content
(FR-011). The one backend change (extending `GET /api/state`'s payload for
the `"sentence"`/`"feedback"` steps with `answer`/`correct`) MUST be
additive/backward-compatible — existing fields keep their existing meaning.

**Scale/Scope**: Same as `003-web-ui` — single learner, single shared
session; this feature changes rendering and one response shape only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development | New/extended tests for the `GET /api/state` payload additions and the duplicate-submission guard are written before their implementation — see Project Structure and `tasks.md` (next command). | PASS |
| II. Pedagogical Accuracy & Safety | This feature makes no change to language judgment or grading — it only changes how already-correct results are displayed and prevents a duplicate review request. Nothing new for this principle to gate. | PASS |
| III. Learner Data Privacy | No new data collected or exposed beyond what the server already computes for the learner's own current session (their own recall answer/correctness, already sent to their own browser during the same session). No new persistence, no new destination. | PASS |

No violations to justify; **Complexity Tracking** is not needed for this
feature.

**Post-Phase 1 re-check**: `data-model.md` adds no entity, only two
additional fields to an existing runtime-only state shape; `contracts/`
documents that addition as backward-compatible. All three gates still PASS
after design.

## Project Structure

### Documentation (this feature)

```text
specs/004-web-ui-ux-polish/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/web/
├── session_state.py   # CHANGED: state() includes `answer`/`correct` for the
│                       # "sentence" and "feedback" steps (from the existing
│                       # pending_attempt — no new fields are computed, only
│                       # exposed); no change to submit_answer/submit_sentence's
│                       # grading/review logic
├── app.py              # unchanged
├── templates/
│   └── index.html      # CHANGED: word-feedback element moved out of
│                        # #recall-view into a persistent area; input+button
│                        # pairs wrapped in a row container (FR-004)
└── static/
    ├── style.css        # CHANGED: .field-row layout for input+button;
    │                    # .feedback-correct/.feedback-incorrect colors;
    │                    # disabled-state styling for the sentence form
    └── app.js           # CHANGED: render word feedback from state (not
                          # from the transient POST /api/answer response
                          # alone) so it survives a reload; disable the
                          # sentence form for the duration of its request;
                          # exact wording per spec's Assumptions

tests/
├── contract/
│   └── test_web_api_contract.py       # EXTENDED: GET /api/state for
│                                        # "sentence"/"feedback" steps
│                                        # includes `answer`/`correct`
├── integration/
│   └── test_web_session_flow.py      # EXTENDED: a second POST /api/sentence
│                                       # sent while PracticeSession is still
│                                       # mid-review is rejected/ignored
│                                       # (see research.md for how this is
│                                       # simulated deterministically)
└── unit/
    └── test_session_state.py         # EXTENDED: state()'s new fields for
                                        # "sentence"/"feedback" steps
```

**Structure Decision**: No new files, no new package. Every change is
either presentation (`templates/`, `static/`) or a strictly additive field
on the one existing runtime state shape (`session_state.py`'s `state()`
method) — consistent with this being a UX/rendering fix on top of
`003-web-ui`, not a new feature surface.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
