---

description: "Task list for 017-vocabulary-ipa"
---

# Tasks: IPA Pronunciation for Vocabulary

**Input**: Design documents from `/specs/017-vocabulary-ipa/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED. Constitution Principle I (Test-First, NON-NEGOTIABLE) applies. Every test task is written and **seen failing for the right reason** before its implementation task starts.

**Organization**: by spec.md user stories:
- **US1 (P1)**: see the pronunciation once the answer is revealed.
- **US2 (P1)**: every existing word gets a correct British IPA.
- **US3 (P2)**: new words, including uploads, can carry a pronunciation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: US1, US2, US3. Setup, Foundational and Polish tasks have no story label.

## Path Conventions

Single project.

- **New source**: `src/lib/ipa.py`, `src/tools/__init__.py`, `src/tools/add_ipa.py`.
- **Changed source**: `src/models/vocabulary_item.py`, `src/services/vocabulary_loader.py`, `src/services/word_lists.py`, `src/web/session_state.py`, `src/cli/session.py`, `src/web/templates/index.html`, `src/web/static/app.js`, `src/web/static/style.css`, `.gitignore`, `README.md`.
- **Data**: `vocabulary/*.md` and `word-lists/zhoudan/*.md` are local gitignored learner data; `design/fixtures/vocabulary/sample.md` is committed.
- **Not touched**: `src/services/{matcher,llm_client,progress_log,accounts}.py`, `src/web/app.py` routes, and the spec 015/016 session and account logic.
- Existing tests only get new test functions added.

---

## Phase 1: Setup

- [X] T001 [P] In `.gitignore`, under "# Local runtime data", add `/backups/` (holds IPA fill backups, the mapping and REVIEW.md, which contain learner word lists).
- [X] T002 [P] Create `src/tools/__init__.py` with a one-line docstring: `"""Maintenance tools run with python -m (spec 017)."""`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the IPA value rules and the `ipa` field on `VocabularyItem`. Display (US1), fill (US2) and uploads (US3) all need them.

### Tests (write first, confirm they FAIL)

- [X] T003 [P] Create `tests/unit/test_ipa.py` for `normalize_ipa(raw) -> tuple[str | None, str | None]` and `display_ipa(ipa: str | None) -> str` in `src/lib/ipa.py`, per `data-model.md` § "IPA value rules":
  - `None` → `(None, None)`;
  - `"rɪˈsiːv"`, `"/rɪˈsiːv/"`, `"[rɪˈsiːv]"` and `"  /rɪˈsiːv/ "` → `("rɪˈsiːv", None)`;
  - `"ˈtend tə"` keeps its inner space;
  - **invalid**, giving `(None, <problem>)` where the problem contains `is not a pronunciation`: the integer `123`, `""`, `"//"`, `"123"`, `"/12ə/"` (an ASCII digit), `"ˈː"` (no letter), and `"a" * 101`;
  - the problem message quotes the raw value (`ipa "123"`);
  - `display_ipa("rɪˈsiːv") == "/rɪˈsiːv/"` and `display_ipa(None) == ""`.
- [X] T004 [P] In `tests/unit/test_models_vocabulary_item.py`, add tests:
  - `VocabularyItem(english="receive", chinese="收到")` has `ipa is None` and `ipa_problem is None`;
  - `from_block({"english": "receive", "chinese": "收到", "ipa": "/rɪˈsiːv/"})` has `.ipa == "rɪˈsiːv"`;
  - `from_block({..., "ipa": 42})` still returns an item, with `.ipa is None` and `"is not a pronunciation" in item.ipa_problem`;
  - `accepted_expressions()` is unchanged by `ipa`;
  - two items differing only in `ipa_problem` compare equal (`compare=False`), and `repr` doesn't include `ipa_problem`.
- [X] T005 [P] In `tests/contract/test_vocabulary_markdown_contract.py`, add tests per `contracts/ipa-field-format.md`. Use a temporary vocabulary dir with three blocks: one with `ipa: rɪˈsiːv`, one with no `ipa`, and one with `ipa: 42`.
  - `load_vocabulary` returns all 3 items, with `ipa` values `"rɪˈsiːv"`, `None` and `None`.
  - Warnings contain exactly one message, matching `<file>: 'bad': ipa "42" is not a pronunciation — shown without one`.
  - A file with no `ipa` anywhere produces **0** warnings (FR-002).
  - An `ipa: on` line loads as the text `"on"` and is valid, since it contains letters (YAML 1.2 loader regression guard).

### Implementation

- [X] T006 [P] Create `src/lib/ipa.py` (module docstring cites spec 017, data-model.md). Makes T003 pass.
  - **Constants**: `MAX_IPA_LENGTH = 100`.
  - **`normalize_ipa(raw)`**:
    - `None` → `(None, None)`;
    - a non-`str` value → problem;
    - otherwise `s = raw.strip()`, then strip one surrounding pair of `/…/` or `[…]`, then `strip()` again;
    - invalid (`not s`, `len(s) > MAX_IPA_LENGTH`, `any(c.isascii() and c.isdigit() for c in s)`, or `not any(c.isalpha() for c in s)`) → `(None, f'ipa "{raw}" is not a pronunciation')`;
    - valid → `(s, None)`.
  - **`display_ipa(ipa)`**: `f"/{ipa}/" if ipa else ""`.
- [X] T007 In `src/models/vocabulary_item.py`, depends on T006; makes T004 pass:
  - add `ipa: str | None = None` and `ipa_problem: str | None = field(default=None, compare=False, repr=False)`;
  - in `from_block`, call `ipa, problem = normalize_ipa(block.get("ipa"))` and pass `ipa=ipa, ipa_problem=problem`;
  - `__post_init__` accepts `ipa` as `None` or `str`.
- [X] T008 In `src/services/vocabulary_loader.py`, after appending an item, if `item.ipa_problem`, append the warning `f"{md_file.name}: '{item.english}': {item.ipa_problem} — shown without one"`. Depends on T007; makes T005 pass.

**Checkpoint**: the foundational tests pass, and the full suite still passes. Nothing is visible yet.

---

## Phase 3: User Story 1 - See the pronunciation once a word is revealed (Priority: P1) 🎯 MVP

**Goal**: IPA appears as `/…/` after the answer is revealed (correct, wrong or "Show answer"), and on the sentence and feedback steps, in the web UI and the CLI. It never appears during recall.

**Independent Test**: with a vocabulary item that has `ipa: rɪˈsiːv`, `GET /api/state` at `recall` has no `ipa` key. After a wrong answer, `state["ipa"] == "rɪˈsiːv"`. In the CLI, `run_recall_step` prints `Pronunciation: /rɪˈsiːv/` only after the answer.

### Tests (write first, confirm they FAIL)

- [X] T009 [P] [US1] In `tests/unit/test_session_state.py`, add tests per `contracts/ipa-display-contract.md`. Use a vocab file whose first block has `ipa: rɪˈsiːv` and whose second has none.
  - At `recall`, `"ipa" not in session.state()` and `"rɪˈsiːv" not in str(session.state())`.
  - After `submit_answer("receive")` in sentence mode (step `sentence`), `state()["ipa"] == "rɪˈsiːv"`. After `submit_sentence` with a patched `request_correction` (step `feedback`), it's the same.
  - In recall-only mode, a wrong answer (step `reveal`) also has `state()["ipa"] == "rɪˈsiːv"`.
  - For the second word (no IPA) at `reveal`, `state()["ipa"] is None`.
  - At `choose`, `complete` and `empty`, there is no `ipa` key.
- [X] T010 [P] [US1] Create `tests/integration/test_ipa_flow.py` with these tests. Reuse the `_make_client` pattern of `tests/integration/test_web_session_flow.py` (no accounts; legacy mode is fine for display).
  - **(a) Web reveal flow**: `GET /api/state` at recall has no `ipa`. `POST /api/answer {"answer": "wrong"}`, then `GET /api/state`, gives `ipa == "rɪˈsiːv"`.
  - **(b) CLI pronunciation line**: `run_recall_step(VocabularyItem("receive", "收到", ipa="rɪˈsiːv"), answer_input=lambda: "x")`. Using `capsys`, the first output line (the meaning line) has no `/rɪˈsiːv/`, and the output contains the line `Pronunciation: /rɪˈsiːv/`.
  - **(c) CLI without IPA**: an item without `ipa` prints no `Pronunciation:` line.
  - **(d) Sentence prompt**: `run_sentence_step("receive", sentence_input=lambda: "", ipa="rɪˈsiːv", ...)`, with `request_correction` patched in `src.cli.session` to avoid Ollama, prints `Write a sentence using "receive" /rɪˈsiːv/:`. Without `ipa`, the prompt is exactly as today.
  - **(e) `run_session` passes the IPA**: monkeypatch `run_sentence_step` to capture its kwargs and assert `ipa == item.ipa`.
- [X] T011 [P] [US1] In `tests/unit/test_web_static_assets.py`, add assertions:
  - `index.html` `#sentence-view` contains `id="target-ipa"` with `class="ipa"` and `lang="en-GB-fonipa"`;
  - `app.js` contains `state.ipa`, the string `"ipa"` used as a class name, and `en-GB-fonipa`;
  - `app.js` references `state.ipa` inside `renderRecallResult`, `renderSentence` and `renderFeedback`. Slice each function's body from `function renderX(` to the next `\n  function ` and assert `state.ipa` is in each;
  - `style.css` has a `.ipa` rule.

### Implementation

- [X] T012 [US1] In `src/web/session_state.py`, in `state()`, inside the existing `if self.step in ("sentence", "feedback", "reveal"):` block, add `base["ipa"] = item.ipa`. Change nothing else. Depends on T007; makes T009 and T010(a) pass.
- [X] T013 [US1] In `src/cli/session.py`, depends on T006 and T007; makes T010(b–e) pass.
  - **`run_recall_step`**: after the existing Correct/Incorrect print, add `if item.ipa: console.print(f"Pronunciation: {display_ipa(item.ipa)}")`.
  - **`run_sentence_step`**: add a keyword parameter `ipa: str | None = None`. The prompt becomes `f'Write a sentence using "[bold]{target_expression}[/bold]" {display_ipa(ipa)}:'` when `ipa` is set, and is unchanged otherwise.
  - **`run_session`**: pass `ipa=item.ipa` to `run_sentence_step`.
- [X] T014 [P] [US1] In `src/web/templates/index.html`, inside `.target-row` after the `h1.target-slot`, add `<span id="target-ipa" class="ipa" lang="en-GB-fonipa"></span>`.
- [X] T015 [US1] In `src/web/static/app.js`, depends on T012 and T014; makes T011 pass.
  - **Helper**: add `ipaEl(ipa)`, which returns `el("span", "ipa", \`/${ipa}/\`)` with `lang="en-GB-fonipa"`, or `null` when `!ipa`.
  - **`renderRecallResult`, correct answer**: append `ipaEl(state.ipa)` after the stamp, when it isn't `null`.
  - **`renderRecallResult`, wrong answer**: append it inside `.answer-reveal` right after the `.answer-text` span.
  - **`renderSentence`**: set `#target-ipa` text to `/${state.ipa}/`, or `""` when `null`.
  - **`renderFeedback`**: append `ipaEl(state.ipa)` to `.feedback-head` after the `h2`.
  - **Safety**: never use `innerHTML`.
- [X] T016 [P] [US1] In `src/web/static/style.css`, add `.ipa` with `font-family: var(--font-body)`, `font-style: normal`, `color: var(--color-muted)`, `font-size: 0.6em` (inside headings) and `white-space: nowrap`. Add `.word-feedback > .ipa, .answer-reveal .ipa { display: block; font-size: 20px; margin-top: var(--space-1); }` and `.target-row .ipa { font-size: 22px; }`. At ≤600px, make `.target-row .ipa` and `.feedback-head .ipa` `display: block`. Use existing tokens only.

**Checkpoint**: words that have IPA show it after reveal, on the web and in the CLI. US1 passes on its own; use the committed fixture after T024, or any file with `ipa:` lines.

---

## Phase 4: User Story 2 - Fill every existing word with British IPA (Priority: P1)

**Goal**: all 233 existing words (182 in `vocabulary/`, 47 in `word-lists/zhoudan/`, and 4 in `design/fixtures/vocabulary/`) get British IPA. The only change is the inserted `ipa:` lines. A `REVIEW.md` with a 30-word spot-check sample is produced.

**Independent Test**: the tool's dry run reports `missing 0`. After the real run, `grep -c '^ipa:'` counts match, `git diff --no-index` against the backups shows only `+ipa:` lines, a second run reports everything as `already had`, and the app loads every file with 0 warnings.

### Tests (write first, confirm they FAIL)

- [X] T017 [P] [US2] In `tests/unit/test_ipa.py`, add tests for `check_british_ipa(ipa: str) -> list[str]`, which returns problems with an empty list meaning OK, per research R6:
  - **valid**, returning `[]`: `rɪˈsiːv`, `ˈteɪbl̩` (syllabic mark), `ˈtend tə`, `ˌɪmprəvaɪˈzeɪʃn̩`, `ˈwæɡən`, `bʌlk`, `ˈpɪtʃə`, `dɪˈspjuːt`, `ˈskænti`, `ˈrɪvə`, `ˈdʒɜːni`, `braɪt`, `ˈpeɪʃnt`, `tə(r)` with an optional sound;
  - **invalid characters**: an American `ɚ` (`ˈrɪvɚ`), `oʊ` (`ˈsoʊ`), `ɹ`, and ASCII `g` (`ˈwægən`), whose message mentions `ɡ`;
  - **stress**: a missing primary stress on a 2+ syllable word (`rɪsiːv`); two `ˈ` in one word (`ˈrɪˈsiːv`); a one-syllable word without stress (`bʌlk`) is OK;
  - **rhotic `r`**: `r` before a consonant (`ˈwɔːrm`) or at the end of a word (`ˈrɪvər`) is a problem;
  - **phrases**: in `tend tə`, each word is checked separately; function-word syllables (`tə`) need no stress, but the phrase needs at least one `ˈ`.
- [X] T018 [P] [US2] Create `tests/unit/test_add_ipa_tool.py` for `src/tools/add_ipa.py`, per `contracts/add-ipa-tool-contract.md`. Use tmp files that copy the real file style: `alternates: []`, `alternates:\n- argument` and quoted values. Call `main(argv)` and `capsys`.
  - **(a) Inserting**: the line `ipa: <value>` is inserted right after `english:` in each mapped block, and the edited file equals the original with exactly those lines inserted. Compare `difflib.ndiff` lines: only `+ ipa:` additions.
  - **(b) Existing IPA**: a block that already has `ipa:` is left alone and counted as `already had`.
  - **(c) Empty mapping IPA**: no line is inserted, the word is counted as `left empty`, and its note appears in REVIEW.md.
  - **(d) Not in the mapping**: the block is counted as `missing from mapping`.
  - **(e) Validation failure**: one invalid mapping value, e.g. `ˈrɪvɚ`, gives exit code `1` and an output line naming the file and word. **No** file changes and no backup directory is created.
  - **(f) Dry run**: `--dry-run` writes nothing and prints the same counts.
  - **(g) Backups**: a real run creates `<backup-root>/ipa-*/files/<relative path>` byte-identical to the originals, plus `REVIEW.md` and `mapping.tsv`.
  - **(h) Running twice**: the second run changes nothing (no new backup files are written for unchanged files) and reports everything as `already had`.
  - **(i) Restore on failure**: monkeypatch the verify step to report a mismatch. The original file content is restored, and the exit code is `1`.
  - **(j) Reloading**: after a run, `load_vocabulary` on the folder returns the same `english`/`chinese`/`alternates`/`group` for every block, with `ipa` set, and 0 warnings.
  - **(k) REVIEW.md**: contains a `Spot check` section with `min(30, filled)` rows.

### Implementation

- [X] T019 [US2] In `src/lib/ipa.py`, add `check_british_ipa(ipa) -> list[str]`, implementing research R6 (a)–(d). Makes T017 pass. Define:
  - `ALLOWED = set("pbtdkɡfvθðszʃʒhmnŋlrjw" + "iɪeæʌɒɔʊuəɑɜa" + "ˈˌː()") | {" ", "̩"}`;
  - `VOWELS = set("iɪeæʌɒɔʊuəɑɜa")`.

  Then:
  - **(a)**: any char not in `ALLOWED` is a problem; ASCII `g` → "use ɡ (U+0261), not g".
  - **(b)**: per word (split on spaces), count syllables as runs of vowel symbols, plus syllabic consonants marked `̩`. A word with ≥2 syllables needs exactly one `ˈ`, unless it is one of the unstressed function forms `{"tə", "tʊ", "ə", "ən", "ðə", "əv", "fə", "frəm"}`. The whole value needs at least one `ˈ` if it has ≥2 syllables in total. More than one `ˈ` in a single word is a problem.
  - **(c)**: every `r` must be followed by a vowel char; otherwise "non-rhotic British IPA: no r before a consonant or at the end".
- [X] T020 [US2] Create `src/tools/add_ipa.py` with `main(argv: list[str] | None = None) -> int` and `if __name__ == "__main__": raise SystemExit(main())`. Implement `contracts/add-ipa-tool-contract.md`. Depends on T008 and T019; makes T018 pass.
  - **Parsing**: read the mapping as tab-separated, 4 columns (note optional), with `#` and blank lines ignored, keyed by `(file, english)`. Validate every non-empty IPA with `normalize_ipa` and then `check_british_ipa`, and print all failures before exiting `1`.
  - **Editing**: work line by line on each file's text, keeping its line endings. Track whether you're inside a `---` block. On an `english:` line inside a block, look ahead to the closing `---` to see whether the block already has an `ipa:` line. Recover the English value by YAML-loading that single line (`yaml.load(line, Loader=_BlockLoader)`, imported from `src.lib.markdown_blocks`), so quoted values match.
  - **Backups**: name the folder `ipa-%Y%m%d-%H%M%S`, and copy files with `shutil.copy2`. Write files atomically.
  - **Verify**: compare `[(i.english, i.chinese, i.alternates, i.group) for i in load_vocabulary-per-file]` before and after, plus the warning counts. On any mismatch, restore from the backup.
  - **REVIEW.md**: write counts, the full table, the empty words with notes, and a `## Spot check (30)` table sampled with `random.Random(timestamp).sample`.
  - **Summary line**: `filled N · already had N · left empty N · missing from mapping N — review: <path>`.
