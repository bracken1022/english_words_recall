# Feature Specification: Web UI for Remote Access

**Feature Branch**: `003-web-ui`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Build a web UI for the existing English vocabulary tutor. Goal:
allow the tutor to be used from other devices (phone, tablet, another computer) through a web
browser, on the same local network, with no authentication and no database, reusing the existing
vocabulary/progress Markdown files and the existing local Ollama review pipeline unchanged. Not
exposed to the public Internet by default. Desktop/mobile/tablet browser compatible, simple and
responsive. Out of scope: public Internet hosting, user accounts, cloud deployment, multiple
users, voice input, speech recognition."

## Clarifications

### Session 2026-09-18

- Q: Does the sentence-writing step happen after every recall attempt, or only after a correct one? → A: Always ask for a sentence, correct or incorrect (matches existing CLI behavior exactly).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Practice vocabulary recall in a web browser (Priority: P1)

A learner opens the tutor's address in a web browser (on the same machine
running it, to start) and sees the Chinese meaning of the current vocabulary
item, types the English expression from memory, and is told whether they
were right — with the same grading rule and reveal behavior the existing
tutor already uses — before moving on to the next item.

**Why this priority**: This is the smallest slice that proves "practicing
vocabulary through a browser" works at all, and it's fully demoable without
the sentence-review/LLM piece. Every other story in this feature builds on
this one existing first.

**Independent Test**: Point the web server at a small vocabulary file, open
the page in a browser, complete several recall attempts (correct, incorrect,
blank), and confirm the grading and revealed expression match what the
existing command-line tool would do for the same file and inputs.

**Acceptance Scenarios**:

1. **Given** the current vocabulary item has a Chinese meaning and English
   expression, **When** the page loads, **Then** only the Chinese meaning is
   shown and the English expression is not present anywhere in the page
   until an answer is submitted.
2. **Given** the learner submits a correct answer, **When** it is graded,
   **Then** the page shows it as correct and reveals the accepted
   expression(s).
3. **Given** the learner submits an incorrect answer, **When** it is graded,
   **Then** the page shows it as incorrect and reveals the correct
   expression(s).
4. **Given** the learner submits a blank answer, **When** it is graded,
   **Then** it is treated as incorrect and the page still reveals the
   expression, without an error.
5. **Given** the learner has finished with the current item, **When** they
   choose to continue, **Then** the next item's Chinese meaning is shown, and
   there is no control that skips an item without answering or returns to a
   previous one.

---

### User Story 2 - Get sentence-writing practice with LLM feedback in the browser (Priority: P2)

The learner writes an original sentence using the target expression; while
the sentence is reviewed by the existing local LLM pipeline, the page shows
a visible working indicator, then displays whether the sentence is
grammatically correct, whether it uses the target expression correctly, a
more natural version when one is available, and a short explanation.

**Why this priority**: This is what turns the recall drill into the full
learning loop the tutor already provides on the command line. It depends on
User Story 1 having already surfaced the target expression, so it is
sequenced after it.

**Independent Test**: Complete a recall step, submit a sentence, and confirm
a loading indicator appears while the review is in progress and all four
pieces of feedback are shown afterward — using the same review pipeline and
outcomes (needs correction / already correct / missing expression /
unavailable) the command-line tool already has.

**Acceptance Scenarios**:

1. **Given** the recall step for the current item has been answered
   (correct or incorrect), **When** the learner is prompted to write a
   sentence, **Then** the prompt asks them to use the target English
   expression in an original sentence.
2. **Given** the learner has submitted a sentence, **When** the review
   request is in progress, **Then** a visible, continuously animating
   working indicator is shown, with no fabricated percentage or step count.
3. **Given** the review completes with a usable result, **When** it is
   shown, **Then** the page displays whether the sentence is grammatically
   correct, whether the target expression was used correctly, a more natural
   version of the sentence when the review indicates one is available, and a
   short explanation — and the working indicator is gone by that point.
