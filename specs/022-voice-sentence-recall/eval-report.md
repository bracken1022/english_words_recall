# Eval report: voice in sentence recall (spec 022)

## SC-002 recognition accuracy and SC-001 speed

### Smoke run (synthetic voice) — 2026-10-15

- 20 example sentences from the spec 021 review set (`backups/examples-021-eval/REVIEW.md`, rows 1–20),
  spoken by macOS `say` (Samantha), saved as AAC/MP4 (what Safari records).
- `python -m src.tools.eval_voice backups/voice-022-smoke`, Whisper `base`, `int8`.

| Measure | Result | Target |
|---|---|---|
| Word accuracy | 203/204 (99.5%) | ≥ 90% |
| Time per clip | median 0.3 s, max 0.8 s, 0 over 3 s | < 3 s |
| Misses | `s01`: "zealous" heard as "jealous" | — |

`compute_type="int8"` was chosen over the default (float16, converted to
float32 on this Mac with a warning): same accuracy, slowest clip 2.2 s →
0.8 s.

The one miss is the target word itself, which is exactly what the
highlight shows the learner (they edit it before revealing).

### Release gate (real voice) — PENDING

A synthetic voice is not a learner. The gate needs 20 example sentences
read aloud by a real learner (with consent), one file per sentence plus
`sentences.yml`, in `backups/voice-022-eval/`, then:

```sh
.venv/bin/python -m src.tools.eval_voice backups/voice-022-eval
```

Pass: ≥ 90% of words and every clip under 3 s. If `base` is under 90%,
re-run with `--model small` (research R1).

## SC-007 comparison correctness

`tests/fixtures/word_diff_cases.yml`: 27 reviewed cases, all passing
(`tests/unit/test_word_diff.py`), including the accepted limits
(contractions, digits, British/American spelling). The "two words
swapped" case marks `always` as moved (either word would be a fair
guide).
