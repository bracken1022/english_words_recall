---

description: "Task list for 022-voice-sentence-recall"
---

# Tasks: Voice Answers for Sentence Recall

**Input**: design documents from `/specs/022-voice-sentence-recall/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/ (practice-api.md, voice-input.md, word-diff.md), quickstart.md

**Tests**: included and REQUIRED (Constitution Principle I). Each test
task is written first and seen failing for the right reason before its
implementation task starts. No existing test is deleted or weakened.

**Organization**:

- **US1 (P1)**: say the sentence, edit the transcript, reveal with the
  differences highlighted. The comparison also works for typed attempts.
- **US2 (P2)**: practice still works without voice (not installed,
  blocked microphone, insecure page, nothing heard, errors).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no unfinished
  dependencies)
- **[Story]**: US1 or US2

---

## Phase 1: Setup

- [X] T001 Restore the optional `voice` extra in `pyproject.toml`
  (`voice = ["faster-whisper>=1.0"]`, under
  `[project.optional-dependencies]`), with a one-line comment: local
  speech-to-text for sentence recall (spec 022), optional.
- [X] T002 [P] Create `tests/fixtures/word_diff_cases.yml`, a reviewed set
  of at least 25 `{attempt, sentence, missing, extra}` cases, where
  `missing` and `extra` list the expected words (as written) in order.
  Include every row of `contracts/word-diff.md`'s "Required examples",
  plus: identical text; capitals only; punctuation only (commas, final
  `.`/`?`/`!`, quotes); curly vs straight apostrophes; a missing first
  word; a missing last word; a repeated word (`the the`); words in a
  different order; an attempt with no word in common; hyphenated words
  (`well-known`); an attempt with a stray `—`; extra spaces and line
  breaks; a blank and a whitespace-only attempt (expect no comparison,
  marked `none: true`); British vs American spelling (`colour`/`color`,
  accepted limit). Add a header comment saying the cases are reviewed
  (Constitution II, SC-007) and that the "accepted limit" rows are
  deliberate.

---

## Phase 2: Foundational (blocks both stories)

**Purpose**: the comparison, the recogniser client, the session checks,
and keeping real speech models out of tests.

### Tests first

- [X] T003 [P] Write `tests/unit/test_word_diff.py`:
  - a parametrised test over every case in
    `tests/fixtures/word_diff_cases.yml`, checking the words marked
    `missing` in the sentence and `extra` in the attempt (in order), and
    that all others are `same`;
  - `compare("", s)` and `compare("   \n", s)` return `None`;
  - every input word appears once, in order, with its original spelling
    and punctuation (`team.` stays `team.`);
  - a word that is only punctuation is not in the output;
  - the result is identical when called twice (deterministic).
- [X] T004 [P] Write `tests/unit/test_speech_client.py` with a fake
  `WhisperModel` (monkeypatch `speech_client._get_model`; never load a
  real model):
  - text from segments joined and trimmed → `outcome "ok"`;
  - no segments or only whitespace → `"nothing_heard"`, `text None`;
  - the model raising (load or decode failure) → `"unavailable"`;
  - empty bytes → `"unavailable"` without calling the model;
  - `transcribe` passes `language="en"` and `vad_filter=True`, and
    passes the audio as an in-memory stream (`io.BytesIO`), never a path;
  - `faster_whisper` not importable (monkeypatch `sys.modules`) →
    `is_available()` false and `transcribe` → `"unavailable"`;
  - `preload()` never raises, even when loading fails;
  - `transcribe` writes no file: patch `builtins.open` and
    `tempfile.NamedTemporaryFile` to fail the test if called.
- [X] T005 [P] Add to `tests/unit/test_session_state.py` (done in
  `tests/unit/test_session_example.py`, beside the sentence-recall helpers):
  - `can_transcribe()` is true only at `sentence-recall` with
    `sentence_revealed` false (false at choose, recall, reveal, after
    reveal, complete, empty);
  - `state()` at `sentence-recall` includes `voice_available` taken
    from the session's `voice_available` setting; other steps don't
    include it;
  - `sentence_recall_action("reveal", attempt="…")` returns the
    comparison and does not keep the attempt (no attribute on the
    session holds it; a later `state()` has no `comparison`);
  - `got` / `not_yet` / `skip` with an attempt record only the mark, as
    in spec 021 (the written attempt has no attempt text).
- [X] T006 Extend `tests/conftest.py`: an autouse fixture that makes
  `src.services.speech_client._get_model` raise, so no test can load a
  real Whisper model (tests that need a model patch it themselves,
  which overrides this).

### Implementation

- [X] T007 [P] Implement `src/lib/word_diff.py` per
  `contracts/word-diff.md`: `WordMark(word, status)` with status
  `"same" | "missing" | "extra"`; `AttemptComparison(sentence, attempt)`;
  `compare(attempt, sentence) -> AttemptComparison | None` (`None` when
  the attempt is blank after trimming); normalise (lower case, curly →
  straight apostrophes, strip leading and trailing punctuation, keep
  inner `'` and `-`, drop punctuation-only words); align with
  `difflib.SequenceMatcher(None, a, b, autojunk=False)`; and
  `to_json()` giving `{"sentence": [{"word", "status"}], "attempt": […]}`.
  Make T003 pass.
