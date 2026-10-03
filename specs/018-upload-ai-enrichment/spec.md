# Feature Specification: Local-AI Enrichment of Uploaded Word Lists

**Feature Branch**: `018-upload-ai-enrichment`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Enhance the existing vocabulary upload feature by adding automatic local-AI enrichment after a word list is uploaded. For each uploaded word or expression, generate an IPA transcription, a concise Chinese meaning and conservative alternates, using the existing local model. Show progress while enriching, show a preview the learner reviews and confirms, then save with the existing vocabulary Markdown format. Mark existing entries, never silently overwrite, handle per-item failures and an unavailable model without losing the upload, and validate everything before saving. Existing upload UI, My Word Lists, deletion, learning flow, progress tracking and sentence review stay unchanged."

## Context

Spec 016 lets each learner upload their own word lists; every word must
arrive with its Chinese meaning, and the list is saved immediately. Spec
017 added an optional `ipa` pronunciation field and explicitly kept new
uploads from being filled in automatically (017 FR-010). This feature
replaces that rule for uploads: the local model fills in what a word list
is missing, and the learner reviews the result before anything is saved.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload bare English words and get them filled in (Priority: P1)

A learner has a list of English words they want to study, often just the
words themselves, with no meanings or pronunciations. They upload it with
the existing "Upload word list" action. Instead of the list being rejected
for missing Chinese meanings, the tutor uses the local model to fill in a
pronunciation, a short Chinese meaning and any safe alternate spellings
for each word. The learner watches progress ("Enriching vocabulary:
12 / 40"), then reviews a preview and confirms it. The list then appears
in "My Word Lists", ready to practice.

**Why this priority**: This is the core of the request. Without it,
learners must type every meaning and pronunciation by hand before
uploading.

**Independent Test**: Upload a `.txt` file with 10 English words, one per
line. Confirm that progress counts up item by item, that the preview shows
English, IPA, Chinese and alternates for every word, and that after
confirming, the list appears in "My Word Lists" and can be practiced, with
the IPA shown when an answer is revealed.

**Acceptance Scenarios**:

1. **Given** a logged-in learner, **When** they upload a list containing
   only English words, **Then** the words are extracted, enrichment starts
   automatically, and the screen shows that enrichment is running with a
   real item count ("Enriching vocabulary: n / total").
2. **Given** enrichment is running, **When** each word finishes, **Then**
   the count advances by one, so the learner can see real progress rather
   than an estimated percentage.
3. **Given** enrichment has finished, **When** the preview is shown,
   **Then** each word shows its English text exactly as uploaded, its IPA,
   its Chinese meaning and its alternates (or an explicit "none").
4. **Given** the learner reviews the preview, **When** they confirm,
   **Then** the list is saved in the existing vocabulary Markdown format,
   under the list name taken from the file name as today, and appears in
   "My Word Lists".
5. **Given** the learner reviews the preview, **When** they cancel or
   discard it, **Then** nothing is added to their lists and their
   existing vocabulary is unchanged.
6. **Given** an uploaded list that already supplies a Chinese meaning,
   pronunciation or alternates for some words, **When** it is enriched,
   **Then** the supplied values are kept as given, and only the missing
   fields are generated.

---

### User Story 2 - Failures don't lose my upload (Priority: P1)

Enrichment depends on the local model, which can be stopped, slow, or
can occasionally return nonsense for a word. The learner wants every good
result kept, the bad ones clearly flagged, and the ability to try again
later without uploading the file a second time.

**Why this priority**: Without this, a single bad word or a stopped model
throws away the whole upload, and invalid model output could be written
into the learner's vocabulary.

**Independent Test**: With the model stopped, upload a list. Confirm a
clear "local AI unavailable" message, that the uploaded words are still
listed as waiting, and that "Retry" works once the model is started.
Separately, make one word return malformed output, and confirm the others
are enriched, the failed one is marked, and retrying only that word works.

**Acceptance Scenarios**:

1. **Given** the local model is not running, **When** a learner uploads a
   list, **Then** the extracted words are kept as a pending import, a
   clear message says the local AI is unavailable, and a "Retry
   enrichment" action is offered. No vocabulary file is created or
   changed.
2. **Given** a pending import whose enrichment failed, **When** the
   learner returns later (including after a server restart) and retries,
   **Then** enrichment resumes for the words not yet enriched, without
   re-uploading.
3. **Given** a batch where some words fail, **When** enrichment ends,
   **Then** the status reads "partially failed" with counts (e.g.
   "37 enriched, 3 failed"), the successful words are kept, and each failed
   word is marked with a short reason and can be retried on its own or with
   "Retry failed".
4. **Given** the model returns output that is malformed or fails
   validation for a word, **When** it is received, **Then** that word is
   treated as failed. The output is never shown as a valid result and
   never saved.
5. **Given** a batch is already enriching, **When** the learner presses
   upload, retry or confirm again (double-click, second tab, second
   device), **Then** no second batch starts for that import and the
   learner sees the running batch's progress.

---

### User Story 3 - Words I already have are flagged, not overwritten (Priority: P2)

A learner often uploads a list that overlaps with words they already
study. They want to see which words are already in their vocabulary, and
they want their existing entries left alone unless they choose to update
them.

**Why this priority**: This protects data the learner may have curated by
hand. It matters, but only once uploads with enrichment work at all.

**Independent Test**: With an existing list containing "receive", upload a
list containing "receive" and "zealous". Confirm the preview marks
"receive" as already existing and shows both the stored and the generated
values. Confirm that after confirming with the default choice, the stored
"receive" entry is byte-for-byte unchanged.

**Acceptance Scenarios**:

1. **Given** an uploaded word that already exists in the learner's current
   vocabulary, **When** the preview is shown, **Then** that word is
   clearly marked "already in your words" with the list it is in, showing
   the stored values next to the generated ones.
2. **Given** an existing word, **When** the learner confirms without
   choosing to update it, **Then** the existing entry stays unchanged.
3. **Given** an existing word, **When** the learner explicitly chooses
   "Update existing entry" for it and confirms, **Then** only that entry's
   fields are replaced by the reviewed values, and its English text and
   list stay the same.
4. **Given** the same word appears twice in one upload, **When** the
   preview is shown, **Then** it is enriched once and marked as a duplicate
   within the upload.

---

### User Story 4 - Pronunciations I can trust (Priority: P2)

The learner relies on the IPA to learn how to say a word. They want one
consistent convention across everything they import, and they want to be
told when the tutor is unsure, rather than shown a confident guess.

**Why this priority**: This is required by Constitution Principle II, and
it builds on the core flow.

**Independent Test**: Upload a list that includes a heteronym whose
meaning isn't given (e.g. "record", "lead") and an invented word. Confirm
those entries are marked "pronunciation needs review" instead of showing
a guessed IPA, while ordinary words show IPA in the chosen convention.

**Acceptance Scenarios**:

1. **Given** an ordinary word, **When** it is enriched, **Then** its IPA
   follows the single convention defined in FR-008.
2. **Given** a word whose pronunciation depends on a meaning that the
   upload does not fix, or which has no standard pronunciation, **When**
   it is enriched, **Then** it is marked "pronunciation needs review" with
   no IPA, rather than guessed.
3. **Given** an entry marked "pronunciation needs review", **When** the
   learner confirms the preview, **Then** the word is saved without IPA,
   and practice shows no pronunciation for it, as 017 does for words
   without IPA.

---

### Edge Cases

- **Multi-word expressions** (e.g. "tend to", "give up"): enriched as one
  expression, with a single IPA covering the whole expression.
- **Mixed-case or punctuated input** (e.g. "Hello!", "  zealous "): the
  English text is trimmed of surrounding whitespace only and otherwise
  kept exactly as uploaded. The model never rewrites it.
- **Model returns a different English word** (e.g. corrects a typo):
  rejected as invalid for that item. A suspected typo may be shown as a
  note, but the English is never changed.
- **Model output includes a group name, file name, or extra fields**:
  ignored. The group is always the list name derived from the file name,
  as today.
- **Alternates that are too broad** (e.g. "arduous" → "difficult"): the
  rules are given in FR-011. Alternates that fail them are dropped, and
  an empty alternates list is valid.
- **Alternate identical to the English word, or duplicated**: removed.
- **Very long Chinese output** (a dictionary-style paragraph): fails
  validation for that item (see FR-010) rather than being saved as is.
- **Large lists** (up to the existing 5,000-word limit): enrichment
  proceeds item by item with progress shown. The learner may leave the
  page and come back to the same pending import.
- **Learner deletes or replaces a list with the same name** while its
  import is pending: the existing replace-confirmation from spec 016
  applies when they confirm the import.
- **Model becomes unavailable mid-batch**: words already enriched are
  kept, and the status becomes "failed — local AI unavailable" with
  "n / total enriched". Retry continues from where it stopped.
- **A word list file in an unsupported format, or with no English words**:
  rejected exactly as today (spec 016 FR-004). No enrichment starts.
- **Server restart during enrichment**: the pending import and all
  results finished so far survive. The batch shows as interrupted and can
  be retried.

## Requirements *(mandatory)*

### Functional Requirements

**Upload and extraction (existing, extended)**

- **FR-001**: The existing upload action, accepted file types, size and
  word limits, list naming and error messages MUST be unchanged, except
  that a word without a Chinese meaning MUST no longer be skipped. It is
  kept for enrichment instead.
- **FR-002**: After extraction, enrichment MUST start automatically for
  the extracted words. No list is saved to "My Word Lists" until the
  learner confirms the preview.
- **FR-003**: The extracted words, everything enriched so far, and the
  status of each word MUST be kept as a pending import for that learner
  until the learner confirms or discards it. A pending import MUST
  survive a server restart and MUST be visible only to its owner.

**Enrichment**

- **FR-004**: Enrichment MUST use only the existing local model
  integration. No word or other learner data may be sent to any cloud or
  third-party service.
- **FR-005**: Enrichment MUST be performed, tracked and stored per word.
  The result for one word MUST NOT depend on another word succeeding.
- **FR-006**: For each word, the model MUST be asked only for enrichment
  data: pronunciation, Chinese meaning, alternates, and whether the
  pronunciation is ambiguous. The model MUST NOT determine the English
  text, the list or group name, file names or locations, the workflow
  state, or whether anything is saved. Any such content in its reply MUST
  be ignored.
- **FR-007**: Values supplied in the upload (Chinese meaning, IPA,
  alternates) MUST be kept, and only missing fields MUST be generated.

**Field rules**

- **FR-008**: IPA MUST follow one consistent convention for all imported
  vocabulary, and MUST be stored in the existing `ipa` field.
  The convention is **American English (General American)**, transcribed
  in the style of standard American learner's dictionaries. This applies
  to newly imported words only. Words already filled with British IPA by
  spec 017 are not changed, so a learner's collection may contain both
  accents (accepted trade-off; see Assumptions).
- **FR-009**: When a word's pronunciation is genuinely ambiguous (a
  heteronym whose meaning isn't fixed by the upload, a proper noun or
  abbreviation without a standard reading, or a word the model flags as
  uncertain), the word MUST be marked "pronunciation needs review" with
  no IPA, instead of a guess.