- [X] T021 [US2] **Data task (pedagogical content)**: write `backups/ipa-mapping.tsv`.
  - **Coverage**: one line for every block in `vocabulary/T_words.md`, `vocabulary/U_words.md`, `vocabulary/V_words.md`, `vocabulary/W-Z_words.md`, `word-lists/zhoudan/dan_words_list.md` and `design/fixtures/vocabulary/sample.md`. Generate the `(file, english, chinese)` list from the files with a short script first, so none is missed.
  - **Style**: British IPA in Oxford/Cambridge learner's-dictionary style, following research R5's rules:
    - RP vowels and non-rhotic forms, with `ˈ` and `ˌ` stress and `ː` length;
    - syllabic `n̩` and `l̩` only where the dictionaries use them;
    - homographs follow the Chinese meaning;
    - noun/verb stress pairs follow the first-listed Chinese sense, with a note;
    - phrases are transcribed word by word, with weak forms for function words (`tə`).
  - **Uncertain words** get an empty IPA and a note, never a guess.
  - **Check**: run the tool with `--dry-run` until it reports `missing from mapping 0` and no validation errors. `vocabulary/` and `word-lists/` are not in git, so read them directly.
- [X] T022 [US2] Run `.venv/bin/python -m src.tools.add_ipa --mapping backups/ipa-mapping.tsv vocabulary/*.md word-lists/zhoudan/*.md design/fixtures/vocabulary/*.md`. Then:
  - confirm the summary: `filled + left empty == 233`, `missing 0`, and at least 98% filled (SC-001);
  - run `git diff --no-index` against `backups/ipa-*/files/...` to confirm only `+ipa:` lines were added;
  - run it again to confirm everything is `already had`;
  - run `load_vocabulary` on each folder to confirm 0 warnings (SC-005).
