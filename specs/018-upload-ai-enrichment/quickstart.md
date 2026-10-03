# Quickstart: Validating Local-AI Enrichment of Uploads

This guide is a set of runnable checks that the feature works end to end.
The behaviour details are in [contracts/](contracts/) and
[data-model.md](data-model.md).

## Prerequisites

```bash
pip install -e '.[dev]'
ollama serve              # in another terminal
ollama pull qwen3:14b     # or whatever --model you run with
cp accounts.example.yml accounts.yml   # if not done already
```

## 1. Automated tests (mocked model, no Ollama needed)

```bash
pytest
```

Expected results:

- The whole suite passes, including **every pre-existing test unchanged**
  (SC-008).
- The new tests cover:
  - validation rules;
  - the alternates filter traps;
  - heteronym and acronym flags;
  - the American IPA checker;
  - pending-file restart recovery;
  - per-item failure and model-unavailable handling;
  - duplicate-start prevention;
  - existing-entry keep/update;
  - all-or-nothing confirm with an injected I/O failure;
  - account isolation.

```bash
ruff check src tests
```

## 2. Model quality evaluation (real local model, Constitution II)

```bash
python -m src.tools.eval_enrichment --model qwen3:14b
```

The tool reads `tests/fixtures/enrichment_eval.yml` and runs each word
through the full enrich→validate pipeline. The report must show:

- **IPA**: at least 95% match the reviewed transcription, and every
  non-match is flagged as "needs review" rather than wrong (SC-002);
- **Synonym traps**: 0 leaked (SC-003);
- **Spelling variants**: the expected alternate found at least 90% of the
  time (SC-003);
- **Invalid output written**: 0 (SC-002).

## 3. Manual end-to-end check (web UI)

```bash
python -m src.web --model qwen3:14b
```

Log in, open the word-set screen, and work through these scenarios.

| # | Do | Expect | Result (2026-10-03, real qwen3:14b) |
|---|---|---|---|
| a | Upload `z-words.txt` with 10 bare words (zealous, tyre, epitomise, arduous, record, NASA, tend to, colour, receive, zealous) | The status shows "Enriching vocabulary: n / 9", counting up one at a time. The second "zealous" is shown as "Repeated". | ✅ total 9, progress counted 0→9, the repeated word was marked |
| b | Wait for completion | tyre gets alt `tire`; epitomise gets `epitomize`; colour gets `color`; arduous gets alternates `none`, with any dropped synonym shown as "not used". record and NASA show "Pronunciation needs review". Other IPA comes from the offline dictionary in NAmE style. | ✅ tire, epitomize, color; arduous had no alternates; record and NASA flagged; IPA from the dictionary (tyre ˈtaɪər, arduous ˈɑːrdʒuəs) |
| c | Before uploading, have an own list containing `receive` | receive is marked "Already in your words (“unit1”)" with "Keep mine" selected. | ✅ marked “unit1”, Keep mine |
| d | Press Save, then open My word lists | `z-words` is listed. `word-lists/<user>/z-words.md` has blocks in the order `english, ipa?, alternates, chinese, group: z-words`, with no `ipa` key for record and NASA. `unit1.md` is byte-identical (check with `shasum` before and after). | ✅ 8 added, 1 left out (receive kept); unit1.md byte-identical |
| e | Stop Ollama, then upload another file | "Local AI unavailable — start Ollama, then press Retry." The words are shown as Waiting, and no `.md` file changed. | ✅ an unreachable model URL gave the message; words waiting; no new .md |
| f | Start Ollama, then press Retry | Enrichment continues from where it stopped. | ✅ completed after Retry |
| g | Mid-run, restart the server and reload the page | The import shows "interrupted at n / total". Retry continues. | ✅ import survived a new app instance; Retry finished it |
| h | Double-click Save, or press Retry in two tabs | One save and one batch only. | ✅ second confirm → 404; one batch per import (unit tests) |
| i | Practice `z-words` | Recall, reveal (shows American IPA), sentence review and progress logging behave as before. | ✅ recall correct, IPA ˈzeləs shown |
| j | Log in as a second account | That account sees none of the first account's pending import or lists. | ✅ second account sees nothing |

## 4. Visual check

Follow `.claude/skills/frontend-design` → visual-verification: take
screenshots of the panel in its running, partially-failed and preview
states at desktop and phone widths. Confirm that the upload button, the
hint position and the "My word lists" section look as before.

The scenarios were run with a scratch script that calls the real app and
the real local model through Flask's test client, in a temporary folder.
Scenario e used an unreachable model URL instead of stopping the
developer's Ollama. The visual states were checked separately (T054,
`design/verification/import-panel/`).
