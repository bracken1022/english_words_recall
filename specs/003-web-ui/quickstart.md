# Quickstart: Web UI for Remote Access

Validation guide for proving the feature works end-to-end. Field/timing
details live in `contracts/`; this file only sequences the checks.
Prerequisites and vocabulary/progress-file setup are unchanged from
`specs/001-vocab-recall-tutor/quickstart.md` — this only adds checks around
the new web layer.

## Prerequisites

- Everything from `001-vocab-recall-tutor/quickstart.md` (Python
  environment, a vocabulary file, Ollama running for the LLM-dependent
  scenarios).
- The web dependency (`Flask`) installed.
- A second device (phone, tablet, or another computer) on the same local
  network as the host machine, for Scenario 3.

## Scenario 1 — Practice recall through the browser (User Story 1)

1. Start the web server on the host machine pointed at a vocabulary
   directory.
2. Open the shown address in a browser **on the host machine**.
3. **Expected**: the page shows only the Chinese meaning — the English
   expression is not present anywhere in the page source until an answer
   is submitted.
4. Submit the correct answer. **Expected**: marked correct, accepted
   expression(s) revealed.
5. Repeat with an incorrect answer, then a blank answer. **Expected**:
   marked incorrect in both cases, expression still revealed, no error
   page.
6. Use the "continue" control. **Expected**: the next item's Chinese
   meaning appears; there is no control anywhere on the page to skip an
   unanswered item or go back to the previous one.

## Scenario 2 — Sentence review with feedback in the browser (User Story 2)

1. Continuing from Scenario 1, after either a correct or an incorrect
   recall answer, confirm the page prompts for a sentence using the
   revealed target expression (per the resolved Clarification: this
   happens after every recall attempt, not only correct ones).
2. Submit a sentence with a grammar issue. **Expected**: the spinner
   appears the instant you submit, animates for the whole wait, and is
   gone the instant the result appears — the result shows the sentence
   marked as needing correction, a more natural version, and a short
   explanation.
3. Submit a sentence that's already correct and natural. **Expected**:
   spinner appears/clears the same way; result states it's already
   correct, with no invented changes.
4. Submit a sentence that doesn't use the target expression. **Expected**:
   the page tells you the target expression is missing.
5. Stop Ollama (or point `--ollama-url` at an unreachable address) and
   repeat. **Expected**: the page tells you review is unavailable — no
   hang, no crash — and the "continue" control still works.
6. Confirm the completed attempt (each of the cases above) was appended to
   the progress Markdown file in the existing format — identical whether
   produced via the browser or the CLI.

## Scenario 3 — Access from another device on the local network (User Story 3)

1. With the server still running on the host machine, find the host's
   local network address (as shown by the server on startup).
2. From a second device (phone, tablet, or another computer) on the same
   network, open that address in its browser.
3. **Expected**: the same page loads, and a full recall → sentence →
   feedback → continue cycle completes from that second device, behaving
   identically to Scenarios 1-2 on the host machine.
4. On a phone (or a narrowed desktop browser window at phone width),
   **expected**: every control is reachable and legible with no horizontal
   scrolling or overlapping elements, at every step of the cycle (per
   `contracts/responsive-layout-contract.md`).
5. From a device **not** on the same local network (e.g., mobile data with
   Wi-Fi off), attempt to reach the same address. **Expected**: it is not
   reachable — confirming no public-Internet exposure is introduced by
   default.

## Scenario 4 — Edge cases

1. Point the server at an empty vocabulary directory. **Expected**: the
   page shows a clear "no items available" state, no session starts, no
   error page.
2. Point the server at a vocabulary directory containing one malformed
   block alongside a valid one. **Expected**: a warning identifying the
   problem is visible on the page, and the valid item is still
   practiceable.

## Scenario 5 — Existing CLI is unaffected

1. Run `specs/001-vocab-recall-tutor/quickstart.md` and
   `specs/002-sentence-review-indicator/quickstart.md` in full, using the
   command-line tool exactly as before (not the web server).
2. **Expected**: every outcome in both is identical to before this
   feature — the web UI is an additional way to reach the tutor, not a
   change to the existing one.

## Automated coverage

Scenario 1's step sequencing, Scenario 2's four outcomes (needs-correction /
already-correct / missing-expression / unavailable), and Scenario 4's edge
cases should each have a `pytest` test against `src/web/app.py` via
`app.test_client()`, per `contracts/web-api-contract.md`. Scenario 3's
network-reachability and Scenario 2's spinner-visibility/Scenario 3's
responsive-layout claims are manual checks (see `research.md` "Testing the
web layer without a real browser" for why). Scenario 5 is simply "the
existing `001`/`002` test suites still pass unmodified."
