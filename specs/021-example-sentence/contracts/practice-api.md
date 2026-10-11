# Contract: Practice API Changes (web)

## Removed routes

`POST /api/sentence`, `POST /api/skip`, `POST /api/retry-sentence` and
`POST /api/transcribe` are removed and return `404`.

## `POST /api/select`

`mode` is one of `"recall-only"`, `"example"` or `"example-recall"`.
`"sentence"` maps to `"example"`, and any other value also defaults to
`"example"`.

## `GET /api/state`: new fields at `reveal` and `sentence-recall`

```json
{"step": "reveal", "correct": true, "accepted_expressions": ["zealous"], "ipa": "ˈzeləs",
 "pos": ["adj."], "chinese": "热心的",
 "example": {"sentence": "She is a zealous supporter of the local team.",
             "translation": "她是当地球队的狂热支持者。"},
 "example_status": "ready", "mode": "example"}
```

- **`example_status`**:
  - `ready` means `example` is set;
  - `pending` means it is still being written, so the page should poll;
  - `unavailable` means none is available this time;
  - `off` means the mode is recall-only.
- **The `sentence-recall` step**: it sends `example.translation` only;
  `example.sentence` is withheld (`null`) until the page asks to reveal
  it. Revealing it is a client-side action, because the reveal response
  carries it (see below).

## `POST /api/continue` at `reveal`

- **Recall-only, or the example mode**: the attempt is recorded, and the
  session goes to the next word or `complete`.
- **The example-recall mode**: if the example is ready, the step becomes
  `sentence-recall`. Otherwise the attempt is recorded and the session
  moves on.

## `POST /api/sentence-recall`

The body is `{"mark": "got" | "not_yet" | "skip" | "reveal"}`.

| Mark | Result |
|---|---|
| `reveal` | `200`, the state with `example.sentence` filled in. The step stays `sentence-recall`. |
| `got` / `not_yet` | Records the attempt with `sentence_recall`, then moves on. |
| `skip` | Records the attempt without a mark, then moves on. |
| Wrong step | `409 {"error": "Not recalling a sentence."}` |
| Bad mark | `400` |

## `POST /api/example/new`

Valid at `reveal` and `sentence-recall`. It generates a different example
and saves it in place of the old one.

| Case | Status |
|---|---|
| Done | `200`, the state with the new `example` |
| Local AI unavailable, or no valid example after a retry | `503 {"error": "Couldn't make a new example right now."}`; the old one is kept |
| Wrong step | `409` |
