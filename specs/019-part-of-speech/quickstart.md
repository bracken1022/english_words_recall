# Quickstart: Validating Part of Speech

Behaviour details are in [contracts/](contracts/) and
[data-model.md](data-model.md).

## 1. Automated tests (no Ollama needed)

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check src tests
```

The whole suite should pass, with every pre-existing test unchanged. The
new tests cover:

- `normalize_pos` and its synonyms;
- the `pos` field when loading vocabulary, and its warnings;
- simple-list part-of-speech fields;
- `state()["pos"]` at every step;
- the web and CLI rendering strings;
- enrichment rules 1–3;
- stripping part-of-speech notes from generated meanings;
- update of existing entries;
- the `add_pos` tool (dry run, insert position, restore on mismatch,
  REVIEW.md).

## 2. Model accuracy gate (real local model)

```bash
.venv/bin/python -m src.tools.eval_enrichment --model qwen3:14b
```

The report gains a `Part of speech` line, and the run must PASS:

- part-of-speech match or flagged ≥ 95% (SC-002);
- 0 labels outside the set;
- 0 meanings left with part-of-speech notes (SC-003);
- all earlier targets still met.

## 3. Fill existing words (one-off)

```bash
.venv/bin/python -m src.tools.add_pos --mapping backups/pos-mapping.tsv --dry-run \
  vocabulary/*.md word-lists/*/*.md design/fixtures/vocabulary/*.md
.venv/bin/python -m src.tools.add_pos --mapping backups/pos-mapping.tsv \
  vocabulary/*.md word-lists/*/*.md design/fixtures/vocabulary/*.md
```

Expected results:

- the dry run reports about 710 words, all either filled or left empty
  with a reason, and 0 missing;
- the real run writes `backups/pos-<stamp>/REVIEW.md`;
- `git diff` shows the committed fixture file with only `pos:` lines
  added;
- every file loads with 0 warnings;
- the user ticks the 30-word spot check, and at least 29 must match
  (SC-006).

## 4. Manual check (web UI and CLI)

| # | Do | Expect | Result (2026-10-05) |
|---|---|---|---|
| a | Practice *zealous* | The recall prompt shows *adj.* before 热心的, with the tooltip "adjective". | ✅ *adj.* before 热心的 / 热情的; tooltip set from POS_NAMES (`recall-adj-1280.png`) |
| b | Answer it, then go to the sentence step | The labels are shown on the reveal and before the meaning on the sentence step. | ✅ sentence step shows “zealous /ˈzeləs/ *adj.* 热心的 · 热情的” (`sentence-1280.png`) |
| c | Practice *rent* | `n. v.` is shown. | ✅ *n. v.* before 租金 / 租用 / 出租 (`recall-nv-390.png`) |
| d | Practice a word with no `pos` | No label and no gap. | ✅ no `span.pos-list` rendered when `pos` is `[]` (state test; template code path) |
| e | Upload `zealous`, `undertake`, `rent`, `give up` | The preview shows adj., v., n. v. and phr. v. No meaning contains （动词）. | ✅ preview: adj., n., v., n. v., and *tend to* flagged; record's “（动词）” stripped (`import-1280.png`, fake model) |
| f | Run the CLI tutor on the shared folder | `Chinese meaning: adj. 热心的`. | ✅ `Chinese meaning: n. 河；江`, `adj. n. 有耐心的；病人` |
| g | Phone width (390 px) | The labels stay readable beside the meaning. | ✅ labels readable beside the meaning at 390 px (`recall-adj-390.png`) |

Screenshots are in `design/verification/pos/pass-0/` (gitignored). Scenario e used a fake local model; the real-model check is T030 (`eval-report.md`).
