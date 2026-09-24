# Contract Delta: Web JSON API (extends `003-web-ui` and its `004`/`006`/`007`/`009`/`011` deltas)

This is not a new contract — it is a backward-compatible amendment to
`specs/003-web-ui/contracts/web-api-contract.md` (as already amended by
`004`, `006`, `007`, `009`, and `011`'s deltas). Existing fields, status
codes, and endpoints are unchanged; only the addition below applies.

## `POST /api/select` — new optional field

| Field | Type | Required | Notes |
|---|---|---|---|
| `collection` | `string \| null` | Yes (unchanged from `007`) | `400` + `{"error": "missing 'collection'"}` if absent, exactly as before |
| `order` | `"sequential" \| "random"` | No (unchanged from `011`) | Missing/invalid → `"sequential"` |
| `mode` | `"sentence" \| "recall-only"` | **No** | If absent, or any value other than these two strings, treated as `"sentence"` — never a `400` for this field |

Example — collection, order, and mode together (new):

```json
{ "collection": "unit1", "order": "random", "mode": "recall-only" }
```

Both produce a `200` response with the same shape `007`'s contract
already documents (`GET /api/state`'s `"recall"` or `"empty"` body) —
this delta adds no new response field. The only observable difference
recall-only mode makes is what happens after each subsequent
`POST /api/answer`.

## `POST /api/answer` — behavior delta, no shape change

The response shape is unchanged (`{"correct": ..., "accepted_expressions":
[...]}`), but which step follows now depends on the session's mode
(decided at `POST /api/select` time, or at startup):

| Mode | `GET /api/state`'s `step` right after `POST /api/answer` |
|---|---|
| `sentence` (default) | `"sentence"` — unchanged from today |
| `recall-only` | `"recall"` (more words remain) or `"complete"` (that was the last word) — `"sentence"` is never reached |

No request-shape change to `POST /api/answer` itself.

## Endpoints unaffected in recall-only mode

`POST /api/sentence` and `POST /api/skip` are simply never called by a
recall-only session's own UI flow (there is no sentence-writing screen
to submit from) — their contracts are unchanged, and both still return
their existing `409` if a recall-only session is somehow driven to call
them directly (session step will be `"recall"` or `"complete"`, never
`"sentence"`, so the existing `WrongStepError` guard already covers
this — no new logic is needed for this rejection).

## Out of scope for this delta

- No change to `GET /api/state`'s response shape for any step — the
  chosen mode is not reported back anywhere; it's consumed once and not
  stored for display (`data-model.md`).
- No change to `POST /api/restart` — returning to `"choose"` re-offers
  collection, order, and mode together, the same combined screen.
- No change to the CLI's own contract (it has no HTTP API) — its
  `--mode` flag is documented in `data-model.md` and the repository
  `README.md`, not here.
