# Feature Specification: Speak Your Sentence Instead of Typing It

**Feature Branch**: `009-voice-sentence-input`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Now lets integrate with the voice input, I can say a sentence instead of manually input it."

## Clarifications

### Session 2026-09-21

- Q: How should this feature handle the fact that the most common browser voice-input implementation sends audio to a third-party cloud service, given this app's existing "local machine only" and voice-data-privacy rules? → A: Use a local speech-to-text model — the same "runs on the learner's own machine/network" pattern the app already uses for sentence correction (Ollama) — instead of either cloud transcription or the browser's own built-in recognizer. Recorded audio is sent to that local service for transcription, never to a third party. This may require installing a new local speech-recognition library/model as part of setup, the same way Ollama itself is a local prerequisite today.
- Q: Should the local speech-to-text service be a hard requirement for the app to start, or an optional dependency that degrades gracefully (like Ollama already does) if it's not running? → A: Optional/soft dependency — mirrors how Ollama already works: if the local speech-to-text service isn't reachable, voice input is simply unavailable (same messaging/fallback as FR-004), typing works as normal, and the app starts fine either way.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Speak a sentence instead of typing it (Priority: P1)

A learner reaches the sentence-writing step and, instead of typing, wants
to say their sentence out loud and have it appear as text they can review
before submitting — faster and more natural than typing on a phone.

**Why this priority**: This is the entire ask — a second way to fill in
the same sentence, without changing what happens after it's filled in.

**Independent Test**: Can be fully tested by starting voice input on the
sentence-writing step, speaking a sentence, and confirming it appears as
editable text in the same field a typed sentence would use — independent
of every other part of the app.

**Acceptance Scenarios**:

1. **Given** the learner is on the sentence-writing step, **When** they
   start voice input and speak a sentence, **Then** the spoken sentence
   appears as text in the sentence field, exactly where a typed sentence
   would appear.
2. **Given** the sentence field now holds a spoken-and-transcribed
   sentence, **When** the learner reviews it, **Then** they can edit it
   like any typed text before submitting — nothing is submitted directly
   from speech without landing in the field first.
3. **Given** the learner's browser or device doesn't support voice input
   (or the microphone is unavailable/denied), **When** they reach the
   sentence-writing step, **Then** they can still type their sentence
   exactly as they can today, with voice simply not offered.

### Edge Cases

- What happens when speech is misheard or transcribed incorrectly? The
  learner sees the (possibly wrong) text in the field and can correct it
  before submitting, the same as fixing a typo.
- What happens when the learner starts voice input but says nothing, or
  stops partway? The field is simply left as whatever was recognized (or
  empty); nothing is forced or auto-submitted.
- What happens when the app is opened from another device on the same
  local network rather than the same machine running it? Voice input may
  not be offered there even though typing still works — see Assumptions.
- What happens when the local speech-to-text service isn't installed or
  isn't running? Voice input is unavailable (same as any other "not
  available" case, FR-004) and the app otherwise starts and works
  normally — it is never a hard requirement (FR-007).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let the learner start voice input from the
  sentence-writing step as an alternative to typing.
- **FR-002**: The system MUST place the recognized speech into the same
  sentence field used for typing, as editable text, before the learner
  submits — never submitting a sentence directly from speech without it
  first landing in that field for review.
- **FR-003**: The system MUST NOT remove, hide, or disable the existing
  typed-text option; voice input is an additional way to fill the same
  field, never a replacement for it.
- **FR-004**: The system MUST clearly indicate when voice input isn't
  available (unsupported browser/device, denied or missing microphone,
  or any other reason) and MUST let the learner continue by typing
  without the sentence-writing step being blocked in any way.
- **FR-005**: The system MUST perform speech-to-text transcription using a
  speech-recognition service running on the learner's own local machine
  or local network — the same "local model server" pattern already used
  for sentence correction (spec 001) — and MUST NOT send the learner's
  recorded voice audio to any third-party or cloud service.
- **FR-006**: The system MUST NOT retain the recorded audio beyond what's
  needed to produce the transcription for that one sentence; only the
  resulting text is kept afterward (in the sentence field, and later in
  the practice log, exactly as a typed sentence already is today).
- **FR-007**: The local speech-to-text service MUST be an optional
  dependency, not a hard requirement — the app MUST start and remain
  fully usable (typing included) whether or not that service is
  installed or reachable, the same way the app already tolerates the
  local sentence-correction service (Ollama) being unavailable (spec 003
  FR-009). When it isn't reachable, voice input is treated the same as
  any other "not available" case (FR-004).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner on a supported setup can produce a submitted
  sentence using only speech, without typing a single character.
- **SC-002**: A learner on an unsupported setup completes the
  sentence-writing step in exactly as many steps as before this feature
  — voice's absence adds no extra friction.
- **SC-003**: 100% of recognized speech appears as editable text before
  submission; none is ever sent for correction without the learner having
  had the chance to see and change it first.
- **SC-004**: Transcribing spoken sentences requires no network request
  beyond the learner's own local machine/network, the same way sentence
  correction already requires none beyond it — verifiable by the same
  means already used to confirm the correction pipeline stays local.

## Assumptions

- Voice input applies to the sentence-writing step only — the feature
  description specifically says "a sentence," and the recall step (typing
  the English word itself) is a short, deliberately-recalled answer, not
  a scenario where dictation makes sense; it is unaffected.
- Recognized speech always lands in the field for review rather than
  auto-submitting, so speech-recognition mistakes are never confused with
  the learner's own grammar mistakes in the downstream sentence-correction
  review.
- The app's LAN-reachability (spec 003 FR-013) is unaffected in principle,
  but browsers commonly restrict microphone *capture* to "secure contexts"
  (the page's own origin served over HTTPS, or `localhost`) — this is
  independent of where transcription happens afterward. This app is
  typically reached over plain HTTP at a LAN address from other devices,
  so voice input may only actually work when using the app on the same
  machine that's running it, or once/if that's set up with HTTPS. Typing
  remains fully unaffected everywhere either way (FR-003/FR-004).
- Setting up local speech-to-text is expected to require installing a new
  local dependency (a speech-recognition library and/or model), the same
  way Ollama is already a required local prerequisite for sentence
  correction — the exact library/model choice is a planning-phase
  decision, not fixed by this spec.
- Recorded audio is transient: it exists only long enough to produce a
  transcription for the current sentence, and is not written to disk or
  kept once that transcription completes (FR-006).
