# Feature Specification: Automatic Word Corrections

**Feature Branch**: `023-word-corrections`

**Created**: 2026-10-21

**Status**: Draft

**Input**: User description: "I found some of the pronunciation or meaning or verb/adj/noun are not correct. So I want to use qwen api to correct it. I have the api key." Follow-up: corrections are saved automatically (no review step); use the backend Qwen client and word-check task already added (commit 75968c1).

## Overview

Some words in the tutor have a wrong pronunciation (IPA), a wrong or poor
Chinese meaning, or a wrong part of speech (n., v., adj., …). These came
from hand-written lists, the local model (spec 018/019) or the offline
dictionary, and a learner who studies a wrong meaning or pronunciation
learns it wrong. This feature has a stronger online model (Qwen) check
each word's pronunciation, meaning and part of speech in the background,
the first time the word comes up in practice, and **saves its corrections
automatically**. Because nothing is reviewed first, every
change is recorded with its old value so it can be seen and undone. The
English word itself is never changed.

## Clarifications

### Session 2026-10-21

- Q: How is a check started? → A: Automatically in the background, the
  first time each word comes up in practice (no button).
- Q: Who do shared-set corrections apply to? → A: Everyone: one shared
  corrections record, like spec 021's shared example sentences; an undo
  applies to everyone too.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Words correct themselves as I practise (Priority: P1)

A learner practises as usual. The first time a word comes up, it is
checked in the background while the learner answers. Wrong
pronunciations, meanings and parts of speech are fixed and saved straight
away, so by the time the answer is shown, or at the latest the next time
the word comes up, the learner sees the corrected values. The learner can
look at a list of recent corrections: each changed word with what was
changed from what to what.

**Why this priority**: This is the request. It needs no extra step:
every word the learner actually studies gets checked, starting with the
ones they practise most.

**Independent Test**: With a Qwen key set and a temp copy of a learner's
list containing a word with a deliberately wrong meaning, IPA and part of
speech, practise that word and confirm the three fields are corrected in
the list, the English word is unchanged, the corrected values show in
practice, and the corrections list shows each change with its old and
new value.

**Acceptance Scenarios**:

1. **Given** a word with a wrong part of speech that has never been
   checked, **When** it comes up in practice, **Then** a check starts in
   the background without making the learner wait, and the corrected part
   of speech is saved in the list.
2. **Given** the check finishes before the learner's answer is shown,
   **When** the answer is shown, **Then** it shows the corrected values;
   if it finishes later, the corrected values show the next time the
   word comes up.
3. **Given** a word whose values are already right, **When** it is
   checked, **Then** it is left exactly as it was and no correction is
   recorded.
4. **Given** a word that was already checked, **When** it comes up
   again, **Then** it is not sent again unless it was added or edited
   since its last check.
5. **Given** corrections have been saved, **When** the learner opens the
   corrections list, **Then** they see each change as word, field, old
   value, new value, newest first.

---

### User Story 2 - Undo a correction (Priority: P2)

Because changes are saved without review, a learner who disagrees with a
correction can undo it, putting back the value the word had before.

**Why this priority**: Saving automatically is only safe if a bad
correction can be reversed. It is not needed for the first useful check,
so it comes second.

**Independent Test**: Let a check change a word, undo that change from
the corrections list, and confirm the old value is back and the word is
not changed again when it next comes up.

**Acceptance Scenarios**:

1. **Given** a saved correction, **When** the learner undoes it, **Then**
   the word's previous value is restored for the fields that were
   changed.
