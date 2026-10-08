# Research: Remove Words I Don't Want to Recall

Phase 0 for [plan.md](plan.md). The spec's clarifications were settled on
2026-10-08: removal is permanent, with only an immediate undo, and there
is no list view.

## R1. Knowing which file a word came from

- **Decision**: `load_vocabulary()` stamps each `VocabularyItem` with
  `source: Path | None`, the file it was read from. The field has
  `compare=False` and `repr=False`, so equality and grading are
  unaffected. The entry in the file is then found by matching its
  `english` **and** `chinese` against the parsed blocks. The first match
  is removed.
- **Rationale**:
  - The session holds the items that were loaded. The file path tells us
    whether a word belongs to the learner's own list (own folder) or to
    the shared folder.
  - Matching on english plus chinese stays correct even after earlier
    blocks in the same file were removed, which a stored block index
    would not.
- **Alternatives considered**: a block index, which goes stale after any
  earlier removal; or a separate ID field in every block, which would
  change every file.

## R2. Deleting from the learner's own list file, exactly (FR-005, SC-003)

- **Decision**: `WordListStore.remove_word(account, path, english,
  chinese) -> RemovedEntry`. It runs under the existing per-account lock.
  1. Find the matching block's character span with the existing
     `_BLOCK_RE`. The span includes its `---` lines and the single blank
     separator line after it, or before it if it is the last block.
  2. Cut exactly that text. The rest of the file stays byte-identical.
  3. Write atomically, with a temp file and `os.replace`, as `save()`
     does.
  4. Return `RemovedEntry(path, offset, text, file_after)`.

  `WordListStore.restore_word(account, removed)` checks whether the file
  still equals `file_after`. If it does, it re-inserts `text` at
  `offset`, which gives back the original bytes exactly. If the file
  changed in between (for example another device removed a word), it
  inserts the block at the nearest block boundary at or before `offset`,
  so no entry is lost. The path must be inside the account's own folder;
  otherwise the call raises an error.
- **Rationale**: text-level cutting keeps every other entry exactly as
  it was. Re-rendering the whole file through YAML could reformat other
  blocks.
- **Alternatives considered**:
  - **Parse, drop and re-dump the file**: this reformats other blocks,
    breaking SC-003's byte-identical rule.
  - **Marking the entry `removed: true`**: that is reversible hiding,
    which the spec's Q1 ruled out for own lists.

## R3. Shared word sets: hidden per learner (FR-005, FR-007)

- **Decision**: the shared folder is never written. A removal there adds
  `{"group": …, "english": …, "chinese": …}` to
  `word-lists/<username>/.hidden-shared.json`. The file is JSON, written
  atomically, and is invisible to the `*.md` loaders, like spec 018's
  pending-import file.
  - Undo deletes the entry again.
  - When the session loads vocabulary from the shared folder, it filters
    out the learner's hidden entries.
- **Rationale**: this is the only way to "remove" a shared word for one
  learner without changing it for everyone. The file is account-scoped,
  so it survives restarts and works on every device.
- **Alternatives considered**: copying the shared words into the
  learner's own list and deleting from that copy. That would silently
  switch them off the shared sets (spec 016 FR-006), which is too
  surprising.

## R4. Loading with filters (FR-002)

- **Decision**: `PracticeSession` gains an optional `item_filter` (a
  callable that takes the loaded list of items and returns the list to
  practice).
  - All four places that call `load_vocabulary` (init, `restart`,
    `set_vocab_dir`, `end_session`) go through one `_load()` helper that
    applies it.
  - `SessionRegistry` passes a filter that drops the account's hidden
    shared words when the session reads the shared folder, and does
    nothing for own lists, which have no deleted words left in them.
- **Rationale**: word-set counts and "Practice everything" come from
  `all_items`, so filtering at load keeps FR-002 true everywhere with one
  change.

## R5. Removing the current word mid-session (FR-001, FR-003)

- **Decision**: `PracticeSession.remove_current(remove_fn) -> dict`. It
  is valid at `recall`, `reveal` and `sentence`; any other step raises
  `WrongStepError`.
  - **What happens to the word's attempt**:
    - at `recall`, nothing has been answered, so nothing is logged or
      tallied;
    - at `reveal` or `sentence`, the attempt already made is logged,
      exactly as `continue_to_next`/`skip_sentence` would log it, so
      history is kept (spec US1-AS3), and it is tallied as answered.
  - **The word itself**: it is dropped from `items` and `all_items`.
    `current_index` stays the same, so the next word moves into place.
    The step becomes `recall`, or `complete` if no words are left.
  - **Undo**: the session keeps `pending_undo = (item, index,
    removed_entry)`. Any other session action clears it: answer, skip,
    continue, select, restart, end, retry, or another removal.
  - **`undo_remove(restore_fn)`**:
    1. restores the file entry;
    2. re-inserts the item at its old index in `items`, and in
       `all_items`;
    3. makes it the current word again, at `recall`.
- **Rationale**: dropping the word from the in-memory list, rather than
  reloading, keeps the session's place. The undo window of "until the
  next action" matches FR-004.
- **Alternatives considered**: reloading the vocabulary after each
  removal. That loses the session's random order and position.

## R6. Web API and UI

- **API** (accounts mode with a word-list store; otherwise `404`):
  - `POST /api/remove-word` returns
    `{state, removed: {english, chinese}, undo: true}`.
  - `POST /api/undo-remove` returns `state`, or `409` if there is nothing
    to undo.
- **UI**:
  - A **Remove this word** ghost button sits next to "Show answer" on
    recall, and in the actions on reveal and sentence.
  - It asks `confirm("Remove “…” from your words? This can't be undone
    after you move on.")`. The English word is shown only once it has
    been revealed; during recall the dialog shows the meaning instead.
  - A toast with role `status` says "Removed “…”." and has an **Undo**
    button. It disappears on the next action or after 15 seconds.
- **Rationale**: these reuse the patterns of the skip and end-session
  actions. The confirm text tells the learner about the undo window
  before they act.

## R7. Concurrency and isolation

- Every file edit runs under `WordListStore`'s per-account lock, and
  every hidden-file edit under the same lock. A session belongs to one
  account (spec 015), so a learner's devices share one session. A removal
  on one device is therefore seen on the other at its next refresh, and
  never breaks it.
- One account never touches another account's folder. Paths are checked
  to be inside `word-lists/<username>/`.
