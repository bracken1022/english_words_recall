# Contract: Local LLM (Ollama) Sentence Correction Call

Consumed by `services/llm_client.py`. This is an outbound contract (the app is
an HTTP client of the learner's own local Ollama server — it never spawns the
`ollama` CLI as a subprocess), covering FR-007, FR-008, FR-009, FR-010.

**Boundary rule**: the fields returned by this contract are consumed *only*
for display and for the `PracticeAttempt.sentence`/`feedback` log fields.
Nothing in the session's control flow (grading, item ordering, session
progression) may read or branch on any field defined here — see `plan.md`
Constraints and `research.md` "Determinism of the learning state machine."
Ollama evaluates language quality; it never controls lesson progression.

## Request

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
      "needs_correction": {"type": "boolean"},
      "corrected": {"type": ["string", "null"]},
      "explanation": {"type": ["string", "null"]}
    },
    "required": ["uses_expression", "needs_correction", "corrected", "explanation"]
  },
  "messages": [
    {
      "role": "system",
      "content": "You are an English grammar and naturalness checker for a language learner. Respond only with the requested JSON object."
    },
    {
      "role": "user",
      "content": "Target expression: \"<english>\". Learner's sentence: \"<sentence>\". Does the sentence use the target expression? Is it grammatically correct and natural? If not, provide a corrected sentence and a one-to-two sentence explanation; otherwise leave those two fields null."
    }
  ]
}
```

- `<english>` and `<sentence>` are inserted verbatim (after basic whitespace
  normalization); no other preprocessing is required by this contract.
- `model` defaults to `qwen3:14b` and MUST be operator-configurable (the
  app's `--model` flag / `llm_client.request_correction(..., model=...)`
  parameter) — never hardcoded past that default.
- `format` is Ollama's structured-output parameter: a JSON Schema that
  constrains the model's output. This is what makes the reply structured
  data rather than free text.

## Expected response (success path)

```
HTTP 200
```

```json
{
  "message": {
    "role": "assistant",
    "content": "{\"uses_expression\": true, \"needs_correction\": true, \"corrected\": \"I received a gift yesterday.\", \"explanation\": \"Past tense \\\"received\\\" is needed, not \\\"receive\\\".\"}"
  }
}
```

`message.content` is a JSON-encoded string (per Ollama's structured-output
contract); `llm_client.py` MUST `json.loads()` it and validate that all four
keys (`uses_expression`, `needs_correction`, `corrected`, `explanation`) are
present with the expected types before trusting any of them.

## Handling rules (FR-008, FR-009, FR-010)

| Condition | Behavior |
|---|---|
| HTTP 200, `content` parses as JSON with all four keys present and correctly typed | Show `uses_expression`/`needs_correction` result; if correction needed, show `corrected` + `explanation`; if not needed, tell the learner it was already correct. |
| HTTP 200, `uses_expression: false` | Tell the learner the target expression is missing (FR-009), regardless of the other fields. |
| HTTP 200, `content` is not valid JSON, is not a JSON object, or is missing/mistypes a required key | Treat identically to "LLM unavailable" (FR-010) — do not show partial/guessed output to the learner. |
| Connection error, timeout, or non-200 status | Treat as "LLM unavailable" (FR-010): tell the learner correction is unavailable, do not retry indefinitely, let them continue to the next item. |
| Empty response body | Same as "doesn't parse" above. |

## Out of scope for this contract

- Which specific model is loaded in Ollama beyond the configurable default
  (`qwen3:14b`) — model selection/pulling is an operator concern, not a
  functional requirement of this feature.
- Streaming responses (`stream: false` is fixed — the CLI waits for the full
  reply rather than rendering partial tokens).
- Any influence on session control flow — see the Boundary rule above.