- [X] T023 [US2] Self-review pass on `backups/ipa-*/REVIEW.md`: re-read every filled word against its Chinese meaning, specifically for homographs, noun/verb stress pairs and the British forms of US-variant spellings (e.g. `waggon`/`wagon`). Fix any errors in the mapping, then re-run the tool on a fresh copy restored from the backup, or edit the specific `ipa:` lines and re-verify. Record in REVIEW.md that the 30-word dictionary spot check (SC-002) is **for the user**.
- [X] T024 [P] [US2] Confirm `design/fixtures/vocabulary/sample.md` (committed) now has `ipa:` lines from T022, so screenshots show the feature. Then run `git diff design/fixtures`, which should show only `+ipa:` lines.

**Checkpoint**: every existing word has IPA or is listed with a reason. Practising with real data shows the pronunciations.

---

## Phase 5: User Story 3 - New words can carry a pronunciation (Priority: P2)

**Goal**: uploads accept an `ipa` key in `.md` files and a `/…/` column in simple lists, saved lists keep it, and the upload hint mentions it. Nothing is filled automatically (FR-010).

**Independent Test**: upload `receive, 收到, /rɪˈsiːv/, accept` and `bad, 坏, /123/`. The result is 2 added, with the skip message `line 2: "/123/" is not a pronunciation`. The saved file has `ipa: rɪˈsiːv` after `english`, `alternates == ["accept"]`, and revealing the word shows the IPA.