4. **Given** the sentence does not use the target expression, **When** the
   review completes, **Then** the page tells the learner the target
   expression is missing.
5. **Given** the local LLM is unavailable or its reply cannot be used,
   **When** the review is attempted, **Then** the page tells the learner
   review is unavailable — matching the existing tutor's behavior — and the
   learner can still continue to the next item.

---

### User Story 3 - Access the tutor from another device on the local network (Priority: P3)

A learner opens the same address from a phone, tablet, or another computer
on the same local network as the machine running the tutor, and the full
recall-and-sentence-review experience works the same as it does on the host
machine, in a layout that stays usable on a small touchscreen.

**Why this priority**: This is the "remote access" value on top of User
Stories 1 and 2 already working. It's lower priority because the tutor is
still fully usable — just from the host machine only — without it.

**Independent Test**: With the server running on one machine, open the same
address from a second device on the same network and complete a full
recall-and-sentence cycle from that second device.

**Acceptance Scenarios**:

1. **Given** the tutor's web server is running on a host machine, **When** a
   second device on the same local network navigates to that host's
   address, **Then** the same practice page loads and behaves identically to
   opening it on the host machine itself.
2. **Given** the page is opened on a phone-width screen, **When** the
   learner works through a recall-and-sentence cycle, **Then** every control
   (reading the meaning, typing an answer or sentence, continuing) remains
   reachable and legible without horizontal scrolling or overlapping
   elements.
3. **Given** the tutor is running with its default settings, **When**
   anything outside the local network attempts to reach it, **Then** it is
   not reachable — no public-Internet exposure is introduced by this
   feature.

---

### Edge Cases

- What happens when the vocabulary pool is empty (no valid items loaded)?
  The page shows a clear message and no practice session starts — mirroring
  the existing tutor's behavior for this case.
- What happens when a vocabulary Markdown entry is malformed? The rest of
  the pool still loads, and a warning identifying the problem is visible
  somewhere on the page — mirroring the existing tolerant-loading behavior
  rather than silently dropping it.
- What happens if the learner's browser is closed or loses connection while
  a sentence review is in progress? The server-side review may still run to
  completion, but nothing further is shown to that learner since there is no
  longer a connected page to show it on; this does not crash the server or
  affect later requests.
- What happens if the tutor is opened from two devices around the same
  time? See Assumptions — this is not a supported scenario for this
  iteration, consistent with "multiple users" being out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST serve the vocabulary practice experience as a
  web page reachable from a browser, requiring no software on the client
  device beyond the browser itself.
- **FR-002**: The system MUST present the Chinese meaning of the current
  vocabulary item without revealing the target English expression until an
  answer has been submitted.
- **FR-003**: The system MUST grade a submitted English answer using the
  same rule the existing tutor already uses (case-insensitive,
  whitespace-tolerant exact match against the item's accepted expressions,
  no typo tolerance) — this feature introduces no new grading logic.
- **FR-004**: The system MUST reveal the accepted expression(s) to the
  learner immediately after grading, regardless of whether the answer was
  correct.
- **FR-005**: The system MUST prompt the learner to write an original
  sentence using the target expression after every recall attempt for the
  current item — whether that attempt was graded correct or incorrect —
  matching the existing tutor's sentence-practice behavior exactly.
- **FR-006**: The system MUST send the learner's sentence to the existing
  local LLM review pipeline unchanged — this feature introduces no new
  prompt, model choice, or response contract.
- **FR-007**: While a sentence-review request is in progress, the system
  MUST show a visible, indeterminate working indicator on the page, with no
  fabricated percentage or step count — consistent with the tutor's existing
  loading-indicator behavior.
- **FR-008**: Once a sentence review completes with a usable result, the
  system MUST display: whether the sentence is grammatically correct,
  whether the target expression was used correctly, a more natural version
  of the sentence when the review indicates one is available, and a short
  explanation — using only the fields the existing review pipeline already
  returns.
