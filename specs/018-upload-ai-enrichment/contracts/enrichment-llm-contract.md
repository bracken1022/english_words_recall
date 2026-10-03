# Contract: Enrichment Request to the Local Model

`src/services/enrichment_client.py::request_enrichment(english, supplied,
base_url, model, timeout=60.0) -> EnrichmentReply`. This covers FR-004,
FR-006 and FR-007. It uses the same Ollama `/api/chat` endpoint and the
same `--ollama-url`/`--model` as sentence review. Nothing is sent
anywhere else.

*Revised 2026-10-03 (research R4).* The model is asked only for a Chinese
meaning and alternates. Pronunciations come from the offline CMU
dictionary, because the model's IPA proved unreliable (eval-report.md).

## Request

```json
{
  "model": "<configured model>",
  "stream": false,
  "think": false,
  "format": {
    "type": "object",
    "properties": {
      "chinese": {"type": "string"},
      "alternates": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["chinese", "alternates"]
  },
  "options": {"temperature": 0},
  "messages": [
    {"role": "system", "content": "<SYSTEM PROMPT>"},
    {"role": "user", "content": "<USER PROMPT>"}
  ]
}
```

**System prompt**, in substance. The exact wording is implementation
detail, but these rules must all appear:

- You provide dictionary data for one English word or expression, for a
  Chinese-speaking learner.
- `chinese`: a concise modern Chinese meaning for vocabulary study. Give
  at most 4 short meanings, separated by `；`, with no part-of-speech
  labels and no example sentences.
- `alternates`: only spelling variants of the same word (British/American
  spellings, hyphenation). Never give synonyms. Usually this is `[]`.
- Do not change, correct or translate the English word.

**User prompt**: `English: "<english>"`. When the upload supplied a
Chinese meaning, add `Meaning: "<chinese>"`. That line is only context
for the alternates; the supplied meaning is kept regardless of the
model's reply (FR-007).

The prompt contains nothing else: no file name, list name, other words or
account data.

## Reply handling

| Condition | `outcome` |
|---|---|
| `requests.ConnectionError` (refused, DNS), or HTTP `404` | `unavailable` |
| Timeout, any other non-200, missing `message.content`, invalid JSON, non-object, missing required key, or wrong type | `bad_reply`, with `detail` |
| Otherwise | `ok` |

- Only `chinese` and `alternates` are read. Extra keys, including any
  `ipa` the model volunteers, are ignored.
- The model's output is never used as the English text, a list name, a
  group, a path or a workflow decision.
- `request_enrichment` never raises; every failure becomes an `outcome`.

## How the worker uses the outcome

| `outcome` | Effect |
|---|---|
| `ok` | Validate the reply ([enrichment-validation.md](enrichment-validation.md)). The item becomes `enriched`, or `failed` if the Chinese is invalid. |
| `bad_reply` | The item becomes `failed` with `error = "the local AI gave an unusable answer"`, and the batch continues. |
| `unavailable` | The current item goes back to `waiting`, the batch stops, the status becomes `failed`, and `failure_reason` is `"Local AI unavailable — start Ollama, then press Retry."` |

Fields that were supplied (FR-007) are never requested as overrides:

- If Chinese was supplied, the model's `chinese` is ignored.
- An item whose Chinese and IPA were both supplied makes no request at
  all.
