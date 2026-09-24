# Contract Delta: Web JSON API (extends `003-web-ui` and its `004`/`006`/`007`/`009`/`011`/`012` deltas)

This is not a new contract — it is a backward-compatible amendment to
`specs/003-web-ui/contracts/web-api-contract.md` (as already amended by
`004`, `006`, `007`, `009`, `011`, and `012`'s deltas). No new endpoint,
no new request/response fields on any endpoint. Only `POST /api/continue`'s
set of valid originating steps changes.

## `POST /api/continue` — newly valid from one more step

| Originating `state.step` | Before this feature | After this feature |
|---|---|---|
| `"feedback"` | `200`, advances (unchanged) | `200`, advances (unchanged) |
| `"reveal"` (**new step**, recall-only mode) | N/A — step didn't exist | `200`, records the held attempt and advances |
| `"complete"` | `200`, no-op | `200`, no-op (unchanged) |
| Anything else (`"recall"`, `"sentence"`, `"choose"`, `"empty"`) | `409` | `409` (unchanged) |

Request body: none (unchanged — `POST /api/continue` has never taken a
body). Response body: `GET /api/state`'s shape for whatever step results
(unchanged shape — no new fields).

## `POST /api/answer` — behavior delta, no shape change

The response shape is unchanged (`{"correct": ..., "accepted_expressions":
[...]}`), but which step follows now depends on both the session's mode
*and*, for recall-only mode, correctness:

| Mode | Correct? | `GET /api/state`'s `step` right after `POST /api/answer` |
|---|---|---|
| `sentence` (default) | either | `"sentence"` — unchanged |
| `recall-only` | correct | `"recall"` (more words) or `"complete"` (last word) — unchanged from spec `012` |
| `recall-only` | **incorrect** | **`"reveal"`** (new) — previously this also went straight to `"recall"`/`"complete"`; now it waits for `POST /api/continue` |

No request-shape change to `POST /api/answer` itself.

## Out of scope for this delta

- No change to `GET /api/state`'s response *shape* for any step — the
  `"reveal"` step reuses the same `accepted_expressions`/`answer`/
  `correct` fields `"sentence"`/`"feedback"` already expose (data-model.md).
- No change to `POST /api/select`, `POST /api/sentence`, `POST /api/skip`,
  `POST /api/restart`, `POST /api/transcribe`, or `GET /`.
- No change to the CLI's own contract (it has no HTTP API) — its new
  "press Enter to continue" pause is documented in `data-model.md` and
  the repository `README.md`, not here.
