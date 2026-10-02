# Quickstart: Validate IPA Pronunciation

Run from the repository root. Details:
[ipa-field-format](contracts/ipa-field-format.md),
[ipa-display-contract](contracts/ipa-display-contract.md),
[add-ipa-tool-contract](contracts/add-ipa-tool-contract.md),
[data-model](data-model.md).

## 0. Automated tests

```bash
.venv/bin/pytest -q && .venv/bin/ruff check .
```

All new tests pass and all pre-existing tests are unchanged.

## 1. Fill the existing words (US2)

```bash
.venv/bin/python -m src.tools.add_ipa --mapping backups/ipa-mapping.tsv --dry-run \
  vocabulary/*.md word-lists/zhoudan/*.md design/fixtures/vocabulary/*.md
# expected: filled 233, already had 0, left empty ≤ 4 (each with a reason), missing 0
.venv/bin/python -m src.tools.add_ipa --mapping backups/ipa-mapping.tsv \
  vocabulary/*.md word-lists/zhoudan/*.md design/fixtures/vocabulary/*.md
```

Then check:

```bash
git diff --no-index --stat backups/ipa-*/files/vocabulary vocabulary   # only + lines
grep -c '^ipa:' vocabulary/*.md word-lists/zhoudan/*.md
```

Open `backups/ipa-*/REVIEW.md` and check the 30 sampled words against
Cambridge or Oxford Learner's Dictionaries (UK). At least 29 should match
(SC-002).

Run the tool again. It should report `already had` for every word and
change nothing.

## 2. Hidden during recall (FR-003)

Start the web UI with your usual flags and log in. On the recall screen,
no `/…/` is visible. `GET /api/state` at `step: "recall"` has no `ipa`
key.

## 3. Shown after reveal (US1, FR-004)

- Answer correctly: `/rɪˈsiːv/`-style IPA appears under the stamp.
- Answer wrongly, or press "Show answer": the IPA appears after the answer
  text.
- In sentence mode, the sentence step shows the IPA beside the target
  word, and the feedback screen shows it beside the word.
- Check at 390px: the IPA wraps under the word, and nothing scrolls
  horizontally.

## 4. CLI (US1 scenario 5)

```bash
.venv/bin/python -m src.cli --vocab-dir vocabulary --mode recall-only
```

After each answer, a `Pronunciation: /…/` line is printed. Nothing is
printed before answering.

## 5. Uploads with a pronunciation (US3)

Upload `ipa-test.csv` containing:

```text
receive, 收到, /rɪˈsiːv/, accept
bad one, 坏, /123/
```

Expected result: 2 added, and the skip message `line 2: "/123/" is not
a pronunciation`. Revealing *receive* shows `/rɪˈsiːv/`; revealing *bad
one* shows no pronunciation.

## 6. Malformed IPA in a hand-edited file (FR-008)

Add `ipa: 42` to one block in a scratch copy of a vocabulary folder and
start the CLI or web UI against it. A warning names the word, and the word
is still practisable without a pronunciation.
