# Contract Delta: Web JSON API (extends `003-web-ui` and its `004`/`006`/`007` deltas)

This is not a new contract — it is a backward-compatible amendment to
`specs/003-web-ui/contracts/web-api-contract.md` (as already amended by
`004`, `006`, and `007`'s deltas). Existing fields, status codes, and
endpoints are unchanged; only the additions below apply.

## `GET /api/state` — new field, present on every step

| Field | Type | Notes |
|---|---|---|
| `voice_available` | `bool` | `true` iff the local speech-to-text package is importable on this server (data-model.md). Present on **every** step's response (like `warnings`), not just `"sentence"` — the client uses it to decide whether to show the mic control at all, independent of practice-session progression. |

Example (any step):

```json
{ "step": "sentence", "chinese": "收到", "accepted_expressions": ["receive"], "voice_available": true, "warnings": [] }
```

A server where the optional speech-to-text dependency isn't installed
simply always reports `"voice_available": false` — no other field or
status code changes.

## `POST /api/transcribe`

Stateless — valid regardless of the current practice-session step (no
`409` "wrong step" case exists for this endpoint; see `research.md` §3).

Request: raw audio bytes as the request body, with `Content-Type` set to
whatever MIME type the browser's `MediaRecorder` produced (e.g.
`audio/webm;codecs=opus`).

Response (`200`) — mirrors `CorrectionResult`'s established
"always 200, `available` carries success/failure" convention rather than
using HTTP error codes for an expected, routine failure mode:

```json
{ "available": true, "text": "I received a gift yesterday." }
```

```json
{ "available": false, "text": null }
```

| Condition | Response |
|---|---|
| Transcription succeeds | `200`, `{"available": true, "text": "<transcribed sentence>"}` |
| Speech-to-text package not installed, model fails to load, or audio fails to decode | `200`, `{"available": false, "text": null}` — never a `4xx`/`5xx`, matching how `POST /api/sentence` already treats "Ollama unavailable" as a normal, expected outcome rather than a server error |
| Request body is empty/missing | `200`, `{"available": false, "text": null}` — treated the same as any other failure to produce text, no separate `400` case |

This call:
- MUST NOT touch `PracticeSession` or the progress log in any way — it
  has no session-state side effects at all (data-model.md).
- MUST NOT persist the uploaded audio beyond producing this one response
  (spec.md FR-006).
- MUST NOT be gated by the current practice-session step.

## `POST /api/sentence` — unaffected

This delta makes no change to `POST /api/sentence`. Text that arrived via
transcription is submitted through this exact same existing endpoint,
indistinguishable from text the learner typed directly — the client sends
whatever is currently in the sentence field, regardless of how it got
there.

## Out of scope for this delta

- No change to `POST /api/answer`, `POST /api/skip`, `POST /api/continue`,
  `POST /api/select`, `POST /api/restart`, or `GET /`.
- No change to the sentence-review contract
  (`specs/001-vocab-recall-tutor/contracts/ollama-correction-contract.md`)
  or the progress-log format.
- No CLI changes (`src/cli/session.py` is unaffected — see `spec.md`
  Assumptions and `plan.md` Constraints).
- No new endpoint or field for configuring which speech-to-text model is
  used, or for pre-downloading it — an operational/setup concern covered
  in `quickstart.md`, not an API surface.
