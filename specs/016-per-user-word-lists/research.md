# Research: Personal Word Lists per Account

Context resolved from the codebase: Python 3.11+, Flask ≥3.0, PyYAML,
pytest. Vocabulary is loaded by `src/services/vocabulary_loader.py::
load_vocabulary(dir)` from every `*.md` file in one directory. Spec 015
gives each account its own `PracticeSession` via `SessionRegistry`, but all
sessions read the same shared `vocab_dir`. `PracticeSession` loads the
vocabulary in `__init__`, `restart()` and `end_session()`. No new
dependencies are needed (`csv` is in the standard library).

## R1. Where an account's lists live

- **Decision**: A new `--word-lists-dir` (default `./word-lists`,
  gitignored), with one sub-folder per account: `word-lists/<username>/`.
  Each list is one file, `<list name>.md`, in the **existing vocabulary
  Markdown format**. A CSV or simple-list upload is converted to that
  format when it's saved.
- **Rationale**: FR-011 asks for plain, readable files, consistent with
  today's data. Storing every list in the format `load_vocabulary` already
  reads means the practice side needs **no new parser**: an account's
  folder is just another vocabulary directory. Usernames are already
  restricted to `[a-z0-9_-]` (spec 015), so they are safe folder names.
- **Alternatives considered**:
  - *Keep the original uploaded file (CSV as CSV)*: the loader would need
    to understand several formats at practice time, and a bad file could
    break a session later. Rejected; formats are validated and normalised
    once, at upload.
  - *A database or JSON index*: against the project's "plain files, no
    database" rule (README). Rejected.
  - *Folders inside `vocabulary/`*: `load_vocabulary` only globs the top
    level today, but mixing operator files and uploads in one tree is
    confusing, and the CLI points at `vocabulary/`. Rejected.

## R2. Own lists vs shared folder (the user's Q2 answer)

- **Decision**: `effective_vocab_dir(account)` returns
  `word-lists/<username>/` if that folder contains at least one `*.md`
  file, otherwise the shared `--vocab-dir`. It is all-or-nothing per
  account and evaluated whenever vocabulary is (re)loaded.
- **Rationale**: This is exactly the user's rule ("if a user uploads their
  own list, they will have the folder for their own, no need to use the
  shared folder"). Accounts with no uploads keep today's behaviour, and
  deleting the last list falls back to the shared folder.

## R3. Making a session pick up uploads without breaking it

- **Decision**: Add one small method, `PracticeSession.set_vocab_dir(path)`.
  It stores `self.vocab_dir = path`, and **only if** the session is not
  group-locked and `step in ("choose", "empty")` it reloads `all_items`
  (and sets `step` to `"choose"`/`"empty"`). `SessionRegistry` calls it:
  - when it creates a session, with the effective folder;
  - after every upload, replace, or delete for that account (new
    `SessionRegistry.refresh_vocab(account)`).

  Mid-session steps are untouched. The existing `restart()` and
  `end_session()` already reload from `self.vocab_dir`, so the change
  applies the next time the learner picks a word set (FR-009, US3
  scenario 4).
- **Rationale**: The learner sees a new list on the word-set screen right
  away (US1 scenario 1), and a session in progress keeps its loaded items.
  Grading, review and logging are unchanged (FR-013).
- **Alternatives considered**:
  - *Pass a callable instead of a path*: works, but changes the
    constructor's meaning for every existing caller. Rejected.
  - *Throw away the account's session on every upload*: would wipe an
    in-progress session on another device. Rejected (FR-009).

## R4. One list = one word set

- **Decision**: When saving, set every word's `group` to the list name,
  replacing any `group` value in an uploaded Markdown file.
- **Rationale**: The word-set screen groups by `group` (spec 007), so this
  gives FR-007 ("each uploaded list appears as its own word set") with no
  change to `_available_collections()`. A list replaced or deleted maps
  1:1 to the set that disappears or changes.
- **Trade-off**: uploading `T_words.md`, whose words say `group:
  t-words`, gives a set named `T_words`, not `t-words`. The upload result
  says which set the words went into.

## R5. Accepted upload formats (Q1 answer: both)

