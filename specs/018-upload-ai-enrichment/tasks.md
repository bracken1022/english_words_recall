---

description: "Task list for 018-upload-ai-enrichment"
---

# Tasks: Local-AI Enrichment of Uploaded Word Lists

**Input**: design documents from `/specs/018-upload-ai-enrichment/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ and quickstart.md (all present)

**Tests**: included and REQUIRED, because Constitution Principle I
(Test-First, NON-NEGOTIABLE) applies. Each test task is written first and
**seen failing for the right reason** before its implementation task
starts. Existing tests are never edited (SC-008); new test functions go in
new files, or are appended to existing files.

**Organization**: by spec.md user stories:

- **US1 (P1)**: upload bare English words, watch progress, preview,
  confirm, and see the list in My Word Lists.
- **US2 (P1)**: failures don't lose the upload: per-item failure and
  retry, Ollama unavailable, restart, no duplicate batches.
- **US3 (P2)**: existing entries are flagged and kept by default, with an
  explicit update option.
- **US4 (P2)**: trustworthy pronunciations: the American IPA checker, and
  heteronym and acronym flags.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no unmet dependencies).
- **[Story]**: US1–US4. Setup, Foundational and Polish tasks have no story
  label.

## Path Conventions

This is a single project.

- **New source**:
  - `src/lib/alternates.py`
  - `src/services/enrichment_client.py`
  - `src/services/enrichment.py`
  - `src/tools/eval_enrichment.py`
- **Changed source**:
  - `src/lib/ipa.py`
  - `src/services/llm_client.py` (refactor only)
  - `src/services/word_lists.py`
  - `src/web/app.py`
  - `src/web/templates/index.html`
  - `src/web/static/app.js`
  - `src/web/static/style.css`
  - `README.md`
- **Not touched**:
  - `src/services/{matcher,progress_log,accounts,vocabulary_loader}.py`
  - `src/web/session_state.py`
  - `src/cli/*`
  - `src/tools/add_ipa.py`
  - spec 016's `POST /api/word-lists`, `GET /api/word-lists` and
    `DELETE /api/word-lists/<name>` handlers (behaviour must stay
    identical).
- **Mocking Ollama in tests**: patch `src.services.llm_client.requests.post`.
  Both sentence review and enrichment go through
  `llm_client._post_chat`. Use the `_FakeResponse` / `_content` helper
  pattern from `tests/contract/test_ollama_correction_contract.py`. To
  simulate an unavailable model, set `side_effect =
  requests.ConnectionError()`.

---

## Phase 1: Setup

- [X] T001 [P] Create `tests/fixtures/american_ipa.yml`. It is a reviewed
  YAML list of at least 30 `{english, ipa}` pairs, all in the **Oxford
  Learner's Dictionaries NAmE** style (research R4): length marks kept,
  every r written (`ɑːr`/`ɔːr`/`ɜːr`/`ər`), `oʊ`, `ɡ` (U+0261), `ˈ`/`ˌ`,
  and no slashes. Include:
  - receive `rɪˈsiːv`, zealous `ˈzeləs`, tend to `ˈtend tə`;
  - water `ˈwɔːtər`, car `kɑːr`, go `ɡoʊ`, thought `θɔːt`, hot `hɑːt`,
    better `ˈbetər`, bird `bɜːrd`, color `ˈkʌlər`;
  - epitomize `ɪˈpɪtəmaɪz`, arduous `ˈɑːrdʒuəs`, give up `ˌɡɪv ˈʌp`.

  Also add a top-level `british_counterparts:` list of at least 10
  British forms that must FAIL the American check: `hɒt`, `ɡəʊ`,
  `ˈwɔːtə(r)`, `bɜːd`, `ˈbetə(r)`, `hɪə(r)`, `keə(r)`, `ʃʊə(r)`, `nəʊ`,
  `ˈɒfn`, `ˈkʌlə(r)` and `θɒt`. Add a header comment citing spec 018 research R4 and the
  date reviewed.
- [X] T002 [P] Create `tests/fixtures/enrichment_eval.yml`, the reviewed
  evaluation set for research R10. It has three sections:
  - `words:` holds at least 50 `{english, ipa, chinese_any: [..]}`
    entries, using American IPA in the T001 style.
    - `chinese_any` lists acceptable core glosses; any one appearing as
      a `；` part counts as correct.
    - Include at least 5 multi-word expressions.
  - `heteronyms:` holds at least 8 words (record, present, object, lead,
    tear, wind, live, minute), which are expected to be flagged.
  - `traps:` holds at least 20 `{english, forbidden: [..]}` entries for
    broad synonyms, e.g. arduous→difficult, zealous→enthusiastic,
    big→large, begin→start, rapid→fast, affect→effect and
    accept→except.
  - `variants:` holds at least 10 `{english, expected}` pairs: tyre→tire,
    epitomise→epitomize, colour→color, centre→center, grey→gray,
    travelled→traveled, analyse→analyze, programme→program,
    defence→defense and e-mail→email.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the pieces that every story uses:

- incomplete-word parsing;
- the transport refactor;
- the enrichment client;
- the pending import model and file store;
- Chinese and alternates validation.

### Tests (write first, confirm they FAIL)

- [X] T003 [P] In `tests/unit/test_word_list_parsing.py`, **append**
  tests for `parse_upload(filename, data, require_chinese=False)`, which
  returns `ParsedUpload` whose `items` are `DraftWord`s:
  - `"zealous\ntyre\n"` (`.txt`) gives two drafts, with
    `english == "zealous"`, `chinese is None`, `ipa is None`,
    `alternates == []` and `position == "line 1"`.
  - `"receive, 收到；接受, /rɪˈsiːv/, accept"` gives a draft with
    `chinese == "收到；接受"`, `ipa == "rɪˈsiːv"` and
    `alternates == ["accept"]`.
  - `"  Hello!  "` gives `english == "Hello!"`: trimmed only.
  - A line with an empty first field is still skipped, as
    `line N: no English word`.
  - A Markdown block with `english` but no `chinese` gives a draft with
    `position == "block 1"` and `chinese is None`. A block without
    `english` is skipped as `block N: missing 'english'`.
  - The header row is skipped as before. The 5,000-word limit still
    raises `UploadFormatError`.
  - The default `require_chinese=True` output is unchanged: still
    `VocabularyItem`s, still skipping `no Chinese meaning`. Existing
    tests already cover this, so assert one case here explicitly.
- [X] T004 [P] Create `tests/contract/test_enrichment_llm_contract.py`
  for `request_enrichment(english, supplied, base_url, model,
  timeout=60.0) -> EnrichmentReply`, per
  `contracts/enrichment-llm-contract.md`. Patch
  `src.services.llm_client.requests.post`.
  - **Payload**: the payload has `model`, `stream is False`,
    `think is False` and `options["temperature"] == 0`.
    `format["required"]` is exactly
    `["ipa", "ipa_uncertain", "chinese", "alternates"]`, and the URL ends
    with `/api/chat`.
  - **User message**: the user message contains `English: "zealous"`.
    With `supplied={"chinese": "收到"}` it also contains
    `Meaning: "收到"`.
  - **Message content**: the messages never contain the list name, a file
    name, or any other word. Call the function with
    `english="zealous"` and assert that `"z-words"` and `".txt"` are
    absent.
  - **System prompt**: it contains the substrings `General American`,
    `Oxford`, `NAmE`, `ipa_uncertain`, `；`, `spelling variants` and
    `Never give synonyms`.
  - **A valid reply** gives `outcome == "ok"`, with the fields copied.
    Extra keys (`"group": "x"`, `"english": "zeal"`) are ignored, and
    `EnrichmentReply` has no `english` or `group` attribute.
  - **`ConnectionError`** → `outcome == "unavailable"`, and HTTP `404` →
    `"unavailable"`.
  - **`bad_reply`** with a non-empty `detail` for each of the following:
    `requests.Timeout`, HTTP 500, a missing `message`, content
    `"not json"`, content `"[]"`, a missing `alternates`,
    `ipa_uncertain` given as `"yes"` (a str), and `alternates` given as
    `"tire"` (a str).
  - The function never raises.
- [X] T005 [P] Append to `tests/contract/test_ollama_correction_contract.py`
  one regression test: patching `requests.post` with `ConnectionError`
  still yields `available is False` from `request_correction`. This
  guards the `_post_json` → `_post_chat` refactor.
- [X] T006 [P] Create `tests/unit/test_alternates.py` for
  `src/lib/alternates.py`, per `contracts/enrichment-validation.md` §
  Alternates.
  - **`is_spelling_variant`**: true for tyre/tire, epitomise/epitomize,
    colour/color, centre/center, travelled/traveled, e-mail/email,
    analyse/analyze, defence/defense, grey/gray,
    organisation/organization, anaemia/anemia and catalogue/catalog.
    False for arduous/difficult, zealous/enthusiastic, affect/effect,
    accept/except, big/large, tire/tired and form/from.
  - **`filter_alternates(english, supplied, proposed)`** returns
    `(kept, dropped)`.
    - Supplied alternates come first and are always kept, even when they
      are synonyms.
    - Proposed alternates are kept only if `is_spelling_variant`.
    - Dedupe is case-insensitive and keeps the first occurrence.
    - Entries equal to `english` (case-insensitive) or empty after
      `strip()` are dropped.
    - At most 5 are kept. Any entry over 64 characters is dropped.
    - `dropped` lists the rejected proposals in order.
- [X] T007 [P] Create `tests/unit/test_enrichment_validation.py` for
  `validate_chinese(text) -> tuple[str | None, str | None]` in
  `src/services/enrichment.py`, per § Chinese.
  - `"热心的;热情的"` gives `("热心的；热情的", None)`; ASCII `,` and
    full-width `，` are normalised to `；`.
  - `" 收到 "` gives `"收到"`.
  - These fail with `"meaning was unusable"`:
    - `""`, `"hello"` (no CJK);
    - `"a\nb热"` (a newline);
    - 5 parts;
    - an empty part (`"热心；；热情"`);
    - 41 characters;
    - `"n. 热心"`, `"【热心】"`;
    - `"热心 used in a sentence"` (4 or more Latin words).
- [X] T008 [P] Create `tests/contract/test_pending_import_file_contract.py`
  for `PendingImportStore(root)` in `src/services/enrichment.py`, per
  `contracts/pending-import-file.md`. Use `tmp_path` and an `Account`.
  - **Round trip**: `save(account, pending)` then `load(account)`
    round-trips every field of the `PendingImport` and `ImportItem`s.
    The file is at `root/<username>/.pending-import.json`, it is valid
    JSON with `"version": 1`, and it contains non-ASCII characters
    literally (`ensure_ascii=False`).
  - **No stored derived fields**: there is no `total`, `done`,
    `enriched_count` or `failed_count` key in the file.
  - **Atomic write**: monkeypatch `os.replace` to raise. The previous file
    content is intact and no `*.tmp` file is left behind.
  - **Restart recovery**: a file with `status: running` and one item
    `enriching` loads as `status == "interrupted"` with that item
    `waiting`, and the file on disk is rewritten to match.
  - **Unreadable file**: `"{"` (invalid JSON) or `"version": 2` loads as
    `None`, and the file is renamed to
    `.pending-import.broken-<timestamp>.json`.
  - **`delete`**: `delete(account)` removes the file. `load` on a missing
    file returns `None`.
  - **Invisibility**: with only a pending file present,
    `WordListStore(root).list(account) == []`, `word_source(account) ==
    "shared"`, and `load_vocabulary(root/username)` returns `([], [])`.
  - **Isolation**: account A's `load` never reads B's file.
- [X] T009 [P] Create `tests/unit/test_pending_import_model.py` for the
  dataclasses in `src/services/enrichment.py`.
  - **Derived properties**:
    - `total` excludes `duplicate` items;
    - `done` counts `enriched` and `failed` items;
    - `enriched_count` and `failed_count` count their states;
    - `savable` lists the items that are `enriched` and not
      `(existing.source == "own" and choice == "keep")`, and also not
      `(existing.source == "own" and choice == "update")`, since updates
      are counted separately;
    - `updates` lists the `enriched` items with `existing.source == "own"`
      and `choice == "update"`.
  - **`to_api()`** returns the Import State shape of
    `contracts/import-api-contract.md`. Each item carries its `index`.
    `upload_skipped` is capped at 20, and `upload_skipped_count` is the
    full count.

### Implementation

- [X] T010 In `src/services/llm_client.py`, add
  `_post_chat(base_url, payload, timeout) -> tuple[str | None, str | None]`.
  It returns `(content, failure)`, where `failure` is one of:
  - `"unavailable"`, for `requests.ConnectionError` or HTTP 404;
  - `"timeout"`, for `requests.Timeout`;
  - `"bad_status"`, for any other non-200;
  - `"bad_body"`, for a missing `message.content`;
  - `"error"`, for any other `requests.RequestException`.

  Make `_post_json` a thin wrapper: `content, _ = _post_chat(...); return
  content`. The behaviour of `request_correction` is unchanged. This makes
  T005 pass, and every existing test in
  `tests/contract/test_ollama_correction_contract.py` must still pass
  unchanged.
- [X] T011 [P] Create `src/lib/alternates.py`, per research R6. It makes
  T006 pass.
  - **`canonical(s)`**:
    1. Lowercase, then remove `-` and spaces.
    2. Apply these rewrites with `re`, in order:
       - `isation→ization`; `ise\b→ize`, plus `ise(?=d\b|s\b|r\b|ing\b)→iz`;
       - `yse→yze`; `our\b`/`our(?=s|ed|ing|ful|ite)→or`;
       - `tre\b→ter`; `ogue\b→og`; `ence\b→ense` (only for
         defence/offence/licence/pretence; keep a small set);
       - `ll(?=ed\b|ing\b|er\b)→l`;
       - `ae→e` and `oe→e`, only when not at the start.
  - **`IRREGULAR_VARIANTS`**: a frozenset of frozenset pairs: tyre/tire,
    grey/gray, aluminium/aluminum, plough/plow, kerb/curb,
    programme/program, cosy/cozy, mould/mold, sceptic/skeptic,
    pyjamas/pajamas, storey/story, moustache/mustache, cheque/check,
    draught/draft, and jewellery/jewelry.
  - **`is_spelling_variant(a, b)`**: `a.casefold() != b.casefold()`, and
    either `canonical(a) == canonical(b)` or the lowercased pair is in
    `IRREGULAR_VARIANTS`.
  - **`filter_alternates(english, supplied, proposed) -> tuple[list[str],
    list[str]]`**: `MAX_ALTERNATES = 5` and `MAX_ALTERNATE_LENGTH = 64`.
  - Add a module docstring citing spec 018 FR-011.
- [X] T012 In `src/services/word_lists.py`, add
  `@dataclass DraftWord(english: str, chinese: str | None, ipa: str |
  None, alternates: list[str], position: str)`, and a keyword parameter
  `require_chinese: bool = True` on `parse_upload`, `_parse_simple` and
  `_parse_markdown`. Makes T003 pass.
  - **Default `True`**: the current code path, byte-for-byte the same
    behaviour.
  - **`False`, simple list**: a line with field 1 present becomes a
    `DraftWord`. Field 2 is the Chinese if it is non-empty and not a
    pronunciation (`_is_pronunciation`). The extras are split as in
    `_simple_item`, reusing its pronunciation-message logic.
  - **`False`, Markdown**: a block needs `english` (a non-empty str).
    `chinese` is taken if it is a non-empty str. `ipa` goes through
    `normalize_ipa`, adding the problem to `skipped` as today.
    `alternates` must be a list of str, or the block is skipped as
    `block N: alternates must be a list of words`. `group` is ignored.
- [X] T013 Create `src/services/enrichment_client.py` with
  `@dataclass EnrichmentReply(outcome: str, ipa: str | None = None,
  ipa_uncertain: bool = False, chinese: str | None = None, alternates:
  list[str] = field(default_factory=list), detail: str | None = None)`,
  plus the module constants `_SYSTEM_PROMPT` and `_RESPONSE_FORMAT`
  (exactly per the contract), and `request_enrichment(...)`. Depends on
  T010; makes T004 pass.
  - Call `llm_client._post_chat`, and map `failure == "unavailable"` to
    `outcome="unavailable"`. Every other failure becomes
    `outcome="bad_reply", detail=failure`.
  - Parse with `llm_client._parse_object_reply(content, required, ...)`
    and type-check `alternates` as a list of str. Any problem becomes
    `bad_reply` with `detail="unusable reply"`.
  - Read only the four keys.
  - Add a module docstring stating that the model never decides the
    English text, names, paths, workflow or persistence (FR-006).
- [X] T014 In `src/services/enrichment.py`, create the data model of
  `data-model.md`. Makes T007 and T009 pass.
  - **`PendingImport`**: `version`, `list_name`, `source_filename`,
    `created_at`, `status`, `failure_reason`, `upload_skipped` and
    `items`.
  - **`ImportItem`**: `english`, `position`, `supplied`, `state`, `ipa`,
    `ipa_review`, `chinese`, `alternates`, `dropped_alternates`, `error`,
    `existing`, `choice` (default `"keep"`) and `duplicate_of`.
  - **Constants**:
    - `STATUSES = ("running", "completed", "partially_failed", "failed",
      "interrupted")`;
    - `ITEM_STATES = ("waiting", "enriching", "enriched", "failed",
      "duplicate")`;
    - `MAX_CHINESE_LENGTH = 40`;
    - `MAX_CHINESE_PARTS = 4`.
  - **Derived properties**: `total`, `done`, `enriched_count`,
    `failed_count`, `savable` and `updates`.
  - **`to_api()`**, plus `to_json()` and `from_json()` that omit the
    derived fields.
  - **`validate_chinese(text)`**, per T007.
- [X] T015 In `src/services/enrichment.py`, add
  `PendingImportStore(root: Path)` with `path(account)`, `load(account) ->
  PendingImport | None`, `save(account, pending)` and `delete(account)`,
  per `contracts/pending-import-file.md`. Depends on T014; makes T008
  pass.
  - `load` applies restart recovery: `running` becomes `interrupted`,
    `enriching` becomes `waiting`, and the file is rewritten.
  - It quarantines unreadable files as `.pending-import.broken-<UTC
    YYYYmmddTHHMMSS>.json`.
  - It writes atomically with `tempfile.NamedTemporaryFile(dir=folder,
    suffix=".tmp", delete=False)` followed by `os.replace`, as
    `WordListStore.save` does.
  - It uses a per-account `threading.Lock`.

**Checkpoint**: the foundational tests pass, `pytest` is fully green, and
nothing user-visible has changed yet.

---

## Phase 3: User Story 1 - Upload bare English words and get them filled in (Priority: P1) 🎯 MVP

**Goal**: picking a file in the existing upload control creates a pending
import, enriches each word through the local model with real progress,
shows a preview, and on Save writes the list in the existing Markdown
format so that it appears in My Word Lists.

**Independent Test**: with a mocked model, `POST /api/word-lists/import`
of `zealous\ntyre\nepitomise\n` returns `202`. After the worker finishes,
`GET /api/word-lists/import` shows 3 enriched items with tyre→`[tire]`.
`POST /confirm` returns `200 {added: 3}`.
`word-lists/<user>/<name>.md` holds 3 blocks in the key order `english,
ipa, alternates, chinese, group`, and `GET /api/word-lists` lists it.

### Tests (write first, confirm they FAIL)

- [X] T016 [P] [US1] Create `tests/unit/test_enrichment_runner.py`,
  covering the happy path of `EnrichmentRunner(pending_store,
  base_url, model, request_fn=request_enrichment)` in
  `src/services/enrichment.py`. Inject a fake `request_fn` that returns
  canned `EnrichmentReply`s.
  - **`start(account) -> threading.Thread | None`** processes the items
    sequentially in file order. Record the call order and the
    `(english, supplied)` arguments.
    - Each item goes `waiting → enriching → enriched`.
    - The pending file is saved after every item. Assert this with a
      spying store: the save count is at least the number of items.
    - The final status is `completed`.
    - `done` counts up by 1 per item. Capture `pending.done` inside the
      fake at each call to get `[0, 1, 2]`.
  - **Supplied values are kept (FR-007)**:
    - An item with supplied `chinese` keeps it verbatim even when the
      reply's `chinese` differs.
    - An item with supplied `chinese` **and** `ipa` makes **no**
      `request_fn` call and is `enriched`.
  - **Model alternates are filtered**: the reply `alternates=["tire",
    "wheel"]` for `tyre` gives `alternates == ["tire"]` and
    `dropped_alternates == ["wheel"]`.
  - **Valid IPA** (`"ˈzeləs"` with `ipa_uncertain=False`) gives
    `ipa == "ˈzeləs"` and `ipa_review is None`.
  - **Malformed IPA**: `normalize_ipa` fails on `"123"`, which gives
    `ipa is None`, `ipa_review == "generated pronunciation was unusable"`
    and `state == "enriched"`. The item does not fail.
  - **Bad Chinese**: the reply's `chinese="hello"` gives
    `state == "failed"` and `error == "meaning was unusable"`.
  - **English stays as uploaded**: the `english` value is never changed,
    even if the fake returns odd data.
  - **`wait(account, timeout)`** joins the worker (a test helper used by
    the web tests).
- [X] T017 [P] [US1] Create `tests/contract/test_import_api_contract.py`
  using the `_make_app` and `_client` pattern of
  `tests/contract/test_word_lists_api_contract.py` (accounts plus a
  store). Patch `src.services.llm_client.requests.post` with a fake that
  returns per-word canned replies keyed on `English: "<w>"` in the user
  message. After each start, call `app.enrichment_runner.wait(account,
  5)`.
  - **Login**: every `/api/word-lists/import*` route without login gives
    `401 {"error": "login required"}`.
  - **`POST /api/word-lists/import`**:
    - no file → `400 "Choose a file to upload."`;
    - `.xlsx` → `415`;
    - over 1 MB → `413`;
    - no English words → `422`, with an error starting `"No words
      found. Put one English word per line"`;
    - more than 5,000 words → `422`;
    - otherwise `202`, with `import.status == "running"`, `total == 3`,
      `list_name == "z-words"` (from `z-words.txt`) and
      `source_filename == "z-words.txt"`.
  - **No word files are written yet**: after a `202`, no `*.md` exists in
    `word-lists/<user>/`, and `GET /api/word-lists` still shows `lists:
    []`.
  - **`GET /api/word-lists/import`**: returns `{"import": null}` with
    nothing pending. After the worker finishes, the status is
    `completed` and the item fields match the contract example's keys
    exactly.
  - **`POST /confirm {}`**:
    - `200` with `{name: "z-words", replaced: false, added: 3,
      updated: 0, left_out: 0, first_list: true, applies_now: true}`;
    - the `.md` file is written with `group: z-words` in every block;
    - `.pending-import.json` is deleted;
    - `GET /api/word-lists` lists `z-words` with `word_count == 3`;
    - `GET /api/state` has `word_source == "own"`.
  - **Second confirm** → `404 {"error": "Nothing to save."}`, and the file
    is unchanged.
  - **Name already exists**:
    - confirm with an existing `z-words` list gives `409 {"exists": true,
      "name": "z-words"}`, and nothing changes;
    - confirm with `{"replace": true}` gives `200 replaced: true`.
  - **`DELETE /api/word-lists/import`** → `200 {"discarded": true}` and
    the file is gone. A second `DELETE` → `404`.
  - **The model never names anything**: with a fake reply that includes
    `"group": "evil"` and `"english": "other"`, the saved block has
    `english: zealous` and `group: z-words`.
- [X] T018 [P] [US1] Append to `tests/contract/test_word_lists_api_contract.py`
  one test confirming that the legacy `POST /api/word-lists` still saves
  immediately and returns `200` with the spec 016 body keys: `name`,
  `replaced`, `added`, `skipped_count`, `skipped`, `first_list` and
  `applies_now`. It must not create `.pending-import.json`.
- [X] T019 [P] [US1] Create `tests/integration/test_import_flow.py`,
  testing the US1 journey end to end with the mocked model:
  1. Upload `z-words.txt` (zealous, tyre, epitomise, tend to).
  2. Wait for the worker.
  3. Check the preview items: tyre `alternates == ["tire"]`, epitomise
     `["epitomize"]`, and `tend to` with IPA `ˈtend tə`.
  4. Confirm.
  5. `POST /api/select {"collection": "z-words"}`, then answer `zealous`.
     The state has `ipa == "ˈzeləs"` (the 017 display path unchanged).

  Also assert that `load_vocabulary(word-lists/<user>)` returns 4 items
  with **0** warnings.
- [X] T020 [P] [US1] In `tests/unit/test_web_static_assets.py`,
  **append** these tests:
  - **Panel markup**: `index.html` `#upload-area` contains
    `id="import-panel"` (hidden), placed after `id="upload-result"`. It
    contains `id="import-status"` with `role="status"` and
    `aria-live="polite"`, `id="import-preview"` and `id="import-actions"`.
  - **Existing controls**: the upload button, input and accept list
    still match the existing regexes.
  - **`app.js`**:
    - it contains `/api/word-lists/import`, `Enriching vocabulary:` and
      `/api/word-lists/import/confirm`;
    - it uses a `<progress>` element (the string `"progress"` in an
      `el(` call or `createElement`);
    - it contains no `%` progress text; assert that `"%"` does not appear
      in the import section, sliced from
      `// --- word-list import (spec 018)` to the next `// ---`;
    - it never uses `innerHTML` in that section.
  - **Hint text**: the `#upload-format-hint` text contains
    `just the English is enough` and still contains `/rɪˈsiːv/`.
  - **`style.css`**: it has `.import-panel`, `.import-preview` and
    `.badge-review` rules.

### Implementation

- [X] T021 [US1] In `src/services/enrichment.py`, implement
  `build_import(list_name, source_filename, parsed: ParsedUpload) ->
  PendingImport`.
  - Items are created in order with `state="waiting"`. `supplied`
    holds only the keys the draft had (`chinese`, `ipa`, `alternates`).
  - Duplicate English within the upload (`strip().casefold()`) gives
    `state="duplicate"` and `duplicate_of=<first index>`.
  - Existing-entry detection is left as a hook argument
    `existing_lookup: Callable[[str], dict | None] = lambda _: None`,
    which is filled in by US3.
  - The initial status is `running`, or `completed` if no item needs the
    model.

  Depends on T012 and T014.
- [X] T022 [US1] In `src/services/enrichment.py`, implement `validate_item(item, reply) -> None`, which mutates the item. It follows `contracts/enrichment-validation.md`:
  - IPA rules **1, 5 and 7 only**. Rules 2, 3, 4 and 6 are added in US4 (T047). Until then, any `normalize_ipa`-valid IPA is accepted.
  - § Chinese, via `validate_chinese`.
  - § Alternates, via `filter_alternates`.

  The final state is `enriched`, or `failed` with `error`. Depends on T011 and T014; makes the validation parts of T016 pass.
- [X] T023 [US1] In `src/services/enrichment.py`, implement
  `EnrichmentRunner`. Depends on T013, T015, T021 and T022; makes T016
  pass.
  - **Constructor**: `__init__(self, pending_store, base_url, model,
    request_fn=request_enrichment)`.
  - **`start(account)`**:
    - It holds a per-account lock.
    - If a worker for the account is alive, it returns `None`.
    - Otherwise it sets the status to `running`, saves, spawns a daemon
      thread `_work(account)`, and returns the thread.
  - **`_work`**: loads the pending import, then for each `waiting`
    item in order:
    1. Check the cancel flag.
    2. Set the item to `enriching` and save.
    3. If both `chinese` and `ipa` were supplied, copy them and skip the
       request.
    4. Otherwise call `request_fn(item.english, item.supplied,
       base_url, model)`, then `validate_item`, then save.
  - **End status**: `completed` if no item failed, otherwise
    `partially_failed`. Unavailable handling is added in US2.
  - **`wait(account, timeout)`** and **`cancel(account)`**.
- [X] T024 [US1] In `src/services/word_lists.py`, add
  `WordListStore.apply_import(account, name, new_items:
  list[VocabularyItem], updates: dict[str, list[tuple[str, dict]]] = {},
  replace=False) -> SaveResult`, per research R8. Depends on T012.
  - It runs under `self._lock(account)`, using the same name resolution
    and `ListExistsError` as `save()`.
  - It renders `new_items` with `_to_markdown(name, ...)`. `updates` is
    a no-op until US3.
  - It writes every target to a temp file first, then backs up each
    existing target to `<file>.bak`, then `os.replace`s each one.
  - On any exception it restores from `.bak`, deletes the temps, and
    re-raises. On success it deletes the `.bak` files.
  - It must **not** change `save()`.
- [X] T025 [US1] In `src/web/app.py`, inside the `if accounts is not None
  and store is not None:` block, add the import routes per
  `contracts/import-api-contract.md`. Depends on T021, T023 and T024;
  makes T017, T018 and T019 pass.
  - **Setup**: `pending_store = PendingImportStore(word_lists_dir)` and
    `app.enrichment_runner = EnrichmentRunner(pending_store,
    app.config["OLLAMA_URL"], app.config["MODEL"])`.
  - **`GET /api/word-lists/import`**.
  - **`POST /api/word-lists/import`**:
    - It parses with `require_chinese=False`, giving the same 400, 413,
      415 and 422 handling as the legacy route. The 422 hint is `"No
      words found. Put one English word per line — or upload a .md
      vocabulary file."`
    - It computes the name with `sanitize_list_name(Path(filename).stem)`.
    - It discards any existing pending import, which is handled fully in
      US2; for now, overwrite.
    - It runs `build_import`, then `pending_store.save`, then
      `runner.start`, and returns `202` with `to_api()`.
  - **`POST /api/word-lists/import/confirm`**:
    1. `404` if there is no pending import, `409` if it is running, and
       `422` if there is nothing to save.
    2. It builds `VocabularyItem(english, chinese, alternates, ipa=ipa)`
       from `pending.savable`. Any `VocabularyItemError` gives `500`
       with no file touched.
    3. It calls `store.apply_import(..., replace=body.get("replace") is
       True)`. `ListExistsError` gives `409 {"exists": true, "name":
       ...}`. An `OSError` gives `500 {"error": "Couldn't save the list;
       nothing was changed."}`.
    4. It deletes the pending file and calls
       `app.session_registry.refresh_vocab(account)`.
    5. It returns the Confirm Result. `left_out` counts the items that
       are not saved and not duplicates.
  - **`DELETE /api/word-lists/import`**: calls `runner.cancel`, then
    `pending_store.delete`; `404` if there is nothing to discard.
  - The legacy routes are left as they are.
- [X] T026 [P] [US1] In `src/web/templates/index.html`, inside
  `#upload-area` directly after `#upload-result`, add:

  ```html
  <section id="import-panel" class="import-panel" hidden>
    <p id="import-status" role="status" aria-live="polite"></p>
    <progress id="import-progress" hidden></progress>
    <div id="import-preview" class="import-preview"></div>
    <div id="import-actions" class="import-actions"></div>
  </section>
  ```

  Change the `#upload-format-hint` text to: `One word per line — just the
  English is enough; meanings and pronunciations are filled in for you to
  review. Or add your own: <code>receive, 收到, /rɪˈsiːv/</code> — or a
  .csv / .md file.` Nothing else in the template changes.
- [X] T027 [US1] In `src/web/static/app.js`, add a section `// --- word-list
  import (spec 018) ---` after the spec 016 upload section. Depends on
  T025 and T026; makes T020 pass.
  - **Upload**: `uploadInput`'s `change` handler now calls
    `startImport(file)`, which posts `FormData` to
    `/api/word-lists/import`. Keep `uploadFile` and its strings, which
    are used by existing tests and the legacy path.
  - **Errors**: `400`, `413`, `415` and `422` go to the existing
    `showUploadResult(...)`.
  - **`renderImport(data.import)`**:
    - **Status line**: per `contracts/import-ui-contract.md` § Status
      line, with `<progress max=total value=done>` while running.
    - **Preview table**: a `<table>` with the header `English | IPA |
      中文 | Alternates | Status`. Rows are built with `el()` only.
      - **IPA**: `/ipa/`, or a `span.badge-review` reading
        "Pronunciation needs review" with `title=ipa_review`.
      - **Alternates**: the kept alternates joined by `, `, or `none`,
        plus `span.text-muted` reading `not used: …` when
        `dropped_alternates` is non-empty.
      - **Status**: the text per state.
    - **Actions**: `Save {savable_count} words` (with ` — {left_out}
      left out` when > 0), and `Discard`.
  - **Polling**: `pollImport()` runs `setTimeout` at 1000 ms while the
    status is `running`.
  - **While running**: `uploadButton`, `emptyUploadButton` and
    `uploadInput` are disabled, and so are the Save and Retry buttons.
  - **Confirm**:
    - `409 exists` → `confirm("Replace your list “${name}”?")`, then
      re-post `{replace: true}`.
    - On success, hide the panel, `await fetchState()`, then call
      `showUploadResult(["Added N words to “name”.", ...])` with the same
      first-list and locked tail lines as spec 016.
  - **Discard**: `confirm("Discard this import? Nothing will be
    saved.")`, then `DELETE`.
  - **On choose-screen render**: when `canUpload`, call `GET
    /api/word-lists/import` and render any pending import.
- [X] T028 [P] [US1] In `src/web/static/style.css`, add `.import-panel`,
  `.import-preview` (a table with `width: 100%`, `border-collapse:
  collapse`, and cell padding `var(--space-2)`), `.import-actions`
  (flex, gap `var(--space-2)`), `.badge-review`, `.badge-existing`,
  `.import-status--error`, and `.import-preview .ipa` (which reuses the
  017 `.ipa` look).
  - At `max-width: 600px`, collapse the table rows into stacked cards:
    `thead` hidden, `tr` as blocks, and `td::before { content:
    attr(data-label) }`. `app.js` must therefore set `data-label` on each
    `td`.
  - Use only the existing tokens.

**Checkpoint**: US1 is fully usable with a running Ollama. Uploading
bare words, then previewing and saving, gives a practicable list. Failure
handling is basic: failed items are visible but can't be retried yet.

---

## Phase 4: User Story 2 - Failures don't lose my upload (Priority: P1)

**Goal**: an unavailable model or a bad reply never loses data. Failed
words are marked and can be retried, singly or all at once. A restart
gives an `interrupted` import that can be resumed. Duplicate batches and
duplicate saves are impossible.

**Independent Test**: with `requests.post` raising `ConnectionError`,
the upload returns `202`. After the worker finishes, the status is
`failed`, `failure_reason` starts with `Local AI unavailable`, every item
is `waiting`, and no `.md` file exists. Make the model available again,
then `POST /retry {}`; the status becomes `completed`.

### Tests (write first, confirm they FAIL)

- [X] T029 [P] [US2] Append to `tests/unit/test_enrichment_runner.py`:
  - **Bad reply**: a `bad_reply` reply for item 2 of 4 gives item 2
    `failed` with `error == "the local AI gave an unusable answer"`.
    Items 1, 3 and 4 are `enriched`, and the status is
    `partially_failed`.
  - **Unavailable at item 3 of 5**: items 1 and 2 are `enriched`, item 3
    is back to `waiting`, items 4 and 5 are `waiting`, and there are no
    further `request_fn` calls after item 3. The status is `failed`, with
    `failure_reason == "Local AI unavailable — start Ollama, then press
    Retry."`.
  - **`retry(account, index=None)`**:
    - It resets every `failed` item to `waiting`, with `error=None`.
    - It keeps `enriched` items untouched; their values are byte-equal
      before and after.
    - It restarts the worker, which only calls `request_fn` for the
      waiting items.
  - **`retry(account, index=i)`**: only item `i` is retried. A non-failed
    `i` raises `ValueError`.
  - **Duplicate start (FR-020)**:
    1. Use a fake `request_fn` that blocks on a `threading.Event`.
    2. `start` returns a thread, and a second `start` or `retry` while it
       is alive returns `None`.
    3. Assert that only one thread made calls.
  - **`cancel`**: during a blocked run, `cancel(account)` followed by
    releasing the event makes the worker stop before the next item,
    without saving it to the store afterwards. Assert that the
    pending-store `save` is not called after cancel.
  - **Interrupted batch**: a pending import loaded as `interrupted`,
    followed by `retry(account)`, resumes from the first `waiting` item.
- [X] T030 [P] [US2] Append to `tests/contract/test_import_api_contract.py`:
  - **`POST /api/word-lists/import/retry`**:
    - `404 "Nothing to retry."` when nothing is pending;
    - `400 "That word can't be retried."` for an out-of-range or
      non-failed `index`;
    - `202` when started;
    - `200` with the current state, and no new thread, while running.
      Use the blocking fake.
  - **Confirm while running** → `409 "Still enriching — wait until it
    finishes."`.
  - **A second pending import**: `POST /import` while one is pending,
    without `discard_pending`, gives `409 {"pending": true, "import":
    {...}}`, and the original is unchanged. With
    `discard_pending=true`, the old worker is cancelled and the new
    import is created.
  - **Partially failed confirm**: confirming with `partially_failed`
    saves only the enriched items. `left_out` equals the failed count,
    and the failed items are not in the `.md` file.
  - **Save failure (FR-015)**: monkeypatch `os.replace` in
    `src.services.word_lists` to raise `OSError` on its second call,
    with an existing own list `unit1.md` that is updated in US3 (or a
    replace target here). The confirm returns `500`, every pre-existing
    `.md` file is byte-identical (compare its sha256 before and after),
    no `.tmp` or `.bak` file is left, and the pending import still
    exists.
  - **Ollama unavailable (SC-004)**: with Ollama down, the existing
    `unit1.md` is byte-identical after an upload and the worker run.
- [X] T031 [P] [US2] Append to `tests/integration/test_import_flow.py`:
  - **Restart simulation**: the upload runs with a blocking fake.
    `create_app(...)` is then called a second time on the same
    `word_lists_dir`, as a new process would. `GET /import` on the new
    app shows `status == "interrupted"` with the correct `done`.
    `POST /retry {}` on the new app completes the import, and the
    confirm saves every word.
  - **Isolation**: account B's `GET /import` is `null` while A has a
    pending import. B's `POST /retry`, `/confirm` and `DELETE` give
    `404` and never touch A's file.
- [X] T032 [P] [US2] In `tests/unit/test_web_static_assets.py`, append: the `app.js` import section contains `Retry failed`, `/api/word-lists/import/retry`, `failure_reason`, `interrupted`, `You have an unfinished import`, and `discard_pending`.

### Implementation

- [X] T033 [US2] In `src/services/enrichment.py`, extend
  `EnrichmentRunner`. Makes T029 pass.
  - **`unavailable` outcome**: reset the current item to `waiting`, set
    `status="failed"` and `failure_reason=UNAVAILABLE_MESSAGE`
    (`"Local AI unavailable — start Ollama, then press Retry."`), save,
    and stop.
  - **`bad_reply`**: `state="failed"`, with `error="the local AI gave
    an unusable answer"`.
  - **Final status**: `failed` if a failure reason is set, otherwise
    `partially_failed` if any item failed, otherwise `completed`.
  - **`retry(account, index=None) -> threading.Thread | None`**:
    - It holds the per-account lock and returns `None` if a worker is
      alive.
    - Otherwise it resets the targeted `failed` items to `waiting`,
      clears `failure_reason`, and calls `start`.
    - It raises `ValueError` for a bad index.
  - **`cancel(account)`**: sets a per-account `threading.Event`.
    `_work` checks it before each item and before each save, and exits
    without saving.
- [X] T034 [US2] In `src/web/app.py`, add `POST
  /api/word-lists/import/retry`, and extend `POST /import` and `POST
  /confirm` per the contract. Depends on T033; makes T030 and T031 pass.
  - **`POST /import`**: `409 {"pending": true, ...}` unless
    `discard_pending == "true"`. When discarding, call
    `runner.cancel(account)`, then `runner.wait(account, 5)`, then
    `pending_store.delete(account)`.
  - **`POST /confirm`**: `409` while running, determined by
    `pending.status == "running"`.
  - **Double-submit safety**: wrap confirm in a per-account lock so that
    a concurrent second confirm sees no pending import. Reuse
    `WordListStore._lock(account)` via a public `store.lock(account)`
    accessor, or keep a separate `threading.Lock` dict in `app.py`.
- [X] T035 [US2] In `src/web/static/app.js`, depends on T034; makes T032
  pass.
  - **Retry controls**:
    - a per-row `Retry` button on failed rows, which posts `{index}`;
    - a `Retry failed` action, shown when `failed_count > 0` or the
      status is `failed` or `interrupted`, which posts `{}`.
  - **Failed status**: show `failure_reason` and `${done} / ${total}
    enriched so far.`, with the class `import-status--error`.
  - **Interrupted status**: text per the UI contract.
  - **Pending conflict**: on `409 {"pending": true}` from the upload, ask
    `confirm("You have an unfinished import of “${source_filename}”.
    Discard it and start this one?")`, then re-post with
    `discard_pending=true`.
  - **Polling**: resume polling after a retry `202`.

**Checkpoint**: US1 and US2 together are the full P1 scope. They are
robust against Ollama being down, bad replies and restarts.

---

## Phase 5: User Story 3 - Words I already have are flagged, not overwritten (Priority: P2)

**Goal**: an existing own-list word is marked, kept by default, and can
be updated on request. A shared-folder match is marked but still included.
Duplicates within the upload are handled.

**Independent Test**: own list `unit1.md` contains `receive`. Upload
`receive` and `zealous`. The preview item `receive` has `existing.source
== "own"`, `existing.list == "unit1"` and `choice == "keep"`. The confirm
gives `added: 1, updated: 0`, and `unit1.md` is byte-identical.

### Tests (write first, confirm they FAIL)

- [X] T036 [P] [US3] Create `tests/unit/test_existing_entries.py` for
  `existing_lookup_for(store, account, shared_dir) -> Callable[[str],
  dict | None]` in `src/services/enrichment.py`.
  - **Own-list match**: with own lists, `Receive ` matches `receive` in
    `unit1.md` and returns `{"source": "own", "list": "unit1", "ipa":
    ..., "chinese": ..., "alternates": [...]}`.
  - **Shared-folder match**: with no own lists, it matches against the
    shared `vocab_dir` and returns `"source": "shared"`. The `list` is
    the block's `group`, or the file stem.
  - **No match**: returns `None`.
  - **Pending file ignored**: the pending file itself is never treated as
    a list.
- [X] T037 [P] [US3] Append to `tests/contract/test_import_api_contract.py`:
  - **`POST /api/word-lists/import/choice`**:
    - `{index, "choice": "update"}` on an own-list match → `200`, and the
      item has `choice == "update"`;
    - on a shared match, a non-match, or with `choice: "maybe"` →
      `400 "That word has no entry to update."`;
    - with no pending import → `404`.
  - **Confirm, default keep**: confirming gives `updated: 0`. `unit1.md`
    is byte-identical (sha256), and the new list doesn't contain
    `receive` (SC-007).
  - **Confirm, update**: with `choice: update`, the confirm gives
    `updated: 1`.
    - In `unit1.md`, the `receive` block has the new `ipa`, `chinese` and
      `alternates`, with the same `english` and `group: unit1`.
    - Every other block in `unit1.md` is equal to its original, comparing
      the parsed YAML dicts. That includes a sibling block carrying an
      invalid `ipa: 42`, which must be preserved verbatim.
  - **Shared-folder match**: the account has no own lists and `receive`
    is in the shared folder. The preview shows `existing.source ==
    "shared"`. The confirm **includes** `receive` in the new list, and
    the shared folder files are byte-identical.
  - **Duplicate in the upload**: an upload with `zealous` twice shows the
    second as `duplicate` with `duplicate_of == 0`, makes only one model
    call, saves only one block, and `total` excludes the duplicate.
- [X] T038 [P] [US3] In `tests/unit/test_web_static_assets.py`, append:
  the `app.js` import section contains `Already in your words`, `Also in
  the shared words`, `Keep mine`, `Update with this`,
  `/api/word-lists/import/choice` and `Repeated — already above`.

### Implementation

- [X] T039 [US3] In `src/services/enrichment.py`, add
  `existing_lookup_for(store, account, shared_dir)`. Makes T036 pass.
  - It uses `store.effective_dir(account, shared_dir)` and
    `store.word_source(account)`.
  - For own lists, it iterates `sorted(folder.glob("*.md"))` with
    `parse_blocks`, keyed by the file stem. For shared, it uses
    `load_vocabulary(shared_dir)`.
  - It builds a dict keyed by `english.strip().casefold()`, where the
    first occurrence wins.
- [X] T040 [US3] Wire up existing entries. Depends on T039; makes T037
  pass.
  - **`build_import`**: call `existing_lookup` per non-duplicate item and
    set `item.existing`.
  - **`savable` and `updates`**: these already follow the data model
    (T014).
  - **`WordListStore.apply_import(updates=...)`**:
    - `updates` maps a list stem to `[(english, {"ipa", "chinese",
      "alternates"})]`.
    - For each listed file, parse its raw blocks with `parse_blocks`.
      For each block whose `english.strip().casefold()` matches, set
      `alternates` and `chinese`. Set `ipa` if it is not None, and
      **remove** `ipa` if the new value is None. Keep every other key.
    - Re-dump all blocks with `yaml.safe_dump(allow_unicode=True,
      sort_keys=False, default_flow_style=False)` in the original key
      order, and add the file to the all-or-nothing write set.
    - Files that are not in `updates` are never opened for writing.
  - **`src/web/app.py`**:
    - add `POST /api/word-lists/import/choice`;
    - `POST /import` passes `existing_lookup_for(store, account,
      vocab_dir)`;
    - `POST /confirm` passes `pending.updates`, grouped by
      `existing["list"]`, and returns `updated=len(pending.updates)`.
- [X] T041 [US3] In `src/web/static/app.js` (with `.badge-existing` in
  `src/web/static/style.css`), depends on T040; makes T038 pass.
  - **Existing badge**: when `item.existing` is set, render it under the
    English cell. The text is `Already in your words (“${list}”)` for an
    own match, or `Also in the shared words` for a shared one.
  - **Stored values**: show a muted line `Now: /ipa/ · chinese ·
    alternates`.
  - **Keep or update**: for an own match, add two radio inputs, `Keep
    mine` (checked when `choice == "keep"`) and `Update with this`.
    Their `change` handler posts to `/api/word-lists/import/choice` and
    re-renders.
  - **Duplicates**: render duplicate rows with the status `Repeated —
    already above`.
  - **Save result**: include `Updated N existing words.` when `updated`
    > 0.

**Checkpoint**: US1, US2 and US3 all work. Existing data is never changed
without the learner choosing to change it.

---

## Phase 6: User Story 4 - Pronunciations I can trust (Priority: P2)

**Goal**: imported IPA is consistently OALD NAmE-style American. Heteronyms
whose meaning isn't given, acronyms, model-unsure words, and IPA that
fails the check are all marked "Pronunciation needs review" with no IPA.

**Independent Test**: upload `record`, `NASA` and `zealous` with a mocked
model that returns `ˈrekərd` for record and `ˈzeləs` for zealous. The result
is: record gets `ipa_review == "pronunciation depends on the meaning"`;
NASA gets `"abbreviation — check how it's said"`; zealous gets
`ipa == "ˈzeləs"`. With the reply for zealous changed to `ˈzɛləs` (`ɛ` is not in the convention), it
gets `ipa_review` starting `generated pronunciation failed check:`.

### Tests (write first, confirm they FAIL)

- [X] T042 [P] [US4] Create `tests/unit/test_american_ipa.py` for
  `check_american_ipa(ipa) -> list[str]` and `is_heteronym(english) ->
  bool` in `src/lib/ipa.py`.
  - **Fixture**: every `tests/fixtures/american_ipa.yml` entry passes
    (returns `[]`), and every `british_counterparts` entry fails.
  - **Specific failures**:
    - `ɡ` vs `g` gives `"use ɡ (U+0261), not g"`;
    - `ɚ`, `ɝ` and `ɾ` are each rejected;
    - `ˈˈzeləs` reports more than one primary stress;
    - `zeləs` (2 syllables) reports no primary stress;
    - `ˈtend tə` passes thanks to the weak form `tə`.
  - **`is_heteronym`**: true for `Record`, ` lead `, `tear`, `wind`,
    `minute`, `present` and `object`; false for `zealous` and `receive`.
    `len(HETERONYMS) >= 40`.
  - **British regression**: every existing assertion about
    `check_british_ipa` still passes. Run `tests/unit/test_ipa.py`
    unchanged.
- [X] T043 [P] [US4] Append to `tests/unit/test_enrichment_validation.py`
  the full IPA rule table, rules 1–7 of `contracts/enrichment-validation.md`,
  in order, via `validate_item` with constructed `EnrichmentReply`s.
  - **Rule 1**: a supplied British IPA `rɪˈsiːv` is kept as is.
  - **Rule 2**: `NASA` and `UK` give `"abbreviation — check how it's
    said"`, even when the reply has a valid IPA.
  - **Rule 3**: `record` with no supplied Chinese gives `"pronunciation
    depends on the meaning"`. `record` with supplied Chinese `"记录"`,
    plus a valid reply IPA, gives the IPA.
  - **Rule 4**: `ipa_uncertain=True` gives `"the local AI wasn't sure"`.
  - **Rules 5 and 6**: the corresponding messages.
  - **Rule 7**: valid → `ipa` is set.
  - **Never fails the item**: in every case `state == "enriched"` when
    the Chinese is valid. The rules never fail the item.
- [X] T044 [P] [US4] Append to `tests/contract/test_import_api_contract.py`:
  - **Review mark in the API**: an item with `ipa_review` is returned
    with `ipa: null`.
  - **Saved without IPA**: after the confirm, its `.md` block has **no**
    `ipa` key, and practicing it shows `state["ipa"] is None` (017
    behaviour).
- [X] T045 [P] [US4] In `tests/unit/test_web_static_assets.py`, append:
  the `app.js` import section contains `Pronunciation needs review`, and
  sets the `title` from `ipa_review`.

### Implementation

- [X] T046 [US4] In `src/lib/ipa.py`, makes T042 pass.
  - **Shared stress helper**: extract the stress checks from
    `check_british_ipa` into `_stress_problems(ipa, unstressed) ->
    list[str]`. `check_british_ipa`'s output must stay identical.
  - **American constants**:
    - `_US_CONSONANTS` = `set("pbtdkɡfvθðszʃʒhmnŋlrjw")`;
    - `_US_VOWELS` = `set("iɪeæʌɑɔʊuəɜao")`; marks `ˈ ˌ ː`, space,
      syllabic U+0329 and flap U+032C;
    - `_US_UNSTRESSED` = `{"tə", "tʊ", "ə", "ən", "ðə", "əv", "fər",
      "frəm", "ənd", "ət", "əz", "ɪn", "ɑn"}`.
  - **`check_american_ipa(ipa)`** reports:
    - `g` → `"use ɡ (U+0261), not g"`;
    - `ɒ`, `əʊ`, `ɪə`, `eə`, `ʊə` or `(r)` → `"British IPA marker: <sym>"`,
      and `ɜː` not followed by `r` → `"British IPA marker: ɜː without r"`;
    - any other symbol outside the allowed set (including `ɚ ɝ ɾ`) →
      `f"not American IPA (OALD NAmE style): {' '.join(bad)}"`;
    - then the stress problems from the helper.
  - **`HETERONYMS`**: a frozenset of at least 40 entries.
  - **`is_heteronym(english)`**: `english.strip().casefold() in
    HETERONYMS`.
  - Update the module docstring to mention spec 018.
- [X] T047 [US4] In `src/services/enrichment.py`, complete
  `validate_item`'s IPA handling in exact rule order 1–7. It uses
  `is_heteronym`, the acronym test `not any(c.islower() for c in
  english)`, `reply.ipa_uncertain`, `normalize_ipa` and
  `check_american_ipa`, with the exact `ipa_review` strings from the
  contract, adding rules 2, 3, 4 and 6 to T022's implementation. Depends
  on T046; makes T043 and T044 pass.
- [X] T048 [US4] In `src/web/static/app.js` (with `.badge-review` in `src/web/static/style.css`), make sure the IPA cell renders `span.badge-review` reading `Pronunciation needs review` with `title = ipa_review`, and renders IPA values as `span.ipa` with `lang="en-US-fonipa"`. Makes T045 pass.

**Checkpoint**: all four user stories are complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T049 [P] Create `src/tools/eval_enrichment.py`
  (`python -m src.tools.eval_enrichment [--model M] [--ollama-url U]
  [--fixture PATH]`), per research R10.
  - It runs every fixture word through `request_enrichment` and
    `validate_item`, the real pipeline.
  - It prints these measures:
    - **IPA**: the exact-match % against the fixture's `ipa`, the flagged
      %, and the wrong-and-unflagged count;
    - **Chinese**: the hit % (any `chinese_any` gloss among the `；`
      parts);
    - **Heteronyms**: the flagged %;
    - **Synonym traps**: the count of forbidden alternates kept, which
      must be 0;
    - **Variants**: the recall %.
  - It exits non-zero if SC-002 or SC-003 thresholds are missed: IPA
    match plus flagged must be ≥ 95% with 0 invalid written, traps must
    be 0, and variants must be ≥ 90%.
  - It is not run by `pytest`.
  - Add `tests/unit/test_eval_enrichment.py`, which runs the tool's
    `main()` against a 3-word fixture with a mocked `requests.post`, and
    asserts the report format and the exit codes.
- [X] T050 [P] In `README.md`, under "### Your own word lists (web UI)",
  add a subsection "#### Automatic meanings and pronunciations (spec
  018)". It covers:
  - bare-word uploads;
  - local-only enrichment through the same Ollama model;
  - the progress, preview, Save, Retry and Discard actions;
  - American IPA for imports, with the existing British IPA unchanged;
  - "Pronunciation needs review";
  - spelling-variant-only alternates;
  - keep or update for existing words;
  - the hidden `.pending-import.json` file;
  - `python -m src.tools.eval_enrichment`.
- [X] T051 [P] In `src/models/vocabulary_item.py`, update only the
  `ipa` comment: "IPA without slashes: British for the shared/017 fill,
  American for spec 018 imports".
- [X] T052 Run `ruff check src tests` and the full `pytest`. Every
  pre-existing test must pass **unchanged** (SC-008). Check this with
  `git diff --stat -- tests/` and confirm that only additions appear in
  pre-existing test files.
- [X] T053 Run `python -m src.tools.eval_enrichment --model qwen3:14b`
  against the local Ollama, and record the report in
  `specs/018-upload-ai-enrichment/eval-report.md`. If thresholds are
  missed, tune `_SYSTEM_PROMPT` in `src/services/enrichment_client.py`
  and re-run. Never loosen the validators to pass.
- [X] T054 Do the visual verification with the `frontend-design` skill's
  `visual-verification.md` recipe. Take desktop and 390 px phone
  screenshots of the import panel in four states: running, partially
  failed, preview with an existing-entry row and a review badge, and
  failed (Ollama down). Confirm that the upload button, the hint
  placement and the "My word lists" section are unchanged from the
  current UI.
- [X] T055 Run the manual scenarios a–j in
  `specs/018-upload-ai-enrichment/quickstart.md` §3 against a real
  Ollama, and tick each one off in that file's table, adding a "Result"
  column.

---

## Phase 8: IPA Source Revision (added 2026-10-03 after T053)

**Why**: T053's real-model evaluation failed SC-002. `qwen3:14b` wrote
well-formed but wrong American IPA for 21 of 50 words, and prompt tuning
only partly helped (eval-report.md). The product owner chose an offline
American dictionary. See research R4 (revised) and
contracts/enrichment-validation.md (revised rules 3–7).

- [X] T056 [P] [US4] Create `tests/unit/test_us_pronunciation.py`, testing
  `lookup_american_ipa` and `arpabet_to_ipa`. It covers 35+ single words
  and 6 phrases in OALD NAmE style, plus:
  - unknown words and phrases;
  - the spelling-variant fallback (epitomise → epitomize);
  - stress-ambiguous entries (research, advertisement) flagged;
  - vowel-only variants using the first entry (either);
  - direct conversions (hour, zero, actual, argue, mobile, London,
    street, extract).

  Every converted value must also pass `check_american_ipa`.
- [X] T057 [US4] Create `src/lib/us_pronunciation.py`: it loads CMUdict
  (from the `cmudict` package's data file, read directly) and converts
  ARPABET to OALD NAmE IPA. The rules are listed in research R4. Add
  `cmudict>=1.0` to `pyproject.toml`. Makes T056 pass. Over the whole
  dictionary, 99.9% of converted entries pass the checker.
- [X] T058 [US4] In `src/lib/ipa.py`, let `ɜː` be followed by a stress mark
  before its `r` (ˌekstrətɜːˈrestriəl). Add a test in
  `tests/unit/test_american_ipa.py`.
- [X] T059 [US4] Change `src/services/enrichment_client.py` to request and
  read only `chinese` and `alternates`. `EnrichmentReply` loses `ipa` and
  `ipa_uncertain`. Update `tests/contract/test_enrichment_llm_contract.py`
  first: the required fields, the system prompt mentions no IPA, and a
  volunteered `ipa` is ignored.
- [X] T060 [US4] In `src/services/enrichment.py`, `_resolve_ipa` follows
  the revised rules 1–7: supplied → abbreviation → heteronym (always) →
  ambiguous → not in the dictionary → check → dictionary value. The
  variants it tries are only the alternates that pass
  `is_spelling_variant`. Alternates are computed before IPA. Update
  `tests/unit/test_enrichment_validation.py` first, and adjust the
  runner, contract and integration tests whose expected IPA now comes
  from the dictionary (receive → `rəˈsiːv`).
- [X] T061 In `src/tools/eval_enrichment.py`, compare IPA modulo
  dictionary conventions: stress-mark placement within a cluster,
  secondary stress, flap, unstressed ɪ/ə, ɑː/ɔː, and syllabic n/l. Also
  accept `ipa_also` variants that Merriam-Webster attests, which were
  added to the fixture for schedule, leisure, resilient and February.
  Covered in `tests/unit/test_eval_enrichment.py`.
- [X] T062 Update `README.md` and the spec documents (spec Assumptions,
  research R3/R4, plan, data-model, the LLM and validation contracts)
  for the dictionary IPA source.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: no dependencies. T001 is needed by T042, and
  T002 by T049.
- **Foundational (T003–T015)**: blocks all stories.
  - The tests T003–T009 run in parallel.
  - T010 comes before T013.
  - T011 and T012 are independent.
  - T014 comes before T015.
- **US1 (T016–T028)**: depends on Foundational.
- **US2 (T029–T035)**: depends on US1's runner (T023) and routes (T025).
- **US3 (T036–T041)**: depends on US1 (build_import, apply_import,
  confirm). It is independent of US2.
- **US4 (T042–T048)**: depends on US1 (validate_item). It is independent
  of US2 and US3.
- **Polish (T049–T055)**: depends on all stories. T049 needs T013, T022
  and T047.

### User Story Dependencies

```text
Foundational ──► US1 (MVP) ──┬──► US2
                             ├──► US3
                             └──► US4
```

### Within Each Story

1. Tests come first, and must be seen failing.
2. Services (`src/services/enrichment.py`).
3. Store (`src/services/word_lists.py`).
4. Routes (`src/web/app.py`).
5. Template.
6. `app.js` and `style.css`.

`src/services/enrichment.py` and `src/web/app.py` are edited by many
tasks, so those tasks are sequential.

---

## Parallel Examples

```bash
# Foundational tests, all different files:
T003 test_word_list_parsing.py  |  T004 test_enrichment_llm_contract.py  |  T005 test_ollama_correction_contract.py
T006 test_alternates.py         |  T007 test_enrichment_validation.py    |  T008 test_pending_import_file_contract.py
T009 test_pending_import_model.py

# Foundational implementation that is independent:
T011 src/lib/alternates.py  |  T012 src/services/word_lists.py  |  T010 → T013 llm_client / enrichment_client

# US1 tests:
T016 test_enrichment_runner.py | T017 test_import_api_contract.py | T018 legacy regression | T019 test_import_flow.py | T020 static assets

# After US1, the three remaining stories touch mostly separate concerns:
US2 (runner failure paths) | US3 (existing lookup + apply_import updates) | US4 (src/lib/ipa.py American checker)
#   but all three edit src/services/enrichment.py, src/web/app.py and app.js, so merge them in sequence.
```

---

## Implementation Strategy

### MVP (US1 only)

Do Setup, then Foundational, then US1. With Ollama running, the learner
can upload bare words, preview them and save. This is already valuable,
but failure recovery is minimal, so **do not release without US2**
(both are P1).

### Incremental Delivery

1. US1 + US2: the full P1 scope. It is functional, but any
   `normalize_ipa`-valid IPA is accepted until US4 lands.
   *(Superseded by Phase 8: IPA no longer comes from the model.)*
2. US4 next: recommended before real use, because it closes the gap where
   British or ill-formed IPA from the model can be saved
   (Constitution II).
3. US3: protects curated existing entries. Until it lands, duplicate
   words are simply added to the new list, as spec 016 does today.
4. Polish: the evaluation report (T053) is the **release gate** for
   Constitution II and SC-002/SC-003.

---

## Notes

- Never edit an existing test's body. Only append new test functions or
  create new files (SC-008).
- The model's reply is untrusted everywhere. Only `validate_item` turns
  it into item fields, and confirm validates again before writing.
- Commit after each phase checkpoint.
