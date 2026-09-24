# Feature Specification: Choose Recall-Only or Sentence Practice Mode

**Feature Branch**: `012-practice-mode-choice`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Maybe can help to add a choice to let user choose the sentence mode or just only recall the vocabulary"

## Clarifications

### Session 2026-09-22

- Q: Should the choice between recall-only and sentence mode be available on both the command-line tool and the web UI, or should it be web-UI-only like the skip-confirmation, collection-picker, and voice-input features? → A: Both — the command-line tool gets a new startup flag alongside the web UI's interactive choose-screen control, since this is a plain setting rather than an interactive-widget convenience (confirming the same precedent spec `011` established).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose recall-only or sentence practice before starting (Priority: P1)

A learner starting a session wants to choose whether each word also
requires writing a sentence and getting corrected (today's existing
flow), or whether the session is just the recall step — see the Chinese
meaning, write the English word, see whether it was right — with no
sentence-writing step at all. Some sessions call for the deeper sentence
practice; other times (a quick review, or no time to write full
sentences) the learner just wants fast recall drilling.

**Why this priority**: This is the entire ask — a choice made once,
before a session starts, with no other behavior change.

**Independent Test**: Can be fully tested by starting a session, choosing
recall-only mode, and confirming that after answering each word the
session goes straight to the next word (or to completion) with no
sentence prompt ever shown, while the session's completion tally still
reflects every word's recall outcome.

**Acceptance Scenarios**:

1. **Given** a learner is about to start a session, **When** they choose
   sentence mode, **Then** the session behaves exactly as it does today —
   recall, then write a sentence, then see correction feedback, for every
   word.
2. **Given** a learner is about to start a session, **When** they choose
   recall-only mode, **Then** after they submit an answer for a word and
   see whether it was correct, the session goes directly to the next word
   (or to "session complete" on the last word) — no sentence prompt, no
   correction request, no sentence feedback appears at any point.
3. **Given** a recall-only session has completed, **When** the learner
   views the completion tally, **Then** it reports the same "X of Y
   correct" result it would for a sentence-mode session covering the same
   words, based on the recall step alone.
4. **Given** either mode was chosen, **When** the learner is partway
   through the session, **Then** the existing rule still holds: words are
   presented one at a time, moving forward only, with no way to skip an
   unanswered word or revisit an answered one (unaffected by this
   feature).

### Edge Cases

- What happens if the local correction service (used for sentence mode)
  isn't running or is unreachable? A recall-only session is entirely
  unaffected — it never requests a correction, so it works regardless of
  whether that service is available.
- What happens with only one word available? Both modes complete after
  that one word, differing only in whether a sentence prompt appeared.
- What happens when a learner returns to start a new session (e.g., after
  finishing one, or via a fresh command-line run)? They choose the mode
  again — the choice is not remembered from a previous session (see
  Assumptions).
- What happens to the existing "skip this sentence" confirmation (a
  separate, already-shipped feature for when a learner leaves the
  sentence field blank)? It has nothing to skip in recall-only mode,
  since no sentence prompt is ever shown there — it remains unchanged for
  sentence-mode sessions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let the learner choose, before a session's
  words are first presented, between "sentence mode" (today's existing
  recall, then write-a-sentence, then correction-feedback flow) and
  "recall-only" mode (recall each word's English form only, with no
  sentence-writing step at all).
- **FR-002**: In recall-only mode, after the learner submits an answer
  for a word and its correctness is revealed, the system MUST proceed
  directly to the next word, or to session completion on the last word —
  without presenting a sentence-writing prompt, without requesting any
  sentence correction, and without showing any sentence-related feedback.
- **FR-003**: In recall-only mode, the system MUST still reveal the
  correct accepted expression(s) for each word immediately after the
  learner submits an answer, exactly as sentence mode already does.
- **FR-004**: The chosen mode MUST be decided once, before the session's
  first word is shown, and MUST NOT change partway through a session.
- **FR-005**: This feature MUST NOT change sentence mode's existing
  behavior in any way — a learner who chooses (or defaults to) sentence
  mode gets exactly today's recall → sentence → feedback flow, unchanged.
- **FR-006**: The system MUST record each recall-only attempt in the
  learner's progress log with the same recall-outcome fields already
  recorded today (the word, the learner's answer, whether it was
  correct), leaving the sentence and feedback fields absent — the same
  shape already used when a learner skips writing a sentence in sentence
  mode.
- **FR-007**: The system MUST let this choice be made both interactively
  (when starting a session without a pre-selected configuration) and
  non-interactively (as a startup option, for scripted/unattended use),
  matching how choosing a vocabulary collection and word order already
  work.
- **FR-008**: The session-completion tally (words recalled correctly out
  of total) MUST include recall-only attempts on the same basis as
  sentence-mode attempts — it always grades the recall step only,
  regardless of which mode was used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can start and complete an entire session using
  recall-only mode without the local sentence-correction service running
  at all.
- **SC-002**: A learner can start a recall-only session in the same
  number of steps choosing a vocabulary collection already takes today.
- **SC-003**: Choosing sentence mode produces results indistinguishable
  from today's existing behavior (same flow, same fields recorded).
- **SC-004**: 100% of recall-only attempts are reflected in the session's
  completion tally.

## Assumptions

- **Scope: both the command-line tool and the web UI get this** (confirmed
  via clarification, 2026-09-22), the same way spec `011` (sequential/
  random order) already established: choosing a practice mode is a plain
  session setting — the same shape as the existing `--group` and `--order`
  startup options — not an interactive-widget convenience like the
  skip-confirmation (`006`), collection-picker screen (`007`), or voice
  input (`009`), which stayed web-UI-only.
- **Where the interactive choice lives**: on the same combined
  collection/order choice screen introduced by specs `007` and `011`,
  gaining a third control rather than a new screen — one combined "how do
  you want to practice" choice covering collection, order, and mode
  together, submitted in the same selection action.
- **Decided once per session, not remembered**: like collection and
  order, there is no settings file or database (spec 001 FR-011/012) —
  the learner chooses the mode every time they start a new session.
- **Relationship to the existing "skip this sentence" feature (spec
  006)**: unrelated and unaffected. That feature offers to skip writing a
  sentence for one word at a time, within sentence mode, when the field
  is left blank. Recall-only mode instead removes the sentence step from
  every word for the whole session, decided upfront; the two do not
  interact, since recall-only sessions never enter the sentence step to
  begin with.
- **Non-interactive/scripted use**: passing a pre-selected mode (e.g., at
  command-line startup) skips the interactive choice for that run, the
  same way pre-selecting a vocabulary collection via `--group` already
  does.
