# Quickstart: Sentence-Review Loading Indicator

Validation guide for proving the feature works end-to-end. Timing/behavior
details live in `contracts/loading-indicator-contract.md`; this file only
sequences the checks. Prerequisites and general app setup are unchanged from
`specs/001-vocab-recall-tutor/quickstart.md` — this only adds checks around
the existing sentence-correction step.

## Prerequisites

- Everything from `specs/001-vocab-recall-tutor/quickstart.md` (Python
  environment, a vocabulary file, Ollama running for the "real" scenarios
  below — though Scenario 2 below deliberately does not need it).

## Scenario 1 — Spinner shows during a slow review (interactive terminal)

1. Run the app in a real terminal (not redirected) against a vocabulary item,
   answering the recall step normally.
2. When prompted for a sentence, submit one. If your local model responds in
   under a second, temporarily point `--ollama-url` at a deliberately slow or
   unreachable stand-in (or use a large/slow model) so the wait is long
   enough to observe.
3. **Expected**: the instant you submit the sentence, an animating spinner
   appears — before any feedback text — and keeps animating for the entire
   wait. No percentage or step count ever appears in it.
4. **Expected**: the moment the review finishes, the spinner is gone and the
   correction feedback (or "unavailable" message) appears in its place, with
   no visible overlap or leftover spinner text.

## Scenario 2 — Indicator clears correctly on every outcome

Run each of these (Ollama running for the first two, stopped for the third —
mirrors `001-vocab-recall-tutor/quickstart.md` Scenarios 2 and 3):

1. A sentence with a grammar issue → spinner, then corrected sentence +
   explanation. Spinner is gone by the time either appears.
2. A sentence that's already correct → spinner, then "already correct."
   Spinner is gone by the time it appears.
3. Ollama stopped/unreachable → spinner, then "correction unavailable."
   Spinner is gone by the time it appears — this must look identical to how
   `001-vocab-recall-tutor` already behaves, aside from the spinner having
   been shown during the wait.

**Expected** in all three: no case shows a fabricated percentage, and no case
leaves the spinner on screen alongside or after the result.

## Scenario 3 — Non-interactive output falls back safely

1. Run the app with stdout redirected to a file (or otherwise made
   non-interactive), and complete a sentence-review step.
2. **Expected**: no ANSI spinner artifacts appear in the file; instead, a
   single plain line (e.g., "Reviewing your sentence...") appears before the
   result, and the app does not crash or hang.
3. Inspect the file afterward: the output should be clean, readable text —
   no corrupted control sequences — matching FR-007.

## Scenario 4 — Learning behavior is provably unchanged

1. Re-run `specs/001-vocab-recall-tutor/quickstart.md` Scenarios 1-6 in full.
2. **Expected**: every outcome (grading, progression, progress-log content,
   determinism regardless of LLM output) is identical to before this
   feature — the only observable difference anywhere in the app is the
   presence of the spinner/fallback line during the wait itself.

## Automated coverage

Each scenario above should have a corresponding `pytest` test: Scenario 1's
timing contract and Scenario 3's fallback in
`tests/unit/test_loading_indicator.py` and
`tests/contract/test_loading_indicator_contract.py`; Scenario 2 as additions
to the existing `tests/integration/test_sentence_correction_flow.py` cases;
Scenario 4 is simply "the existing `001-vocab-recall-tutor` test suite still
passes unmodified." See `plan.md` Project Structure and `research.md`
"Testing approach for 'the spinner animated.'"
