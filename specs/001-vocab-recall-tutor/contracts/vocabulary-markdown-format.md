# Contract: Vocabulary Markdown File Format

Read by `services/vocabulary_loader.py` via `lib/markdown_blocks.py`. This is
the format any person authoring vocabulary content must follow (FR-001,
FR-012, FR-013).

## File shape

A vocabulary Markdown file (any `.md` file under the configured vocabulary
directory) contains zero or more blocks, each delimited by a line containing
only `---` before and after, with YAML inside:

```markdown
---
english: receive
alternates: [accept]
chinese: 收到；接受
group: unit1
---

---
english: give up
chinese: 放弃
group: unit1
---
```

- Blocks may be separated by any amount of surrounding prose/whitespace; only
  the `---`-delimited YAML content is parsed as data. This allows an author to
  add commentary/notes in the same file without breaking parsing.
- Multiple files may exist in the vocabulary directory; all are loaded and
  combined into one pool before any `group` filtering is applied.

## Field contract

| Field | Required | Type | Default if absent |
|---|---|---|---|
| `english` | **yes** | string | — block is invalid without it |
| `chinese` | **yes** | string | — block is invalid without it |
| `alternates` | no | list of strings | `[]` |
| `group` | no | string | `null` (only included when the learner selects "all") |

## Error handling (FR-013)

- A block that fails to parse as YAML, or parses but is missing `english` or
  `chinese`, is **skipped**. Loading continues with the remaining blocks in
  the same file and other files.
- Each skipped block produces one human-readable warning identifying the file
  and, where possible, a snippet of the offending block — surfaced to the
  learner/author, not silently swallowed.
- An empty vocabulary directory, or a directory where every block fails to
  parse, results in an empty vocabulary pool — the session start behavior for
  that case is defined in `quickstart.md` / the corresponding edge-case task,
  not in this file-format contract.

## Non-goals

- No enforced file-naming convention; `group` is the only supported way to
  organize items (a file may hold one lesson or many).
- No schema versioning — this is a v1, single-project format.
