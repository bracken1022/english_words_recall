# Research: Automatic Word Corrections

All open points from the spec are settled below. The two spec
clarifications (check in the background on first practice; shared
corrections apply to everyone) are taken as given.

## R1. When and how a check runs

**Decision**: A new `CorrectionService` (in `src/services/corrections.py`)
mirrors spec 021's `ExampleService`: the session calls
`prepare(item)` whenever a word comes up (`_word_started`), in every mode
including recall-only. `prepare` returns at once; the check runs on a
daemon thread. At most one check per word runs at a time (keyed like
examples), and at most **2** checks run at once overall (a semaphore), so
a learner skipping quickly doesn't fire dozens of requests.

**Rationale**: The examples pattern is proven in this codebase (prepare →
background thread → save → mark ready), keeps practice free of waits
(FR-003, SC-003), and is easy to fake in tests (inject the checker).

**Alternatives considered**: A queue with one worker (simpler cap, but a
slow word would hold up the word the learner is on now); checking at
upload time only (doesn't cover existing words, and the user chose
first-practice checks).

## R2. When corrected values appear

**Decision**: The service updates the session's own `VocabularyItem` in
place once a correction is saved, and `state()` already reads the item's
fields each time. So:
- the meaning and part of speech shown during recall are whatever the
  word had when it came up;
- at reveal (and later steps), the page shows the corrected IPA, meaning
  and part of speech if the check finished by then (FR-012);
- otherwise the next load of the list shows them.

The reveal state also gets `corrected: ["chinese", …]` for the current
word when a correction was saved for it this session, so the page can
add a small "Updated" note by the changed fields.

**Rationale**: No polling or new step; matching only uses the English
word and its spelling variants, which corrections never touch (FR-002),
so changing the meaning under an answer can't change its grading.

**Alternatives considered**: Waiting for the check before showing the
word (adds up to 45 s of waiting, breaks SC-003); swapping the meaning
mid-recall (confusing: the prompt would change while the learner thinks).

## R3. Pronunciation style (dialect)

**Decision**: `word_check` gains a `dialect` argument (`"british"` or
`"american"`) that picks the prompt line ("British (RP) IPA in the
Oxford Learner's Dictionaries style" / "General American IPA") and the
validator (`check_british_ipa` / `check_american_ipa`, existing). The
dialect is:
- **British** for the shared sets (spec 017);
- for a learner's own list, decided per **file**: **British** when any
  word in the file has an IPA that passes the British check and fails the
  American one (lists copied from the shared sets), otherwise
  **American** (spec 018 uploads). Per file, not per word, because many
  British forms (`ˈteɪlə`) also pass the American check, and a per-word
  rule would let those be rewritten as American (`ˈteɪlər`).

An IPA answer that fails its dialect's check is rejected (the whole
answer, FR-007). For heteronyms (`is_heteronym`, existing list) the IPA
is never changed: the right one depends on the meaning, and spec 018
already found models unreliable there; the meaning and part of speech
are still checked.

**Rationale**: FR-008, and the edge case "never swaps a correct British
form for an American one". Both checks exist and are tested.

**Alternatives considered**: Always American (would rewrite every shared
and copied British IPA); letting the model choose (unverifiable).

## R4. A word's identity when its meaning changes

**Problem**: The Chinese meaning is part of a word's key in several
places: spec 020's hidden shared words `(group, english, chinese)`, spec
021's `.examples.json` key `group|english|chinese`, and
`WordListStore._find_block(english, chinese)`. A correction that changes
the meaning would orphan a shared word's example and un-hide a removed
shared word.

**Decision**: `VocabularyItem` gets `origin_chinese` (not compared, not
shown): the meaning as written in the file, set by the loader *before*
shared corrections are applied. Every key that identifies a shared word
(`hidden`, `.examples.json`, corrections) uses `origin_chinese`. For own
lists the correction is written into the file itself, so the file's
meaning *is* the new identity: the inline example stays in its block,
and own lists have no hidden list.

**Rationale**: One small field fixes every key at once, and shared files
never change, so their written meaning is a stable identity.

**Alternatives considered**: Keying by English only (homographs such as
"bank" with two blocks would collide); rewriting the other stores on
each correction (three stores, three failure points).

