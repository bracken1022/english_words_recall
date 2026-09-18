# Feature Specification: Vocabulary Recall Tutor

**Feature Branch**: `001-vocab-recall-tutor`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Build a local English-learning tutor for Chinese speakers. The app should: show a Chinese meaning, ask the learner to recall the English expression, ask the learner to make a sentence, use a local LLM to correct grammar and naturalness, use Markdown files instead of a database"

## Clarifications

### Session 2026-09-18

- Q: Should the recall-matching check accept minor spelling mistakes, or only exact matches (plus the alternate expressions already authored per item)? → A: Exact match only (case-insensitive, whitespace-tolerant) against the item's authored expression(s) — no typo tolerance.
- Q: Should each practice session always run through the entire vocabulary pool, or can the learner pick a subset (e.g., a lesson/tag) first? → A: Learner can filter by lesson/tag before starting a session; filtering to "all" remains the default.
- Q: Once a session is underway, can the learner skip an item or go back to a previous one, or must they move strictly forward? → A: Strictly forward, one item at a time — no skip, no back; submitting blank counts as an attempt and advances.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recall the English Expression (Priority: P1)

A Chinese-speaking learner is shown the Chinese meaning of a target English word or
phrase and must type the English expression from memory, without seeing it first.

**Why this priority**: This is the core recall drill the whole product exists to
deliver. Without it there is no product; every other capability builds on top of a
vocabulary item being presented and answered.

**Independent Test**: Can be fully tested by loading a vocabulary set, presenting one
item's Chinese meaning, typing an English answer, and confirming the system tells the
learner whether it was correct — with no sentence-writing or LLM correction involved.

**Acceptance Scenarios**:

1. **Given** a vocabulary item with a Chinese meaning and its correct English
   expression, **When** the learner is presented the item, **Then** only the Chinese
   meaning is shown and the English expression is hidden until an answer is submitted.
2. **Given** the learner has submitted an answer, **When** it matches the correct
   English expression (per the matching rule in FR-004), **Then** the system marks the
   attempt correct and reveals the accepted expression.
3. **Given** the learner has submitted an answer, **When** it does not match, **Then**
   the system marks the attempt incorrect and reveals the correct expression.
4. **Given** the learner submits an empty answer, **When** they confirm submission,
   **Then** the system treats it as incorrect and reveals the correct expression
   without erroring.

---

### User Story 2 - Practice the Expression in a Sentence (Priority: P2)

After recalling (or being shown) the English expression, the learner writes an
original sentence using it, and a local LLM reviews the sentence for grammar and
naturalness, returning feedback the learner can act on.

**Why this priority**: This is what turns a vocabulary flashcard drill into language
*production* practice — the stated differentiator of this tutor — but it depends on
Story 1 having already surfaced the target expression.

**Independent Test**: Can be fully tested by supplying a target expression and a
learner-written sentence directly to the correction step and confirming the system
returns a grammar/naturalness assessment and, when applicable, a corrected version.

**Acceptance Scenarios**:

1. **Given** the learner has answered the recall step (correctly or not), **When**
   they are prompted for a sentence, **Then** the system asks them to write one
   original sentence that uses the target English expression.
2. **Given** a learner-submitted sentence, **When** it is sent for correction,
   **Then** the local LLM returns a grammaticality/naturalness judgment and, if issues
   are found, a corrected version of the sentence plus a plain-language explanation of
   what changed.
3. **Given** a learner-submitted sentence that is already correct and natural,
   **When** it is corrected, **Then** the system tells the learner it is correct
   rather than inventing unnecessary changes.
4. **Given** the sentence does not actually use the target expression, **When** it is
   submitted, **Then** the system tells the learner the target expression is missing
   before or alongside the grammar feedback.
5. **Given** the local LLM is not running or unreachable, **When** the learner submits
   a sentence, **Then** the system tells the learner correction is unavailable rather
   than hanging indefinitely or crashing, and lets them continue to the next item.

---

### User Story 3 - Author and Track Vocabulary as Markdown (Priority: P3)

A learner (or content author) adds, edits, or reviews vocabulary items and their own
practice history by reading and editing plain Markdown files, without needing a
database, server, or special editor.

**Why this priority**: This is the storage/authoring model the whole feature is
committed to. It's lower priority than the two learning interactions themselves
because the app can launch with a fixed starter vocabulary set, but the app is not
"done" until content and progress are genuinely just Markdown files.

**Independent Test**: Can be fully tested by hand-editing a vocabulary Markdown file
to add a new item, restarting the app, and confirming the new item appears in
practice — and separately, by completing a practice session and confirming the
learner's history is readable as Markdown afterward.

**Acceptance Scenarios**:

1. **Given** a new vocabulary item is added by editing a Markdown file, **When** the
   app is (re)started, **Then** the new item is available for practice.
2. **Given** a vocabulary Markdown file has a malformed or incomplete entry, **When**
   the app loads vocabulary, **Then** the system skips or flags that entry with a
   clear message rather than failing to load the rest of the set.
3. **Given** a learner has completed one or more practice attempts, **When** they (or
   anyone) open the progress files in a plain text editor, **Then** the attempt
   history (item, answer, correct/incorrect, timestamp) is readable without needing
   the app.

---

### Edge Cases

- What happens when the vocabulary set is empty (no Markdown items found)?
- How does the system handle a learner submitting a sentence with only the target
  expression and no other words (e.g., just repeating the word itself)?
