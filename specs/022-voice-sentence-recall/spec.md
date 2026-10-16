# Feature Specification: Voice Answers for Sentence Recall

**Feature Branch**: `022-voice-sentence-recall`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Let learners answer by voice, but only for the sentence recall. They can edit the transcript before it is checked. No audio is kept and it should carry over to a future IOS app."

## Overview

Sentence recall (spec 021) shows the Chinese translation of a word's
example sentence and asks the learner to produce the English sentence
from memory. Today they can only type their attempt, though the screen
already says "Type it, or just say it". This feature lets them **say the
sentence aloud** and have it turned into text in the same attempt box,
where they can correct it before revealing the real sentence. Word recall
stays typed. Nothing the learner says is kept as audio, and the behaviour
is defined so the same feature can work in a future iPhone app.

## Clarifications

### Session 2026-10-15

- Q: How is a spoken attempt checked? → A: Highlight differences, the
  learner still marks. At reveal, words that differ from the real
  sentence are highlighted; the learner still marks "Got it" or
  "Not yet". The app never marks it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Say the sentence instead of typing it (Priority: P1)

In sentence recall, the learner taps a microphone button, says the
sentence they remember, and sees what was heard appear as text in the
attempt box. They fix any recognition mistakes, then reveal the real
sentence and compare.

**Why this priority**: This is the whole request. Saying a sentence out
loud is closer to real speaking practice than typing it, and it is much
faster on a phone.

**Independent Test**: Start a session with sentence recall on, reach the
sentence-recall step, use voice input to say a sentence, confirm it
appears as editable text in the attempt box, edit it, reveal, and confirm
the edited attempt is the one shown next to the real sentence.

**Acceptance Scenarios**:

1. **Given** the sentence-recall step, **When** the learner starts voice
   input and says a sentence, **Then** the recognised text appears in the
   attempt box, where a typed attempt would be.
2. **Given** recognised text in the attempt box, **When** the learner
   edits it, **Then** the edited text is what is used at reveal; nothing
   is revealed or marked automatically when speech ends.
3. **Given** the learner has already typed part of an attempt, **When**
   they use voice input, **Then** the recognised text is added after what
   they typed rather than silently erasing it.
4. **Given** the learner reveals the sentence, **When** the reveal is
   shown, **Then** their attempt (spoken, typed or both) is shown next to
   the real sentence with the words that differ highlighted, and they
   still mark "Got it" or "Not yet" themselves, as today.
5. **Given** an attempt that differs only in capital letters or
   punctuation, **When** the sentence is revealed, **Then** no difference
   is highlighted.

---

### User Story 2 - Practice still works without voice (Priority: P2)

A learner whose device has no microphone, who denies microphone access,
or whose setup has no speech recognition available can still do sentence
recall exactly as today.

**Why this priority**: Voice is an extra. It must never block practice or
make the app fail to start.

**Independent Test**: Run with speech recognition unavailable, and
separately with microphone access denied; confirm sentence recall works
by typing (or by just revealing) and that a clear, short note explains
why voice is not available.

**Acceptance Scenarios**:

1. **Given** speech recognition is unavailable, **When** the learner
   reaches sentence recall, **Then** the microphone button is not offered
   (or is shown as unavailable) and typing, reveal, skip and marking all
   work as today.
2. **Given** the learner denies microphone access, **When** they try
   voice input, **Then** they see a short note saying the microphone is
   blocked, and can keep typing.
3. **Given** recognition fails or hears nothing, **When** speech ends,
   **Then** the attempt box keeps whatever it held before, and a short
   note invites them to try again or type.

---

### Edge Cases

- The learner starts recording and then reveals, skips or ends the
  session: recording stops and nothing is added to the attempt.
- Very long speech: recording stops automatically after a time limit
  (see FR-007) and what was heard so far is used.
- The learner speaks Chinese or another language: whatever is recognised
  is shown as is; the learner can clear it. No language judgement is made.
- The learner taps the microphone twice quickly: only one recording is
  active at a time.
- Background noise produces wrong words: the learner edits them, as with
  any recognition mistake.
