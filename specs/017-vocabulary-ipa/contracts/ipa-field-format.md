# Contract: The `ipa` Field in Vocabulary and Uploads

Extends `specs/001-vocab-recall-tutor/contracts/vocabulary-markdown-format.md`
and `specs/016-per-user-word-lists/contracts/upload-formats.md`. Covers spec
FR-001, FR-002, FR-007, FR-008.

## Vocabulary Markdown (shared folder, personal lists, `.md` uploads)

| Field | Required | Type | Default |
|---|---|---|---|
| `ipa` | no | string, British IPA, with or without `/…/` or `[…]` | none |

```yaml
---
english: tend to
ipa: ˈtend tə
alternates: []
chinese: 倾向于；往往会
group: t-words
---
```

- Valid values are normalised to the bare transcription.
- An invalid value doesn't skip the block. The block loads with no
  pronunciation, and a warning is reported in the same channel as today's
  vocabulary warnings: `<file>: '<english>': ipa "<raw>" is not a
  pronunciation — shown without one`.
- In uploads, the same message appears in the upload result's `skipped`
  list, prefixed `block N:`, but the word still counts as added.

## Simple list uploads (`.csv` / `.txt` / `.tsv`)

After `English, Chinese`, any further field written as `/…/` or `[…]` is
the pronunciation. Other further fields are still extra accepted answers.

```text
receive, 收到；接受, /rɪˈsiːv/, accept
give up，放弃，/ˌɡɪv ˈʌp/
look up	查找	[lʊk ˈʌp]	search
```

- The pronunciation can appear in any position after field 2.
- A second pronunciation field on one line is ignored, with skip message
  `line N: more than one pronunciation — kept the first`. The word is
  still added.
- An invalid pronunciation, e.g. `/123/`, gives the word no IPA, with skip
  message `line N: "/123/" is not a pronunciation`. The word is still
  added.

## Saved personal lists

`word-lists/<username>/<name>.md` blocks are written in this key order:
`english`, `ipa` (only when present), `alternates`, `chinese`, `group`.

## Upload format hint (UI text)

`One word per line: receive, 收到 — add /rɪˈsiːv/ for the pronunciation —
or a .csv / .md file.`
