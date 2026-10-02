---

description: "Task list for 016-per-user-word-lists"
---

# Tasks: Personal Word Lists per Account

**Input**: Design documents from `/specs/016-per-user-word-lists/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED. Constitution Principle I (Test-First, NON-NEGOTIABLE) overrides the "tests optional" default. Every test task is written and **seen failing for the right reason** before its implementation task starts.

**Organization**: Grouped by spec.md user stories: US1 (P1) upload my own list, US2 (P1) practise only my own words, US3 (P2) view, replace and delete my lists.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: US1, US2, US3. Setup, Foundational and Polish tasks have no story label.

## Path Conventions

Single project. New source file: `src/services/word_lists.py`.

Changed source files:
- `src/web/session_state.py` (adds `set_vocab_dir` only)
- `src/web/session_registry.py`
- `src/web/app.py`
- `src/web/__main__.py`
- `src/web/templates/index.html`, `src/web/static/app.js`, `src/web/static/style.css`
- `.gitignore`, `README.md`

**Not touched**: `src/cli/`, `src/models/`, `src/lib/`, `src/services/{vocabulary_loader,matcher,llm_client,progress_log,accounts}.py`. Existing tests only get new test functions added; no existing assertion changes.

**Test helpers** used throughout:
- Build apps like `tests/contract/test_web_auth_contract.py::_make_app`: a shared `vocab/unit1.md` fixture, two `Account`s (`weibo` → `progress.md`, `lily` → `progress-lily.md`), and `offer_choice=True`.
- Pass `word_lists_dir=tmp_path / "word-lists"`.
- Upload with `client.post("/api/word-lists", data={"file": (io.BytesIO(content_bytes), "unit1.csv")}, content_type="multipart/form-data")`.
- One test client = one browser.

---

## Phase 1: Setup

- [X] T001 In `.gitignore`, under "# Local runtime data", add `/word-lists/` beside the existing `/vocabulary/`, `/progress.md`, `/progress-*.md` and `/accounts.yml`. No new dependencies are needed (`csv` is standard library).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Upload parsing, the per-account `WordListStore` (save and effective folder), `PracticeSession.set_vocab_dir`, and making `SessionRegistry` aware of each account's effective folder. Every story needs these.

**⚠️ CRITICAL**: No user-story work starts until this phase is complete.

### Tests (write first, confirm they FAIL)

- [X] T002 [P] Create `tests/unit/test_word_list_parsing.py` for `parse_upload(filename: str, data: bytes) -> ParsedUpload` (with `.items: list[VocabularyItem]` and `.skipped: list[str]`) and `UploadFormatError` from `src/services/word_lists.py`, per `contracts/upload-formats.md`. Cover:
  - **Extension routing** (case-insensitive): `.md`/`.markdown` use the Markdown format; `.csv`/`.txt`/`.tsv` use the simple list; `x.xlsx` raises `UploadFormatError` with the message `Unsupported file type ".xlsx". Upload a .csv, .txt or .md file.`; a file with no extension is also rejected.
  - **Decoding**:
    - UTF-8 with a BOM (`b"\xef\xbb\xbf" + "receive, 收到".encode()`) parses, and the English is `"receive"` with no BOM;
    - `"receive, 收到".encode("gb18030")` parses to Chinese `"收到"`;
    - bytes that are invalid in both, e.g. `b"\xff\xfe\xfa"`, raise `UploadFormatError` containing `Save it as UTF-8`.
  - **Simple-list separators**: `receive, 收到` with an ASCII comma; `give up，放弃` with a full-width comma; `look up\t查找\tsearch` with tabs, giving alternates `["search"]`; `receive, 收到；接受, accept, get`, giving Chinese `"收到；接受"` and alternates `["accept", "get"]`; and a quoted field `"set off, start", 出发`, giving English `"set off, start"`.
  - **Trimming**: whitespace around fields is trimmed; empty extra fields (`receive, 收到, ,`) add no alternates.
  - **Ignored lines**: blank lines and lines starting with `#` are skipped and not reported.
  - **Header row**: the first row is skipped when its first field is `English`, `word`, `英文` or `单词`, and is not reported.
  - **Skip messages** use 1-based **file** line numbers. In `"English, Chinese\nreceive, 收到\nbroken line\n, 放弃\n"` the result is 1 item, with skipped exactly `["line 3: no Chinese meaning", "line 4: no English word"]`.
  - **Markdown**: a two-block `.md` where block 2 lacks `chinese` gives 1 item and one skipped message starting `block 2:`. A block's `group: t-words` is not used as the result's group; that is set at save time. `english: on` stays the string `"on"`.
  - **Limit**: 5,001 valid simple lines raise `UploadFormatError` with `That list has 5001 words; the limit is 5,000.` Exactly 5,000 is accepted.
  - **No words**: zero valid words returns an empty `items` list. The API decides the 422; the parser does not raise.
