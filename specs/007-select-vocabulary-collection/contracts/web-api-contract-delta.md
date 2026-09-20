# Contract Delta: Web JSON API (extends `003-web-ui`, `004-web-ui-ux-polish`, and `006-confirm-skip-word`'s deltas)

This is not a new contract — it is a backward-compatible amendment to
`specs/003-web-ui/contracts/web-api-contract.md` (as already amended by
`004`'s and `006`'s deltas). Existing fields, status codes, and endpoints
are unchanged; only the additions below apply.

**Backward compatibility note**: every addition here only ever applies
when the web server was started *without* a collection pre-selected (no
`--group`). Starting with `--group` continues to behave exactly as
`003`/`004`/`006` already document — `"choose"` never appears, `"complete"`
stays a dead end, `POST /api/select` and `POST /api/restart` both `409`.

## `GET /api/state` — new `"choose"` step, and new field on `"complete"`

| `step` | Fields |
|---|---|
| `"choose"` (**new**) | `collections`: list of `{"key": string \| null, "label": string, "count": int}`, per `data-model.md`'s derived view. `null` key = practice everything (always first); real `group` values next, alphabetical; `"__ungrouped__"` last if applicable. |
| `"complete"` | existing `total`/`correct` fields, **plus new** `can_restart` (bool) |

Example, `step == "choose"`:

```json
{
  "step": "choose",
  "collections": [
    { "key": null, "label": "Practice everything", "count": 23 },
    { "key": "t-words", "label": "t-words", "count": 20 },
    { "key": "unit1", "label": "unit1", "count": 3 }
  ],
  "warnings": []
}
```

Example, `step == "complete"` (interactive/unlocked session):

```json
{ "step": "complete", "total": 3, "correct": 2, "can_restart": true, "warnings": [] }
```

A `--group`-locked session's `"complete"` response is unchanged from
`006`'s contract except for the added `can_restart: false`.

## `POST /api/select`

Valid only when `step == "choose"`; otherwise `409 Conflict` with
`{"error": "not choosing a collection"}` and no state change.

Request — the `"collection"` key MUST be present (its value may be `null`):

```json
{ "collection": "unit1" }
```

| Condition | Response |
|---|---|
| `"collection"` key missing from the request body | `400 Bad Request`, `{"error": "missing 'collection'"}`, no state change |
| `step != "choose"` | `409 Conflict`, `{"error": "not choosing a collection"}`, no state change |
| Valid | `200`, same shape as `GET /api/state` for the resulting step (`"recall"` or, defensively, `"empty"`) |

This call MUST NOT call `request_correction` or touch the progress log —
it only changes which words are in the active pool and resets session
progress counters (`data-model.md`).

## `POST /api/restart`

Valid only when `step == "complete"` **and** the session was not started
with a collection pre-selected (`group_locked` is false); otherwise
`409 Conflict` with `{"error": "not ready to restart"}` and no state
change. No request body.

This call:
- MUST reload vocabulary from disk (picking up files added, removed, or
  edited since the session started — spec.md Assumptions).
- MUST return to `"choose"` (or `"empty"` if the reload now finds nothing).
- MUST NOT touch the progress log itself (no attempt is recorded by this
  call; it only changes what's available to select next).

Response (`200`): same shape as `GET /api/state` for the resulting step.

## Out of scope for this delta

- No change to `POST /api/answer`, `POST /api/sentence`, `POST /api/skip`,
  `POST /api/continue`, or `GET /` — their existing contracts are
  unaffected, including `POST /api/continue`'s existing "complete is a
  no-op" behavior, which is unchanged (`restart()` is a separate, new
  action, not folded into `continue`).
- No change to the sentence-review contract
  (`specs/001-vocab-recall-tutor/contracts/ollama-correction-contract.md`)
  or the progress-log file format.
- No change to the CLI (`src/cli/session.py` is unaffected — see `spec.md`
  Assumptions).
- No way to switch collections while a session is in progress (only from
  `"choose"` at the very start, or `"complete"` at the very end) — per the
  2026-09-20 clarification in `spec.md`.
