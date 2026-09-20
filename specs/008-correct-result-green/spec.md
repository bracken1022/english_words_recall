# Feature Specification: Show a Correct Recall Result in Green

**Feature Branch**: `008-correct-result-green`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "Can help to change the correct result to green color. such as Correct: unbearable, should be green"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a correct answer marked in green (Priority: P1)

A learner answers a word's recall step correctly (e.g. types "unbearable" for the right word) and sees the "Correct: unbearable" result. Today it's shown in the same red as an incorrect result; the learner wants a correct answer to read as green instead, so right and wrong are told apart by color as well as by wording.

**Why this priority**: This is the entire ask — a purely visual change to how an already-correct result is displayed, with no change to grading or session behavior.

**Independent Test**: Can be fully tested by answering a word's recall step correctly and confirming the result reads in green, independent of every other part of the app.

**Acceptance Scenarios**:

1. **Given** the learner submits a correct answer, **When** the result appears, **Then** it is shown in green.
2. **Given** the learner submits an incorrect answer, **When** the result appears, **Then** it still reads in red, exactly as it does today, and remains clearly distinguishable from a correct result by more than color alone (see FR-002).
3. **Given** a learner with red-green color vision deficiency, **When** either result appears, **Then** they can still tell a correct result from an incorrect one without relying on color (see FR-002).

### Edge Cases

- What happens for the other places the app already signals "this was correct" (the session-completion stamp, and a sentence that needed no correction)? Out of scope for this change — see Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a correct recall result in a distinct green color, instead of the red used today.
- **FR-002**: The system MUST continue to distinguish a correct result from an incorrect one by more than color alone (e.g. the existing wording and/or symbol difference), so the change remains usable for learners who cannot distinguish red from green.
- **FR-003**: The system MUST NOT change how an incorrect recall result looks — it keeps its existing red color and wording.
- **FR-004**: The system MUST NOT change any grading, scoring, or session-progress logic — this is a display-only change to an already-correct/incorrect result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of correct recall results are shown in green instead of red, verified by inspecting the result immediately after a correct answer.
- **SC-002**: 100% of incorrect recall results continue to look exactly as they did before this change.
- **SC-003**: A learner can still tell a correct result from an incorrect one with color removed entirely (e.g. viewed in grayscale), matching today's accessibility behavior.

## Assumptions

- **Scope**: this applies to the recall-step result banner (the "Correct: ..." / "Incorrect. The correct expression is: ..." indicator shown after answering a word). It does not extend to the session-completion stamp or to the "your sentence is already correct" sentence-review message, which are separate indicators the feature description didn't mention; either can be revisited separately if the learner wants the same treatment there.
- **Symbol/wording stays**: the existing ✓ / "Correct:" and ✗ / "Incorrect." distinction is kept as-is alongside the new color, rather than being removed — this is what keeps FR-002's accessibility guarantee intact while still doing what was asked.
- The exact shade of green is a visual-design decision made during planning, not fixed by this spec; it only needs to read clearly as "green" and remain easily readable against its background in both light and dark presentations, matching the app's existing support for both.
