# Quickstart: Show a Correct Recall Result in Green

Validates that the feature described in `spec.md` works end-to-end, once
implemented per `plan.md`/`tasks.md`.

## Prerequisites

```bash
cd english-tutor
.venv/bin/pip install -e ".[dev]"
```

```bash
mkdir -p /tmp/green-quickstart-vocab
cat > /tmp/green-quickstart-vocab/one.md <<'EOF'
---
english: receive
alternates: [accept]
chinese: 收到；接受
---
EOF
```

## Run

```bash
.venv/bin/python -m src.web \
  --vocab-dir /tmp/green-quickstart-vocab \
  --progress-file /tmp/green-quickstart-progress.md \
  --port 8420
```

Open `http://localhost:8420/`.

## Validation scenarios

### 1. Correct answer shows green (US1, FR-001, SC-001)

1. Type `receive` (or `accept`) and submit.
2. **Expected**: the "✓ Correct: receive, accept" result appears in green,
   not the red used elsewhere in the app (the margin rule, the stamp,
   etc.).

### 2. Incorrect answer is unchanged (FR-003, SC-002)

1. Restart with a fresh progress file, answer incorrectly this time
   (e.g. type `nonsense`).
2. **Expected**: the "✗ Incorrect. The correct expression is: ..." result
   still appears exactly as it did before this feature — same red,
   same stamp styling.

### 3. Correct/incorrect stay distinguishable without color (FR-002, SC-003)

1. With either result showing, view the page with color removed (e.g. a
   browser's built-in grayscale rendering, an OS grayscale display mode,
   or simply squint-testing that the ✓/✗ symbol and "Correct:"/
   "Incorrect." wording alone are enough to tell them apart).
2. **Expected**: still unambiguous which outcome occurred, with no
   reliance on color.

### 4. Dark mode reads clearly (Constraints)

1. Repeat Scenario 1 with the OS/browser set to dark mode (or
   `prefers-color-scheme: dark` forced in devtools).
2. **Expected**: the green is legible against the dark card background,
   not washed out or low-contrast.

## Automated coverage

- `tests/unit/test_web_static_assets.py` — static assertion that
  `.feedback-correct` references the new green token and not `--red`
  (see `research.md` §3). This proves the token changed; it does not
  replace Scenarios 1–4 above, which are the actual visual proof.

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src/
```

Both MUST pass, and Scenarios 1–4 MUST be run in a real browser, before
this feature is considered done.
