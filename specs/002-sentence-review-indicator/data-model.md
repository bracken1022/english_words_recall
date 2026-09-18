# Data Model: Sentence-Review Loading Indicator

No new entities. This feature introduces no persisted data and does not
modify the entities already defined in
`specs/001-vocab-recall-tutor/data-model.md` (`VocabularyItem`,
`PracticeAttempt`, `LearnerProgressLog`) — the indicator is transient UI
state, scoped to the lifetime of a single `request_correction(...)` call,
and is never read from or written to the progress log (per spec FR-006 and
Assumptions).

## Runtime-only concept: indicator state

Not persisted, not a data entity — exists only as the lifetime of a Python
context manager:

| Attribute | Notes |
|---|---|
| `is_terminal` | Read once from the console at the start of the wrapped call; decides which of the two display modes (animated spinner vs. one plain line) is used. Not stored anywhere. |
| `active` | Implicit in whether the `with`/`try` block wrapping `request_correction(...)` has been entered/exited yet. Never observable outside `run_with_indicator`'s own call stack. |

## Relationships

```text
run_sentence_step (src/cli/session.py)
  --wraps call to--> request_correction (src/services/llm_client.py, unchanged)
  --via--> run_with_indicator (src/cli/loading_indicator.py, NEW)
```

`run_with_indicator` has no relationship to `VocabularyItem`, `PracticeAttempt`,
or the progress log — it receives and returns only whatever
`request_correction` already returns (a `CorrectionResult`), unmodified.
