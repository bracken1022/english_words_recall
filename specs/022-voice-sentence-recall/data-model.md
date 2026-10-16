# Data Model: Voice Answers for Sentence Recall

Nothing in this feature is saved. The practice history, word lists and
example stores are unchanged (SC-006).

## TranscriptionResult (in memory, `src/services/speech_client.py`)

| Field | Type | Rules |
|---|---|---|
| `outcome` | `"ok"` \| `"nothing_heard"` \| `"unavailable"` | `ok` only when `text` is non-empty after trimming. `nothing_heard`: the recogniser ran but found no speech. `unavailable`: package missing, model failed to load, or the audio couldn't be decoded. |
| `text` | `str \| None` | Set only for `ok`. Never logged or stored. |

The audio bytes exist only for the length of one `/api/transcribe`
request.

## WordMark (in memory, `src/lib/word_diff.py`)

| Field | Type | Rules |
|---|---|---|
| `word` | `str` | The word as written, with its punctuation (for display). |
| `status` | `"same"` \| `"missing"` \| `"extra"` | `missing` appears only in the sentence list, `extra` only in the attempt list. |

## AttemptComparison (in memory, returned once at reveal)

| Field | Type | Rules |
|---|---|---|
| `sentence` | `list[WordMark]` | One entry per word of the real sentence, in order; each `same` or `missing`. |
| `attempt` | `list[WordMark]` | One entry per word of the attempt, in order; each `same` or `extra`. |

- `compare(attempt, sentence)` returns `None` for an attempt that is
  empty after trimming (nothing is highlighted).
- Words are compared after normalising (`contracts/word-diff.md`); two
  texts that differ only in capitals and punctuation give all `same`.
- Built only for the reveal reply; not kept in the session, the history
  or any log.

## Practice session (existing, `src/web/session_state.py`)

No new stored fields. Two read-only checks are added:

- `can_transcribe()`: true only at step `sentence-recall` with
  `sentence_revealed` false.
- The reveal action accepts an optional attempt and returns the
  comparison alongside the state, without keeping the attempt.

`GET /api/state` gains `voice_available` (bool) at the `sentence-recall`
step: true when the recogniser package is installed.

## State transitions

Unchanged from spec 021. Recording and transcription happen inside the
`sentence-recall` step before reveal and never move the step:

```text
sentence-recall (hidden) ──record/transcribe (0..n times)──▶ sentence-recall (hidden)
sentence-recall (hidden) ──reveal (+ attempt)──▶ sentence-recall (revealed, comparison shown once)
sentence-recall ──got / not_yet / skip──▶ next word or complete
```
