# Feature Specification: Choose Sequential or Random Word Order

**Feature Branch**: `011-vocabulary-order-choice`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "can help to let user choose recall the vocabulary by order or by random order"

## Clarifications

### Session 2026-09-22

- Q: Should this order choice apply to the command-line tool as well as the web UI, or should it be web-UI-only like the recent skip-confirmation, collection-picker, and voice-input features? → A: Both — the command-line tool gets a new startup flag alongside the web UI's interactive picker, since this is a plain setting rather than an interactive-widget convenience.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pick sequential or random order before practicing (Priority: P1)

A learner starting a session wants to choose whether the words come in
their usual, authored order (the order they appear in the vocabulary
files) or in a shuffled, random order — so they can either follow a
lesson's intended sequence, or avoid memorizing "the third word is
always X" instead of actually recalling each word from its meaning.

**Why this priority**: This is the entire ask — a choice made once, before
a session starts, with no other behavior change.

**Independent Test**: Can be fully tested by starting a session, choosing
random order, and confirming the words appear in a different order than
the vocabulary files list them, while every word still appears exactly
once before the session completes.

**Acceptance Scenarios**:

1. **Given** a learner is about to start a session, **When** they choose
   sequential order, **Then** words appear in exactly the order they're
   authored in the vocabulary files — today's existing behavior.
2. **Given** a learner is about to start a session, **When** they choose
   random order, **Then** words appear in a shuffled order — different
   from the authored order (barring the rare chance a shuffle happens to
   match it) — and every word in the chosen collection still appears
   exactly once by the time the session completes.
3. **Given** either order was chosen, **When** the learner is partway
   through the session, **Then** the existing rule still holds: words are
   presented one at a time, moving forward only, with no way to skip an
   unanswered word or revisit an answered one (unaffected by this
   feature — see Assumptions).

### Edge Cases

- What happens with only one word available? Sequential and random order
  produce the same (only possible) result.
- What happens when a learner returns to start a new session (e.g., after
  finishing one, or via a fresh command-line run)? They choose the order
  again — the choice is not remembered from a previous session (see
  Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let the learner choose, before a session's
  words are first presented, between sequential order (the order words
  are authored in the vocabulary files) and random order.
- **FR-002**: When random order is chosen, the system MUST present every
  word in the session's pool exactly once before the session completes —
  the same completion guarantee sequential order already has, just in a
  shuffled sequence.
- **FR-003**: The chosen order MUST be decided once, before the session's
  first word is shown, and MUST NOT change partway through a session.
- **FR-004**: This feature MUST NOT change any other existing rule about
  how words are presented — no skipping an unanswered word, no returning
  to an answered one, one word at a time, remain exactly as they are
  today regardless of which order is chosen.
- **FR-005**: The system MUST let this choice be made both interactively
  (when starting a session without a pre-selected configuration) and
  non-interactively (as a startup option, for scripted/unattended use),
  matching how choosing a vocabulary collection already works.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can start a session in random order without
  editing any configuration file, in the same number of steps choosing a
  vocabulary collection already takes today.
- **SC-002**: 100% of words in a session's pool are presented exactly
  once by completion, regardless of which order was chosen.
- **SC-003**: Choosing sequential order produces results indistinguishable
  from today's existing behavior (same words, same sequence).

## Assumptions

- **Relationship to the existing "forward order only" rule** (spec 001
  FR-016, reaffirmed by spec 003 FR-010): that rule — read together with
  the sentences that immediately clarify it ("MUST NOT offer a way to
  skip an item without submitting an answer, or to return to a previously
  answered item") — is about the *direction* of travel through the
  session's pool (always forward, never skip, never back), not about the
  pool's order being fixed to file order specifically. Shuffling the pool
  once, before the session starts, and then walking through it forward
  exactly as today satisfies that rule; it is not an exception to it,
  the way spec `006`'s per-word skip was.
- **"Random order" means a shuffle, not repeated random sampling**: every
  word appears exactly once, same as today — this is a randomized
  permutation of the same finite pool, not a longer or shorter session,
  and not a mode where a word could be shown twice or not at all.
- **Scope: both the command-line tool and the web UI get this** (confirmed
  via clarification, 2026-09-22), unlike several recent features (`006`
  skip-confirmation, `007`'s collection picker screen, `009` voice input)
  that were deliberately web-UI-only because they're interactive-widget
  conveniences with no sensible command-line equivalent. Choosing an
  order is a simple setting, already exactly the shape of the existing
  `--group` startup option the command-line tool already has.
- **Where the interactive choice lives**: in the web UI, this is added to
  the same collection-choice screen introduced in spec `007`, rather than
  a new separate screen — one combined "how do you want to practice"
  choice instead of two.
- **Not remembered across sessions**: like every other startup/session
  choice in this app, there is no settings file or database (spec 001
  FR-011/012) — the learner chooses order every time they start a new
  session, the same way they already choose (or don't choose) a
  collection every time today.
- **Non-interactive/scripted use**: passing a pre-selected order (e.g., at
  command-line startup) skips the interactive choice for that run, the
  same way pre-selecting a vocabulary collection via `--group` already
  skips that choice screen entirely.
