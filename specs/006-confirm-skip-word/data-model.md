# Data Model: Confirm Before Skipping a Word Without a Sentence

No new entities. This feature reaches a state that the existing data
model already allows but never previously produced.

## `PracticeAttempt` (existing — `src/models/practice_attempt.py`)

| Field | Type | Notes |
|---|---|---|
| `timestamp` | `str` | unchanged |
| `item` | `str` | unchanged — the English expression |
| `answer` | `str` | unchanged — the learner's recall answer (may be empty string, not `None`) |
| `correct` | `bool` | unchanged — recall-step correctness; **unaffected by skip** |
| `sentence` | `str \| None` | for a skipped word: `None` (previously always a string in practice, even if `""`) |
| `feedback` | `str \| None` | for a skipped word: `None` (must match `sentence`'s presence/absence — existing invariant, unchanged) |

No field additions. The existing `__post_init__` invariant — `sentence`
and `feedback` must be both present or both absent — already models
"skipped" vs. "attempted" correctly; this feature is the first caller to
actually construct the both-absent case from a real (non-test) code path.

## `PracticeSession` (existing — `src/web/session_state.py`)

No new fields. `self.correct_count` (added for the end-of-session tally)
is updated by the new transition exactly the way it already is by
`continue_to_next()`.

### State machine — new transition

```text
                 submit_answer()          submit_sentence()         continue_to_next()
     recall  ─────────────────────▶ sentence ─────────────────▶ feedback ─────────────────▶ recall | complete
                                        │
                                        │ skip_sentence()   (NEW)
                                        └───────────────────────────────────────────────────▶ recall | complete
```

`skip_sentence()` is a new, direct edge from `"sentence"` to
`"recall"`/`"complete"` that never visits `"feedback"` — mirroring
`continue_to_next()`'s index-advancement and completion logic, but
finalizing the current item's `PracticeAttempt` with no sentence/feedback
instead of reading `self.last_correction`.

| Method | Valid from | Goes to | Side effects |
|---|---|---|---|
| `skip_sentence()` | `"sentence"` | `"recall"` (more items) or `"complete"` (last item) | Appends a `PracticeAttempt` with `sentence=None`/`feedback=None`; updates `correct_count` from the already-known recall outcome; advances `current_index`; clears `pending_attempt` |

Invalid-step calls raise `WrongStepError`, matching every existing
transition method's convention (`submit_answer`, `submit_sentence`,
`continue_to_next`).

## Progress log (existing format — unchanged)

A skipped attempt's YAML block simply omits the `sentence:` and
`feedback:` keys, e.g.:

```yaml
---
timestamp: '2026-09-19T10:02:11+00:00'
item: tailor
answer: talor
correct: false
---
```

...compared to a completed one, which still includes them:

```yaml
---
timestamp: '2026-09-19T10:04:47+00:00'
item: tale
answer: tale
correct: true
sentence: This is a fairy tale.
feedback: already correct
---
```

`progress_log.append_attempt` and `read_attempts`/`PracticeAttempt.from_block`
require no changes — this shape round-trips correctly today.
