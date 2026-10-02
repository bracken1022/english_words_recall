# Feature Specification: IPA Pronunciation for Vocabulary

**Feature Branch**: `017-vocabulary-ipa`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "please help to add an ipa field to every vocabulary and fill it with the correct IPA pronunciation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See how a word is pronounced once it's revealed (Priority: P1)

A learner recalls an English word from its Chinese meaning. Once the
answer is revealed — whether they got it right or wrong — they also want
to see how the word is pronounced, written in IPA (e.g. *receive*
/rɪˈsiːv/), so they learn to say it correctly, not just spell it.

**Why this priority**: The pronunciation is only useful if the learner
actually sees it while studying the word; storing it without showing it
delivers nothing.

**Independent Test**: Practice a word whose entry has a pronunciation;
after answering (correctly or not), the revealed answer shows the IPA next
to the English word. Before answering, no pronunciation is visible.

**Acceptance Scenarios**:

1. **Given** a word with a pronunciation, **When** the learner is still
   recalling it, **Then** no pronunciation is shown (it would give the
   answer away).
2. **Given** the learner answers correctly or incorrectly, or presses
   "Show answer", **When** the answer is revealed, **Then** the IPA is
   shown beside the English word, between slashes.
3. **Given** the learner moves on to the sentence step or sentence
   feedback for that word, **When** the target word is displayed, **Then**
   its IPA is shown with it.
4. **Given** a word with no pronunciation recorded, **When** its answer is
   revealed, **Then** nothing is shown in its place (no empty slashes, no
   error).
5. **Given** the command-line tutor, **When** a word's answer is
   revealed, **Then** its IPA is printed beside it as well.

---

### User Story 2 - Every existing word gets a correct pronunciation (Priority: P1)

The learner's existing words — the 182 words in the shared vocabulary
folder and the 47 words already uploaded to a personal list — should all
have their IPA filled in, accurately, without anyone typing them by hand.

**Why this priority**: This is the explicit ask ("fill it with the correct
IPA"); displaying pronunciations is pointless if the words don't have
them.

**Independent Test**: After the fill, every word in the shared vocabulary
folder and every existing uploaded list has an IPA entry; a reviewed
sample matches a standard dictionary pronunciation.

**Acceptance Scenarios**:

1. **Given** the existing vocabulary files, **When** the fill is done,
   **Then** every word has an IPA entry in British (UK) pronunciation, as
   given by standard British learner's dictionaries (Oxford / Cambridge
   style transcription).
2. **Given** a multi-word expression (e.g. "tend to"), **When** it is
   filled, **Then** its IPA covers the whole expression.
3. **Given** a word whose existing content (English, meaning, accepted
   alternates, word set) was set by hand, **When** the IPA is added,
   **Then** nothing else in the entry changes.
4. **Given** a word that has more than one standard pronunciation (e.g. a
   noun and verb stressed differently), **When** it is filled, **Then**
   the pronunciation matching the recorded Chinese meaning is used, or the
   common one if the meanings cover both.

---

### User Story 3 - New words can carry a pronunciation too (Priority: P2)

Words keep being added: the operator edits vocabulary files, and learners
upload new lists. Those words should be able to carry a pronunciation as
well.

**Why this priority**: Keeps the feature useful after the one-time fill,
but the existing words (US2) come first.

**Independent Test**: Add a word with an IPA value to a vocabulary file,
and upload a list that includes a pronunciation column; both show their
IPA when revealed. A word added later *without* a pronunciation simply
shows none — nothing is filled in automatically; filling a new list is a
separate, reviewed step done on request, like this one.

**Acceptance Scenarios**:

1. **Given** the operator adds `ipa` to an entry in a vocabulary file,
   **When** that word is revealed, **Then** the IPA is shown.
2. **Given** a learner uploads a list whose lines include a pronunciation
   (Markdown `ipa` field, or a pronunciation column in the simple list),
   **When** that word is revealed, **Then** the IPA is shown.
3. **Given** an uploaded or hand-written pronunciation that is malformed
   (e.g. empty, or obviously not IPA such as only digits), **When** it is
   loaded, **Then** the word still works and simply shows no
   pronunciation; the problem is reported as a warning, not a failure.

---

### Edge Cases

