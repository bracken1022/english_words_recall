# Implementation Plan: Multiple Learner Accounts with Simple Login

**Branch**: `015-multi-account-login` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-multi-account-login/spec.md`

## Summary

Let several household members use one running web tutor, each under their
own account. The operator lists accounts (username, password, optional
display name) in a gitignored `accounts.yml` read at start-up — no sign-up
or verification. The web UI shows a login screen until a valid login; a
Flask signed cookie remembers the username. Each account gets its own
`PracticeSession` (via a small registry) and its own progress file — the
first account keeps the existing `progress.md`, others get
`progress-<username>.md`. A single `before_request` guard returns `401` for
any `/api/*` call without a login. Grading, review, vocabulary loading, the
progress-log format, and the CLI are unchanged.

## Technical Context

**Language/Version**: Python 3.11+ (back end); vanilla JS/HTML/CSS (front end, no build step)

**Primary Dependencies**: Flask ≥3.0 (signed-cookie `session`), PyYAML ≥6.0 — both already present; no new dependencies

**Storage**: Plain files — `accounts.yml` (read-only, new); per-account Markdown progress logs (existing format); in-memory practice sessions

**Testing**: pytest (contract / integration / unit, Flask `test_client`); ruff

**Target Platform**: Local machine running the Flask dev server, reached from browsers on the home LAN (desktop and phone)

**Project Type**: Single project — CLI + web UI sharing `src/services`

**Performance Goals**: Login round trip feels instant (< 200 ms on LAN); a slow Ollama review for one account must not block the other account's requests

**Constraints**: Must not change grading, review, persistence, or the progress-log format; must keep every existing test passing unchanged; passwords never printed or rendered; no new dependencies

**Scale/Scope**: 2–5 accounts, ~2 concurrent learners; ~8 source files touched/added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Test-First (NON-NEGOTIABLE) | Tests for account loading/validation, the login API, the `401` guard, per-account isolation (state + progress files), logout discarding the word in progress, and start-up failure messages are written and seen failing before implementation. Tasks must order tests ahead of code. | ✅ Planned |
| II. Pedagogical Accuracy & Safety | No change to how English is generated, graded, corrected, or explained. `matcher`, `llm_client`, and `PracticeSession` logic are untouched; existing correctness tests still run unchanged. | ✅ N/A — no new language logic |
| III. Learner Data Privacy | Spec's "Data Handling" section documents what's collected and why. Design minimizes it: cookie holds only the username; passwords live only in the gitignored `accounts.yml` and are never logged/printed/rendered; each learner's history is a separate file and the API only ever acts on the logged-in account's data; nothing leaves the machine. | ✅ Pass |

No violations → Complexity Tracking left empty.

**Post-design re-check (after Phase 1)**: still passes. The design adds no
language logic (II); contracts specify the generic login error, the
no-password-in-output rule, and per-account file separation (III); every
contract has a matching test group to write first (I). One deliberate
choice is recorded rather than hidden: plain-text passwords with no
lockout, justified by the spec's trusted-household assumption (research R6).

## Project Structure

### Documentation (this feature)

```text
specs/015-multi-account-login/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R9
├── data-model.md        # Phase 1: Account, Login, SessionRegistry
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── accounts-file-format.md
│   ├── web-auth-api-contract.md
│   └── login-ui-contract.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
accounts.example.yml             # NEW — committed template
.gitignore                       # + /accounts.yml, /progress-*.md

src/
├── models/
│   └── account.py               # NEW — Account dataclass (password hidden from repr)
├── services/
│   └── accounts.py              # NEW — load_accounts(), AccountsFileError, authenticate()
├── web/
│   ├── session_registry.py      # NEW — {username: PracticeSession}, get()/reset()
│   ├── app.py                   # create_app(accounts=None): login/logout routes,
│   │                            #   before_request guard, per-account session lookup,
│   │                            #   "account" in /api/state
│   ├── __main__.py              # --accounts-file; load/validate; exit 2 on error; banner
│   ├── session_state.py         # unchanged
│   ├── templates/index.html     # #login-view, header #account-name + #logout-button
│   └── static/
│       ├── app.js               # 401 → login view; login/logout handlers
│       └── style.css            # login form + header account styles (existing tokens)
└── cli/                         # unchanged

tests/
├── unit/
│   ├── test_accounts_loader.py      # NEW — parsing, normalization, every validation error,
│   │                                #   progress-file derivation, no password in messages/repr
│   └── test_session_registry.py     # NEW — lazy create, per-account progress file, reset
├── contract/
│   ├── test_accounts_file_contract.py   # NEW — example file loads; documented messages
│   └── test_web_auth_contract.py        # NEW — /api/login, /api/logout, 401 guard on
│                                        #   every route, "account" in state
└── integration/
    ├── test_multi_account_flow.py   # NEW — two accounts: separate histories, interleaved
    │                                #   sessions, logout discards word, first account owns
    │                                #   pre-existing progress.md
    └── test_web_startup_accounts.py # NEW — __main__ exit 2 + messages; banner has no password
```

**Structure Decision**: Keep the existing single-project layout. New
account parsing goes in `src/models` + `src/services` like vocabulary and
progress; the per-account session registry sits beside `session_state.py`
in `src/web`, since only the web UI has logins. Existing web tests keep
calling `create_app()` without `accounts` and stay valid (research R8).

## Complexity Tracking

No constitution violations to justify.
