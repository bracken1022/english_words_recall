# Feature Specification: Personal Word Lists per Account

**Feature Branch**: `016-per-user-word-lists`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Each user can upload the words list and each user can recall the words separately."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload my own word list from the web UI (Priority: P1)

Since spec 015, each household member logs in to their own account, but
everyone still practices from one shared vocabulary folder that only the
operator can change by editing files on the machine. A learner wants to
add the words *they* are studying themselves: from the web UI, on any
device, they pick a word-list file and upload it, and its words become
available for them to practice right away, without anyone touching the
computer running the tutor.

**Why this priority**: Without a way for a learner to get their own words
in, there is nothing personal to practice. This is the core of the ask.

**Independent Test**: Log in as account A, upload a word-list file from the
web UI, and confirm A's word-set screen immediately offers those words and
A can practice them.

**Acceptance Scenarios**:

1. **Given** a learner is logged in on the word-set screen, **When** they
   choose "Upload word list" and pick a valid word-list file, **Then** they
   see how many words were added and the new list appears as a word set
   they can practice immediately.
2. **Given** an uploaded file in which some entries are malformed (e.g. a
   word with no meaning), **When** it is uploaded, **Then** the valid words
   are added, and the learner is told how many entries were skipped and
   why, in plain language.
3. **Given** a file that contains no valid words at all, or is not a
   supported word-list file, **When** it is uploaded, **Then** nothing is
   added and the learner is told the file couldn't be used and what format
   is expected.

---

### User Story 2 - Practice only my own words (Priority: P1)

Each learner wants to recall the words in *their* lists only. The words
another person uploaded should not show up in their word sets or practice
sessions, and their own uploads shouldn't clutter anyone else's.

**Why this priority**: This is the second half of the ask ("each user can
recall the words separately"); uploads are of little use if they get mixed
into everyone's practice.

**Independent Test**: A uploads list X and B uploads list Y. A's word-set
screen offers X (and not Y); B's offers Y (and not X). A practice session
for each contains only that learner's words.

**Acceptance Scenarios**:

1. **Given** A uploaded list X and B uploaded list Y, **When** A opens the
   word-set screen, **Then** A sees X and does not see Y, and "Practice
   everything" for A counts and includes only A's words.
2. **Given** the same setup, **When** B practices, **Then** no word from X
   ever appears in B's session.
3. **Given** A and B both upload a list with the same name, **When** each
   views their word sets, **Then** each sees only their own version.
4. **Given** a learner has uploaded at least one list, **When** they open
   the word-set screen, **Then** they see only their own lists — the shared
   vocabulary folder's word sets are no longer shown to them.
5. **Given** a learner has never uploaded a list (or has deleted all of
   their lists), **When** they open the word-set screen, **Then** they see
   the shared vocabulary folder's word sets exactly as today, along with
   the "Upload word list" action.
6. **Given** a learner uploads their first list, **When** the upload
   finishes, **Then** they are told that from now on they'll practice
   their own lists instead of the shared words.

---

### User Story 3 - Manage my lists: replace and remove (Priority: P2)

Over time a learner's lists change: they fix typos, add words to a unit, or
finish a unit and want it gone. They want to see the lists they've
uploaded, upload a corrected version to replace one, and delete a list
they no longer need.

**Why this priority**: Upload + separate practice is already usable;
managing lists keeps it usable after the first week.

**Independent Test**: Upload list "unit1", upload a corrected "unit1"
(replace), confirm the word set shows the corrected words only; delete
"unit1", confirm it no longer appears; another account's lists are
unaffected throughout.

**Acceptance Scenarios**:

1. **Given** a learner has uploaded lists, **When** they open "My word
   lists", **Then** they see each list's name, word count, and when it was
   uploaded.
2. **Given** a learner has a list named "unit1", **When** they upload
   another file named "unit1", **Then** they are asked to confirm replacing
   it, and on confirming, the old words are replaced by the new ones.
3. **Given** a learner has a list, **When** they delete it and confirm,
   **Then** it disappears from their lists and word sets; their past
   practice history for those words is kept.
4. **Given** a learner is mid-session in a word set, **When** they replace
   or delete that list from another device, **Then** the session in
   progress is not broken; the change applies from the next time they
   choose a word set.

---

### Edge Cases

- File too large: uploads over a sensible limit (see FR-010) are refused
  with a message stating the limit; nothing is added.
- Duplicate words inside one upload, or the same word in two of the
  learner's lists: both are kept as uploaded (each list is practiced as
  given); "Practice everything" may therefore show the word more than
  once, matching how duplicate words across vocabulary files behave today.
- List names: derived from the uploaded file's name; names that are empty
  after removing unsafe characters fall back to "My words" (with a number
  if taken).
- Upload without being logged in: refused like any other action (spec 015).
- The tutor was started locked to one group (start-up option): uploading is
  still allowed, but the locked session ignores word sets as it does today;
  the upload screen says new lists appear when the tutor isn't locked.
- Server restarts: uploaded lists are kept; they are stored on the tutor's
  machine, not in the browser.
- Two uploads at the same time by the same learner: each completes on its
  own; if both have the same name, the later one wins after confirmation.
