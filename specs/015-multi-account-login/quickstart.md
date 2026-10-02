# Quickstart: Validate Multiple Learner Accounts

Run from the repository root. Formats and endpoint details:
[accounts-file-format](contracts/accounts-file-format.md),
[web-auth-api-contract](contracts/web-auth-api-contract.md),
[login-ui-contract](contracts/login-ui-contract.md),
[data-model](data-model.md).

## Prerequisites

- `.venv` set up per README (`.venv/bin/pip install -e ".[dev]"`).
- A vocabulary folder (the README's `./vocabulary/`, or
  `design/fixtures/vocabulary/`).
- Ollama is only needed for scenario 3's sentence step; recall-only works
  without it.

## 0. Automated tests

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

Expected: all tests pass, including the new account, login-guard, and
isolation tests, and every pre-existing test unchanged.

## 1. Configure accounts

```bash
cp accounts.example.yml accounts.yml
# edit accounts.yml: two accounts, e.g. weibo (first) and lily
```

Start the web UI:

```bash
.venv/bin/python -m src.web --vocab-dir vocabulary --progress-file progress.md
```

Expected banner includes
`Accounts: weibo → progress.md, lily → progress-lily.md`. No password
appears anywhere in the output.

## 2. Login is required (US1, FR-002, FR-011)

```bash
curl -s -i http://localhost:8420/api/state | head -1        # HTTP/1.1 401
curl -s -i -X POST http://localhost:8420/api/answer \
  -H 'Content-Type: application/json' -d '{"answer":"x"}' | head -1   # 401
```

Expected: both `401`; `progress.md` is unchanged. In a browser, opening
`http://localhost:8420/` shows only the login screen.

## 3. Separate histories (US1, SC-002)

1. In the browser, log in as `Weibo ` (capital, trailing space) with the
   right password → word-set screen, header shows "Weibo".
2. Practice two words (one right, one wrong), then **Log out**.
3. Log in as `lily` → word-set screen, header shows "Lily". Practice one
   word.
4. Check files:

```bash
tail -n 20 progress.md        # weibo's 2 new attempts, none of lily's
cat progress-lily.md          # exactly lily's 1 attempt
```

## 4. Wrong credentials (edge cases, FR-004)

- Wrong password for `weibo` and an unknown username `nobody` both show
  "Username or password is incorrect" and stay on the login screen.
- Submitting with an empty field shows "Enter both a username and a
  password" and sends no request.

## 5. Practicing at the same time (US2, SC-003)

1. Device/browser A (or a private window): log in as `weibo`, pick a
   collection, **Random** order.
2. Device/browser B: log in as `lily`, pick a different collection,
   **Sequential**, recall-only.
3. Alternate ~10 answers each. Expected: each side's word counter, score,
   and collection only move when that side acts; reloading either page
   resumes that learner's own word.

## 6. Logout and stay-logged-in (US3, FR-009, FR-010)

1. Logged in as `weibo`, answer a word correctly so you're on the sentence
   step, then **Log out**. Expected: login screen; `progress.md` gains no
   new attempt for that word.
2. Log in as `weibo` again → word-set screen (fresh session).
3. Close and reopen the browser (server still running) → still logged in.
4. Restart the server → the page shows the login screen; histories intact.

## 7. Start-up validation (FR-013)

```bash
mv accounts.yml /tmp/accounts.bak
.venv/bin/python -m src.web; echo "exit=$?"     # message names accounts.example.yml, exit=2
mv /tmp/accounts.bak accounts.yml
```

Also try a duplicated username (`Lily` and `lily`) → start-up refuses and
names `lily`.

## 8. CLI unchanged (FR-014)

```bash
.venv/bin/python -m src.cli --vocab-dir vocabulary --progress-file progress.md --mode recall-only
```

Expected: no login prompt; behaves exactly as before.
