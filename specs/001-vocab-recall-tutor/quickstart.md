# Quickstart: Vocabulary Recall Tutor

Validation guide for proving the feature works end-to-end. Field/format
details live in `contracts/`; this file only sequences the checks.

## Prerequisites

- Python 3.11+ installed.
- Project dependencies installed (`requests`, `PyYAML`, `rich`,
  `pytest` — see `plan.md` Technical Context).
- [Ollama](https://ollama.com) installed and running locally, reachable at
  `http://localhost:11434` (the app talks to this HTTP API directly — it
  never shells out to the `ollama` CLI), with the default model pulled:

  ```bash
  ollama pull qwen3:14b
  ```

  A different model may be used instead via the app's `--model` flag (see
  `contracts/ollama-correction-contract.md`). Ollama is not required for the
  recall-only checks below.
- A vocabulary directory containing at least one valid Markdown file per
  `contracts/vocabulary-markdown-format.md`.

## Scenario 1 — Recall drill only (User Story 1, no LLM needed)

1. Create a vocabulary file with one item, e.g. `english: receive`,
   `chinese: 收到`.
2. Run the app and start a session against that vocabulary directory.
3. Confirm only the Chinese meaning (`收到`) is shown — the English expression
   must not appear yet.
4. Submit the correct answer (`receive`). **Expected**: marked correct, the
   accepted expression is revealed.
5. Restart the drill on the same item and submit an incorrect answer.
   **Expected**: marked incorrect, the correct expression is revealed.
6. Restart again and submit an empty answer. **Expected**: marked incorrect,
   no crash/error.

## Scenario 2 — Sentence correction with the local LLM (User Story 2)

1. With Ollama running, repeat the recall step from Scenario 1 for the
   `receive` item.
2. When prompted, submit a sentence that uses the expression but has a clear
   grammar issue, e.g. `I recieve a gift yesterday.`
   **Expected**: feedback indicates correction is needed, shows a corrected
   sentence, and gives a short explanation.
3. Submit a sentence that is already correct and natural, e.g.
   `I received a wonderful gift from my friend.`
   **Expected**: feedback states the sentence is already correct — no
   invented changes.
4. Submit a sentence that does not use the target expression at all, e.g.
   `I am happy today.`
   **Expected**: the app tells you the target expression is missing.

## Scenario 3 — Local LLM unavailable (User Story 2 edge case)

1. Stop the Ollama server (or point the app at a port nothing is listening
   on).
2. Repeat the recall step for any item and submit any sentence.
   **Expected**: the app tells you correction is unavailable — no hang, no
   crash — and lets you continue to the next item.
3. Confirm the recall step itself (Scenario 1) still works fully with the LLM
   stopped.

## Scenario 3b — Malformed structured output from Ollama

1. With Ollama running, point the app at a model (or a stub/proxy standing
   in for one) that returns a reply not matching the expected schema — e.g.,
   plain text instead of JSON, or JSON missing a required key.
2. Submit any sentence. **Expected**: identical to Scenario 3 — the app
   tells you correction is unavailable, with no partial/guessed output shown
   and no crash (see `contracts/ollama-correction-contract.md` Handling
   rules). This is exercised automatically by
   `tests/contract/test_ollama_correction_contract.py`.

## Scenario 4 — Author vocabulary as Markdown (User Story 3)

1. While the app is not running, add a second item to your vocabulary
   Markdown file (or a new file in the same directory) following
   `contracts/vocabulary-markdown-format.md`.
2. Start the app again. **Expected**: the new item is available for
   practice without any rebuild/migration step.
3. Edit one block into an invalid state (e.g., remove `english:`), keeping a
   second, valid block in the same file. Start the app again.
   **Expected**: a warning is shown identifying the bad block, and the
   valid block still loads and is practiceable.
4. After completing at least one full attempt (recall + sentence step, from
   Scenario 1/2), open `progress.md` in a plain text editor.
   **Expected**: you can identify, for that attempt, which item it was, what
   you answered, whether it was correct, your sentence, and the correction
   feedback — entirely from reading the file (see
   `contracts/progress-log-format.md`).

## Scenario 5 — Session scope and navigation (Clarifications)

1. Add a `group` value to some vocabulary items and leave it off others.
2. Start a session filtered to one `group`. **Expected**: only items with
   that `group` are presented.
3. Start a session with no filter. **Expected**: all items (grouped and
   ungrouped) are presented.
4. During any session, attempt to skip an item without answering, or return
   to a previous item. **Expected**: neither is possible — the app only
   accepts an answer (blank or not) and moves forward.

## Scenario 6 — Learning state machine is deterministic and LLM-independent

1. Run a full session (Scenario 1's recall step) with Ollama stopped.
   **Expected**: grading and item-to-item progression behave identically to
   a run with Ollama up — because neither depends on any LLM response (see
   `research.md` "Determinism of the learning state machine" and the
   Boundary rule in `contracts/ollama-correction-contract.md`).
2. Run the same vocabulary set twice with the same answers, once with
   Ollama returning a "needs correction" verdict and once with it returning
   "already correct" (or unavailable) for the same sentence. **Expected**:
   which item comes next, whether the session ends, and how recall was
   graded are unaffected in both runs — only the displayed/logged feedback
   text differs.

## Automated coverage

Each scenario above should have a corresponding `pytest` integration test
under `tests/integration/`; the request/response and file-format assumptions
each scenario depends on should each have a `tests/contract/` test asserting
the contract itself (independent of any specific scenario). See `plan.md`
Project Structure and `research.md` Testing strategy.