- [X] T003 [P] Create `tests/unit/test_word_list_store.py` for `sanitize_list_name(stem: str) -> str` and `WordListStore(root: Path)` from `src/services/word_lists.py`, per `data-model.md` § Word List. Use `Account` objects from `src/models/account.py`.
  - **`sanitize_list_name`** (rule: "Unicode letters/digits, space, `-`, `_`; whitespace collapsed; no leading `.`/space; 1–64 chars"):
    - `"Unit 1"` → `"Unit 1"`; `"  my   words "` → `"my words"`; `"../../etc/passwd"` → `"etcpasswd"`; `".hidden"` → `"hidden"`; `"单元一"` → `"单元一"`; `"a"*80` → 64 chars;
    - `"$$$"` → `""`; the store maps an empty name to `My words`.
  - **`store.save(account, name, items, replace=False)`**:
    - writes `root/<username>/<name>.md` (creating folders) and returns `SaveResult(name, replaced, first_list)`;
    - `load_vocabulary(root/"lily")` reads the items back with the same English, Chinese and alternates in file order, and `group == name` for every item (research R4), including an `english: "on"` round-trip;
    - an empty name saves as `My words`, then `My words 2`;
    - the first save for an account gives `first_list=True`, and the second gives `False`.
  - **Existing names** (case-insensitive: existing `unit1`, new `Unit1`):
    - `replace=False` raises `ListExistsError` carrying the existing name `"unit1"`, and the file is unchanged;
    - `replace=True` overwrites that same file (`unit1.md`), gives `replaced=True`, and no `Unit1.md` is created.
  - **Atomic write**: after save, no temp files remain in the folder.
  - **`store.effective_dir(account, shared: Path)`**: returns `shared` when the account folder is missing or has no `*.md`, and `root/<username>` once a list exists.
  - **Isolation**: saving for `lily` creates nothing under `root/weibo`.
- [X] T004 [P] In `tests/unit/test_session_state.py`, add **new** tests (existing tests unchanged) for `PracticeSession.set_vocab_dir(path)`, per research R3:
  - **(a) Interactive session at `choose`:** `PracticeSession(vocab_dir=A, ..., offer_choice=True)`; after `set_vocab_dir(B)`, `vocab_dir == B`, `all_items` are B's words and `step == "choose"`.
  - **(b) Empty to choose:** a session at `empty` (A empty) moves to `choose` after `set_vocab_dir(B)` with words.
  - **(c) Choose to empty:** pointing to an empty folder gives `step == "empty"`.
  - **(d) Mid-session no-op:** at `recall` after `select_collection(None)`, `set_vocab_dir(B)` leaves `items`, `step`, `current_index` and `all_items` unchanged. A later `end_session()` reloads from B.
  - **(e) Group-locked:** `group="unit1", offer_choice=False` leaves `step` and `items` unchanged, only storing the path.
- [X] T005 [P] In `tests/unit/test_session_registry.py`, add **new** tests (existing ones unchanged):
  - **Effective folder:** `SessionRegistry(vocab_dir=shared, ..., word_lists=WordListStore(root))`. `get(lily)` before any save gives `vocab_dir == shared`. After saving one of lily's lists in the store, and for a **new** registry, `get(lily).vocab_dir == root/"lily"`, while `get(weibo).vocab_dir == shared`.
  - **`refresh_vocab`:** with a live lily session at `choose`, saving a list then calling `refresh_vocab(lily)` gives `step == "choose"` with collections containing only that list's name. Weibo's session is unchanged.
  - **No session yet:** `refresh_vocab` on an account without a live session does not raise.
  - **Store omitted:** constructing without `word_lists` keeps spec 015 behaviour (always shared).

### Implementation

