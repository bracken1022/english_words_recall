# Quickstart: Web UI State & Feedback Polish

Validation guide for proving the fix works end-to-end. Field/behavior
details live in `contracts/`; this file only sequences the checks.
Prerequisites are unchanged from `specs/003-web-ui/quickstart.md`.

## Prerequisites

- Everything from `003-web-ui/quickstart.md` (server running, a vocabulary
  file, Ollama running for the review-dependent scenarios).

## Scenario 1 — Input and submit button read as one unit (User Story 3)

1. Open the tutor. On the vocabulary-question step, look at the answer
   input and its Submit button.
   **Expected**: they sit together as one visual row/unit — the button is
   never pushed onto its own line below a full-width input.
2. Narrow the browser to phone width.
   **Expected**: the two remain grouped; neither wraps away from the
   other.
3. Repeat both checks once the sentence-input step is showing, for that
   form too.

## Scenario 2 — Word-answer feedback is colored and explicit (User Story 2)

1. Submit a **correct** vocabulary answer.
   **Expected**: feedback reads `Correct: <expression>` in green.
2. Submit an **incorrect** vocabulary answer (on a different item).
   **Expected**: feedback reads `Incorrect. The correct expression is:
   <expression>` in red.
3. For both, confirm the text alone (imagine viewing the page in
   grayscale) is enough to tell which one happened — color is never the
   only signal.

## Scenario 3 — Sentence section timing and word feedback persist together (User Story 1)

1. Load a vocabulary item. **Expected**: the sentence-practice section is
   not visible anywhere on the page yet.
2. Submit the vocabulary answer (try both a correct and, on another item,
   an incorrect one). **Expected**: immediately after, both the word
   feedback (Scenario 2's text/color) **and** the sentence-practice prompt
   + input are visible together — not one replacing the other.
3. While still on the sentence step, reload the page.
   **Expected**: the word feedback is still shown (re-derived from
   `GET /api/state`, not lost on reload), alongside the same sentence
   prompt/input.

## Scenario 4 — Loading state visible only during an actual review (User Story 1)

1. Before submitting a sentence, confirm "Reviewing your sentence..." and
   the spinner are **not** visible.
2. Submit a sentence. **Expected**: the spinner and "Reviewing your
   sentence..." appear immediately, and the sentence input/button become
   disabled (see Scenario 5).
3. Once the review completes (or fails, e.g. with Ollama stopped),
   **Expected**: the spinner and message disappear immediately, replaced
   by the result (or failure message) and a Continue control.
4. Click Continue and confirm the process, repeated on the next item,
   behaves the same way each time.

## Scenario 5 — Duplicate sentence submissions are prevented (User Story 1)

1. Submit a sentence, and while the spinner is showing, try clicking
   Submit again (or pressing Enter again) before the result appears.
   **Expected**: nothing happens on the second attempt — the control is
   disabled, no second request is sent, and only one result eventually
   appears.
2. (If testable in your setup) open the same session in a second browser
   tab while a review is in flight from the first, and attempt a sentence
   submission from the second tab too.
   **Expected**: the second tab's request is rejected (a clear error, not
   a second concurrent review) — this is the server-side guard from
   `contracts/web-api-contract-delta.md`, independent of which tab's UI
   happens to be disabled.

## Scenario 6 — Existing learning behavior and Ollama integration are unaffected

1. Re-run `specs/001-vocab-recall-tutor/quickstart.md`,
   `specs/002-sentence-review-indicator/quickstart.md`, and
   `specs/003-web-ui/quickstart.md` in full.
2. **Expected**: every outcome in all three is identical to before this
   feature — grading, the review pipeline, and the progress log are
   untouched (FR-011).

## Automated coverage

Scenario 3's reload-resilience and Scenario 5's server-side rejection
should each have a `pytest` test against the extended `GET /api/state`
shape and `PracticeSession.submit_sentence`'s guard, per
`contracts/web-api-contract-delta.md`. Scenarios 1, 2, and 4's visual
claims (grouping, color, spinner timing) are manual checks, matching how
`002`/`003` treated equivalent claims. Scenario 6 is simply "the existing
`001`/`002`/`003` test suites still pass unmodified."
