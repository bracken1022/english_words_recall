# Research: Example Sentences Instead of Sentence Review

Phase 0 for [plan.md](plan.md). The spec's clarifications were settled
on 2026-10-11:

- sentence recall is self-checked;
- examples are generated on a word's first practice and then saved.

## R1. Practice modes and steps (FR-001, FR-008)

- **Decision**: there are three modes. The old `"sentence"` mode is
  removed.

  | Mode | What happens |
  |---|---|
  | `"recall-only"` | Unchanged. |
  | `"example"` | The new **default**. Recall the word, then see the answer and an example sentence. |
  | `"example-recall"` | Like `"example"`, then the self-checked sentence recall (US2). |

  `"sentence"`, sent by old pages, URLs or `--mode sentence`, is
  accepted as an alias for `"example"`.

  **Steps**:
  - `choose`, `recall`, `reveal`, `complete` and `empty` stay.
  - `sentence-recall` is new.
  - `sentence` and `feedback` are removed.

  ```text
  recall ──answer──► (recall-only & correct) record ► next
                └──► reveal  (recall-only & wrong, or any example mode)
  reveal ──continue──► example-recall mode & example ready ► sentence-recall
                   └──► record attempt ► next
  sentence-recall ──mark got / not yet / skip──► record attempt (+ mark) ► next
  ```

- **Rationale**:
  - The reveal step already exists (spec 013). Making every example-mode
    answer go through it gives one place to show the example.
  - A word's attempt is recorded once, at the end of the word, with the
    self-mark when there is one.

## R2. Retiring sentence review (FR-001)

- **Removed**:
  - `PracticeSession.submit_sentence`, `skip_sentence` and
    `retry_sentence`, and the `sentence`/`feedback` steps;
  - the routes `/api/sentence`, `/api/skip`, `/api/retry-sentence` and
    `/api/transcribe`;
  - `request_correction` and its Judge/Teacher prompts from
    `src/services/llm_client.py`. The module keeps `_post_chat` and
    `_parse_object_reply`, which enrichment uses;
  - `src/services/speech_client.py`, and the optional `voice`
    dependency (`faster-whisper`);
  - the CLI's `run_sentence_step`;
  - the sentence view, the mic button and the recording code in the web
    UI.
- **Kept**: `PracticeAttempt.sentence` and `feedback` stay as optional
  fields, so old history entries still load (FR-009, SC-005). New
  entries never set them.
- **Tests**:
  - **Deleted**, because they test only removed behaviour:
    `test_ollama_correction_contract.py`,
    `test_sentence_correction_flow.py` and `test_speech_client.py`.
  - **Edited**: tests that drove the sentence step, often only because
    `"sentence"` was the default mode, are rewritten to the example or
    recall-only flow. This is a deliberate exception to "existing tests
    are only appended to": the behaviour they pin is being removed. Each
    edited file is listed in tasks.md and in the commit message.
- **Rationale**: the spec says to remove sentence review. Keeping dead
  code paths would leave two practice flows to maintain.

## R3. Generating an example (FR-003, FR-004)

- **Decision**:
  `src/services/example_client.py::request_example(english, chinese, pos,
  base_url, model, timeout=30) -> ExampleReply`.
  - **Request**: one local `/api/chat` call with `think: false`,
    temperature 0.7 (so "New example" can differ), and the format
    `{sentence: str, translation: str}`.
  - **The prompt asks for** one short (at most 20 words), natural,
    everyday sentence that a native speaker would say. The word must be
    used in the given Chinese meaning and part of speech, with a natural
    Chinese translation, and the content must suit a family learner.
  - **Outcomes**: `unavailable`, `bad_reply` or `ok`, as in spec 018.
- **Validation** (`validate_example`): the example is accepted only if
  all of these hold:
  - the sentence contains the word (see R4);
  - it is one sentence: no newline, exactly one sentence-ending mark,
    which comes at the end;
  - it has 3 to 20 words;
  - the translation contains Chinese characters and is at most 60
    characters long;
  - neither text contains a word from a small reviewed blocklist
    (`src/lib/content_filter.py`), which covers Constitution II's safety
    filter.

  A rejected reply is retried once. If the second also fails, the word
  is "unavailable" for this session.
- **Rationale**: these checks catch the failures most likely to mislead
  a learner: a sentence missing the word, a rambling paragraph, an
  empty translation, or unsuitable content. Naturalness itself is
  measured by people on a reviewed sample (R8).

## R4. "Contains the word" check

