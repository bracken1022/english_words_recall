# Data Model: Choose Recall-Only or Sentence Practice Mode

No new persistent entities, no storage changes (spec.md Assumptions: not
remembered across sessions — there is no settings file or database in
this project). This feature adds one new parameter, threaded through
existing entry points, and one new piece of session state consumed on
every recall step.

## `mode` parameter (new — a call-time argument, resolved into stored state)

| Value | Meaning |
|---|---|
| `"sentence"` (default) | Today's exact behavior — every word goes recall → sentence → feedback |
| `"recall-only"` | Every word goes recall → next word (or complete) directly; no sentence step is ever shown |

Any other value behaves the same as `"sentence"` (defensive default, not
reachable through either real UI — research.md §3, mirroring `order`'s
own rule).

## `PracticeSession` (existing — `src/web/session_state.py`) — one new stored attribute, changed call sites

| Member | Change |
|---|---|
| `self.recall_only: bool` (**new**) | Resolved from `mode == "recall-only"` at the point the mode is decided; unlike `order`, this is read again on every `submit_answer()` call for the rest of the session, not just once |
| `__init__(..., mode: str = "sentence")` | In the existing `group_locked` (`else`) branch, sets `self.recall_only = mode == "recall-only"`. In the interactive branch, sets `self.recall_only = False` as a placeholder — `select_collection()`'s own `mode` argument is what actually governs an interactive session |
| `select_collection(key, order: str = "sequential", mode: str = "sentence")` | Sets `self.recall_only = mode == "recall-only"`, alongside its existing `order`-driven shuffle |
| `submit_answer(answer)` | After grading (unchanged): if `self.recall_only`, immediately finalize the attempt (record → tally `correct_count` if correct → advance `current_index` → land on `"recall"`/`"complete"`) exactly as `skip_sentence()`/`continue_to_next()` already do; otherwise (default), unchanged — stash `pending_attempt`, move to `"sentence"` |

No new `Step` value is introduced — a recall-only session only ever
visits `"recall"` and `"complete"` (plus `"choose"`/`"empty"` at the
start, same as any session); `"sentence"` and `"feedback"` are simply
never entered.

## `run_session` (existing — `src/cli/session.py`) — changed call site, no new state

| Function | Change |
|---|---|
| `run_session(..., mode: str = "sentence")` | Per item: if `mode == "recall-only"`, build the `PracticeAttempt` directly from `run_recall_step()`'s result (no `sentence`/`feedback` fields) and skip calling `run_sentence_step()` entirely; otherwise (default), unchanged |

## Web request contract — `POST /api/select`

| Field | Type | Required | Notes |
|---|---|---|---|
| `collection` | `string \| null` | Yes (unchanged from spec `007`) | `400` if the key is missing from the request body at all |
| `order` | `"sequential" \| "random"` | No (spec `011`) | Missing/invalid → `"sequential"` |
| `mode` | `"sentence" \| "recall-only"` | **No** (new) | Missing, or any value other than the two valid strings, is treated as `"sentence"` — see research.md §6 |

## CLI flags — new on both entry points

| Flag | Values | Default | Applies to |
|---|---|---|---|
| `--mode` (`src/cli/__main__.py`) | `sentence`, `recall-only` | `sentence` | Always takes effect directly (no interactive picker exists in the CLI) |
| `--mode` (`src/web/__main__.py`) | `sentence`, `recall-only` | `sentence` | Only takes effect when `--group` is also given (`group_locked` mode) — otherwise the interactive choose screen governs mode fresh (research.md §4, mirroring `--order`) |

## `PracticeAttempt` (existing — unchanged shape, new usage pattern)

A recall-only attempt uses exactly the subset of fields `skip_sentence()`
already produces today: `timestamp`, `item`, `answer`, `correct` —
`sentence` and `feedback` stay absent (already optional on the model).
No schema change.

## Everything else — UNCHANGED

`VocabularyItem`, the progress-log file format, `state()`'s existing
field set for every step, `skip_sentence()`/`continue_to_next()`/
`restart()` themselves, and every existing `GET /api/state` field are all
untouched — this feature only changes *which path* `submit_answer()`
takes, once the mode is decided.