- [X] T006 Create `src/services/word_lists.py` (module docstring citing spec 016 and `contracts/upload-formats.md`). Makes T002 and the parsing parts of T003 pass. Contents:
  - Exceptions `UploadFormatError(Exception)` and `ListExistsError(Exception)`, the latter with a `.name` attribute.
  - A `ParsedUpload` dataclass with `items` and `skipped`.
  - Constants `MAX_WORDS = 5000`, `SIMPLE_EXTENSIONS = {".csv", ".txt", ".tsv"}`, `MARKDOWN_EXTENSIONS = {".md", ".markdown"}`, `HEADER_WORDS = {"english", "word", "英文", "单词"}`.
  - `_decode(data)`: try `utf-8-sig`, then `gb18030`; else raise `UploadFormatError("Couldn't read the file's text. Save it as UTF-8 and try again.")`.
  - `_parse_simple(text)`: iterate `text.splitlines()` with 1-based numbers:
    - skip blank or `#` lines;
    - if a line contains `\t`, split it with `csv.reader([line], delimiter="\t")`; otherwise replace `，` with `,` and use `csv.reader([line])`;
    - strip every field;
    - skip the first content row if `fields[0].lower()` is in `HEADER_WORDS`;
    - missing or empty field 1 → `line N: no English word`;
    - missing or empty field 2 → `line N: no Chinese meaning`;
    - otherwise `VocabularyItem(english, chinese, [f for f in fields[2:] if f])`.
  - `_parse_markdown(text)`: reuse `parse_blocks` and `VocabularyItem.from_block`, numbering found blocks from 1 as `block N: <reason>`, and drop `group`.
    - `parse_blocks` drops blocks it can't parse and returns their warnings separately, so the block numbers may need to come from re-scanning. Simplest: map each parse warning to `block ?: <warning>` if it can't be numbered. Keep the numbering exact for missing-field blocks.
  - `parse_upload(filename, data)`: route by `Path(filename).suffix.lower()`; on a bad extension, raise the contract's unsupported-type message; after parsing, raise when `len(items) > MAX_WORDS`; return the `ParsedUpload`.
  - `sanitize_list_name(stem)`: `unicodedata`-aware; keep a char if `ch.isalnum() or ch in " -_"`; collapse whitespace with `" ".join(s.split())`; `lstrip(". ")`; truncate to 64 then `strip()`.
- [X] T007 In `src/services/word_lists.py`, add `class WordListStore` and `SaveResult(name: str, replaced: bool, first_list: bool)`. Depends on T006; makes the rest of T003 pass. Members:
  - `__init__(root: Path)`, plus a per-username `threading.Lock` dict guarded by a meta-lock.
  - `folder(account) -> Path`: `root / account.username`.
  - `_find(account, name) -> Path | None`: case-insensitive match against existing `*.md` stems.
  - `save(account, name, items, replace=False) -> SaveResult`, under the account lock:
    - the empty name becomes `My words`, then ` 2`, ` 3` while taken;
    - an existing name with `not replace` raises `ListExistsError(existing_stem)`; with `replace`, overwrite the existing file path, keeping its original case;
    - `first_list = not any(folder.glob("*.md"))` before writing;
    - write the blocks with `yaml.safe_dump({"english", "alternates", "chinese", "group": name}, allow_unicode=True, sort_keys=False, default_flow_style=False)`, each wrapped as `---\n...---\n\n`, to a `tempfile.NamedTemporaryFile(dir=folder, delete=False, suffix=".tmp")`, then `os.replace` it into place.
  - `effective_dir(account, shared) -> Path`: the account folder if it has any `*.md`, else `shared`.
  - `word_source(account) -> "own" | "shared"`.
- [X] T008 [P] In `src/web/session_state.py`, add `set_vocab_dir(self, vocab_dir: Path) -> None`, with a docstring citing spec 016 research R3:
  - set `self.vocab_dir = vocab_dir`;
  - if `not self.group_locked and self.step in ("choose", "empty")`, reload with `load_vocabulary`, set `self.warnings` and `self.all_items`, and set `self.step = "choose" if self.all_items else "empty"`.

  Change nothing else in the file. Makes T004 pass.
- [X] T009 In `src/web/session_registry.py`, depends on T007 and T008; makes T005 pass:
  - add an optional `word_lists: WordListStore | None = None` constructor parameter;
  - `_new_session(account)` uses `self._word_lists.effective_dir(account, self._vocab_dir)` when a store is present, else `self._vocab_dir`;
  - add `refresh_vocab(account)`: under the lock, if the account has a live session, call `session.set_vocab_dir(<effective dir>)`;
  - `reset()` (logout) also uses the effective folder through `_new_session`.

**Checkpoint**: the four foundational test files pass, and the full suite still passes. No web behaviour has changed yet.

---

## Phase 3: User Story 1 - Upload my own word list from the web UI (Priority: P1) 🎯 MVP