- [X] T008 [P] Restore `src/services/speech_client.py` from spec 009
  (`git show 67b0725^:src/services/speech_client.py`) and change it per
  data-model.md: `TranscriptionResult(outcome, text)` with outcome
  `"ok" | "nothing_heard" | "unavailable"`; `transcribe(audio)` calls
  `model.transcribe(io.BytesIO(audio), language="en", vad_filter=True,
  condition_on_previous_text=False)`; `DEFAULT_MODEL_SIZE = "base"`,
  overridable through `configure(model_size)`; `preload()` that loads
  the model and swallows any error; and a module docstring stating that
  audio is never written to disk or logged and that the expected
  sentence is never passed to the model (research R2). Make T004 pass.
- [X] T009 Implement in `src/web/session_state.py`: a `voice_available`
  constructor argument (default `False`); `can_transcribe()`;
  `voice_available` in `state()` at `sentence-recall`; and
  `sentence_recall_action(mark, attempt=None)` that, for `reveal`,
  returns `word_diff.compare(attempt, example.sentence)` (or `None`)
  without storing the attempt, and ignores the attempt for other marks.
  Pass `voice_available` through `src/web/session_registry.py` the same
  way as `example_service`. Make T005 pass (depends on T007).

**Checkpoint**: `pytest tests/unit` passes; nothing in the web layer has
changed yet.

---

## Phase 3: User Story 1 - Say the sentence instead of typing it (Priority: P1) 🎯 MVP

**Goal**: in sentence recall, tap Speak, say the sentence, see it in the
attempt box, edit it, reveal, and see the differences highlighted, then
mark as before.

**Independent Test**: with a faked recogniser, select the
example-recall mode, answer a word, `POST /api/transcribe` at
sentence-recall and get the text; reveal with an edited attempt and get
a `comparison`; mark `got` and confirm the history has only the mark.

### Tests first

- [X] T010 [P] [US1] Write `tests/contract/test_voice_api.py` (faked
  `speech_client.transcribe`):
  - at `sentence-recall`, `POST /api/transcribe` with an `audio/webm`
    body → `200 {"outcome": "ok", "text": …}`, and the session's step
    and state are unchanged;
  - `voice_available` is in `GET /api/state` at sentence-recall;
  - `POST /api/sentence-recall {"mark": "reveal", "attempt": "…"}` →
    `200` with `comparison` matching `contracts/practice-api.md`'s
    example (zealous / the missing, zelous extra);
  - reveal with no or blank attempt → `comparison: null`;
  - `attempt` that isn't a string, or is longer than 1000 characters →
    `400`;
  - a later `GET /api/state` has no `comparison`;
  - with accounts on: signed out → `401` for `/api/transcribe`.
- [X] T011 [P] [US1] Write
  `tests/integration/test_voice_sentence_recall_flow.py` using a temp
  copy of the fixture data (never real learner data): log in, select
  `example-recall` with a ready example, answer, continue to
  sentence-recall, transcribe (faked), reveal with the edited transcript,
  mark `got`, and check that `progress.md` records the
  `sentence_recall: got` mark with no attempt or transcript text
  (SC-006); and that no file was created anywhere under the temp data
  folder or `tmp_path` during the transcribe call (SC-003).
