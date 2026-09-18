# Feature Specification: Web UI State & Feedback Polish

**Feature Branch**: `004-web-ui-ux-polish`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Update the existing web UI feature with UX requirements covering:
(1) the word-answer input and its submit button must be visually grouped as one form section, not
detached; (2) word-answer feedback must use both color (green/red) and explicit text
('Correct'/'Incorrect'), never color alone; (3) the sentence-practice section must stay hidden
until after the vocabulary answer is submitted, then show regardless of correctness; (4)
'Reviewing your sentence...' and its spinner must be visible only while a review request is
actually in progress — not before submission, not after completion or failure — and duplicate
sentence submissions must be prevented while one is in flight; (5) the page must render according
to the current learning state (vocabulary question+input → word feedback+sentence input → sentence
submitted+loading → review result+Continue), never showing all controls at once. Existing learning
logic and Ollama integration must remain unchanged."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The page always shows exactly one step's controls (Priority: P1)

At every point in a practice cycle, the learner sees only the controls
relevant to what's happening right now — the vocabulary question and its
input, or the word feedback and sentence input, or the sentence-review
loading state, or the review result and a Continue control — never more
than one of these areas at once, and never a page with nothing actionable
on it while an item is active.

**Why this priority**: This is the structural foundation every other
requirement in this feature depends on. A page that shows multiple steps'
controls at once (or the wrong one) is confusing regardless of how good any
individual piece of feedback looks, and it's the failure mode most likely
to make the tutor feel broken.

**Independent Test**: Drive the existing web UI through a full cycle
(load → submit word answer → submit sentence → review completes) and, at
each point, inspect what's visible: confirm exactly one of the four areas
above is shown, and that the sentence-review loading state is visible only
for the span of an actual in-progress request.

**Acceptance Scenarios**:

1. **Given** a vocabulary item has just been presented, **When** the page is
   in that state, **Then** only the vocabulary question and its answer
   input are shown — the sentence-practice section is not visible anywhere
   on the page.
2. **Given** the learner has submitted a word answer, **When** it has been
   graded — whether correct or incorrect — **Then** the word feedback and
   the sentence-practice section (prompt and input) are both shown; the
   sentence section's visibility does not depend on whether the word
   answer was correct.
3. **Given** the learner submits a sentence, **When** the review request
   begins, **Then** the sentence-submission control is replaced or disabled
   (so a second submission cannot be sent while this one is outstanding),
   and the loading indicator plus "Reviewing your sentence..." are shown.
4. **Given** a sentence review is in progress, **When** it completes or
   fails, **Then** the loading indicator and "Reviewing your sentence..."
   are hidden immediately, replaced by the review result (or a failure
   message) and a Continue control.
5. **Given** no sentence review is currently in progress (before one has
   been submitted, or after one has completed or failed), **When** the page
   is inspected, **Then** "Reviewing your sentence..." and the loading
   indicator are not visible.

---

### User Story 2 - Word-answer feedback is clear without relying on color alone (Priority: P2)

After submitting a word answer, the learner sees feedback that is
unambiguous even without perceiving color: explicit wording ("Correct" or
"Incorrect...") paired with a supporting color (green for correct, red for
incorrect).

**Why this priority**: This makes one specific, already-shown piece of
information (was I right?) unambiguous and accessible. It depends on User
Story 1 already putting the feedback in the right place at the right time,
but is independently valuable and testable on its own.

**Independent Test**: Submit a correct word answer and an incorrect one,
and confirm each result includes both a distinct color and explicit
correct/incorrect wording — verifiable by reading the text alone, without
needing to distinguish the color.

**Acceptance Scenarios**:

1. **Given** the learner submits a correct word answer, **When** feedback is
   shown, **Then** it appears in green and explicitly states it was correct
   (e.g., "Correct: tailor").
