# Research: Require Confirmation Before Advancing Past a Wrong Recall-Only Answer

No open `NEEDS CLARIFICATION` markers — `/speckit-clarify` found no
critical ambiguities (the one candidate fork, the CLI's continue
mechanism, already had a low-risk default in spec.md's Assumptions).
This file records the remaining implementation-shape decisions.

## 1. A new `"reveal"` step, not a repurposed existing one

**Decision**: Add a new `Step` value, `"reveal"`, entered only from
`submit_answer()` when `self.recall_only` is `True` and the answer is
incorrect. It is distinct from `"sentence"` (which prompts for a
sentence — not applicable here) and `"feedback"` (which carries
sentence-correction data — `sentence`/`feedback` dict fields — not
applicable here either).

**Rationale**: Neither existing step's shape fits: `"sentence"` implies
a sentence-writing prompt should appear (violates spec.md FR-002,
carried over unchanged from spec `012`); `"feedback"` implies
`state()`'s `sentence`/`feedback` fields are populated, which would be
meaningless for a recall-only attempt that has no sentence. A new,
narrow step keeps each step's `state()` shape meaning exactly what it
already means elsewhere, rather than overloading one with a conditional
sub-shape.

**Alternatives considered**:
- **Reuse `"feedback"`** — rejected: would require every consumer of
  `state()`'s `"feedback"` step (today, always sentence-correction data)
  to also handle a "no sentence/feedback fields present" case, adding
  conditional complexity to a shape that's supposed to be exactly what
  `submit_sentence()` returns.

## 2. Reuse `continue_to_next()` / `POST /api/continue` — no new endpoint

**Decision**: `continue_to_next()` gains one new branch: when
`self.step == "reveal"`, `append_attempt()` the held `pending_attempt`
(exactly the shape `skip_sentence()` already writes — no `sentence`/
`feedback` fields) and then call the existing `_advance_after_attempt()`
helper (introduced in spec `012`, already shared by `skip_sentence()`
and the existing `"feedback"` branch). The web route `POST /api/continue`
needs no changes at all — it already just calls `continue_to_next()` and
returns `session.state()`.

**Rationale**: `POST /api/continue` already means exactly "the learner
has finished looking at whatever's being shown; advance now" — that's
precisely what's needed here too. A dedicated new endpoint (e.g.
`POST /api/continue-recall`) would duplicate that meaning for no
benefit, and would need its own contract test tier, its own
`WrongStepError` guard, etc., for behavior `continue_to_next()` already
has the shape for.

**Alternatives considered**:
- **A new endpoint specific to the "reveal" step** — rejected: no
  behavioral difference from `POST /api/continue` that would justify a
  second endpoint; adds surface area without adding capability.
- **Auto-append at `submit_answer()` time, only deferring the *step
  advance*** — rejected: FR-006 depends on the progress log recording
  attempts as they're actually confirmed, not the instant they're
  graded; deferring the whole finalize-and-record step together (as
  `skip_sentence()` already does for its own case) keeps "when is this
  attempt considered done" a single, consistent moment, and avoids a
  half-written attempt existing in the log before the learner has even
  seen the correct answer.

## 3. `state()`: extend the existing three-step tuple, not a parallel branch

**Decision**: The existing line
`if self.step in ("sentence", "feedback"): base["accepted_expressions"] = ...`
becomes `if self.step in ("sentence", "feedback", "reveal"): ...`. No
other change to `state()` — the `"reveal"` step never touches the
`if self.step == "feedback":` block below it (which sets `sentence`/
`feedback`), so those fields correctly stay absent for a `"reveal"`
state, exactly matching what FR-003 needs exposed (the correct
expression) and nothing more.

**Rationale**: Minimal, obviously-correct diff — one tuple gains one
value; every other line of `state()` is unchanged.

## 4. Web UI: the Continue button becomes a persistent element, reused as-is

**Decision**: `<button id="continue-button">` moves out of
`#feedback-view` to a persistent element at the top level of the page
(the same pattern already used for `#word-feedback` since spec `004`) —
visible whenever `state.step` is `"feedback"` or `"reveal"`, hidden
otherwise. Its existing click handler (`POST /api/continue`, then
render the result) needs **no changes** — it already does exactly the
right thing for both steps.