- [X] T012 [P] [US1] Add to `tests/unit/test_web_static_assets.py`:
  - `index.html` has a Speak button (`#speak-button`) and the
    listening / transcribing notes inside `#sentence-recall-view` only;
    no mic control in `#recall-view`;
  - the attempt label reads "Your sentence (optional, not saved)";
  - `app.js` uses `MediaRecorder`, posts to `/api/transcribe`, has a
    30-second limit (`30000` or `30 * 1000`), appends to the box rather
    than replacing it, sends `attempt` with the reveal, renders
    `comparison` with `missing` / `extra` classes, and shows "We heard
    this. Fix anything before you check.";
  - `app.js` never calls `sendSentenceRecall` from the recorder's stop
    or transcription handlers (no auto reveal or mark);
  - `style.css` styles `.word--missing` and `.word--extra`.

### Implementation

- [X] T013 [US1] In `src/web/app.py`: create sessions with
  `voice_available=speech_client.is_available()`; start
  `speech_client.preload()` in a daemon thread at app start when
  available; add `POST /api/transcribe` (`409 {"error": "Voice is only
  for recalling a sentence."}` unless `can_transcribe()`; `400 {"error":
  "No recording received."}` for an empty body; read `request.get_data()`
  and return `{"outcome", "text"}` without logging either); and let
  `POST /api/sentence-recall` accept `attempt` (string, at most 1000
  characters, else `400`) and add `comparison` to the reveal reply.
  Make T010 and T011 pass.
- [X] T014 [US1] In `src/web/templates/index.html`: add the Speak button
  beside the sentence-recall textarea, a `#voice-status` note
  (`aria-live="polite"`, hidden), and the "We heard this…" hint; change
  the label to "Your sentence (optional, not saved)"; add the comparison
  containers to `#sentence-recall-check` ("You said / wrote" and
  "Example", plus "Differences are a guide. You decide.").
- [X] T015 [US1] In `src/web/static/app.js`, inside the sentence-recall
  section: restore the spec 009 recorder (`git show
  67b0725^:src/web/static/app.js`, lines ~694–800) scoped to this step:
  preferred types `audio/webm;codecs=opus`, `audio/webm`, `audio/mp4`;
  Speak ↔ Stop; a running timer; stop at 30 s; one recording at a time;
  upload the blob to `/api/transcribe`; on `ok`, append the text (with a
  space) to the box, focus it, and show the hint. Stop and discard the
  recording on reveal, skip, End session, logout and step change; drop a
  transcription that returns after the step changed. Send `attempt` with
  the reveal and render `comparison` word by word into spans with
  `word--missing` / `word--extra`. Keep `voice_available` false → no
  button. Make T012 pass.
- [X] T016 [P] [US1] In `src/web/static/style.css`: Speak/Stop button
  states (a recording dot), the status note, `.word--missing`
  (underlined in the accent colour) and `.word--extra` (struck through,
  muted), in light and dark themes, wrapping at phone width.

**Checkpoint**: US1 works end to end with a faked recogniser; manual
quickstart rows a, b, c, e and k pass with the real one.

---

## Phase 4: User Story 2 - Practice still works without voice (Priority: P2)

**Goal**: no recogniser, a blocked microphone, a phone on `http://`, an
empty recording or an error never block sentence recall.

**Independent Test**: with `is_available()` false, there's no Speak
button and sentence recall works by typing; with the recogniser
returning `nothing_heard` or `unavailable`, the box is unchanged and a
note shows.

### Tests first

- [X] T017 [P] [US2] Add to `tests/contract/test_voice_api.py`:
  - recogniser not installed → `voice_available: false` in state, and
    `/api/transcribe` → `200 {"outcome": "unavailable", "text": null}`;
  - `nothing_heard` passes through as `200`;
  - empty body → `400`;
  - a body over 1 MB → `413 {"error": "The recording is too long."}`
    (word-list upload keeps its own 413 message);
  - at `choose`, `recall`, `reveal`, after reveal, and `complete` →
    `409`;
  - reveal, got, not_yet and skip all still work with
    `voice_available: false`.
