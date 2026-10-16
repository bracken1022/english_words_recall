# Contract: Voice Input in Sentence Recall (UI)

Device-independent behaviour (FR-010). The web page is the first
implementation; a future iPhone app follows the same rules with its own
on-device recogniser.

## Where

- Only on the `sentence-recall` step, before the sentence is revealed
  (FR-001). Word recall, reveal and every other screen have no mic.
- The CLI has no voice input.

## Controls (web)

- A mic button sits beside the attempt box: "Speak".
- **Idle → listening**: tap "Speak". The first time, the browser asks for
  microphone permission. While listening the button reads "Stop" and a
  "Listening…" note with a running timer shows.
- **Listening → transcribing**: tap "Stop", or 30 seconds pass (FR-007).
  A "Turning speech into text…" note shows; the mic button is disabled.
- **Transcribing → idle**: the text is added to the attempt box (after any
  existing text, separated by a space; FR-003) and the box is focused so
  the learner can edit it. A small label reads "We heard this. Fix
  anything before you check." (FR-011). Nothing is revealed or marked
  (FR-002).
- Only one recording at a time; taps during transcribing are ignored.

## Leaving mid-recording

- Show sentence, Skip, End session, logout, or moving to another screen
  stops the recording and discards it; nothing is uploaded or added.
- If a transcription returns after the step has changed, its text is
  dropped.

## When voice isn't available (FR-008, FR-009, US2)

| Situation | What the learner sees |
|---|---|
| Recogniser not installed (`voice_available: false`) | No mic button. Typing works as before. |
| Browser can't record, or the page isn't secure (phone over `http://`) | No mic button, and a one-line note: "Voice needs this page on the Mac itself (or over https)." |
| Microphone permission denied or no microphone | Button stays; a note: "The microphone is blocked. Allow it in the browser, or type instead." |
| `nothing_heard` | Note: "Didn't catch that. Try again, or type it." The box is unchanged. |
| `unavailable` or a network error | Note: "Voice isn't working right now. Type it instead." The box is unchanged. |

## Privacy text

- The attempt label changes from "Your sentence (optional, stays on this
  device)" to "Your sentence (optional, not saved)".
- Nothing about the recording or its text appears in the practice
  history.

## Reveal

- On "Show sentence" the page sends the attempt with the reveal (see
  `practice-api.md`) and renders `comparison` as described in
  `word-diff.md`: "You said / wrote" with extra words struck through,
  then "Example" with missing words underlined.
- No comparison (empty attempt): only the example shows, as in spec 021.
