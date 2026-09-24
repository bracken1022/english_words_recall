# Data Model: Choose Sequential or Random Word Order

No new persistent entities, no storage changes (spec.md Assumptions: not
remembered across sessions — there is no settings file or database in
this project). This feature adds one new parameter, threaded through
existing entry points, and one in-place transformation of an existing
list.

## `order` parameter (new — not a stored field, a call-time argument)

| Value | Meaning |
|---|---|
| `"sequential"` (default) | No change to `self.items`'s order — today's exact behavior |
| `"random"` | `random.shuffle(self.items)` called exactly once, at the same point the pool is otherwise finalized |

Any other value behaves the same as `"sequential"` (defensive default,
not reachable through either real UI — research.md §2).

## `PracticeSession` (existing — `src/web/session_state.py`) — changed call sites, no new fields

| Method | Change |
|---|---|
| `__init__(..., order: str = "sequential")` | In the existing `group_locked` branch, after the existing group filter, shuffle `self.items` in place if `order == "random"` |
| `select_collection(key, order: str = "sequential")` | After the existing key-based filter, shuffle `self.items` in place if `order == "random"`, before `current_index`/counters are reset |

No new attribute is stored on `PracticeSession` — `order` is consumed at
the moment the pool is finalized and then discarded, exactly like `group`
already is today.

## `run_session` (existing — `src/cli/session.py`) — changed call site, no new state

| Function | Change |
|---|---|
| `run_session(..., order: str = "sequential")` | After the existing group filter, shuffle `items` in place if `order == "random"`, before the practice loop begins |

## Web request contract — `POST /api/select`

| Field | Type | Required | Notes |
|---|---|---|---|
| `collection` | `string \| null` | Yes (unchanged from spec `007`) | `400` if the key is missing from the request body at all |
| `order` | `"sequential" \| "random"` | **No** (new) | Missing, or any value other than the two valid strings, is treated as `"sequential"` — see `research.md` §5 |

## CLI flags — new on both entry points

| Flag | Values | Default | Applies to |
|---|---|---|---|
| `--order` (`src/cli/__main__.py`) | `sequential`, `random` | `sequential` | Always takes effect directly (no interactive picker exists in the CLI) |
| `--order` (`src/web/__main__.py`) | `sequential`, `random` | `sequential` | Only takes effect when `--group` is also given (`group_locked` mode) — otherwise the interactive choose screen governs order fresh (research.md §3) |

## Everything else — UNCHANGED

`VocabularyItem`, `PracticeAttempt`, the progress-log format,
`submit_answer`/`submit_sentence`/`skip_sentence`/`continue_to_next`/
`restart`, and every existing `GET /api/state` field are all untouched —
this feature only changes what order `self.items` is already walked
through in, once, before the walk starts.
