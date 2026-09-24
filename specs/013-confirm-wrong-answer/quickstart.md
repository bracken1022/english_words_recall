# Quickstart: Require Confirmation Before Advancing Past a Wrong Recall-Only Answer

Validates that the feature described in `spec.md` works end-to-end, once
implemented per `plan.md`/`tasks.md`.

## Prerequisites

```bash
cd english-tutor
.venv/bin/pip install -e ".[dev]"
```

A scratch vocabulary with two words:

```bash
mkdir -p /tmp/confirm-wrong-vocab
cat > /tmp/confirm-wrong-vocab/words.md <<'EOF'
---
english: receive
chinese: 收到
group: unit1
---

---
english: mystery
chinese: 谜
group: unit1
---
EOF
```

## Scenario 1 — CLI, correct answer still auto-advances

```bash
printf 'receive\nmystery\n' | .venv/bin/python -m src.cli --vocab-dir /tmp/confirm-wrong-vocab --progress-file /tmp/confirm-wrong-progress.md --group unit1 --mode recall-only
```

**Expected**: both correct answers print `Correct!` and the session
moves straight to the next word / finishes, with no extra prompt —
unchanged from spec `012`.

## Scenario 2 — CLI, wrong answer waits for confirmation

```bash
printf 'wrongword\n\nmystery\n' | .venv/bin/python -m src.cli --vocab-dir /tmp/confirm-wrong-vocab --progress-file /tmp/confirm-wrong-progress2.md --group unit1 --mode recall-only
```

**Expected**: after the wrong answer, `Incorrect.` and the correct
expression print, then a "Press Enter to continue..." prompt appears and
blocks — only after the blank line is consumed does the session move on
to the next word.

## Scenario 3 — Web UI, correct answer still auto-advances

```bash
.venv/bin/python -m src.web --vocab-dir /tmp/confirm-wrong-vocab --progress-file /tmp/confirm-wrong-progress3.md --group unit1 --mode recall-only --port 8420
```

Open `http://localhost:8420/`, answer "receive" correctly.

**Expected**: the green "Correct: receive" stamp appears briefly, the
input disables, then the session automatically moves to the next word —
unchanged from spec `012`'s already-shipped behavior.

## Scenario 4 — Web UI, wrong answer waits for confirmation

Continuing the same session, answer "mystery" incorrectly (e.g. type
"wrong").

**Expected**: the red "Incorrect. The correct expression is: mystery"
stamp appears and a "Continue" button appears alongside it — the session
does **not** move on by itself, no matter how long you wait. Clicking
"Continue" then advances to session completion.

## Scenario 5 — Sentence mode is unaffected

```bash
.venv/bin/python -m src.web --vocab-dir /tmp/confirm-wrong-vocab --progress-file /tmp/confirm-wrong-progress4.md --group unit1 --port 8421
```

Open `http://localhost:8421/`, answer either word right or wrong.

**Expected**: today's existing sentence-mode flow, completely unchanged
— a sentence prompt always follows the recall answer, regardless of
whether it was correct.

## Automated coverage

See `plan.md`'s Project Structure for exact file paths:
- `tests/unit/test_session_state.py` — `submit_answer()`'s new `"reveal"`
  branch, `continue_to_next()`'s new `"reveal"` branch, and a regression
  test for the unchanged correct-answer path
- `tests/integration/test_session_mode.py` — CLI wrong-answer pause
- `tests/contract/test_web_api_contract.py` — `POST /api/continue` valid
  from `"reveal"`; a full wrong-then-continue flow through the test client
- `tests/unit/test_web_static_assets.py` — the moved Continue button and
  the new `app.js` branch

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src/
```

Both MUST pass, and Scenarios 1–5 above MUST be run manually before this
feature is considered done.
