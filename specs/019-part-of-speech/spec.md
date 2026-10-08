# Feature Specification: Part of Speech for Vocabulary

**Feature Branch**: `019-part-of-speech`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "there is no place to show the word whether it is verb or ajective. Can help to add a field and show it"

## Context

A vocabulary entry currently holds the English word, its Chinese
meaning, alternates, its word set, and (since spec 017) a pronunciation.
It has no part of speech, so a learner can't tell whether *zealous* is an
adjective or *undertake* a verb. Some uploaded meanings work around this
inside the Chinese text, for example "租金；租用；（动词）出租". Spec 018's
enrichment already fills in missing fields for uploads; this feature adds
part of speech as one more.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See whether a word is a verb, adjective, … (Priority: P1)

A learner studying *zealous* wants to see that it is an adjective, so
they know how to use it, and in particular how to use it correctly in
the sentence step. The part of speech is shown as a short label next to
the meaning, for example `adj.` 热心的；热情的.

**Why this priority**: This is the request itself. Storing the field
without showing it delivers nothing.

**Independent Test**: Practice a word whose entry has a part of speech.
The label appears where described in FR-004, in the web UI and in the
command-line tutor. A word without one shows no label and no gap.

**Acceptance Scenarios**:

1. **Given** a word whose entry says it is an adjective, **When** the
   learner is recalling it, **Then** `adj.` is shown before its Chinese
   meaning. It is still shown after the answer is revealed.
2. **Given** a word that is used as more than one part of speech (e.g.
   *rent*, a noun and a verb), **When** it is shown, **Then** every
   recorded label is shown, in the recorded order (`n. v.`).
3. **Given** a word with no part of speech recorded, **When** it is
   practiced, **Then** nothing is shown in its place: no empty label, no
   error.
4. **Given** the sentence step for a verb, **When** the target word is
   displayed, **Then** its label is shown with it, so the learner writes
   the sentence using the right part of speech.

---

### User Story 2 - New uploads get their part of speech filled in (Priority: P1)

When a learner uploads bare words, spec 018 already fills in the
meaning, IPA and alternates. The part of speech should be filled in the
same way and shown in the preview, so the learner reviews it before
saving.

**Why this priority**: Uploads are how learners add words now. Without
this, every new word would lack a part of speech.

**Independent Test**: Upload `zealous`, `undertake`, `rent`. The preview
shows `adj.`, `v.` and `n. v.`, and after saving, practice shows those
labels.

**Acceptance Scenarios**:

1. **Given** an upload of bare words, **When** enrichment finishes,
   **Then** each word's preview row shows its part of speech next to the
   meaning.
2. **Given** an upload that already gives a part of speech for a word,
   **When** it is enriched, **Then** the given value is kept and not
   replaced.
3. **Given** the local AI returns a part of speech that isn't one of the
   allowed labels, or none at all, **When** the reply is checked,
   **Then** the word is saved without a part of speech and marked
   "part of speech needs review". The word itself is not rejected.
4. **Given** generated meanings, **When** a part of speech is recorded,
   **Then** the Chinese meaning no longer carries labels like "（动词）",
   because the part of speech now has its own field.
5. **Given** an expression such as *give up* or *tend to*, **When** it is
   enriched, **Then** it is labelled as a phrase (e.g. `phr. v.` for a
   phrasal verb) rather than forced into a single-word class.

---

### User Story 3 - Words I already have get a part of speech (Priority: P2)

The learner already has hundreds of words, in the shared folder and in
uploaded lists. They want those to show a part of speech too.

**Why this priority**: It makes the feature useful straight away for
existing words, but new uploads (US2) keep the feature growing on their
own.

**Independent Test**: After the fill, existing words show labels in
practice. A reviewed sample matches a standard learner's dictionary.
Nothing else in any entry has changed.

**Acceptance Scenarios**:

1. **Given** the existing vocabulary files, **When** the fill is done,
   **Then** every word, in the shared folder **and** in every learner's
   uploaded lists, either has a part of speech or appears on a review
   list with the reason.
4. **Given** the fill, **When** it changes files, **Then** each file is
   backed up first, only part-of-speech lines are added, and a review
   list of every filled word is produced for a person to check, as with
   the spec 017 pronunciation fill.
2. **Given** an existing entry, **When** its part of speech is added,
   **Then** its English, meaning, alternates, pronunciation and word set
   are unchanged.
3. **Given** a word whose recorded Chinese meanings cover two parts of
   speech (e.g. 租金 and 出租 for *rent*), **When** it is filled,
   **Then** both labels are recorded, in the order the meanings appear.

---

### Edge Cases

- **Multiple parts of speech**: both labels are kept and shown in order
  (`n. v.`).
- **Phrases**: phrasal verbs and multi-word expressions get a phrase
  label, not one guessed word class.
- **Hand-written values**: an entry written by hand with a label in a
  different style (`adjective`, `Adj`, `形容词`) is understood as the
  same label and shown in the standard form (`adj.`). A value that
  isn't a recognised part of speech is ignored with a warning, and the
  word still loads, as with a malformed pronunciation in spec 017.
- **Grading**: the part of speech never affects grading. The learner
  still types only the English word.
- **Existing entries**: in an upload, an existing entry's part of speech
  is kept unless the learner chooses "Update with this", the same rule
  as the other fields (spec 018).