### Tests (write first, confirm they FAIL)

- [X] T025 [P] [US3] In `tests/unit/test_word_list_parsing.py`, add tests per `contracts/ipa-field-format.md`:
  - `receive, 收到, /rɪˈsiːv/, accept` gives `ipa == "rɪˈsiːv"` and `alternates == ["accept"]`;
  - a pronunciation in any position after field 2 works: `receive, 收到, accept, [rɪˈsiːv]`;
  - tabs work;
  - two pronunciation fields on one line keep the first and add the skip message `line N: more than one pronunciation — kept the first`, with the item still added;
  - `/123/` gives `ipa is None` and the skip message `line N: "/123/" is not a pronunciation`, with the item still added;
  - a `.md` upload with `ipa: 42` gives an item with no IPA and a skip message starting `block 1:` that contains `is not a pronunciation`;
  - no line without slashes gains an IPA (no automatic filling, FR-010).
- [X] T026 [P] [US3] In `tests/unit/test_word_list_store.py`, add a test: saving an item with `ipa="rɪˈsiːv"` writes `ipa: rɪˈsiːv` on the line right after `english:`; `load_vocabulary` reads it back; and an item without IPA writes no `ipa:` key.
- [X] T027 [P] [US3] In `tests/unit/test_web_static_assets.py`, assert that the `#upload-format-hint` text contains `/rɪˈsiːv/`.

