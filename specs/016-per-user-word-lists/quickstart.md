# Quickstart: Validate Personal Word Lists

Run from the repository root. Details:
[upload-formats](contracts/upload-formats.md),
[word-lists-api-contract](contracts/word-lists-api-contract.md),
[word-lists-ui-contract](contracts/word-lists-ui-contract.md),
[data-model](data-model.md).

## Prerequisites

- Spec 015 in place: `accounts.yml` with two accounts (e.g. `weibo`, `lily`).
- Use an isolated instance so real data isn't touched:

```bash
mkdir -p design/verification
.venv/bin/python -m src.web --vocab-dir design/fixtures/vocabulary \
  --progress-file design/verification/progress.md \
  --word-lists-dir design/verification/word-lists \
  --accounts-file accounts.yml --host 127.0.0.1 --port 8421
```

Banner includes `Word lists: design/verification/word-lists`.

Sample files:

```bash
printf 'English, Chinese\nreceive, 收到；接受, accept\ngive up，放弃\nbroken line\n' > /tmp/unit1.csv
cp vocabulary/T_words.md /tmp/T_words.md   # or any existing vocabulary .md
```

## 0. Automated tests

```bash
.venv/bin/pytest -q && .venv/bin/ruff check .
```

All new tests pass; every pre-existing test unchanged.

## 1. Upload a simple list (US1, FR-002/003)

Browser, logged in as `lily`: word-set screen shows "Practicing the shared
word sets…" → **Upload word list** → pick `/tmp/unit1.csv`.

Expected: "Added 2 words to “unit1”. Skipped 1: line 4: no Chinese
meaning", "From now on you'll practice your own lists."; the screen now
shows only the **unit1** set (2 words) — fixture sets are gone.

```bash
cat design/verification/word-lists/lily/unit1.md   # 2 blocks, group: unit1
```

## 2. Separate words (US2, SC-002)

Logged in as `weibo` (other browser/device): still sees the shared fixture
sets, no `unit1`. Upload `/tmp/T_words.md` → weibo sees only **T_words**.
Lily still sees only **unit1**. Practice a word in each; each history file
records only its own words (spec 015 files).

## 3. Markdown upload & rejects (FR-004, FR-010)

- Upload a `.xlsx` (any file renamed) → "Unsupported file type…", nothing
  added.
- Upload a `.txt` with only blank lines → "No words found…".
- Upload a > 1 MB file → "The file is larger than 1 MB."

## 4. Replace and delete (US3, FR-008/009)

1. As lily, start practicing **unit1**, answer one word, then on another
   device (also lily) upload an edited `unit1.csv` → confirm "Replace your
   list “unit1”?" → OK. First device's session continues unaffected; after
   it ends, **unit1** shows the new words.
2. Delete **unit1** → confirm → lily has no lists → word-set screen falls
   back to the shared fixture sets ("Practicing the shared word sets…").
3. `progress-lily.md` still contains every earlier attempt.

## 5. Isolation via API

```bash
# with weibo's cookie jar:
curl -s -b weibo.jar -X DELETE http://127.0.0.1:8421/api/word-lists/unit1   # 404 (lily's list)
curl -s -b weibo.jar -X DELETE 'http://127.0.0.1:8421/api/word-lists/..%2Flily%2Funit1'  # 404
curl -s -o /dev/null -w '%{http_code}\n' -F file=@/tmp/unit1.csv http://127.0.0.1:8421/api/word-lists  # 401, no login
```

## 6. Restart persistence (SC-004)

Restart the server, log in again → each account's lists are still there and
practicable.

## 7. CLI unchanged

`.venv/bin/python -m src.cli --vocab-dir vocabulary --mode recall-only`
behaves exactly as before (shared folder only, no uploads involved).
