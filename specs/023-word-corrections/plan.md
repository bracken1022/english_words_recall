# Implementation Plan: Automatic Word Corrections

**Branch**: `023-word-corrections` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/023-word-corrections/spec.md`

## Summary

The first time a word comes up in practice, a background check sends its
English, IPA, meaning and parts of speech to Qwen (through the existing
backend `qwen_client` and `word_check` task) and gets corrected values
back. A fully valid answer that differs is saved straight away: into the
list file for a learner's own lists, or into a shared overlay
(`vocabulary/.corrections.json`) that the loader applies on top of the
untouched shared files for everyone. Each changed field is recorded with
its old value; a Corrections page lists them and undoes them. A
content fingerprint marks words as checked, so a word is sent once and
again only after it's edited. The pronunciation keeps the list's
dialect (British for shared and copied lists, American for uploads).
Practice never waits for a check; corrected values show at reveal if the
check finished, otherwise next time.

## Technical Context

**Language/Version**: Python 3.11+ (server); vanilla JavaScript, HTML,
CSS (page)

**Primary Dependencies**: Flask, requests, PyYAML (existing); the
backend Qwen client (`src/services/qwen_client.py`) and word-check task
(`src/services/word_check.py`), both already committed

**Storage**: Files only. Own lists: corrected values written into the
list `.md` blocks. New hidden `.corrections.json` per word folder
(overlay for shared sets, checked fingerprints, records). Shared `.md`
files never written.

**Testing**: pytest (unit, contract, integration), ruff. Qwen is faked
everywhere; `conftest.py` already clears the Qwen environment variables
and blocks real HTTP.

**Target Platform**: The local web app (`python -m src.web`); the CLI
gets the shared overlay through the loader but doesn't run checks.

**Project Type**: Single Python project with a web UI (`src/web`)

**Performance Goals**: No added waiting in practice (SC-003): `prepare`
returns immediately; at most 2 checks in flight; 45 s per-request
timeout

**Constraints**: Only word data leaves the machine (FR-013); key stays
on the server; shared vocabulary files untouched (SC-006); no learner
identifiers in `.corrections.json`

**Scale/Scope**: A family's few accounts on one Mac; about 1,000 words
today, each sent at most once until edited

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan satisfies it | Status |
|---|---|---|
| I. Test-first | Each task in `tasks.md` starts with failing tests: dialect prompt and validation, fingerprints, corrections-file read/write and limits, the service (dedup, cap, pauses, compare-and-set, records, undo), loader overlay and `origin_chinese` keys, the API contract, the page wiring, and the eval tool with a fake checker. | Pass |
| II. Pedagogical accuracy & safety | Answers are only used when every field passes the same rules as hand-written lists, plus the dialect's IPA check and the family-safe filter (FR-007, research R3). Heteronym IPA is never changed. Every change is recorded and undoable (FR-004/005). Quality is measured on a reviewed 100-word fixture before relying on it (SC-001/002, research R10). The English word, spelling variants and examples are never touched, so grading is unaffected. | Pass |
| III. Learner data privacy | Sent to Qwen: the English word, its IPA, meaning, parts of speech and the dialect, nothing else (FR-013, research R11): no account, list name, progress, attempts, examples or recordings. The user explicitly asked for the online service (spec Assumptions); the key stays server-side and errors never leak it (`qwen_client`). `.corrections.json` holds word data only. | Pass |

**Post-design re-check**: Pass. One deliberate change of direction: this
is the first feature that sends data off the machine. It is limited to
word data, off without a key, and documented in the spec and research
R11.

## Project Structure

### Documentation (this feature)

```text
specs/023-word-corrections/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── corrections-api.md
│   ├── corrections-file.md
│   └── word-check-task.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── models/
│   └── vocabulary_item.py        # + origin_chinese (not compared)
├── services/
│   ├── word_check.py             # + dialect (prompt line + IPA check); heteronym IPA kept
│   ├── corrections_file.py       # NEW: read/write .corrections.json, fingerprints, limits
│   ├── corrections.py            # NEW: CorrectionService (prepare/background check, cap 2,
│   │                             #   pause, compare-and-set save, records, undo) + bound view
│   ├── vocabulary_loader.py      # set origin_chinese; apply the folder's overlay
│   ├── examples.py               # shared keys use origin_chinese
│   └── word_lists.py             # hidden keys use origin_chinese; set_values() for a block
├── tools/
│   └── eval_corrections.py       # NEW: errors fixed / right words made worse (SC-001/002)
└── web/
    ├── __main__.py               # "Corrections: on (model)/off" line
    ├── app.py                    # build the service from QwenConfig.from_env();
    │                             #   GET /api/corrections, POST /api/corrections/undo
    ├── session_registry.py       # bind the service per account
    ├── session_state.py          # prepare on _word_started; `corrected` in state
    ├── templates/index.html      # Corrections view; "Updated" note at reveal
    └── static/
        ├── app.js                # load/render corrections, undo, Updated note
        └── style.css

tests/
├── fixtures/word_check_cases.yml # NEW: 50 known errors + 50 right words (reviewed)
├── unit/
│   ├── test_word_check.py        # + dialect, heteronyms
│   ├── test_corrections_file.py  # NEW
│   ├── test_corrections.py       # NEW (fake checker, threads joined)
│   ├── test_vocabulary_overlay.py# NEW: overlay + origin_chinese keys (hidden, examples)
│   ├── test_eval_corrections.py  # NEW
│   └── test_web_static_assets.py # + Corrections view, undo, Updated note
├── contract/
│   └── test_corrections_api.py   # NEW
└── integration/
    └── test_word_corrections_flow.py  # NEW: practise → corrected → reveal → undo → not re-sent
```

**Structure Decision**: Same single project as specs 001–022. The
service follows spec 021's `ExampleService` shape (background thread per
word, bound per account, hidden JSON beside shared files), so the
session and registry wiring is the same as for examples.

## Complexity Tracking

No constitution violations to justify.