**Goal**: A logged-in learner picks a `.csv`, `.txt` or `.md` file on the word-set screen. Valid words are saved as a new list, skipped entries are reported, and the list appears as a word set right away.

**Independent Test**: Log in as lily and upload `"English, Chinese\nreceive, 收到\nbroken\n"` as `unit1.csv`. The response says 1 added and 1 skipped, and `GET /api/state` then shows a `unit1` collection with 1 word.

### Tests (write first, confirm they FAIL)

- [X] T010 [P] [US1] Create `tests/contract/test_word_lists_api_contract.py` covering `POST /api/word-lists` per `contracts/word-lists-api-contract.md` and the limits in `contracts/upload-formats.md`.
  - **Request errors:**
    - no login → `401` `{"error": "login required"}`, and nothing is created under `word-lists/`;
    - no `file` part, or an empty filename → `400` `{"error": "Choose a file to upload."}`;
    - `x.xlsx` → `415` with the unsupported-type message;
    - an all-blank `.txt` → `422`, with `error` starting `No words found.`, and no file written;
    - a 5,001-line upload → `422` with the limit message.
  - **Too large:** a body over 1 MiB (`b"a, b\n" * 220000`) → `413` with JSON `{"error": "The file is larger than 1 MB."}`, not Flask's HTML page.
  - **Success:** `200` with exactly the Upload Result keys `name`, `replaced`, `added`, `skipped_count`, `skipped`, `first_list`, `applies_now`, and values `"unit1"`, `False`, `1`, `1`, `["line 3: no Chinese meaning"]`, `True`, `True`.
  - **Skip cap:** 25 broken lines and 1 good line give `skipped_count == 25` and `len(skipped) == 20`.
  - **Existing name:** uploading `Unit1.csv` again without `replace` → `409` `{"exists": true, "name": "unit1"}`, and the file is unchanged.
  - **Legacy and no-store apps:** `create_app(...)` without `word_lists_dir`, with or without accounts, has no route: `POST /api/word-lists` returns `404`, or `401` before login in accounts mode. After login it is `404`.
- [X] T011 [P] [US1] Create `tests/integration/test_word_lists_flow.py`:
  - **Upload shows up right away:** lily, at `choose` with the shared fixture sets, uploads `unit1.csv`. A following `GET /api/state` has `step == "choose"` and collections `[Practice everything (1), unit1 (1)]`, with none of the shared groups. Selecting `unit1` and answering `receive` is graded correct, and the attempt lands in `progress-lily.md`.
  - **Markdown upload:** a `.md` file whose blocks say `group: t-words` shows up as a set named after the file stem.
  - **Startup flag:** `src.web.__main__` main with `--word-lists-dir <tmp>` prints `Word lists: <tmp>`. Monkeypatch `Flask.run`, as in `tests/integration/test_web_startup_accounts.py`, and assert `build_arg_parser().parse_args([]).word_lists_dir == Path("word-lists")`.
- [X] T012 [P] [US1] In `tests/unit/test_web_static_assets.py`, add tests per `contracts/word-lists-ui-contract.md`:
  - `index.html` `#choose-view` contains `id="upload-button"` with the text `Upload word list`, and `<input id="upload-input" type="file"` with `accept=".csv,.txt,.tsv,.md,.markdown"`;
  - it contains `id="upload-format-hint"` and `id="upload-result"` with `role="status"`;
  - `#empty-view` contains `id="empty-upload-button"`;
  - `app.js` references `/api/word-lists`, `FormData` and `replace`, plus the strings `Added ` and `From now on you'll practice your own lists.`

### Implementation

- [X] T013 [US1] In `src/web/app.py`, depends on T007 and T009; makes T010 and part of T011 pass.
  - **Parameter:** add `word_lists_dir: Path | None = None`.
  - **Store:** in accounts mode with `word_lists_dir` set, create `store = WordListStore(word_lists_dir)` and pass `word_lists=store` to `SessionRegistry`.
  - **Request size:** set `app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024` and add `@app.errorhandler(413)` returning `jsonify({"error": "The file is larger than 1 MB."}), 413`.
  - **`POST /api/word-lists`:**
    - get `file = request.files.get("file")`; if it's missing or has no `filename` → `400`;
    - `parse_upload(file.filename, file.read())`; `UploadFormatError` → `415`, or `422` when the message starts with `That list has`;
    - no items → `422` with `{"error": "No words found. Use one word per line, like: receive, 收到 — or a .md vocabulary file.", "skipped": parsed.skipped[:20], "skipped_count": len(parsed.skipped)}`;
    - get `name = sanitize_list_name(Path(file.filename).stem)` and `replace = request.form.get("replace") == "true"`;
    - `store.save(account, name, parsed.items, replace)`; `ListExistsError` → `409 {"exists": True, "name": exc.name}`;
    - then `app.session_registry.refresh_vocab(account)`;
    - return the Upload Result with `applies_now = not _current_session().group_locked`.
  - **Scope:** register the route only when the store exists.
