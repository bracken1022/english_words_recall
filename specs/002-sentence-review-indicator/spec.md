# Feature Specification: Sentence-Review Loading Indicator

**Feature Branch**: `002-sentence-review-indicator`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Update the current vocabulary-practice feature with this UX
improvement: when the application is waiting for the local LLM to review the learner's
sentence, show a visible loading indicator so the learner knows the application is still
working. Requirements: the indicator should appear immediately after the learner submits a
sentence; it should remain visible while the Ollama request is in progress; it should
disappear when the review completes or fails; do not show a fake percentage unless actual
progress is available; for the CLI version, prefer a spinner or similar indeterminate loading
indicator; the learning behavior and sentence-review logic must remain unchanged."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See that the app is still working while a sentence is reviewed (Priority: P1)

A learner submits their sentence for correction and, while the app is waiting on the
local LLM's review (which can take several seconds or longer depending on the model),
sees a clearly visible, continuously moving indicator confirming the app is still
working — rather than a silent, unchanging screen that looks frozen or crashed.

**Why this priority**: This is the entire point of the feature. Today, nothing is
shown between the sentence being submitted and the correction feedback appearing;
on a slow local model that gap can be long enough that a learner reasonably wonders
whether the app has hung. This is the one behavior that must exist for the feature
to have shipped at all.

**Independent Test**: Can be fully tested by submitting a sentence while the review
call is deliberately held open (e.g., a slow or delayed response) and confirming a
visibly animating indicator is on screen for the entire wait, appearing right after
submission with no noticeable gap.

**Acceptance Scenarios**:

1. **Given** the learner has just submitted a sentence for review, **When** the app
   begins waiting on the local LLM's response, **Then** a visible, indeterminate
   loading indicator (e.g., a spinner) appears immediately, with no perceptible delay.
2. **Given** the loading indicator is showing, **When** the review request is still in
   progress, **Then** the indicator keeps animating for as long as the wait lasts —
   it never freezes on a single static frame or disappears prematurely while the
   request is still outstanding.
3. **Given** the loading indicator is showing, **When** it is displayed, **Then** it
   never shows a percentage, a step count, or any other specific progress measurement,
   since no such measurement is available for this call.

---

### User Story 2 - The indicator clears correctly however the review ends (Priority: P2)

Whether the sentence review finishes normally, comes back malformed, or the local
LLM turns out to be unavailable, the loading indicator disappears at exactly that
moment and the learner sees the appropriate result — never both at once, and never
the indicator left behind on screen.

**Why this priority**: An indicator that shows correctly but doesn't clear reliably
would be worse than no indicator at all — it would make the app look stuck exactly
when it has already finished. This depends on Story 1's indicator existing, so it is
the necessary follow-through, not a separate feature.

**Independent Test**: Can be fully tested by completing a review call under each of
its existing outcomes (needs correction, already correct, missing target expression,
unavailable/malformed) and confirming in each case that the indicator is gone by the
time that outcome's message is shown, with no overlap or leftover indicator text.

**Acceptance Scenarios**:

1. **Given** the loading indicator is showing, **When** the local LLM returns a usable
   review (needing correction or already correct), **Then** the indicator disappears
   and the correction feedback is shown in its place.
2. **Given** the loading indicator is showing, **When** the review fails for any
   reason (the LLM is unreachable, or its reply is malformed/unusable), **Then** the
   indicator disappears and the existing "correction unavailable" message is shown —
   exactly as it is shown today, unchanged.
3. **Given** a review completes very quickly, **When** the indicator has only been
   visible for a moment, **Then** it still disappears cleanly and correctly — the app
   never artificially delays showing the real result just to keep the indicator
   visible longer.

---

### Edge Cases

- What happens when the review completes almost instantly (e.g., a fast local model)?
  The indicator appears and clears for whatever brief moment it was actually needed;
  the app does not hold it on screen artificially, and does not skip showing it
  inconsistently either.
- What happens when the app's output is not an interactive terminal (e.g., output is
  redirected to a file, or the session is otherwise non-interactive)? The app must not
  corrupt output or crash — see Assumptions for the resolved default.
- What happens if the learner's sentence is missing the target expression, so the
  review still has to run but the eventual message differs from a grammar
  correction? The indicator behaves identically to any other outcome — it appears,
  then clears exactly when that (or any other) result is ready.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a visible, indeterminate loading indicator
  immediately after the learner submits a sentence for review, before any correction
  feedback or unavailability message is shown.
- **FR-002**: The loading indicator MUST remain visible and actively animating for the
  entire duration that the sentence-review request is in progress — its visible
  duration is driven entirely by how long the actual request takes, never by a fixed
  or guessed delay.
- **FR-003**: The loading indicator MUST be removed as soon as the review request
  settles, in every possible outcome (successful review — needs correction or already
  correct —, a review indicating the target expression is missing, a malformed/
  unparseable reply, or an unreachable LLM), before that outcome's message is shown.
- **FR-004**: The loading indicator MUST NOT display a percentage, a step count, or any
  other specific progress measurement, because no such measurement is available for
  this request.
- **FR-005**: In the command-line interface, the loading indicator MUST be an
  indeterminate, continuously animating indicator (e.g., a spinner), not a static
  "please wait" message shown once and left unchanged.
- **FR-006**: The system MUST NOT change the existing recall grading, sentence-review
  request/response handling, or what is recorded to the learner's practice history as
  a result of adding this indicator — this is a display-only addition layered on top
  of the existing, unchanged review flow.
- **FR-007**: The system MUST continue to function correctly (no crash, no corrupted
  output) when its output is not an interactive terminal, by not attempting to animate
  the indicator in that situation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every sentence submission shows a visible working indicator before the
  review completes — there is no scenario in which the learner sees a silent, unchanged
  screen while a review is in progress.
- **SC-002**: In every review outcome, the working indicator is gone at the exact point
  the result (feedback or unavailability message) is shown — zero observed cases of the
  indicator and the result appearing together, or the indicator lingering afterward.
- **SC-003**: Zero instances of a fabricated percentage, step count, or other specific
  progress measurement appear in the indicator, across all review outcomes.
- **SC-004**: A learner practicing with a slow local model can always tell, within a
  couple of seconds of submitting a sentence, whether the app is still working —
  without needing to guess or resubmit.

## Assumptions

- This UX change applies to the existing command-line interface only; the app has no
  other interface today, so there is no separate "web" or "GUI" variant to design for.
- The indicator is scoped to a single sentence-review request at a time (it is not a
  persistent, app-wide loading state) and carries no data of its own — nothing about it
  is written to the practice history or affects the Vocabulary Item / Practice Attempt
  data already defined for this feature.
- When the app's standard output is not an interactive terminal (redirected to a file,
  piped, or otherwise non-interactive), the app shows a plain one-time "working..."
  style message instead of an animated spinner, rather than attempting to animate
  where animation cannot be seen — this keeps output well-formed without silently
  doing nothing.
- No fixed minimum or maximum display duration is introduced for the indicator; it is
  shown for exactly as long as the underlying request takes, per FR-002.
