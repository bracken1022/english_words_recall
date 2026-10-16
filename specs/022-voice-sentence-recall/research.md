# Research: Voice Answers for Sentence Recall

## R1. Which speech recogniser the web app uses

- **Decision**: Local Whisper through `faster-whisper`, model `base`,
  English only (`language="en"`), with voice-activity filtering. It is an
  optional extra (`pip install -e '.[voice]'`) brought back from spec 009
  (`src/services/speech_client.py`, removed in spec 021). The model is
  loaded in a background thread when the web app starts, so the first
  recording doesn't pay the load time.
- **Rationale**: It runs on the learner's own Mac, like Ollama, so audio
  never leaves the machine (FR-004). It is already proven here (spec 009),
  already installed in the dev venv (1.2.1) with the `base` model cached,
  and it decodes the formats browsers record (WebM/Opus from Chrome and
  Firefox, MP4/AAC from Safari) straight from memory. `base` transcribes a
  20-word sentence in well under a second on Apple silicon (SC-001).
  Fixing the language to English stops it guessing Chinese from a short or
  accented clip. Voice-activity filtering drops silence, which is where
  Whisper invents filler text such as "Thank you."
- **Accuracy gate**: SC-002 (≥ 90% of words right on 20 clearly read
  example sentences) is measured with the eval tool (R6). If `base`
  misses it, switch to `small` (the only change is the model name) and
  re-measure the time against SC-001.
- **Alternatives considered**:
  - *The browser's built-in recognition (Web Speech API)*: Chrome sends
    the audio to Google and Safari may send it to Apple, which breaks
    FR-004. Firefox doesn't support it. Rejected, as in spec 009.
  - *`mlx-whisper` (large-v3-turbo is cached on this Mac)*: more accurate
    but Apple-silicon only, much bigger and slower to load. Kept as the
    fallback if `small` still misses SC-002.
  - *Whisper.cpp in the browser (WebAssembly)*: keeps audio in the
    browser, but a ~150 MB download per device and slow on phones.
    Rejected for now.

## R2. Never hint the expected sentence to the recogniser

- **Decision**: The recogniser gets only the audio. The real sentence is
  never passed as a prompt, hint word list or "initial prompt".
- **Rationale**: Whisper biases strongly towards a prompt. Given the
  answer, it would "hear" the right sentence even when the learner said
  something else, and the highlight (FR-012) would hide real mistakes,
  which breaks Constitution II. It also means `/api/transcribe` needs
  nothing from the session except that the step is right.

## R3. Where the attempt is compared with the sentence

- **Decision**: On the server, in a pure function
  (`src/lib/word_diff.py`), when the learner reveals the sentence. The
  page sends its attempt with the reveal (`{"mark": "reveal", "attempt":
  "…"}`); the reply carries the comparison. The attempt is used for that
  one reply and dropped: it is not kept in the session, the history or
  the server log (FR-006).
- **Rationale**: The comparison is the part of this feature that can be
  wrong in a way a learner trusts, so it needs a reviewed test set
  (Constitution II, SC-007). The project's tests are pytest, so a Python
  function can be tested against a reviewed fixture; JavaScript logic here
  has no test runner. A future iPhone app can call the same endpoint, or
  port the documented rules in `contracts/word-diff.md`.
- **Change from spec 021**: there, the typed attempt never left the
  browser, and the field said "stays on this device". With voice, audio
  goes to the server anyway, and the page may be opened from a phone on
  the home network, so that label would be wrong. It becomes "optional,
  not saved", which is true for both: the attempt and the audio reach the
  learner's own server and are never stored.

## R4. How the comparison works

- **Decision**: Split both texts into words; compare a normalised form
  (lower case, curly apostrophes made straight, leading and trailing
  punctuation removed, so "Don't," matches "don't"); align the two word
  lists with `difflib.SequenceMatcher` (`autojunk=False`). Each word of
  the real sentence is `same` or `missing` (a replaced word counts as
  missing); each word of the attempt is `same` or `extra`. The original
  spelling and punctuation are kept for display. An empty attempt gives no
  comparison.
- **Rationale**: Word-level alignment is what a learner reads ("I said
  *went* but it's *goes*"), standard-library only, and deterministic.
  Ignoring capitals and punctuation is required by FR-012 and stops
  Whisper's own punctuation choices from showing as mistakes.
- **Known limits, accepted because the highlight is a guide only and the
  learner marks**: "don't" and "do not" are different words; "10" and
  "ten" are different words (Whisper often writes digits); "color" and
  "colour" are different words. These are listed in the fixture as
  expected differences so the behaviour is deliberate and tested.
- **Alternatives considered**: character-level diff (noisy for
  learners); fuzzy matching of near-spellings (would hide spelling
  mistakes in typed attempts).

## R5. Audio handling and limits

- **Decision**:
  - The page records with `MediaRecorder` and stops at 30 seconds
    (FR-007). The upload goes to `POST /api/transcribe` as the raw body.
  - The server reads the body into memory and passes it to the
    recogniser as an in-memory stream. It is never written to disk, never
    logged, and the bytes go out of scope when the request ends (FR-005).
  - The existing 1 MB request limit covers it: 30 seconds of Opus or AAC
    is about 100–250 KB. A larger body gets `413` with a voice-specific
    message.
  - `/api/transcribe` needs a login (the existing guard) and is allowed
    only while the session is at `sentence-recall` with the sentence still
    hidden (`409` otherwise), so voice is offered nowhere else (FR-001).
- **Note on phones**: browsers only allow the microphone on secure pages
  (`https://` or `localhost`). Opening the app from a phone at
  `http://<mac-ip>:8420` therefore has no microphone, and the page says so
  (FR-008, US2). Serving HTTPS on the home network is out of scope; the
  future iPhone app (R7) doesn't have this limit.

## R6. Measuring recognition accuracy (SC-002)

- **Decision**: A tool, `python -m src.tools.eval_voice <folder>`, reads
  recordings named after fixture entries plus a small YAML of expected
  sentences, transcribes each, and reports word accuracy using the same
  `word_diff` (words of the sentence marked `same` ÷ all words) and the
  time per clip. The recordings are made by the operator for this check
  (not learner data) and live outside the repo, under `backups/`. For a
  quick smoke test, macOS `say` can generate clips; the release gate uses
  20 sentences read by a real learner.
- **Rationale**: Mirrors `eval_examples` and `eval_enrichment`; reusing
  `word_diff` means accuracy is measured the way the learner sees it.

## R7. Carrying over to an iPhone app (FR-010)

- **Decision**: Nothing iPhone-specific is built. The behaviour is written
  down device-independently in `contracts/voice-input.md` (when voice is
  offered, where text goes, what is kept, what happens on failure) and
  `contracts/word-diff.md` (the comparison rules), so an iPhone app can
  meet the same rules with Apple's on-device recogniser
  (`SFSpeechRecognizer` with `requiresOnDeviceRecognition`), which keeps
  audio on the phone, and either call `/api/sentence-recall` for the
  comparison or port the rules.
- **Rationale**: The iPhone app's overall shape (server, on-device model
  or bundled examples) is a separate, bigger decision; this feature only
  avoids making it harder.

## R8. CLI

- **Decision**: No change. The CLI's sentence recall stays keyboard-only
  (spec assumption).