- [X] T014 [US1] In `src/web/__main__.py`, depends on T013; makes T011's start-up assertions pass:
  - add `parser.add_argument("--word-lists-dir", type=Path, default=Path("word-lists"), help="Where each account's uploaded word lists are kept (default: word-lists)")`;
  - pass `word_lists_dir=args.word_lists_dir` to `create_app`;
  - print `f"Word lists: {args.word_lists_dir}"` after the Accounts line.
- [X] T015 [P] [US1] In `src/web/templates/index.html`, per the UI contract. Makes T012's template assertions pass.
  - In `#choose-view`, after `.word-sets`, add `<div id="upload-area" class="upload-area" hidden>` containing:
    - `<button id="upload-button" type="button" class="btn btn-secondary">Upload word list</button>`;
    - `<input id="upload-input" type="file" accept=".csv,.txt,.tsv,.md,.markdown" hidden>`;
    - `<p id="upload-format-hint" class="option-hint">One word per line: <code>receive, 收到</code> — or a .csv / .md file.</p>`;
    - `<div id="upload-result" class="upload-result" role="status" hidden></div>`.
  - In `#empty-view`, add `<button id="empty-upload-button" type="button" class="btn btn-secondary" hidden>Upload word list</button>`.
- [X] T016 [US1] In `src/web/static/app.js`, depends on T013 and T015; makes T012's JS assertions pass.
  - **Showing the controls:** in `renderState`, unhide `#upload-area` (choose) and `#empty-upload-button` (empty) only when `state.account` is present and `state.word_source` is defined (store enabled).
  - **Opening the picker:** both buttons call `uploadInput.click()`.
  - **`uploadFile(file, replace=false)`:**
    - build a `FormData` with `file`, and `replace="true"` when confirming;
    - send `fetch("/api/word-lists", {method: "POST", body: form})`, and run `isUnauthorized(resp)` first;
    - on `409`, ask `confirm(\`Replace your list “${data.name}”?\`)` and, if confirmed, call `uploadFile(file, true)`;
    - on `200`, render the result into `#upload-result`: "Added N words to “name”.", then the skipped list when `skipped_count > 0` ("Skipped K:" followed by `<li>` items built with `textContent`, never `innerHTML`), then "From now on you'll practice your own lists." when `first_list`, then the locked note when `!applies_now`. After that, call `fetchState()`;
    - otherwise show `data.error`.
  - **Resetting the picker:** on input `change`, upload `uploadInput.files[0]` and then set `uploadInput.value = ""`.
- [X] T017 [P] [US1] In `src/web/static/style.css`, using existing tokens only:
  - `.upload-area`: `margin-top: 48px`, a flex column with `gap: var(--space-3)`, `align-items: flex-start`;
  - `.upload-result`: font size 15px; a list inside with `padding-left: 1.2em`; error text in `var(--color-accent-2-700)` via `.upload-result--error`;
  - `.option-hint code`: `font: inherit`, background `var(--color-surface)`, padding `0 4px`;
  - at ≤600px, `.upload-area .btn` stretches.

**Checkpoint**: a learner can upload a list from the web UI and practise it. US1 tests and the full suite pass.

---

## Phase 4: User Story 2 - Practise only my own words (Priority: P1)

**Goal**: An account with lists practises only its own lists, and an account without any uses the shared folder. No account ever sees another's lists. The UI says which source is in use.

**Independent Test**: Lily uploads `unit1`, and weibo uploads `T_words.md`. Each `GET /api/state` at `choose` lists only that account's own set. A second app instance on the same `word-lists` dir (a "restart") gives the same result.

### Tests (write first, confirm they FAIL)

