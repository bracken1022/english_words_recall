# Implementation Plan: Choose a Vocabulary Collection Before Practicing

**Branch**: `007-select-vocabulary-collection` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-select-vocabulary-collection/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

When the web UI is started without a collection pre-selected (no `--group`
flag), it now shows a new `"choose"` step listing every distinct
collection tag found in the loaded vocabulary (plus a "practice
everything" option and, if any words have no tag, an "ungrouped" option)
before any recall content appears. Picking one scopes the whole session to
just that collection, reusing the existing recall → sentence → feedback →
completion flow unchanged. Reaching "complete" offers a way back to that
same choice screen (re-loading vocabulary from disk, so newly added files
are picked up) rather than a dead end — but only when no collection was
pre-selected at startup; starting with `--group` continues to behave
exactly as it does today; a session in progress never offers a way to
switch collections early (per the 2026-09-20 clarification in spec.md).

No changes to vocabulary content, the vocabulary file format, the CLI, or
the sentence-correction pipeline are needed — this is purely a new
selection layer in front of the existing, unchanged `PracticeSession`
mechanics.

## Technical Context

**Language/Version**: Python 3.11+ (backend, per `pyproject.toml`); vanilla ES2017 JavaScript, HTML, CSS (frontend — no build step, no framework)

**Primary Dependencies**: Flask 3.x, PyYAML — both already in use; no new dependencies

**Storage**: Plain Markdown files (`progress.md`, vocabulary `*.md`) — unchanged; this feature adds no new storage, only a new in-memory selection layer over the same loaded pool

**Testing**: pytest, three existing tiers (`tests/contract`, `tests/integration`, `tests/unit`); frontend behavior covered by static-content assertions (established convention) plus a manual `quickstart.md` browser pass, consistent with `005`/`006`

**Target Platform**: Existing LAN-reachable Flask dev server (`src/web`); single learner, no auth

**Project Type**: Single project (existing `src/`, `tests/` layout, unchanged)

**Performance Goals**: N/A — single learner, local requests; vocabulary files are small (tens of words), so a full reload on returning to the choice screen is effectively instantaneous

**Constraints**:
- MUST NOT change `src/services/vocabulary_loader.py`, `src/models/vocabulary_item.py`, `src/models/practice_attempt.py`, or the vocabulary/progress-log file formats — this feature is a selection layer over data shapes that already exist
- MUST NOT change CLI behavior (`src/cli/`) at all — the CLI keeps its existing `--group` startup flag, unchanged (spec.md Assumptions)
- MUST preserve byte-identical behavior for the web UI when `--group` is passed at startup (SC-004) — the new `"choose"` step and `"restart"` action only exist when no collection was pre-selected
- MUST follow the additive "Contract Delta" convention already established by `004`/`006` for amending `003-web-ui`'s API contract

**Scale/Scope**: One new state-machine step (`"choose"`), two new `PracticeSession` methods (`select_collection`, `restart`), two new endpoints (`POST /api/select`, `POST /api/restart`), one new template section rendered dynamically from server-provided data, no new files/dependencies

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Plan requires unit tests for `select_collection`/`restart`/collection-listing, contract tests for both new endpoints, and an integration test for the full choose → practice → complete → restart loop, all written before their implementation, following the project's established red-green-refactor convention | PASS |
| II. Pedagogical Accuracy & Safety | No new language generation, correction, or scoring logic — this feature only changes which existing words are in the practice pool | PASS (N/A) |
| III. Learner Data Privacy | No new data collected; progress-log entries are unchanged in shape and still all go to the one `--progress-file` regardless of which collection produced them | PASS |

**Relationship to prior "no skip/back" requirements** (`001` FR-016, `003` FR-010, reaffirmed by `006`'s plan): those requirements govern movement *within* a single pool traversal (no skipping an unanswered item, no revisiting an answered one). This feature doesn't touch that — `"choose"` only appears *before* a traversal starts or *after* one has fully finished (`"complete"`), never mid-traversal (the 2026-09-20 clarification makes this explicit in spec.md). No exception to those requirements is needed here, unlike `006`.

**Post-design re-check**: Phase 1 artifacts (data-model.md, contracts/web-api-contract-delta.md, quickstart.md) introduce one new derived view (the collections list, computed from data that already exists — no new persistent entity) and two new endpoints that are additive and match existing conventions exactly (see research.md). All three gates still PASS unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/007-select-vocabulary-collection/
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
├── models/                     # UNCHANGED
├── services/
│   └── vocabulary_loader.py    # UNCHANGED — still returns a flat (items, warnings); no group filtering here, same as today
├── cli/                        # UNCHANGED — out of scope (see spec.md Assumptions)
└── web/
    ├── app.py                  # + POST /api/select, + POST /api/restart
    ├── session_state.py        # + "choose" step, + select_collection(), + restart(), + collection-listing helper
    ├── templates/index.html    # + choose-view section (collections rendered client-side from state)
    └── static/
        ├── app.js              # + choose-view rendering/handlers, + restart handling on complete-view
        └── style.css           # + choose-view styling, consistent with the existing notebook/card design

tests/
├── contract/
│   └── test_web_api_contract.py         # + POST /api/select, POST /api/restart cases
├── integration/
│   └── test_web_session_flow.py         # + full choose → practice → complete → restart scenario
└── unit/
    ├── test_session_state.py             # + select_collection()/restart()/collection-listing tests
    └── test_web_static_assets.py          # + assertion that app.js renders/wires the choose-view and restart control
```

**Structure Decision**: Single project (existing Option 1 layout, established by `001`–`006`). This feature only touches the existing `src/web/` slice; no new projects, packages, or directories.

## Complexity Tracking

*No constitution violations requiring justification. Table omitted.*