2. **Given** an undone correction, **When** the word comes up again, **Then**
   it does not re-apply the same change (the learner's choice stands).

---

### User Story 3 - Correct the shared word sets (Priority: P3)

The built-in shared word sets that learners without their own lists
practise are checked the same way when their words come up. A correction
applies to every learner, and the shared files themselves are left
untouched.

**Why this priority**: Shared sets are smaller (about 180 words) and
were curated by hand, so they have fewer errors, but they are what new
learners see first.

**Independent Test**: On a temp copy of the shared sets, practise a
shared word with a wrong meaning as one learner, then as another learner
confirm the corrected meaning is shown, while the shared vocabulary files
are byte-for-byte unchanged.

**Acceptance Scenarios**:

1. **Given** a shared word with a wrong meaning, **When** it is checked
   during one learner's practice, **Then** every learner's practice shows
   the corrected meaning and the shared file is unchanged.
2. **Given** a shared-set correction, **When** any learner undoes it,
   **Then** every learner's practice shows the shared file's original
   value again.
3. **Given** a shared word already checked for one learner, **When** it
   comes up for another, **Then** it is not sent again.

---

### Edge Cases

- **No key set**: no word is checked, nothing changes and practice works
  as before.
- **A check fails** (timeout, busy, unusable answer): the word keeps its
  current values, practice is not affected, and the word is checked
  again the next time it comes up.
- **Qwen is down or the key is rejected**: practice carries on with the
  current values; checks pause for a while instead of failing on every
  word, and the learner is not interrupted. The reason ("Qwen rejected
  the API key", "Qwen could not be reached") is shown where the
  corrections list is.
- **An answer that doesn't fit** (not a pronunciation, a meaning that is
  empty, too long or not family-safe, an unknown part of speech): the
  word is left alone. A partly valid answer is never partly applied.
- **A list changes during a check** (the learner edits, removes or
  uploads words): the check never overwrites a newer edit, and a word
  removed meanwhile is skipped.
- **The same word comes up twice, or for two learners at once**: it is
  checked only once at a time.
- **Moving on quickly**: skipping or answering before the check finishes
  never waits for it; the check still completes and is saved.
- **Learner-written meanings**: a meaning the learner typed when
  uploading is corrected like any other value (it is recorded and can be
  undone).
- **Pronunciation dialect**: shared sets use British IPA (spec 017) and
  own lists American IPA (spec 018). A correction keeps the list's
  dialect; it never swaps a correct British form for an American one.
- **Spelling variants and example sentences** are not part of the check
  and are never changed by it.
- **Cost**: a word is sent only the first time it comes up (and again
  only after it is edited), so practising unchanged words sends nothing.
  Words never practised are never sent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST check a word's pronunciation (IPA),
  Chinese meaning and parts of speech with Qwen and save any corrected
  values automatically, without a review step.
- **FR-002**: The system MUST never change a word's English text, its
  spelling variants, its group or list, or its example sentence.
- **FR-003**: A word MUST be checked automatically in the background the
  first time it comes up in practice; checking MUST NOT delay showing the
  word, accepting an answer or moving on.
- **FR-004**: Every saved correction MUST be recorded with the word, the
  field, the old value, the new value and when it was made, and the
  learner MUST be able to see these records.
- **FR-005**: A learner MUST be able to undo a correction, restoring the
  old values of that word's changed fields; an undone change MUST NOT be
  re-applied by later checks.
- **FR-006**: Each word MUST be checked at most once unless it was edited
  since its last check; a failed check MAY be retried when the word next
  comes up, and the same word MUST NOT be checked twice at the same time.
- **FR-007**: A Qwen answer MUST be fully valid before any of it is
  used: the pronunciation, meaning and parts of speech follow the same
  rules as values in a hand-written list (meaning family-safe and at most
  60 characters). Otherwise the word is left unchanged.
- **FR-008**: A correction MUST keep the list's pronunciation dialect
  (British for the shared sets, American for own lists).
- **FR-009**: The shared vocabulary files MUST never be modified; shared
  words are corrected through one separate corrections record that
  practice applies on top of them for every learner, and an undo of a
  shared correction applies to every learner.
- **FR-010**: A failed check MUST leave the word unchanged and MUST NOT
  interrupt practice; after a rejected key or an unreachable service,
  checks MUST pause for a while rather than fail on every word, and the
  reason MUST be shown with the corrections list.
- **FR-011**: The learner MUST be able to see a list of corrections that
  apply to the words they practise (their own lists' corrections and the
  shared ones), newest first.
- **FR-012**: When a check finishes before the answer is shown, the
  answer MUST show the corrected values; a check MUST NOT overwrite a
  value edited while it ran.
- **FR-013**: Only word data MUST be sent to Qwen: the English word and
  its current pronunciation, meaning and parts of speech. No learner
  name, account, progress history, recordings or attempts.
- **FR-014**: Without a Qwen key the check MUST be unavailable and
  everything else MUST work exactly as before.
- **FR-015**: Error messages MUST NOT show the key, prompts, or Qwen's
  raw answers.

### Key Entities

- **Word check result**: Qwen's validated pronunciation, meaning and
  parts of speech for one word; untrusted until it passes FR-007.
- **Correction record**: one saved change: word (English, list or group),
  field, old value, new value, time, and whether it was undone. Own-list
  records belong to that learner; shared-set records are shared.
- **Check status per word**: whether the word has been checked, and the
  values it had then, so unchanged words are not sent again (FR-006).
- **Shared corrections record**: corrected values for shared-set words,
  kept apart from the shared files and applied on top of them in
  practice (FR-009).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a reviewed sample of 50 words with known errors (wrong
  meaning, wrong part of speech, wrong IPA), at least 90% of the errors
  are corrected by the check.
- **SC-002**: On a reviewed sample of 50 words that are already correct,
  at most 5% are changed in a way a reviewer judges worse.
- **SC-003**: Checking adds no waiting to practice: showing a word,
  answering and moving on take no longer with checks on than with them
  off.
- **SC-004**: Any correction can be undone in at most two actions from
  the corrections list, and 100% of undone corrections stay undone when
  the word comes up again.
- **SC-005**: Practising a word that has already been checked and not
  edited since sends 0 requests to Qwen.
- **SC-006**: The shared vocabulary files are byte-for-byte unchanged
  after any check, and a shared correction made in one learner's session
  shows in every learner's practice.
- **SC-007**: A check never changes any word's English text, spelling
  variants or example sentence (0 such changes across the test lists).

## Assumptions

- Qwen is reached through the backend client and word-check task
  already in the project (`qwen_client`, `word_check`, commit 75968c1),
  configured by `DASHSCOPE_API_KEY`, `QWEN_BASE_URL` and `QWEN_MODEL`.
  The key stays on the server.
- Sending word data (not learner data) to an online service is
  acceptable to the user: it was requested explicitly and replaces the
  earlier "local model only" rule for this feature alone. Example
  sentences and voice stay local.
- The cost of checking each practised word once is acceptable (at most
  about 1,000 words today); words never practised are never sent.
- The existing rules for a valid pronunciation, meaning and part of
  speech (specs 017–019) are the acceptance rules for Qwen's answers.
- Checks run from the web app's practice, which is where the learner
  sees the corrections list and undoes changes; the CLI is not required
  to check words or show corrections.
- Corrections to a learner's own lists are written into those lists (as
  spec 021 does for example sentences), so they show everywhere the list
  is used.