### Implementation

- [X] T028 [US3] In `src/services/word_lists.py`, depends on T007; makes T025 and T026 pass.
  - **`_parse_simple`**: among `fields[2:]`, treat fields matching `^/.*/$` or `^\[.*\]$` as pronunciation candidates. Take the first one and run it through `normalize_ipa`; an invalid value adds the skip message `line N: "<raw>" is not a pronunciation`. Extra candidates add `line N: more than one pronunciation — kept the first`. The remaining fields are alternates.
  - **`_parse_markdown`**: when `item.ipa_problem` is set, add `block N: <problem>`, but keep the item.
  - **`_to_markdown`**: write keys in the order `english`, `ipa` (only if set), `alternates`, `chinese`, `group`.
- [X] T029 [P] [US3] In `src/web/templates/index.html`, set the `#upload-format-hint` text to `One word per line: <code>receive, 收到</code> — add <code>/rɪˈsiːv/</code> for the pronunciation — or a .csv / .md file.`

**Checkpoint**: all three stories work.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T030 [P] Update `README.md`:
  - in "Vocabulary content", add `ipa` to the example block and the field list: optional British IPA, shown only after the answer is revealed;
  - in "Your own word lists", add the `/…/` column to the simple-list example;
  - add a short "Pronunciations (IPA)" note: words added later show IPA only if their file includes it, and `python -m src.tools.add_ipa --mapping … FILES` fills a list from a reviewed mapping, with backups in `backups/`.
