# Contract: Word-Lists API

Implemented in `src/web/app.py`, accounts mode only (`create_app(accounts=...)`).
Every route here is behind spec 015's login guard — no login → `401
{"error": "login required"}`, nothing read or written. Every route acts only
on `word-lists/<logged-in username>/`. Covers spec FR-001, FR-003 – FR-009,
FR-012.

## `GET /api/word-lists`

`200`:

```json
{
  "word_source": "own",
  "lists": [
    { "name": "unit1", "word_count": 42, "uploaded_at": "2026-10-02T09:15:00+00:00" }
  ]
}
```

`lists` sorted by name (case-insensitive); empty list and `"word_source":
"shared"` when the account has no lists.

## `POST /api/word-lists`

`multipart/form-data` with `file` (required) and `replace` (`"true"` to
confirm replacing; anything else / absent = false).

| Case | Status | Body |
|---|---|---|
| No `file` part / empty filename | `400` | `{"error": "Choose a file to upload."}` |
| Unsupported type / undecodable | `415` | `{"error": "<message from upload-formats.md>"}` |
| Too large | `413` | `{"error": "The file is larger than 1 MB."}` |
| 0 words / > 5,000 words | `422` | per `upload-formats.md` |
| Name exists (case-insensitive) and `replace` not `"true"` | `409` | `{"exists": true, "name": "unit1"}` — nothing changed |
| Saved | `200` | Upload Result (below) |

Upload Result:

```json
{
  "name": "unit1",
  "replaced": false,
  "added": 40,
  "skipped_count": 2,
  "skipped": ["line 12: no Chinese meaning", "line 30: no English word"],
  "first_list": true,
  "applies_now": true
}
```

After a successful save, the account's practice session picks up the change
if it is on the word-set screen (or empty screen); a session in progress is
untouched (research R3).

## `DELETE /api/word-lists/<name>`

`<name>` is URL-encoded; matched case-insensitively within the caller's own
folder only.

| Case | Status | Body |
|---|---|---|
| Deleted | `200` | `{"deleted": "unit1", "word_source": "own" \| "shared"}` |
| No such list for this account | `404` | `{"error": "No list named \"unit1\"."}` |

Practice history is never touched. Session refresh as for upload.

## `GET /api/state` — added field (accounts mode)

`"word_source": "own" | "shared"` — which words this account currently
practices from.

## Isolation guarantees

- Account A can never list, read, replace, or delete B's lists; a name that
  only exists for B returns `404` for A.
- A list name can never address a path outside the caller's folder
  (names are re-sanitised; `../x` becomes `x`).