## R5. Where corrections and check status are kept

**Decision**: A hidden `.corrections.json` beside the word files, one
per folder, like `.examples.json`:
- `vocabulary/.corrections.json` for the shared sets: the **overlay**
  (corrected values per word, applied by the loader for every learner,
  FR-009), the checked fingerprints and the records;
- `word-lists/<account>/.corrections.json` for a learner's own lists:
  checked fingerprints and records only (the values go into the list
  files, as spec 021 does for examples).

Written atomically (temp file + `os.replace`) under a per-file lock;
records keep the newest 500. Format: [contracts/corrections-file.md](contracts/corrections-file.md).

**Rationale**: Shared vocabulary files are never edited (project rule,
FR-009, SC-006); the examples precedent means the shared folder already
accepts a hidden JSON file, and the loader already skips non-`.md`
files.

**Alternatives considered**: A `checked:` line inside each own-list
block (spreads bookkeeping into learners' files and still needs a record
store for undo); one global database file (no precedent in the project).

## R6. "Already checked" (FR-006, SC-005)

**Decision**: A word's **fingerprint** is a hash of its file name,
group, English, IPA, meaning and parts of speech. After a check the
fingerprint of the values the word now has (corrected or unchanged) is
stored as checked. A word is sent only if its current fingerprint is not
in the checked set. An undo stores the restored values' fingerprint too,
so the word isn't sent again and the undone change can't come back
(FR-005). Editing a word (new upload, hand edit) changes its fingerprint,
so it is checked again.

A failed check stores nothing, so the word is retried next time it comes
up. For a shared word the fingerprint of the values sent is stored too, so
another learner whose session loaded the word before the correction
doesn't send it again.

**Rationale**: Content-based, so it needs no hook into every place a list
can change, and it survives restarts.

## R7. Applying a correction safely (FR-012)

**Decision**: Own list: under the account's list lock, find the block by
English **and the exact values that were sent**; if it no longer
matches (edited, removed), drop the correction. Otherwise replace only
`ipa`, `chinese` and `pos` (reusing `_updated_block`'s rules), leaving
every other line, example lines included, as it was. Shared: under the
`.corrections.json` lock, set the overlay for that word only if the
word's current effective values still equal the values sent.

Only fields whose value actually changed are recorded; an answer equal
to the current values records nothing (spec Story 1, scenario 3).
Values are compared after normalising (IPA without slashes, parts of
speech as labels, meaning trimmed).

## R8. Pausing after a provider failure (FR-010)

**Decision**: The service remembers the last provider failure:
- `auth` (key rejected): checks pause until the server restarts, since
  the key won't fix itself;
- `unavailable`, `rate_limited`, `timeout`: checks pause for **5
  minutes**;
- `bad_reply`, `bad_status`: that word only; no pause.

The reason (QwenError's fixed message) is shown on the corrections
page. Practice is never interrupted.

## R9. Turning the feature on

**Decision**: `create_app` always builds the service, but it checks
words only when `QwenConfig.from_env()` returns a config (`enabled`);
otherwise no checks run, the corrections page says "Qwen is not set up",
earlier corrections can still be listed and undone, and everything else
is as before (FR-014). `python -m src.web` prints `Corrections: on
(qwen3.8-flash)` or `Corrections: off (set DASHSCOPE_API_KEY)`.
Shared-set overlays still apply without a key, so corrections made
earlier keep showing.

## R10. Measuring quality before relying on it (SC-001, SC-002)

**Decision**: `src/tools/eval_corrections.py` runs the check (no saving)
over a reviewed fixture `tests/fixtures/word_check_cases.yml`: 50 words
with a known error and the right values, and 50 words that are already
right. It reports errors fixed (target ≥ 90%) and right words changed
for the worse (target ≤ 5%, judged against the fixture's accepted
values). It needs a key and is run by hand, like `eval_voice`; tests
cover it with a fake checker.

## R11. Data sent to Qwen (FR-013, Principle III)

Only the English word, its current IPA, meaning, parts of speech and the
dialect line. No account name, list name, progress, example sentences,
recordings or attempts. This is the one place the project sends data
off the machine; the user asked for it explicitly (spec Assumptions).
Example sentences and voice stay local.
