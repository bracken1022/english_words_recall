# Contract Delta: Web JSON API (extends `003-web-ui`'s web-api-contract.md and `004-web-ui-ux-polish`'s delta)

This is not a new contract — it is a backward-compatible amendment to
`specs/003-web-ui/contracts/web-api-contract.md` (as already amended by
`specs/004-web-ui-ux-polish/contracts/web-api-contract-delta.md`). Existing
fields, status codes, and endpoints are unchanged; only the addition below
applies.

**Explicit note on `003`'s "no skip" line**: `003`'s contract states "There
is no endpoint to move backward or to skip an unanswered item ... none
should be added by implementation." `POST /api/skip` below is a deliberate,
narrow exception to that line, not an oversight — see `plan.md`'s
Constitution Check and `spec.md`'s Assumptions for why it does not
reintroduce the thing `003` was guarding against (skipping an item's
recall answer, or moving backward).

## `POST /api/skip`

Valid only when `step == "sentence"`; otherwise `409 Conflict` with
`{"error": "not awaiting a sentence"}` and no state change — same
convention as every other wrong-step rejection in this contract.

No request body.

This call:
- MUST NOT invoke sentence correction (no call to `request_correction` /
  the local LLM) — this is the entire point of skipping.
- MUST append the current item's `PracticeAttempt` to the progress log
  with no `sentence`/`feedback` fields (see `data-model.md`).
- MUST advance `step` directly to `"recall"` (more items remain) or
  `"complete"` (this was the last item) — it MUST NOT pass through
  `"feedback"` for this item.

Response (`200`): same shape as `GET /api/state` for whatever the new step
is — identical response contract to `POST /api/continue`.

Example — skipping mid-session:

```json
{
  "step": "recall",
  "chinese": "裁缝；定制",
  "warnings": []
}
```

Example — skipping the last item:

```json
{
  "step": "complete",
  "total": 3,
  "correct": 2,
  "warnings": []
}
```

(`total`/`correct` on the `"complete"` step were already added by the
session-tally feature; unchanged by this delta, and — per FR-006/FR-008 —
still accurate when the session includes skipped words.)

## `POST /api/sentence` — unaffected

This delta makes no change to `POST /api/sentence`. An empty or
whitespace-only `sentence` value sent to this endpoint directly (bypassing
the client's own check) is still accepted and processed exactly as today
— the confirmation/skip behavior is a client-side convenience layered in
front of this endpoint, not a new server-side validation rule on it. (A
future change could add server-side rejection of empty sentences if a
non-browser client needs the same guarantee; out of scope here since the
spec's actor is the existing web UI.)

## Out of scope for this delta

- No change to `POST /api/answer`, `GET /api/state`'s existing fields for
  `"recall"`/`"sentence"`/`"feedback"`, or `GET /`.
- No change to the sentence-review request/response contract
  (`specs/001-vocab-recall-tutor/contracts/ollama-correction-contract.md`).
- No change to the progress-log file format
  (`specs/001-vocab-recall-tutor/contracts/progress-log-format.md`) — the
  no-sentence shape it documents implicitly (via `PracticeAttempt`) already
  covers this.
- No CLI changes (`src/cli/session.py` is unaffected — see `spec.md`
  Assumptions).
