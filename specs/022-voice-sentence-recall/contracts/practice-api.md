# Contract: Practice API Changes (web)

All routes keep the existing login guard (`401 {"error": "login
required"}` when signed out).

## `GET /api/state` at `sentence-recall`

Adds `voice_available`:

```json
{"step": "sentence-recall", "sentence_revealed": false,
 "example": {"sentence": null, "translation": "她是当地球队的狂热支持者。"},
 "voice_available": true}
```

`voice_available` is `true` when the speech recogniser is installed.
Other steps don't include it.

## `POST /api/transcribe` (new)

- **Body**: the raw recording (`Content-Type` such as `audio/webm`,
  `audio/mp4`, `audio/ogg`). At most 1 MB.
- **Allowed only** at `sentence-recall` before the sentence is revealed.

| Case | Status | Body |
|---|---|---|
| Speech recognised | `200` | `{"outcome": "ok", "text": "She is a zealous supporter of the team."}` |
| Nothing heard | `200` | `{"outcome": "nothing_heard", "text": null}` |
| Recogniser missing, model failed, audio undecodable | `200` | `{"outcome": "unavailable", "text": null}` |
| Empty body | `400` | `{"error": "No recording received."}` |
| Over 1 MB | `413` | `{"error": "The recording is too long."}` |
| Wrong step, or sentence already revealed | `409` | `{"error": "Voice is only for recalling a sentence."}` |

Guarantees:
- The audio is never written to disk, logged or kept after the request.
- The recognised text is not logged or stored; it is only returned.
- The real sentence is never used in recognition (research R2).
- The session's step and state are unchanged by this call.

## `POST /api/sentence-recall` with `reveal`

The body may now include the learner's attempt:

```json
{"mark": "reveal", "attempt": "She is a zelous supporter of team"}
```

- `attempt` is optional; it must be a string of at most 1000 characters
  (`400` otherwise). It is used only to build `comparison` and is then
  dropped (not stored, not logged, not in later `GET /api/state`).
- The reply is the state (as before) plus `comparison`:

```json
{"step": "sentence-recall", "sentence_revealed": true,
 "example": {"sentence": "She is a zealous supporter of the team.", "translation": "…"},
 "comparison": {
   "sentence": [{"word": "She", "status": "same"}, {"word": "is", "status": "same"},
                {"word": "a", "status": "same"}, {"word": "zealous", "status": "missing"},
                {"word": "supporter", "status": "same"}, {"word": "of", "status": "same"},
                {"word": "the", "status": "missing"}, {"word": "team.", "status": "same"}],
   "attempt":  [{"word": "She", "status": "same"}, {"word": "is", "status": "same"},
                {"word": "a", "status": "same"}, {"word": "zelous", "status": "extra"},
                {"word": "supporter", "status": "same"}, {"word": "of", "status": "same"},
                {"word": "team", "status": "same"}]}}
```

- `comparison` is `null` when the attempt is missing or blank.
- `got`, `not_yet` and `skip` ignore any `attempt` and behave as in
  spec 021; the history still records only the mark.
