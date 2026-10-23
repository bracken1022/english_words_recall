---

description: "Task list for 023-word-corrections"
---

# Tasks: Automatic Word Corrections

**Input**: design documents from `/specs/023-word-corrections/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/ and quickstart.md

**Tests**: included and REQUIRED, under Constitution Principle I. Every
implementation task is preceded by tests that are written first and seen
failing. Qwen is always faked: inject a fake `check` callable into the
service, or patch `src.services.qwen_client.requests.post`. The autouse
fixture in `tests/conftest.py` already clears the Qwen environment
variables.

**Organization**:

- **US1 (P1)**: words correct themselves while practising, plus a
  corrections list. Covers own lists.
- **US2 (P2)**: undo a correction.
- **US3 (P3)**: correct the shared sets through the
  `vocabulary/.corrections.json` overlay, for everyone.

**Data rules for every task**: never write the shared `vocabulary/*.md`
files; manual checks use temp copies only, never the real `vocabulary/`,
`word-lists/` or `progress.md`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 [P] Create `tests/fixtures/word_check_cases.yml`, a reviewed
  fixture for `eval_corrections` (research R10). Add a header comment
  citing spec 023 R10. Each entry has `english`, `dialect` (`british` or
  `american`), `sent` (`ipa`, `chinese`, `pos`, the values to send) and
  `accepted` (the right values: `ipa` as a list of acceptable forms,
  `chinese_any` as a list of key meanings of which at least one must
  appear, and `pos` as a list of labels).
  - **50 `known_error` cases**: about 17 each of a wrong meaning, a wrong
    part of speech (such as a noun labelled `v.`) and a wrong IPA
    (including American IPA sent with `dialect: british`, and a wrong
    stress).
  - **50 `correct` cases**: already right, taken from the shared sets
    and from `tests/fixtures/enrichment_eval.yml`, with at least 5
    heteronyms (record, present, object, …) and 5 phrases.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the pieces every story needs: the dialect in the word
check, a word's file meaning (`origin_chinese`) and the keys that use it,
fingerprints, and the corrections file.

### Tests (write first, confirm they FAIL)

- [X] T002 [P] Append to `tests/unit/test_word_check.py`
  (`contracts/word-check-task.md`, research R3):
  - `user_text(english, ipa, chinese, pos, dialect)` has exactly five
    lines in this order: `English:`, `Dialect: British` or
    `Dialect: American`, `Current IPA:`, `Current Chinese:`,
    `Current parts of speech:`. Nothing else is sent (FR-013).
  - `system_prompt("british")` asks for British (RP) IPA in the Oxford
    Learner's Dictionaries style; `system_prompt("american")` asks for
    General American IPA. Any other dialect raises `ValueError`.
  - `validate(data, dialect)` rejects the whole answer when the IPA
    fails the dialect's check (`check_british_ipa` or
    `check_american_ipa` returns problems). For example, `ˈteɪlɚ` is
    rejected for British and `ˈteɪlə` for American.
  - `check_word(config, english, ipa, chinese, pos, dialect)` sends the
    dialect line, through a patched `requests.post`.
  - For a heteronym (`is_heteronym`, such as "record"), `check_word`
    returns the **current** IPA whatever Qwen answers, still validates
    and returns the meaning and part of speech, and doesn't reject the
    answer for a wrong-dialect IPA.
  - The existing rules still hold: exactly the keys `ipa`, `chinese` and
    `pos`; `chinese` is "non-empty after trimming, ≤ 60 characters,
    passes the family-safe filter"; `pos` is a "non-empty list;
    `normalize_pos` maps every item to a label".
- [X] T003 [P] Create `tests/unit/test_corrections_file.py` for
  `src/services/corrections_file.py` (`contracts/corrections-file.md`,
  data-model.md), using temp dirs:
  - **`fingerprint(file_name, group, english, values)`** is the hex
    `sha256("file|group|english|ipa|chinese|pos")`. It is stable,
    uses the file name only (not its path), and changes when any of the
    six parts changes. It treats values that differ only in slashes
    around the IPA, spaces around the meaning, or part-of-speech
    spelling (`noun` vs `n.`) as the same.
  - **`WordValues(ipa, chinese, pos)`** with `normalized()` and
    equality after normalising: "IPA without slashes, parts of speech
    as labels, meaning trimmed".
  - **Reading** a missing file, invalid JSON, `"version": 2`, or wrong
    types (overlay not an object, checked not a list, a record missing
    a field) gives an empty overlay, an empty checked set and no
    records for that part only. It never raises.
  - **Writing** round-trips `{"version": 1, "overlay", "checked",
    "records"}` with `ensure_ascii=False`. It writes atomically (a temp
    file in the same folder, then `os.replace`), so a failed write
    leaves the old file intact.
  - **Limits**: `checked` is "at most 20,000; oldest dropped first";
    `records` are "newest first, at most 500".
  - **`overlay_key(file, group, english, origin_chinese)`** is
    `"<file>|<group>|<english>|<origin_chinese>"`, with an empty string
    for no group.
  - **`CorrectionRecord`** fields: `id` ("Random, unique within the
    folder's file (12 hex chars)"), `batch`, `file`, `group`,
    `english`, `origin_chinese`, `field` (`"ipa" | "chinese" | "pos"`),
    `old`, `new` (`str | list[str] | null`), `at` ("ISO 8601 UTC,
    seconds") and `undone_at` ("ISO 8601 | null"). Round-trips through
    JSON.
  - `update(folder, fn)` reads, applies `fn`, and writes under a
    per-file lock, so two threads appending records both land.
- [X] T004 [P] Create `tests/unit/test_vocabulary_overlay.py` (research
  R4), using temp copies of a small shared folder:
  - `load_vocabulary` sets `origin_chinese` to the file's meaning on
    every item, and it isn't part of equality (`compare=False`).
  - With `vocabulary/.corrections.json` holding an overlay entry for a
    word, `load_vocabulary(folder)` gives that word the overlay's `ipa`,
    `chinese` and `pos`, while `origin_chinese` stays the file's
    meaning. `english`, `alternates`, `group`, `example` and
    `example_zh` are unchanged (FR-002).
  - An overlay key that matches no word (the word was removed or edited
    in the file) is ignored, and an unreadable `.corrections.json`
    loads the words unchanged with no failure.
  - The `.md` files are byte-for-byte unchanged after loading.
  - **Hidden words**: a shared word hidden by spec 020 with the file's
    meaning stays hidden after its meaning is corrected by the overlay
    (`SessionRegistry._item_filter` uses `origin_chinese`), and
    `hide_shared` from the remove route stores the file meaning.
  - **Examples**: a shared word's `.examples.json` entry, keyed by the
    file meaning, is still found after its meaning is corrected
    (`examples._json_key` uses `origin_chinese`).

### Implementation

- [X] T005 [P] In `src/services/word_check.py`:
  - add `DIALECTS = ("british", "american")`;
  - replace `SYSTEM_PROMPT` with `system_prompt(dialect)`, where only the
    `"ipa"` line differs: British (RP) IPA in the Oxford Learner's
    Dictionaries style, or General American IPA;
  - add a `Dialect:` line to `user_text`;
  - give `validate` a dialect argument (use `functools.partial` when
    passing it to `complete_json`) and run the dialect's IPA check;
  - make `check_word(config, english, ipa, chinese, pos, dialect)` keep
    the current IPA for a heteronym: validate the IPA leniently (any
    normalisable value) and return `ipa` unchanged;
  - update the module docstring, which still says "American IPA".

  Makes T002 pass.
- [X] T006 [P] Create `src/services/corrections_file.py` with
  `WordValues`, `fingerprint`, `overlay_key`, `CorrectionRecord`,
  `CorrectionsData` (overlay, checked as an ordered list, records),
  `read(folder)`, `write(folder, data)`, and `update(folder, fn)` with a
  module-level per-path lock. It also has the constants `FILE_NAME =
  ".corrections.json"`, `MAX_CHECKED = 20_000` and `MAX_RECORDS = 500`.
  Makes T003 pass.
- [X] T007 Add `origin_chinese` to the model and use it for every
  shared-word key (research R4):
  - **`src/models/vocabulary_item.py`**: add `origin_chinese: str |
    None = field(default=None, compare=False, repr=False)`, which
    defaults to `chinese` in `__post_init__`.
  - **`src/services/vocabulary_loader.py`**: set `origin_chinese` from
    the block, then apply the folder's overlay through
    `corrections_file.read(vocab_dir).overlay`, keyed by `overlay_key`.
  - **`src/services/examples.py`**: `_json_key` uses
    `item.origin_chinese`, and `_save` passes `item.origin_chinese` to
    `set_example`.
  - **`src/web/session_registry.py`**: `keep_visible` compares
    `(i.group, i.english, i.origin_chinese)`.
  - **`src/web/app.py`**: the remove route passes `item.origin_chinese`
    to `remove_word` and `hide_shared`.

  Depends on T006; makes T004 pass. The full suite stays green.

**Checkpoint**: checks know the dialect, shared words keep their
identity when their meaning changes, and the corrections file can be
read and written. The suite is green.

---

## Phase 3: User Story 1 - Words correct themselves as I practise (Priority: P1) 🎯 MVP

**Goal**: with a key set, the first time an own-list word comes up it is
checked in the background; corrected values are written into the list
file and recorded, shown at reveal with an "Updated" note, and listed on
a Corrections page. Practice never waits. Shared-set words are not
checked yet: the service skips any item that isn't in the account's own
lists until US3.

**Independent Test**: on a temp copy of an own list with a word whose
meaning, IPA and part of speech are wrong, and with a fake checker,
practise the word: the list file has the corrected `ipa`, `chinese` and
`pos` with the same English, alternates and example lines; reveal shows
them with `corrected`; `GET /api/corrections` lists three records; the
same word practised again (and after a new app) makes no more checks.

### Tests (write first, confirm they FAIL)

- [X] T008 [P] [US1] Create `tests/unit/test_corrections.py` for
  `CorrectionService` (`src/services/corrections.py`), using temp
  folders, a real `WordListStore` and a fake `check(english, ipa,
  chinese, pos, dialect)` that records its calls. Threads are joined
  with `service.wait_all()`.
  - **prepare**:
    - returns at once, even while the fake check blocks on an event;
    - a word is checked once;
    - two `prepare` calls for the same word at the same time make one
      call;
    - at most 2 checks run at once (a fourth `prepare` while 2 are
      blocked doesn't start a third call until one finishes).
  - **Own-list save**: an answer that differs is written into the block
    by `WordListStore.set_values`, which changes only `ipa`, `chinese`
    and `pos`. Every other byte of the file is unchanged (English,
    alternates, `example` and `example_zh` lines, the other blocks), and
    the file loads with 0 warnings.
  - **Records**: one per changed field in
    `word-lists/<account>/.corrections.json`, with the same `batch` and
    with `old` and `new` normalised. An answer equal to the current
    values (after normalising) writes nothing to the list and records
    nothing, but marks the fingerprint checked.
  - **Live item**: the session's item gets the new `ipa`, `chinese`,
    `pos` and `origin_chinese` in place, and `corrected_fields(item)`
    returns the changed fields.
  - **Checked**: the fingerprint of the values the word now has is
    stored, so a new service instance on the same folder doesn't send
    the word again (SC-005). Editing the word in the file makes it
    checked again.
  - **Compare-and-set (R7)**: if the block was edited or removed while
    the check ran, nothing is written and nothing is recorded.
  - **Dialect (R3, per file)**: every word in an own-list file where any
    word's IPA passes the British check and fails the American one
    (e.g. `hɒt`) is checked with `"british"`, including a word like
    `ˈteɪlə` that passes both; a file with no such word is checked with
    `"american"`.
  - **Failures (R8)**, with the fake raising `QwenError`:
    - `bad_reply` or `bad_status` leaves the word unchanged and
      unchecked, so the next `prepare` sends it again, and there is no
      pause;
    - `timeout`, `unavailable` or `rate_limited` pauses checks for 5
      minutes (an injected clock), so `prepare` sends nothing, and
      `paused()` returns `{"reason": <QwenError message>, "until":
      <ISO>}`; after 5 minutes checks resume;
    - `auth` pauses until restart (`"until": None`);
    - a non-`QwenError` exception is treated like `bad_reply` and never
      escapes the thread.
  - **Shared items are skipped in US1**: an item whose source isn't in
    the account's own folder isn't sent.
  - `bind(account)` returns a view with `prepare`, `corrected_fields`,
    `list` and `paused`.
- [X] T009 [P] [US1] Append to `tests/unit/test_word_list_store.py`:
  `set_values(account, path, english, old: WordValues, new: WordValues)`
  under the account lock:
  - it finds the block by English **and** the values sent, and returns
    False without writing when there's no match;
  - otherwise it replaces only the `ipa`, `chinese` and `pos` lines,
    keeping key order and every other line;
  - rendering is YAML-safe (`yaml.safe_dump` per line, as
    `set_example` does);
  - a path outside the account's folder raises, as `_own_path` does.
- [X] T010 [P] [US1] Create `tests/contract/test_corrections_api.py`
  following `contracts/corrections-api.md`, with `create_app(...,
  accounts=..., word_lists_dir=...)` and a fake checker injected via
  `create_app(..., correction_check=fake)`:
  - **State**: at `reveal`, `GET /api/state` has `corrected` (a list,
    empty when nothing changed) and the corrected `ipa`, `chinese` and
    `pos` once `app.correction_service.wait_all()` returns. `recall`
    has no `corrected`.
  - **List**: `GET /api/corrections` returns `{"enabled": true,
    "paused": null, "corrections": [...]}`, newest first and at most
    200. Each entry has `id`, `scope` (`"own"`), `english`, `list` (the
    file name only), `field`, `old`, `new`, `at`, `undone` and
    `can_undo`.
  - **Paused**: after a fake `QwenError("unavailable")`, `paused` is
    `{"reason": "Qwen could not be reached.", "until": <ISO>}`.
  - **No key**: `QwenConfig.from_env()` gives None (the conftest
    default), `app.correction_service` is None, `GET /api/corrections`
    gives `enabled: false` with an empty list, and practice works
    unchanged.
  - **Logged out**: `401 {"error": "login required"}`.
  - **No leaks (FR-015)**: no route response or log line contains the
    key, the system prompt or the fake's raw output (`caplog`).
- [X] T011 [P] [US1] Create
  `tests/integration/test_word_corrections_flow.py` for the own-list
  flow, with the fake checker:
  1. log in, select an own list, and answer the broken word;
  2. reveal shows the corrected values and `corrected`;
  3. the list file is corrected, with English, alternates and example
     unchanged (SC-007);
  4. a fresh `create_app` on the same folders practising the word again
     makes 0 calls (SC-005);
  5. answering immediately while the fake blocks still reaches reveal
     (with the old values) without waiting, and the next load shows the
     corrected values.
- [X] T012 [P] [US1] Append to `tests/unit/test_web_static_assets.py`, as
  new functions:
  - `index.html` has `id="corrections-view"`, `id="corrections-list"`
    and a nav link or button to open it;
  - `app.js` contains `/api/corrections`, `Updated`, `Qwen is not set
    up` and `No corrections yet.`;
  - `app.js` renders `corrected` next to the IPA, meaning and part of
    speech at reveal.

### Implementation

- [X] T013 [US1] In `src/services/word_lists.py`, add `set_values`
  (T009), reusing `_find_block`'s block matching (extended to compare
  the sent values) and `_updated_block`'s per-key replacement for
  `ipa`, `chinese` and `pos`. Makes T009 pass.
- [X] T014 [US1] Create `src/services/corrections.py` with
  `CorrectionService(store, config, check=None, clock=time.monotonic,
  now=<UTC now>)`:
  - `check` defaults to `functools.partial(word_check.check_word,
    config)`;
  - `prepare(account, item)` (a daemon thread, deduplicated per key
    `file|group|english|origin_chinese`, a `threading.Semaphore(2)`);
  - `_dialect(item, shared)` (R3), `_values(item)`,
    `_save_own(...)` (via `set_values` and `corrections_file.update`),
    pause handling (R8), `corrected_fields(item)`, `list(account)`,
    `paused()`, `wait_all(timeout)`, and `BoundCorrections`;
  - logging records only the English word, the outcome and the
    QwenError code: never values, prompts or replies.

  Depends on T005, T006, T007 and T013; makes T008 pass.
- [X] T015 [US1] Wire up the server:
  - **`src/web/session_state.py`**: add `correction_service=None`, and
    call `correction_service.prepare(self.current_item)` in
    `_word_started` in **every** mode, including recall-only (R1). In
    `state()` at `reveal` and `sentence-recall`, add `corrected`. The
    item's fields are read at each call, so a finished correction
    shows.
  - **`src/web/session_registry.py`**: accept `correction_service` and
    pass `.bind(account)` to each session.
  - **`src/web/app.py`**:
    - add `create_app(..., correction_check=None)`, which builds
      `app.correction_service = CorrectionService(store, config,
      check=correction_check)` only when `QwenConfig.from_env()` returns
      a config or `correction_check` is given (tests); otherwise None;
    - pass it to the registry and the single session;
    - add `GET /api/corrections`, which returns `enabled`, `paused` and
      `corrections` as in the contract.
  - **`src/web/__main__.py`**: print `Corrections: on (<model>)` or
    `Corrections: off (set DASHSCOPE_API_KEY)` at startup (R9).

  Makes T010 and T011 pass.
- [X] T016 [US1] Update the web UI:
  - **`src/web/templates/index.html`**: a `#corrections-view` section
    with a status line (`#corrections-status`), `#corrections-list`, and
    a link to open it from the practice and choose screens.
  - **`src/web/static/app.js`**:
    - `loadCorrections()` renders each entry as word, field, old → new
      and time, newest first; `pos` lists are joined with spaces and
      `null` shows as "—";
    - the status shows "Qwen is not set up" when `enabled` is false and
      the pause reason when `paused`, otherwise nothing;
    - with no entries it shows "No corrections yet.";
    - at reveal, it adds a small "Updated" note by each field in
      `corrected`.
  - **`src/web/static/style.css`**: `.corrections-list` and
    `.updated-note` styles that follow the existing tokens and work at
    390 px.

  Makes T012 pass.

**Checkpoint**: own-list words correct themselves while practising and
the corrections are listed. This is the MVP.

---

## Phase 4: User Story 2 - Undo a correction (Priority: P2)

**Goal**: each correction in the list has Undo. It restores the old
values of every field changed by that check, and the change never comes
back.

**Independent Test**: let the fake checker change an own-list word, then
`POST /api/corrections/undo` with one record's id. The file has the old
values, every record of that batch is `undone`, and practising the word
again makes no call and leaves the values alone (SC-004).

### Tests (write first, confirm they FAIL)

- [X] T017 [P] [US2] Append to `tests/unit/test_corrections.py`:
  - `undo(account, id)` restores the `old` value of every record in the
    id's batch through `set_values` (compare-and-set against the `new`
    values) and sets `undone_at` on each;
  - it stores the restored values' fingerprint as checked, so the next
    `prepare` sends nothing and the change can't come back (FR-005);
  - the live session item is updated in place;
  - an unknown id raises `CorrectionNotFound`;
  - an already-undone batch raises `AlreadyUndone`;
  - a word edited or removed since raises `WordChanged`, with nothing
    written;
  - `list(account)` reports `undone` and `can_undo` (false once undone,
    or when the word's current values no longer equal the `new` values).
- [X] T018 [P] [US2] Append to `tests/contract/test_corrections_api.py`,
  `POST /api/corrections/undo` per the contract table:
  - `200 {"undone": ["chinese", "pos"]}`;
  - `404 {"error": "That correction wasn't found."}`;
  - `409 {"error": "That correction was already undone."}`;
  - `409 {"error": "That word has changed since, so it can't be
    undone."}`;
  - `400 {"error": "id is required"}` for a body that isn't
    `{"id": <string>}`;
  - after an undo of the current word, `GET /api/state` shows the old
    values;
  - undo works without a key for records made earlier (an app built
    without `correction_check`, reading the same folder).
- [X] T019 [P] [US2] Append to
  `tests/integration/test_word_corrections_flow.py`: correct, undo, then
  practise the word again in a fresh app. There are 0 calls and the old
  values stay (SC-004).
- [X] T020 [P] [US2] Append to `tests/unit/test_web_static_assets.py`:
  `app.js` contains `/api/corrections/undo`, an `Undo` button per entry
  shown only when `can_undo`, and `Undone` for undone entries.

### Implementation

- [X] T021 [US2] In `src/services/corrections.py`, add `undo`, the three
  exceptions, `undone` and `can_undo` in `list`, and undo without a
  checker. Undo needs only the store and the files, so build a light
  `CorrectionService` with `config=None` when there's no key (no checks
  run). Makes T017 pass.
- [X] T022 [US2] In `src/web/app.py`, add `POST /api/corrections/undo`
  with the status mapping, and refresh the live session's item. Make
  `GET /api/corrections` list earlier records without a key (`enabled:
  false`). Makes T018 and T019 pass.
- [X] T023 [US2] In `src/web/static/app.js` (and `style.css` if needed),
  add an Undo button per entry. It posts the id, re-renders the list on
  `200`, and shows the error text on `404` or `409`. Undone entries show
  "Undone" with no button. Makes T020 pass.

**Checkpoint**: corrections can be undone and stay undone.

---

## Phase 5: User Story 3 - Correct the shared word sets (Priority: P3)

**Goal**: shared words are checked the same way. Their corrections go into
the `vocabulary/.corrections.json` overlay and apply to every learner;
an undo applies to everyone too. The shared `.md` files never change.

**Independent Test**: on a temp shared folder, learner A practises a
broken shared word (with the fake checker). Learner B's new session shows
the corrected value and doesn't send it again. The `.md` files have the
same checksums. A undoes it, and B's next load shows the file value
(SC-006).

### Tests (write first, confirm they FAIL)

- [X] T024 [P] [US3] Append to `tests/unit/test_corrections.py`, for a
  shared item:
  - it is checked with `"british"`;
  - a differing answer sets `overlay[overlay_key(file, group, english,
    origin_chinese)]` to all three corrected fields (an entry "holds all
    three fields") and records one record per changed field, with
    `origin_chinese` set to the file's meaning, in
    `vocabulary/.corrections.json`;
  - the `.md` files are byte-identical;
  - compare-and-set: if the word's effective values (file plus overlay)
    changed since the values were sent, nothing is saved;
  - the fingerprint is stored in the shared folder's `checked`, so a
    second account's `prepare` sends nothing (US3 scenario 3);
  - `undo` of a shared batch puts the `old` values back in the overlay
    (or removes the entry when they equal the file's values), sets
    `undone_at`, and marks the restored fingerprint checked;
  - `list(account)` includes shared records (`scope: "shared"`) only
    when the account practises the shared sets
    (`store.word_source(account) != "own"`).
- [X] T025 [P] [US3] Append to
  `tests/integration/test_word_corrections_flow.py`, the two-learner
  shared flow:
  - A corrects a shared word;
  - B sees it, and it isn't re-sent;
  - the `.md` sha256 sums are unchanged;
  - A undoes it, and B's next session shows the file value;
  - a corrected shared word removed by A (spec 020) hides and its undo
    restores it (quickstart k);
  - a corrected shared word keeps its saved example (quickstart l).
- [X] T026 [P] [US3] Append to `tests/contract/test_corrections_api.py`:
  `GET /api/corrections` for a shared-set learner lists `scope:
  "shared"` entries, and undo of a shared entry gives `200` for any
  learner who sees it, or `404` for an own-lists learner.

### Implementation

- [X] T027 [US3] In `src/services/corrections.py`, remove the US1
  shared-item skip, and add `_save_shared` (overlay plus records under
  `corrections_file.update` on the shared folder), shared undo, and
  shared records in `list`. The shared folder is the `vocab_dir` passed
  to the service (`CorrectionService(..., shared_dir=vocab_dir)` from
  `create_app`). After a shared correction, the item's in-memory
  `chinese`, `ipa` and `pos` are updated, but not its `origin_chinese`.
  Makes T024–T026 pass.

**Checkpoint**: all stories are complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T028 [P] Create `src/tools/eval_corrections.py` (R10): `python -m
  src.tools.eval_corrections tests/fixtures/word_check_cases.yml` runs
  `check_word` for each case (no saving).
  - **Scoring**: a `known_error` case counts as fixed when the
    erroneous field now matches `accepted`; a `correct` case counts as
    made worse when any field leaves `accepted`.
  - **Output**: errors fixed (target ≥ 90%), right words made worse
    (target ≤ 5%), failures by QwenError code, and a list of the
    worsened words. The exit code is 0 only when both targets pass.
  - Without a key it prints how to set `DASHSCOPE_API_KEY` and exits
    with 2.

  Add `tests/unit/test_eval_corrections.py` with a fake checker,
  covering the scoring, the targets and the exit codes.
- [X] T029 [P] In `README.md`, add a "Word corrections" section: what is
  checked, which data is sent to Qwen (word data only), the three
  environment variables, where corrections are saved, the Corrections
  page and Undo, and the startup line.
- [X] T030 Run `.venv/bin/ruff check src tests`, `.venv/bin/ruff format
  --check src tests` and `.venv/bin/python -m pytest -q`. All must be
  green.
- [ ] T031 Run the eval on the real model with the user's key: `.venv/
  bin/python -m src.tools.eval_corrections tests/fixtures/word_check_cases.yml`.
  Record the results in `specs/023-word-corrections/eval-report.md`.
  **Stop and ask the user** if either target fails (the SC-001/SC-002
  gate), and before any change to the prompt.
- [X] T032 Do the visual check at 1280 and 390 px: the Corrections page
  (empty, with entries, undone, paused, not set up) and the "Updated"
  note at reveal. Fix anything wrong.
  - Done 2026-10-21 on temp copies with a fake checker. Fixed at 390 px:
    the account name was squeezed to one letter mid-session (now hidden
    while End session shows), and the "Undone" tag wrapped (the list and
    date now go on their own line).
- [ ] T033 Run the quickstart scenarios a–l on temp copies of the data,
  using the user's key, and record the results in `quickstart.md`.
  Confirm the shared `.md` checksums are unchanged (SC-006).

---

## Dependencies & Execution Order

- **Setup (T001)**: needed by T028 and T031 only.
- **Foundational (T002–T007)**: blocks all stories. T006 comes before
  T007.
- **US1 (T008–T016)**: write the tests T008–T012 first. Then T013 before
  T014, T014 before T015, and T015 before T016.
- **US2 (T017–T023)**: needs US1's service and routes. T021 comes before
  T022 and T023.
- **US3 (T024–T027)**: needs US1's service and US2's undo, since shared
  undo extends it.
- **Polish (T028–T033)**: comes last. T031 is the human gate.

```text
Setup ─┐
Foundational ──► US1 (MVP) ──► US2 ──► US3 ──► Polish (eval gate)
```

## Parallel Examples

```bash
# Foundational tests
T002 word_check dialect | T003 corrections_file | T004 overlay + keys
# Foundational implementation
T005 word_check | T006 corrections_file   (then T007)
# US1 tests
T008 service | T009 set_values | T010 API contract | T011 flow | T012 static assets
# US2 tests
T017 | T018 | T019 | T020
# US3 tests
T024 | T025 | T026
# Polish
T028 eval tool | T029 README
```

## Implementation Strategy

1. Do Foundational, then US1. Own-list words then correct themselves.
   That's the MVP, usable once the eval gate (T031) passes.
2. Add US2 (Undo), which makes saving without review safe.
3. Add US3 (shared sets through the overlay).
4. Polish, then the eval gate, then commit to `main` when asked.

## Notes

- Shared `.md` files are never written. Shared corrections live in
  `vocabulary/.corrections.json`.
- Only the five word lines are sent to Qwen (FR-013). The key, prompts
  and replies never appear in responses or logs (FR-015).
- The English word, alternates, group and example lines are never
  changed (FR-002, SC-007).
