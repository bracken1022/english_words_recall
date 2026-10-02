# Implementation Plan: Personal Word Lists per Account

**Branch**: `016-per-user-word-lists` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/016-per-user-word-lists/spec.md`

## Summary

Let each logged-in learner upload their own word lists from the web UI and
practise only their own words.

- **Upload formats**: a file can be the existing vocabulary Markdown, or a
  simple `English, Chinese` list / CSV, which accepts tabs and full-width
  commas.
- **Storage**: each upload is validated, converted to the existing Markdown
  format, and saved as `word-lists/<username>/<list name>.md`. Every word's
  `group` is set to the list name, so each list shows up as its own word
  set.
- **Which words an account practises**: if the account has at least one
  list, it uses its own folder; otherwise it uses the shared `vocabulary/`
  folder, as the user asked.
- **Session changes**: `PracticeSession` gains a single
  `set_vocab_dir()` method, so a new list appears on the word-set screen
  right away while a session in progress is left alone.
- **Unchanged**: grading, review, the progress history and the CLI.

## Technical Context

**Language/Version**: Python 3.11+ for the back end; vanilla JS, HTML and CSS for the front end (no build step)

**Primary Dependencies**: Flask ≥3.0 (multipart uploads, `MAX_CONTENT_LENGTH`), PyYAML ≥6.0, and the standard-library `csv`. No new dependencies.

**Storage**: plain files.
- New: `word-lists/<username>/*.md` in the existing vocabulary format.
- Existing, unchanged: the shared `vocabulary/` folder and the per-account progress logs from spec 015.

**Testing**: pytest (contract, integration and unit tests, using Flask's `test_client` with multipart data); ruff

**Target Platform**: the local Flask server on the home LAN, used from desktop and phone browsers (uploads come from the phone's file picker)

**Project Type**: a single project, with the CLI and the web UI sharing `src/services`

**Performance Goals**: parsing and saving a 5,000-word upload takes under 1 second; the word-set screen refreshes immediately after an upload

**Constraints**:
- no database;
- uploads are at most 1 MiB and 5,000 words;
- a learner can never reach another account's folder;
- a session in progress is never disrupted;
- the existing tests stay unchanged;
- grading, review and the progress-log format are unchanged.

**Scale/Scope**: 2–5 accounts, tens of lists each; about 9 source files touched or added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Test-First (NON-NEGOTIABLE) | Tests are written first and seen failing for each of these: upload parsing (both formats, decoding, skip reporting, limits); `WordListStore` (save, replace, delete, name sanitising, per-account isolation, effective folder); `PracticeSession.set_vocab_dir`; the API contract (every status code, the login guard, isolation, path traversal); the integration flows (first upload switches the account to its own words, deleting the last list switches it back, a session in progress survives a replace); and static UI assertions. | ✅ Planned |
| II. Pedagogical Accuracy & Safety | No change to how answers are graded, how sentences are reviewed, or how feedback is shown. Uploaded words become ordinary `VocabularyItem`s, and the existing correctness tests still apply. The one content-related risk is a learner uploading wrong translations. That is the learner's own material, which the tutor never presents as authoritative; it is graded exactly as written, the same as shared vocabulary today. | ✅ No new language logic |
| III. Learner Data Privacy | The spec has a "Data Handling" section covering what is collected (the learner's lists) and why. Lists are stored only on the operator's machine, in each account's own folder. They can be reached only through that account's login, by name, inside that folder (path traversal is tested). No list content is logged or sent anywhere, and `word-lists/` is gitignored. | ✅ Pass |

No violations, so Complexity Tracking is left empty.

**Post-design re-check**: still passes. The contracts state the isolation guarantees. The design adds one small method to `PracticeSession` (R3), which stays outside grading and persistence. Sharing parsing with `parse_blocks` and `VocabularyItem` means uploaded Markdown is validated by exactly the same rules as shared vocabulary.

## Project Structure

### Documentation (this feature)

```text
specs/016-per-user-word-lists/
├── plan.md              # This file
├── research.md          # Phase 0: R1–R9
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── upload-formats.md
│   ├── word-lists-api-contract.md
│   └── word-lists-ui-contract.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
.gitignore                         # + /word-lists/

src/
├── services/
│   └── word_lists.py              # NEW: parse_upload(), UploadFormatError,
│                                  #   sanitize_list_name(), WordListStore
├── web/
│   ├── session_state.py           # + set_vocab_dir() (only change)
│   ├── session_registry.py        # takes the store; effective folder per account;
│   │                              #   + refresh_vocab()
│   ├── app.py                     # create_app(..., word_lists_dir=None); /api/word-lists
│   │                              #   GET/POST/DELETE; MAX_CONTENT_LENGTH + JSON 413;
│   │                              #   "word_source" in /api/state
│   ├── __main__.py                # --word-lists-dir (default word-lists); banner line
│   ├── templates/index.html       # upload button, hidden input, hint, result, My word lists
│   └── static/
│       ├── app.js                 # upload / replace-confirm / delete flows
│       └── style.css              # list rows and upload area (existing tokens)
└── cli/, models/, lib/            # unchanged

tests/
├── unit/
│   ├── test_word_list_parsing.py      # NEW: both formats, separators, header,
│   │                                  #   decoding, skip messages, limits
│   ├── test_word_list_store.py        # NEW: save/replace/delete, names, isolation,
│   │                                  #   effective_dir, atomic file, round-trip load
│   ├── test_session_state.py          # + set_vocab_dir cases (additions only)
│   ├── test_session_registry.py       # + effective folder and refresh_vocab (additions)
│   └── test_web_static_assets.py      # + upload UI assertions (additions)
├── contract/
│   └── test_word_lists_api_contract.py    # NEW
└── integration/
    └── test_word_lists_flow.py        # NEW: two accounts end to end
```

**Structure Decision**: keep the existing single-project layout. All upload
parsing and storage goes into one new service module, next to
`vocabulary_loader.py`. The web layer gets thin routes plus the registry
hook. `create_app(word_lists_dir=None)` means "no uploads": the
word-list routes are not registered, and every account uses the shared
folder. That keeps spec 015's tests and app factory calls valid. The entry
point always passes `--word-lists-dir`, so the real web UI always has
uploads. `SessionRegistry` likewise works without a store.

## Complexity Tracking

No constitution violations to justify.
