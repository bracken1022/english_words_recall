---

description: "Task list for 021-example-sentence"
---

# Tasks: Example Sentences Instead of Sentence Review

**Input**: design documents from `/specs/021-example-sentence/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ and quickstart.md

**Tests**: included and REQUIRED, under Constitution Principle I.

- **New behaviour**: tests are written first and seen failing.
- **Removed sentence review (justified deviation, plan Complexity
  Tracking)**: tests that pin only removed behaviour are **deleted**.
  Tests that walk through the old sentence step are **rewritten** to
  the example flow. Every such file is listed in T019–T021, and in the
  commit message.

**Organization**:

- **US1 (P1)**: see an example sentence after each answer.
- **US3 (P1)**: sentence review is gone.
- **US2 (P2)**: self-checked sentence recall.

US1 and US3 are done together as one P1 increment, because the new modes
replace the old one.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 [P] Create `tests/fixtures/example_eval.yml`, a reviewed list
  of 50 `{english, chinese, pos}` entries for `eval_examples` (R8):
  - 35 single words, taken from `tests/fixtures/enrichment_eval.yml`
    and its multi-class words (rent, record, light, figure, present…);
  - 10 phrases (give up, tend to, look forward to, take off, make up
    for, …);
  - 5 words with two distinct meanings, each given one meaning only.

  Add a header comment citing spec 021 R8.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the pieces every story needs: word-form matching, the
content filter, the example generator and validator, the example stores,
and the new model fields.

### Tests (write first, confirm they FAIL)

- [X] T002 [P] Create `tests/unit/test_word_forms.py` for
  `contains_form(sentence, english)` in `src/lib/word_forms.py` (R4).
  - **True**:
    - zealous in "She is zealous.";
    - receive in "I received it." and "We are receiving guests.";
    - study in "He studies hard." and "studied";
    - stop in "stopped" and "stopping";
    - make in "making";
    - give up in "They gave it up." and "gave up";
    - tend to in "Prices tend to rise." and "It tends to rain.";
    - take off in "The plane took off.";
    - look forward to in "I'm looking forward to it.";
    - case-insensitive, punctuation ignored: "Rent" in "RENT is due!".
  - **False**:
    - zealous in "She is zeal.";
    - rent in "parent" (a token match only, not a substring);
    - give up when the words are more than 2 apart ("give the old man a
      chance to get up");
    - an empty sentence.
  - `IRREGULAR_VERBS` has at least 120 entries.
- [X] T003 [P] Create `tests/unit/test_content_filter.py` for
  `is_clean(text)` in `src/lib/content_filter.py`:
  - it returns false for any word on the reviewed blocklist, with case
    and punctuation ignored, and for Chinese blocklist entries;
  - it returns true for ordinary sentences, and for words that merely
    contain a blocked word as a substring (for example "class" and
    "assess").
- [X] T004 [P] Create `tests/contract/test_example_client.py`
  (`contracts/practice-api.md`, R3). It patches
  `src.services.llm_client.requests.post`.
  - **Request**: the payload has `think` False, `options.temperature`
    0.7, and `format.required == ["sentence", "translation"]`. The user
    message holds the English word, its meaning and its part of speech.
    The system prompt contains "natural", "at most 20 words",
    "everyday" and "family".
  - **Outcomes**: `ConnectionError` gives `unavailable`; a malformed
    reply gives `bad_reply`; a valid reply gives `ok`.
  - **`validate_example(english, sentence, translation)`** returns
    `(ok, reason)`:
    - accepts a valid pair;
    - rejects a missing word;
    - rejects two sentences ("I like it. It is good.");
    - rejects a newline;
    - rejects more than 20 or fewer than 3 words;
    - rejects a translation with no Chinese or over 60 characters;
    - rejects anything that fails `is_clean`.
- [X] T005 [P] Create `tests/unit/test_examples_store.py` for
  `ExampleService` (`src/services/examples.py`) and
  `WordListStore.set_example`, using temporary dirs and a fake
  generator.
  - **Own list**: `set_example(lily, path, english, chinese, sentence,
    translation)` adds `example:` and `example_zh:` lines at the end of
    that block only, so every other byte is unchanged and the file loads
    with 0 warnings and the item has the example. A second call replaces
    the lines in place, and quoting is YAML-safe (`: ` and `#` in a
    sentence round-trip).
  - **Shared**: an item whose source is in a shared folder is saved to
    `<folder>/.examples.json` under the key `group|english|chinese`.
    The `.md` files stay byte-identical. A second service instance reads
    it back.
  - **`get(item)`** prefers the block's example over the JSON one.
  - **`prepare(item)`**:
    - runs the generator once in the background, so `status` goes from
      `pending` to `ready`;
    - two `prepare` calls for the same word make one generator call;
    - a generator that returns `unavailable` gives the status
      `unavailable`;
    - an invalid reply is retried exactly once.
  - **`renew(item)`** replaces the saved example synchronously, and on a
    failure keeps the old one and raises `ExampleUnavailable`.
  - **Removal**: removing the word with spec 020's `remove_word` removes
    its example lines too.
