# Quickstart: Choose Sequential or Random Word Order

Validates that the feature described in `spec.md` works end-to-end, once
implemented per `plan.md`/`tasks.md`.

## Prerequisites

```bash
cd english-tutor
.venv/bin/pip install -e ".[dev]"
```

A scratch vocabulary with several words, so a shuffle is visibly
different from file order most of the time:

```bash
mkdir -p /tmp/order-quickstart-vocab
cat > /tmp/order-quickstart-vocab/words.md <<'EOF'
---
english: receive
chinese: 收到
group: unit1
---

---
english: tailor
chinese: 裁缝
group: unit1
---

---
english: mystery
chinese: 谜
group: unit1
---

---
english: unbearable
chinese: 难以忍受的
group: unit1
---
EOF
```

## Scenario 1 — CLI, sequential (unchanged default)

```bash
.venv/bin/python -m src.cli --vocab-dir /tmp/order-quickstart-vocab --progress-file /tmp/order-quickstart-progress.md --group unit1
```

**Expected**: words appear in file order — `receive`, `tailor`,
`mystery`, `unbearable` — exactly as before this feature existed.

## Scenario 2 — CLI, random order

```bash
.venv/bin/python -m src.cli --vocab-dir /tmp/order-quickstart-vocab --progress-file /tmp/order-quickstart-progress2.md --group unit1 --order random
```

**Expected**: the four words still all appear, each exactly once, before
the session ends — but very likely not in file order this time.

## Scenario 3 — Web UI, interactive picker offers both

```bash
.venv/bin/python -m src.web --vocab-dir /tmp/order-quickstart-vocab --progress-file /tmp/order-quickstart-progress3.md --port 8420
```

Open `http://localhost:8420/`.

1. **Expected**: the choose screen (spec `007`) now also shows an order
   toggle (Sequential/Random), defaulting to Sequential, alongside the
   collection list.
2. Select Random, then pick "unit1".
3. **Expected**: proceeds straight into the recall step; over the course
   of the session, all four words appear exactly once, in an order that's
   very likely not file order.
4. Finish the session, use "Practice again" (spec `007`), and pick Random
   again.
5. **Expected**: a fresh shuffle — not necessarily the same order as the
   previous pass (no order is remembered between sessions).

## Scenario 4 — Web UI, `--order` only applies when `--group` is locked

```bash
.venv/bin/python -m src.web --vocab-dir /tmp/order-quickstart-vocab --progress-file /tmp/order-quickstart-progress4.md --group unit1 --order random --port 8421
```

**Expected**: goes straight into the recall step (no choose screen, per
`007`'s existing `--group`-locked behavior) with the four words in a
shuffled order.

```bash
.venv/bin/python -m src.web --vocab-dir /tmp/order-quickstart-vocab --progress-file /tmp/order-quickstart-progress5.md --order random --port 8422
```

**Expected**: `--group` is absent, so the interactive choose screen still
appears (per `007`) — the `--order random` flag here has no effect;
Sequential is still the pre-selected default on that screen, per
`research.md` §3.

## Automated coverage

See `plan.md`'s Project Structure for exact file paths:
- `tests/unit/test_session_state.py` — `order` on `__init__`/
  `select_collection`, shuffle-invocation and permutation checks
- `tests/integration/test_session_order.py` — CLI `run_session(order=...)`
- `tests/contract/test_web_api_contract.py` — `POST /api/select`'s
  `"order"` field
- `tests/integration/test_web_session_flow.py` — full web random-order
  scenario
- `tests/unit/test_web_static_assets.py` — order-toggle wiring in `app.js`

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src/
```

Both MUST pass, and Scenarios 1–4 above MUST be run manually (a shuffle's
actual visible effect isn't something the automated suite asserts
directly — see `research.md` §6), before this feature is considered done.