**Rationale**: `showOnly(state.step)` already hides every named
`<section>` for any step that isn't one of its keys — since `"reveal"`
isn't (and won't become) a section key, every section correctly
disappears for that step, leaving only the persistent `#word-feedback`
stamp and (with this change) the persistent Continue button on screen —
precisely the intended "just the reveal and a way to move on" view. No
new `<section>` is needed at all — just relocating one existing button
to be a persistent element alongside `#word-feedback`.

**Alternatives considered**:
- **A dedicated `#reveal-view` section with its own duplicate Continue
  button** — rejected: doubles a button that already exists and already
  does the right thing; two buttons wired to the same endpoint for two
  different steps is duplication with no behavioral difference.

## 5. `app.js`: extend the existing three-way branch in the answer handler

**Decision**: The answer-submit handler (already restructured once, in
the bugfix following spec `012`, to check the state that follows
`POST /api/answer`) gains a third branch:
- `state.step === "sentence" || state.step === "feedback"` → sentence
  mode, unchanged.
- `state.step === "reveal"` → recall-only, incorrect: `renderState(state)`
  and stop — no timer, no auto-advance (the persistent Continue button,
  decision #4, is now visible and awaits a click).
- otherwise (`"recall"`/`"complete"`) → recall-only, correct: the
  existing brief timed reveal-then-advance, completely unchanged
  (spec.md FR-001, Assumptions).

**Rationale**: This is the natural extension of the branch the bugfix
already introduced — one more `if` arm, no restructuring of the two
existing ones.

## 6. CLI: a small, directly-called pause, gating the existing `append_attempt()` call

**Decision**: A new private helper,
`_wait_for_continue(prompt: str = "Press Enter to continue...") -> None`
(a thin wrapper around `input()`, mirroring the existing
`_default_answer_input()`'s directness — no dependency-injection
parameter needed, since tests already monkeypatch `builtins.input`
globally for this module). `run_session()`'s loop calls it — only when
`mode == "recall-only"` and `not recall_attempt.correct` — immediately
before the (already-existing) `append_attempt()` call for that item.

**Rationale**: The CLI's loop already calls `append_attempt()` once per
item, right after grading (for recall-only) or after the sentence step
(for sentence mode). Gating that one call behind a pause, only in the
one case that needs it, is a two-line change with no restructuring —
consistent with how minimal the equivalent web-side change is (decision
#2 reuses an existing endpoint; this reuses an existing call site).

**Alternatives considered**:
- **A `continue_input` callable parameter threaded through
  `run_session()`, matching `answer_input`/`sentence_input`'s
  dependency-injection style** — rejected as unnecessary: those
  parameters exist because their *default* (`input()`) needed to be
  overridable independently per call in some tests; here, the existing
  `monkeypatch.setattr("builtins.input", ...)` pattern (already used by
  every CLI integration test in this project) already intercepts a bare
  `input()` call just as well, one fewer parameter for the same
  testability.

## 7. Test strategy

**Decision**: Same tiers as `006`–`012`:
- `tests/unit/test_session_state.py` — `submit_answer()`'s new branch
  (incorrect + recall-only → step `"reveal"`, `pending_attempt` held,
  nothing appended yet); `continue_to_next()`'s new branch (from
  `"reveal"`: appends, tallies, advances); a regression test proving the
  correct-answer path (already tested in spec `012`) is byte-for-byte
  unchanged.
- `tests/integration/test_session_mode.py` — a CLI-level test confirming
  a wrong recall-only answer blocks on `input()` (via the existing
  `monkeypatch.setattr("builtins.input", ...)` pattern with one extra
  scripted value) before the next word's Chinese meaning is printed.
- `tests/contract/test_web_api_contract.py` — `POST /api/continue` now
  valid (`200`) from `"reveal"`, still `409` from `"recall"`/`"choose"`/
  etc.; a full flow (`select` recall-only → wrong `answer` → confirm
  step is `"reveal"` and progress log is still empty for that word →
  `continue` → confirm it's now recorded and advanced).
- `tests/unit/test_web_static_assets.py` — static assertions for the
  new `app.js` branch and the moved Continue button markup (now outside
  `#feedback-view`'s bounds, alongside `#word-feedback`).

**Alternatives considered**: None beyond what `012`'s research.md §7
already established for this project's test-tier conventions.
