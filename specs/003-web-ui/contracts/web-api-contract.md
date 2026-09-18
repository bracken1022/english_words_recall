# Contract: Web JSON API

Implemented by `src/web/app.py`, backed by `src/web/session_state.py`'s
`PracticeSession`. Covers FR-001 through FR-010, FR-017.

**Boundary rule**: every endpoint here is a thin wrapper over the existing,
unchanged services (`vocabulary_loader`, `matcher.grade_answer`,
`llm_client.request_correction`, `progress_log.append_attempt`). No
endpoint here re-implements or alters grading, review, or persistence logic
— see `plan.md` Constraints.

## `GET /api/state`

Returns the current step and whatever is safe to show for it. Never
includes the target English expression while `step == "recall"` (FR-002).

```json
{
  "step": "recall",
  "chinese": "收到",
  "warnings": []
}
```

| `step` | Additional fields |
|---|---|
| `"empty"` | none — the pool has no valid items (FR-017 edge case) |
| `"recall"` | `chinese` (string) |
| `"sentence"` | `chinese`, `accepted_expressions` (list[string]) — recall already resolved, target now revealed (FR-004) |
| `"feedback"` | `chinese`, `accepted_expressions`, `sentence` (the learner's submitted sentence), `feedback` (see `POST /api/sentence`'s response shape) |
| `"complete"` | none — the pool is exhausted |

`warnings` (list of strings) is always present and carries any
vocabulary-loading warnings captured at startup (FR-017).

## `POST /api/answer`

Valid only when `step == "recall"`; otherwise responds `409 Conflict` with
`{"error": "not awaiting an answer"}` and changes nothing.

Request:

```json
{ "answer": "receive" }
```

Response (`200`):

```json
{ "correct": true, "accepted_expressions": ["receive", "accept"] }
```

Grades via `matcher.grade_answer` unchanged (FR-003); reveals the accepted
expression(s) regardless of correctness (FR-004); advances `step` to
`"sentence"`.

## `POST /api/sentence`

Valid only when `step == "sentence"`; otherwise `409 Conflict` as above.
This is the one call that may take several seconds — see
`contracts/loading-indicator-contract.md`.

Request:

```json
{ "sentence": "I recieve a gift yesterday." }
```

Response (`200`) — same fields `001`'s `CorrectionResult` already carries,
passed straight through (FR-006, FR-008):

```json
{
  "available": true,
  "uses_expression": true,
  "needs_correction": true,
  "corrected": "I received a gift yesterday.",
  "explanation": "Past tense is needed."
}
```

When `available` is `false` (LLM unreachable or reply unusable), the other
fields are `null`; the client shows the existing "review unavailable"
message (FR-009). In every case, this call also appends the completed
`PracticeAttempt` to the progress log (FR-012, `001`'s
`contracts/progress-log-format.md`, unchanged) and advances `step` to
`"feedback"`.

## `POST /api/continue`

Valid when `step == "feedback"` (advances to the next item, or to
`"complete"` if the pool is exhausted) or `step == "complete"` (no-op,
stays `"complete"`); otherwise `409 Conflict`. No request body.

Response (`200`): same shape as `GET /api/state` for whatever the new step
is. There is no endpoint to move backward or to skip an unanswered item
(FR-010) — none is defined by this contract, and none should be added by
implementation.

## Error handling

| Condition | Response |
|---|---|
| Request for the wrong step (see per-endpoint rules above) | `409 Conflict`, `{"error": "<reason>"}`, no state change |
| Malformed JSON body / missing required field | `400 Bad Request`, `{"error": "<reason>"}`, no state change |
| Any other unexpected server error | `500`, generic message — MUST NOT crash the process or corrupt `PracticeSession` state for subsequent requests |

## Out of scope for this contract

- Authentication/session identity (FR-014 — there is none).
- Any endpoint for selecting a lesson/group after startup (research.md:
  filtering is a server-startup flag, not an API).
- Any change to `specs/001-vocab-recall-tutor/contracts/ollama-correction-contract.md`
  — `POST /api/sentence` calls `request_correction` exactly as specified
  there.
