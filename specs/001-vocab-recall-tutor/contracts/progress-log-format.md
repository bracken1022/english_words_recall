# Contract: Progress Log Markdown Format

Written and read by `services/progress_log.py` via the same
`lib/markdown_blocks.py` helper used for vocabulary files. Covers FR-011 and
the read side of SC-005.

## File shape

A single file, `progress.md`, in the configured progress directory. Every
completed PracticeAttempt is **appended** as one `---`-delimited YAML block:

```markdown
---
timestamp: 2026-09-18T10:15:32
item: receive
answer: recieve
correct: false
sentence: I recieve a gift yesterday.
feedback: "corrected: I received a gift yesterday. (past tense needed)"
---
```

- Blocks are appended in the order attempts complete; the file is never
  rewritten or reordered by the app, only appended to.
- `sentence` and `feedback` are both omitted from the block entirely (not
  written as empty strings) when the sentence-correction step never completed
  for that attempt (e.g., the learner's process was interrupted before it —
  out of this feature's required scenarios, but the format tolerates it).

## Field contract

| Field | Required | Type | Notes |
|---|---|---|---|
| `timestamp` | yes | ISO-8601 string | Local time is acceptable; must be parseable. |
| `item` | yes | string | The `english` value of the VocabularyItem practiced. |
| `answer` | yes | string | May be an empty string (`""`), never absent. |
| `correct` | yes | boolean | Result of exact-match grading. |
| `sentence` | no | string | Present iff the sentence step was reached. |
| `feedback` | no | string | Present iff the sentence step resolved (including "correction unavailable" as a valid feedback value). |

## Error handling

- On read, a block that fails to parse, or is missing `timestamp`/`item`/
  `answer`/`correct`, is skipped with a reported warning — the rest of the log
  remains readable (mirrors the vocabulary-file contract's tolerance).
- Because writes are append-only, a parse failure on read can only affect a
  block that was itself corrupted after the fact (e.g., manual editing); it
  never affects attempts recorded before or after it.

## Non-goals

- No pruning, rotation, or size limit (per spec Assumptions).
- No cross-referencing back into the vocabulary files by anything other than
  the `item` string — the log stays self-contained and readable even if the
  vocabulary set later changes.