- [X] T018 [P] [US2] In `tests/integration/test_word_lists_flow.py`, add tests:
  - **(a) Separate word sets:** with two clients, lily uploads `unit1.csv` and weibo uploads `T_words.md`. Lily's collections contain `unit1` and not `T_words`, and the reverse for weibo. Each one's "Practice everything" count equals its own word count.
  - **(b) Shared folder until the first upload:** weibo without uploads, while lily has some, still sees the shared fixture group(s).
  - **(c) Practice stays separate:** lily practises all of `unit1` in recall-only mode. `progress-lily.md` holds only `unit1` words, and `progress.md` doesn't exist.
  - **(d) Restart persistence (SC-004):** a fresh `create_app` on the same `word_lists_dir`, after a fresh login, still shows each account's own sets.
  - **(e) Same name for both accounts:** both upload `unit1.csv` with different words. Each practises only its own words, and the files are `word-lists/lily/unit1.md` and `word-lists/weibo/unit1.md`.
  - **(f) Mid-session upload:** lily is at `recall` after selecting a shared set, and uploads on a second lily client. Her first client's `position`, `total` and `chinese` are unchanged. After `POST /api/end`, the collections show only `unit1`.
- [X] T019 [P] [US2] In `tests/contract/test_word_lists_api_contract.py`, add tests:
  - in accounts mode with a store, `GET /api/state` includes `word_source`, which is `"shared"` before any upload and `"own"` after;
  - with no store, `word_source` is absent;
  - the `GET /api/state` response never includes the path of another account's folder (assert `"lily"` is not in weibo's state JSON).
- [X] T020 [P] [US2] In `tests/unit/test_web_static_assets.py`, add assertions that `index.html` `#choose-view` contains `id="word-source-note"`, and that `app.js` contains both note strings, "Practicing your own word lists." and "Practicing the shared word sets".

### Implementation

- [X] T021 [US2] In `src/web/app.py`, in `GET /api/state`, add `state["word_source"] = store.word_source(_current_account())` when the store exists. If T018 shows another shared-state leak, route vocabulary through `SessionRegistry` and `store.effective_dir` only, with no module-level vocabulary. Depends on T013; makes T018 and T019 pass.
- [X] T022 [P] [US2] In `src/web/templates/index.html`, add `<p id="word-source-note" class="option-hint" hidden></p>` at the top of `.word-sets` in `#choose-view`.
- [X] T023 [US2] In `src/web/static/app.js`, in `renderState`, when `state.word_source` is present, set `#word-source-note` text to "Practicing your own word lists." for `"own"`, or "Practicing the shared word sets — upload a list to practice your own words." for `"shared"`, and unhide it. Otherwise hide it. Depends on T016 and T022; makes T020 pass.

**Checkpoint**: US1 and US2 together match the user's requested model. quickstart scenarios 1, 2, 5 and 6 pass.

---

## Phase 5: User Story 3 - View, replace and delete my lists (Priority: P2)

**Goal**: "My word lists" shows name, word count and upload date. Uploading an existing name asks to confirm and then replaces the list. Delete asks to confirm and then removes the list. History and sessions in progress are untouched.

**Independent Test**: Upload `unit1`, upload `unit1` again with `replace=true` (only the new words remain), then delete `unit1`. The account is back on the shared folder, and `progress-lily.md` is unchanged throughout.

### Tests (write first, confirm they FAIL)

- [X] T024 [P] [US3] In `tests/unit/test_word_list_store.py`, add tests:
  - **`store.list(account)`** returns `[{"name", "word_count", "uploaded_at"}]`, sorted case-insensitively by name. `uploaded_at` is ISO-8601 UTC from the file mtime, and `word_count` matches the saved items.
  - **`store.delete(account, name)`** works case-insensitively and removes the file. An unknown name raises `KeyError`. A traversal attempt like `delete(lily, "../weibo/unit1")` sanitises to `weibounit1`, raises `KeyError`, and leaves weibo's file intact. Deleting the last list makes `effective_dir` return `shared`.
- [X] T025 [P] [US3] In `tests/contract/test_word_lists_api_contract.py`, add tests:
  - **`GET /api/word-lists`**: before uploads → `{"word_source": "shared", "lists": []}`; after uploading `b.csv` and `A.csv` → names in order `["A", "b"]`, each with `word_count` and `uploaded_at`.
  - **Replace:** `POST` with `replace=true` on an existing name → `200` with `replaced: true` and `first_list: false`. The saved file contains only the new words.
  - **`DELETE /api/word-lists/unit1`**: → `200` `{"deleted": "unit1", "word_source": "shared"}`.
  - **Delete errors:** a second delete → `404` `{"error": "No list named \"unit1\"."}`. Weibo deleting lily's `unit1` → `404`, and lily's file still exists. `DELETE /api/word-lists/..%2Flily%2Funit1` as weibo → `404`. No login → `401`.
