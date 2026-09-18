# Contract Delta: Web JSON API (extends `003-web-ui`'s web-api-contract.md)

This is not a new contract — it is a backward-compatible amendment to
`specs/003-web-ui/contracts/web-api-contract.md`. Existing fields, status
codes, and endpoints are unchanged; only the additions below apply.

## `GET /api/state` — additional fields

| `step` | Additional fields (beyond `003`'s contract) |
|---|---|
| `"sentence"` | `answer` (string) — the learner's just-submitted recall answer; `correct` (bool) — whether it was graded correct |
| `"feedback"` | same two fields, still present (the recall outcome for the item just being reviewed) |

Example, `step == "sentence"`:

```json
{
  "step": "sentence",
  "chinese": "收到",
  "accepted_expressions": ["receive", "accept"],
  "answer": "receive",
  "correct": true,
  "warnings": []
}
```

**Why this is additive, not a breaking change**: every field `003`'s
contract already specifies for these steps (`chinese`,
`accepted_expressions`, `sentence`, `feedback`, `warnings`) keeps its exact
existing meaning and type; a client written against `003`'s contract alone
continues to work unmodified, simply ignoring the two new fields it
doesn't look for.

## `POST /api/sentence` — new rejection case

| Condition | Response |
|---|---|
| A second `POST /api/sentence` is received while a previous one for the same session is still being processed (server-side `_review_in_progress` is `True`) | `409 Conflict`, `{"error": "a sentence review is already in progress"}` — identical shape to the existing "wrong step" `409`, no new status code introduced |

This supplements, not replaces, `003`'s existing `step != "sentence"` `409`
case — both are instances of the same "not ready for this request" rule
from the caller's point of view.

## Out of scope for this delta

- No change to `POST /api/answer`, `POST /api/continue`, or `GET /` —
  their `003` contracts are unaffected.
- No change to the sentence-review request/response contract itself
  (`specs/001-vocab-recall-tutor/contracts/ollama-correction-contract.md`)
  or to the progress-log format — this delta only concerns what
  `GET /api/state` exposes and one additional rejection case.