- Words containing Chinese, accented letters, or punctuation upload and
  display correctly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A logged-in learner MUST be able to upload a word-list file
  from the web UI, from any device that can reach the tutor.
- **FR-002**: The system MUST accept both (a) the existing vocabulary
  Markdown format (the same files the shared vocabulary folder uses
  today), and (b) a simple list with one word per line —
  `English, Chinese` plus optional extra accepted answers — including a
  CSV file saved from a spreadsheet. Each word needs an English expression
  and a Chinese meaning; alternate accepted answers are optional. The
  upload screen shows a short example of the simple format.
- **FR-003**: On upload, the system MUST add every valid word, skip invalid
  entries, and tell the learner how many words were added and how many
  entries were skipped with a short reason for each (e.g. "line 12: no
  Chinese meaning").
- **FR-004**: A file with no valid words, or in an unsupported format, MUST
  be rejected with nothing added and a message describing the expected
  format.
- **FR-005**: Each uploaded file MUST become one named word list owned by
  the uploading account, named after the file (without extension).
- **FR-006**: Each account MUST have its own word-list storage. An account
  with at least one uploaded list MUST practice only from its own lists;
  an account with none MUST practice from the shared vocabulary folder as
  today. No account ever sees another account's uploaded lists.
- **FR-007**: Each uploaded list MUST appear as its own word set on the
  owner's word-set screen; "Practice everything" MUST cover only the words
  that account currently practices from (its own lists, or the shared
  folder if it has none).
- **FR-008**: Learners MUST be able to view their lists (name, word count,
  upload date), replace a list by uploading a file with the same name
  (after confirming), and delete a list (after confirming).
- **FR-009**: Replacing or deleting a list MUST NOT alter or remove any
  practice history, and MUST NOT disrupt a practice session already in
  progress.
- **FR-010**: The system MUST refuse uploads larger than 1 MB or containing
  more than 5,000 words, with a message stating the limit.
- **FR-011**: Uploaded lists MUST persist across server restarts and be
  readable by a person as plain files on the tutor's machine, consistent
  with how vocabulary and history are kept today.
- **FR-012**: Uploading, listing, replacing, and deleting MUST require a
  login, and a learner MUST only ever be able to see or change their own
  lists.
- **FR-013**: Grading, sentence review, practice order/mode choices, and
  the practice history format MUST behave exactly as today for uploaded
  words.

### Key Entities

- **Word List**: A named set of words owned by one account. Attributes:
  name, owner account, upload date, words. One uploaded file = one list.
- **Account Word Folder**: Each account's own collection of uploaded word
  lists. When it holds at least one list, it replaces the shared
  vocabulary folder for that account.
- **Shared Vocabulary Folder**: The existing operator-maintained folder;
  used only by accounts whose own folder is empty, and by the command-line
  tutor.
- **Word**: The existing vocabulary item: English expression, Chinese
  meaning, optional alternate accepted answers. Belongs to one word list.
- **Upload Result**: What the learner is told after an upload: words
  added, entries skipped with reasons, and whether a list was created or
  replaced.

### Data Handling (Constitution Principle III)

- **Collected**: the word lists a learner uploads (words and meanings),
  the list names, and upload dates, stored under that learner's account.
- **Why**: so each learner can practice their own words.
- **Access**: only the owning account can see, practice, replace, or
  delete its lists through the web UI; files stay on the operator's
  machine and are never sent elsewhere.
- **Not done**: uploaded content isn't shared with other accounts, used
  for anything other than that learner's practice, or sent to any third
  party (sentence review already sends only the learner's own sentence to
  the local model, unchanged).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can upload a 50-word list and start practicing it
  in under 1 minute, from a phone.
- **SC-002**: After two learners each upload different lists, 0 words from
  one learner's lists appear in the other learner's word sets or sessions.
- **SC-003**: For an upload containing malformed entries, 100% of valid
  words are added and every skipped entry is reported with its position.
- **SC-004**: Uploaded lists are all still present and practicable after a
  server restart (0 lost).
- **SC-005**: Replacing or deleting a list leaves 100% of the learner's
  existing practice history intact.
- **SC-006**: A learner who has never used a computer's file system for
  the tutor (e.g. the second household member) can add their own words
  without help, using only the web UI.

## Assumptions

- Builds on spec 015: accounts, login, per-account sessions and histories
  already exist; this feature adds per-account vocabulary.
- Switching from shared words to own lists is all-or-nothing per account:
  there is no mixing of shared and own word sets. A learner who wants some
  shared words alongside their own uploads them as one of their lists
  (the shared folder's Markdown files upload as-is).
- The shared vocabulary folder itself is never changed by uploads; it is
  still maintained by the operator editing files.
- Learners prepare word-list files themselves (e.g. exported from a
  spreadsheet or notes app); editing individual words inside the web UI
  is out of scope — fix a list by re-uploading it.
- The command-line tutor keeps reading the vocabulary folder given on its
  command line, unchanged.
- Uploaded lists are only practiced, not shared or copied between
  accounts; sharing a list means each person uploads the same file.
- The trusted-household assumptions of spec 015 still apply (no virus
  scanning or content moderation of uploaded word lists beyond format
  validation).
- Practice history keeps recording the English word as today; deleting a
  list doesn't delete history entries for its words.
