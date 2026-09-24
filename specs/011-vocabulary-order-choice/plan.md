# Implementation Plan: Choose Sequential or Random Word Order

**Branch**: `011-vocabulary-order-choice` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-vocabulary-order-choice/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Both the CLI and the web UI gain an `order` setting (`"sequential"`
[default, today's exact behavior] or `"random"`). The pool is shuffled
**once**, right when it's finalized — in `PracticeSession.__init__()`'s
already-existing "locked" branch for a pre-selected group, or in the
already-existing `select_collection()` for the web UI's interactive
picker — then walked forward exactly as today (spec `001` FR-016's
"forward order only" rule is about traversal direction, not file order;
see spec.md Assumptions). The web UI's interactive collection-choice
screen (spec `007`) gains an order toggle submitted together with the
collection in the same `POST /api/select` call, rather than a second
screen. The CLI gets a new `--order` flag alongside its existing
`--group`.

## Technical Context

**Language/Version**: Python 3.11+ (`random.shuffle` from the standard
library — no new dependency); vanilla JS for the one new web-UI control

**Primary Dependencies**: None new — `random` is stdlib

**Storage**: N/A — the choice is never persisted (spec.md Assumptions: no
settings file/database exists in this project)

**Testing**: pytest, existing tiers. Shuffling itself is verified by
patching `random.shuffle` and asserting it's called exactly when
`order == "random"` and never otherwise — actual randomness isn't
something a deterministic test should depend on; what's testable and
matters is (a) shuffle is invoked only when asked for, and (b) the result
is always a permutation of the same items (spec.md FR-002)

**Target Platform**: Existing CLI and web UI, both

**Project Type**: Single project — touches both `src/cli/` and
`src/web/`, the first feature to touch both since `001`-`003` (every
interactive feature since — `006`, `007`, `009` — was web-UI-only; see
spec.md's Clarifications for why this one differs)

**Performance Goals**: N/A — shuffling a list of tens of words is
effectively instantaneous

**Constraints**:
- MUST default to `"sequential"` everywhere, so every existing caller
  that doesn't pass `order` keeps today's exact behavior (spec.md FR-003,
  SC-003) — mirrors how `offer_choice`/`group` defaults already work
- MUST shuffle exactly once, before the first word is shown, never
  re-shuffling mid-session (FR-003)
- MUST NOT change `submit_answer`/`submit_sentence`/`skip_sentence`/
  `continue_to_next` or their CLI equivalents at all — only *how the pool
  is ordered before the walk starts* changes, not the walk itself (FR-004)
- MUST NOT add a new interactive screen in the web UI — the order choice
  is added to the existing collection-choice screen (spec `007`),
  submitted together in one `POST /api/select` call
- For the web UI, `--order` (a startup flag) only has any effect when
  `--group` is also given (i.e., only in `group_locked` mode) — when no
  `--group` is given, the interactive choose screen always governs order
  fresh, the same way it already governs collection choice regardless of
  any startup default (research.md §3)

**Scale/Scope**: One new parameter threaded through `PracticeSession.__init__`/
`select_collection` (web), `run_session` (CLI), `create_app` (web), and one
new `--order` flag on both CLI entry points; one new control on the web
UI's existing choose screen; no new files in `src/`, one new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Plan requires unit tests (session_state, CLI session) proving shuffle is invoked only for `"random"` and a permutation guarantee holds, contract tests for the new `POST /api/select` field, all written before implementation, per this project's established convention | PASS |
| II. Pedagogical Accuracy & Safety | No language generation/correction/scoring touched — purely which order existing, already-graded words are shown in | PASS (N/A) |
| III. Learner Data Privacy | No new data collected or stored — the choice isn't even persisted (spec.md Assumptions) | PASS (N/A) |

**Post-design re-check**: Phase 1 artifacts (data-model.md, contracts/,
quickstart.md) introduce no new entities, no persistence, and no
language-judgment changes — only a new parameter and one new UI control.
All three gates still PASS unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/011-vocabulary-order-choice/
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
│   ├── __main__.py          # + --order {sequential,random} flag
│   └── session.py           # + order parameter on run_session(), shuffle after group filtering
└── web/
    ├── __main__.py           # + --order {sequential,random} flag (only effective alongside --group — see Constraints)
    ├── app.py                 # + create_app(order=...) param; POST /api/select reads optional "order" from body
    ├── session_state.py       # + order param on __init__ (locked branch) and select_collection() (interactive branch)
    ├── templates/index.html   # + order toggle on the existing #choose-view
    └── static/
        ├── app.js             # + tracks the selected order, includes it in POST /api/select
        └── style.css          # + minor styling for the new toggle, consistent with existing design

tests/
├── contract/
│   └── test_web_api_contract.py         # + POST /api/select "order" field cases
├── integration/
│   ├── test_web_session_flow.py         # + one full web choose-with-random-order scenario
│   └── test_session_order.py            # NEW — CLI-level order tests, mirroring test_session_group_filter.py's style
└── unit/
    ├── test_session_state.py             # + order param tests for __init__ and select_collection()
    └── test_web_static_assets.py          # + assertion that app.js wires up the order toggle
```

**Structure Decision**: Single project (existing Option 1 layout, established `001`–`010`). This is the first feature since `001`–`003` to touch both `src/cli/` and `src/web/` in the same change.

## Complexity Tracking

*No constitution violations requiring justification. Table omitted.*