- How does the system handle extremely long sentence submissions?
- What happens if two vocabulary Markdown files define the same English expression
  with different Chinese meanings?
- How does the system behave if the local LLM returns an empty or malformed response?
- What happens if the progress Markdown file is manually edited into an invalid state
  between sessions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load vocabulary items from Markdown files stored on the
  learner's local filesystem; no database or remote content service is used.
- **FR-002**: System MUST present a vocabulary item to the learner by showing only its
  Chinese meaning, keeping the English expression hidden until the learner submits an
  answer.
- **FR-003**: System MUST let the learner submit a free-text English answer for the
  currently presented item.
- **FR-004**: System MUST judge a submitted answer as correct if it matches the
  vocabulary item's accepted English expression(s) under a case-insensitive,
  whitespace-tolerant comparison; each vocabulary item MAY list more than one accepted
  expression (e.g., synonyms) authored directly in its Markdown entry. The comparison
  MUST be exact (no typo/fuzzy tolerance) — a misspelled answer is judged incorrect
  even if close to an accepted expression.
- **FR-005**: System MUST reveal the correct English expression(s) to the learner
  immediately after they submit an answer, regardless of whether it was correct.
- **FR-006**: System MUST, after the recall step, prompt the learner to write one
  original sentence that uses the item's target English expression.
- **FR-007**: System MUST send the learner's sentence, together with the target
  expression, to a locally running LLM for grammar and naturalness review.
- **FR-008**: System MUST display the LLM's feedback to the learner, including at
  minimum: whether the sentence needed correction, a corrected version when it did,
  and a short explanation of what changed.
- **FR-009**: System MUST detect and inform the learner when their submitted sentence
  does not use the target expression.
- **FR-010**: System MUST inform the learner clearly and continue functioning (without
  crashing or hanging) when the local LLM is unavailable or returns an error.
- **FR-011**: System MUST record each practice attempt (vocabulary item, submitted
  answer, correct/incorrect, submitted sentence, LLM feedback summary, timestamp) to a
  Markdown-based progress log on the local filesystem.
- **FR-012**: System MUST allow a person to add or modify vocabulary items by editing
  Markdown files directly, with changes reflected the next time the app loads content
  (no rebuild or migration step required).
- **FR-013**: System MUST tolerate a malformed or incomplete entry in a vocabulary
  Markdown file by skipping/flagging that entry with a clear message, rather than
  failing to load the rest of the vocabulary set.
- **FR-014**: System MUST operate fully on the learner's local machine, requiring no
  network access other than communicating with the local LLM.
- **FR-015**: System MUST let the learner filter which vocabulary items to include in
  a practice session by lesson/unit grouping (as authored on each item), defaulting to
  the entire vocabulary pool when no filter is selected.
- **FR-016**: System MUST present items strictly one at a time, in forward order only,
  within a session; the system MUST NOT offer a way to skip an item without submitting
  an answer, or to return to a previously answered item.

### Key Entities

- **Vocabulary Item**: A single English expression to be learned. Attributes: the
  target English expression, one or more accepted alternate English forms, its
  Chinese meaning, and an optional grouping (e.g., lesson/unit) used to filter which
  items a session includes. Stored as an entry within a Markdown file.
- **Practice Attempt**: One learner interaction with a Vocabulary Item. Attributes:
  which item, the learner's recall answer, whether the recall was judged correct, the
  learner's written sentence, the LLM's correction/feedback summary, and when it
  happened. Stored as an entry appended to a Markdown-based progress log.
- **Learner Progress Log**: The learner's cumulative history of Practice Attempts,
  used to show what has been practiced and how it went. Stored as Markdown file(s) on
  the local filesystem, human-readable without the app.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can go from seeing a vocabulary item's Chinese meaning to
  receiving grammar/naturalness feedback on their own sentence within a single
  uninterrupted session, without leaving the app.
- **SC-002**: A person can introduce a brand-new vocabulary item into practice by
  editing exactly one Markdown file and restarting the app — no other file, tool, or
  step is required.
- **SC-003**: 100% of vocabulary content and learner progress data remains readable as
  plain Markdown text using any ordinary text editor, with no proprietary or binary
  storage involved.
- **SC-004**: When the local LLM is unavailable, learners can still complete the
  recall step for every vocabulary item; only the sentence-correction feedback is
  affected.
- **SC-005**: A learner reviewing their progress log can determine, for any past
  attempt, which item it was, what they answered, and what the correction feedback
  said, without consulting the app.

## Assumptions

- This is a single-learner, single-machine tool: no multi-user accounts,
  authentication, or network sync are in scope for this feature.
- "Local LLM" means a language model the learner already has running/available on
  their own machine; installing, downloading, or configuring that LLM is outside this
  feature's scope — the feature only needs to call it and handle its response.
- The app ships with (or the learner supplies) at least one vocabulary Markdown file
  to start from; generating vocabulary content from scratch is out of scope.
- Within the selected set of items (all items, or those matching a chosen lesson/tag
  filter), presentation order is a simple pass (e.g., sequential or random) rather
  than a spaced-repetition scheduling algorithm; smarter scheduling can be layered on
  later without changing this feature's scope.
- Pronunciation, listening, or audio practice is out of scope — this feature covers
  written recall and written sentence production only.
- The learner's practice attempts are appended to the progress log indefinitely; no
  automatic pruning, rotation, or size limit is defined for this feature.
