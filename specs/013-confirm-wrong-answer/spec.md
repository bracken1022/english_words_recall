# Feature Specification: Require Confirmation Before Advancing Past a Wrong Recall-Only Answer

**Feature Branch**: `013-confirm-wrong-answer`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Can we change a little, for the correct vacabulary, we can automatically switch to the new word. But for the wrong result, can let the user manually chose to switch to new word"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manually confirm before moving on from a missed word (Priority: P1)

A learner practicing in recall-only mode gets a word wrong. Today, the
session reveals the correct expression and then moves on by itself after
a short pause — too short to really study the mistake. The learner wants
to control when they move on from a word they got wrong, so they can
actually read and absorb the correct answer before it's replaced by the
next word. When they get a word right, though, they're happy for the
session to keep moving on its own, exactly as it already does.

**Why this priority**: This is the entire ask — the fix that already
gave recall-only mode a visible pass/fail result didn't go far enough for
the case that matters most for learning: the mistakes.

**Independent Test**: Can be fully tested by practicing in recall-only
mode, answering one word correctly (confirming the session still moves
on by itself) and one word incorrectly (confirming the session waits,
with the correct expression still visible, until the learner explicitly
continues).

**Acceptance Scenarios**:

1. **Given** a learner is practicing in recall-only mode, **When** they
   answer a word correctly, **Then** the session briefly confirms the
   correct result and then automatically moves on to the next word (or
   session completion) — unchanged from today.
2. **Given** a learner is practicing in recall-only mode, **When** they
   answer a word incorrectly, **Then** the session reveals the correct
   expression and waits — it does not move on by itself, no matter how
   long the learner takes.
3. **Given** a learner is looking at a revealed correct expression for a
   missed word, **When** they take the explicit "continue" action,
   **Then** the session moves on to the next word (or session
   completion), exactly as it would have automatically for a correct
   answer.
4. **Given** a learner is practicing in sentence mode (not recall-only),
   **When** they answer a word right or wrong, **Then** nothing about
   this feature changes their experience — sentence mode already always
   waits for the learner to write a sentence and continue, regardless of
   the recall outcome.

### Edge Cases

- What happens if the wrong answer is on the last word in the session?
  The session still waits for the learner's explicit continue action;
  taking it then shows session completion, same as it would for a
  correct answer on the last word.
- What happens in a session where every answer is wrong? The learner
  confirms every single word themselves; none advance automatically.
- What happens in sentence mode? Unaffected — this feature only changes
  recall-only mode's advancement timing (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: In recall-only mode, when the learner's answer is correct,
  the system MUST continue to automatically proceed to the next word (or
  session completion) after briefly confirming the correct result — this
  part of today's behavior is unchanged.
- **FR-002**: In recall-only mode, when the learner's answer is
  incorrect, the system MUST NOT automatically proceed to the next word;
  it MUST wait for the learner to take an explicit continue action first.
- **FR-003**: While waiting for that explicit action after an incorrect
  answer, the correct accepted expression(s) MUST remain visible for as
  long as the learner needs, with no time limit.
- **FR-004**: The explicit continue action MUST become available as soon
  as an incorrect answer's result is revealed, and MUST advance the
  session to the next word (or session completion) when taken.
- **FR-005**: This feature MUST NOT change sentence mode's existing
  behavior in any way — sentence mode already always requires the
  learner to complete the sentence-writing step and continue explicitly,
  regardless of whether the recall answer was right or wrong.
- **FR-006**: The session-completion tally and progress-log recording
  MUST behave exactly as they already do today — only the timing of when
  the session advances past an incorrect recall-only answer changes, not
  what gets recorded or counted.
- **FR-007**: This behavior MUST apply consistently on both the
  command-line tool and the web UI, matching recall-only mode's own
  existing availability on both.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner who answers correctly in recall-only mode reaches
  the next word without taking any action, exactly as today.
- **SC-002**: A learner who answers incorrectly in recall-only mode is
  never moved to the next word without deliberately choosing to
  continue — 0% of incorrect answers auto-advance.
- **SC-003**: A learner can keep a missed word's correct expression on
  screen for as long as they want before continuing — never cut off by a
  timer.

## Assumptions

- **Scope: only recall-only mode's advancement timing changes.**
  Sentence mode already requires an explicit "Continue" action after
  every word regardless of correctness, so it already satisfies what
  this feature asks for on the "wrong answer" side, and the "right
  answer auto-advances" side isn't how sentence mode has ever worked (it
  always involves writing a sentence first). Applying this feature to
  sentence mode would be a different, unrelated change.
- **Applies to both the CLI and the web UI**, the same way recall-only
  mode itself already does (its own scope decision): the CLI's "press
  Enter/type anything to continue" idiom and the web UI's continue
  button are both valid forms of "an explicit continue action" — this
  spec doesn't prescribe which.
- **The automatic pause on a correct answer keeps its existing brief,
  non-blocking length** — this feature doesn't change how long a correct
  result stays visible before auto-advancing, only what happens on an
  incorrect one.
- **Not remembered across sessions or configurable** — like every other
  behavior in this app, this isn't a setting the learner chooses; it's
  simply how recall-only mode behaves now, for every learner, every
  session.
- **No new data is collected or stored** — this changes when the session
  advances, not what's recorded about each attempt (FR-006).
