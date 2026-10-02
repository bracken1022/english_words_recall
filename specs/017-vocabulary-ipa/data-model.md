# Data Model: IPA Pronunciation for Vocabulary

## VocabularyItem (existing — `src/models/vocabulary_item.py`)

| Field | Type | Change |
|---|---|---|
| `english` | str | unchanged |
| `chinese` | str | unchanged |
| `alternates` | list[str] | unchanged |
| `group` | str \| None | unchanged |
| **`ipa`** | str \| None | **new**, default `None`. Bare British IPA without slashes, e.g. `rɪˈsiːv`; for phrases, words separated by a space (`tend tə`). |
| **`ipa_problem`** | str \| None | **new**, `compare=False, repr=False`. Set when a block had an `ipa` value that failed validation; the item still loads with `ipa=None`. |

- `from_block(block)` reads `block.get("ipa")` through `normalize_ipa()`.
- `accepted_expressions()` is unchanged, so IPA never affects grading
  (FR-009).
- Display form: `display_ipa(ipa) -> f"/{ipa}/"`, which is `""` when
  `ipa` is `None`.

## IPA value rules (`src/lib/ipa.py::normalize_ipa`)

| Input | Result |
|---|---|
| missing key / `None` | `(None, None)` |
| `"rɪˈsiːv"`, `"/rɪˈsiːv/"`, `"[rɪˈsiːv]"`, `"  /rɪˈsiːv/ "` | `("rɪˈsiːv", None)` |
| non-string (e.g. YAML number `123`), `""`, `"//"`, `"123"`, no letter, contains an ASCII digit, > 100 chars | `(None, "ipa \"…\" is not a pronunciation")` |

Loader warning text: `<file>: '<english>': ipa "<raw>" is not a
pronunciation — shown without one`.

## Vocabulary block (file format — extends spec 001 contract)

```yaml
---
english: receive
ipa: rɪˈsiːv
alternates: [accept]
chinese: 收到；接受
group: unit1
---
```

`ipa` is optional and its position doesn't matter to the loader. The fill
tool and saved uploads place it right after `english`.

## Web state (extends `PracticeSession.state()`)

| Step | `ipa` key |
|---|---|
| `choose`, `empty`, `complete`, `recall` | **absent** |
| `sentence`, `feedback`, `reveal` | present: bare IPA string, or `null` |

## IPA mapping file (fill input — not committed)

`backups/ipa-<timestamp>/mapping.tsv`, UTF-8, one line per entry:

```text
<relative file path>\t<english>\t<ipa or empty>\t<note>
```

A key of (`file`, `english`) identifies the block. An empty IPA means
"leave this word without one" and must come with a note giving the
reason.

## Fill run outputs (`backups/ipa-<timestamp>/`)

- `files/…`: byte-for-byte copies of every file before editing.
- `REVIEW.md`:
  - counts (filled / already had / left empty / not in mapping);
  - a table of every word → `/ipa/` with notes;
  - the empty words with their reasons;
  - "Spot check these 30", a random sample, seeded by the timestamp, with
    blank ✓ columns.

## Relationships

```text
Vocabulary file 1 ── N blocks ── 1 VocabularyItem (0..1 ipa)
Mapping line ──(file, english)──▶ block   (fill only; one-time / on request)
PracticeSession.state() ──exposes ipa only after recall──▶ web UI
run_recall_step / run_sentence_step ──print ipa after reveal──▶ CLI
```