- **FR-010**: The Chinese meaning MUST be concise and suited to vocabulary
  study. It holds the common modern meanings, with separate important
  meanings divided by `；`. Validation limits: at most 4 meanings and at
  most 40 characters in total. Output with no Chinese characters, or
  longer than these limits, MUST fail validation.
- **FR-011**: Alternates MUST be conservative. Only spelling variants,
  British/American spelling pairs (tyre/tire, epitomise/epitomize) and
  very close equivalents that are safe as the same recall answer are
  allowed. Broad or merely related synonyms (arduous → difficult) MUST NOT
  be added. An empty list is valid. Each alternate MUST be a non-empty
  string that is different from the English word.

**Validation and persistence**

- **FR-012**: Before a word can be saved, it MUST have a non-empty
  English text identical to the extracted text. It MUST have either a
  valid IPA (per the 017 field format) or the "pronunciation needs review"
  mark. It MUST have a non-empty Chinese meaning that passes FR-010, and
  alternates that form a valid list per the existing schema. Words that
  fail these checks MUST be marked failed with a reason, and MUST NOT be
  written to any vocabulary file.
- **FR-013**: On confirmation, the system MUST save the confirmed words
  using the existing vocabulary Markdown format and the existing
  per-account list storage, with the group set to the list name as today.
  The new list MUST appear in "My Word Lists" like any uploaded list.
