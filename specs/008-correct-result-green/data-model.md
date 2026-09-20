# Data Model: Show a Correct Recall Result in Green

No entities, no storage, no state-machine changes. This feature changes
the presentation of an outcome (`correct: true`/`false`) that already
exists and is already computed elsewhere (`matcher.grade_answer`,
unchanged) — it adds no new data of its own.

## Existing values this feature reads (unchanged)

| Source | Field | Used for |
|---|---|---|
| `GET /api/state` (`"sentence"`/`"feedback"` steps) | `correct` (bool) | `app.js`'s existing `renderWordFeedback()` already toggles `.feedback-correct`/`.feedback-incorrect` on `#word-feedback` from this field (spec `004`) — this feature only changes what those two classes look like |

No field, endpoint, or file format is added, renamed, or removed.