- [X] T031 [P] Run `.venv/bin/ruff check .`, and `ruff format` on new files only.
- [X] T032 Run `.venv/bin/pytest -q`. Every pre-existing test must pass unchanged (`git diff tests/` shows only additions).
- [X] T033 Visual check with the `frontend-design` workflow on an isolated instance using the filled `design/fixtures/vocabulary`. Screenshot at 1280 and 390 px: a correct reveal, a wrong reveal, the sentence step and feedback (feedback shows "unavailable" if Ollama is off, which is fine). Check that IPA symbols render (no tofu boxes), the IPA is muted and secondary, and there's no horizontal scroll.
- [ ] T034 Run quickstart.md scenarios 0–6 and report:
  - the fill counts;
  - the list of words left empty, with reasons;
  - the 30-word spot-check sample, which the user checks against a UK learner's dictionary (SC-002).
  - *Status (2026-10-02)*: scenarios 0–6 were run.
    - **Fill**: filled 233, left empty 0, missing 0. All 6 files differ from their backups only by added `ipa:` lines. A second run gives `already had 233`. All folders load with 0 warnings.
    - **Display**: the web state has no `ipa` key during recall; the web UI shows IPA on the wrong-answer reveal, the sentence step and feedback (screenshots in `design/verification/ipa/pass-0/`); the CLI prints `Pronunciation: /…/` after each answer.
    - **Uploads**: the `/…/` column and the invalid-value cases are covered by tests.
    - **Not checked**: the correct-answer reveal (the stamp plus IPA) needs a click, so it wasn't screenshotted; it's covered by the static test.
    - **Still to do by a person**: the 30-word spot check in `backups/ipa-20261002-233232/REVIEW.md` (SC-002).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: none. T001 ∥ T002.