- **FR-014**: Failed words, and words still waiting for enrichment, MUST
  NOT be saved on confirmation. The preview MUST state how many words will
  be saved and how many will be left out. The left-out words MUST stay in
  the pending import for retry, or be discarded if the learner chooses.
- **FR-015**: Saving MUST be all-or-nothing per confirmation. A failure
  while saving MUST leave every existing vocabulary file exactly as it was
  before.

**Existing entries**

- **FR-016**: The preview MUST mark every word whose English text
  (compared case-insensitively, after trimming) already exists in the
  learner's current vocabulary. It MUST name the list it is in and show
  the stored values next to the generated ones.
- **FR-017**: An existing entry MUST NOT be changed unless the learner
  explicitly chooses "Update existing entry" for that word before
  confirming. By default, existing words are left as they are and not
  added again.

**Progress and status**

- **FR-018**: While enriching, the UI MUST show real item-based progress
  ("Enriching vocabulary: n / total") that updates as each word finishes.
- **FR-019**: The UI MUST show the import's status as one of: running,
  completed, partially failed (with enriched and failed counts), or failed
  (with a clear reason such as "local AI unavailable").
- **FR-020**: Only one enrichment batch per pending import may run at a
  time. Repeated start, retry or confirm requests while it runs MUST NOT
  start another batch or save twice.
