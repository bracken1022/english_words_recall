# Quickstart: Validating Example Sentences

## 1. Automated tests

```bash
.venv/bin/python -m pytest && .venv/bin/ruff check src tests
```

The new tests cover:
- the word-form matching, the example validation and the content filter;
- the example client, against a mocked model;
- both example stores, including exact block edits;
- background preparation;
- the new step machine;
- the API routes, including that the removed ones return `404`;
- old history still loading;
- the UI strings.

## 2. Example quality (real local model)

```bash
.venv/bin/python -m src.tools.eval_examples --sample 50
```

The automatic pass rate is reported. Then tick `REVIEW.md`: at least 95%
should be natural, correct and in the right meaning, with 0 unsafe
(SC-002).

## 3. Manual check (temporary copy of data)

| # | Do | Expect | Result (2026-10-11) |
|---|---|---|---|
| a | The word-set screen | Three mode choices, and no "Sentence" option | ✅ modes are recall-only / example / example-recall; no `sentence` option |
| b | "Recall + example", answer a word | The answer and an example with its translation, within about 5 s on first sight | ✅ example ready 1.6 s after the answer (first sight, qwen3:14b) |
| c | The same word in a later session | The same example, shown instantly | ✅ same example, 0.00 s, no model call |
| d | New example | A different sentence replaces it, and stays next time | ✅ a different sentence, kept next session (first run found the model repeating the sentence; fixed — see below) |
| e | "Recall + example + sentence recall" | The translation, then Show sentence, then Got it; history has `sentence_recall: got` | ✅ translation only, then the sentence on reveal; history has `sentence_recall: got` |
| f | Stop Ollama, then practice a new word | "No example right now", and practice continues | ✅ `unavailable` → "No example right now.", Continue works (model URL made unreachable; the running Ollama was not stopped) |
| g | An old progress file with reviewed sentences | Still loads | ✅ a copy of the real `progress.md`: 4,649 attempts (206 with reviewed sentences), 0 warnings |
| h | CLI `--mode example-recall` | Example lines and the recall prompts | ✅ `Example:` line, `Recall the sentence:` prompt, `Did you get it? [y/n]`; `sentence_recall: got` logged |

Scenarios a–h were scripted against the real app and the real local model
(qwen3:14b) on temporary copies of `vocabulary/` and `progress.md`; the
originals' checksums were unchanged afterwards.

**Found and fixed in scenario d**: asked for a new example, the model
returned the same English sentence with a reworded translation. "New
example" now sends the current sentence to avoid
(`Write a different sentence from: "…"`), and a reply that repeats it
counts as invalid and is retried once
(`test_renew_never_repeats_the_old_sentence`,
`test_request_asks_for_a_different_sentence`).

**Visual check (T035)**: captured at 1280 and 390 px in
`design/verification/example/pass-0/` (choose, reveal with a ready /
pending / unavailable example, sentence recall before and after Show
sentence), on an isolated server with a scripted fake model. No fixes
needed: no horizontal scroll at 390 px; mode labels wrap to two lines
there, and "Remove this word" drops to its own row, both readable and
tappable.

