# Contract: Word-List Import API (enriched uploads)

Implemented in `src/web/app.py`, in accounts mode with `word_lists_dir`
set; these are the same conditions as spec 016's routes. Every route is
behind the spec 015 login guard (no login → `401 {"error": "login
required"}`) and acts only on the logged-in account's pending import.

Spec 016's `POST /api/word-lists`, `GET /api/word-lists` and
`DELETE /api/word-lists/<name>` are **unchanged** (research R9).

## Import State (the response body used below)

```json
{
  "import": {
    "list_name": "z-words",
    "source_filename": "z-words.txt",
    "status": "running",
    "failure_reason": null,
    "total": 40,
    "done": 12,
    "enriched_count": 11,
    "failed_count": 1,
    "savable_count": 10,
    "upload_skipped": ["line 7: no English word"],
    "upload_skipped_count": 1,
    "items": [
      {
        "index": 0,
        "english": "zealous",
        "state": "enriched",
        "ipa": "ˈzeləs",
        "ipa_review": null,
        "chinese": "热心的；热情的",
        "alternates": [],
        "dropped_alternates": ["enthusiastic"],
        "error": null,
        "existing": null,
        "choice": "keep",
        "duplicate_of": null
      },
      {
        "index": 1,
        "english": "receive",
        "state": "enriched",
        "ipa": "rɪˈsiːv",
        "ipa_review": null,
        "chinese": "收到；接受",
        "alternates": [],
        "dropped_alternates": [],
        "error": null,
        "existing": { "source": "own", "list": "unit1", "ipa": "rɪˈsiːv", "chinese": "收到；接受", "alternates": ["accept"] },
        "choice": "keep",
        "duplicate_of": null
      }
    ]
  }
}
```

- `"import": null` means the account has no pending import.
- `status` is one of `running`, `completed`, `partially_failed`, `failed`
  or `interrupted`.
- `state` is one of `waiting`, `enriching`, `enriched`, `failed` or
  `duplicate`.
- `upload_skipped` holds at most 20 entries, as in 016.

## `GET /api/word-lists/import`

`200` with the Import State. This is polled by the UI while the status is
`running`.

## `POST /api/word-lists/import`

`multipart/form-data` with `file` (required) and `discard_pending`
(`"true"` to replace an existing pending import).

The parsing, file types, decoding, size and word limits are those of
spec 016's `upload-formats.md`, with one difference: a missing Chinese
meaning is **not** a skip reason.

| Case | Status | Body |
|---|---|---|
| No file | `400` | `{"error": "Choose a file to upload."}` |
| Unsupported type / undecodable | `415` | as 016 |
| Too large | `413` | as 016 |
| 0 English words / > 5,000 | `422` | as 016 (the "No words found" hint is updated: see UI contract) |
| A pending import exists and `discard_pending` ≠ `"true"` | `409` | `{"pending": true, "import": <Import State>}`; nothing changed |
| Accepted | `202` | Import State with `status: "running"`, or `completed` if no item needs the model |

On acceptance:

1. Any previous pending import is discarded. A running worker is cancelled
   first.
2. Duplicates and existing entries are detected (research R7).
3. The file is written.
4. The worker starts.

Nothing under `word-lists/<user>/*.md` changes.

## `POST /api/word-lists/import/retry`

JSON body `{"index": <int>}` retries one item. An empty body `{}`
retries every `failed` item, plus the `waiting` items of a `failed` or
`interrupted` batch.

| Case | Status | Body |
|---|---|---|
| No pending import | `404` | `{"error": "Nothing to retry."}` |
| Already `running` | `200` | Current Import State. No second worker is started (FR-020). |
| `index` out of range, or the item isn't `failed` | `400` | `{"error": "That word can't be retried."}` |
| Started | `202` | Import State with `status: "running"` |

## `POST /api/word-lists/import/choice`

JSON body `{"index": <int>, "choice": "keep" | "update"}`.

| Case | Status |
|---|---|
| The item has `existing.source == "own"` | `200`, Import State |
| Any other item, or a bad `choice` | `400` `{"error": "That word has no entry to update."}` |
| No pending import | `404` |

## `POST /api/word-lists/import/confirm`

JSON body `{"replace": true | false}`. Use `true` once the learner has
confirmed replacing an existing list with the same name.

| Case | Status | Body |
|---|---|---|
| No pending import | `404` | `{"error": "Nothing to save."}` |
| Status `running` | `409` | `{"error": "Still enriching — wait until it finishes."}` |
| `savable_count == 0` and no `update` choices | `422` | `{"error": "No words are ready to save."}` |
| The list name exists and `replace` is not `true` | `409` | `{"exists": true, "name": "z-words"}`; nothing changed |
| Save failed (I/O) | `500` | `{"error": "Couldn't save the list; nothing was changed."}`; files restored, pending import kept |
| Saved | `200` | Confirm Result (below) |

Confirm Result:

```json
{
  "name": "z-words",
  "replaced": false,
  "added": 38,
  "updated": 1,
  "left_out": 2,
  "first_list": false,
  "applies_now": true
}
```

- `left_out` counts the failed and waiting items, and own-list
  existing entries kept as they are.
- After the save, the pending import file is deleted and
  `session_registry.refresh_vocab(account)` runs, as for a 016 upload.
- A double-submitted confirm sees no pending import on its second call
  and gets `404`, so nothing is saved twice.

## `DELETE /api/word-lists/import`

This discards the pending import. It cancels any running worker and
deletes the file.

`200` `{"discarded": true}`, or `404` if there is nothing to discard.

## Isolation

- Every route acts on `word-lists/<logged-in username>/.pending-import.json`
  only. An account can never read or act on another account's import.
- No route accepts a file path, list name or group from the request body.
  The list name comes only from the uploaded file name, via
  `sanitize_list_name`.