- **FR-021**: Learners MUST be able to retry a single failed word, all
  failed words, or a batch that failed entirely, without re-uploading.

**Compatibility**

- **FR-022**: The existing upload screen layout, "My Word Lists" display,
  list deletion and replacement, practice flow, grading, IPA display,
  progress history, sentence correction and local sentence review MUST
  behave exactly as today. The enrichment status, progress and preview are
  added to the existing upload flow without redesigning it.
- **FR-023**: Words in previously saved lists and in the shared vocabulary
  folder MUST NOT be enriched or changed by this feature.

### Key Entities

- **Pending Import**: An uploaded list that the learner has not yet
  confirmed. It holds the owner account, the list name (from the file
  name), the extracted words in file order, the overall status (running /
  completed / partially failed / failed / interrupted), the progress
  counts, and when it was created.
- **Import Item**: One extracted word within a pending import. It holds
  the English text exactly as uploaded, any values the upload supplied,
  the generated values (IPA or "needs review", Chinese, alternates), its
  status (waiting / enriching / enriched / failed), a failure reason, its
  existing-entry match (the list name and stored values), and the
  learner's choice for an existing entry (keep / update).
- **Enrichment Result**: The model's proposed values for one item. It is
  untrusted until it passes validation (FR-012), and it never carries any
  file, group or workflow decisions.
- **Vocabulary Entry / Word List**: These are unchanged from specs 001,
  016 and 017.

### Data Handling (Constitution Principle III)

