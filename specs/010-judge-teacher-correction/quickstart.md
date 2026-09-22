# Quickstart: Split Sentence Review into Judge and Teacher Roles

Validates that the feature described in `spec.md` works end-to-end, once
implemented per `plan.md`/`tasks.md`. Unlike most other features in this
project, there is no new user-facing flow to click through — the mandatory
verification here is the Principle II correctness check (FR-008), run
directly against `llm_client.request_correction()`.

## Prerequisites

```bash
cd english-tutor
.venv/bin/pip install -e ".[dev]"
```

Ollama running locally with the default model pulled (see repository
`README.md`):

```bash
ollama pull qwen3:14b
```

## Automated coverage (run first)

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src/
```

Both MUST pass. This proves the two-call plumbing is correct (right
requests made in the right order, every failure mode still reported as
`available=False`, `CorrectionResult`'s shape unchanged) — it does **not**
prove the model's actual judgments are good. That's what the manual pass
below is for.

## Manual correctness check (FR-008, Constitution Principle II) — REQUIRED

Run each example sentence below through the live pipeline:

```bash
.venv/bin/python -c "
from src.services.llm_client import request_correction
result = request_correction('<target>', '<sentence>', base_url='http://localhost:11434')
print(result)
"
```

| # | Target | Sentence | Expected `needs_correction` | Notes |
|---|---|---|---|---|
| 1 | `receive` | "I received a gift yesterday." | `False` | Already correct and natural — confirm the Teacher is never invoked (no extra delay past the Judge call) |
| 2 | `receive` | "I receive a gift yesterday." | `True` | Grammar problem (wrong tense) — `corrected` should read naturally in the past tense |
| 3 | `receive` | "I did receive of a gift." | `True` | Grammatically parseable but unnatural phrasing — confirms the Judge's `natural` check catches something `grammatically_correct` alone might not |
| 4 | `receive` | "I am happy today." | `False` | Target expression missing (`uses_expression: False`), but otherwise correct — confirms a missing target expression does not by itself trigger the Teacher (matches today's existing independence between the two signals) |
| 5 | `tailor` | "He is a tailor who make suits." | `True` | Grammar problem (subject-verb agreement) with a different target word, for variety |
| 6 | `unbearable` | "The heat was unbearable." | `False` | A second already-correct example with a different target word |
| 7 | `receive` | "I happy today." | `True` | Combined case: target expression missing *and* a grammar problem — confirms the Teacher still runs based on `needs_correction` alone, independent of `uses_expression` |

For each row, confirm:
- `available` is `True` (Ollama reachable and both calls, as applicable, succeeded).
- `uses_expression` matches whether the sentence actually contains the
  target expression (not affected by this feature, but worth reconfirming
  it's still independent of `needs_correction`).
- `needs_correction` matches the table above.
- When `True`, `corrected` reads as a natural, grammatically sound
  sentence using the target expression, and `explanation` is a short,
  accurate description of the mistake — a **human judgment call**, which
  is the actual point of this check (Principle II: "a reviewed test suite
  ... a human pedagogical review, or both").

If a result looks wrong, don't proceed to `/speckit-tasks`'s completion —
revisit the Judge/Teacher prompt wording (`contracts/ollama-correction-contract-delta.md`)
first.

## Regression check

Confirm the full practice flow still works end-to-end through the web UI
(any existing vocabulary folder), since this feature is invisible from
that side by design:

```bash
.venv/bin/python -m src.web --vocab-dir vocabulary --progress-file /tmp/judge-teacher-progress.md --group unit1
```

Answer a recall step, submit a sentence with a deliberate mistake, and
confirm the feedback shown is exactly the same kind of message
(`Corrected: ...` / `Your sentence is already correct and natural.` /
etc.) as before this feature — because nothing downstream changed, this
should be indistinguishable from today's behavior.