2. **Given** the learner submits an incorrect word answer, **When** feedback
   is shown, **Then** it appears in red and explicitly states it was
   incorrect along with the correct expression (e.g., "Incorrect. The
   correct expression is: tailor").
3. **Given** a learner who cannot distinguish the two colors, **When** they
   read the feedback text alone, **Then** they can still determine whether
   the answer was correct — color is never the only signal.

---

### User Story 3 - The word-answer input and its submit control read as one unit (Priority: P3)

The vocabulary-answer input field and the button used to submit it are
visually grouped together as a single, cohesive form section, rather than
appearing as two unrelated elements on the page.

**Why this priority**: Pure layout polish with no behavior change — lowest
risk, and valuable on its own regardless of whether Stories 1-2 are also
in place, but least critical of the three.

**Independent Test**: View the vocabulary-question step and confirm the
input and its submit control are presented together as one section (e.g.,
adjacent, aligned, and clearly connected), at both desktop and phone
widths.

**Acceptance Scenarios**:

1. **Given** the vocabulary-question step is shown, **When** the learner
   looks at the answer input, **Then** its submit control is presented
   immediately alongside it as one visual unit, not separated by unrelated
   spacing or content.
2. **Given** the page is viewed at phone width, **When** the same step is
   shown, **Then** the input and submit control remain visually grouped
   rather than appearing detached from each other.

---

### Edge Cases

- What happens if the learner tries to submit a second sentence while a
  review is already in progress (e.g., a double-click, or pressing Enter
  twice)? The sentence-submission control is disabled for the duration of
  the in-flight request, so the second attempt has no effect and no second
  request is sent (FR-008).
- What happens when the review fails or the local LLM is unavailable — does
  a Continue control still appear? Yes: an unavailable/failed review counts
  as "the review has concluded" for the purpose of showing the result and
  Continue control, matching the existing tutor's behavior of always
  letting the learner proceed.
- What happens on a very fast review (completes almost instantly)? The
  loading state is shown and cleared for exactly as long as the real
  request takes — no minimum display duration is added, and it is not
  skipped inconsistently either (carried over from the existing
  loading-indicator behavior this feature does not change).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST show, at any moment while a vocabulary item
  is active, exactly one of the following as the page's primary
  interactive area: the vocabulary-answer input, the sentence-practice
  input, the sentence-review loading state, or the review result with its
  Continue control — never more than one simultaneously, and never none.
- **FR-002**: The system MUST NOT show the sentence-practice section
  (prompt and input) until after the learner has submitted their
  vocabulary answer for the current item.
- **FR-003**: The system MUST show the sentence-practice section
  immediately once the vocabulary answer is submitted, regardless of
  whether that answer was graded correct or incorrect.
- **FR-004**: The system MUST visually present the vocabulary-answer input
  and its submit control as one cohesive form section, such that the
  control never appears detached or unrelated to the input it submits.
- **FR-005**: After the vocabulary answer is graded, the system MUST show
  feedback that includes explicit text stating whether the answer was
  correct or incorrect together with the relevant expression (e.g.,
  "Correct: tailor" or "Incorrect. The correct expression is: tailor").
- **FR-006**: The system MUST display correct-answer feedback and
  incorrect-answer feedback in visually distinct colors (e.g., green for
  correct, red for incorrect), while never relying on color alone to convey
  the result (FR-005's text is always present alongside it).
- **FR-007**: The system MUST show the "Reviewing your sentence..." message
  and its loading indicator only for the span that a sentence-review
  request is actually in progress — never before a sentence has been
  submitted, and never after that review has completed or failed.
- **FR-008**: While a sentence-review request is in progress, the system
  MUST prevent the learner from submitting another sentence for review
  until that request has completed or failed.
- **FR-009**: The instant a sentence-review request completes or fails, the
  system MUST hide the loading indicator and "Reviewing your sentence..."
  and show the corresponding result or failure message in their place.
- **FR-010**: After a sentence-review request completes or fails, the
  system MUST show a control letting the learner continue to the next
  vocabulary item.
- **FR-011**: This feature MUST NOT change the existing vocabulary grading
  logic, the sentence-review request/response handling, or what is
  recorded to the progress log — every change here is to what is
  shown/hidden and how it is styled, not to any underlying behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At every point observed during a practice cycle, exactly one
  actionable control area is visible — zero instances of two step's
  controls appearing together, and zero instances of no actionable control
  being visible while an item is active.
- **SC-002**: 100% of vocabulary-answer feedback includes explicit
  "Correct"/"Incorrect" wording, independently understandable without
  perceiving color.
- **SC-003**: Zero instances of the sentence-practice section appearing
  before the vocabulary answer has been submitted, across any session.
- **SC-004**: Zero instances of "Reviewing your sentence..." or its loading
  indicator being visible outside the span of an actual in-progress review
  request.
- **SC-005**: Zero instances of two overlapping sentence-review requests
  being triggered from a single sentence submission.
- **SC-006**: A learner can identify the vocabulary-answer input and its
  submit control as one unit without visually searching the page for a
  separated button, at both desktop and phone widths.

## Assumptions

- This feature changes only the web UI's presentation layer (`003-web-ui`):
  what is shown, hidden, or styled, and when. It introduces no new
  endpoints, data, or changes to the existing vocabulary-grading or
  sentence-review pipeline (FR-011).
- The example feedback wording given in the request ("Correct: tailor",
  "Incorrect. The correct expression is: tailor") is adopted as the actual
  wording to show, replacing whatever slightly different phrasing the
  current web UI uses today.
- "Prevent duplicate sentence submissions" is satisfied by disabling the
  sentence-submission control for the duration of the in-flight request
  (per the request's own wording: "replace/disable sentence submission");
  no additional request-deduplication mechanism beyond that is required.
- No specific accessibility contrast ratio (e.g., a WCAG level) is
  mandated for the green/red feedback colors beyond FR-006's requirement
  that text, not color, carries the actual meaning; ordinary legible color
  choices are sufficient.
- Reloading the page mid-cycle continues to behave as already established
  for the web UI (`003-web-ui`'s Assumptions: a fresh pass through the
  vocabulary pool, no cross-session resume) — this feature does not change
  that.
