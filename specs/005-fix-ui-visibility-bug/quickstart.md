# Quickstart: Fix Web UI State Visibility

Validation guide for proving the fix works end-to-end **in a real
browser** — this feature exists specifically because DOM-level automated
tests could not catch the original bug (research.md), so manual
verification here is not optional the way it might be for other features.

## Prerequisites

- Everything from `specs/003-web-ui/quickstart.md` (server running, a
  vocabulary file, Ollama running for the review-dependent scenarios).

## Scenario 1 — Empty/complete messages only show when genuinely applicable

1. Point the server at a **non-empty** vocabulary directory and open the
   page. **Expected**: "No vocabulary items are available for this
   session." is not visible anywhere on the page.
2. Complete every item in a small vocabulary set through to the end.
   **Expected**: only after the last item's review concludes and you
   continue does "Session complete — you've gone through every item."
   appear — not before.
3. Point the server at an **empty** vocabulary directory and open the
   page. **Expected**: "No vocabulary items are available for this
   session." is shown (this case still exists and still works).

## Scenario 2 — Recall and sentence steps are never shown together

1. Load a vocabulary item. **Expected**: only the vocabulary question and
   its answer input are visible — no sentence-writing prompt or input
   anywhere on the page.
2. Submit the answer. **Expected**: the vocabulary-answer input is no
   longer visible/active; the sentence-writing prompt and input appear
   (alongside the word feedback, per `004`) — the two input steps are
   never both on screen.

## Scenario 3 — The review-loading message only shows during an actual review

1. Before submitting a sentence, confirm "Reviewing your sentence..." and
   the spinner are **not** visible anywhere on the page (not just
   logically "hidden" — actually not rendered).
2. Submit a sentence. **Expected**: the spinner and "Reviewing your
   sentence..." appear immediately.
3. Once the review completes (or fails, e.g. with Ollama stopped),
   **Expected**: both disappear immediately, replaced by the result or
   failure message.

## Scenario 4 — Prior work is not regressed

1. Re-run `specs/003-web-ui/quickstart.md` and
   `specs/004-web-ui-ux-polish/quickstart.md` in full, in a real browser.
2. **Expected**: every outcome in both — word-feedback color/text, the
   input/button grouping, the duplicate-submission guard, the responsive
   layout at phone/tablet/desktop widths, and the LAN-access scenarios —
   is unaffected by this fix.

## Automated coverage

A regression-guard test in `tests/unit/test_web_static_assets.py` asserts
the `[hidden]` override rule exists in `style.css` (research.md). It
cannot itself prove correct rendering — Scenarios 1-3 above are the only
way this feature's actual visual claims get verified, and must be run in
a real browser, not assumed from the test suite being green.