- [X] T006 [P] Append to `tests/unit/test_models_practice_attempt.py`
  and `tests/contract/test_progress_log_contract.py`:
  - `PracticeAttempt(..., sentence_recall="got")` round-trips through
    `append_attempt` and the reader;
  - `sentence_recall` must be one of `None`, `"got"` and `"not_yet"`;
  - an old block with `sentence` and `feedback` still loads (SC-005).

### Implementation

- [X] T007 [P] Create `src/lib/word_forms.py`, with `IRREGULAR_VERBS`
  (at least 120 reviewed entries, each mapping a base form to its past
  and past-participle forms), `inflections(word)` and `contains_form`.
  Makes T002 pass.
- [X] T008 [P] Create `src/lib/content_filter.py`: a reviewed
  `BLOCKLIST` of English and Chinese entries, and `is_clean(text)`
  doing whole-token matching for English and substring matching for
  Chinese. Makes T003 pass.
- [X] T009 Create `src/services/example_client.py`, with
  `ExampleReply(outcome, sentence, translation, detail)`,
  `request_example(english, chinese, pos, base_url, model, timeout=30)`
  using `llm_client._post_chat` and `_parse_object_reply`, and
  `validate_example`. Depends on T007 and T008; makes T004 pass.
- [X] T010 In `src/models/vocabulary_item.py`, add `example: str | None`
  and `example_zh: str | None`, read in `from_block`. In
  `src/services/word_lists.py`, add `set_example(account, path,
  english, chinese, sentence, translation)`:
  - it is an exact block text edit, reusing spec 020's block matching and
    `_own_path`, under the account lock;
  - each line is rendered with `yaml.safe_dump({"example": …})`.
- [X] T011 Create `src/services/examples.py` with `ExampleService(store,
  base_url, model, generate=request_example)`:
  - `get(item) -> dict | None`, `status(item)`, `prepare(item)`
    (a daemon thread, deduplicated per key) and `renew(item)`;
  - a JSON store for words that are not in the account's own lists;
  - per-file locks.

  Depends on T009 and T010; makes T005 pass.
- [X] T012 In `src/models/practice_attempt.py` and
  `src/services/progress_log.py`, add the optional `sentence_recall`
  field, validated against `None`, `"got"` and `"not_yet"`, and write it
  only when set. Makes T006 pass.

**Checkpoint**: examples can be generated, validated and saved. The
suite is green.

---

## Phase 3: User Story 1 + 3 - Example after each answer; sentence review gone (Priority: P1) 🎯 MVP

**Goal**: in the `example` mode (the default), every answer goes to
`reveal`, which shows the answer and the word's example (or a pending or
unavailable note) with "New example". Sentence writing, review and voice
input are gone from the web UI and the CLI.

**Independent Test**:
1. `/api/select` with `mode: "example"` and a mocked model, then answer.
2. The state is `reveal` with `example_status`, which settles to `ready`
   with the example.
3. `/api/continue` goes to the next word.
4. `/api/sentence` gives `404`.
5. In the UI there is no Sentence option and no mic.

### Tests (write first, confirm they FAIL)