- [X] T026 [P] [US3] In `tests/integration/test_word_lists_flow.py`, add tests:
  - **(a) Replace mid-session:** lily practises `unit1` and answers 1 word, giving one history attempt. A second lily client replaces `unit1`. The first client's session continues with the old words until its end. After `restart` or `end`, `unit1` has the new word count. `progress-lily.md` keeps the earlier attempt.
  - **(b) Delete the last list:** deleting her only list at `choose` makes lily's collections show the shared fixture sets again, with `word_source == "shared"`. History is unchanged.
- [X] T027 [P] [US3] In `tests/unit/test_web_static_assets.py`, add assertions that `index.html` has `id="my-lists"` in `#choose-view`, and that `app.js` references `method: "DELETE"`, `encodeURIComponent`, the string `Your practice history is kept.`, and `data-list-name` or `dataset.listName`.

### Implementation

- [X] T028 [US3] In `src/services/word_lists.py`, add to `WordListStore`, depends on T007; makes T024 pass:
  - `list(account) -> list[dict]`: for each `*.md`, the name is the stem; `word_count = len(load_vocabulary-style items)`, either via `load_vocabulary` on a single file or `parse_blocks` and `from_block`; `uploaded_at = datetime.fromtimestamp(st_mtime, UTC).isoformat(timespec="seconds")`; sort by `name.lower()`.
  - `delete(account, name)`: under the lock, `path = self._find(account, sanitize_list_name(name))`; if it's missing, raise `KeyError(name)`; otherwise `path.unlink()`. Return the deleted stem.
- [X] T029 [US3] In `src/web/app.py`, depends on T013 and T028; makes T025 and T026 pass:
  - add `GET /api/word-lists` → `{"word_source": ..., "lists": store.list(account)}`;
  - add `DELETE /api/word-lists/<path:name>`: on success → `refresh_vocab` and `{"deleted": stem, "word_source": ...}`; `KeyError` → `404 {"error": f'No list named "{name}".'}`;
  - confirm the T013 POST handles `replace=true`; the store already does.
- [X] T030 [P] [US3] In `src/web/templates/index.html`, inside `#upload-area` before the result, add `<section id="my-lists" class="my-lists" hidden><h2 class="label">My word lists</h2><ul id="my-lists-items" class="my-lists-items"></ul></section>`.
- [X] T031 [US3] In `src/web/static/app.js`, depends on T016, T029 and T030; makes T027 pass.
  - **Fetching:** add `fetchLists()`, which calls `GET /api/word-lists` (through `api()`) whenever `renderState` shows `choose` or `empty` with `state.word_source` present.
  - **Rendering:** render rows with `textContent`: the name, then a `.text-muted` "N words · uploaded <toLocaleDateString(undefined, {day: "numeric", month: "short"})>", then a `.btn-ghost` "Delete" button with `dataset.listName = name`. Hide `#my-lists` when the list is empty.
  - **Delete click:** `confirm(\`Delete your list “${name}”? Your practice history is kept.\`)`, then `fetch(\`/api/word-lists/${encodeURIComponent(name)}\`, {method: "DELETE"})`. Run `isUnauthorized` on the response, then call `fetchState()`.
- [X] T032 [P] [US3] In `src/web/static/style.css`:
  - `.my-lists-items`: no list style; rows use flex with `gap: var(--space-3)` and `align-items: baseline`, and `border-top: 1px solid var(--color-divider)`;
  - the name uses `font-weight: 600`; the meta text uses `.text-muted` at 14px; the Delete button sits at `margin-left: auto`;
  - at ≤600px, rows wrap.

**Checkpoint**: all three stories work. quickstart scenarios 3 and 4 pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T033 [P] Update `README.md`:
  - in "Running (web UI)", mention the `--word-lists-dir` flag;
  - add a "Your own word lists (web UI)" subsection covering:
    - how to upload;
    - both formats, with the simple-list example including `，` and tab;
    - one file = one word set named after the file;
    - the rule that once you have a list you practise only your own lists, otherwise the shared `vocabulary/` (deleting your last list switches you back);
    - replace and delete, and that history is kept;
    - the limits (1 MB, 5,000 words);
    - files live in `word-lists/<username>/` (gitignored, readable Markdown);
  - extend the Caution note so `word-lists/` also sits outside `--vocab-dir`;
  - state that the CLI is unchanged.
