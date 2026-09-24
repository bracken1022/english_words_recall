# Implementation Plan: Choose Recall-Only or Sentence Practice Mode

**Branch**: `012-practice-mode-choice` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-practice-mode-choice/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Both the CLI and the web UI gain a `mode` setting (`"sentence"` [default,
today's exact behavior] or `"recall-only"`). It's stored on
`PracticeSession` (unlike `order`/`group`, which are consumed once and
discarded, `mode` must persist for the whole session because it's
consulted on every `submit_answer()` call). When `mode == "recall-only"`,
`submit_answer()` finalizes the attempt and advances immediately — the
same tail logic `skip_sentence()`/`continue_to_next()` already use
(record the attempt, tally if correct, advance `current_index`, land on
`"recall"` or `"complete"`) — instead of transitioning to `"sentence"`.
No sentence-writing step is ever shown, and `request_correction()` is
never called, in that mode. The web UI's interactive choose screen
(specs `007`/`011`) gains a third control (mode), submitted together with
collection and order in the same `POST /api/select` call. The CLI gets a
new `--mode` flag alongside its existing `--group`/`--order`.

## Technical Context

**Language/Version**: Python 3.11+; vanilla JS for the one new web-UI
control

**Primary Dependencies**: None new

**Storage**: N/A — the choice is never persisted (spec.md Assumptions: no
settings file/database exists in this project)

**Testing**: pytest, existing tiers. The key behavioral assertion is that
in recall-only mode, `submit_answer()` never leaves `self.step` at
`"sentence"` and `request_correction`/`run_sentence_step` is never
called; in sentence mode (default), behavior is provably unchanged
(existing test suite already covers it end to end).

**Target Platform**: Existing CLI and web UI, both

**Project Type**: Single project — touches both `src/cli/` and
`src/web/`, following the same shape as spec `011`

**Performance Goals**: N/A — this only changes which steps a session
visits, not any per-request cost

**Constraints**:
- MUST default to `"sentence"` everywhere, so every existing caller that
  doesn't pass `mode` keeps today's exact behavior (spec.md FR-005) —
  mirrors how `order`/`group`/`offer_choice` defaults already work
- MUST decide the mode once, before the first word is shown, and MUST
  NOT change it partway through a session (FR-004) — unlike `order`
  (consumed once at pool-finalization time), `mode` must be stored as
  session state (`self.recall_only`) because `submit_answer()` consults
  it on every single word, not just once at the start
- MUST NOT call `request_correction` (web) / `run_sentence_step` (CLI)
  at all in recall-only mode (FR-002, SC-001) — not "call it and ignore
  the result," genuinely skipped
- MUST NOT add a new interactive screen in the web UI — the mode choice
  is added to the existing collection/order choice screen (specs
  `007`/`011`), submitted together in one `POST /api/select` call
- MUST reuse `skip_sentence()`/`continue_to_next()`'s existing
  attempt-finalization tail (record → tally → advance `current_index` →
  land on `"recall"`/`"complete"`) rather than duplicating that logic a
  third time

**Scale/Scope**: One new parameter threaded through
`PracticeSession.__init__`/`select_collection` (web, stored as
`self.recall_only`), `run_session` (CLI), `create_app` (web), and one new
`--mode` flag on both CLI entry points; one new control on the web UI's
existing choose screen; no new files in `src/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Plan requires unit tests (session_state, CLI session) proving recall-only mode never enters "sentence"/calls the correction function, and sentence mode is unaffected, plus contract tests for the new `POST /api/select` field, all written before implementation, per this project's established convention | PASS |
| II. Pedagogical Accuracy & Safety | No language generation/correction/scoring logic is added or changed — recall-only mode only removes an existing, already-verified step from the flow; sentence mode's existing correction logic is untouched | PASS (N/A) |
| III. Learner Data Privacy | No new data collected — recall-only mode collects *strictly less* (no sentence text is ever written or sent to the local LLM in that mode); nothing is persisted beyond today's existing progress-log fields | PASS (N/A) |

**Post-design re-check**: Phase 1 artifacts (data-model.md, contracts/,
quickstart.md) introduce no new entities, no persistence, and no
language-judgment changes — only a new parameter/stored flag and one new
UI control. All three gates still PASS unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/012-practice-mode-choice/
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
│   ├── __main__.py          # + --mode {sentence,recall-only} flag
│   └── session.py           # + mode parameter on run_session(); skips run_sentence_step() entirely when recall-only
└── web/
    ├── __main__.py           # + --mode {sentence,recall-only} flag (only effective alongside --group — mirrors --order)
    ├── app.py                 # + create_app(mode=...) param; POST /api/select reads optional "mode" from body
    ├── session_state.py       # + mode param on __init__ (locked branch) and select_collection() (interactive branch), stored as self.recall_only; submit_answer() branches on it
    ├── templates/index.html   # + mode toggle on the existing #choose-view, alongside the order toggle
    └── static/
        ├── app.js             # + tracks the selected mode, includes it in POST /api/select
        └── style.css          # + minor styling for the new toggle, reusing the order-toggle treatment

tests/
├── contract/
│   └── test_web_api_contract.py         # + POST /api/select "mode" field cases; recall-only end-to-end via the test client
├── integration/
│   └── test_session_order.py            # (unchanged — mode is a separate concern from order)
└── unit/
    ├── test_session_state.py             # + mode/self.recall_only tests for __init__, select_collection(), and submit_answer()'s branch
    └── test_web_static_assets.py          # + assertion that app.js wires up the mode toggle

# CLI-level mode test lives alongside the existing session tests:
tests/integration/test_session_group_filter.py  # unchanged; a new sibling test module or additions cover mode (see tasks.md)
```

**Structure Decision**: Single project (existing Option 1 layout,
established `001`–`011`). Continues `011`'s precedent of touching both
`src/cli/` and `src/web/` in the same change.

## Complexity Tracking

*No constitution violations requiring justification. Table omitted.*
