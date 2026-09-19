# Feature Specification: Confirm Before Skipping a Word Without a Sentence

**Feature Branch**: `006-confirm-skip-word`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "If user did not give the sentence, can just pop up a message to confirm user want to skip this word."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirm before skipping an unwritten sentence (Priority: P1)

A learner reaches the "write a sentence" step for a word, but doesn't want to (or can't think of one) and tries to move on without typing anything. Instead of silently accepting an empty sentence and sending it off for correction, the app asks the learner to confirm they want to skip this word before doing anything else.

**Why this priority**: Without this, an empty sentence is currently treated like a real one — it gets sent for correction and recorded as if the learner had attempted it, which is misleading and wastes a correction request on nothing. This is the core behavior being requested.

**Independent Test**: Can be fully tested by opening the sentence-writing step, leaving the input empty, and submitting — a confirmation prompt must appear before any other action is taken, and can be verified in isolation from every other part of the app.

**Acceptance Scenarios**:

1. **Given** the learner is on the "write a sentence" step with an empty input, **When** they submit the form, **Then** a confirmation prompt appears asking whether they want to skip this word, and no sentence-correction request is made.
2. **Given** the learner is on the "write a sentence" step with an input containing only spaces, **When** they submit the form, **Then** the same confirmation prompt appears (whitespace-only counts as no sentence given).
3. **Given** the confirmation prompt is showing, **When** the learner confirms they want to skip, **Then** the session moves on to the next word (or to the session-complete screen, if this was the last word) without ever showing sentence-correction feedback for the skipped word.
4. **Given** the confirmation prompt is showing, **When** the learner declines/cancels, **Then** they remain on the same word's sentence-writing step, free to type and submit a real sentence, and nothing about the session's progress has changed.
5. **Given** the learner types a non-empty sentence, **When** they submit the form, **Then** no confirmation prompt appears and the sentence is reviewed exactly as it is today.

---

### User Story 2 - Skipped words still show up correctly afterward (Priority: P2)

A learner who skipped the sentence step for one or more words wants the session's end-of-session summary and saved practice history to make sense — the word's recall result should still count, and it should be clear later that the sentence step was skipped rather than completed.

**Why this priority**: This is what makes skipping trustworthy rather than a way to lose track of progress; it depends on User Story 1 existing first, so it's ranked second.

**Independent Test**: Can be tested by skipping at least one word in an otherwise-normal session and confirming the end-of-session summary and saved history both reflect it accurately.

**Acceptance Scenarios**:

1. **Given** a learner answered a word's Chinese-to-English recall step correctly and then skipped the sentence step, **When** the session ends, **Then** that word still counts toward the "words recalled correctly" total in the end-of-session summary.
2. **Given** a learner skipped the sentence step for a word, **When** their saved practice history is reviewed later, **Then** that word's entry is distinguishable from a word where a sentence was actually submitted.

---

### Edge Cases

- What happens if the learner confirms skipping on the very last word of the session? The session must reach the normal "session complete" screen, the same as finishing any other last word.
- What happens if the learner opens the confirmation prompt and then changes their mind? Declining must leave them exactly where they were, with the sentence-writing step still active and nothing about session progress changed.
- What happens if the learner had typed something and then deleted it all before submitting? Same as never having typed anything — this is treated as no sentence given.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect, at the moment the learner submits the sentence-writing step, whether the sentence field is empty or contains only whitespace.
- **FR-002**: When the sentence field is empty or whitespace-only at submission, the system MUST show a confirmation prompt asking the learner to confirm they want to skip the current word, before taking any other action.
- **FR-003**: The system MUST NOT send an empty or whitespace-only sentence for correction/grading.
- **FR-004**: If the learner confirms skipping, the system MUST advance the session to the next word, or to the session-complete screen if this was the last word, without requiring a sentence and without showing sentence-correction feedback for the skipped word.
- **FR-005**: If the learner declines or dismisses the confirmation prompt, the system MUST leave the learner on the current word's sentence-writing step with the session state unchanged, so they can write and submit a sentence normally.
- **FR-006**: The system MUST record the word's recall outcome (correct/incorrect) for a skipped word exactly as it does for any other word, unaffected by the skip.
- **FR-007**: The system MUST record, in the learner's saved practice history, that a word's sentence step was skipped, distinguishably from a word where a sentence was actually submitted.
- **FR-008**: A non-empty sentence (anything other than empty/whitespace-only) MUST continue to be submitted for correction exactly as it works today, with no confirmation prompt.

### Key Entities *(include if feature involves data)*

- **Practice Attempt**: The existing record of a learner's attempt at one word (already includes the recall answer and correctness). This feature adds the possibility that its sentence-related information is absent because the step was skipped, rather than because it hasn't happened yet.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of sentence-step submissions with an empty or whitespace-only sentence show a confirmation prompt and trigger zero correction requests.
- **SC-002**: A learner who confirms a skip reaches the next word (or the completion screen) in a single additional action, with no other input required.
- **SC-003**: A learner who declines a skip prompt returns to the same word with the session otherwise completely unchanged, 100% of the time.
- **SC-004**: End-of-session recall-accuracy summaries remain fully accurate for sessions that mix skipped and completed words, matching what a manual count of recall answers would show.

## Assumptions

- The confirmation prompt is a simple yes/no confirmation (its exact visual treatment is a design/implementation choice); what matters is that it clearly asks the learner to confirm before skipping.
- Whitespace-only input is treated the same as empty input for the purposes of triggering the skip confirmation.
- Skipping the sentence step does not requeue the word for another attempt later in the same session — the session continues through the word list the same way it already does today.
- This feature only applies to the sentence-writing step; it does not add a way to skip the earlier Chinese-to-English recall step, which is unaffected.
- The app remains single-learner, unauthenticated, and local-only; this feature does not change that.
- Two earlier specs (`001-vocab-recall-tutor` FR-016, `003-web-ui` FR-010) say the learner must not be able to "skip an unanswered item." Read narrowly, that rule is unaffected here: by the time the sentence-writing step exists at all, the learner has already answered the recall step for this item (right or wrong). This feature only ever lets them skip the follow-on sentence, never the item's recall answer, and it introduces no way to move backward. This is a deliberate, narrow exception to those two requirements' "no skip" wording and is called out explicitly rather than silently reinterpreted.
- This feature applies to the web UI only. The CLI (`src/cli/session.py`) documents its own "no skip/back" design for the same reason and is intentionally left unchanged.
