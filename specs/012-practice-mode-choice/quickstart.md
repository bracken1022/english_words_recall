# Quickstart: Choose Recall-Only or Sentence Practice Mode

Validates that the feature described in `spec.md` works end-to-end, once
implemented per `plan.md`/`tasks.md`.

## Prerequisites

```bash
cd english-tutor
.venv/bin/pip install -e ".[dev]"
```

A scratch vocabulary with a couple of words:

```bash
mkdir -p /tmp/mode-quickstart-vocab
cat > /tmp/mode-quickstart-vocab/words.md <<'EOF'
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

## Scenario 1 — CLI, sentence mode (unchanged default)

```bash
.venv/bin/python -m src.cli --vocab-dir /tmp/mode-quickstart-vocab --progress-file /tmp/mode-quickstart-progress.md --group unit1
```

**Expected**: a sentence prompt appears after each word, exactly as
today — no change in behavior.

## Scenario 2 — CLI, recall-only mode

```bash
.venv/bin/python -m src.cli --vocab-dir /tmp/mode-quickstart-vocab --progress-file /tmp/mode-quickstart-progress2.md --group unit1 --mode recall-only
```

**Expected**: after answering each word and seeing whether it was
correct, the session moves straight to the next word (or ends) — no
sentence prompt appears at all, and no local LLM/correction call is
made (this works even if Ollama isn't running).

## Scenario 3 — Web UI, interactive picker offers mode alongside collection and order

```bash
.venv/bin/python -m src.web --vocab-dir /tmp/mode-quickstart-vocab --progress-file /tmp/mode-quickstart-progress3.md --port 8420
```

Open `http://localhost:8420/`.

1. **Expected**: the choose screen now shows a mode toggle
   (Sentence/Recall-only), defaulting to Sentence, alongside the
   existing order toggle and collection list.
2. Select Recall-only, then pick "unit1".
3. **Expected**: proceeds into the recall step; after answering the
   first word, the app goes straight to the next recall step (or
   "session complete" if it was the last word) — no sentence screen ever
   appears.
4. Finish the session, use "Practice again", and pick Sentence mode this
   time.
5. **Expected**: today's existing recall → sentence → feedback flow
   appears for every word.

## Scenario 4 — Web UI, `--mode` only applies when `--group` is locked

```bash
.venv/bin/python -m src.web --vocab-dir /tmp/mode-quickstart-vocab --progress-file /tmp/mode-quickstart-progress4.md --group unit1 --mode recall-only --port 8421
```

**Expected**: goes straight into the recall step (no choose screen, per
existing `--group`-locked behavior); after answering, moves straight to
the next word/completion — no sentence step.

```bash
.venv/bin/python -m src.web --vocab-dir /tmp/mode-quickstart-vocab --progress-file /tmp/mode-quickstart-progress5.md --mode recall-only --port 8422
```

**Expected**: `--group` is absent, so the interactive choose screen
still appears — the `--mode recall-only` flag here has no effect;
Sentence is still the pre-selected default on that screen.

## Scenario 5 — Recall-only works with the local correction service stopped

Stop (or don't start) the local Ollama server, then repeat Scenario 2 (or
Scenario 3 picking Recall-only). **Expected**: the recall-only session
completes normally with no error, since it never attempts a correction
call (SC-001) — contrast with attempting sentence mode under the same
condition, which already degrades gracefully today (shows "correction
unavailable") rather than failing.

## Automated coverage

See `plan.md`'s Project Structure for exact file paths:
- `tests/unit/test_session_state.py` — `mode`/`self.recall_only` on
  `__init__`/`select_collection()`, and `submit_answer()`'s branch
- A CLI-level integration test covering `run_session(mode=...)`
- `tests/contract/test_web_api_contract.py` — `POST /api/select`'s
  `"mode"` field, and a full recall-only flow through the test client
- `tests/unit/test_web_static_assets.py` — mode-toggle wiring in
  `app.js`

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src/
```

Both MUST pass, and Scenarios 1–5 above MUST be run manually before this
feature is considered done.
