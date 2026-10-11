# Feature Specification: Example Sentences Instead of Sentence Review

**Feature Branch**: `021-example-sentence`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Actually, we can think about to remove the sentence review part. Instead of it, I suggest to let llm generate a sentence for that word. The sentence should be very nature. Then let user recall the sentence if he want"

## Context

Today, after recalling a word in "Sentence" mode, the learner writes (or
says) their own sentence with it, and the local model reviews that
sentence for grammar and naturalness (specs 001, 002, 009, 010). The
learner finds this step heavier than it is worth. They would rather
**see a natural example sentence** that uses the word, written by the
local model, and **optionally practice recalling that sentence**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a natural example sentence for each word (Priority: P1)

After the learner recalls a word (right or wrong), the tutor shows a short,
natural English sentence that uses the word the way native speakers do,
with its Chinese translation, so the learner sees the word in context.

**Why this priority**: This replaces the sentence review that is being
removed; it is the core of the request.

**Independent Test**: Practice any word; after answering, an example
sentence containing the word (or its accepted form) is shown with a
Chinese translation, and no "write a sentence" step appears.

**Acceptance Scenarios**:

1. **Given** the learner has answered a word, **When** the answer is
   revealed, **Then** an example sentence using that word, with its
   Chinese translation, is shown along with the word's pronunciation and
   part of speech.
2. **Given** a word with several meanings, **When** its example is shown,
   **Then** the sentence uses the word in one of the meanings the learner
   studies (its recorded Chinese meaning), not an unrelated sense.
3. **Given** the local AI is not running, **When** a word has no example
   yet, **Then** practice continues normally with a short note that no
   example is available, and nothing else breaks.
4. **Given** the same word comes up again later, **When** its answer is
   revealed, **Then** the same example sentence is shown again (it does
   not change every time) unless the learner asks for a new one.

---

### User Story 2 - Practice recalling the example sentence (optional) (Priority: P2)

A learner who wants extra practice can recall the example sentence, not
just the word. They see the sentence's Chinese translation, try to say or
type the English sentence from memory, then reveal the example and mark
themselves "Got it" or "Not yet". There is no automatic grading.

**Why this priority**: Optional extra practice; seeing the example (US1)
already delivers most of the value.

**Independent Test**: Turn on sentence recall and answer a word. The
Chinese translation is shown with the English sentence hidden. Type an
attempt (optional), reveal the sentence, and mark "Got it". The mark is
saved in the history and the session moves on. With sentence recall off,
no extra step appears.

**Acceptance Scenarios**:

1. **Given** the learner chose to practice sentences, **When** a word's
   answer is revealed, **Then** the sentence-recall step follows before
   the next word.
2. **Given** the learner did not choose it, **When** a word's answer is
   revealed, **Then** the session goes straight to the next word after
   the example.
3. **Given** the sentence-recall step, **When** the learner skips it,
   **Then** the session moves on without counting anything against them.
4. **Given** the sentence-recall step, **When** the learner reveals the
   sentence, **Then** their own attempt (if they typed one) is shown next
   to the example. They choose "Got it" or "Not yet", and that self-mark
   is recorded.
5. **Given** a word with no example available, **When** sentence recall
   is on, **Then** the step is skipped for that word.

---

### User Story 3 - Sentence review is gone (Priority: P1)

The old "write your own sentence and have it reviewed" step, and its
voice input, no longer appear anywhere in practice.

**Why this priority**: Explicitly requested; leaving both flows would be
confusing.

**Independent Test**: The practice-mode choice offers no "write a sentence"
option, no sentence is sent for review in any mode, and existing practice
history still loads.

**Acceptance Scenarios**:

1. **Given** the word-set screen, **When** the learner picks how to
   practice, **Then** the choices are "Recall only" and "Recall + example
   sentence" (plus sentence recall per US2), with no sentence-writing
   option.
2. **Given** older practice history that contains reviewed sentences,
   **When** it is read, **Then** it still loads and is kept unchanged.

---

### Edge Cases

- The model's sentence does not actually contain the word (or a form of
  it): it is not shown; the word is treated as having no example and
  generation can be retried later.
