# Feature Specification: Fix Web UI State Visibility

**Feature Branch**: `005-fix-ui-visibility-bug`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "There are some issues need to be fixed: (1) remove the first line
'No vocabulary items are available for this session.'; (2) remove 'Session complete — you've gone
through every item.'; (3) 'Your answer' and 'Your sentence' can not be shown at the same time —
only after submitting your answer should 'Your sentence' show; (4) 'Reviewing your sentence...'
always exists — only show it when the user submits a sentence."

## User Scenarios & Testing *(mandatory)*

<!--
  All four reported symptoms trace to the same underlying pattern: content
  meant to be shown only for one specific learning state is instead visible
  regardless of state. Items 1 and 2 are interpreted as "these messages
  must not always be on screen" (they are still needed when their state
  genuinely applies — an empty vocabulary pool, or a finished session —
  since removing them entirely would leave the learner with no explanation
  in those cases) rather than "delete this text from the product forever."
  See Assumptions.
-->

### User Story 1 - Only the current step's question/answer content is shown (Priority: P1)

At any point in a practice session, the learner sees exactly one of: the
"no items available" message (only if the pool is genuinely empty), the
current vocabulary question with its answer input, the word feedback with
the sentence-writing prompt/input, or the "session complete" message (only
once every item has actually been finished) — never more than one of these
at the same time, and never one that doesn't currently apply.

**Why this priority**: This is the core defect. Right now the page shows
several states' content simultaneously, which is confusing and makes the
tutor feel broken regardless of any other issue — this has to be fixed for
the tutor to be usable at all.

**Independent Test**: Load the tutor with a non-empty vocabulary set and
step through a full cycle (question shown → answer submitted → sentence
submitted → review shown → continue), confirming at each point that only
that one step's content is visible on screen, and that neither the "no
items" nor "session complete" message appears until its state genuinely
occurs.

**Acceptance Scenarios**:

1. **Given** the vocabulary pool has items and the session is not yet
   complete, **When** the learner views the page at any point, **Then**
   "No vocabulary items are available for this session." is not visible
   anywhere on the page.
2. **Given** the learner has not yet finished every item in the session,
   **When** they view the page at any point, **Then** "Session complete —
   you've gone through every item." is not visible anywhere on the page.
3. **Given** a vocabulary item is being presented for recall, **When** the
   learner views the page, **Then** only the vocabulary question and its
   answer input are shown — the sentence-writing prompt and input are not
   visible.
4. **Given** the learner has just submitted their vocabulary answer,
   **When** the page updates, **Then** the sentence-writing prompt and
   input become visible and the vocabulary-answer input is no longer the
   active, visible input on the page — the two are never shown together.
5. **Given** the vocabulary pool is genuinely empty, **When** the learner
   opens the tutor, **Then** "No vocabulary items are available for this
   session." is shown (this message still exists for this real case).
6. **Given** the learner has genuinely finished every item, **When** the
   last item's review concludes and they continue, **Then** "Session
   complete — you've gone through every item." is shown (this message
   still exists for this real case).

---

### User Story 2 - The review-loading message only appears during an actual review (Priority: P2)

"Reviewing your sentence..." and its loading indicator are visible only
for the span that a sentence submitted for review is actually being
processed — not before a sentence has been submitted, and not after the
review has finished or failed.

**Why this priority**: A real but narrower defect than User Story 1 — one
specific element (the loading message) rather than the whole page's
structure. Worth its own story since it can be verified independently once
Story 1's step-visibility is correct.

**Independent Test**: Watch the sentence-practice step from before any
sentence is submitted, through submission, to the result being shown, and
confirm "Reviewing your sentence..." is absent, then present, then absent
again, tracking exactly with whether a review is actually in progress.

**Acceptance Scenarios**:

1. **Given** the learner has not yet submitted a sentence for review,
   **When** they view the sentence-practice step, **Then** "Reviewing your
   sentence..." and its loading indicator are not visible.
