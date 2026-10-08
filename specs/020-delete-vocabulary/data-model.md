# Data Model: Remove Words I Don't Want to Recall

## VocabularyItem (existing)

| Field | Type | Notes |
|---|---|---|
| `source` | `Path \| None` | **New.** The file the item was loaded from, set by `load_vocabulary()`. `compare=False` and `repr=False`. Never used for grading. |

## RemovedEntry (`src/services/word_lists.py`)

What a removal from an own list leaves behind, kept only so it can be
undone.

| Field | Type | Notes |
|---|---|---|
| `path` | Path | Inside `word-lists/<username>/`. |
| `offset` | int | The character offset where the cut text started. |
| `text` | str | The exact text removed: the block plus one separator line. |
| `file_after` | str | The whole file's text right after the cut, used for an exact restore. |

## Hidden shared words (`word-lists/<username>/.hidden-shared.json`)

```json
{"version": 1, "hidden": [{"group": "t-words", "english": "tablet", "chinese": "药片"}]}
```

- **Writes**: the file is written atomically, under the account lock.
- **Invisibility**: the name doesn't end in `.md`, so the word-list
  store, the loaders and the word counts all ignore it.
- **Matching**: an entry matches a loaded shared item when `english` and
  `chinese` are equal, and `group` is equal, with `None` for an ungrouped
  word.

## PracticeSession (existing)

| New member | Notes |
|---|---|
| `item_filter` | An optional callable, `list[VocabularyItem] -> list[VocabularyItem]`, applied on every load (research R4). |
| `pending_undo` | `None`, or `(item, index_in_items, index_in_all_items, removal)`. Any other action clears it. |
| `remove_current(remove_fn) -> dict` | Valid at `recall`, `reveal` and `sentence` (research R5). |
| `undo_remove(restore_fn)` | Valid only while `pending_undo` is set. |

### Step changes

```text
recall   ──remove──► recall (next word)  |  complete (no words left)
reveal   ──remove──► (log held attempt) ► recall | complete
sentence ──remove──► (log attempt, as skip) ► recall | complete
any      ──undo────► recall (restored word is current)
```