- [X] T018 [P] [US2] Add to `tests/unit/test_web_static_assets.py`:
  `app.js` hides the Speak button when `navigator.mediaDevices`,
  `MediaRecorder` or `window.isSecureContext` is missing and shows "Voice
  needs this page on the Mac itself (or over https)."; shows "The
  microphone is blocked. Allow it in the browser, or type instead." when
  `getUserMedia` rejects; shows "Didn't catch that. Try again, or type
  it." for `nothing_heard`; and shows "Voice isn't working right now.
  Type it instead." for `unavailable` or a failed request, leaving the
  box unchanged in each case.
- [X] T019 [P] [US2] Add to `tests/contract/test_practice_api.py`:
  `create_app` starts and serves
  `/api/state` when `faster_whisper` can't be imported, and when
  `preload()` fails (FR-009).

### Implementation

- [X] T020 [US2] In `src/web/app.py`: a 413 handler that returns "The
  recording is too long." for `/api/transcribe` and keeps the existing
  message for uploads; make sure startup never fails when the extra is
  missing or preload fails. Make T017 and T019 pass.
- [X] T021 [US2] In `src/web/static/app.js`: the secure-context and
  capability check, the permission-denied note, and the
  `nothing_heard` / `unavailable` / network-error notes from
  `contracts/voice-input.md`, each leaving the attempt box unchanged.
  Make T018 pass.

**Checkpoint**: both stories pass; quickstart rows d, f, g, h, i and j
pass.

**Note**: the US2 server and page behaviour was built in T013/T015 (same
route and file as US1), so T017–T019 passed when first run; T020/T021
needed no further change.

---

## Phase 5: Polish & Cross-Cutting

- [X] T022 [P] Write `tests/unit/test_eval_voice.py` (faked
  `transcribe`): word accuracy is `same` sentence words ÷ all sentence
  words, using `word_diff`; per-clip times are reported; a missing clip
  is reported, not crashed on; the exit status is 0 at ≥ 90% accuracy
  with every clip under 3 s, 1 otherwise, 2 when the recogniser is
  unavailable.
- [X] T023 Implement `src/tools/eval_voice.py`
  (`python -m src.tools.eval_voice <folder> [--model base|small]`):
  read `<folder>/sentences.yml` (`{file: sentence}`), transcribe each
  clip from memory, print word accuracy, misses per clip and times
  (SC-001, SC-002). Make T022 pass.
- [X] T024 [P] Update `README.md`: a "Voice in sentence recall" section
  (install `.[voice]`, where the Speak button is, local only, nothing
  kept, works only on the Mac itself or over https, `eval_voice`).
- [X] T025 Run `.venv/bin/python -m pytest -q` and
  `.venv/bin/ruff check src tests`; fix anything failing.
- [X] T026 Run the quickstart manual scenarios a–k against a temp copy
  of the data with the real recogniser and a browser on the Mac; record
  results in `specs/022-voice-sentence-recall/quickstart.md`.
- [ ] T027 (smoke run done with `say`, 99.5%; real-voice gate pending the
  user's recordings — see eval-report.md) Run `eval_voice` on 20 example sentences read aloud (the
  user records them; a `say` smoke run first). Record word accuracy and
  times in `specs/022-voice-sentence-recall/eval-report.md`; if `base`
  is under 90%, re-run with `small` and note the decision (research R1).

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T009)** → **US1
  (T010–T016)** → **US2 (T017–T021)** → **Polish (T022–T027)**.
- T007 needs T003 and T002; T008 needs T004 and T006; T009 needs T005
  and T007.
- US2 builds on US1's route and page code (same files), so it follows
  US1. Its server-side fallback is already in T008 (`is_available`,
  `unavailable`), so US1's MVP never crashes without the extra.
- T027 needs the user's recordings; everything else can be done without
  them.

## Parallel Examples

- Foundational tests: T003, T004 and T005 together (three files).
- Foundational code: T007 and T008 together.
- US1 tests: T010, T011 and T012 together; then T013, T014/T015 (page),
  and T016 (CSS) in parallel.
- US2 tests: T017, T018 and T019 together.
- Polish: T022 and T024 together.

## Implementation Strategy

1. **MVP = Phases 1–3 (US1)**: voice in sentence recall, editable
   transcript, highlighted differences, only the mark saved.
2. **Then US2**: the fallbacks and notes that make it safe to leave on
   for every device.
3. **Release gate**: tests and ruff clean; quickstart a–k pass; SC-002
   met in `eval-report.md`.
