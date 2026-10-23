# Contract: Corrections API and Practice State (web)

All routes keep the existing login guard (`401 {"error": "login
required"}` when signed out).

## `GET /api/state` at `reveal` and `sentence-recall` (changed)

Adds `corrected`: the fields corrected for the current word during this
session (empty list when none), so the page can show a small "Updated"
note next to them. `ipa`, `chinese` and `pos` are the word's values now,
so a correction that finished while the learner answered shows here.

```json
{"step": "reveal", "chinese": "热心的；狂热的", "pos": ["adj."], "ipa": "ˈzɛləs",
 "corrected": ["chinese", "pos"], "...": "..."}
```

Other steps don't include `corrected`. Recall shows the values the word
had when it came up (research R2).

## `GET /api/corrections` (new)

The corrections that apply to the words this learner practises: their
own lists' records, plus the shared sets' records when they practise the
shared sets. Newest first, at most 200.

```json
{
  "enabled": true,
  "paused": null,
  "corrections": [
    {"id": "a1b2c3d4e5f6", "scope": "own", "english": "tailor",
     "list": "T_words.md", "field": "chinese",
     "old": "裁缝；定制；使适合", "new": "裁缝；定做（衣服）；使适应",
     "at": "2026-10-21T09:30:00Z", "undone": false, "can_undo": true}
  ]
}
```

- `enabled`: `false` when no Qwen key is set (the page says "Qwen is not
  set up"); records made earlier are still listed.
- `paused`: `null`, or `{"reason": "Qwen could not be reached.",
  "until": "2026-10-21T09:35:00Z" | null}` (`null` until restart, after
  a rejected key; research R8). `reason` is always one of QwenError's
  fixed messages.
- `scope`: `"own"` or `"shared"`. `list` is the file name only.
- `old`/`new`: string, list of labels (`pos`) or `null`.
- `can_undo`: `false` once undone, or when the word has been edited or
  removed since.

## `POST /api/corrections/undo` (new)

```json
{"id": "a1b2c3d4e5f6"}
```

Undoes every field changed by the same check of that word (its batch),
restoring the old values (FR-005).

| Case | Status | Body |
|---|---|---|
| Undone | `200` | `{"undone": ["chinese", "pos"]}` |
| Unknown id, or not one this learner can see | `404` | `{"error": "That correction wasn't found."}` |
| Already undone | `409` | `{"error": "That correction was already undone."}` |
| The word changed or was removed since | `409` | `{"error": "That word has changed since, so it can't be undone."}` |
| Body not `{"id": <string>}` | `400` | `{"error": "id is required"}` |

After an undo, the restored values' fingerprint is marked checked, so
the word is not sent again and the change can't come back. A shared
correction undone by one learner is undone for everyone. A live session
sees the restored values from its next list load (the current word's
`state` is updated at once).

## Guarantees

- No route returns or logs the key, the prompt or Qwen's raw answer.
- Checks never change the session's step, and no route waits for a
  check.
- Without a key, `GET /api/corrections` works (`enabled: false`) and
  undo still works for earlier records.
