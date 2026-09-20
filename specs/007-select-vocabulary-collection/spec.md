# Feature Specification: Choose a Vocabulary Collection Before Practicing

**Feature Branch**: `007-select-vocabulary-collection`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "There is a new requirements, I can choose which collect of the vocabularies I want to go through. Such as if I have two md files inside ./vocabulary folder, then I can choose one to go through"

## Clarifications

### Session 2026-09-20

- Q: Can the learner switch to a different collection before finishing the one they're currently on, or only after it's complete? → A: No mid-session switching — the collection picker only reappears once the current session reaches "complete" (Option A).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose a collection before practicing (Priority: P1)

A learner keeps more than one set of words to practice — for example, one Markdown file per lesson or topic in their vocabulary folder. Today, practicing just one of those sets means restarting the app with a command-line option; this learner instead wants to open the app and simply pick which set to go through.

**Why this priority**: This is the entire ask — without it, there is no way to focus a session on one set of words from within the app itself.

**Independent Test**: Can be fully tested by placing two differently-tagged sets of words in the vocabulary folder, opening the app, and confirming both are offered as choices before any word appears — independent of every other part of the app.

**Acceptance Scenarios**:

1. **Given** the vocabulary folder contains words from more than one collection, **When** the learner opens the app, **Then** they see a list of the available collections, plus an option to practice every loaded word combined, before any recall content appears.
2. **Given** the learner selects one named collection, **When** they proceed, **Then** the practice session only ever shows words from that collection, going through the same recall → sentence → feedback → completion flow as today.
3. **Given** the learner selects "practice everything," **When** they proceed, **Then** every loaded word across every collection appears, exactly matching today's behavior when no collection is chosen.
4. **Given** the vocabulary folder has no valid words at all, **When** the learner opens the app, **Then** they see today's existing "no words are waiting" message directly, with no choice screen shown.

---

### User Story 2 - Start a different collection without restarting (Priority: P2)

A learner who just finished going through one collection wants to immediately practice a different one (or the same one again), without stopping and restarting the app.

**Why this priority**: This is what makes the choice genuinely useful across a single sitting rather than a one-time decision at launch; it depends on User Story 1 existing first.

**Independent Test**: Can be tested by finishing a session for one collection and confirming the same choice screen reappears, offering to start again with any collection.

**Acceptance Scenarios**:

1. **Given** a practice session has just reached "session complete," **When** the learner asks to practice again, **Then** they are shown the same collection-choice screen offered at the very start.
2. **Given** they pick a different collection this time, **When** they proceed, **Then** the new session is limited to that collection only, independent of the previous session's progress or tally.

---

### Edge Cases

- What happens when only one collection exists? It still appears as a valid choice — the learner is never left with nothing to pick.
- What happens to words that have no collection tag at all? They remain reachable as their own choice, distinct from any named collection, so no loaded word is ever silently hidden from selection.
- What happens if the vocabulary folder changes (files added, removed, or edited) while the app is already running? Out of scope for this feature — vocabulary is loaded once per session the same way it already is today (see Assumptions).
- What happens if the learner wants to switch collections before finishing the one they're on? Not supported — the collection-choice screen only reappears once the current session reaches "complete" (FR-006). There is no mid-session abandon/switch action; this matches the app's existing forward-only session flow (no skip/back at the item level).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST show the learner the list of distinct vocabulary collections available, before any recall content is shown, whenever more than zero collections exist.
- **FR-002**: The system MUST let the learner select exactly one collection from that list, or select an option to practice every loaded word combined regardless of collection.
- **FR-003**: Once a collection is selected, the system MUST limit the practice session to only the words belonging to that collection — or, for the "practice everything" choice, every loaded word — using the existing recall/sentence/feedback/completion flow unchanged.
- **FR-004**: The system MUST treat words with no collection tag as their own selectable choice, so every loaded vocabulary word remains reachable through some option in the list.
- **FR-005**: When there are no valid vocabulary words to load at all, the system MUST show the existing "no words are waiting" message directly, without presenting a choice screen.
- **FR-006**: When a practice session reaches its normal completion, the system MUST let the learner return to the collection-choice screen to start a new session, with the same or a different collection, without restarting the application. The system MUST NOT offer a way to switch collections before that point — a session in progress runs to completion on the collection it started with, matching the existing forward-only session flow.
- **FR-007**: The system MUST continue to support starting with one collection already chosen via a startup option (as it already does today), bypassing the interactive choice screen in that case.
- **FR-008**: Each collection in the list MUST be labeled with its existing collection name (the same tag already authored on its words); the "practice everything" option MUST be clearly distinguished from any single named collection.

### Key Entities *(include if feature involves data)*

- **Vocabulary Collection**: A named grouping of vocabulary words that already exists in the authored content today (the collection tag already present on each word). This feature adds a way to choose one to focus a session on; it does not introduce a new stored entity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner with multiple vocabulary collections can start a session limited to just one of them in a single selection, with no configuration editing or application restart.
- **SC-002**: 100% of loaded vocabulary words remain selectable through some listed choice (a named collection, or "practice everything") — none become permanently unreachable.
- **SC-003**: A learner can go from finishing one collection to starting a different one in two actions or fewer (return to the choice screen, then select).
- **SC-004**: Existing unattended/scripted startup with a collection already chosen continues to work exactly as before, unchanged.

## Assumptions

- **"Collection" means the existing collection tag already authored on each word (today: `group`), not literally "one Markdown file."** The feature description's example (two files, pick one) already matches this in the learner's own vocabulary folder today, since each file's words currently share one tag. Reusing the existing tag needs no changes to how vocabulary is authored or loaded, and doesn't foreclose true per-file selection later if the two ever need to diverge.
- This feature's interactive choice screen applies to the web UI, the app's primary interactive surface. The command-line tool keeps its existing startup option for choosing a collection in advance, unchanged, since scripted/unattended use has no interactive screen to show.
- The previous behavior — starting with no collection chosen and practicing everything by default — remains available as the explicit "practice everything" option; it is no longer the silent default when no startup option is given, since the learner is now asked directly instead.
- Vocabulary content is still loaded once per session, the same as today; changes to the vocabulary folder while a session is already running are not picked up until a new session is started from the choice screen.
- No new persistent data is introduced. This feature is presentation and selection only; it does not add a database, user accounts, or any new file format.
