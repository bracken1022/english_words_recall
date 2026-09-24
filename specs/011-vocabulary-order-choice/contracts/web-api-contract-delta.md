# Contract Delta: Web JSON API (extends `003-web-ui` and its `004`/`006`/`007`/`009` deltas)

This is not a new contract — it is a backward-compatible amendment to
`specs/003-web-ui/contracts/web-api-contract.md` (as already amended by
`004`, `006`, `007`, and `009`'s deltas). Existing fields, status codes,
and endpoints are unchanged; only the addition below applies.

## `POST /api/select` — new optional field

| Field | Type | Required | Notes |
|---|---|---|---|
| `collection` | `string \| null` | Yes (unchanged from `007`) | `400` + `{"error": "missing 'collection'"}` if absent, exactly as before |
| `order` | `"sequential" \| "random"` | **No** | If absent, or any value other than these two strings, treated as `"sequential"` — never a `400` for this field |

Example — collection only (unchanged from `007`, still valid):

```json
{ "collection": "unit1" }
```

Example — collection with random order (new):

```json
{ "collection": "unit1", "order": "random" }
```

Both produce a `200` response with the same shape `007`'s contract
already documents (`GET /api/state`'s `"recall"` or `"empty"` body) — this
delta adds no new response field. The only observable difference random
order makes is the sequence the words are subsequently presented in.

## Behavior

- Valid only when `step == "choose"` — unchanged 409 rule from `007`
  applies identically; `order` doesn't change when this call is valid.
- When `order == "random"`, the collection's filtered pool is shuffled
  once, in place, before `current_index`/progress counters reset —
  exactly the same moment `007`'s existing filtering already happens.
- MUST NOT touch the progress log or `PracticeSession`'s step machine
  beyond what `007`'s contract already documents for this endpoint.

## Out of scope for this delta

- No change to `GET /api/state`'s response shape for any step — the
  chosen order is not reported back anywhere; it's consumed once and not
  stored (`data-model.md`).
- No change to `POST /api/answer`, `POST /api/sentence`, `POST /api/skip`,
  `POST /api/continue`, `POST /api/restart`, or `GET /`.
- No change to the CLI's own contract (it has no HTTP API) — its
  `--order` flag is documented in `data-model.md` and the repository
  `README.md`, not here.
