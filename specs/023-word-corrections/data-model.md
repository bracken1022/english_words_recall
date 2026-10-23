# Data Model: Automatic Word Corrections

## VocabularyItem (changed)

| Field | Change | Notes |
|---|---|---|
| `origin_chinese` | NEW, `str`, not compared | The meaning as written in the file, set by the loader before shared corrections are applied. Every key for a shared word (hidden words, `.examples.json`, `.corrections.json`) uses it (research R4). Defaults to `chinese`. |
| `ipa`, `chinese`, `pos` | unchanged type | May now be replaced by a correction: in the list file (own lists) or by the shared overlay at load time. |

`english`, `alternates`, `group`, `example`, `example_zh` are never
changed by a correction (FR-002).

## WordCheck (existing, `src/services/word_check.py`)

Qwen's validated answer for one word: `ipa` (bare IPA), `chinese`
(trimmed, ≤ 60 chars, family-safe), `pos` (labels from `POS_LABELS`,
non-empty). Changed by this feature:
- `check_word(..., dialect)`: `dialect` is `"british"` or `"american"`
  (research R3); it picks the prompt line and the IPA check
  (`check_british_ipa` / `check_american_ipa`), and a failing IPA
  rejects the whole answer.
- For a heteronym the answer's IPA is ignored and the current IPA kept.

## WordValues

The three checked fields of a word at one moment: `ipa: str | None`,
`chinese: str`, `pos: list[str]`. Compared after normalising (IPA without
slashes, parts of speech as labels, meaning trimmed).

## Fingerprint

`sha256("file|group|english|ipa|chinese|pos")` over a word's file name
(not its path), group, English and current `WordValues`, as hex. A word
is checked iff its fingerprint is in its folder's `checked` set
(research R6).

## CorrectionRecord

One saved change to one field of one word.

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Random, unique within the folder's file (12 hex chars). |
| `file` | `str` | The word's list file name (e.g. `T_words.md`). |
| `group` | `str \| null` | As in the file. |
| `english` | `str` | As in the file. |
| `origin_chinese` | `str` | Shared sets: the file's meaning (the overlay key). Own lists: the meaning before this correction. |
| `field` | `"ipa" \| "chinese" \| "pos"` | Only fields whose value changed get a record. |
| `old`, `new` | `str \| list[str] \| null` | Normalised values. |
| `at` | ISO 8601 UTC, seconds | When it was saved. |
| `undone_at` | ISO 8601 \| null | Set by an undo; never cleared. |
| `batch` | `str` | Same for all records saved by one check, so a word's changes are undone together. |

Records are kept newest first, at most 500 per folder; older ones are
dropped (the values stay corrected).

## Corrections file (`.corrections.json`, one per folder)

```text
{ "version": 1,
  "overlay": { "<file>|<group>|<english>|<origin_chinese>": WordValues },   # shared folder only
  "checked": [ "<fingerprint>", ... ],
  "records": [ CorrectionRecord, ... ] }
```

See [contracts/corrections-file.md](contracts/corrections-file.md). A
missing or unreadable file means "nothing checked, no overlay, no
records"; it is never fatal.

## CorrectionService state (in memory)

| Item | Purpose |
|---|---|
| per-word thread map | One check per word at a time (FR-006). |
| semaphore(2) | At most two checks at once overall (research R1). |
| `paused_until`, `pause_reason` | Research R8. `paused_until = inf` after `auth`. |
| `corrected_this_session` | Per item key: the fields corrected, for the reveal note (research R2). |

## State transitions (one word)

```text
unchecked ──prepare──▶ checking ──ok, values differ──▶ corrected (records saved, fingerprint of new values checked)
                          │      ──ok, values same────▶ checked   (fingerprint checked, no record)
                          │      ──word edited meanwhile▶ unchecked (nothing saved)
                          └──────failure──────────────▶ unchecked (retry next time; pause per R8)
corrected ──undo──▶ checked (old values back, their fingerprint checked; undone_at set)
checked / corrected ──word edited──▶ unchecked (fingerprint no longer matches)
```