- The sentence is too long, contains more than one sentence, or the
  translation is missing: rejected the same way.
- Multi-word expressions (*tend to*, *give up*) appear in the sentence as
  a natural inflected form (*tends to*, *gave up*).
- A word removed by the learner (spec 020) loses its example with it.
- Content safety: sentences must be suitable for a household learner — no
  offensive or adult content; anything flagged is discarded.
- The command-line tutor follows the same change (no sentence review;
  examples shown when available).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The sentence-writing step, its review by the local model,
  and its voice input MUST be removed from practice in the web UI and the
  command-line tutor.
- **FR-002**: After each word's answer is revealed, the tutor MUST show an
  example sentence that uses the word, with a Chinese translation, when
  one is available.
- **FR-003**: Example sentences MUST be generated by the existing local
  model only (no cloud service), MUST be short (one sentence, at most 20
  words), natural, everyday English, and MUST use the word in its
  recorded meaning.
- **FR-004**: A generated example MUST be checked before it is kept: it
  contains the word (or an inflected form of it), is a single sentence
  within the length limit, has a non-empty Chinese translation, and
  passes a content-safety check; otherwise it is discarded.
- **FR-005**: An example MUST be generated the first time a word is
  practiced (preparation starts as soon as the word appears, so it is
  usually ready by the time the answer is revealed) and then saved, so the
  same example is shown in every later session. The learner MUST be able
  to ask for a different one, which replaces the saved example.
- **FR-006**: Sentence recall (US2) MUST be self-checked: it shows the
  Chinese translation and hides the English sentence; an optional typed
  attempt; a reveal that shows the example (and the attempt next to it);
  and the learner's own "Got it" / "Not yet" mark, which is recorded in
  the history.
- **FR-007**: If no example can be produced (model unavailable or output
  rejected), practice MUST continue without one, with a short note.
- **FR-008**: Practice MUST offer a choice between recall only, and
  recall plus example sentence (the default), plus the optional
  sentence recall of US2.
- **FR-009**: Existing practice history MUST stay readable and unchanged;
  new history entries record the word attempt as today (and the sentence
  recall result when US2 is used).

### Key Entities

- **Example Sentence**: an English sentence for one vocabulary entry, its
  Chinese translation, and when it was made; belongs to that entry.
- **Vocabulary Entry**: existing, gains an optional example sentence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After answering, the learner sees the word's example
  sentence in under 1 second whenever it has already been saved. On a
  word's first practice, it appears within 5 seconds of the answer, or a
  "no example" note does.
- **SC-002**: In a reviewed sample of 50 generated examples, at least 95%
  are judged natural, correct, and in the recorded meaning; 0 contain
  unsafe content.
- **SC-003**: 100% of shown examples contain the target word or an
  inflected form of it.
- **SC-004**: 0 sentence-review steps or requests remain in any practice
  mode.
- **SC-005**: All existing practice history files still load with 0 errors.

## Clarifications

### Session 2026-10-11

- Q: What does "recall the sentence" look like? → A: Self-check. Show
  the Chinese translation, let the learner say or type the sentence from
  memory, reveal the example, and let them mark "Got it" or "Not yet".
- Q: When are examples generated? → A: The first time each word is
  practiced, then saved. There is no up-front fill.

## Assumptions

- "Remove the sentence review part" covers writing your own sentence, the
  model's review of it, and voice input for it; recall-only practice and
  everything else stay.
- The local model used today (and its "thinking" disabled) generates the
  examples; quality is checked with a reviewed reference sample before
  release, as in specs 018/019 (Constitution II).
- One example per word is enough; the learner can request a new one.
- Examples for words in a learner's own lists are saved in those lists.
  The shared word sets stay operator-maintained: their examples are saved
  in a separate examples store shared by all learners, never by editing
  the shared files.
- Because examples are generated during practice, they aren't reviewed
  by a person before they're shown. Quality relies on the automatic
  checks (FR-004) and on a reviewed sample of generated examples measured
  before release (SC-002, Constitution II).
