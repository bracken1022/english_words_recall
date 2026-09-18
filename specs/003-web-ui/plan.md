# Implementation Plan: Web UI for Remote Access

**Branch**: `003-web-ui` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-web-ui/spec.md`

## Summary

A LAN-reachable web front end for the existing vocabulary tutor, sitting
alongside (not replacing) the CLI from `001-vocab-recall-tutor` /
`002-sentence-review-indicator`. A small Flask app serves one page (recall →
sentence → feedback → next) and three JSON endpoints backed by a new
in-memory `PracticeSession` that is a thin orchestration layer over the
*exact same* existing services — `vocabulary_loader`, `matcher`,
`llm_client.request_correction`, `progress_log` — none of which change.
Vanilla JS shows a spinner during the one slow call (`/api/sentence`) and a
mobile-first CSS layout keeps it usable on phone/tablet/desktop widths. No
database, no auth, bound to the LAN only.

## Technical Context

**Language/Version**: Python 3.11+ (same project as `001`/`002`)

**Primary Dependencies**: `Flask` (new — the web server and its bundled
Jinja2 templating); `requests`, `PyYAML` (already present, used unchanged by
the underlying services this feature calls into). `rich` is CLI-specific and
is not used by the web layer. No client-side framework or build step —
plain HTML/CSS/vanilla JS served as static files.

**Storage**: Unchanged — the existing vocabulary Markdown files and the
existing progress Markdown log (`001-vocab-recall-tutor`'s formats,
untouched). No database is introduced (FR-011, FR-012).

**Testing**: `pytest`, using Flask's `app.test_client()` to exercise the
JSON endpoints without a real browser or network socket; the underlying
services continue to be tested exactly as they already are in `001`/`002`
(this feature adds no new tests for them, since they don't change).

**Target Platform**: A Flask dev server bound to `0.0.0.0` on the host
machine's LAN, reachable from any modern desktop, mobile, or tablet browser
on that same local network (FR-013); not reachable from outside it by
default (FR-015).

**Project Type**: Web application layer added to the existing single-project
CLI tool — server-rendered HTML (one template) + a handful of JSON
endpoints, no separate frontend build/project.

**Performance Goals**: Non-review endpoints (`/api/state`, `/api/answer`,
`/api/continue`) respond well under 200ms, matching the existing tutor's
non-LLM operations. `/api/sentence`'s latency is bounded by the local LLM,
exactly as it already is for the CLI — this feature adds no additional
delay around that call.

**Constraints**: MUST NOT introduce a database (FR-011, FR-012) or any
authentication (FR-014). MUST NOT change `request_correction`'s contract,
`matcher`'s grading rule, or the vocabulary/progress Markdown formats — this
feature is a new transport/UI layer only, calling those exact functions.
MUST bind only to the local network by default (FR-015) — no port-forwarding,
tunneling, or public-hosting configuration is introduced. MUST remain usable
at phone-width, tablet-width, and desktop-width viewports (FR-016). Per
spec.md Assumptions: exactly one shared, in-memory session (no per-visitor
or per-cookie state, no concurrency handling beyond "don't crash") — this
is a deliberate simplification consistent with "multiple users" being out
of scope.

**Scale/Scope**: Single learner, single shared session, LAN-only — same
scale as `001`/`002`; this feature only adds a second way to reach the same
practice loop.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development | New contract tests for each JSON endpoint and a unit-tested `PracticeSession` state machine are written before their implementation — see Project Structure and `tasks.md` (next command). | PASS |
| II. Pedagogical Accuracy & Safety | This feature changes no language-judging logic: `request_correction`'s contract (`001`'s `contracts/ollama-correction-contract.md`) and `matcher`'s grading rule are called unchanged. There is nothing new here for this principle to gate — the review pipeline's correctness guarantees (fixture-tested in `001`) carry over unmodified. | PASS |
| III. Learner Data Privacy | No new data collection: the same recall answers, sentences, and feedback already sent to the local LLM and logged to the local Markdown file are unchanged in kind or destination. The one new consideration — the server is now reachable by any device on the local network, unauthenticated — is an explicit, already-decided tradeoff in spec.md (FR-014/FR-015/Assumptions), not a new principle violation: data still never leaves the learner's own local network to any third party. | PASS |

No violations to justify; **Complexity Tracking** is not needed for this
feature (adding a web framework dependency is not a constitution violation).

**Post-Phase 1 re-check**: `data-model.md` adds one runtime-only,
non-persisted concept (`PracticeSession`) and no database; `contracts/`
describes the new JSON/UI surface without changing the existing Ollama or
Markdown-format contracts from `001`. All three gates still PASS after
design.

## Project Structure

### Documentation (this feature)

```text
specs/003-web-ui/
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
├── models/                    # unchanged (from 001)
├── services/                  # unchanged (from 001/002) — vocabulary_loader.py,
│                               # matcher.py, llm_client.py, progress_log.py are
│                               # called by the web layer but not modified
├── lib/                        # unchanged (from 001)
├── cli/                        # unchanged (from 001/002) — the existing CLI
│                               # keeps working side by side with the web UI
└── web/                        # NEW
    ├── __main__.py             # entry point: `python -m src.web --vocab-dir ...
    │                           # --progress-file ... --group ... --host 0.0.0.0
    │                           # --port ... --ollama-url ... --model ...`
    ├── app.py                  # create_app(...) factory: builds the Flask app,
    │                           # registers routes, owns one PracticeSession
    ├── session_state.py        # PracticeSession: load items (via
    │                           # vocabulary_loader), track current
    │                           # index/step, wrap matcher/request_correction/
    │                           # progress_log calls — no new business logic,
    │                           # just sequencing across HTTP requests
    ├── templates/
    │   └── index.html          # single-page shell (Jinja2)
    └── static/
        ├── style.css           # mobile-first responsive layout
        └── app.js              # fetch()-based interactivity + spinner around
                                 # the /api/sentence call only

tests/
├── contract/
│   └── test_web_api_contract.py      # NEW: request/response shape and status
│                                       # codes for /api/state, /api/answer,
│                                       # /api/sentence, /api/continue
├── integration/
│   └── test_web_session_flow.py      # NEW: full recall→sentence→continue cycle
│                                       # via Flask's test client; malformed-vocab
│                                       # warning surfaced; empty-pool handling;
│                                       # LAN-binding configuration
└── unit/
    └── test_session_state.py         # NEW: PracticeSession step transitions,
                                        # forward-only guarantee, out-of-order
                                        # request rejection (e.g., /api/sentence
                                        # before /api/answer)
```

**Structure Decision**: Still a single project — `src/web/` is added
alongside the existing `src/cli/`, both consuming the same
`models/`/`services/`/`lib/` with no duplication of business logic. There is
no separate frontend project/build: the page is server-rendered and the
client-side code is plain static JS/CSS, matching "simple" from the spec and
avoiding a second toolchain.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