- **Labels inside meanings**: labels already written into existing
  Chinese meanings (e.g. "（动词）告密") are left as written. Cleaning
  them up is out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each vocabulary entry MUST support an optional part of
  speech: one or more labels from a fixed set, in order. This applies to
  the shared folder, to uploaded lists, and to the files that store
  them.
- **FR-002**: The fixed label set MUST be: `n.` (noun), `v.` (verb),
  `adj.` (adjective), `adv.` (adverb), `prep.` (preposition), `conj.`
  (conjunction), `pron.` (pronoun), `det.` (determiner), `int.`
  (interjection), `num.` (number), `phr. v.` (phrasal verb) and `phr.`
  (other phrase or idiom).
- **FR-003**: Entries without a part of speech MUST keep working exactly
  as today. Existing files MUST NOT need any change to keep loading.
- **FR-004**: The part of speech MUST be shown with the Chinese meaning
  as short labels, in both the web UI and the command-line tutor. It
  MUST be shown **during recall, before the meaning**, like a dictionary
  entry ("adj. 热心的"). It is a hint that never reveals the English word.
  It MUST also appear on the answer reveal, the sentence step and the
  sentence feedback.
- **FR-005**: The import preview (spec 018) MUST show each word's part of
  speech, or a "part of speech needs review" mark.
- **FR-006**: Upload enrichment MUST fill in a missing part of speech
  using the existing local model, without any cloud service. The
  model's reply MUST be accepted only if every label is in the FR-002
  set; otherwise the word is saved without one and marked for review.
  The generated part of speech MUST agree with the generated Chinese
  meanings.
- **FR-007**: Uploads MUST accept a part of speech the learner supplies,
  both in the Markdown format and in the simple list format, and MUST
  keep it as given (normalised to the FR-002 form).
- **FR-008**: Generated Chinese meanings MUST NOT contain
  part-of-speech annotations such as "（动词）" or "v.", since the label
  has its own field.
- **FR-009**: Filled parts of speech MUST be checked for accuracy before
  release (Constitution Principle II). A reviewed reference set of words,
  including multi-class words and phrases, MUST be used to measure the
  local model's accuracy, as spec 018 does for meanings.
- **FR-010**: Grading, sentence review, practice history, word sets and
  pronunciations MUST be unaffected by the presence or absence of a part
  of speech.
- **FR-011**: A malformed part-of-speech value in a file MUST NOT break
  loading, grading or practice. The word shows no label, and a warning
  is reported.
- **FR-012**: Every existing word (the shared folder and all uploaded
  lists, about 710 words) MUST be given a part of speech by a one-time
  fill. Each file is backed up first. Only part-of-speech lines are
  added, and nothing else changes. A review list of every filled word is
  produced, and any word that can't be classified confidently is left
  empty and listed with a reason rather than guessed.

### Key Entities

- **Vocabulary Entry**: existing fields (English, Chinese meaning,
  alternates, word set, pronunciation) plus an optional **part of
  speech**, an ordered list of labels from the FR-002 set.
- **Part-of-Speech Label**: one of the FR-002 abbreviations, with its
  full name (shown as a tooltip or accessible name).
- **Import Item** (spec 018): gains a part of speech and a "part of
  speech needs review" mark.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a word with a recorded part of speech, its label is
  visible at every point FR-004 defines, with no extra click.
- **SC-002**: On the reviewed reference set of at least 50 words
  (including at least 10 multi-class words and 5 phrases), at least 95%
  of generated parts of speech match the reference, or are marked for
  review. 0 labels outside the FR-002 set are saved.
- **SC-003**: 0 generated Chinese meanings in new uploads contain
  part-of-speech annotations.
- **SC-004**: All existing vocabulary files and uploaded lists still load
  with 0 new warnings, and grading results are unchanged.
- **SC-005**: Adding a part of speech to an upload adds no noticeable
  time per word compared with spec 018. Enrichment of a 40-word list
  still shows steady progress and completes within a few minutes.
- **SC-006**: 100% of existing words either have a part of speech after
  the fill or appear on the review list, with at least 95% filled. In a
  spot check of 30 random filled words against a learner's dictionary,
  at least 29 match.

## Clarifications

### Session 2026-10-05

- Q: When is the part of speech shown? → A: During recall, before the
  Chinese meaning ("adj. 热心的"), and on every later step for that word.
- Q: Which existing words get a part of speech? → A: All of them: the
  shared folder and every learner's uploaded lists, by a one-time
  reviewed fill.

## Assumptions

- Labels use the short English abbreviations common in Chinese learners'
  dictionaries (`adj.`, `v.`), not Chinese names (形容词). The full name
  is available as a tooltip.
- Part of speech is recorded per entry, not per meaning. A word with
  meanings in two classes lists both labels. Tying each label to
  specific meanings is out of scope.
- New uploads get their part of speech from the same local model that
  already writes meanings (spec 018), in the same request. The offline
  pronunciation dictionary has no part-of-speech data.
- Cleaning up part-of-speech text already embedded in existing meanings
  is out of scope.
- The one-time fill edits learner data files in place (`vocabulary/` and
  `word-lists/`, which are not in git), with backups kept in the
  gitignored backups folder, as the spec 017 fill did.
- The trusted-household setup of specs 015, 016 and 018 still applies.
  Nothing leaves the machine.