- **FR-009**: If the local LLM is unavailable or its reply cannot be used,
  the system MUST tell the learner review is unavailable, matching the
  existing tutor's behavior, and MUST still let them continue to the next
  item.
- **FR-010**: The system MUST let the learner advance to the next vocabulary
  item after the sentence-review step concludes (successfully or not),
  moving strictly forward through the pool with no control to skip an
  unanswered item or return to a previous one.
- **FR-011**: The system MUST read vocabulary content only from the existing
  vocabulary Markdown files and MUST NOT introduce any other storage for
  vocabulary content.
- **FR-012**: The system MUST record each completed practice attempt to the
  existing progress Markdown log, in the existing format, and MUST NOT
  introduce a database or any other persistent store.
- **FR-013**: The system MUST be reachable from other devices on the same
  local network as the machine running it, using only a web browser on the
  other device.
- **FR-014**: The system MUST NOT require the learner to sign in, register,
  or otherwise authenticate in this version.
- **FR-015**: The system MUST NOT be reachable from outside the local
  network by default — this feature introduces no public-Internet exposure,
  port-forwarding, or tunneling.
- **FR-016**: The system MUST remain usable — every control reachable and
  legible, with no horizontal scrolling or overlapping elements — at
  phone-width, tablet-width, and desktop-width browser windows.
- **FR-017**: The system MUST show a visible warning when a vocabulary
  Markdown entry is malformed and cannot be loaded, while still making the
  rest of the vocabulary pool available — mirroring the existing
  tolerant-loading behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can complete a full recall-and-sentence-review cycle
  for one vocabulary item entirely through a web browser, with no other
  software required on the client device.
- **SC-002**: A learner can complete that same cycle from a second device on
  the same local network as the host machine, with no setup on that second
  device beyond opening a browser to the given address.
- **SC-003**: On a phone-width screen, a learner can complete every step of
  the cycle without needing to scroll horizontally or zoom to reach any
  control.
- **SC-004**: Every sentence submission shows a visible working indicator for
  the entire wait, gone at the exact moment feedback appears — zero
  instances of a fabricated percentage or step count, in the browser just as
  in the existing command-line tool.
- **SC-005**: When the local LLM is unavailable, a learner can still complete
  the recall step for every item through the browser; only sentence-review
  feedback is affected.
- **SC-006**: Vocabulary content and practice history remain readable as
  plain Markdown files outside the browser, identical in format whether the
  learner used the web UI or the existing command-line tool.

## Assumptions

- Single learner at a time is the supported case: the web server holds one
  shared "current item" state rather than a separate one per device or
  browser tab. Opening the tutor from two devices around the same time is
  not a supported scenario for this iteration (consistent with "multiple
  users" being explicitly out of scope) — behavior in that case is
  undefined and not tested for.
- The web UI is an additional way to run the same local tutor, not a
  replacement for the existing command-line interface; both may continue to
  exist side by side.
- Whoever runs the tutor starts the web server manually on the host machine,
  the same way the command-line tool is started today; this feature does
  not add an auto-starting background service.
- "A more natural version" refers to the existing review pipeline's
  corrected-sentence output, shown only when the review indicates a
  correction is needed. This feature changes nothing about the review
  pipeline's prompt, model, or language-variety targeting — it only displays
  what that pipeline already returns.
- Each time a practice session starts (e.g., the page is loaded), it begins a
  fresh pass through the vocabulary pool from the first item, exactly
  matching the existing command-line tool's behavior; there is no
  cross-session "resume where I left off" feature in this iteration.
- Plain HTTP over the local network is sufficient; no transport encryption is
  introduced, consistent with "no authentication required" and the
  local-network-only scope.
- Existing lesson/tag filtering (choosing which items to practice) remains
  available in some form through the web UI, since "existing learning
  behavior must remain unchanged" is stated to include it.
