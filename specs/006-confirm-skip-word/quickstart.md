# Quickstart: Confirm Before Skipping a Word Without a Sentence

Validates that the feature described in `spec.md` works end-to-end, once
implemented per `plan.md`/`tasks.md`. Assumes the project is already set
up per the repository root `README.md` (venv created, dependencies
installed).

## Prerequisites

```bash
cd english-tutor
.venv/bin/pip install -e ".[dev]"
```

A small scratch vocabulary directory keeps this quick and deterministic:

```bash
mkdir -p /tmp/skip-quickstart-vocab
cat > /tmp/skip-quickstart-vocab/words.md <<'EOF'
---
english: receive
alternates: [accept]
chinese: 收到；接受
group: q
---

---
english: tailor
alternates: []
chinese: 裁缝；定制
group: q
---
EOF
```

## Run

```bash
.venv/bin/python -m src.web \
  --vocab-dir /tmp/skip-quickstart-vocab \
  --progress-file /tmp/skip-quickstart-progress.md \
  --port 8420
```

Open `http://localhost:8420/` in a browser.

## Validation scenarios

### 1. Skipping mid-session (US1, FR-001–FR-005)

1. On the recall step, type anything and submit (e.g. `receive`) to reach
   the sentence-writing step.
2. Leave the sentence input empty (or type only spaces) and submit.
   - **Expected**: a confirmation prompt appears asking whether to skip
     this word. No spinner, no "Reviewing your sentence..." — no
     correction request is made.
3. Decline/cancel the prompt.
   - **Expected**: still on the same word's sentence-writing step; the
     input is exactly as you left it; nothing else has changed.
4. Submit empty again, and this time confirm.
   - **Expected**: immediately moves to the next word's recall step
     (`裁缝；定制`) — no sentence-correction feedback screen was shown for
     `receive`.

### 2. Skipping the last word reaches completion (Edge case)

1. On the second word's recall step, answer anything, then at the
   sentence step submit empty and confirm the skip.
   - **Expected**: reaches the "Session complete" screen directly (this
     was the last word).

### 3. Skipped words count correctly afterward (US2, FR-006–FR-008)

1. Check the completion screen's tally.
   - **Expected**: both words count toward "words recalled correctly" (or
     not) based on what was typed at the recall step — whether the
     sentence was skipped has no effect on this count.
2. Inspect the progress file:

   ```bash
   cat /tmp/skip-quickstart-progress.md
   ```

   - **Expected**: the skipped word's YAML block has `timestamp`, `item`,
     `answer`, `correct` — and no `sentence:`/`feedback:` keys. Any word
     where a real sentence was submitted still has both.

### 4. Non-empty sentences are unaffected (FR-008)

1. Start a fresh session (restart the server, or use a fresh
   `--progress-file`) and this time type a real sentence at the sentence
   step.
   - **Expected**: no confirmation prompt appears; behaves exactly as
     before this feature (spinner, correction feedback, etc.).

## Automated coverage

The scenarios above are also covered by (see `plan.md`'s Project
Structure for exact file paths):
- `tests/unit/test_session_state.py` — `skip_sentence()` transition logic
- `tests/contract/test_web_api_contract.py` — `POST /api/skip` HTTP
  contract, including that `request_correction` is never called
- `tests/integration/test_web_session_flow.py` — full recall → skip →
  next/complete flow, plus progress-log read-back
- `tests/unit/test_web_static_assets.py` — static assertion that `app.js`
  wires up the empty-check/confirm/`/api/skip` path

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src/
```

Both MUST pass before this feature is considered done.