- [X] T013 [P] [US1] Create `tests/unit/test_session_example.py`, using a
  fake `ExampleService`.
  - **The example mode** (and the default when no mode is given):
    - a correct answer goes to `reveal` with `correct` true;
    - a wrong answer goes to `reveal`;
    - the attempt is not logged until `continue_to_next`, which logs it
      once and advances.
  - **State**: at `reveal`, the state has `example`, `example_status`
    and `mode`.
  - **Preparation**: `prepare` is called when each word becomes current
    in the example modes, and never in recall-only.
  - **Recall-only**: the behaviour is unchanged (a correct answer
    advances, a wrong one reveals), and `example_status` is `off`.
  - **Alias**: `mode="sentence"` behaves as `"example"`.
  - **`renew_example()`**: at `reveal` it calls `service.renew`; at any
    other step it raises `WrongStepError`.
- [X] T014 [P] [US1] Create `tests/contract/test_practice_api.py`,
  following `contracts/practice-api.md`, with the model mocked through
  `requests.post`.
  - **Select**: `mode: example` and `mode: sentence` both give the
    example mode.
  - **Reveal**: after an answer, the `reveal` state carries the
    `example` fields. Polling `/api/state` turns `pending` into `ready`
    (the test waits on `app.example_service`).
  - **New example**: `POST /api/example/new` gives `200` with a new
    example, and `503` when the model is down (the old one is kept).
  - **Removed routes**: `/api/sentence`, `/api/skip`,
    `/api/retry-sentence` and `/api/transcribe` all give `404`.
  - **No model**: practice still works with `unavailable`.
- [X] T015 [P] [US1] Create `tests/integration/test_example_flow.py`:
  - **Web**: an account practices an own list in the example mode. The
    first time a word is seen, its example is saved into the list file.
    The next session shows the same example without calling the model.
  - **CLI**: `run_recall_step` in the example mode prints `Example:` and
    the translation, using a fake service. With no example it prints
    `(No example right now.)`.
- [X] T016 [P] [US1] Append to `tests/unit/test_web_static_assets.py`, as
  new functions:
  - the mode radios have the values `recall-only`, `example` (checked)
    and `example-recall`;
  - `index.html` has no `id="sentence-view"`, `id="mic-button"` or
    `id="feedback-view"`;
  - `app.js` contains `/api/example/new`, `Writing an example…`, `No
    example right now.` and `New example`;
  - `app.js` doesn't contain `/api/sentence"`, `/api/transcribe` or
    `MediaRecorder`.

### Removal of old tests (justified deviation, listed for the commit message)

- [X] T017 [US3] **Delete** the tests that cover only removed behaviour:
  - `tests/contract/test_ollama_correction_contract.py`;
  - `tests/integration/test_sentence_correction_flow.py`;
  - `tests/unit/test_speech_client.py`.
- [X] T018 [US3] **Rewrite**, function by function, the tests in
  `tests/unit/test_session_state.py`,
  `tests/contract/test_web_api_contract.py` and
  `tests/integration/test_web_session_flow.py`:
  - each test that drives `submit_sentence`, `skip_sentence`,
    `retry_sentence`, `/api/sentence`, `/api/skip`,
    `/api/retry-sentence` or the `sentence`/`feedback` steps either
    becomes the equivalent example-mode test (answer, then `reveal`,
    then continue), or is removed if it only covers sentence review;
  - tests of unrelated behaviour stay unchanged.

  Keep a list of the removed and rewritten test names in
  `specs/021-example-sentence/test-changes.md`.
- [X] T019 [US3] Do the same for the smaller files:
  - `tests/integration/test_multi_account_flow.py`,
    `test_session_mode.py`, `test_ipa_flow.py`, `test_session_order.py`,
    `test_non_interactive_output.py`, `test_determinism.py`,
    `test_session_group_filter.py`, `test_progress_log_readability.py`,
    `test_edge_cases.py` and `test_word_lists_flow.py`;
  - `tests/unit/test_session_registry.py`, `test_session_remove.py`,
    `test_models_practice_attempt.py`, `test_design_workflow_skill.py`
    and `test_web_static_assets.py` (only where existing functions
    assert removed markup);
  - `tests/contract/test_web_auth_contract.py`.

  Record each change in `test-changes.md`.

### Implementation

