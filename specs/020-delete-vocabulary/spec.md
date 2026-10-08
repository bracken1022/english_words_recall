# Feature Specification: Remove Words I Don't Want to Recall

**Feature Branch**: `020-delete-vocabulary`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Help to add a functionality to delete the vocabulary which I do not want to recall"

## Context

Today a learner can only remove words by deleting a whole word list
(spec 016) or by editing files on the tutor's machine. A list often has a
few words the learner already knows well, or never wants to study (an
odd word, a duplicate, a bad meaning). These keep coming back in every
session. The learner wants to take individual words out of their
practice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove a word while practicing it (Priority: P1)

A word comes up that the learner doesn't want to see again, so they
remove it right there instead of answering. The session moves on to the
next word, and that word no longer appears in any later session.

**Why this priority**: This is the moment the learner notices an
unwanted word, and acting on it in one step is the core of the request.

**Independent Test**: Start a session, remove the current word, and
confirm the session continues with the next word. Start a new session
and confirm the removed word is not offered and is not counted in the
word-set totals.

**Acceptance Scenarios**:

1. **Given** a word on the recall screen, **When** the learner chooses
   "Remove this word" and confirms, **Then** the session moves to the
   next word (or finishes if it was the last), and the removed word is
   not counted as right or wrong.
2. **Given** a word has been removed, **When** the learner starts any
   later session, including "Practice everything", **Then** that word
   never appears, and the word-set counts exclude it.
3. **Given** the answer has just been revealed or the learner is on the
   sentence step, **When** they choose "Remove this word", **Then** the
   same thing happens. The attempt already made is kept in their
   history.
4. **Given** the learner opens the remove action, **When** they cancel
   the confirmation, **Then** nothing changes.

---

### User Story 2 - Undo a removal straight away (Priority: P2)

A learner sometimes removes a word by mistake and wants it back at once.

**Why this priority**: Removal is permanent (spec Q1), so a quick way to
reverse a mis-tap makes the one-step removal in US1 safe.

**Independent Test**: Remove a word, press "Undo" in the confirmation,
and confirm the word is back in its word list, unchanged and in the same
place, and is practiced again in later sessions.

**Acceptance Scenarios**:

1. **Given** a word was just removed, **When** the learner presses
   "Undo" in the confirmation message, **Then** the word is put back in
   its word list exactly as it was (meaning, pronunciation, part of
   speech, alternates, position), and later sessions include it again.
2. **Given** a word was removed, **When** the learner moves on (answers
   the next word, ends the session or leaves the page) without pressing
   "Undo", **Then** the removal is final and there is no later way to
   restore it in the web UI. Re-uploading a list that contains the word
   brings it back.

### Edge Cases

- **Every word removed**: if all words in a word set are removed, the
  set shows 0 words and can't be started. "Practice everything" with no
  words left shows the existing "No words are waiting" screen.
- **The same word in two word sets**: removing it during practice
  removes that entry in that set only. A copy in another set stays,
  unless that one is removed too.
- **Shared word sets**: the shared word sets belong to everyone and are
  never edited. A learner who practices them (because they have no lists
  of their own) can still remove a word. For them it is hidden from their
  own practice for good, with the same immediate "Undo". Other learners
  still see it.
- **Re-uploads**: removal deletes the word from the file, so
  re-uploading a list that contains it brings it back.
- **Last word in a list**: removing the only word left in one of the
  learner's lists leaves an empty list, which "My word lists" shows with
  0 words. The learner can delete the list as before (spec 016).
- **Practice history**: answers given before a removal stay in the
  history.
- **Two devices**: if a word is removed on one device while the same
  learner is mid-session on another, the other session is not broken.
  The removal takes effect there from the next word or session.
- **Locked sessions**: when the tutor is started locked to one word
  set, removing words still works and applies from the next word.
- **Other learners**: one learner's removals never affect anyone else.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: During practice, on the recall, reveal and sentence
  steps, the learner MUST be able to remove the current word, after a
  confirmation.
- **FR-002**: A removed word MUST NOT appear in any later session for
  that learner. It MUST be excluded from word-set counts and from
  "Practice everything".
- **FR-003**: Removing the current word MUST move the session to the
  next word, or to the end, without recording a right or wrong answer
  for it.
- **FR-004**: Right after a removal, the learner MUST be shown a short
  confirmation with an "Undo" action that restores the word exactly. The
  undo is available until the learner's next practice action, the end of
  the session, or a page reload, whichever comes first.
- **FR-005**: Removing a word from one of the learner's own lists MUST
  delete that entry from the word-list file, leaving every other entry
  unchanged. A word in the shared word sets MUST instead be hidden from
  that learner's practice permanently, and the shared files MUST NOT
  change.
- **FR-006**: Viewing a list's words, or removing words outside a
  practice session, is out of scope (spec Q2).
- **FR-007**: Removals MUST apply only to the learner's own account. The
  shared word sets and other learners' words MUST NOT change.
- **FR-008**: Practice history MUST be kept unchanged by removals and
  restorations.
- **FR-009**: Removals MUST persist across server restarts and devices.
- **FR-010**: Undo MUST bring the word back with all its details and its
  position in the list unchanged.
- **FR-011**: The command-line tutor is unchanged. Removal is a web UI
  feature.

### Key Entities

- **Hidden Shared Word**: a word in the shared sets that one learner
  removed. It holds the learner, the English word and its word set.
  Words from the learner's own lists are deleted outright instead.
- **Pending Undo**: the most recently removed entry, kept just long
  enough to restore it exactly.
- **Vocabulary Entry / Word List**: existing, from specs 001 and 016.

### Data Handling (Constitution Principle III)

- **Collected**: removal edits the learner's own word-list files. For
  the shared sets, it stores which words that learner hid. Both stay
  with that learner's data on the tutor's machine.
- **Why**: so the learner's practice stops showing those words.
- **Access**: only the owning learner. Nothing is sent anywhere.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can remove the word they are practicing in 2
  actions or fewer (choose remove, then confirm), in under 5 seconds.
- **SC-002**: 0 removed words appear in any later session for that
  learner, across restarts and devices.
- **SC-003**: Undo restores a just-removed word with 100% of its details
  and its position intact. A removal without undo leaves the rest of the
  list file byte-identical apart from the deleted entry.
- **SC-004**: Removals by one learner change 0 words for any other
  learner, and 0 files in the shared word sets.
- **SC-005**: 100% of practice history recorded before a removal
  remains after it.

## Clarifications

### Session 2026-10-08

- Q: Reversible hiding, or permanent deletion? → A: Permanent. The word
  is deleted from the learner's list file, with only an immediate undo.
  Shared words, which can't be edited, are hidden for that learner.
- Q: Remove words from a list view too? → A: No. Removal during practice
  only, for now.

## Assumptions

- "Delete the vocabulary" means taking individual words out of the
  learner's own practice, not editing word meanings. Deleting whole
  lists already exists (spec 016).
- A removal is per learner and per word set, so a word in two sets can
  be removed from one only.
- The command-line tutor keeps its simpler flow, as with other web-only
  conveniences (spec 007 onward).
- The trusted-household setup of spec 015 applies. Nothing leaves the
  machine.