- **Foundational**: T006 → T007 → T008. Blocks every story.
- **US1**: needs Foundational.
- **US2**: needs Foundational, plus T002 (the tools package). Independent of US1 except that the fixtures it fills make US1 visible on screen.
- **US3**: needs Foundational, and touches `word_lists.py` and the template hint. Independent of US1 and US2.
- **Polish**: after all stories.

### Test-before-code pairs

- T003 → T006
- T004 → T007
- T005 → T008
- T009/T010/T011 → T012–T016
- T017 → T019
- T018 → T020
- T025/T026/T027 → T028/T029
- T021 (data) needs T020 (tool) for its dry-run validation.

### Parallel Opportunities

- T003 ∥ T004 ∥ T005, and T006 ∥ the tests.
- T009 ∥ T010 ∥ T011, then T014 ∥ T016 alongside T012/T013.
- T017 ∥ T018.
- T025 ∥ T026 ∥ T027.
- **After Foundational**: the US1, US2 and US3 phases can proceed in parallel. They touch different files, apart from the shared test files and `index.html`, so coordinate those edits.
- T030 ∥ T031.

---

## Parallel Example: User Story 1

```bash
Task: "ipa exposure-by-step tests in tests/unit/test_session_state.py"
Task: "web + CLI reveal flow tests in tests/integration/test_ipa_flow.py"
Task: ".ipa rendering assertions in tests/unit/test_web_static_assets.py"
# then:
Task: "#target-ipa markup in src/web/templates/index.html"
Task: ".ipa styles in src/web/static/style.css"
```

## Parallel Example: User Story 2

```bash
Task: "check_british_ipa tests in tests/unit/test_ipa.py"
Task: "add_ipa tool tests in tests/unit/test_add_ipa_tool.py"
```

---

## Implementation Strategy

### MVP (Phases 1–4: US1 + US2)

Both stories are P1, and together they are the user's request: the field exists, is filled correctly, and is visible. US1 alone shows nothing on real data until US2 fills it, so deliver them together. US3 (uploads) follows.

### Incremental Delivery

1. Setup and Foundational: the field loads, and a bad value only warns.
2. US1: display on the web and in the CLI, validated with the fixture or a hand-added `ipa:`.
3. US2: tool, mapping, fill and review. Validate quickstart scenario 1.
4. US3: upload support. Validate quickstart scenario 5.
5. Polish: README, lint, full regression run, screenshots, quickstart report.

---

## Notes

- The IPA mapping (T021) is language content. Principle II's mitigations are the automated British-IPA checks (T019), leaving uncertain words empty, the self-review (T023), and the **user's** 30-word spot check (T034 / SC-002). Don't claim the IPA is verified beyond what was actually checked.
- `vocabulary/`, `word-lists/` and `backups/` are local and gitignored. Only `design/fixtures/vocabulary/sample.md` and the code are committed.
- IPA never reaches grading: `matcher.grade_answer` and `accepted_expressions()` are unchanged.