- **Decision**: `src/lib/word_forms.py::contains_form(sentence, english)`.
  It lowercases and tokenises the sentence, then checks the target:
  - **A single word**: the target matches if a token equals it, or one
    of its regular inflections:
    - `-s`, `-es`, `-ed`, `-d`, `-ing`, `-er` and `-est`;
    - `y`→`-ies`/`-ied`;
    - a dropped final `e` before `-ing`/`-ed`;
    - a doubled final consonant before `-ed`/`-ing`;

    or one of its irregular forms, from a reviewed table of about 150
    common irregular verbs (give→gave/given, take→took/taken, …).
  - **A phrase**: each word is matched in order, the first word allowing
    inflection and the others matched exactly, with gaps of at most 2
    words. So *give up* matches "gave it up", and *tend to* matches
    "tends to".
- **Rationale**: this is deterministic and testable, and it is lenient
  enough for natural inflected use.
- **Alternative considered**: asking the model which form it used. That
  can't be trusted without the same check anyway.

## R5. Saving examples (FR-005)

- **Decision**: there are two stores, chosen by where the word came from.
  1. **The learner's own list** (`item.source` inside
     `word-lists/<user>/`): the example is written into the word's block
     as two keys, `example:` and `example_zh:`. The edit is a text edit:
     existing example lines are replaced, and new ones are inserted
     before the block's closing `---`. Every other byte stays the same.
     This uses the same block-finding as spec 020's `remove_word`, under
     the account lock. Removing a word (spec 020) removes its example
     with it.
  2. **Any other source** (the shared folder, the CLI's vocabulary
     folder, or a server without accounts): the example goes into
     `<folder of the word's file>/.examples.json`, which is
     `{"version": 1, "examples": {"<group>|<english>|<chinese>":
     {"sentence", "translation", "created"}}}`.
     - It is written atomically, under a per-file lock.
     - The `.md` files are never edited.
     - It is shared by every learner who uses that folder.
- **Loading**: `VocabularyItem` gains optional `example` and
  `example_zh`, read from the block. `ExampleService.get(item)` returns
  the block's example first, then the JSON store's.
- **Rationale**: a learner's own lists keep everything about a word in
  one readable file. Shared words get one cached example that everyone
  benefits from, without touching operator files.

## R6. Preparing in the background (FR-005, SC-001)

- **Decision**: `ExampleService` (`src/services/examples.py`):
  - **`prepare(item)`**: when a word becomes the current word in an
    example mode, this starts a daemon thread to generate and save its
    example, unless one exists or is already being made. There is one
    job per word key. A generation already in progress is shared rather
    than started twice.
  - **`status(item)`**: one of `ready`, `pending` or `unavailable`.
  - **`renew(item)`**: generates synchronously, replaces the saved
    example, and returns it, for "New example".
- **Web**: at `reveal` and `sentence-recall`, the state carries
  `example`, which is `{sentence, translation}` or `null`, and
  `example_status`. While the status is `pending`, the page polls
  `/api/state` once a second. After 6 seconds it shows "No example right
  now", though the server keeps going and saves the example for next
  time.
- **CLI**: after the answer, it calls `get_or_generate(item)`
  synchronously behind the existing loading indicator, with the same
  6-second limit.
- **Rationale**: on qwen3:14b a short reply takes about 1–3 s, so
  starting during recall usually hides it completely.

## R7. Sentence recall (FR-006, US2)

- **Decision**:
  - **Shown on the step**: the example's translation; an optional text
    box ("Type it, or just say it"); and buttons for **Show sentence**
    and **Skip**.
  - **After Show sentence**: the example, with the learner's attempt
    above it, and buttons for **Got it** and **Not yet**.
  - **Recording**: the mark is stored on the word's attempt as
    `sentence_recall: got | not_yet`, a new optional field in the
    progress log. The attempt text itself isn't stored, keeping what is
    saved to a minimum (Constitution III). Skip records no mark.
- **API**:
  - `POST /api/sentence-recall {"mark": "got" | "not_yet" | "skip"}`;
  - `POST /api/example/new` for "New example", valid at `reveal` and
    `sentence-recall`.

## R8. Accuracy check (SC-002, Constitution II)

- **Decision**: `python -m src.tools.eval_examples [--sample 50]`.
  1. It generates examples for 50 reviewed fixture words, a mix of
     words, phrases and multi-meaning words, using the real model and the
     full validator.
  2. It reports the automatic pass rate and the rejection reasons.
  3. It writes `REVIEW.md`, a table of word, meaning, sentence and
     translation, for a person to tick as natural, correct and in the
     right meaning.

  The release gate is: at least 95% ticked, and 0 unsafe.
- **Rationale**: naturalness is a human judgment. The tool makes the
  judging quick and repeatable.
