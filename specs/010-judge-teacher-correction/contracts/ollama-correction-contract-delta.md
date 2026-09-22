# Contract Delta: Local LLM (Ollama) Sentence Correction Call

Extends `specs/001-vocab-recall-tutor/contracts/ollama-correction-contract.md`.
That contract described one request/response pair; this delta replaces it
with two, made sequentially against the same `base_url`/`model`. Nothing
outside `src/services/llm_client.py` observes this change — its own
public contract (`request_correction()`'s signature, `CorrectionResult`'s
shape) is unchanged, per `001`'s Boundary rule and this feature's FR-003.

## Request 1 — Judge

```
POST http://localhost:11434/api/chat
Content-Type: application/json
```

```json
{
  "model": "qwen3:14b",
  "stream": false,
  "format": {
    "type": "object",
    "properties": {
      "uses_expression": {"type": "boolean"},
      "grammatically_correct": {"type": "boolean"},
      "natural": {"type": "boolean"}
    },
    "required": ["uses_expression", "grammatically_correct", "natural"]
  },
  "messages": [
    {
      "role": "system",
      "content": "You are an English grammar and naturalness judge for a language learner. Respond only with the requested JSON object."
    },
    {
      "role": "user",
      "content": "Target expression: \"<english>\". Learner's sentence: \"<sentence>\". Does the sentence use the target expression? Is it grammatically correct? Does it sound natural to a native speaker?"
    }
  ]
}
```

Expected response (success path):

```json
{ "message": { "role": "assistant", "content": "{\"uses_expression\": true, \"grammatically_correct\": false, \"natural\": true}" } }
```

`llm_client.py` MUST `json.loads()` `message.content` and validate all
three keys are present with boolean types before trusting any of them —
identical validation discipline to `001`'s contract, just three keys
instead of four.

## Request 2 — Teacher (conditional)

Only made when Request 1 succeeded **and** `grammatically_correct` and
`natural` were not both `true` (i.e., `needs_correction` per
`data-model.md`). Never made otherwise.

```json
{
  "model": "qwen3:14b",
  "stream": false,
  "format": {
    "type": "object",
    "properties": {
      "corrected": {"type": "string"},
      "explanation": {"type": "string"}
    },
    "required": ["corrected", "explanation"]
  },
  "messages": [
    {
      "role": "system",
      "content": "You are an English writing teacher helping a language learner fix a mistake in their sentence. Respond only with the requested JSON object."
    },
    {
      "role": "user",
      "content": "Target expression: \"<english>\". Learner's sentence: \"<sentence>\". This sentence has a grammar or naturalness problem. Provide a corrected, natural version and a one-to-two sentence explanation of the mistake."
    }
  ]
}
```

Expected response (success path):

```json
{ "message": { "role": "assistant", "content": "{\"corrected\": \"I received a gift yesterday.\", \"explanation\": \"Past tense \\\"received\\\" is needed, not \\\"receive\\\".\"}" } }
```

## Handling rules (replaces `001`'s single-request table)

| Condition | Behavior |
|---|---|
| Judge: HTTP 200, `content` parses with all three keys present/typed, both `grammatically_correct` and `natural` are `true` | `CorrectionResult(available=True, uses_expression=<judge value>, needs_correction=False, corrected=None, explanation=None)` — Teacher is **never** called |
| Judge: HTTP 200, valid, but `grammatically_correct` or `natural` is `false` | Proceed to Request 2 |
| Judge: connection error, timeout, non-200, unparseable/invalid JSON, missing/mistyped key | Treat as "unavailable" (`CorrectionResult(available=False, ...)`) — identical to `001`'s existing rule, applied to the Judge call; Teacher is never called |
| Teacher (only reached when Judge said correction is needed): HTTP 200, valid JSON with both keys present/typed | `CorrectionResult(available=True, uses_expression=<judge value>, needs_correction=True, corrected=<teacher value>, explanation=<teacher value>)` |
| Teacher: connection error, timeout, non-200, unparseable/invalid JSON, missing/mistyped key | Treat as "unavailable" — the **whole** result, not a partial one; the Judge's already-successful verdict is discarded rather than surfaced alone (spec.md FR-005) |

`uses_expression: false` no longer gets special-cased in this table (it
didn't change behavior in `001`'s table either, beyond "regardless of the
other fields" — that's still true here: it's just one of the three Judge
booleans, read straight through to `CorrectionResult` either way).

## Out of scope for this delta

- Which specific model is loaded — unchanged from `001`.
- Streaming — unchanged (`stream: false` for both requests).
- Any influence on session control flow — unchanged; the Boundary rule
  from `001`'s contract applies identically to both requests.
- Retrying either request, or running them in parallel — both requests
  are made sequentially, at most once each, exactly as `001`'s single
  request was.
