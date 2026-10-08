# Data Model: Part of Speech for Vocabulary

## Part-of-speech label (`src/lib/pos.py`)

The fixed set, from FR-002, in display form, with full names:

| Label | Name | Label | Name |
|---|---|---|---|
| `n.` | noun | `pron.` | pronoun |
| `v.` | verb | `det.` | determiner |
| `adj.` | adjective | `int.` | interjection |
| `adv.` | adverb | `num.` | number |
| `prep.` | preposition | `phr. v.` | phrasal verb |
| `conj.` | conjunction | `phr.` | phrase or idiom |

`normalize_pos(raw) -> (list[str] | None, str | None)` turns a raw value
into a non-empty, ordered, duplicate-free list of labels, or reports a
problem. Accepted spellings are listed in research R2.

## VocabularyItem (`src/models/vocabulary_item.py`)

Existing fields are unchanged. New fields:

| Field | Type | Notes |
|---|---|---|
| `pos` | `list[str]` | Labels in display form; `[]` when there are none. Not used in grading or `accepted_expressions()`. |
| `pos_problem` | `str \| None` | Why a block's `pos` was rejected. `compare=False` and `repr=False`, like `ipa_problem`. |

`from_block()` reads `pos` through `normalize_pos`. A problem gives `pos = []`
and a loader warning:
`<file>: '<english>': pos "<raw>" is not a part of speech — shown without one`.

## Vocabulary Markdown

- The `pos` key is optional ([contracts/pos-field-format.md](contracts/pos-field-format.md)).
- Key order when a tool writes a block: `english`, `ipa`, `pos`,
  `alternates`, `chinese`, `group`.

## DraftWord (spec 018)

Gains `pos: list[str]`, which is what the upload supplied, or `[]`.

## ImportItem (spec 018, pending import)

| Field | Type | Notes |
|---|---|---|
| `pos` | `list[str]` | The final labels, supplied or generated, after validation. Defaults to `[]`. |
| `pos_review` | `str \| None` | `"part of speech needs review"` when the generated labels were missing or invalid. |

`supplied` may now hold `pos`. Both new fields default, so pending files
written before this feature still load (research R7). The update map for
existing entries includes `pos`.

## EnrichmentReply (spec 018)

Gains `pos: list[str]`, read from the reply's `pos` array of strings.
It is untrusted until `validate_item` normalises it.

## Fill review (one-off)

`backups/pos-<stamp>/REVIEW.md` lists:

- every filled word with its labels;
- the words left empty, with the reason;
- the mapping entries that matched no word;
- a 30-word spot-check sample.