- Word recall (typing the English word) never offers voice input.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The sentence-recall step MUST offer voice input as an
  alternative to typing the attempt. No other step (including word
  recall) offers voice input.
- **FR-002**: Recognised speech MUST be placed in the attempt box as
  editable text and MUST never trigger reveal, marking or moving on by
  itself.
- **FR-003**: If the attempt box already has text, recognised speech
  MUST be appended to it, not replace it.
- **FR-004**: Speech recognition MUST run on the learner's own device or
  their own local machine. Audio MUST never be sent to a third-party
  service.
- **FR-005**: Audio MUST be discarded as soon as its text is produced (or
  recognition fails). No audio is written to disk, logged, or kept in the
  practice history.
- **FR-006**: The spoken attempt is treated exactly like a typed attempt:
  it is shown next to the real sentence at reveal, and, as in spec 021,
  only the learner's mark is kept in the history, never the attempt text.
- **FR-007**: A single recording MUST stop automatically after 30
  seconds, and the learner MUST be able to stop it earlier.
- **FR-008**: The app MUST show clearly when it is listening, when it is
  turning speech into text, and when voice is unavailable (no microphone,
  access denied, or recognition not set up), with a short note in each
  failure case.
- **FR-009**: Voice input MUST be an optional capability: the app starts
  and every practice mode works when speech recognition is unavailable.
- **FR-010**: Voice input behaviour (what is recorded, where text goes,
  what is kept, what happens on failure) MUST be defined independently of
  the device, so a future iPhone app can provide it with that device's
  own on-device recognition and the same rules.
- **FR-011**: The app MUST NOT present recognised text as a judgement of
  the learner's pronunciation. It is labelled as what was heard.
- **FR-012**: At reveal, the app MUST highlight where the attempt differs
  from the real sentence: words in the sentence that are missing or wrong
  in the attempt, and extra words in the attempt. Capital letters and
  punctuation are ignored. The highlight is a guide only; the learner
  always gives the "Got it" / "Not yet" mark, and the app never marks it.
  This applies to typed and spoken attempts alike; with an empty attempt,
  nothing is highlighted.

### Key Entities

- **Spoken attempt**: text recognised from one recording during sentence
  recall. Exists only on screen in the attempt box until the step ends;
  not stored.
- **Attempt comparison**: shown at reveal only; which words of the
  attempt and of the real sentence differ. Not stored.
- **Sentence recall result**: unchanged from spec 021 (the learner's mark
  in the practice history).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a sentence of up to 20 words, the recognised text
  appears in the attempt box within 3 seconds of the learner stopping.
- **SC-002**: On a reviewed set of at least 20 example sentences read
  aloud clearly by a learner, at least 90% of words are recognised
  correctly before any editing.
- **SC-003**: 0 audio files or audio data remain anywhere after a session
  ends, and 0 audio leaves the learner's device or local machine.
- **SC-004**: With speech recognition unavailable, 100% of sentence-recall
  steps can still be completed by typing or revealing.
- **SC-005**: 100% of spoken attempts land in the editable attempt box;
  0 steps advance or get marked without a learner action.
- **SC-006**: Existing practice history files still load with 0 errors,
  and no new attempt-text field is written.
- **SC-007**: On a reviewed set of attempt/sentence pairs, 100% of
  highlighted words are real differences (ignoring capitals and
  punctuation), and 100% of differing words are highlighted.

## Assumptions

- Voice is offered in the web app only. The CLI's sentence recall stays
  keyboard-only.
- Recognition follows the same rule as the earlier voice input (spec 009)
  and the rest of the app: local only, and an optional dependency that
  degrades gracefully when missing.
- Recognition is for English. The learner's attempt is always editable,
  so recognition mistakes are fixed by the learner, not judged by the app.
- The future iPhone app is out of scope here. This feature only keeps
  its rules device-independent (FR-010) so that app can follow them with
  the phone's own on-device recognition.
- Microphone permission is requested by the browser or device the first
  time voice input is used, not before.
- Privacy note (Constitution III): the feature collects the learner's
  voice only while they are recording, only to produce text for that one
  attempt, and keeps neither the audio nor the text.
