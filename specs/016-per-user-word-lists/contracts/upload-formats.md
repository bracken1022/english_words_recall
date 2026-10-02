# Contract: Word-List Upload Formats

Parsed by `src/services/word_lists.py::parse_upload(filename, data)`.
Covers spec FR-002 – FR-004 and FR-010. The format is chosen by the file
extension, with case ignored.

| Extension | Format |
|---|---|
| `.md`, `.markdown` | Vocabulary Markdown |
| `.csv`, `.txt`, `.tsv` | Simple list |
| anything else | rejected: `Unsupported file type ".xlsx". Upload a .csv, .txt or .md file.` |

## Text decoding

The bytes are decoded as `utf-8-sig`. If that fails, they are decoded as
`gb18030`. If both fail, the upload is rejected with: `Couldn't read the
file's text. Save it as UTF-8 and try again.`

## A. Vocabulary Markdown

Same format as the shared vocabulary folder
(`specs/001-vocab-recall-tutor/contracts/vocabulary-markdown-format.md`):
`---`-delimited YAML blocks with `english`, `chinese` and optional
`alternates`. Any `group` value is ignored, because the list name becomes
the group (research R4). A block that fails to parse, or lacks `english` or
`chinese`, is skipped and reported as `block <n>: <reason>`, where `n`
counts the blocks found from 1.

## B. Simple list

One word per line:

```text
English, Chinese
receive, 收到；接受, accept
give up，放弃
look up	查找	search
"set off, start", 出发
```

- **Separators**: a tab, a comma `,`, or a full-width comma `，`. If a line
  contains a tab, tabs are the separators for that line. Otherwise both
  comma forms are separators. Fields may be quoted as in CSV (`"a, b"`).
- **Fields**:
  1. The English expression (required).
  2. The Chinese meaning (required). Use `；` to separate several meanings.
  3. Any further non-empty fields are extra accepted answers.

  Each field is trimmed.
- **Ignored**: blank lines and lines whose first character is `#`.
- **Header row**: if the first non-ignored row's first field is `english`,
  `word`, `英文` or `单词` (case-insensitive), that row is skipped.
- **Skipped lines** are reported as `line <n>: <reason>`, where `n` is the
  1-based line number in the file:
  - `line <n>: no Chinese meaning`, when there's one field or field 2 is
    empty;
  - `line <n>: no English word`, when field 1 is empty.

## Limits and results (both formats)

| Condition | Result |
|---|---|
| Upload body > 1 MiB | `413` `{"error": "The file is larger than 1 MB."}` |
| 0 valid words | `422` `{"error": "No words found. <format hint>", "skipped": [...], "skipped_count": n}`; nothing is saved |
| > 5,000 valid words | `422` `{"error": "That list has <n> words; the limit is 5,000."}`; nothing is saved |
| Otherwise | the list is saved; see `word-lists-api-contract.md` for the response |

The format hint is: `Use one word per line, like: receive, 收到 — or a .md
vocabulary file.`

At most 20 skip messages are returned, in file order. `skipped_count` is
always the full total.

## Saved form

Every list is saved as vocabulary Markdown in
`word-lists/<username>/<name>.md`, whatever format was uploaded. Each word
becomes one block, written with `yaml.safe_dump` (`allow_unicode=True`,
`sort_keys=False`) in this field order: `english`, `alternates`,
`chinese`, `group`, where `group` is the list name. YAML-1.1-boolean-looking
words such as `on`, `off` and `yes` come out quoted, so they round-trip as
text through the existing loader.
