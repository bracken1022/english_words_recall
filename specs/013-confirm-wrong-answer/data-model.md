# Data Model: Require Confirmation Before Advancing Past a Wrong Recall-Only Answer

No new persistent entities, no storage changes. This feature adds one
new state-machine `Step` value and two changed method branches, reusing
`PracticeAttempt`'s existing shape and `_advance_after_attempt()`'s
existing tail (both introduced in spec `012`).

## `Step` — one new value

| Value | Meaning |
|---|---|
| `"reveal"` (**new**) | Recall-only mode only. Entered from `submit_answer()` when the answer was incorrect. The attempt is held (`self.pending_attempt`), not yet written to the progress log. Exits only via `continue_to_next()`. |

Full set: `"empty" \| "choose" \| "recall" \| "sentence" \| "feedback" \| "reveal" \| "complete"`.

## `PracticeSession` (existing — `src/web/session_state.py`) — changed method branches, no new fields

| Method | Change |
|---|---|
| `submit_answer(answer)` | When `self.recall_only`: **correct** → unchanged from spec `012` (`append_attempt()` immediately, `_advance_after_attempt()`). **Incorrect** (new) → stash `pending_attempt` (same shape `skip_sentence()`/`012`'s recall-only branch already build: `timestamp`, `item`, `answer`, `correct`), set `self.step = "reveal"`. Non-recall-only: unchanged (always `"sentence"`). |
| `continue_to_next()` | Gains a `self.step == "reveal"` branch: `append_attempt()` the held `pending_attempt`, then `_advance_after_attempt(self.pending_attempt["correct"])` — the same tail already used for the existing `"feedback"` branch and for `skip_sentence()`. The existing `"feedback"` branch and the `"complete"` no-op are unchanged. Any other originating step still raises `WrongStepError`. |
| `state()` | The existing `if self.step in ("sentence", "feedback"): ...` condition (which sets `accepted_expressions`/`answer`/`correct`) is extended to `("sentence", "feedback", "reveal")`. The `if self.step == "feedback": ...` block below it (which sets `sentence`/`feedback`) is untouched — those fields correctly stay absent for `"reveal"`. |

No new attribute is stored on `PracticeSession` — `"reveal"` is just
another value `self.step` can take, and the held attempt uses the
existing `self.pending_attempt` dict, exactly as `"sentence"`/
`"feedback"` already do.

## `run_session` (existing — `src/cli/session.py`) — one new gated call, no new state

| Function | Change |
|---|---|
| `run_session(...)` | Per item, when `mode == "recall-only"` and `not recall_attempt.correct`: calls a new `_wait_for_continue()` helper (blocks on `input()`) immediately before the existing `append_attempt()` call for that item. When correct, or when `mode == "sentence"`, behavior is unchanged. |

## Web response contract — `POST /api/continue`

| Aspect | Before (spec `007`) | After this feature |
|---|---|---|
| Valid originating steps | `"feedback"` (also a no-op from `"complete"`) | `"feedback"` **or** `"reveal"` (also a no-op from `"complete"`) |
| Invalid originating steps | Everything else → `409` | Unchanged, everything else (including `"recall"`, `"sentence"`, `"choose"`) still → `409` |
| Response body | `session.state()` | Unchanged shape |

## Everything else — UNCHANGED

`VocabularyItem`, `PracticeAttempt`'s field set, the progress-log file
format, `submit_sentence()`, `skip_sentence()`, `restart()`,
`select_collection()`, and every other existing `GET /api/state` field
for every other step are all untouched — this feature only changes what
happens between a recall-only incorrect answer and the next word.
