# Data Model: Split Sentence Review into Judge and Teacher Roles

No new persistent entities, no storage changes. This feature restructures
one internal call into two; the only "entity" involved is the existing,
unchanged `CorrectionResult`, plus one new internal-only shape used
between the two new helper functions.

## `CorrectionResult` (existing — `src/services/llm_client.py`) — UNCHANGED

| Field | Type | Notes |
|---|---|---|
| `available` | `bool` | unchanged meaning |
| `uses_expression` | `bool \| None` | unchanged meaning; now sourced from the Judge call instead of the single combined call |
| `needs_correction` | `bool \| None` | unchanged meaning; now derived as `not (grammatically_correct and natural)` from the Judge's verdict (data-model.md below), not asked for directly |
| `corrected` | `str \| None` | unchanged meaning; now sourced from the Teacher call (only present when `needs_correction` is `True`) |
| `explanation` | `str \| None` | unchanged meaning; same source as `corrected` |

No field is added, removed, or renamed — per spec.md FR-003.

## `_JudgeVerdict` (new, internal-only — not exported, not part of any public contract)

Exists only inside `llm_client.py`, between `_request_judge()` and
`request_correction()`. Never constructed or seen by any caller outside
this file.

| Field | Type | Notes |
|---|---|---|
| `uses_expression` | `bool` | passed straight through to `CorrectionResult` |
| `grammatically_correct` | `bool` | combines with `natural` into `needs_correction`; not exposed on its own |
| `natural` | `bool` | combines with `grammatically_correct` into `needs_correction`; not exposed on its own |

## Call flow (replaces `request_correction()`'s single call)

```text
request_correction(target_expression, sentence, base_url, model, timeout)
  │
  ├─▶ _request_judge(...) ──▶ None (failure) ──▶ return _unavailable()   [FR-004]
  │                       └─▶ _JudgeVerdict
  │
  ├─ needs_correction = not (verdict.grammatically_correct and verdict.natural)
  │
  ├─ not needs_correction ──▶ return CorrectionResult(available=True,
  │                             uses_expression=verdict.uses_expression,
  │                             needs_correction=False,
  │                             corrected=None, explanation=None)         [FR-002: Teacher never called]
  │
  └─ needs_correction ──▶ _request_teacher(...) ──▶ None (failure) ──▶ return _unavailable()   [FR-005]
                                                  └─▶ (corrected, explanation)
                                                       ──▶ return CorrectionResult(available=True,
                                                             uses_expression=verdict.uses_expression,
                                                             needs_correction=True,
                                                             corrected=corrected, explanation=explanation)
```

`_unavailable()` is the existing helper (`CorrectionResult(available=False,
uses_expression=None, needs_correction=None, corrected=None,
explanation=None)`) — unchanged, now reused for two failure sites instead
of one.

## Progress log / everything downstream — UNCHANGED

`PracticeAttempt`, the progress-log format, `session_state.py`, and every
UI file read only `CorrectionResult`'s existing fields and are completely
unaware that two requests happened instead of one.
