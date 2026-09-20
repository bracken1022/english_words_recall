# Quickstart: Choose a Vocabulary Collection Before Practicing

Validates that the feature described in `spec.md` works end-to-end, once
implemented per `plan.md`/`tasks.md`. Assumes the project is already set
up per the repository root `README.md`.

## Prerequisites

```bash
cd english-tutor
.venv/bin/pip install -e ".[dev]"
```

A scratch vocabulary folder with two collections plus one ungrouped word:

```bash
mkdir -p /tmp/collections-quickstart-vocab
cat > /tmp/collections-quickstart-vocab/unit1.md <<'EOF'
---
english: receive
alternates: [accept]
chinese: 收到；接受
group: unit1
---
EOF
cat > /tmp/collections-quickstart-vocab/t-words.md <<'EOF'
---
english: tailor
chinese: 裁缝；定制
group: t-words
---

---
english: mystery
chinese: 谜；神秘
---
EOF
```

## Run — interactive mode (no `--group`)

```bash
.venv/bin/python -m src.web \
  --vocab-dir /tmp/collections-quickstart-vocab \
  --progress-file /tmp/collections-quickstart-progress.md \
  --port 8420
```

Open `http://localhost:8420/`.

### 1. Choice screen appears first (US1, FR-001–FR-002, FR-004, FR-008)

- **Expected**: before any Chinese meaning appears, a list of choices:
  "Practice everything" (3), "t-words" (1), "unit1" (1), "Ungrouped words"
  (1) — in that order.

### 2. Picking a named collection scopes the session (US1, FR-003)

- Pick "unit1". **Expected**: only `receive`'s Chinese meaning ever
  appears; finishing it reaches "Session complete" immediately (it's the
  only word in that collection).

### 3. No mid-session switch is offered (Edge case, FR-006)

- Start over, pick "Practice everything," answer the first word's recall
  step, and reach the sentence-writing step.
  - **Expected**: nothing on screen offers a way back to the choice
    screen until the session reaches "Session complete."

### 4. Completion offers restart (US2, FR-006)

- Finish the "Practice everything" session (skip sentences to move
  quickly — see `006`'s quickstart).
  - **Expected**: the completion screen offers a "practice again" control
    in addition to the existing tally.
- Use it. **Expected**: the same choice screen from step 1 reappears.

### 5. Restart picks up vocabulary changes (Assumptions)

- While still on the choice screen from step 4, add a new file:

  ```bash
  cat > /tmp/collections-quickstart-vocab/new.md <<'EOF'
  ---
  english: tablet
  chinese: 平板电脑
  group: unit1
  ---
  EOF
  ```

- Reload the choice screen (or trigger restart again from a completed
  session). **Expected**: "unit1"'s count is now 2, including `tablet`.

## Run — locked mode (`--group`, unchanged from `006`)

```bash
.venv/bin/python -m src.web \
  --vocab-dir /tmp/collections-quickstart-vocab \
  --progress-file /tmp/collections-quickstart-progress2.md \
  --group unit1 --port 8421
```

- **Expected**: the recall step for `receive` appears immediately — no
  choice screen at any point, and the completion screen (once reached)
  offers no "practice again" control, exactly matching `006`'s existing
  behavior.

## Automated coverage

See `plan.md`'s Project Structure for exact file paths:
- `tests/unit/test_session_state.py` — collection listing,
  `select_collection()`, `restart()`, `group_locked` behavior
- `tests/contract/test_web_api_contract.py` — `POST /api/select`,
  `POST /api/restart` HTTP contract
- `tests/integration/test_web_session_flow.py` — full choose → practice →
  complete → restart loop, and a `--group`-locked run that never sees
  `"choose"`
- `tests/unit/test_web_static_assets.py` — static assertion that `app.js`
  renders the choice list and wires the restart control

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src/
```

Both MUST pass before this feature is considered done.
