---

description: "Task list for 019-part-of-speech"
---

# Tasks: Part of Speech for Vocabulary

**Input**: design documents from `/specs/019-part-of-speech/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ and quickstart.md (all present)

**Tests**: included and REQUIRED, because Constitution Principle I
(Test-First) applies. Write each test task first and see it fail for the
right reason. Existing tests are never edited; new test functions are
only appended or put in new files.

**Organization**: by spec.md user stories:

- **US1 (P1)**: see the part of speech with the meaning (recall, reveal,
  sentence, feedback; web and CLI).
- **US2 (P1)**: new uploads get a part of speech filled in and shown in
  the preview.
- **US3 (P2)**: all about 710 existing words get a part of speech from a
  one-time reviewed fill.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no unmet dependencies).
- **[Story]**: US1–US3. Setup, Foundational and Polish tasks have no
  story label.

## Path Conventions

This is a single project.

- **New source**: `src/lib/pos.py`, `src/tools/add_pos.py`.
- **Changed source**:
  - `src/models/vocabulary_item.py`
  - `src/services/vocabulary_loader.py`
  - `src/services/word_lists.py`
  - `src/services/enrichment_client.py`
  - `src/services/enrichment.py`
  - `src/web/session_state.py`
  - `src/web/static/app.js`
  - `src/web/static/style.css`
  - `src/web/templates/index.html`
  - `src/cli/session.py`
  - `src/tools/eval_enrichment.py`
  - `README.md`
- **Not touched**:
  - `src/services/matcher.py` (grading)
  - `src/services/progress_log.py`
  - `src/lib/ipa.py`
  - `src/lib/us_pronunciation.py`
  - `src/tools/add_ipa.py` (its helpers are only imported)

---

## Phase 1: Setup

- [X] T001 [P] Extend `tests/fixtures/enrichment_eval.yml`, the reviewed
  reference for research R6.
  - Give every `words` entry a `pos` list (the labels that must be
    present) and, where the word is commonly used in another class, a
    `pos_ok` list. For example:
    - zealous `[adj.]`;
    - figure `pos: [n.]`, `pos_ok: [v.]`;
    - forward `pos: [adv.]`, `pos_ok: [adj., v.]`;
    - give up `[phr. v.]`;
    - tend to `pos: [phr. v.]`, `pos_ok: [v., phr.]`.
  - Append at least 10 multi-class words, each with ipa, chinese_any,
    pos and pos_ok: rent `[n., v.]`, record, present, increase, light,
    answer, dance, schedule, contract and project.
  - Update the header comment to cite spec 019 R6 and the date reviewed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the label set and normaliser, and the `pos` field on
`VocabularyItem`. Display (US1), uploads (US2) and the fill (US3) all
need these.

### Tests (write first, confirm they FAIL)

- [X] T002 [P] Create `tests/unit/test_pos.py` for `src/lib/pos.py`,
  following data-model.md and research R2.
  - **Constants**: `POS_LABELS` is exactly the 12 FR-002 labels in this
    order: `n.`, `v.`, `adj.`, `adv.`, `prep.`, `conj.`, `pron.`,
    `det.`, `int.`, `num.`, `phr. v.`, `phr.`. `POS_NAMES["adj."] ==
    "adjective"`, and `POS_NAMES["phr. v."] == "phrasal verb"`.
  - **`normalize_pos(raw) -> (list[str] | None, str | None)`**:
    - `None` → `(None, None)`;
    - `"adj."`, `"Adj"`, `"adjective"` and `"形容词"` → `(["adj."], None)`;
    - `["n.", "v."]`, `"n. v."`, `"n., v."`, `"noun/verb"`, `"名词；动词"`
      and `"n、v"` → `(["n.", "v."], None)`;
    - `"vt."`, `"vi"`, `"及物动词"` → `["v."]`;
    - `"phrasal verb"`, `"phr. v."`, `"phr.v."`, `"短语动词"` →
      `["phr. v."]`;
    - `"idiom"`, `"短语"` → `["phr."]`;
    - `"art."` → `["det."]`;
    - duplicates are removed and order is kept: `"v. n. v."` →
      `["v.", "n."]`;
    - **invalid**, giving `(None, problem)` where the problem contains
      `is not a part of speech` and quotes the raw value: `"verbish"`,
      `""`, `42`, `[]`, `["n.", 3]`, `"n. foo"`.
  - **`is_pos_field(text) -> bool`** (simple lists): true for `"adj."`,
    `"n. v."`, `"noun"`, `"形容词"` and `"phr. v."`; false for `"n"`,
    `"a"`, `"v"`, `"tire"`, `"收到"` and `"/rɪˈsiːv/"`.
  - **`strip_pos_notes(text) -> str`**:
    - `"租金；租用；（动词）出租"` → `"租金；租用；出租"`;
    - `"（名词）记录；(v.) 记录"` → `"记录；记录"`;
    - `"热心的"` is unchanged;
    - `"（动词）"` → `""`;
    - a note made of a non-label word in brackets, such as
      `"（俚语）卑鄙的人"`, is unchanged.
  - **`display_pos(labels) -> str`**: `["n.", "v."]` → `"n. v."`, and
    `[]` → `""`.
- [X] T003 [P] Append to `tests/unit/test_models_vocabulary_item.py`:
  - `VocabularyItem("receive", "收到").pos == []` and its `pos_problem`
    is `None`;
  - `from_block({"english": "rent", "chinese": "租", "pos": "n. v."}).pos
    == ["n.", "v."]`;
  - `from_block({..., "pos": "verbish"})` returns an item with
    `pos == []` and `"is not a part of speech" in item.pos_problem`;
  - items that differ only in `pos_problem` compare equal, and the
    `repr` doesn't include `pos_problem`;
  - `accepted_expressions()` is unaffected by `pos`.
- [X] T004 [P] Append to `tests/contract/test_vocabulary_markdown_contract.py`,
  following `contracts/pos-field-format.md`. Use a temporary vocab dir
  with blocks `pos: [adj.]`, `pos: noun/verb`, no `pos`, and
  `pos: verbish`.
  - `load_vocabulary` returns all 4 items with pos `["adj."]`,
    `["n.", "v."]`, `[]`, `[]`.
  - There is exactly one warning:
    `<file>: 'bad': pos "verbish" is not a part of speech — shown without one`.
  - A file without any `pos` gives 0 warnings.

### Implementation

- [X] T005 Create `src/lib/pos.py`, with a module docstring citing spec
  019 R2. Makes T002 pass.
  - **Constants**: `POS_LABELS` (an ordered tuple) and `POS_NAMES`.
  - **Synonyms**: a private `_SYNONYMS` dict from lowercased,
    dot-stripped token to label. It covers the English abbreviations,
    the full names and the Chinese names in research R2. `phr. v.`,
    `phr.v.` and `phrasal verb` are matched before splitting.
  - **`normalize_pos`**: lists are taken as they are; strings are split
    on `[\s,/;；、]+`, after first protecting multi-word labels.
  - **`is_pos_field`**: every token must be dotted, a full English name
    of length ≥ 4, or a CJK name.
  - **`strip_pos_notes`**: removes `[（(]\s*<any synonym>\s*[）)]`, then
    collapses empty `；` parts and spaces.
  - **`display_pos`**.
- [X] T006 In `src/models/vocabulary_item.py`, add
  `pos: list[str] = field(default_factory=list)` and
  `pos_problem: str | None = field(default=None, compare=False, repr=False)`.
  `from_block` calls `normalize_pos(block.get("pos"))`.
  `__post_init__` requires `pos` to be a list of str. Depends on T005;
  makes T003 pass.
- [X] T007 In `src/services/vocabulary_loader.py`, after the `ipa_problem`
  warning, add:
  `if item.pos_problem: warnings.append(f"{md_file.name}: '{item.english}': {item.pos_problem} — shown without one")`.
  Depends on T006; makes T004 pass.
- [X] T008 In `src/services/word_lists.py` `_to_markdown`, write
  `pos: [..]` as a YAML flow list after `ipa` and before `alternates`,
  only when `item.pos` is non-empty. Use
  `yaml.safe_dump(..., default_flow_style=None)` for that key, or build
  the line by hand as `pos: [n., v.]`. Then append a test to
  `tests/unit/test_word_list_store.py` that round-trips a list with
  `pos=["n.", "v."]` through save → load and checks the key order
  `english, ipa, pos, alternates, chinese, group`. Depends on T006.

**Checkpoint**: `pytest` is fully green. `pos` loads, but isn't shown
yet.

---

## Phase 3: User Story 1 - See whether a word is a verb, adjective, … (Priority: P1) 🎯 MVP

**Goal**: labels appear before the Chinese meaning during recall, on the
reveal, and on the sentence and feedback steps, in the web UI and the
CLI.

**Independent Test**: with a vocab block `pos: [adj.]`,
`GET /api/state` at `recall` has `pos == ["adj."]`. The page shows
*adj.* before 热心的, and the CLI prints
`Chinese meaning: adj. 热心的`.

### Tests (write first, confirm they FAIL)

- [X] T009 [P] [US1] Append to `tests/unit/test_session_state.py`, using a
  vocab file whose first block has `pos: [adj.]` and whose second has no
  `pos`:
  - at `recall`, `state()["pos"] == ["adj."]`;
  - after a wrong answer in recall-only mode (`reveal`), after a correct
    answer in sentence mode (`sentence`), and after `submit_sentence`
    (`feedback`), `pos` is still `["adj."]`;
  - the second word has `pos == []`;
  - at `choose`, `complete` and `empty` there is no `pos` key;
  - grading is unchanged: answering `"adj."` is wrong.
- [X] T010 [P] [US1] Create `tests/integration/test_pos_flow.py`:
  - **(a) Web**: `GET /api/state` at recall includes `pos`, using the
    `_make_client` pattern of `tests/integration/test_ipa_flow.py`.
  - **(b) CLI with labels**: `run_recall_step(VocabularyItem("zealous",
    "热心的", pos=["adj."]), answer_input=lambda: "x")` prints a line
    containing `Chinese meaning: adj. 热心的`. Use `capsys` and strip the
    rich markup by reading the plain output.
  - **(c) CLI without labels**: an item with no pos prints
    `Chinese meaning: 热心的` exactly as before.
- [X] T011 [P] [US1] Append to `tests/unit/test_web_static_assets.py`:
  - `app.js` defines `posList(` and uses it in `renderRecall`,
    `renderSentence` and `renderFeedback` (slice each function body as
    the spec 017 IPA test does);
  - it sets `title` and `aria-label` from `POS_NAMES`;
  - it contains every one of the 12 labels with its full name;
  - it never uses `innerHTML` in `posList`;
  - `style.css` has `.pos-list` and `.pos` rules.

### Implementation

- [X] T012 [US1] In `src/web/session_state.py` `state()`, add
  `base["pos"] = list(item.pos)` right after `base["chinese"] =
  item.chinese`. Change nothing else. Depends on T006; makes T009 and
  T010(a) pass.
- [X] T013 [US1] In `src/cli/session.py` `run_recall_step`, print
  `Chinese meaning: {display_pos(item.pos)} [bold]{item.chinese}[/bold]`
  when `item.pos` is set, and exactly the current line otherwise.
  Depends on T005 and T006; makes T010(b, c) pass.
- [X] T014 [US1] In `src/web/static/app.js`:
  - **Lookup table**: add a `POS_NAMES` object with all 12 labels.
  - **`posList(pos)`**: returns a `span.pos-list` containing one
    `span.pos` per label, each with `title` and `aria-label` set to the
    full name, or returns `null` when the list is empty or missing.
  - **Recall prompt**: `renderMeanings(chinese)` →
    `renderMeanings(chinese, pos)` prepends `posList(pos)` inside
    `#chinese`. Update its callers in `renderRecall` and
    `renderRecallResult` to pass `state.pos`.
  - **Sentence and feedback**: `renderSentence` and `renderFeedback`
    prepend `posList(state.pos)` before the `#target-meaning` text. Use
    `replaceChildren(posList, text node)`, never `innerHTML`.

  Depends on T012; makes T011 pass.
- [X] T015 [P] [US1] In `src/web/static/style.css`, add a section headed
  `/* — part of speech (spec 019) — */`:
  - `.pos-list` with `margin-right: 0.4em` and `white-space: nowrap`;
  - `.pos` with `font-style: italic`, `font-weight: 400`,
    `color: var(--color-accent-700)`, `font-size: 0.55em` inside
    `.meanings`, `font-size: inherit` in `.target-meaning`, and
    `cursor: help`;
  - `.pos + .pos { margin-left: 0.3em; }`;
  - `.meanings .pos-list { vertical-align: 0.35em; }`.

  Use existing tokens only.

**Checkpoint**: a hand-written `pos:` shows everywhere. This is the
deliverable MVP.

---

## Phase 4: User Story 2 - New uploads get their part of speech filled in (Priority: P1)

**Goal**: uploads accept a part of speech supplied in the file, and
enrichment generates one, validated against the fixed set. The preview
shows it, generated meanings lose "（动词）" notes, and "Update with this"
includes `pos`.

**Independent Test**: with the model mocked, uploading `zealous` and
`rent` produces previews with `pos` `["adj."]` and `["n.", "v."]`. After
Save, the `.md` has `pos: [adj.]`. A reply `pos: ["verbish"]` gives
`pos_review`, and the word is still savable.

### Tests (write first, confirm they FAIL)

- [X] T016 [P] [US2] Append to `tests/unit/test_word_list_parsing.py`,
  following `contracts/pos-field-format.md`:
  - **Simple-list drafts**:
    - `"zealous, adj., 热心的"` gives a draft with `pos == ["adj."]` and
      `chinese == "热心的"`;
    - `"rent, 租金；出租, n. v."` gives pos `["n.", "v."]`;
    - `"give up, 放弃, phr. v., /ˌɡɪv ˈʌp/"` gives pos `["phr. v."]` and
      its ipa;
    - `"tyre, 轮胎, n"` gives `alternates == ["n"]` and `pos == []`;
    - two part-of-speech fields give the skip message `line 1: more than
      one part of speech — kept the first`.
  - **Legacy route**: `parse_upload(..., require_chinese=True)` on
    `"receive, v., 收到"` gives a `VocabularyItem` with
    `chinese == "收到"` and `pos == ["v."]`.
  - **Markdown drafts**: a block with `pos: adjective` gives
    `["adj."]`. `pos: verbish` adds `block 1: pos "verbish" is not a
    part of speech` to skipped, and the word is still added.
- [X] T017 [P] [US2] Append to `tests/contract/test_enrichment_llm_contract.py`:
  - `format["required"] == ["chinese", "pos", "alternates"]`;
  - the system prompt contains `pos`, `phr. v.` and `Do not put
    part-of-speech labels inside`;
  - a valid reply with `"pos": ["adj."]` gives `reply.pos == ["adj."]`;
  - `pos` given as a string or with a non-string entry gives
    `bad_reply`.

  Because `_reply()` in that file builds the payload, append a new helper
  rather than editing it; existing assertions on `required` will need
  the new value. If an existing test asserts the old `required` list,
  this task is the one sanctioned edit: update that single expected value
  and note it in the commit message.
- [X] T018 [P] [US2] Append to `tests/unit/test_enrichment_validation.py`,
  following `contracts/enrichment-pos-delta.md`:
  - **Rule 1**: supplied pos `["v."]` is kept even if the reply says
    `["n."]`;
  - **Rule 2**: the reply `["Adjective"]` gives `["adj."]`;
  - **Rule 3**: the replies `[]`, `["verbish"]` and `["n.", "foo"]` each
    give `pos == []` and
    `pos_review == "part of speech needs review"`, with
    `state == "enriched"`;
  - **Note stripping**: `validate_chinese("租金；（动词）出租")` gives
    `("租金；出租", None)`; `validate_chinese("（动词）")` gives
    `(None, "meaning was unusable")`;
  - **Supplied meanings untouched**: a supplied meaning containing
    "（动词）" is kept verbatim.
- [X] T019 [P] [US2] Append to `tests/contract/test_import_api_contract.py`:
  - the fake replies for `zealous` (`["adj."]`) and `rent`
    (`["n.", "v."]`) are added through a new `POS` dict merged into the
    replies inside the new tests; `REPLIES` is not edited;
  - the preview items carry `pos` and `pos_review`;
  - the saved `.md` has `pos` in key order;
  - "Update with this" on an existing own entry replaces its `pos`, and
    empty new labels remove the key;
  - a pending-import file written without `pos` keys still loads.
- [X] T020 [P] [US2] Append to `tests/unit/test_web_static_assets.py`:
  - the import section of `app.js` renders `posList(item.pos)` in the
    中文 cell;
  - it contains `Part of speech needs review` with `title` from
    `item.pos_review`;
  - the `#upload-format-hint` text contains `v.`.

### Implementation

- [X] T021 [US2] In `src/services/word_lists.py`:
  - **DraftWord**: gains `pos: list[str] = field(default_factory=list)`.
  - **Simple lists**: in `_split_extras`, the first field where
    `is_pos_field` is true becomes `pos`. Later ones give the skip
    message. Alternates exclude part-of-speech fields.
  - **Meaning field**: the Chinese meaning is the first field after the
    English word that is neither a pronunciation nor a part of speech.
    This holds for both the draft and the legacy path; return pos on
    `VocabularyItem` too.
  - **Markdown drafts**: read `pos` through `normalize_pos`, with the
    skip message on a problem.
  - **Updated blocks**: `_updated_block` also sets or removes `pos` from
    `fields`.

  Depends on T005 and T006; makes T016 pass.
- [X] T022 [US2] In `src/services/enrichment_client.py`:
  - add `pos` (an array of strings) to `_RESPONSE_FORMAT`, with
    `required = ["chinese", "pos", "alternates"]`;
  - add the prompt lines from `contracts/enrichment-pos-delta.md`;
  - `EnrichmentReply` gains `pos: list[str]`, type-checked like
    `alternates`.

  Makes T017 pass.
- [X] T023 [US2] In `src/services/enrichment.py`:
  - **ImportItem**: gains `pos: list[str] = field(default_factory=list)`
    and `pos_review: str | None = None`. Add them to `to_api()` items and
    to `reset()`.
  - **`build_import`**: puts a draft's pos in `supplied["pos"]`.
  - **`validate_item`**: applies the part-of-speech rules 1–3.
  - **`validate_chinese`**: first applies `strip_pos_notes`, only on the
    generated path. The supplied path never calls it.
  - **Update map**: `update_map()` includes `pos`.
  - **Existing entries**: `_existing_entry` includes `pos`.

  Depends on T021 and T022; makes T018 and T019 pass.
- [X] T024 [US2] In `src/web/static/app.js`, inside the import section:
  - `importChinese(item)` starts with `posList(item.pos)`, or with a
    `span.badge-review` reading "Part of speech needs review" (`title =
    item.pos_review`) when `pos_review` is set;
  - the existing-entry "Now:" line includes the stored pos.

  In `src/web/templates/index.html`, change the hint example to
  `receive, v., 收到, /rɪˈsiːv/`. Depends on T014 and T023; makes T020
  pass.

**Checkpoint**: uploads get labels, and the P1 scope is complete.

---

## Phase 5: User Story 3 - Words I already have get a part of speech (Priority: P2)

**Goal**: every existing word, about 710 of them, is either labelled
from a reviewed mapping or listed with a reason. Nothing else changes.

**Independent Test**: on a temp copy of a vocabulary file, `add_pos`
inserts only `pos:` lines after `ipa:`, or after `english:` when there
is none. It refuses invalid mappings, restores on mismatch, and writes
REVIEW.md.

### Tests (write first, confirm they FAIL)

- [X] T025 [P] [US3] Create `tests/unit/test_add_pos_tool.py`, following
  `contracts/add-pos-tool-contract.md` and modelled on
  `tests/unit/test_add_ipa_tool.py`:
  - **Insert position**: `pos: [adj.]` goes after the `ipa:` line, or
    directly after `english:` when there is no ipa;
  - **Nothing else changes**: the rest of the file is byte-identical;
  - **Already present**: an existing `pos:` is counted as "already" and
    left untouched;
  - **Empty mapping value**: counted as "left empty", with the note shown
    in REVIEW.md;
  - **Missing words**: listed as missing;
  - **Invalid mapping**: a value such as `verbish` exits 1 and writes no
    file;
  - **Dry run**: `--dry-run` writes nothing;
  - **Backups**: written under `pos-<stamp>/files/`;
  - **Restore on mismatch**: monkeypatch the snapshot so a mismatch is
    simulated; every file is restored and the tool exits 1;
  - **REVIEW.md**: contains "Filled", "Left empty" and "Spot check"
    sections.

### Implementation

- [X] T026 [US3] Create `src/tools/add_pos.py`, following the contract.
  - Import `_english_of` and `_write_atomic` from `src.tools.add_ipa`.
    Do not modify `add_ipa`.
  - **Snapshot**: compares `(english, chinese, alternates, group, ipa)`
    and the load-warning count.
  - **Insert**: `pos: [<labels joined ", ">]`.

  Makes T025 pass.
- [X] T027 [US3] Write the reviewed mapping
  `backups/pos-mapping.tsv` (gitignored learner data). It needs one line
  per block in:
  - `vocabulary/*.md`;
  - `word-lists/weibo/*.md`;
  - `word-lists/zhoudan/*.md`;
  - `design/fixtures/vocabulary/sample.md`.

  Classify each word from its **own recorded Chinese meanings**, with
  labels in meaning order. Use `phr. v.` and `phr.` for multi-word
  expressions. Leave a word empty, with a note, when its meanings don't
  settle the class. Generate the skeleton (file, english, chinese)
  with a short script, then fill in the labels by careful review.
- [X] T028 [US3] Run `python -m src.tools.add_pos --mapping
  backups/pos-mapping.tsv --dry-run` over the files from T027 and
  confirm 0 missing. Then run it for real and confirm 0 load warnings.
  `git diff design/fixtures` must show only `pos:` lines. Record the
  totals and the `REVIEW.md` path in `specs/019-part-of-speech/fill-report.md`,
  and present the 30-word spot check to the user (SC-006).

**Checkpoint**: existing words show labels in practice.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 In `src/tools/eval_enrichment.py`, add part-of-speech
  accuracy, as in research R6:
  - a match is all labels in `pos ∪ pos_ok` and at least one in `pos`,
    or a flagged item;
  - report a `Part of speech:` line, plus a count of meanings that still
    contain part-of-speech notes;
  - the PASS condition adds part of speech ≥ 95% and 0 notes left.

  Add tests to `tests/unit/test_eval_enrichment.py`, as new functions
  with their own fixtures.
- [X] T030 Run `python -m src.tools.eval_enrichment --model qwen3:14b` on
  the real local model, and record the result in
  `specs/019-part-of-speech/eval-report.md`. If the part-of-speech gate
  fails, stop and ask the user (plan Risks).
- [X] T031 [P] In `README.md`, add a "Parts of speech" subsection next to
  "Pronunciations (IPA)". It covers:
  - the `pos:` field and the accepted spellings;
  - the simple-list field (`zealous, adj., 热心的`);
  - where the labels show;
  - that upload enrichment fills them in;
  - `python -m src.tools.add_pos`.
- [X] T032 Run `ruff check src tests` and the full `pytest`. Verify with
  `git diff -U0 -- tests/` that pre-existing test bodies only gained
  lines, apart from the one sanctioned edit noted in T017.
- [X] T033 Do visual verification with the `frontend-design` recipe.
  Take 1280 px and 390 px screenshots of the recall prompt with `adj.`,
  the recall prompt with `n. v.`, the sentence step, and the import
  preview with a "Part of speech needs review" badge. Compare them
  against the current UI and fix anything wrong.
- [X] T034 Run the quickstart §4 manual scenarios a–g, and record the
  results in `specs/019-part-of-speech/quickstart.md`.

---

## Phase 7: Separate Part-of-Speech Request (added 2026-10-05 after T030 failed)

**Why**: the combined request over-labelled words (tomato `n. adj.`):
part of speech reached 85%, below the 95% target. It also cost spelling
variants, which fell to 64% against a 90% target. The product owner
chose a separate, stricter request (eval-report.md).

- [X] T035 [US2] In `tests/contract/test_enrichment_llm_contract.py`,
  revert the T017 required-fields edit, so the meaning request is back to
  `["chinese", "alternates"]` and no spec 018 test line stays changed.
  Replace the in-request part-of-speech tests with `request_pos` contract
  tests: shape, the user message carrying the meaning, the prompt rules,
  the reply read, bad types, and unavailable.
- [X] T036 [US2] In `src/services/enrichment_client.py`, restore the
  meaning request (no `pos`), and add `request_pos(english, chinese,
  base_url, model, timeout)` with its own narrow prompt and format.
- [X] T037 [US2] In `src/services/enrichment.py`, add
  `with_pos(item, reply, pos_request_fn, base_url, model)`, called after
  the meaning reply:
  - it is skipped when the upload supplied `pos`, or when the meaning is
    unusable;
  - if the model is unavailable, the word waits;
  - any other failure gives labels `[]`, so the word goes to review.

  `EnrichmentRunner` gains `pos_request_fn` (`None` by default, so spec
  018 runner tests are unaffected), and `src/web/app.py` passes
  `request_pos`. Add runner tests in `tests/unit/test_enrichment_runner.py`.
  The `FakeOllama` helper in `tests/contract/test_import_api_contract.py`
  records part-of-speech requests apart from meaning requests, so the
  existing per-word call counts still hold.
- [X] T038 `src/tools/eval_enrichment.py` uses `with_pos` too.
- [X] T039 Fix the reference data: T001 had split `phr. v.` into
  `[phr., v.]` for 5 phrases in `tests/fixtures/enrichment_eval.yml`.
  Also remove the extra sentence added to the meaning prompt, so it is
  byte-identical to spec 018 again.
- [X] T040 [US2] After the second T030 run reached 88%, the product owner
  chose to keep only the model's first label. In `src/services/enrichment.py`,
  `_resolve_pos` returns `labels[:1]`; supplied labels are kept in full.
  Tests are in `tests/unit/test_enrichment_validation.py`, and the 019
  runner and import tests are updated to match.
- [X] T041 Re-run T030 and record the result in `eval-report.md`. Run 3 reached 93% against the 95% target; the decision is with the product owner.

---

## Dependencies & Execution Order

- **Setup (T001)**: needed only by T029 and T030.
- **Foundational (T002–T008)**: blocks every story.
  - T002–T004 can run in parallel.
  - T005 comes before T006, T006 before T007, and T006 before T008.
- **US1 (T009–T015)**: depends on Foundational. It is the MVP.
- **US2 (T016–T024)**: depends on Foundational, and on T014 (the
  `posList` helper) for T024.
- **US3 (T025–T028)**: depends on Foundational only, so it can run in
  parallel with US1 and US2. T027 and T028 come after T026.
- **Polish (T029–T034)**: T029 and T030 need US2 and T001. T033 and
  T034 need everything.

```text
Foundational ─┬─► US1 (MVP) ──► US2 (T024 needs posList)
              └─► US3 (independent)
```

Within each story: tests, then model and lib changes, then services,
then routes and state, then UI.

## Parallel Examples

```bash
# Foundational tests
T002 tests/unit/test_pos.py | T003 test_models_vocabulary_item.py | T004 test_vocabulary_markdown_contract.py
# US1 tests
T009 test_session_state.py | T010 test_pos_flow.py | T011 test_web_static_assets.py
# US2 tests
T016 parsing | T017 llm contract | T018 validation | T019 import API | T020 static assets
# Across stories, after Foundational
US1 UI work  ||  US3 add_pos tool + mapping
```

## Implementation Strategy

1. **MVP**: Foundational plus US1. Hand-written or uploaded `pos:`
   values show everywhere.
2. **Then US2**: new uploads label themselves, and the model gate
   (T030) runs before relying on them.
3. **Then US3**: the one-time fill of about 710 words, with the user's
   30-word spot check as its release gate.
4. **Then Polish**: README, visual check and manual scenarios. Commit to
   `main` at each checkpoint, when asked.

## Notes

- `pos` must never reach grading (`accepted_expressions`, `matcher`).
- Labels in the model's reply are untrusted. Only `normalize_pos` output
  is stored.
- Learner data files are edited only by `add_pos`, with backups.
