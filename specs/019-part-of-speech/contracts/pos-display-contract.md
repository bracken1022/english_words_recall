# Contract: Showing the Part of Speech

This covers FR-004, FR-005, SC-001 and the spec's Q1 answer: labels are
shown during recall, with the meaning.

## `GET /api/state`

`pos` (a list of labels) is present exactly when `chinese` is, that is
at steps `recall`, `reveal`, `sentence` and `feedback`. It is `[]` for a
word without labels. It is absent at `choose`, `complete` and `empty`.

## Web UI

| Where | Rendering |
|---|---|
| Recall prompt (`#chinese`), which stays on the reveal | `span.pos-list` **before** the meanings. Each label is a `span.pos` with `title` and `aria-label` set to its full name ("adjective"). |
| Sentence step and feedback (`#target-meaning` row) | The same `span.pos-list`, before the meaning text. |
| Import preview (spec 018) | The 中文 cell starts with the labels, or with a `span.badge-review` reading "Part of speech needs review" when `pos_review` is set. |

- **No labels**: a word with no labels renders no `span.pos-list` and
  leaves no empty gap.
- **Style**: italic, in the accent colour, smaller than the meaning,
  using existing tokens. On phones it stays on the same line as the
  meaning, wrapping if needed.
- **Grading**: nothing in grading, the answer input, or what counts as
  correct changes.

## Command-line tutor

The recall prompt is `Chinese meaning: adj. 热心的`. The labels come
first, separated by spaces; the meaning stays in bold. A word with no
labels prints exactly as today.