- [X] T034 [P] Run `.venv/bin/ruff check .`, and `ruff format` on **new** files only (the repo doesn't enforce format on existing files).
- [X] T035 Run `.venv/bin/pytest -q`. Every pre-existing test must pass unchanged; `git diff --stat tests/` shows only additions in the existing files.
- [X] T036 Visual check with the project's `frontend-design` workflow. Start an isolated instance with `--word-lists-dir design/verification/word-lists`, log in through cookie jars (as for spec 015), and screenshot at 1280, 390 and 375 px:
  - the choose screen with the shared note and the upload area;
  - after an upload, the result message and "My word lists";
  - the empty screen with the upload button.

  Fix overflow or spacing in `src/web/static/style.css`. Use `--wait-for-timeout` so the fade-in has finished.
- [ ] T037 Run `specs/016-per-user-word-lists/quickstart.md` scenarios 0–7 against the isolated instance through the API, and record which steps need a real browser (the file picker, confirm dialogs) for the user to click through.
  - *Status (2026-10-02)*: scenarios 0, 3, 4 and 5 were run against a live isolated server through the API with curl, including the replace confirmation (409, then `replace=true`), deleting the last list falling back to the shared folder, both traversal attempts returning 404, and the 1 MB, `.xlsx` and blank-file rejections. Scenarios 1, 2 and 6 are covered end to end by `tests/integration/test_word_lists_flow.py`. Scenario 7 holds because `src/cli` is unchanged (empty diff). Screenshots are in `design/verification/wl/pass-0/`. **Still to do by a person**: picking a file with the real browser and phone file picker, clicking OK/Cancel on the replace and delete confirmation dialogs, and uploading a CSV exported from Excel or Numbers.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: T006 → T007 → T009; T008 ∥ T006. Blocks all stories.
- **US1 (Phase 3)**: needs Phase 2.
- **US2 (Phase 4)**: needs US1's T013 (the upload route) to have data to separate.
- **US3 (Phase 5)**: needs US1 (T013, T016). Independent of US2 apart from `app.js` and the shared test files; coordinate those edits.
- **Polish (Phase 6)**: after the stories you ship.

### Test-before-code pairs

- T002/T003 → T006/T007
- T004 → T008
- T005 → T009
- T010/T011/T012 → T013–T017
- T018–T020 → T021–T023
- T024–T027 → T028–T032

### Parallel Opportunities

- T002 ∥ T003 ∥ T004 ∥ T005, then T006 ∥ T008.
- T010 ∥ T011 ∥ T012, then T015 ∥ T017 alongside T013/T014.
- T018 ∥ T019 ∥ T020, and T022 alongside T021.
- T024 ∥ T025 ∥ T026 ∥ T027, then T030 ∥ T032 alongside T028/T029.
- T033 ∥ T034.

---

## Parallel Example: Foundational

```bash
Task: "parse_upload tests in tests/unit/test_word_list_parsing.py"
Task: "WordListStore + sanitize tests in tests/unit/test_word_list_store.py"
Task: "set_vocab_dir tests in tests/unit/test_session_state.py"
Task: "registry effective-folder tests in tests/unit/test_session_registry.py"
```

## Parallel Example: User Story 1

```bash
Task: "POST /api/word-lists contract tests in tests/contract/test_word_lists_api_contract.py"
Task: "upload-then-practice flow in tests/integration/test_word_lists_flow.py"
Task: "upload UI static assertions in tests/unit/test_web_static_assets.py"
# then alongside T013:
Task: "upload markup in src/web/templates/index.html"
Task: "upload styles in src/web/static/style.css"
```

---

## Implementation Strategy

### MVP (Phases 1–4: US1 + US2)

Both stories are P1, and together they are the user's request: upload your own words, then practise them separately. US1 on its own already gives separation through the foundational effective-folder logic, so after Phase 3 you can stop and check that lily uploads and practises only her list. Phase 4 adds the `word_source` note and the isolation tests.

### Incremental Delivery

1. Phases 1–2: the foundation, with no visible change.
2. US1: upload works. Validate quickstart scenario 1.
3. US2: the word-source note and isolation proofs. Validate scenarios 2, 5 and 6.
4. US3: list, replace and delete. Validate scenarios 3 and 4.
5. Polish: README, lint, full regression run, screenshots, quickstart.

---

## Notes

- `create_app(word_lists_dir=None)` registers no word-list routes and uses only the shared folder, so every spec 015 test stays valid. The real entry point always passes `--word-lists-dir`.
- Render uploaded text (list names, skip messages) with `textContent` only. List names come from user filenames.
- Never build a filesystem path from a raw request value. Always use `sanitize_list_name`, then `_find` inside `store.folder(account)`.
- Commit after each phase or logical group.