2. **Given** the learner has submitted a sentence, **When** the review is
   in progress, **Then** "Reviewing your sentence..." and its loading
   indicator are visible.
3. **Given** the review has completed or failed, **When** the result or
   failure message is shown, **Then** "Reviewing your sentence..." and its
   loading indicator are no longer visible.

---

### Edge Cases

- What happens with the already-existing automated tests that check these
  states by inspecting a flag/attribute rather than what actually renders
  on screen? Those tests may report success even though a real browser
  shows multiple states at once — this is why the bug shipped undetected;
  fixing it requires verifying actual on-screen rendering, not only the
  underlying flag's value (see Assumptions).
- What happens to the other, already-correct behaviors from prior work
  (word-feedback text and color, the duplicate-sentence-submission guard,
  input/button grouping, responsive layout at phone/tablet/desktop widths)
  when this fix is applied? None of them should change — this feature
  fixes visibility only, and must not regress anything already verified.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST NOT display "No vocabulary items are
  available for this session." unless the vocabulary pool is actually
  empty.
- **FR-002**: The system MUST NOT display "Session complete — you've gone
  through every item." unless the learner has actually completed every
  item in the current session's pool.
- **FR-003**: The system MUST show only the vocabulary-question and its
  answer input while the learner is being asked to recall the current
  item's English expression — the sentence-writing prompt and input MUST
  NOT be visible at the same time.
- **FR-004**: The system MUST show the sentence-writing prompt and input
  once the learner's vocabulary answer has been submitted, and the
  vocabulary-answer input MUST NOT remain the active, visible input at the
  same time.
- **FR-005**: The system MUST NOT display "Reviewing your sentence..." or
  its loading indicator before a sentence has been submitted for review.
- **FR-006**: The system MUST display "Reviewing your sentence..." and its
  loading indicator only for the span that a sentence-review request is
  actually in progress.
- **FR-007**: The system MUST hide "Reviewing your sentence..." and its
  loading indicator the instant the review completes or fails.
- **FR-008**: This fix MUST NOT change or regress any already-established
  behavior: vocabulary grading, the sentence-review pipeline, progress-log
  content, the persistent word-feedback text and color, the
  duplicate-sentence-submission guard, input/button grouping, or the
  responsive layout at any supported width.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At every point observed during a practice session, exactly
  one of the page's states (no-items, question+answer, feedback+sentence,
  review-loading, review-result+continue, session-complete) is visible —
  zero instances of two or more shown together.
- **SC-002**: "No vocabulary items are available for this session." is
  observed only in sessions where the pool is genuinely empty.
- **SC-003**: "Session complete — you've gone through every item." is
  observed only after every item in the session has genuinely been
  completed.
- **SC-004**: "Reviewing your sentence..." is visible for the entire span
  of an actual in-progress review and for none of the time before
  submission or after completion/failure.
- **SC-005**: A learner can always tell, from what's on screen alone,
  which single step they are currently on, without seeing two steps'
  prompts or two different completion-style messages at once.

## Assumptions

- Items 1 and 2 of the request are interpreted as "these messages must
  stop being shown when they don't apply," not "delete this text from the
  product." The empty-pool and session-complete states are still real,
  already-established cases (from prior work on this tutor) that the
  learner needs to be told about; this feature restores that they show
  *only* when genuinely applicable, per Acceptance Scenarios 5-6.
- All four reported symptoms are treated as one class of defect — content
  tied to a specific learning state staying visible outside that state —
  because that is the common pattern across all four reports (two
  messages that stay visible, one input that stays visible alongside
  another, and a loading message that stays visible). Resolving that
  shared pattern is assumed to be a reasonable, unified fix rather than
  four unrelated ones.
- The step-visibility, word-feedback persistence, duplicate-submission
  guard, and responsive-layout behaviors already specified in this
  project's prior work remain the intended behavior; this feature exists
  because the *implementation* did not actually deliver on what was
  already specified, not because the specification itself needs to
  change.