- **Collected**: the words of a learner's uploaded list and the generated
  enrichment, stored as a pending import under that learner's account
  until confirmed or discarded.
- **Why**: so that enrichment can be reviewed, resumed and retried without
  re-uploading.
- **Access**: only the owning account. The words are sent only to the
  local model on the tutor's machine, never to any cloud service.
- **Retention**: a pending import is removed when it is confirmed (after
  saving) or discarded. Pending imports are not used for anything else.

### Pedagogical Accuracy (Constitution Principle II)

- Generated content is never saved without the learner reviewing and
  confirming it.
- Uncertain pronunciations are flagged, not guessed (FR-009).
- Validation rejects malformed or overlong output (FR-010–FR-012).
- The model's behaviour for IPA, meanings and alternates MUST be checked
  against a reviewed set of known words, including heteronyms, spelling
  variants and broad-synonym traps, before the feature ships.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can upload a 40-word list of bare English words,
  review the preview and have the list ready to practice with no manual
  typing beyond confirming.
- **SC-002**: In a reviewed set of at least 50 known words, 0 invalid or
  malformed model outputs reach a saved vocabulary file. At least 95% of
  generated IPA matches a standard dictionary in the chosen convention,
  with the rest flagged for review rather than wrong.
- **SC-003**: In a reviewed set of at least 20 broad-synonym traps (e.g.
  arduous/difficult), 0 broad synonyms are saved as alternates. Known
  spelling-variant pairs get the expected alternate at least 90% of the
  time.
- **SC-004**: When the local model is unavailable, 100% of uploaded words
  are still available in the pending import, and existing vocabulary files
  are byte-for-byte unchanged.
- **SC-005**: When some words fail, 100% of successfully enriched words
  are kept, and each failed word can be retried individually.
- **SC-006**: Progress shown during enrichment always equals the actual
  number of finished words. No estimated percentages are shown.
- **SC-007**: Existing entries are byte-for-byte unchanged after any
  confirmation in which the learner did not choose "Update existing
  entry".
- **SC-008**: All existing automated tests for upload, word lists, practice,
  IPA display and sentence review still pass unchanged.

## Assumptions

- The "current vocabulary collection" used for existing-entry checks is the
  learner's effective word source from spec 016: their own uploaded lists,
  or the shared folder if they have none.
- The list name and group always come from the uploaded file name using the
  existing spec 016 rules. The `group: z-words` in the request's example
  illustrates this, and is not generated.
- The request's example `zealous → alternates: [enthusiastic]` conflicts
  with its own conservative-alternates rule. The rule (FR-011) takes
  precedence, so "enthusiastic" would not be generated for "zealous".
- Learners cannot edit generated fields inline in the preview. They
  review, choose keep/update for existing words, confirm, discard, or
  retry. Editing a word by hand is still done by re-uploading a corrected
  file, as in spec 016.
- Each learner has at most one pending import at a time. Uploading another
  file while one is pending asks whether to discard the pending one.
- The model is the one already configured for sentence review, with its
  thinking mode disabled as today. Enrichment uses the same local endpoint.
- The command-line tutor is unaffected. Enrichment is a web upload
  feature only.
- The one-off IPA fill tool from spec 017 remains separate and unchanged.
- IPA source (decided 2026-10-03 during implementation, after the
  local-model evaluation failed SC-002): pronunciations come from an
  offline American pronouncing dictionary (CMUdict) on the same machine.
  The local model provides only meanings and alternates. This is still
  fully local, as FR-004 requires. Words the dictionary doesn't have, or
  can't pronounce unambiguously, are marked "pronunciation needs review"
  (FR-009).
- IPA accent (clarified 2026-10-03): imports use American IPA, and
  existing British IPA entries are left as they are. A mixed-accent
  collection is accepted. Re-filling existing words in American IPA, or
  adding an accent setting, is out of scope. An entry whose IPA was
  supplied in the upload keeps that IPA as given, whatever its accent
  (FR-007).