- [X] T020 [US1] [US3] In `src/web/session_state.py`:
  - normalise the modes, with `"sentence"` mapped to `"example"` and
    `"example"` the default;
  - add `example_service` and its calls to `prepare` on each new current
    word;
  - in the example modes, every answer goes to `reveal`, with the
    attempt held;
  - `continue_to_next` from `reveal` logs and advances. In the
    example-recall mode with a ready example it goes to
    `sentence-recall`; that part is completed in US2;
  - add `renew_example()`;
  - add the `state()` fields;
  - **remove** `submit_sentence`, `skip_sentence`, `retry_sentence`,
    the `sentence` and `feedback` steps, and `_review_in_progress`;
  - keep `remove_current` working at `recall` and `reveal`, and later at
    `sentence-recall`.

  Makes T013 pass.
- [X] T021 [US1] [US3] Update the services:
  - **`src/services/llm_client.py`**: remove `request_correction`,
    `_request_judge`, `_request_teacher` and their prompts and
    dataclasses. Keep `_post_chat`, `_post_json`, `_parse_object_reply`
    and `DEFAULT_MODEL`.
  - **`src/services/speech_client.py`**: delete it, and remove the
    `voice` extra from `pyproject.toml`.
  - **`src/web/session_registry.py`** passes the `ExampleService`.
  - **`src/web/app.py`**:
    - creates `app.example_service` (an `ExampleService` with the
      word-list store or `None`, and the Ollama URL and model);
    - adds `POST /api/example/new` and the `/api/select` mode mapping;
    - removes `/api/sentence`, `/api/skip`, `/api/retry-sentence`,
      `/api/transcribe` and `VOICE_AVAILABLE`.

  Makes T014 pass.
- [X] T022 [US1] [US3] Update the web UI:
  - **`src/web/templates/index.html`**:
    - the mode choice is Recall only / Recall + example / Recall +
      example + sentence recall, with hints;
    - remove the sentence view, the mic, transcribing and spinner
      markup, and the feedback view;
    - add `#example-block` (sentence, translation, `#new-example-button`)
      in the recall-result area.
  - **`src/web/static/app.js`**:
    - render the example states (ready, pending with polling for at most
      6 s, unavailable);
    - wire up New example;
    - remove the sentence, recording, review and feedback code;
    - keep the remove-word and IPA/part-of-speech rendering.
  - **`src/web/static/style.css`**: add `.example-block` styles, and
    remove the unused sentence and feedback styles.

  Makes T016 pass.
- [X] T023 [US1] [US3] Update the CLI:
  - **`src/cli/session.py`**: remove `run_sentence_step`. After each
    answer in the example modes, show the example through
    `ExampleService.get` or a synchronous generation behind
    `run_with_indicator`, with a 6 s limit.
  - **`src/cli/__main__.py`**: `--mode` accepts `recall-only`,
    `example` (the default) and `example-recall`, with `sentence` as an
    alias.

  Makes T015's CLI part pass.

**Checkpoint**: examples replace sentence review everywhere, and the
suite is green.

---

## Phase 4: User Story 2 - Self-checked sentence recall (Priority: P2)

**Goal**: in the `example-recall` mode, after `reveal`, the learner sees
the translation, tries the sentence, reveals it, and marks Got it or
Not yet, which is recorded.

**Independent Test**:
1. In the example-recall mode with a ready example, answer, then
   continue.
2. The state is `sentence-recall`, with the translation and the sentence
   withheld.
3. `mark: reveal` shows the sentence.
4. `mark: got` advances, and the progress log has
   `sentence_recall: got`.

### Tests (write first, confirm they FAIL)

- [X] T024 [P] [US2] Append to `tests/unit/test_session_example.py`:
  - in the example-recall mode, `continue_to_next` from `reveal` goes to
    `sentence-recall` only when the example is ready, and otherwise logs
    and advances;
  - `sentence_recall_action("reveal")` sets `revealed`, and the state
    then includes the sentence;
  - `"got"` and `"not_yet"` log the attempt with that mark and advance;
  - `"skip"` logs without a mark;
  - a wrong step raises `WrongStepError`, and an invalid mark raises
    `ValueError`;
  - `remove_current` works at `sentence-recall`.
- [X] T025 [P] [US2] Append to `tests/contract/test_practice_api.py`
  (`POST /api/sentence-recall`):
  - the statuses are `200`, `409` and `400`;
  - the sentence is withheld until `reveal`;
  - the progress file contains `sentence_recall`.
