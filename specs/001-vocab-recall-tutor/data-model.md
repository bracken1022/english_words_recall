# Data Model: Vocabulary Recall Tutor

Derived from the spec's Key Entities. No database — every entity below maps
directly to a Markdown block on disk (see `contracts/` for the exact file
formats).

## VocabularyItem

Represents one English expression to learn.

| Field | Type | Required | Notes |
|---|---|---|---|
| `english` | string | yes | The target English expression; unique *within* one lesson/group, but the same expression MAY recur across groups with a different `chinese` meaning (not an error — matching is always scoped to the currently presented item, per FR-004). |
| `alternates` | list[string] | no | Additional accepted English forms (synonyms/variants). Defaults to empty list. |
| `chinese` | string | yes | The Chinese meaning shown to the learner before recall. |
| `group` | string | no | Lesson/unit tag used for session filtering (FR-015). Items without a `group` are only included when the learner selects "all". |

**Validation rules** (FR-013): a block missing `english` or `chinese` is
invalid and MUST be skipped with a reported warning; `alternates` and `group`
are optional and default to empty/none rather than causing a validation
failure.

**Lifecycle**: read-only at runtime; created/edited only by a person directly
editing a vocabulary Markdown file (FR-012). No in-app create/update/delete.

## PracticeAttempt

Represents one learner interaction with one VocabularyItem, in one of two
recall states (correct/incorrect) plus its downstream sentence-correction
outcome.

| Field | Type | Required | Notes |
|---|---|---|---|
| `timestamp` | ISO-8601 datetime string | yes | When the attempt was recorded. |
| `item` | string | yes | The `english` value of the VocabularyItem practiced. |
| `answer` | string | yes | What the learner typed for recall; empty string is valid (FR-004 acceptance scenario 4). |
| `correct` | boolean | yes | Result of the exact-match grading (FR-004). |
| `sentence` | string | no | The learner's original sentence using the expression; absent if the LLM step could not be completed for any reason. |
| `feedback` | string | no | Short summary of the LLM's correction outcome (e.g., "already correct", "corrected: ...", or "correction unavailable"). Absent under the same condition as `sentence`. |

**Validation rules**: `correct` is always present and boolean, since recall
grading never depends on the LLM. `sentence`/`feedback` are both present or
both absent together — the sentence step either completed (however the LLM
judged it, including "unavailable") or never happened.

**Lifecycle**: append-only. A PracticeAttempt is written once, immediately
after the sentence-correction step resolves (or is skipped), and is never
edited or deleted by the app afterward (manual edits by the learner are
tolerated per the malformed-entry handling below, not required).

## LearnerProgressLog

The ordered collection of all PracticeAttempts for this learner, persisted as
`progress.md`.

| Field | Type | Notes |
|---|---|---|
| `attempts` | list[PracticeAttempt] | Ordered by append time (oldest first). |

**Validation rules**: on load, each attempt block is parsed independently; a
block that fails to parse is skipped with a reported warning (same tolerance
pattern as VocabularyItem, FR-013) rather than blocking access to the rest of
the log — this is what lets a manually-edited file recover gracefully.

**Lifecycle**: append-only across the tool's entire lifetime; no pruning,
rotation, or size cap (per spec Assumptions).

## Relationships

```text
VocabularyItem (1) ──practiced-in──> (0..N) PracticeAttempt
PracticeAttempt (N) ──appended-to──> (1) LearnerProgressLog
```

A PracticeAttempt references its VocabularyItem by `english` value (a string
match), not by a database foreign key — if the referenced item is later
removed from the vocabulary files, the PracticeAttempt record remains valid
and readable on its own (SC-005 requires the log to be self-contained).

## Runtime-only concept: Practice Session

Not persisted as its own entity. At runtime, starting a session means: (1)
load all VocabularyItems, (2) apply the optional group filter (FR-015), (3)
walk the resulting list strictly forward, one item at a time, with no skip/back
(FR-016). A session's attempts are written to the LearnerProgressLog as they
happen; there is no separate "session record" file.
