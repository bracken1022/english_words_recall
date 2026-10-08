---

description: "Task list for 020-delete-vocabulary"
---

# Tasks: Remove Words I Don't Want to Recall

**Input**: design documents from `/specs/020-delete-vocabulary/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ and quickstart.md

**Tests**: included and REQUIRED, because Constitution Principle I
(Test-First) applies. Each test is written first and seen failing.
Existing tests are only appended to.

**Organization**:

- **US1 (P1)**: remove a word while practicing it.
- **US2 (P2)**: undo the removal straight away.

The spec's US3 (a list view) is out of scope (FR-006).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel.
- **[Story]**: US1 or US2.

## Path Conventions

This is a single project.

- **Changed**:
  - `src/models/vocabulary_item.py`
  - `src/services/vocabulary_loader.py`
  - `src/services/word_lists.py`
  - `src/web/session_state.py`
  - `src/web/session_registry.py`
  - `src/web/app.py`
  - `src/web/templates/index.html`
  - `src/web/static/app.js`
  - `src/web/static/style.css`
  - `README.md`
- **Not touched**: `src/cli/*`, `src/services/matcher.py`,
  `src/services/progress_log.py`, and the shared `vocabulary/` folder.

---

## Phase 1: Setup

No setup is needed: there are no new dependencies or folders.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the file-level remove and restore operations and the
`source` stamp. Both stories need them.

### Tests (write first, confirm they FAIL)

- [X] T001 [P] Append to `tests/contract/test_vocabulary_markdown_contract.py`:
  - every item from `load_vocabulary(dir)` has `source` equal to its
    file's `Path`;
  - two items that differ only in `source` compare equal, and `repr`
    doesn't show `source`.
- [X] T002 [P] Create `tests/unit/test_word_list_remove.py`, covering
  `WordListStore.remove_word` and `restore_word` and the hidden-shared
  helpers. It uses a `tmp_path` store, the account `lily`, and a 3-block
  list file written with `_to_markdown`.
  - **Cutting**:
    - `remove_word(lily, path, "rent", "租金；出租")` returns a
      `RemovedEntry`;
    - the file no longer contains the block, and loads with 2 items and
      0 warnings;
    - `before.replace(removed.text, "", 1) == after`, so every other
      byte is unchanged.
  - **First, middle and last block**: each can be removed. No blank
    lines pile up, and no `---` is left orphaned.
  - **Exact restore**: `restore_word(lily, removed)` makes the file
    byte-identical to before (compare sha256).
  - **Restore after the file changed**: remove word A, then remove word
    B, then restore A. The file still loads with A present and B absent,
    and nothing else is lost.
  - **Duplicates**: with two identical blocks, only the first is
    removed.
  - **Not found**: a word that isn't in the file raises `KeyError`, and
    the file is unchanged.
  - **Path checks**: a path outside `word-lists/lily/`, for example the
    shared folder or another account's folder, raises `ValueError` for
    both remove and restore, and the file is unchanged.
  - **Hidden shared words**:
    - `hide_shared(lily, group, english, chinese)`, then
      `hidden_shared(lily)` gives a `set` of `(group, english, chinese)`
      tuples;
    - `unhide_shared` removes the entry again;
    - the file `word-lists/lily/.hidden-shared.json` has
      `"version": 1`;
    - `WordListStore.list(lily) == []` and
      `word_source(lily) == "shared"` while only that file exists;
    - another account's `hidden_shared` is empty.

### Implementation

- [X] T003 In `src/models/vocabulary_item.py`, add
  `source: Path | None = field(default=None, compare=False, repr=False)`.
  In `src/services/vocabulary_loader.py`, set `item.source = md_file`
  for each loaded item. Makes T001 pass.
- [X] T004 In `src/services/word_lists.py`, add the file and hidden-word
  operations from research R2 and R3 and data-model.md. Makes T002 pass.
  - **`RemovedEntry`**: a dataclass with `path`, `offset`, `text` and
    `file_after`.
  - **`_own_path(account, path)`**: resolves the path and raises
    `ValueError` unless it is inside `self.folder(account)`.
  - **`remove_word(account, path, english, chinese)`**:
    1. Runs under `self._lock(account)`.
    2. Uses `_BLOCK_RE.finditer`, parsing each match with
       `parse_blocks`, to find the first block whose `english` and
       `chinese` match after `str().strip()`.
    3. The cut span is the match plus one following `\n` separator. For
       the last block, it is the preceding `\n` instead.
    4. Writes atomically, with a temp file and `os.replace`.
    5. Returns the `RemovedEntry`, or raises `KeyError` if no block
       matches.
  - **`restore_word(account, removed)`**:
    - If the file still equals `removed.file_after`, writes
      `file_after[:offset] + text + file_after[offset:]`.
    - Otherwise, inserts `text` at the start of the first block that
      begins at or after `offset`, or appends it with a separating
      `\n`.
    - Writes atomically.
  - **Hidden shared words**: `hidden_shared`, `hide_shared` and
    `unhide_shared` work on `self.folder(account) /
    ".hidden-shared.json"` (`{"version": 1, "hidden": [{"group",
    "english", "chinese"}]}`). Writes are atomic and use
    `ensure_ascii=False`. An unreadable file reads as empty.

**Checkpoint**: file operations are exact and isolated, and the full
suite is green.

---

## Phase 3: User Story 1 - Remove a word while practicing it (Priority: P1) 🎯 MVP

**Goal**: "Remove this word" on recall, reveal and sentence moves the
session on, and the word is gone from later sessions. Words from the
learner's own lists are deleted from the file; shared words are hidden
for that learner only.

**Independent Test**:
1. Log in, select a list, and call `POST /api/remove-word` at recall.
2. The state shows the next word, and the file no longer has the entry.
3. `/api/select` again: the word-set count is one less and the word
   never appears.

### Tests (write first, confirm they FAIL)

- [X] T005 [P] [US1] Create `tests/unit/test_session_remove.py`, testing
  `PracticeSession.remove_current(remove_fn)` with a fake `remove_fn`
  that records its calls and returns a token.
  - **Recall**: the word is dropped from `items` and `all_items`, and
    `current_index` is unchanged, so the next word is current. Nothing
    is appended to the progress file, and `correct_count` is unchanged.
  - **Reveal** (recall-only, wrong answer): the held attempt is appended
    to the progress file, and then the word is dropped.
  - **Sentence step**: the attempt is appended, as with a skip, and
    counted if it was correct.
  - **Last word**: the step becomes `complete`.
  - **Other steps**: `choose`, `feedback`, `complete` and `empty` raise
    `WrongStepError`, and `remove_fn` is not called.
  - **Failure**: if `remove_fn` raises `OSError`, the session is
    unchanged and the error propagates.
  - **Filtering**: `PracticeSession(..., item_filter=f)` applies `f` on
    init, on `restart()`, on `set_vocab_dir()` and on `end_session()`.
    Use a filter that drops `english == "rent"`.
- [X] T006 [P] [US1] Create `tests/contract/test_remove_word_api.py`,
  following `contracts/remove-word-api.md`. Use the accounts and store
  app pattern from `tests/contract/test_word_lists_api_contract.py`.
  - **Own list**:
    1. Upload `unit1` with 3 words (legacy route), select `unit1` with
       recall-only, then `POST /api/remove-word`.
    2. Expect `200` with `removed.english` equal to the first word,
       `undo: true`, and the state at recall on the second word.
    3. `unit1.md` lacks the entry, `GET /api/word-lists` shows
       `word_count == 2`, and after `POST /api/end` the choose state's
       `unit1` count is 2.
  - **Shared word**:
    1. As an account with no lists, select `shared-set` and remove
       `river`.
    2. The shared file is byte-identical.
    3. A new session for this account never offers `river` (its count
       is 0).
    4. Another account still sees `river`.
  - **Wrong step**: `409` when called at `choose`.
  - **No store**: `404` without a word-list store, and in no-accounts
    mode.
  - **Login**: `401` without a login.
  - **File error**: monkeypatch `os.replace` in `src.services.word_lists`
    to raise. The response is `500` with the contract message, and both
    the session state and the file are unchanged.
- [X] T007 [P] [US1] Append to `tests/unit/test_web_static_assets.py`:
  - **Template**: `index.html` has `id="remove-word-button"` inside
    `#recall-hints`, and a `#remove-toast` with `role="status"` that is
    hidden.
  - **`app.js`**:
    - posts to `/api/remove-word`;
    - contains the confirm texts `from your words? You can undo this
      only until you move on.` and `Removed “`;
    - doesn't use `innerHTML` in the remove section, which is delimited
      by `// --- remove word (spec 020)`.

### Implementation

- [X] T008 [US1] In `src/web/session_state.py`, add the session behaviour
  from research R4 and R5. Makes T005 pass.
  - **Constructor**: takes `item_filter=None`.
  - **`_load(vocab_dir)`**: wraps `load_vocabulary` and applies the
    filter. Use it in all four places that load vocabulary.
  - **`remove_current(remove_fn)`**:
    1. Validates the step.
    2. Calls `token = remove_fn(item)` first, so an exception leaves the
       session untouched.
    3. Logs the held attempt at reveal or sentence (tallying it if it
       was correct), as continue and skip do.
    4. Pops the item from `items` and from `all_items`.
    5. Sets `step = "complete"` if `current_index >= len(items)`,
       otherwise `"recall"`.
    6. Stores `self.pending_undo = {item, index, all_index, token}` and
       returns `{"english": item.english, "chinese": item.chinese}`.
  - **Clearing `pending_undo`**: every other public action sets it to
    `None` at its start: `submit_answer`, `submit_sentence`,
    `select_collection`, `skip_sentence`, `continue_to_next`, `restart`,
    `end_session` and `retry_sentence`.
- [X] T009 [US1] In `src/web/session_registry.py`, `_new_session` passes
  `item_filter`.
  - When the account's vocab dir is the shared folder and a store
    exists, the filter drops items whose `(group, english, chinese)` is
    in `store.hidden_shared(account)`. Otherwise there is no filter.
  - `refresh_vocab` keeps working, because the filter is read at each
    load.
- [X] T010 [US1] In `src/web/app.py`, inside the accounts-and-store
  block, add `POST /api/remove-word`, following the API contract.
  - **`remove_fn(item)`**:
    - if `item.source` is inside `store.folder(account)`, it calls
      `store.remove_word(account, item.source, item.english,
      item.chinese)` and returns `("own", entry)`;
    - otherwise it calls `store.hide_shared(account, item.group,
      item.english, item.chinese)` and returns `("shared", key)`.
  - **Status codes**:
    - a `KeyError` (the word is gone already) is caught inside
      `remove_fn`, which returns `None`, so the word is removed from the
      session with `undo: false`;
    - an `OSError` gives `500`;
    - a `WrongStepError` gives `409`.

  Makes T006 pass.
- [X] T011 [US1] In `src/web/templates/index.html`, add
  `<button id="remove-word-button" type="button" class="btn btn-ghost">Remove
  this word</button>` after `#show-answer-button` in `#recall-hints`. In
  `app.js`, the same button is moved into the step actions on reveal
  and sentence.

  Add `<div id="remove-toast" class="remove-toast" role="status"
  hidden><span id="remove-toast-text"></span> <button id="undo-remove-button"
  type="button" class="btn btn-ghost">Undo</button></div>` after
  `#word-feedback`.
- [X] T012 [US1] In `src/web/static/app.js`, add a section
  `// --- remove word (spec 020)`. Makes T007 pass.
  - **`removeWord()`**:
    1. Builds the confirm text from the contract (the meaning at recall,
       the English word otherwise).
    2. Posts to `/api/remove-word`.
    3. On `200`, calls `renderState(data.state)`, then `showRemoveToast(…)`.
    4. On an error, shows the message as `submitAnswer` does.
  - **Visibility**: the button shows only when `state.word_source !==
    undefined` and the step is recall, reveal or sentence.
  - **Placement**: the button is moved into `#step-actions` on reveal,
    and next to Skip on sentence.
  - **Toast**: it hides after 15 s, and on any other action, through a
    `hideRemoveToast()` called at the start of `submitAnswer`, the
    sentence submit, skip, continue and select.
- [X] T013 [P] [US1] In `src/web/static/style.css`, add `.remove-toast`.
  It is a flex row with gap `var(--space-2)`, a surface background,
  `padding: var(--space-2) var(--space-3)`, a 1 px divider border and
  `margin-top: var(--space-3)`. Use existing tokens only.

**Checkpoint**: removal works end to end. This is the MVP.

---

## Phase 4: User Story 2 - Undo a removal straight away (Priority: P2)

**Goal**: "Undo" puts the word back exactly, as the current word, until
the learner's next action.

**Independent Test**: remove, then undo. The file sha256 equals its
value before the removal, the state is at recall on the same word, and
a second undo gives `409`.

### Tests (write first, confirm they FAIL)

- [X] T014 [P] [US2] Append to `tests/unit/test_session_remove.py`:
  - `undo_remove(restore_fn)` calls `restore_fn(token)`, re-inserts the
    item at its old index in `items` and `all_items`, sets
    `step = "recall"`, and clears `pending_undo`;
  - it works after the last word made the session `complete`;
  - `undo_remove` with nothing pending raises `WrongStepError`;
  - after `remove_current`, then `submit_answer` on the next word, then
    `undo_remove`, it raises `WrongStepError` (the window has closed);
  - if `restore_fn` raises `OSError`, the session is unchanged.
- [X] T015 [P] [US2] Append to `tests/contract/test_remove_word_api.py`:
  - **Own list**: remove, then `POST /api/undo-remove`. Expect `200`,
    state at recall on the removed word, and the `unit1.md` sha256 equal
    to its value before. A second undo gives `409 {"error": "Nothing to
    undo."}`.
  - **Shared word**: remove, then undo. The word is offered again in a
    new session, and `.hidden-shared.json` no longer lists it.
  - **Window closed**: remove, then answer the next word, then undo gives
    `409`.
- [X] T016 [P] [US2] Append to `tests/unit/test_web_static_assets.py`:
  `app.js` posts to `/api/undo-remove`, and `#undo-remove-button` exists.

### Implementation

- [X] T017 [US2] In `src/web/session_state.py`, add
  `undo_remove(restore_fn)`, following research R5. Makes T014 pass.
- [X] T018 [US2] In `src/web/app.py`, add `POST /api/undo-remove`.
  - **`restore_fn(token)`**: `("own", entry)` calls
    `store.restore_word`, `("shared", key)` calls `store.unhide_shared`,
    and `None` does nothing.
  - **Status codes**: a `WrongStepError` gives `409 {"error": "Nothing
    to undo."}`.

  Makes T015 pass.
- [X] T019 [US2] In `src/web/static/app.js`, the Undo button posts to
  `/api/undo-remove`, renders the returned state, and hides the toast.
  Makes T016 pass.

**Checkpoint**: both stories are complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T020 [P] In `README.md`, under "Your own word lists (web UI)", add
  a short "Removing words" paragraph:
  - the button;
  - the permanent deletion from your own list file;
  - the immediate Undo;
  - shared words being hidden only for you;
  - your history being kept.
- [X] T021 Run `ruff check src tests` and the full `pytest`. Confirm with
  `git diff -U0 -- tests/` that pre-existing tests only gained lines.
- [X] T022 Visual check with the `frontend-design` recipe. Take 1280 px
  and 390 px screenshots of recall with the Remove button, of the toast
  with Undo after a removal, and of the sentence step with the button.
  Fix anything wrong.
- [X] T023 Run the quickstart §2 scenarios a–g, against a temporary
  copy of data and never against the real learner files, and record the
  results in `specs/020-delete-vocabulary/quickstart.md`.

---

## Dependencies & Execution Order

- **Foundational (T001–T004)**: blocks both stories. T003 and T004 can be
  done independently after their tests.
- **US1 (T005–T013)**: depends on Foundational.
- **US2 (T014–T019)**: depends on US1's `pending_undo` (T008), its routes
  (T010) and its toast (T012).
- **Polish (T020–T023)**: comes after both stories.

```text
Foundational ──► US1 (MVP) ──► US2
```

## Parallel Examples

```bash
T001 vocabulary contract test | T002 test_word_list_remove.py
T005 test_session_remove.py | T006 test_remove_word_api.py | T007 static assets
T014 | T015 | T016   (US2 tests)
```

## Implementation Strategy

1. Do Foundational, then US1. That makes removal usable, though a
   mistake can't be undone, so don't ship it alone.
2. Add US2 (undo), which completes the spec.
3. Polish, then commit to `main` when asked.

## Notes

- Never write to the shared `vocabulary/` folder.
- Manual checks use temporary copies of learner data, never the real
  `word-lists/`.
