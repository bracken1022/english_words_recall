# Quickstart: Validate Automatic Word Corrections

Use temp copies of learner data for every manual check: never the real
`vocabulary/`, `word-lists/` or `progress.md`. The shared vocabulary
`.md` files must be byte-for-byte unchanged at the end (SC-006).

## Prerequisites

- `DASHSCOPE_API_KEY` set in the shell that starts the app (optional:
  `QWEN_BASE_URL`, `QWEN_MODEL`). Without it, only scenario h applies.
- A temp data folder: a copy of `vocabulary/` and of one account's
  `word-lists/<account>/`, with a few words deliberately broken (a wrong
  meaning, a noun labelled `v.`, an American IPA in a British set).
- Note the shared files' checksums: `shasum vocabulary-copy/*.md`.

## Automated

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
```

Covers: word-check dialect and validation, fingerprints, the corrections
file (read/write, limits, bad files), the service (dedup, cap of two,
pause rules, compare-and-set, records, undo), the loader overlay and
`origin_chinese` keys (hidden words and examples still match), the API
contract, and the page wiring. Qwen is always faked.

## Manual scenarios

| # | Scenario | Expected |
|---|---|---|
| a | Own list: practise a word with a wrong part of speech; wait a few seconds before answering | At reveal the corrected part of speech shows with an "Updated" note; the list file has the new `pos`, the same English, alternates and example lines |
| b | Answer immediately (before the check can finish) | No waiting; the corrected values show the next time the word comes up |
| c | Practise a correct word | Nothing changes; no record |
| d | Practise the same words again (restart the app too) | No new requests (the server log / a request counter shows none) (SC-005) |
| e | Open Corrections | Each change: word, field, old → new, newest first |
| f | Undo a correction | Old values back in the file; the word comes up again without being re-sent or re-changed (SC-004) |
| g | Shared set, learner A practises a broken word; then log in as learner B | B sees the corrected value; the shared `.md` checksums are unchanged; `vocabulary/.corrections.json` has the overlay (SC-006) |
| h | Start without `DASHSCOPE_API_KEY` | Startup says `Corrections: off`; practice is unchanged; Corrections page says Qwen is not set up; earlier shared corrections still show |
| i | Start with a wrong key | Practice carries on; Corrections shows "Qwen rejected the API key." and no further requests are made |
| j | A British (shared or copied) word with a wrong IPA | The corrected IPA is British; an American answer is rejected |
| k | Remove a corrected shared word (spec 020), then undo the remove | The word hides and comes back correctly (keys use the file meaning) |
| l | A shared word with a saved example gets its meaning corrected | Its example still shows (not regenerated) |

## Quality (SC-001, SC-002)

```sh
.venv/bin/python -m src.tools.eval_corrections tests/fixtures/word_check_cases.yml
```

Pass: ≥ 90% of the known errors fixed and ≤ 5% of the right words made
worse. Record the result in `eval-report.md`.
