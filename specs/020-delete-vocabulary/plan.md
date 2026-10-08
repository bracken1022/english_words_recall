# Implementation Plan: Remove Words I Don't Want to Recall

**Branch**: `main` (commits go straight to main) | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/020-delete-vocabulary/spec.md`

## Summary

A **Remove this word** action appears on the recall, reveal and sentence
screens. After a confirmation:

- a word from the learner's **own list** is cut out of its Markdown
  file, and every other byte of the file stays the same;
- a word from the **shared** sets is hidden for that learner only, in a
  per-account JSON file, and the shared folder is never written.

The session moves on to the next word. An attempt the learner already
made on the removed word is still logged. A toast offers **Undo** until
the learner's next action, and undo restores the file byte for byte.

## Technical Context

**Language/Version**: Python 3.11+; vanilla JS, HTML and CSS

**Primary Dependencies**: existing only (Flask, PyYAML). No new
dependencies.

**Storage**:
- learner list files in `word-lists/<user>/*.md`, which are edited;
- a new hidden JSON file, `word-lists/<user>/.hidden-shared.json`;
- the shared `vocabulary/`, which is never written.

**Testing**: pytest (unit, contract and integration), static-asset
string tests, and screenshot verification.

**Target Platform**: local tutor server, with browsers on the household
LAN (desktop and phone)

**Project Type**: single project

**Performance Goals**: removal is one small file edit, and it is instant.

**Constraints**:
- per-account isolation;
- an exact restore;
- the CLI is unchanged;
- grading and history are unaffected.

**Scale/Scope**: a single word at a time; lists of up to 5,000 words.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan satisfies it | Status |
|---|---|---|
| **I. Test-First** | Tests come first for: the exact cut and restore, hidden shared words, the session step changes, the undo window, the API and isolation. | ✅ |
| **II. Pedagogical Accuracy & Safety** | No language content is generated or changed. Removal only takes the learner's own chosen words out of practice. A confirmation and an undo make mistakes recoverable. | ✅ |
| **III. Learner Data Privacy** | The only new data is the learner's own hidden-word list, stored with their account and never shared. | ✅ |

There are no violations. **Post-design re-check**: ✅.

## Project Structure

### Documentation (this feature)

```text
specs/020-delete-vocabulary/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/remove-word-api.md, contracts/remove-word-ui.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── models/vocabulary_item.py      # + source (compare=False)
├── services/vocabulary_loader.py  # stamp source
├── services/word_lists.py         # + RemovedEntry, remove_word, restore_word, hidden-shared helpers
├── web/session_state.py           # + item_filter, _load(), remove_current, undo_remove, pending_undo
├── web/session_registry.py        # pass the hidden-shared filter
├── web/app.py                     # + POST /api/remove-word, /api/undo-remove
├── web/templates/index.html       # + button, toast
└── web/static/app.js, style.css   # + remove/undo flow
tests/
├── unit/test_word_list_remove.py           # NEW
├── unit/test_session_remove.py             # NEW
├── contract/test_remove_word_api.py        # NEW
└── unit/test_web_static_assets.py          # + appended
```

**Structure Decision**: this is the existing single-project layout. File
edits live in `WordListStore`, and session behaviour lives in
`PracticeSession`.

## Key Decisions

The reasoning is in [research.md](research.md).

1. Each word records its source file. The block is found by its english
   plus chinese (R1).
2. Own lists use a text-level cut with an exact re-insert on undo, and a
   safe fallback if the file changed in between (R2).
3. Shared words are hidden per account in a JSON file and filtered out
   at load (R3, R4).
4. Removal keeps the session's place. An already-made attempt is logged.
   The undo lasts until the next action (R5).

## Complexity Tracking

There are no constitution violations.