- **Decision**: The format is chosen by file extension.
  - `.md` / `.markdown` → the existing vocabulary Markdown format, parsed
    with the existing `parse_blocks` + `VocabularyItem.from_block`.
  - `.csv` / `.txt` / `.tsv` → the **simple list** (contract
    `upload-formats.md`): one word per line; fields separated by a tab, a
    comma `,` or a full-width comma `，`; field 1 is English, field 2 is
    Chinese, and any further fields are extra accepted answers. CSV quoting
    is honoured, so `"look up, search"` stays one field. Blank lines and
    lines starting with `#` are ignored. A first row whose first field is
    `english`, `word`, `英文` or `单词` (case-insensitive) is treated as a
    header and skipped.
  - Anything else → rejected as unsupported (FR-004).
- **Text decoding**: try `utf-8-sig` (handles Excel's BOM); if that fails,
  `gb18030` (covers Excel CSVs saved on Chinese Windows); otherwise reject
  with "save the file as UTF-8".
- **Rationale**: Extension-based detection is predictable and easy to
  explain on the upload screen. The full-width comma matters because a
  Chinese phone keyboard types `，` by default. Meanings that need
  separators use `；`, as the existing files already do.
- **Alternatives considered**: `csv.Sniffer` (unreliable on short files
  and mixed punctuation); `.xlsx` (needs a new dependency; Excel can save
  CSV). Both rejected.

## R6. Validation, limits and reporting

- **Decision**:
  - `MAX_CONTENT_LENGTH = 1 MiB` on the app. Flask's `413` gets a JSON
    error handler with `{"error": "The file is larger than 1 MB."}`.
  - More than 5,000 valid words → rejected as a whole.
  - Each skipped entry reports where it was and why, e.g. `line 12: no
    Chinese meaning` or `block 3: missing 'english'`.
  - At most the first 20 skip messages are returned, plus a
    `skipped_count` total.
  - Zero valid words → `422`, nothing saved.
  - English or Chinese text is trimmed; empty after trimming counts as
    missing.
  - Words are kept in file order, and duplicates are kept (matching
    today's behaviour across vocabulary files).
- **Rationale**: Covers FR-003, FR-004, FR-010 and SC-003, and keeps
  responses small for a phone.

## R7. List names and replacing

- **Decision**:
  - **Name**: the uploaded file's stem, with path parts dropped. Keep
    Unicode letters and digits, spaces, `-` and `_`; collapse whitespace;
    strip leading dots and spaces; at most 64 characters. If nothing is
    left → `My words`, then `My words 2`, and so on.
  - **Collisions**: names are compared case-insensitively, since macOS
    file systems are case-insensitive.
  - **Replacing**: an existing name without `replace=true` → `409`
    `{"exists": true, "name": ...}` and nothing changes. The front end
    asks "Replace your list X?" and posts again with `replace=true`.
  - **Writes**: write to a temporary file in the same folder, then
    `os.replace` it into place, so a reader never sees half a file.
  - **Locking**: one `threading.Lock` per account serialises that
    account's writes (the edge case of two simultaneous uploads).
  - **Upload date**: the file's modification time; no separate index.
- **Rationale**: Covers FR-005 and FR-008 with nothing beyond the files
  themselves.

## R8. API shape and access control

- **Decision**: These new endpoints exist only in accounts mode and are
  behind spec 015's login guard. Every one works only on
  `word-lists/<logged-in username>/`, and list names are always
  re-sanitised and resolved inside that folder (no path traversal).
  - `GET /api/word-lists`: lists the account's word lists and whether it
    uses its own lists or the shared folder.
  - `POST /api/word-lists`: multipart upload with fields `file` and
    optional `replace`.
  - `DELETE /api/word-lists/<name>`: deletes one list.

  `GET /api/state` gains `"word_source": "own" | "shared"`.
- **Rationale**: Covers FR-012 and Constitution III (each account reaches
  only its own data).

## R9. CLI and legacy mode

- **Decision**: The CLI and `create_app(accounts=None)` are unchanged and
  have no upload routes. `--word-lists-dir` is a web-only flag, and the
  start-up banner adds `Word lists: <dir>`.
