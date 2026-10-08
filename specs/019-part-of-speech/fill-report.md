# Part-of-Speech Fill Report (T028)

**Date**: 2026-10-05
**Tool**: `python -m src.tools.add_pos --mapping backups/pos-mapping.tsv vocabulary/*.md word-lists/*/*.md design/fixtures/vocabulary/sample.md`

## Result

`filled 715 · already had 0 · left empty 0 · missing from mapping 0`

| Folder | Words | With `pos` | Load warnings |
|---|---|---|---|
| `vocabulary/` (shared) | 182 | 182 | 0 |
| `word-lists/weibo/` | 482 | 482 | 0 |
| `word-lists/zhoudan/` | 47 | 47 | 0 |
| `design/fixtures/vocabulary/` (committed) | 4 | 4 | 0 |

- **Backups and review list**: the backups and the full review list are
  in `backups/pos-20261005-214924/`, which is gitignored.
- **Committed fixture**: `git diff design/fixtures` shows only `pos:`
  lines added.
- **How the words were classified**: the mapping has 533 unique
  (word, meaning) pairs. Each was classified from **its own recorded
  Chinese meanings**, with labels in meaning order.
- **Same spelling, different words**: *tense* (时态 → `n.`, 紧张的 →
  `adj.`) and *utter* (完全的 → `adj.`, 说出 → `v.`) are labelled per
  entry.
- **Noisy meanings** in uploaded lists (e.g. *rose*: 增加；上升; *reading*:
  （动词）读) are labelled by their main sense, with a note in the mapping.
- **Nothing left empty**: no word needed to be left empty; every set of
  meanings settled the class.

## Spot check (SC-006): at least 29 of 30 must match

Tick each against a learner's dictionary.

Check each against a learner's dictionary and the word's meanings, and tick it.

| Word | Part of speech | ✓ |
|---|---|---|
| waist | n. |  |
| wicked | adj. |  |
| unsatisfactory | adj. |  |
| refute | v. |  |
| tame | adj. |  |
| turnip | n. |  |
| tutor | n. |  |
| undo | v. |  |
| quiz | n. |  |
| responsibility | n. |  |
| residence | n. |  |
| slobber | v. n. |  |
| temple | n. |  |
| tense | adj. |  |
| regulation | n. |  |
| tropical | adj. |  |
| revolt | v. n. |  |
| qualify | v. |  |
| scanty | adj. |  |
| tense | adj. |  |
| recite | v. |  |
| race | n. |  |
| upward | adj. |  |
| reflexion | n. |  |
| stint | n. v. |  |
| rainy | adj. |  |
| undertaking | n. |  |
| rose | n. |  |
| rocket | n. v. |  |
| quarrel | n. v. |  |