- A pronunciation written with or without surrounding slashes or brackets
  (`rɪˈsiːv`, `/rɪˈsiːv/`, `[rɪˈsiːv]`) is displayed consistently as
  `/rɪˈsiːv/`.
- Words whose spelling covers two unrelated words with different
  pronunciations (e.g. *tear* "眼泪" vs "撕") use the one matching the
  Chinese meaning given.
- Proper nouns, abbreviations, or invented words with no standard
  pronunciation are left without IPA and listed for review rather than
  guessed.
- Alternate accepted answers keep no separate pronunciation; only the main
  English expression has one.
- Vocabulary files without any `ipa` fields keep working exactly as today.
- IPA characters (ˈ ˌ ː ə ʊ θ ð ʃ ʒ ŋ etc.) display correctly on desktop and
  phone, in both the web UI and the terminal.
- Grading never looks at the pronunciation: the learner still types only
  the English word.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each vocabulary entry MUST support an optional pronunciation
  (IPA) value, in the shared vocabulary folder, in uploaded lists, and in
  the files that store uploaded lists.
- **FR-002**: Entries without a pronunciation MUST keep working exactly as
  today; existing files MUST NOT need any change to keep loading.
- **FR-003**: The pronunciation MUST NOT be shown while the learner is
  recalling a word, in either the web UI or the command-line tutor.
- **FR-004**: Once a word's answer is revealed (correct, wrong, or "Show
  answer"), and on the sentence and sentence-feedback steps for that word,
  the pronunciation MUST be shown beside the English word, formatted as
  `/…/`, in both the web UI and the command-line tutor.
- **FR-005**: Every word in the shared vocabulary folder and in every
  existing uploaded list MUST be given a British (UK) IPA pronunciation,
  with all other fields of each entry left unchanged.
- **FR-006**: Filled pronunciations MUST be checked for accuracy before
  they are kept: a reviewed list of every filled word with its IPA MUST be
  produced, and any word whose pronunciation can't be confidently
  determined MUST be left empty and listed for manual review rather than
  guessed (Constitution Principle II).
- **FR-007**: Uploaded lists MUST accept an optional pronunciation: an
  `ipa` field in the Markdown format, and an optional pronunciation column
  in the simple list format, documented on the upload screen's format
  hint and in the README.
- **FR-008**: A malformed pronunciation MUST NOT break loading, grading, or
  practice; the word shows no pronunciation and a warning is reported.
- **FR-009**: Grading, sentence review, practice history, and word sets
  MUST be unaffected by the presence or absence of a pronunciation.
- **FR-010**: Words added or uploaded after the fill MUST NOT get a
  pronunciation generated automatically; they show one only when their
  file supplies it.

### Key Entities

- **Vocabulary Entry**: existing — English expression, Chinese meaning,
  accepted alternates, word set — plus an optional **pronunciation (IPA)**
  for the English expression.
- **Pronunciation Review List**: produced by the fill: every filled word
  with its IPA, plus the words left empty and why, for a person to check.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the 229 existing words (182 shared + 47 uploaded)
  either have an IPA pronunciation or appear on the review list with a
  reason; at least 98% have one.
- **SC-002**: In a spot check of 30 randomly chosen filled words against a
  standard learner's dictionary, at least 29 match (stress mark and
  vowels).
- **SC-003**: 0 pronunciations are visible on the recall screen before the
  learner answers.
- **SC-004**: After every reveal of a word with a pronunciation, the IPA is
  visible without any extra click.
- **SC-005**: All existing vocabulary files and uploaded lists still load
  with 0 new warnings after the fill.

## Assumptions

- "Every vocabulary" means every word that exists today: the shared
  vocabulary folder (182 words across T, U, V and W–Z files) and the one
  uploaded list (47 words). The small design-fixture word set used for
  screenshots is included too so screenshots show the feature.
- The pronunciation describes the main English expression only, not the
  alternates.
- IPA is shown as text, not audio; spoken pronunciation is out of scope.
- One accent only (British); American pronunciations are out of scope.
- Filling pronunciations for lists uploaded after this feature is done on
  request, as a separate reviewed step, not by the tutor itself.
- The shared vocabulary folder and uploaded lists are local learner data
  (not in git); the fill edits those files in place, so a backup copy is
  kept before changing them.
- The trusted-household setup of specs 015/016 still applies; nothing
  about pronunciations leaves the machine.
