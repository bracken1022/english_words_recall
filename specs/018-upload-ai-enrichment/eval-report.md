# Enrichment Evaluation Report (T053)

## Final result (run 2, after the IPA source revision): **PASS**

**Date**: 2026-10-03 · **Model**: `qwen3:14b`, used for meanings and
alternates only · **IPA**: offline CMU Pronouncing Dictionary → OALD NAmE
(research R4, revised) · **Duration**: 81 s for the whole fixture, about
1 s per word.

| Measure | Result | Target | |
|---|---|---|---|
| IPA match or flagged | 50/50 (100%): 48 match, 2 flagged | ≥ 95% (SC-002) | ✅ |
| IPA wrong and unflagged | 0 | 0 | ✅ |
| Chinese meaning hits an accepted gloss | 50/50 (100%) | n/a | ✅ |
| Heteronyms flagged | 8/8 | all | ✅ |
| Synonym traps leaked | 0 | 0 (SC-003) | ✅ |
| Spelling variants found | 10/11 (91%) | ≥ 90% (SC-003) | ✅ |
| Invalid output that would be written | 0 | 0 (SC-002) | ✅ |

- **Flagged**: *genuine* and *advertisement*. The dictionary lists them
  with stress on different syllables, so they are marked for review
  rather than guessed.
- **Missed variant**: *travelled* → *traveled*. The model proposed no
  alternate. This is a safe failure, since alternates are optional.
- **How IPA is compared**: two transcriptions count as the same when they
  differ only in recognized dictionary conventions. Those are: where the
  stress mark sits within a consonant cluster, secondary stress, the
  flap mark, unstressed ɪ/ə, ɑː/ɔː (the cot–caught merger), and
  syllabic n/l versus ən/əl. Four fixture words gained `ipa_also`
  variants that Merriam-Webster attests: schedule, leisure, resilient
  and February. The stressed syllable, the consonants and the full vowels
  must still match exactly.

---

## Run 1 (model-generated IPA): FAIL — kept for the record

**Date**: 2026-10-03
**Model**: `qwen3:14b` (local Ollama, `think: false`, temperature 0)
**Command**: `python -m src.tools.eval_enrichment --model qwen3:14b`
**Fixture**: `tests/fixtures/enrichment_eval.yml`: 50 words, 8 heteronyms,
21 synonym traps, 11 spelling variants. It took 21 minutes, about 17 s per
model call.

### Result: **FAIL**. The IPA target in SC-002 is not met. Every other target passes.

| Measure | Result | Target | |
|---|---|---|---|
| Chinese meaning hits an accepted gloss | 49/49 (100%) | n/a | ✅ |
| Synonym traps leaked as alternates | 0 | 0 (SC-003) | ✅ |
| Spelling variants found | 11/11 (100%) | ≥ 90% (SC-003) | ✅ |
| Heteronyms flagged for review | 8/8 | all | ✅ |
| Invalid output that would be written | 0 | 0 (SC-002) | ✅ |
| IPA match or flagged | 28/50 (56%) | ≥ 95% (SC-002) | ❌ |
| IPA **wrong and unflagged** | 21 | 0 | ❌ |

The validators did their job. No malformed, British-marked or ill-stressed
IPA got through, and 19 such outputs were turned into "Pronunciation
needs review". However, the model often produces **well-formed but wrong**
American IPA. Examples: zealous /ˈzeɪləs/, garage /ˈɡærɑːʒ/,
tomato /ˈtɑːmətoʊ/, vitamin /ˈvɪtəmɪn/ (British), dance /dɑːns/
(British), hierarchy /ˈhɪrɑːkərɪ/. No symbol-level check can detect these.

Three of the 21 are acceptable dictionary variants rather than errors:
library /ˈlaɪbrəri/, nation /ˈneɪʃən/ and inevitable /…təbəl/. The
other 18 are genuinely wrong.

### Prompt tuning attempt

I added worked NAmE examples to the system prompt, using none of the eval
words, plus an instruction to set `ipa_uncertain` when unsure. I re-ran it
on the 23 words that had failed:

- **Before**: 0/23 correct.
- **After**: 7/23 correct, 3 flagged, **13 still wrong and unflagged**.

That is an improvement, but far from the target. The model rarely
reports that it is unsure. The prompt change was **not** kept in
`src/services/enrichment_client.py`.

### Conclusion of run 1

`qwen3:14b` cannot be trusted to generate American IPA unreviewed. The
product owner chose to take IPA from an offline American dictionary
instead (research R4, revised; tasks T056–T062). The validators were not
loosened.