- [X] T026 [P] [US2] Append to `tests/unit/test_web_static_assets.py`:
  - `index.html` has `#sentence-recall-view`;
  - `app.js` contains `/api/sentence-recall`, `Recall the sentence`,
    `Show sentence`, `Got it`, `Not yet` and `Type it, or just say it`;
  - the typed attempt is never sent to the server, so the
    sentence-recall section has no `attempt` in any `postJson` body.

### Implementation

- [X] T027 [US2] In `src/web/session_state.py`, add the `sentence-recall`
  step and `sentence_recall_action(mark)`, and attach the mark to the
  held attempt. Makes T024 pass.
- [X] T028 [US2] In `src/web/app.py`, add `POST /api/sentence-recall`.
  Makes T025 pass.
- [X] T029 [US2] In `src/web/templates/index.html`,
  `src/web/static/app.js` and `src/web/static/style.css`, add the
  sentence-recall view:
  - the translation, the optional textarea (which stays client-only),
    and the Show sentence and Skip buttons;
  - after the reveal, the attempt and the example, with the Got it and
    Not yet buttons.

  Makes T026 pass.
- [X] T030 [US2] In `src/cli/session.py`, add the example-recall prompts
  from `contracts/cli.md`, with a test in
  `tests/integration/test_example_flow.py`.

**Checkpoint**: all stories are complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T031 [P] Create `src/tools/eval_examples.py` (R8):
  - it generates examples for the fixture with the real model and the
    validator, reporting the pass rate and the rejection reasons;
  - it writes `REVIEW.md` (`--out`, defaulting to
    `backups/examples-<stamp>/`) with a tick column.

  Add `tests/unit/test_eval_examples.py` using a mocked model.
- [X] T032 [P] In `README.md`:
  - replace the sentence-review and voice-input sections with an
    "Example sentences" section covering the modes, New example,
    sentence recall and where examples are saved;
  - update the `--mode` docs;
  - remove `faster-whisper` from the setup steps.
- [X] T033 Run `ruff check src tests` and the full `pytest`. Confirm
  that `test-changes.md` lists every deleted or rewritten test, and that
  `git diff -- tests/` has no other edits to existing tests.
- [X] T034 Run `python -m src.tools.eval_examples --sample 50` on the
  real model, and record the automatic results in
  `specs/021-example-sentence/eval-report.md`. **Stop and ask the user**
  to tick `REVIEW.md` (the SC-002 gate).
- [X] T035 Do the visual check with the `frontend-design` recipe, at
  1280 and 390 px:
  - the mode choice;
  - the reveal step with an example, and with pending and unavailable;
  - the sentence-recall step before and after revealing.

  Fix anything wrong.
- [X] T036 Run the quickstart §3 scenarios a–h on a temporary copy of
  the data, and record the results in `quickstart.md`.

---

## Dependencies & Execution Order

- **Setup (T001)**: needed by T031 and T034.
- **Foundational (T002–T012)**: blocks all stories.
  - T007 and T008 come before T009, T009 before T011, T010 before T011.
- **US1+US3 (T013–T023)**: write the tests T013–T016, then make the test
  changes T017–T019 alongside the implementation T020–T023.
  - T020 comes before T021, T021 before T022, and T020 before T023.
- **US2 (T024–T030)**: comes after US1+US3.
- **Polish (T031–T036)**: comes last. T034 is the human gate.

```text
Foundational ──► US1+US3 (MVP) ──► US2 ──► Polish (eval gate)
```

## Parallel Examples

```bash
T002 word_forms | T003 content_filter | T004 example_client | T005 examples store | T006 attempt field
T013 session_example | T014 practice_api | T015 example_flow | T016 static assets
T024 | T025 | T026
```

## Implementation Strategy

1. Do Foundational, then US1+US3. The app then shows examples instead of
   sentence review, which is a releasable MVP once the eval gate (T034)
   passes.
2. Add US2, the optional sentence recall.
3. Polish, then the human review gate, then commit to `main` when asked.

## Notes

- Shared `.md` files are never edited. Examples for shared words live in
  `.examples.json`.
- The typed sentence-recall attempt never leaves the browser
  (Constitution III).
