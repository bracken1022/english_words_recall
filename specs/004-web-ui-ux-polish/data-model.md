# Data Model: Web UI State & Feedback Polish

No new entities. This feature extends one existing runtime-only shape from
`specs/003-web-ui/data-model.md`.

## `PracticeSession` (extended)

All fields are as already defined in `003-web-ui`'s data-model.md, plus one
new field:

| Field | Type | Notes |
|---|---|---|
| `_review_in_progress` | `bool` | **NEW.** `True` for the duration of a `submit_sentence` call (set before invoking `correction_fn`, cleared in a `finally`). A `submit_sentence` call made while this is already `True` raises `WrongStepError` — the server-side half of FR-008's duplicate-submission guard (research.md). Not exposed via `GET /api/state`; it's an internal guard, not learner-facing data. |

No other field changes — `pending_attempt`'s existing `answer`/`correct`
keys (already set by `submit_answer`, per `003`'s data-model.md) are
unchanged; this feature only changes whether `state()` *exposes* them.

## `state()`'s response shape (extended)

`PracticeSession.state()` (`GET /api/state`'s payload) gains two fields for
the `"sentence"` and `"feedback"` steps — both already computed, just not
previously returned:

| `step` | New fields | Source |
|---|---|---|
| `"sentence"` | `answer` (string), `correct` (bool) | `pending_attempt["answer"]`, `pending_attempt["correct"]` — set during the preceding `submit_answer` call |
| `"feedback"` | `answer` (string), `correct` (bool) | same as above; `pending_attempt` isn't cleared until `continue_to_next()` |

`"empty"`, `"recall"`, and `"complete"` are unchanged — there is no recall
outcome to show before one exists, or once the session has moved past
needing it displayed for the *current* item.

## Validation rules

- Both new fields are present together or absent together (same rule
  `PracticeAttempt` itself already follows for `sentence`/`feedback` in
  `001`'s data-model.md) — they exist exactly when `step` is `"sentence"`
  or `"feedback"`, and never otherwise.
- `_review_in_progress` MUST be cleared (set back to `False`) even if
  `correction_fn` raises — the guard must not permanently lock the session
  into rejecting all future sentence submissions after one failure.

## Relationships

Unchanged from `003-web-ui`: `PracticeSession` still has no relationship to
any persisted entity beyond calling the existing, unmodified
`progress_log.append_attempt`. `_review_in_progress` is pure in-memory
guard state, never written anywhere.
