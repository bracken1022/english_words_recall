# Part-of-Speech Evaluation Report (T030, T041)

## Final run (run 4): **PASS**

The setup is the same as run 3. The scoring now accepts any acceptable
label for a multi-word expression, as decided by the product owner on
2026-10-05.

- **Part of speech**: 58/60 (97%). The 2 wrong are hurry (`adv.`) and
  present (`adv.`).
- **Spelling variants**: 10/11 (91%).
- **IPA**: 60/60 match or flagged, 0 wrong.
- **Chinese meanings**: 60/60.
- **Part-of-speech notes, synonym leaks, invalid output**: 0, 0, 0.

---

## Run 3: separate request, first label only — **FAIL by 1 word**

| Measure | Result | Target | |
|---|---|---|---|
| Part of speech match or flagged | 56/60 (93%), 4 wrong | ≥ 95% | ❌ |
| Spelling variants found | 10/11 (91%), back to the spec 018 level | ≥ 90% | ✅ |
| IPA match or flagged | 60/60, 0 wrong | ≥ 95% | ✅ |
| Chinese meaning hits | 60/60 | n/a | ✅ |
| Part-of-speech notes left in meanings / synonym leaks / invalid output | 0 / 0 / 0 | 0 | ✅ |

The 4 misses:

| Word | Model | Reference | Assessment |
|---|---|---|---|
| hurry | adv. | v. | wrong |
| present | adv. | n. adj. v. | wrong |
| take off | v. | phr. v. (v. listed as also acceptable) | defensible: OALD lists it under the verb |
| tend to | v. | phr. v. (v. listed as also acceptable) | defensible: OALD lists it under the verb |

The scoring rule (research R6) requires at least one label from `pos`.
A phrase labelled `v.` alone therefore counts as wrong, even though `v.`
is in its `pos_ok` list. The rule was not changed after seeing the
results; whether to accept `v.` for phrases is the product owner's call.

Runs so far:

| Run | Setup | Part of speech | Variants |
|---|---|---|---|
| 1 | `pos` in the meaning request | 85% | 64% |
| 2 | Separate request, all labels | 88%* | 82% |
| 3 | Separate request, first label only; meaning prompt identical to spec 018 | 93% | 91% |

\*Re-scored after fixing the fixture's `phr. v.` bug (T039).

---

## Run 1

**Date**: 2026-10-05
**Model**: `qwen3:14b` (local Ollama, temperature 0)
**Command**: `python -m src.tools.eval_enrichment --model qwen3:14b`
**Fixture**: `tests/fixtures/enrichment_eval.yml`: 60 words, 10 of them
multi-class.

## Result: **FAIL**

Two targets are missed: the part-of-speech target in spec 019 SC-002,
and, as a regression, the spec 018 spelling-variant target in SC-003.

| Measure | Result | Target | |
|---|---|---|---|
| Part of speech match or flagged | 51/60 (85%): 51 match, 0 flagged, **8 wrong** | ≥ 95% | ❌ |
| Part-of-speech notes left in meanings | 0 | 0 | ✅ |
| Spelling variants found | **7/11 (64%)**, down from 10/11 in the spec 018 run | ≥ 90% | ❌ |
| IPA match or flagged | 59/60 (98%), 0 wrong | ≥ 95% | ✅ |
| Chinese meaning hits | 59/59 | n/a | ✅ |
| Synonym leaks / invalid output | 0 / 0 | 0 | ✅ |

## What went wrong

**Over-labelling.** The model adds extra classes that the meanings don't
support:

| Word | Model's labels | Expected |
|---|---|---|
| tomato | n. adj. | n. |
| coffee | n. v. | n. |
| vitamin | n. v. | n. |
| garage | n. adj. | n. |
| neighbor | n. adj. | n. |
| February | n. adj. adv. det. | n. |
| hurry | adv. adj. v. | v. |
| present | adv. n. v. | n. adj. v. |

Every label is a valid label, so the checks can't catch these. They are
well-formed but wrong, the same failure pattern as the model's IPA in
spec 018.

**Regression.** Adding `pos` to the same request made the model drop
spelling variants it had found before: epitomise→epitomize,
grey→gray, analyse→analyze and travelled→traveled. A longer request
seems to cost alternate quality.

## Status

This is the T030 checkpoint: the gate failed, so the product owner
decides the fallback before upload labels are relied on.
